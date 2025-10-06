#!/usr/bin/env python3
"""
Redis Progress Service
Service for storing and retrieving upload progress data using Redis
"""

import json
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

from src.core.upload_redis_client import get_upload_redis_client
from src.models.upload_progress import (
    UploadProgress,
    ProgressStatus,
    ProgressResponse,
    create_upload_progress
)

logger = logging.getLogger(__name__)


class RedisProgressService:
    """
    Service for managing upload progress data in Redis.
    Extends existing Redis client with progress-specific operations.
    """
    
    def __init__(self):
        """Initialize Redis progress service"""
        self.redis_client = None
        self.progress_prefix = "upload_progress"
        self.progress_ttl = 3600  # 1 hour TTL for progress data
    
    async def initialize(self):
        """Initialize Redis client"""
        try:
            self.redis_client = await get_upload_redis_client()
            logger.info("Redis progress service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis progress service: {e}")
            raise
    
    def _get_progress_key(self, session_id: UUID) -> str:
        """Generate Redis key for progress data"""
        return f"{self.progress_prefix}:{session_id}"
    
    def _get_user_progress_key(self, user_id: UUID) -> str:
        """Generate Redis key for user's active progress sessions"""
        return f"{self.progress_prefix}:user:{user_id}"
    
    async def store_progress(self, progress: UploadProgress) -> bool:
        """
        Store upload progress data in Redis.
        
        Args:
            progress: Upload progress instance to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            progress_key = self._get_progress_key(progress.session_id)
            user_progress_key = self._get_user_progress_key(progress.user_id)
            
            # Convert progress to dictionary for Redis storage
            progress_data = progress.dict()
            
            # Store progress data
            await self.redis_client.redis.hset(progress_key, mapping=progress_data)
            await self.redis_client.redis.expire(progress_key, self.progress_ttl)
            
            # Add to user's active progress sessions
            await self.redis_client.redis.sadd(user_progress_key, str(progress.session_id))
            await self.redis_client.redis.expire(user_progress_key, self.progress_ttl)
            
            logger.debug(f"Stored progress for session {progress.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store progress for session {progress.session_id}: {e}")
            return False
    
    async def get_progress(self, session_id: UUID) -> Optional[UploadProgress]:
        """
        Retrieve upload progress data from Redis.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            Optional[UploadProgress]: Progress data or None if not found
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            progress_key = self._get_progress_key(session_id)
            progress_data = await self.redis_client.redis.hgetall(progress_key)
            
            if not progress_data:
                return None
            
            # Convert Redis data back to UploadProgress
            # Handle type conversions for Redis string values
            converted_data = self._convert_redis_data(progress_data)
            
            return UploadProgress(**converted_data)
            
        except Exception as e:
            logger.error(f"Failed to get progress for session {session_id}: {e}")
            return None
    
    async def update_progress(
        self,
        session_id: UUID,
        bytes_uploaded: int,
        upload_speed: Optional[float] = None,
        status: Optional[ProgressStatus] = None
    ) -> Optional[UploadProgress]:
        """
        Update progress data for a session.
        
        Args:
            session_id: Upload session ID
            bytes_uploaded: Number of bytes uploaded
            upload_speed: Optional upload speed
            status: Optional status update
            
        Returns:
            Optional[UploadProgress]: Updated progress or None if not found
        """
        try:
            # Get existing progress
            progress = await self.get_progress(session_id)
            if not progress:
                return None
            
            # Update progress
            updated_progress = progress.update_progress(
                bytes_uploaded=bytes_uploaded,
                upload_speed=upload_speed,
                status=status
            )
            
            # Store updated progress
            success = await self.store_progress(updated_progress)
            if not success:
                return None
            
            return updated_progress
            
        except Exception as e:
            logger.error(f"Failed to update progress for session {session_id}: {e}")
            return None
    
    async def complete_progress(
        self,
        session_id: UUID,
        video_id: UUID,
        analysis_id: Optional[UUID] = None,
        redirect_url: str = "/dashboard/videos"
    ) -> Optional[UploadProgress]:
        """
        Mark progress as completed with final data.
        
        Args:
            session_id: Upload session ID
            video_id: Video ID after successful upload
            analysis_id: Optional analysis ID
            redirect_url: Redirect URL
            
        Returns:
            Optional[UploadProgress]: Completed progress or None if not found
        """
        try:
            # Get existing progress
            progress = await self.get_progress(session_id)
            if not progress:
                return None
            
            # Update with completion data
            completion_data = {
                'status': ProgressStatus.COMPLETED,
                'percentage': 100.0,
                'video_id': str(video_id),
                'analysis_id': str(analysis_id) if analysis_id else None,
                'redirect_url': redirect_url,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Update progress
            updated_progress = progress.copy(update=completion_data)
            
            # Store updated progress
            success = await self.store_progress(updated_progress)
            if not success:
                return None
            
            return updated_progress
            
        except Exception as e:
            logger.error(f"Failed to complete progress for session {session_id}: {e}")
            return None
    
    async def error_progress(
        self,
        session_id: UUID,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[UploadProgress]:
        """
        Mark progress as failed with error data.
        
        Args:
            session_id: Upload session ID
            error_code: Error code
            error_message: Error message
            error_details: Optional error details
            
        Returns:
            Optional[UploadProgress]: Failed progress or None if not found
        """
        try:
            # Get existing progress
            progress = await self.get_progress(session_id)
            if not progress:
                return None
            
            # Update with error data
            error_data = {
                'status': ProgressStatus.ERROR,
                'error_code': error_code,
                'error_message': error_message,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            if error_details:
                error_data['metadata'] = {**(progress.metadata or {}), 'error_details': error_details}
            
            # Update progress
            updated_progress = progress.copy(update=error_data)
            
            # Store updated progress
            success = await self.store_progress(updated_progress)
            if not success:
                return None
            
            return updated_progress
            
        except Exception as e:
            logger.error(f"Failed to error progress for session {session_id}: {e}")
            return None
    
    async def get_user_progress_sessions(self, user_id: UUID) -> List[UUID]:
        """
        Get all active progress sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[UUID]: List of session IDs
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            user_progress_key = self._get_user_progress_key(user_id)
            session_ids = await self.redis_client.redis.smembers(user_progress_key)
            
            return [UUID(session_id) for session_id in session_ids if session_id]
            
        except Exception as e:
            logger.error(f"Failed to get progress sessions for user {user_id}: {e}")
            return []
    
    async def delete_progress(self, session_id: UUID) -> bool:
        """
        Delete progress data for a session.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            progress_key = self._get_progress_key(session_id)
            
            # Get progress to find user_id for cleanup
            progress = await self.get_progress(session_id)
            if progress:
                user_progress_key = self._get_user_progress_key(progress.user_id)
                await self.redis_client.redis.srem(user_progress_key, str(session_id))
            
            # Delete progress data
            result = await self.redis_client.redis.delete(progress_key)
            
            logger.debug(f"Deleted progress for session {session_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete progress for session {session_id}: {e}")
            return False
    
    async def cleanup_expired_progress(self) -> int:
        """
        Clean up expired progress data.
        
        Returns:
            int: Number of progress records cleaned up
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            pattern = f"{self.progress_prefix}:*"
            keys = await self.redis_client.redis.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                if ":user:" in key:
                    continue  # Skip user session sets
                
                # Check if progress has expired by checking TTL
                ttl = await self.redis_client.redis.ttl(key)
                if ttl == -1:  # No expiry set
                    await self.redis_client.redis.delete(key)
                    cleaned_count += 1
                elif ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired progress records")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired progress: {e}")
            return 0
    
    async def get_progress_stats(self) -> Dict[str, Any]:
        """
        Get progress tracking statistics.
        
        Returns:
            Dict[str, Any]: Progress statistics
        """
        try:
            if not self.redis_client:
                await self.initialize()
            
            pattern = f"{self.progress_prefix}:*"
            keys = await self.redis_client.redis.keys(pattern)
            
            total_progress = 0
            user_sessions = 0
            active_uploads = 0
            
            for key in keys:
                if ":user:" in key:
                    user_sessions += 1
                else:
                    total_progress += 1
                    # Check if it's an active upload
                    progress_data = await self.redis_client.redis.hgetall(key)
                    if progress_data and progress_data.get('status') == 'uploading':
                        active_uploads += 1
            
            return {
                "total_progress_records": total_progress,
                "user_session_sets": user_sessions,
                "active_uploads": active_uploads,
                "progress_prefix": self.progress_prefix,
                "progress_ttl": self.progress_ttl
            }
            
        except Exception as e:
            logger.error(f"Failed to get progress stats: {e}")
            return {"error": str(e)}
    
    def _convert_redis_data(self, redis_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert Redis string data back to appropriate Python types.
        
        Args:
            redis_data: Raw Redis data
            
        Returns:
            Dict[str, Any]: Converted data
        """
        converted = {}
        
        for key, value in redis_data.items():
            if value is None or value == 'None':
                converted[key] = None
            elif key in ['session_id', 'user_id', 'video_id', 'analysis_id']:
                try:
                    converted[key] = UUID(value)
                except ValueError:
                    converted[key] = value
            elif key in ['percentage', 'upload_speed', 'elapsed_time']:
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = 0.0
            elif key in ['bytes_uploaded', 'total_bytes']:
                try:
                    converted[key] = int(value)
                except ValueError:
                    converted[key] = 0
            elif key in ['started_at', 'last_updated', 'completed_at', 'estimated_completion']:
                try:
                    converted[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    converted[key] = value
            elif key == 'status':
                try:
                    converted[key] = ProgressStatus(value)
                except ValueError:
                    converted[key] = ProgressStatus.UPLOADING
            elif key == 'metadata':
                try:
                    converted[key] = json.loads(value) if value else None
                except json.JSONDecodeError:
                    converted[key] = None
            else:
                converted[key] = value
        
        return converted


# Global service instance
_redis_progress_service: Optional[RedisProgressService] = None


def get_redis_progress_service() -> RedisProgressService:
    """
    Get or create the global Redis progress service instance.
    
    Returns:
        RedisProgressService instance
    """
    global _redis_progress_service
    
    if _redis_progress_service is None:
        _redis_progress_service = RedisProgressService()
    
    return _redis_progress_service


# Convenience functions
async def store_upload_progress(progress: UploadProgress) -> bool:
    """
    Convenience function to store upload progress.
    
    Args:
        progress: Upload progress instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    service = get_redis_progress_service()
    if not service.redis_client:
        await service.initialize()
    
    return await service.store_progress(progress)


async def get_upload_progress(session_id: UUID) -> Optional[UploadProgress]:
    """
    Convenience function to get upload progress.
    
    Args:
        session_id: Upload session ID
        
    Returns:
        Optional[UploadProgress]: Progress data or None if not found
    """
    service = get_redis_progress_service()
    if not service.redis_client:
        await service.initialize()
    
    return await service.get_progress(session_id)


async def update_upload_progress(
    session_id: UUID,
    bytes_uploaded: int,
    upload_speed: Optional[float] = None,
    status: Optional[ProgressStatus] = None
) -> Optional[UploadProgress]:
    """
    Convenience function to update upload progress.
    
    Args:
        session_id: Upload session ID
        bytes_uploaded: Number of bytes uploaded
        upload_speed: Optional upload speed
        status: Optional status update
        
    Returns:
        Optional[UploadProgress]: Updated progress or None if not found
    """
    service = get_redis_progress_service()
    if not service.redis_client:
        await service.initialize()
    
    return await service.update_progress(session_id, bytes_uploaded, upload_speed, status)


# Export main service class and convenience functions
__all__ = [
    'RedisProgressService',
    'get_redis_progress_service',
    'store_upload_progress',
    'get_upload_progress',
    'update_upload_progress'
]
