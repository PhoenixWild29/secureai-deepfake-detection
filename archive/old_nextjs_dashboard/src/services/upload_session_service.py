#!/usr/bin/env python3
"""
Upload Session Service
Service for managing upload sessions with Redis storage and quota validation
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
import asyncio
import aioredis
from aioredis import Redis

from src.core.config import upload_settings
from src.services.quota_management import QuotaService, QuotaExceededError
from src.api.v1.dashboard.schemas import (
    UploadSessionInitiateRequest,
    UploadSessionResponse,
    UploadSessionStatus,
    UploadSessionValidationRequest,
    UploadSessionValidationResponse,
    UploadQuotaInfo,
    UploadSessionError,
    UploadSessionErrorCodes,
    UploadConfig,
    DashboardContext
)

logger = logging.getLogger(__name__)


class UploadSessionService:
    """
    Service for managing upload sessions with Redis storage.
    Handles session creation, validation, and quota management.
    """
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.quota_service = QuotaService()
        self.config = upload_settings
        self._redis_pool: Optional[aioredis.ConnectionPool] = None
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection and validate configuration.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Validate configuration
            if not self.config.validate_configuration()['overall_valid']:
                logger.error("Upload session configuration validation failed")
                return False
            
            # Create Redis connection pool
            redis_config = self.config.get_redis_config_dict()
            self._redis_pool = aioredis.ConnectionPool.from_url(
                f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}",
                password=redis_config.get('password'),
                decode_responses=redis_config['decode_responses'],
                socket_timeout=redis_config['socket_timeout'],
                socket_connect_timeout=redis_config['socket_connect_timeout'],
                retry_on_timeout=redis_config['retry_on_timeout'],
                max_connections=redis_config['max_connections'],
                health_check_interval=redis_config['health_check_interval']
            )
            
            # Test Redis connection
            self.redis = aioredis.Redis(connection_pool=self._redis_pool)
            await self.redis.ping()
            
            logger.info("Upload session service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize upload session service: {e}")
            return False
    
    async def close(self):
        """Close Redis connections"""
        if self.redis:
            await self.redis.close()
        if self._redis_pool:
            await self._redis_pool.disconnect()
    
    def _generate_session_key(self, session_id: UUID) -> str:
        """Generate Redis key for session data"""
        return f"{self.config.upload_session.redis_session_prefix}:{session_id}"
    
    def _generate_user_sessions_key(self, user_id: UUID) -> str:
        """Generate Redis key for user's active sessions"""
        return f"{self.config.upload_session.redis_session_prefix}:user:{user_id}"
    
    async def create_upload_session(
        self,
        user_id: UUID,
        request: UploadSessionInitiateRequest
    ) -> UploadSessionResponse:
        """
        Create a new upload session with quota validation.
        
        Args:
            user_id: User ID requesting the session
            request: Session initiation request
            
        Returns:
            UploadSessionResponse: Session details and upload information
            
        Raises:
            QuotaExceededError: If user quota is exceeded
            ValueError: If request validation fails
        """
        try:
            # Validate file size if provided
            if request.expected_file_size:
                if request.expected_file_size > self.config.upload_session.max_file_size_bytes:
                    raise ValueError(f"File size exceeds maximum limit of {self.config.upload_session.max_file_size_mb}MB")
            
            # Validate file format if provided
            if request.file_format:
                if request.file_format not in self.config.upload_session.allowed_formats:
                    raise ValueError(f"Unsupported file format. Allowed: {', '.join(self.config.upload_session.allowed_formats)}")
            
            # Check user quota
            quota_info = await self._get_user_quota_info(user_id)
            
            # Validate quota for expected file size
            if request.expected_file_size:
                if quota_info.quota_remaining < request.expected_file_size:
                    raise QuotaExceededError(
                        f"Insufficient quota. Required: {request.expected_file_size / (1024*1024):.1f}MB, "
                        f"Available: {quota_info.quota_remaining / (1024*1024):.1f}MB"
                    )
            
            # Generate session ID
            session_id = uuid4()
            
            # Create session data
            session_data = {
                'session_id': str(session_id),
                'user_id': str(user_id),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': (datetime.now(timezone.utc) + self.config.upload_session.session_ttl_timedelta).isoformat(),
                'dashboard_context': request.dashboard_context.dict(),
                'expected_file_size': request.expected_file_size,
                'file_format': request.file_format,
                'status': 'active',
                'quota_info': quota_info.dict()
            }
            
            # Store session in Redis
            session_key = self._generate_session_key(session_id)
            user_sessions_key = self._generate_user_sessions_key(user_id)
            
            # Use Redis pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Store session data
                await pipe.hset(session_key, mapping=session_data)
                await pipe.expire(session_key, self.config.upload_session.session_ttl_seconds)
                
                # Add to user's active sessions
                await pipe.sadd(user_sessions_key, str(session_id))
                await pipe.expire(user_sessions_key, self.config.upload_session.session_ttl_seconds)
                
                # Execute pipeline
                await pipe.execute()
            
            # Generate upload URL (placeholder - would integrate with actual storage)
            upload_url = await self._generate_upload_url(session_id, user_id)
            
            # Create response
            response = UploadSessionResponse(
                session_id=session_id,
                upload_url=upload_url,
                max_file_size=self.config.upload_session.max_file_size_bytes,
                allowed_formats=self.config.upload_session.allowed_formats.copy(),
                remaining_quota=quota_info.quota_remaining,
                quota_limit=quota_info.quota_limit,
                session_expires_at=datetime.fromisoformat(session_data['expires_at']),
                dashboard_context=request.dashboard_context,
                upload_instructions={
                    'method': 'PUT',
                    'headers': {
                        'Content-Type': 'application/octet-stream'
                    },
                    'timeout': self.config.upload_session.upload_url_ttl_seconds
                }
            )
            
            logger.info(f"Created upload session {session_id} for user {user_id}")
            return response
            
        except QuotaExceededError:
            raise
        except Exception as e:
            logger.error(f"Failed to create upload session for user {user_id}: {e}")
            raise ValueError(f"Failed to create upload session: {str(e)}")
    
    async def validate_upload_session(
        self,
        request: UploadSessionValidationRequest
    ) -> UploadSessionValidationResponse:
        """
        Validate an upload session and check user ownership.
        
        Args:
            request: Validation request with session_id and user_id
            
        Returns:
            UploadSessionValidationResponse: Validation results
        """
        try:
            session_key = self._generate_session_key(request.session_id)
            
            # Get session data from Redis
            session_data = await self.redis.hgetall(session_key)
            
            if not session_data:
                return UploadSessionValidationResponse(
                    is_valid=False,
                    is_owner=False,
                    error_message="Session not found or expired"
                )
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            is_expired = datetime.now(timezone.utc) > expires_at
            
            if is_expired:
                # Clean up expired session
                await self._cleanup_session(request.session_id, UUID(session_data['user_id']))
                return UploadSessionValidationResponse(
                    is_valid=False,
                    is_owner=False,
                    error_message="Session has expired"
                )
            
            # Check user ownership
            is_owner = session_data['user_id'] == str(request.user_id)
            
            if not is_owner:
                return UploadSessionValidationResponse(
                    is_valid=False,
                    is_owner=False,
                    error_message="Unauthorized access to session"
                )
            
            # Create session status
            session_status = UploadSessionStatus(
                session_id=request.session_id,
                user_id=request.user_id,
                status=session_data['status'],
                created_at=datetime.fromisoformat(session_data['created_at']),
                expires_at=expires_at,
                dashboard_context=DashboardContext(**json.loads(session_data['dashboard_context']) if isinstance(session_data['dashboard_context'], str) else session_data['dashboard_context']),
                upload_url=await self._generate_upload_url(request.session_id, request.user_id),
                is_expired=is_expired,
                is_valid=True
            )
            
            return UploadSessionValidationResponse(
                is_valid=True,
                is_owner=True,
                session_status=session_status
            )
            
        except Exception as e:
            logger.error(f"Failed to validate session {request.session_id}: {e}")
            return UploadSessionValidationResponse(
                is_valid=False,
                is_owner=False,
                error_message=f"Validation failed: {str(e)}"
            )
    
    async def get_user_active_sessions(self, user_id: UUID) -> List[UploadSessionStatus]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[UploadSessionStatus]: List of active sessions
        """
        try:
            user_sessions_key = self._generate_user_sessions_key(user_id)
            session_ids = await self.redis.smembers(user_sessions_key)
            
            active_sessions = []
            for session_id_str in session_ids:
                session_id = UUID(session_id_str)
                session_key = self._generate_session_key(session_id)
                session_data = await self.redis.hgetall(session_key)
                
                if session_data:
                    expires_at = datetime.fromisoformat(session_data['expires_at'])
                    is_expired = datetime.now(timezone.utc) > expires_at
                    
                    if not is_expired:
                        session_status = UploadSessionStatus(
                            session_id=session_id,
                            user_id=user_id,
                            status=session_data['status'],
                            created_at=datetime.fromisoformat(session_data['created_at']),
                            expires_at=expires_at,
                            dashboard_context=DashboardContext(**json.loads(session_data['dashboard_context']) if isinstance(session_data['dashboard_context'], str) else session_data['dashboard_context']),
                            upload_url=await self._generate_upload_url(session_id, user_id),
                            is_expired=is_expired,
                            is_valid=True
                        )
                        active_sessions.append(session_status)
                    else:
                        # Clean up expired session
                        await self._cleanup_session(session_id, user_id)
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions for all users.
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            # Get all session keys
            pattern = f"{self.config.upload_session.redis_session_prefix}:*"
            session_keys = await self.redis.keys(pattern)
            
            cleaned_count = 0
            current_time = datetime.now(timezone.utc)
            
            for session_key in session_keys:
                if ':user:' in session_key:
                    continue  # Skip user session sets
                
                session_data = await self.redis.hgetall(session_key)
                if session_data and 'expires_at' in session_data:
                    expires_at = datetime.fromisoformat(session_data['expires_at'])
                    if current_time > expires_at:
                        session_id = UUID(session_data['session_id'])
                        user_id = UUID(session_data['user_id'])
                        await self._cleanup_session(session_id, user_id)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def _get_user_quota_info(self, user_id: UUID) -> UploadQuotaInfo:
        """Get user quota information"""
        try:
            # Get quota from quota service
            quota_data = self.quota_service.get_user_quota(str(user_id))
            
            quota_limit = quota_data.get('quota_limit', self.config.upload_session.default_quota_limit_bytes)
            quota_used = quota_data.get('quota_used', 0)
            quota_remaining = max(0, quota_limit - quota_used)
            
            # Calculate reset date (simplified - would be more sophisticated in production)
            reset_date = datetime.now(timezone.utc) + timedelta(days=self.config.upload_session.quota_reset_period_days)
            
            return UploadQuotaInfo(
                quota_limit=quota_limit,
                quota_used=quota_used,
                quota_remaining=quota_remaining,
                quota_limit_gb=quota_limit / (1024 * 1024 * 1024),
                quota_used_gb=quota_used / (1024 * 1024 * 1024),
                quota_remaining_gb=quota_remaining / (1024 * 1024 * 1024),
                usage_percentage=(quota_used / quota_limit * 100) if quota_limit > 0 else 0,
                reset_date=reset_date
            )
            
        except Exception as e:
            logger.error(f"Failed to get quota info for user {user_id}: {e}")
            # Return default quota info
            return UploadQuotaInfo(
                quota_limit=self.config.upload_session.default_quota_limit_bytes,
                quota_used=0,
                quota_remaining=self.config.upload_session.default_quota_limit_bytes,
                quota_limit_gb=self.config.upload_session.default_quota_limit_gb,
                quota_used_gb=0,
                quota_remaining_gb=self.config.upload_session.default_quota_limit_gb,
                usage_percentage=0,
                reset_date=datetime.now(timezone.utc) + timedelta(days=self.config.upload_session.quota_reset_period_days)
            )
    
    async def _generate_upload_url(self, session_id: UUID, user_id: UUID) -> str:
        """
        Generate upload URL for the session.
        This is a placeholder implementation - would integrate with actual storage.
        """
        # In a real implementation, this would generate a pre-signed URL
        # For now, return a placeholder URL
        base_url = "https://api.secureai.com"  # Would come from config
        return f"{base_url}/v1/dashboard/upload/{session_id}/file"
    
    async def _cleanup_session(self, session_id: UUID, user_id: UUID):
        """Clean up a session from Redis"""
        try:
            session_key = self._generate_session_key(session_id)
            user_sessions_key = self._generate_user_sessions_key(user_id)
            
            async with self.redis.pipeline() as pipe:
                await pipe.delete(session_key)
                await pipe.srem(user_sessions_key, str(session_id))
                await pipe.execute()
                
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")


# Global service instance
upload_session_service = UploadSessionService()
