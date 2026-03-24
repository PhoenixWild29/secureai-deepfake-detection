#!/usr/bin/env python3
"""
Quota Management Service
User quota management functions for retrieval, validation, and updates with database persistence.
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from uuid import UUID

from ..models.upload_models import UserQuota, QuotaValidationResult


class QuotaManagementError(Exception):
    """Custom exception for quota management errors"""
    pass


class QuotaExceededError(QuotaManagementError):
    """Exception raised when quota limit is exceeded"""
    pass


class QuotaService:
    """
    Quota management service for user upload quotas.
    Integrates with existing user management system and provides database persistence.
    """
    
    def __init__(
        self,
        users_file: str = "users.json",
        default_quota_limit: int = 10 * 1024 * 1024 * 1024,  # 10GB default
        quota_reset_period_days: int = 30
    ):
        """
        Initialize quota service.
        
        Args:
            users_file: Path to users JSON file (existing user management)
            default_quota_limit: Default quota limit in bytes (10GB)
            quota_reset_period_days: Quota reset period in days
        """
        self.users_file = users_file
        self.default_quota_limit = default_quota_limit
        self.quota_reset_period_days = quota_reset_period_days
        
        # Ensure users file exists
        self._ensure_users_file_exists()
    
    def _ensure_users_file_exists(self) -> None:
        """Ensure users file exists with proper structure"""
        if not os.path.exists(self.users_file):
            # Create empty users file
            with open(self.users_file, 'w') as f:
                json.dump({}, f, indent=2)
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users from JSON file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict[str, Any]) -> None:
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            raise QuotaManagementError(f"Failed to save users file: {str(e)}")
    
    def _get_user_key(self, user_id: UUID) -> str:
        """Get user key for JSON storage"""
        return str(user_id)
    
    def _initialize_user_quota(self, user_id: UUID) -> UserQuota:
        """Initialize quota for new user"""
        return UserQuota(
            user_id=user_id,
            quota_limit=self.default_quota_limit,
            quota_used=0,
            quota_remaining=self.default_quota_limit
        )
    
    def _update_user_quota_data(self, user_data: Dict[str, Any], quota: UserQuota) -> None:
        """Update user data with quota information"""
        user_data['quota'] = {
            'limit': quota.quota_limit,
            'used': quota.quota_used,
            'remaining': quota.quota_remaining,
            'last_updated': quota.last_updated.isoformat(),
            'reset_date': (quota.last_updated + timedelta(days=self.quota_reset_period_days)).isoformat()
        }
    
    def _parse_user_quota(self, user_data: Dict[str, Any], user_id: UUID) -> UserQuota:
        """Parse quota data from user data"""
        if 'quota' not in user_data:
            return self._initialize_user_quota(user_id)
        
        quota_data = user_data['quota']
        
        # Check if quota needs reset
        if 'reset_date' in quota_data:
            reset_date = datetime.fromisoformat(quota_data['reset_date'])
            if datetime.now(timezone.utc) > reset_date:
                # Reset quota
                return self._initialize_user_quota(user_id)
        
        return UserQuota(
            user_id=user_id,
            quota_limit=quota_data.get('limit', self.default_quota_limit),
            quota_used=quota_data.get('used', 0),
            quota_remaining=quota_data.get('remaining', self.default_quota_limit),
            last_updated=datetime.fromisoformat(quota_data.get('last_updated', datetime.now(timezone.utc).isoformat()))
        )
    
    async def get_user_quota(self, user_id: UUID) -> UserQuota:
        """
        Retrieve user upload quota.
        
        Args:
            user_id: User ID to get quota for
            
        Returns:
            UserQuota object with current quota information
            
        Raises:
            QuotaManagementError: If quota retrieval fails
        """
        try:
            users = self._load_users()
            user_key = self._get_user_key(user_id)
            
            if user_key not in users:
                # Create new user with default quota
                quota = self._initialize_user_quota(user_id)
                users[user_key] = {
                    'id': str(user_id),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                self._update_user_quota_data(users[user_key], quota)
                self._save_users(users)
                return quota
            
            user_data = users[user_key]
            quota = self._parse_user_quota(user_data, user_id)
            
            # Update quota data if it was reset
            if quota.quota_used == 0 and quota.last_updated > datetime.now(timezone.utc) - timedelta(minutes=1):
                self._update_user_quota_data(user_data, quota)
                self._save_users(users)
            
            return quota
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to get user quota: {str(e)}")
    
    async def validate_upload_quota(
        self, 
        user_id: UUID, 
        file_size: int,
        check_multiple_files: bool = False,
        total_files_size: int = 0
    ) -> QuotaValidationResult:
        """
        Validate if user has sufficient quota for upload.
        
        Args:
            user_id: User ID to validate quota for
            file_size: Size of file to upload in bytes
            check_multiple_files: Whether to check for multiple file upload
            total_files_size: Total size of all files if multiple files
            
        Returns:
            QuotaValidationResult with validation status
            
        Raises:
            QuotaManagementError: If quota validation fails
        """
        try:
            quota = await self.get_user_quota(user_id)
            
            # Determine size to check
            size_to_check = total_files_size if check_multiple_files and total_files_size > 0 else file_size
            
            # Check if user has sufficient quota
            if quota.quota_remaining < size_to_check:
                return QuotaValidationResult(
                    is_valid=False,
                    can_upload=False,
                    quota_remaining=quota.quota_remaining,
                    error_message=f"Insufficient quota. Required: {size_to_check} bytes, Available: {quota.quota_remaining} bytes"
                )
            
            # Calculate remaining quota after upload
            new_quota_remaining = quota.quota_remaining - size_to_check
            
            return QuotaValidationResult(
                is_valid=True,
                can_upload=True,
                quota_remaining=new_quota_remaining
            )
            
        except Exception as e:
            return QuotaValidationResult(
                is_valid=False,
                can_upload=False,
                quota_remaining=0,
                error_message=f"Quota validation failed: {str(e)}"
            )
    
    async def update_user_quota(
        self, 
        user_id: UUID, 
        bytes_used: int,
        increment: bool = True
    ) -> UserQuota:
        """
        Update user quota after successful upload.
        
        Args:
            user_id: User ID to update quota for
            bytes_used: Bytes used (positive for increment, negative for decrement)
            increment: Whether to increment (True) or decrement (False) quota
            
        Returns:
            Updated UserQuota object
            
        Raises:
            QuotaManagementError: If quota update fails
            QuotaExceededError: If quota would be exceeded
        """
        try:
            users = self._load_users()
            user_key = self._get_user_key(user_id)
            
            if user_key not in users:
                raise QuotaManagementError(f"User {user_id} not found")
            
            user_data = users[user_key]
            quota = self._parse_user_quota(user_data, user_id)
            
            # Calculate new quota used
            if increment:
                new_quota_used = quota.quota_used + bytes_used
            else:
                new_quota_used = max(0, quota.quota_used - bytes_used)
            
            # Check if quota would be exceeded
            if new_quota_used > quota.quota_limit:
                raise QuotaExceededError(f"Quota update would exceed limit. Current: {quota.quota_used}, Adding: {bytes_used}, Limit: {quota.quota_limit}")
            
            # Update quota
            quota.quota_used = new_quota_used
            quota.quota_remaining = quota.quota_limit - new_quota_used
            quota.last_updated = datetime.now(timezone.utc)
            
            # Save updated quota
            self._update_user_quota_data(user_data, quota)
            self._save_users(users)
            
            return quota
            
        except QuotaExceededError:
            raise
        except Exception as e:
            raise QuotaManagementError(f"Failed to update user quota: {str(e)}")
    
    async def reset_user_quota(self, user_id: UUID, quota_limit: Optional[int] = None) -> UserQuota:
        """
        Reset user quota (admin function).
        
        Args:
            user_id: User ID to reset quota for
            quota_limit: New quota limit (optional, uses default if not provided)
            
        Returns:
            Reset UserQuota object
            
        Raises:
            QuotaManagementError: If quota reset fails
        """
        try:
            users = self._load_users()
            user_key = self._get_user_key(user_id)
            
            if user_key not in users:
                raise QuotaManagementError(f"User {user_id} not found")
            
            user_data = users[user_key]
            
            # Create new quota with optional limit
            if quota_limit is not None:
                quota = UserQuota(
                    user_id=user_id,
                    quota_limit=quota_limit,
                    quota_used=0,
                    quota_remaining=quota_limit
                )
            else:
                quota = self._initialize_user_quota(user_id)
            
            # Save reset quota
            self._update_user_quota_data(user_data, quota)
            self._save_users(users)
            
            return quota
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to reset user quota: {str(e)}")
    
    async def get_user_quota_usage(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get detailed quota usage information for user.
        
        Args:
            user_id: User ID to get usage for
            
        Returns:
            Dictionary with detailed quota usage information
        """
        try:
            quota = await self.get_user_quota(user_id)
            
            usage_percentage = (quota.quota_used / quota.quota_limit) * 100 if quota.quota_limit > 0 else 0
            
            return {
                "user_id": str(user_id),
                "quota_limit": quota.quota_limit,
                "quota_used": quota.quota_used,
                "quota_remaining": quota.quota_remaining,
                "usage_percentage": round(usage_percentage, 2),
                "last_updated": quota.last_updated.isoformat(),
                "reset_date": (quota.last_updated + timedelta(days=self.quota_reset_period_days)).isoformat(),
                "quota_limit_gb": round(quota.quota_limit / (1024**3), 2),
                "quota_used_gb": round(quota.quota_used / (1024**3), 2),
                "quota_remaining_gb": round(quota.quota_remaining / (1024**3), 2)
            }
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to get quota usage: {str(e)}")
    
    async def get_all_user_quotas(self) -> List[Dict[str, Any]]:
        """
        Get quota information for all users (admin function).
        
        Returns:
            List of dictionaries with user quota information
        """
        try:
            users = self._load_users()
            quotas = []
            
            for user_key, user_data in users.items():
                try:
                    user_id = UUID(user_key)
                    quota_usage = await self.get_user_quota_usage(user_id)
                    quotas.append(quota_usage)
                except (ValueError, TypeError):
                    # Skip invalid user entries
                    continue
            
            return quotas
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to get all user quotas: {str(e)}")
    
    async def bulk_update_quotas(self, quota_updates: List[Dict[str, Any]]) -> List[UserQuota]:
        """
        Bulk update quotas for multiple users (admin function).
        
        Args:
            quota_updates: List of dictionaries with user_id and quota_limit
            
        Returns:
            List of updated UserQuota objects
            
        Raises:
            QuotaManagementError: If bulk update fails
        """
        try:
            updated_quotas = []
            
            for update in quota_updates:
                user_id = UUID(update['user_id'])
                quota_limit = update.get('quota_limit')
                
                quota = await self.reset_user_quota(user_id, quota_limit)
                updated_quotas.append(quota)
            
            return updated_quotas
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to bulk update quotas: {str(e)}")
    
    async def cleanup_expired_quotas(self) -> int:
        """
        Clean up expired quotas and reset them (admin function).
        
        Returns:
            Number of quotas reset
        """
        try:
            users = self._load_users()
            reset_count = 0
            
            for user_key, user_data in users.items():
                try:
                    user_id = UUID(user_key)
                    
                    if 'quota' in user_data and 'reset_date' in user_data['quota']:
                        reset_date = datetime.fromisoformat(user_data['quota']['reset_date'])
                        
                        if datetime.now(timezone.utc) > reset_date:
                            await self.reset_user_quota(user_id)
                            reset_count += 1
                            
                except (ValueError, TypeError):
                    # Skip invalid user entries
                    continue
            
            return reset_count
            
        except Exception as e:
            raise QuotaManagementError(f"Failed to cleanup expired quotas: {str(e)}")


# Convenience functions for backward compatibility
async def get_user_quota(user_id: UUID, users_file: str = "users.json") -> UserQuota:
    """
    Retrieve user upload quota (convenience function).
    
    Args:
        user_id: User ID to get quota for
        users_file: Path to users JSON file
        
    Returns:
        UserQuota object with current quota information
    """
    quota_service = QuotaService(users_file=users_file)
    return await quota_service.get_user_quota(user_id)


async def validate_upload_quota(
    user_id: UUID, 
    file_size: int,
    users_file: str = "users.json"
) -> QuotaValidationResult:
    """
    Validate if user has sufficient quota for upload (convenience function).
    
    Args:
        user_id: User ID to validate quota for
        file_size: Size of file to upload in bytes
        users_file: Path to users JSON file
        
    Returns:
        QuotaValidationResult with validation status
    """
    quota_service = QuotaService(users_file=users_file)
    return await quota_service.validate_upload_quota(user_id, file_size)


async def update_user_quota(
    user_id: UUID, 
    bytes_used: int,
    users_file: str = "users.json",
    increment: bool = True
) -> UserQuota:
    """
    Update user quota after successful upload (convenience function).
    
    Args:
        user_id: User ID to update quota for
        bytes_used: Bytes used (positive for increment, negative for decrement)
        users_file: Path to users JSON file
        increment: Whether to increment (True) or decrement (False) quota
        
    Returns:
        Updated UserQuota object
    """
    quota_service = QuotaService(users_file=users_file)
    return await quota_service.update_user_quota(user_id, bytes_used, increment)


async def reset_user_quota(
    user_id: UUID, 
    quota_limit: Optional[int] = None,
    users_file: str = "users.json"
) -> UserQuota:
    """
    Reset user quota (admin function) (convenience function).
    
    Args:
        user_id: User ID to reset quota for
        quota_limit: New quota limit (optional, uses default if not provided)
        users_file: Path to users JSON file
        
    Returns:
        Reset UserQuota object
    """
    quota_service = QuotaService(users_file=users_file)
    return await quota_service.reset_user_quota(user_id, quota_limit)
