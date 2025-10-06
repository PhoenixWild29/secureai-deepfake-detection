#!/usr/bin/env python3
"""
AWS Cognito User Preferences Integration
Manages user preference storage and retrieval using AWS Cognito user attributes
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CognitoIntegrationError(Exception):
    """Custom exception for Cognito integration errors"""
    pass


@dataclass
class UserPreference:
    """User preference data structure"""
    key: str
    value: Any
    data_type: str
    updated_at: datetime


class UserPreferencesRequest(BaseModel):
    """Request model for updating user preferences"""
    user_id: str = Field(..., description="AWS Cognito user ID")
    preferences: Dict[str, Any] = Field(..., description="Preferences to update")
    replace_all: bool = Field(False, description="Whether to replace all existing preferences")


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences"""
    user_id: str = Field(..., description="AWS Cognito user ID")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    last_updated: datetime = Field(..., description="Last update timestamp")
    preference_count: int = Field(..., description="Number of stored preferences")


class CognitoUserPreferences:
    """
    AWS Cognito user preferences integration
    Manages user preferences using Cognito user attributes
    """
    
    def __init__(
        self,
        user_pool_id: Optional[str] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize Cognito user preferences client
        
        Args:
            user_pool_id: AWS Cognito User Pool ID
            region: AWS region
            aws_access_key_id: AWS access key ID (optional, uses default credentials if not provided)
            aws_secret_access_key: AWS secret access key (optional, uses default credentials if not provided)
        """
        self.user_pool_id = user_pool_id
        self.region = region
        
        # Initialize Cognito client
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.cognito_client = boto3.client(
                    'cognito-idp',
                    region_name=region,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key
                )
            else:
                self.cognito_client = boto3.client(
                    'cognito-idp',
                    region_name=region
                )
            
            logger.info(f"Initialized Cognito client for region: {region}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cognito client: {str(e)}")
            raise CognitoIntegrationError(f"Cognito client initialization failed: {str(e)}")
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences from Cognito user attributes
        
        Args:
            user_id: AWS Cognito user ID
            
        Returns:
            Dictionary containing user preferences
            
        Raises:
            CognitoIntegrationError: If preference retrieval fails
        """
        try:
            logger.debug(f"Fetching preferences for user: {user_id}")
            
            # Get user attributes from Cognito
            response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=user_id
            )
            
            # Extract preferences from custom attributes
            preferences = {}
            for attribute in response.get('UserAttributes', []):
                if attribute['Name'].startswith('custom:dashboard_preference_'):
                    key = attribute['Name'].replace('custom:dashboard_preference_', '')
                    preferences[key] = self._parse_preference_value(attribute['Value'])
            
            # Add default preferences if none exist
            if not preferences:
                preferences = self._get_default_preferences()
            
            logger.info(f"Retrieved {len(preferences)} preferences for user {user_id}")
            return preferences
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotFoundException':
                logger.warning(f"User {user_id} not found, returning default preferences")
                return self._get_default_preferences()
            else:
                logger.error(f"ClientError retrieving preferences for user {user_id}: {str(e)}")
                raise CognitoIntegrationError(f"Failed to retrieve preferences: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error retrieving preferences for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Preference retrieval failed: {str(e)}")
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any],
        replace_all: bool = False
    ) -> UserPreferencesResponse:
        """
        Update user preferences in Cognito user attributes
        
        Args:
            user_id: AWS Cognito user ID
            preferences: Dictionary of preferences to update
            replace_all: Whether to replace all existing preferences
            
        Returns:
            UserPreferencesResponse with updated preferences
            
        Raises:
            CognitoIntegrationError: If preference update fails
        """
        try:
            logger.debug(f"Updating preferences for user: {user_id}")
            
            # Get current preferences if not replacing all
            current_preferences = {}
            if not replace_all:
                current_preferences = await self.get_user_preferences(user_id)
            
            # Merge preferences
            updated_preferences = {**current_preferences, **preferences}
            
            # Prepare user attributes for update
            user_attributes = []
            for key, value in updated_preferences.items():
                attribute_name = f"custom:dashboard_preference_{key}"
                attribute_value = self._serialize_preference_value(value)
                
                user_attributes.append({
                    'Name': attribute_name,
                    'Value': attribute_value
                })
            
            # Update user attributes in Cognito
            self.cognito_client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=user_id,
                UserAttributes=user_attributes
            )
            
            # Create response
            response = UserPreferencesResponse(
                user_id=user_id,
                preferences=updated_preferences,
                last_updated=datetime.now(timezone.utc),
                preference_count=len(updated_preferences)
            )
            
            logger.info(f"Successfully updated {len(preferences)} preferences for user {user_id}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotFoundException':
                logger.error(f"User {user_id} not found")
                raise CognitoIntegrationError(f"User {user_id} not found")
            else:
                logger.error(f"ClientError updating preferences for user {user_id}: {str(e)}")
                raise CognitoIntegrationError(f"Failed to update preferences: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error updating preferences for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Preference update failed: {str(e)}")
    
    async def delete_user_preference(self, user_id: str, preference_key: str) -> bool:
        """
        Delete a specific user preference
        
        Args:
            user_id: AWS Cognito user ID
            preference_key: Key of the preference to delete
            
        Returns:
            True if preference was deleted, False if not found
            
        Raises:
            CognitoIntegrationError: If preference deletion fails
        """
        try:
            logger.debug(f"Deleting preference '{preference_key}' for user: {user_id}")
            
            # Delete the attribute by setting it to empty string
            user_attributes = [{
                'Name': f'custom:dashboard_preference_{preference_key}',
                'Value': ''
            }]
            
            self.cognito_client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=user_id,
                UserAttributes=user_attributes
            )
            
            logger.info(f"Successfully deleted preference '{preference_key}' for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"ClientError deleting preference for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Failed to delete preference: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error deleting preference for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Preference deletion failed: {str(e)}")
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information including preferences
        
        Args:
            user_id: AWS Cognito user ID
            
        Returns:
            Dictionary containing user profile and preferences
            
        Raises:
            CognitoIntegrationError: If profile retrieval fails
        """
        try:
            logger.debug(f"Fetching profile for user: {user_id}")
            
            # Get user details from Cognito
            response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=user_id
            )
            
            # Extract user attributes
            profile = {
                'user_id': user_id,
                'username': response.get('Username', ''),
                'email': '',
                'preferences': {}
            }
            
            for attribute in response.get('UserAttributes', []):
                if attribute['Name'] == 'email':
                    profile['email'] = attribute['Value']
                elif attribute['Name'].startswith('custom:dashboard_preference_'):
                    key = attribute['Name'].replace('custom:dashboard_preference_', '')
                    profile['preferences'][key] = self._parse_preference_value(attribute['Value'])
            
            logger.info(f"Retrieved profile for user {user_id}")
            return profile
            
        except ClientError as e:
            logger.error(f"ClientError retrieving profile for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Failed to retrieve profile: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error retrieving profile for user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"Profile retrieval failed: {str(e)}")
    
    def _parse_preference_value(self, value: str) -> Any:
        """
        Parse preference value from string format
        
        Args:
            value: String value from Cognito attribute
            
        Returns:
            Parsed value (dict, list, bool, int, float, or str)
        """
        if not value:
            return None
        
        try:
            # Try to parse as JSON for complex types
            import json
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Handle primitive types
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            elif value.isdigit():
                return int(value)
            elif value.replace('.', '', 1).isdigit():
                return float(value)
            else:
                return value
    
    def _serialize_preference_value(self, value: Any) -> str:
        """
        Serialize preference value to string format for Cognito
        
        Args:
            value: Value to serialize
            
        Returns:
            String representation suitable for Cognito attributes
        """
        if value is None:
            return ''
        
        # Handle complex types with JSON
        if isinstance(value, (dict, list)):
            import json
            return json.dumps(value)
        
        # Handle primitive types
        return str(value)
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        Get default user preferences
        
        Returns:
            Dictionary containing default preferences
        """
        return {
            'theme': 'light',
            'language': 'en',
            'timezone': 'UTC',
            'notifications_enabled': True,
            'email_notifications': False,
            'dashboard_layout': 'default',
            'auto_refresh_interval': 30,
            'data_privacy_level': 'standard',
            'widgets': {
                'recent_analyses': True,
                'system_status': True,
                'performance_metrics': True,
                'confidence_trends': True
            },
            'date_range': '30d',
            'items_per_page': 20
        }
    
    async def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in Cognito
        
        Args:
            user_id: AWS Cognito user ID
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=user_id
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return False
            else:
                logger.error(f"Error validating user {user_id}: {str(e)}")
                raise CognitoIntegrationError(f"User validation failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error validating user {user_id}: {str(e)}")
            raise CognitoIntegrationError(f"User validation failed: {str(e)}")
    
    async def get_preference_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about user preferences usage
        
        Returns:
            Dictionary containing preference statistics
        """
        try:
            # This would typically involve querying all users and analyzing preferences
            # For now, return basic statistics
            return {
                'total_users': 0,  # Would be calculated from actual data
                'preferences_configured': 0,
                'most_common_theme': 'light',
                'average_preferences_per_user': 0.0,
                'last_updated': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error getting preference statistics: {str(e)}")
            return {
                'error': str(e),
                'last_updated': datetime.now(timezone.utc)
            }
