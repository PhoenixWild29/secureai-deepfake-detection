#!/usr/bin/env python3
"""
AWS Configuration Module
Configuration management for AWS services including S3, Cognito, and CORS settings
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class S3Config:
    """S3 configuration settings."""
    bucket_name: str
    region: str
    use_presigned_urls: bool = True
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    upload_prefix: str = "uploads"
    results_prefix: str = "results"
    enable_server_side_encryption: bool = True
    encryption_algorithm: str = "AES256"


@dataclass
class CognitoConfig:
    """AWS Cognito configuration settings."""
    user_pool_id: str
    client_id: str
    region: str
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour


@dataclass
class CORSConfig:
    """CORS configuration settings."""
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    allow_credentials: bool = True
    max_age: int = 3600


@dataclass
class AWSConfig:
    """Main AWS configuration container."""
    s3: S3Config
    cognito: CognitoConfig
    cors: CORSConfig
    aws_region: str
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None


class AWSConfigManager:
    """
    AWS configuration manager with environment variable loading and validation.
    """
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config: Optional[AWSConfig] = None
    
    def load_config(self) -> AWSConfig:
        """
        Load AWS configuration from environment variables.
        
        Returns:
            AWSConfig instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        if self._config is not None:
            return self._config
        
        # Load S3 configuration
        s3_config = self._load_s3_config()
        
        # Load Cognito configuration
        cognito_config = self._load_cognito_config()
        
        # Load CORS configuration
        cors_config = self._load_cors_config()
        
        # Load general AWS configuration
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        self._config = AWSConfig(
            s3=s3_config,
            cognito=cognito_config,
            cors=cors_config,
            aws_region=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        return self._config
    
    def _load_s3_config(self) -> S3Config:
        """
        Load S3 configuration from environment variables.
        
        Returns:
            S3Config instance
        """
        bucket_name = os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Validate required S3 configuration
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
        
        use_presigned_urls = os.getenv('S3_USE_PRESIGNED_URLS', 'true').lower() == 'true'
        max_file_size = int(os.getenv('S3_MAX_FILE_SIZE', '524288000'))  # 500MB default
        upload_prefix = os.getenv('S3_UPLOAD_PREFIX', 'uploads')
        results_prefix = os.getenv('S3_RESULTS_PREFIX', 'results')
        enable_encryption = os.getenv('S3_ENABLE_ENCRYPTION', 'true').lower() == 'true'
        encryption_algorithm = os.getenv('S3_ENCRYPTION_ALGORITHM', 'AES256')
        
        return S3Config(
            bucket_name=bucket_name,
            region=region,
            use_presigned_urls=use_presigned_urls,
            max_file_size=max_file_size,
            upload_prefix=upload_prefix,
            results_prefix=results_prefix,
            enable_server_side_encryption=enable_encryption,
            encryption_algorithm=encryption_algorithm
        )
    
    def _load_cognito_config(self) -> CognitoConfig:
        """
        Load Cognito configuration from environment variables.
        
        Returns:
            CognitoConfig instance
        """
        user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Validate required Cognito configuration
        if not user_pool_id:
            raise ValueError("COGNITO_USER_POOL_ID environment variable is required")
        if not client_id:
            raise ValueError("COGNITO_CLIENT_ID environment variable is required")
        
        enable_cache = os.getenv('COGNITO_ENABLE_CACHE', 'true').lower() == 'true'
        cache_ttl = int(os.getenv('COGNITO_CACHE_TTL', '3600'))
        
        return CognitoConfig(
            user_pool_id=user_pool_id,
            client_id=client_id,
            region=region,
            enable_cache=enable_cache,
            cache_ttl=cache_ttl
        )
    
    def _load_cors_config(self) -> CORSConfig:
        """
        Load CORS configuration from environment variables.
        
        Returns:
            CORSConfig instance
        """
        # Parse allowed origins
        allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', '*')
        if allowed_origins_str == '*':
            allowed_origins = ['*']
        else:
            allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]
        
        # Parse allowed methods
        allowed_methods_str = os.getenv('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')
        allowed_methods = [method.strip() for method in allowed_methods_str.split(',')]
        
        # Parse allowed headers
        allowed_headers_str = os.getenv(
            'CORS_ALLOWED_HEADERS',
            'Content-Type,Authorization,X-Requested-With,Accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers'
        )
        allowed_headers = [header.strip() for header in allowed_headers_str.split(',')]
        
        allow_credentials = os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
        max_age = int(os.getenv('CORS_MAX_AGE', '3600'))
        
        return CORSConfig(
            allowed_origins=allowed_origins,
            allowed_methods=allowed_methods,
            allowed_headers=allowed_headers,
            allow_credentials=allow_credentials,
            max_age=max_age
        )
    
    def get_config(self) -> AWSConfig:
        """
        Get the current AWS configuration.
        
        Returns:
            AWSConfig instance
        """
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> AWSConfig:
        """
        Reload configuration from environment variables.
        
        Returns:
            AWSConfig instance
        """
        self._config = None
        return self.load_config()
    
    def validate_config(self) -> Dict[str, List[str]]:
        """
        Validate the current configuration.
        
        Returns:
            Dictionary with validation results (errors and warnings)
        """
        errors = []
        warnings = []
        
        try:
            config = self.get_config()
        except Exception as e:
            errors.append(f"Configuration loading failed: {str(e)}")
            return {'errors': errors, 'warnings': warnings}
        
        # Validate S3 configuration
        if not config.s3.bucket_name:
            errors.append("S3 bucket name is required")
        
        if config.s3.max_file_size <= 0:
            errors.append("S3 max file size must be positive")
        
        if config.s3.max_file_size > 5 * 1024 * 1024 * 1024:  # 5GB
            warnings.append("S3 max file size is very large (>5GB)")
        
        # Validate Cognito configuration
        if not config.cognito.user_pool_id:
            errors.append("Cognito User Pool ID is required")
        
        if not config.cognito.client_id:
            errors.append("Cognito Client ID is required")
        
        if config.cognito.cache_ttl <= 0:
            errors.append("Cognito cache TTL must be positive")
        
        # Validate CORS configuration
        if not config.cors.allowed_origins:
            errors.append("CORS allowed origins cannot be empty")
        
        if '*' in config.cors.allowed_origins and config.cors.allow_credentials:
            warnings.append("CORS allows all origins with credentials - security risk")
        
        if config.cors.max_age <= 0:
            errors.append("CORS max age must be positive")
        
        # Validate AWS credentials
        if not config.aws_access_key_id and not config.aws_secret_access_key:
            warnings.append("AWS credentials not provided - using default credential chain")
        elif config.aws_access_key_id and not config.aws_secret_access_key:
            errors.append("AWS access key ID provided but secret access key is missing")
        elif not config.aws_access_key_id and config.aws_secret_access_key:
            errors.append("AWS secret access key provided but access key ID is missing")
        
        return {'errors': errors, 'warnings': warnings}


# Global configuration manager instance
_config_manager: Optional[AWSConfigManager] = None


def get_aws_config() -> AWSConfig:
    """
    Get the global AWS configuration.
    
    Returns:
        AWSConfig instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = AWSConfigManager()
    
    return _config_manager.get_config()


def get_s3_config() -> S3Config:
    """
    Get S3 configuration.
    
    Returns:
        S3Config instance
    """
    return get_aws_config().s3


def get_cognito_config() -> CognitoConfig:
    """
    Get Cognito configuration.
    
    Returns:
        CognitoConfig instance
    """
    return get_aws_config().cognito


def get_cors_config() -> CORSConfig:
    """
    Get CORS configuration.
    
    Returns:
        CORSConfig instance
    """
    return get_aws_config().cors


def validate_aws_config() -> Dict[str, List[str]]:
    """
    Validate AWS configuration.
    
    Returns:
        Dictionary with validation results
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = AWSConfigManager()
    
    return _config_manager.validate_config()


def reload_aws_config() -> AWSConfig:
    """
    Reload AWS configuration from environment variables.
    
    Returns:
        AWSConfig instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = AWSConfigManager()
    
    return _config_manager.reload_config()


# Configuration validation helper
def check_required_env_vars() -> List[str]:
    """
    Check for required environment variables.
    
    Returns:
        List of missing environment variables
    """
    required_vars = [
        'S3_BUCKET_NAME',
        'COGNITO_USER_POOL_ID',
        'COGNITO_CLIENT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars


# Export main components
__all__ = [
    'S3Config',
    'CognitoConfig',
    'CORSConfig',
    'AWSConfig',
    'AWSConfigManager',
    'get_aws_config',
    'get_s3_config',
    'get_cognito_config',
    'get_cors_config',
    'validate_aws_config',
    'reload_aws_config',
    'check_required_env_vars'
]
