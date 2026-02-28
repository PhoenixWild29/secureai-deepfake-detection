#!/usr/bin/env python3
"""
User Preferences Service
Business logic for user dashboard preferences management with validation and role-based access control
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
import structlog

from src.models.user_preferences import (
    UserPreferences,
    UserPreferencesHistory,
    DashboardPreferences,
    UserRole,
    CreatePreferencesRequest,
    UpdatePreferencesRequest,
    PreferencesResponse,
    PreferencesSummaryResponse,
    DefaultPreferencesResponse,
    PreferencesValidationResponse,
    get_default_preferences_for_role,
    validate_preferences
)
from src.dependencies.auth import UserClaims

logger = structlog.get_logger(__name__)


class PreferenceService:
    """
    Service for managing user dashboard preferences
    Handles CRUD operations, validation, and role-based customization
    """
    
    def __init__(self):
        """Initialize preference service"""
        logger.info("PreferenceService initialized")
    
    async def create_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        request: CreatePreferencesRequest
    ) -> PreferencesResponse:
        """
        Create new user preferences
        
        Args:
            session: Database session
            user_claims: User authentication claims
            request: Preferences creation request
            
        Returns:
            Created preferences response
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If user preferences already exist
        """
        try:
            user_id = user_claims.user_id
            logger.info("Creating user preferences", user_id=user_id)
            
            # Determine user role
            role = request.role or self._determine_user_role(user_claims)
            
            # Validate preferences
            validation_result = validate_preferences(request.preferences)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid preferences: {', '.join(validation_result.errors)}")
            
            # Check if preferences already exist
            existing_prefs = await self._get_preferences_by_user_id(session, user_id)
            if existing_prefs:
                raise IntegrityError(f"Preferences already exist for user {user_id}")
            
            # Create new preferences
            preferences_record = UserPreferences(
                user_id=user_id,
                preferences_data=request.preferences.dict(),
                role=role,
                version=request.preferences.version,
                is_active=True
            )
            
            session.add(preferences_record)
            await session.commit()
            await session.refresh(preferences_record)
            
            # Create audit history record
            await self._create_history_record(
                session, user_id, request.preferences.dict(), "create", user_id
            )
            
            logger.info("User preferences created successfully", user_id=user_id, role=role)
            
            return PreferencesResponse(
                user_id=user_id,
                preferences=request.preferences,
                role=role,
                version=preferences_record.version,
                created_at=preferences_record.created_at,
                updated_at=preferences_record.updated_at,
                is_active=preferences_record.is_active
            )
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to create user preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def get_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        include_inactive: bool = False
    ) -> Optional[PreferencesResponse]:
        """
        Get user preferences by user ID
        
        Args:
            session: Database session
            user_claims: User authentication claims
            include_inactive: Whether to include inactive preferences
            
        Returns:
            User preferences response or None if not found
        """
        try:
            user_id = user_claims.user_id
            logger.info("Retrieving user preferences", user_id=user_id)
            
            preferences_record = await self._get_preferences_by_user_id(
                session, user_id, include_inactive
            )
            
            if not preferences_record:
                logger.info("No preferences found for user", user_id=user_id)
                return None
            
            # Convert preferences data back to DashboardPreferences object
            preferences = DashboardPreferences(**preferences_record.preferences_data)
            
            logger.info("User preferences retrieved successfully", user_id=user_id)
            
            return PreferencesResponse(
                user_id=user_id,
                preferences=preferences,
                role=preferences_record.role,
                version=preferences_record.version,
                created_at=preferences_record.created_at,
                updated_at=preferences_record.updated_at,
                is_active=preferences_record.is_active
            )
            
        except Exception as e:
            logger.error("Failed to retrieve user preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def update_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        request: UpdatePreferencesRequest
    ) -> PreferencesResponse:
        """
        Update existing user preferences
        
        Args:
            session: Database session
            user_claims: User authentication claims
            request: Preferences update request
            
        Returns:
            Updated preferences response
            
        Raises:
            ValueError: If validation fails or preferences not found
        """
        try:
            user_id = user_claims.user_id
            logger.info("Updating user preferences", user_id=user_id)
            
            # Get existing preferences
            existing_record = await self._get_preferences_by_user_id(session, user_id)
            if not existing_record:
                raise ValueError(f"No preferences found for user {user_id}")
            
            # Merge with existing preferences
            current_preferences = DashboardPreferences(**existing_record.preferences_data)
            
            if request.preferences:
                # Update preferences fields
                updated_data = request.preferences.dict(exclude_unset=True)
                current_data = current_preferences.dict()
                current_data.update(updated_data)
                current_preferences = DashboardPreferences(**current_data)
            
            # Update custom settings if provided
            if request.custom_settings is not None:
                current_preferences.custom_settings.update(request.custom_settings)
            
            # Validate updated preferences
            validation_result = validate_preferences(current_preferences)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid preferences: {', '.join(validation_result.errors)}")
            
            # Update database record
            existing_record.preferences_data = current_preferences.dict()
            existing_record.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(existing_record)
            
            # Create audit history record
            await self._create_history_record(
                session, user_id, current_preferences.dict(), "update", user_id, request.change_reason
            )
            
            logger.info("User preferences updated successfully", user_id=user_id)
            
            return PreferencesResponse(
                user_id=user_id,
                preferences=current_preferences,
                role=existing_record.role,
                version=existing_record.version,
                created_at=existing_record.created_at,
                updated_at=existing_record.updated_at,
                is_active=existing_record.is_active
            )
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to update user preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def delete_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        reason: Optional[str] = None
    ) -> bool:
        """
        Delete user preferences (soft delete by setting is_active to False)
        
        Args:
            session: Database session
            user_claims: User authentication claims
            reason: Reason for deletion
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If preferences not found
        """
        try:
            user_id = user_claims.user_id
            logger.info("Deleting user preferences", user_id=user_id)
            
            # Get existing preferences
            existing_record = await self._get_preferences_by_user_id(session, user_id)
            if not existing_record:
                raise ValueError(f"No preferences found for user {user_id}")
            
            # Soft delete by setting is_active to False
            existing_record.is_active = False
            existing_record.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            # Create audit history record
            await self._create_history_record(
                session, user_id, existing_record.preferences_data, "delete", user_id, reason
            )
            
            logger.info("User preferences deleted successfully", user_id=user_id)
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to delete user preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def get_default_preferences(
        self,
        user_claims: UserClaims
    ) -> DefaultPreferencesResponse:
        """
        Get default preferences for user's role
        
        Args:
            user_claims: User authentication claims
            
        Returns:
            Default preferences response
        """
        try:
            role = self._determine_user_role(user_claims)
            default_preferences = get_default_preferences_for_role(role)
            
            role_descriptions = {
                UserRole.ADMIN: "Full system access with administrative controls and comprehensive monitoring",
                UserRole.SECURITY_OFFICER: "Security-focused layout with real-time alerts and threat monitoring",
                UserRole.COMPLIANCE_MANAGER: "Compliance-oriented dashboard with reporting and audit capabilities",
                UserRole.ANALYST: "Analytical tools and data visualization for deepfake detection analysis",
                UserRole.VIEWER: "Read-only access with basic detection results and system status",
                UserRole.SYSTEM_ADMIN: "System administration tools with performance monitoring and maintenance"
            }
            
            description = role_descriptions.get(role, "Standard dashboard with basic functionality")
            
            logger.info("Default preferences retrieved", user_id=user_claims.user_id, role=role)
            
            return DefaultPreferencesResponse(
                role=role,
                preferences=default_preferences,
                description=description
            )
            
        except Exception as e:
            logger.error("Failed to get default preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def validate_user_preferences(
        self,
        preferences: DashboardPreferences
    ) -> PreferencesValidationResponse:
        """
        Validate user preferences
        
        Args:
            preferences: Preferences to validate
            
        Returns:
            Validation response with errors, warnings, and suggestions
        """
        try:
            logger.info("Validating user preferences")
            
            validation_result = validate_preferences(preferences)
            
            logger.info("Preferences validation completed", 
                       is_valid=validation_result.is_valid,
                       error_count=len(validation_result.errors),
                       warning_count=len(validation_result.warnings))
            
            return validation_result
            
        except Exception as e:
            logger.error("Failed to validate preferences", error=str(e))
            raise
    
    async def get_preferences_summary(
        self,
        session: AsyncSession,
        user_claims: UserClaims
    ) -> PreferencesSummaryResponse:
        """
        Get user preferences summary
        
        Args:
            session: Database session
            user_claims: User authentication claims
            
        Returns:
            Preferences summary response
        """
        try:
            user_id = user_claims.user_id
            logger.info("Getting preferences summary", user_id=user_id)
            
            preferences_record = await self._get_preferences_by_user_id(session, user_id)
            
            if not preferences_record:
                # Return summary for user without preferences
                role = self._determine_user_role(user_claims)
                return PreferencesSummaryResponse(
                    user_id=user_id,
                    has_preferences=False,
                    role=role,
                    last_updated=None,
                    widget_count=0,
                    theme_type="light"  # Default theme
                )
            
            # Extract information from preferences data
            preferences_data = preferences_record.preferences_data
            widget_count = len(preferences_data.get('widgets', []))
            theme_type = preferences_data.get('theme', {}).get('theme_type', 'light')
            
            logger.info("Preferences summary retrieved", user_id=user_id, has_preferences=True)
            
            return PreferencesSummaryResponse(
                user_id=user_id,
                has_preferences=True,
                role=preferences_record.role,
                last_updated=preferences_record.updated_at,
                widget_count=widget_count,
                theme_type=theme_type
            )
            
        except Exception as e:
            logger.error("Failed to get preferences summary", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def get_preferences_history(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user preferences change history
        
        Args:
            session: Database session
            user_claims: User authentication claims
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of history records
        """
        try:
            user_id = user_claims.user_id
            logger.info("Getting preferences history", user_id=user_id, limit=limit, offset=offset)
            
            # Query history records
            stmt = (
                select(UserPreferencesHistory)
                .where(UserPreferencesHistory.user_id == user_id)
                .order_by(UserPreferencesHistory.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await session.execute(stmt)
            history_records = result.scalars().all()
            
            # Convert to dictionary format
            history_list = []
            for record in history_records:
                history_list.append({
                    "id": str(record.id),
                    "action": record.action,
                    "changed_by": record.changed_by,
                    "change_reason": record.change_reason,
                    "version": record.version,
                    "created_at": record.created_at.isoformat(),
                    "widget_count": len(record.preferences_data.get('widgets', [])),
                    "theme_type": record.preferences_data.get('theme', {}).get('theme_type', 'light')
                })
            
            logger.info("Preferences history retrieved", user_id=user_id, count=len(history_list))
            
            return history_list
            
        except Exception as e:
            logger.error("Failed to get preferences history", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def restore_preferences_from_history(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        history_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> PreferencesResponse:
        """
        Restore preferences from history record
        
        Args:
            session: Database session
            user_claims: User authentication claims
            history_id: ID of history record to restore
            reason: Reason for restoration
            
        Returns:
            Restored preferences response
            
        Raises:
            ValueError: If history record not found
        """
        try:
            user_id = user_claims.user_id
            logger.info("Restoring preferences from history", user_id=user_id, history_id=history_id)
            
            # Get history record
            stmt = select(UserPreferencesHistory).where(
                and_(
                    UserPreferencesHistory.id == history_id,
                    UserPreferencesHistory.user_id == user_id
                )
            )
            result = await session.execute(stmt)
            history_record = result.scalar_one_or_none()
            
            if not history_record:
                raise ValueError(f"History record {history_id} not found for user {user_id}")
            
            # Validate restored preferences
            restored_preferences = DashboardPreferences(**history_record.preferences_data)
            validation_result = validate_preferences(restored_preferences)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid restored preferences: {', '.join(validation_result.errors)}")
            
            # Update current preferences
            existing_record = await self._get_preferences_by_user_id(session, user_id)
            if existing_record:
                existing_record.preferences_data = restored_preferences.dict()
                existing_record.updated_at = datetime.now(timezone.utc)
                existing_record.is_active = True
            else:
                # Create new preferences record
                existing_record = UserPreferences(
                    user_id=user_id,
                    preferences_data=restored_preferences.dict(),
                    role=history_record.role if hasattr(history_record, 'role') else self._determine_user_role(user_claims),
                    version=history_record.version,
                    is_active=True
                )
                session.add(existing_record)
            
            await session.commit()
            await session.refresh(existing_record)
            
            # Create audit history record
            await self._create_history_record(
                session, user_id, restored_preferences.dict(), "restore", user_id, reason
            )
            
            logger.info("Preferences restored successfully", user_id=user_id, history_id=history_id)
            
            return PreferencesResponse(
                user_id=user_id,
                preferences=restored_preferences,
                role=existing_record.role,
                version=existing_record.version,
                created_at=existing_record.created_at,
                updated_at=existing_record.updated_at,
                is_active=existing_record.is_active
            )
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to restore preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    # Private helper methods
    
    async def _get_preferences_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
        include_inactive: bool = False
    ) -> Optional[UserPreferences]:
        """Get user preferences by user ID"""
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        
        if not include_inactive:
            stmt = stmt.where(UserPreferences.is_active == True)
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _create_history_record(
        self,
        session: AsyncSession,
        user_id: str,
        preferences_data: Dict[str, Any],
        action: str,
        changed_by: str,
        reason: Optional[str] = None
    ):
        """Create audit history record"""
        history_record = UserPreferencesHistory(
            user_id=user_id,
            preferences_data=preferences_data,
            action=action,
            changed_by=changed_by,
            change_reason=reason,
            version=preferences_data.get('version', '1.0.0')
        )
        
        session.add(history_record)
        await session.commit()
    
    def _determine_user_role(self, user_claims: UserClaims) -> UserRole:
        """Determine user role from claims"""
        # Check roles in order of precedence
        if 'admin' in user_claims.roles:
            return UserRole.ADMIN
        elif 'system_admin' in user_claims.roles:
            return UserRole.SYSTEM_ADMIN
        elif 'security_officer' in user_claims.roles:
            return UserRole.SECURITY_OFFICER
        elif 'compliance_manager' in user_claims.roles:
            return UserRole.COMPLIANCE_MANAGER
        elif 'analyst' in user_claims.roles:
            return UserRole.ANALYST
        else:
            return UserRole.VIEWER


# Global service instance
_preference_service: Optional[PreferenceService] = None


async def get_preference_service() -> PreferenceService:
    """Get global preference service instance"""
    global _preference_service
    
    if _preference_service is None:
        _preference_service = PreferenceService()
    
    return _preference_service
