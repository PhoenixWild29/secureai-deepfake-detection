#!/usr/bin/env python3
"""
Dashboard Configuration Management
Configuration settings for dashboard API, Redis, and external services
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger(__name__)


class RedisConfig(BaseSettings):
    """Redis configuration settings"""
    
    # Connection settings
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Connection pool settings
    max_connections: int = Field(default=20, description="Maximum Redis connections")
    socket_keepalive: bool = Field(default=True, description="Enable socket keepalive")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout in seconds")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # Cache settings
    default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    dashboard_ttl: int = Field(default=60, description="Dashboard cache TTL in seconds")
    user_activity_ttl: int = Field(default=120, description="User activity cache TTL in seconds")
    system_metrics_ttl: int = Field(default=30, description="System metrics cache TTL in seconds")
    blockchain_ttl: int = Field(default=180, description="Blockchain metrics cache TTL in seconds")
    processing_queue_ttl: int = Field(default=15, description="Processing queue cache TTL in seconds")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False


class AWSConfig(BaseSettings):
    """AWS configuration settings"""
    
    # AWS Cognito settings
    cognito_region: str = Field(default="us-east-1", description="AWS Cognito region")
    cognito_user_pool_id: Optional[str] = Field(default=None, description="Cognito User Pool ID")
    cognito_client_id: Optional[str] = Field(default=None, description="Cognito Client ID")
    cognito_client_secret: Optional[str] = Field(default=None, description="Cognito Client Secret")
    
    # JWT settings
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration time in minutes")
    jwt_issuer: str = Field(default="secureai-dashboard", description="JWT issuer")
    
    # AWS credentials
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_session_token: Optional[str] = Field(default=None, description="AWS session token")
    
    class Config:
        env_prefix = "AWS_"
        case_sensitive = False


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    
    # PostgreSQL settings
    database_url: str = Field(default="postgresql://localhost:5432/secureai", description="Database URL")
    database_host: str = Field(default="localhost", description="Database host")
    database_port: int = Field(default=5432, description="Database port")
    database_name: str = Field(default="secureai", description="Database name")
    database_user: str = Field(default="postgres", description="Database user")
    database_password: str = Field(default="password", description="Database password")
    
    # Connection pool settings
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Database pool timeout in seconds")
    database_pool_recycle: int = Field(default=3600, description="Database pool recycle time in seconds")
    
    class Config:
        env_prefix = "DATABASE_"
        case_sensitive = False


class ExternalServicesConfig(BaseSettings):
    """External services configuration"""
    
    # Core Detection Engine
    detection_engine_url: str = Field(default="http://localhost:8001", description="Core Detection Engine URL")
    detection_engine_timeout: int = Field(default=30, description="Detection Engine timeout in seconds")
    detection_engine_retry_attempts: int = Field(default=3, description="Detection Engine retry attempts")
    
    # User Analytics Service
    analytics_service_url: str = Field(default="http://localhost:8002", description="User Analytics Service URL")
    analytics_service_timeout: int = Field(default=15, description="Analytics Service timeout in seconds")
    analytics_service_retry_attempts: int = Field(default=2, description="Analytics Service retry attempts")
    
    # System Performance Monitoring
    monitoring_service_url: str = Field(default="http://localhost:8003", description="System Monitoring Service URL")
    monitoring_service_timeout: int = Field(default=10, description="Monitoring Service timeout in seconds")
    monitoring_service_retry_attempts: int = Field(default=2, description="Monitoring Service retry attempts")
    
    # Blockchain Service
    blockchain_service_url: str = Field(default="http://localhost:8004", description="Blockchain Service URL")
    blockchain_service_timeout: int = Field(default=45, description="Blockchain Service timeout in seconds")
    blockchain_service_retry_attempts: int = Field(default=3, description="Blockchain Service retry attempts")
    
    class Config:
        env_prefix = "EXTERNAL_"
        case_sensitive = False


class DashboardConfig(BaseSettings):
    """Dashboard-specific configuration"""
    
    # API settings
    api_title: str = Field(default="SecureAI Dashboard API", description="API title")
    api_version: str = Field(default="v1", description="API version")
    api_description: str = Field(default="Dashboard overview API with data aggregation", description="API description")
    
    # Performance settings
    max_response_time_ms: int = Field(default=100, description="Maximum response time in milliseconds")
    enable_caching: bool = Field(default=True, description="Enable Redis caching")
    enable_compression: bool = Field(default=True, description="Enable response compression")
    
    # Data aggregation settings
    recent_analyses_limit: int = Field(default=10, description="Default limit for recent analyses")
    confidence_trends_hours: int = Field(default=24, description="Default hours for confidence trends")
    user_activity_limit: int = Field(default=50, description="Default limit for user activity")
    
    # Security settings
    enable_authentication: bool = Field(default=True, description="Enable authentication")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    enable_performance_logging: bool = Field(default=True, description="Enable performance logging")
    
    class Config:
        env_prefix = "DASHBOARD_"
        case_sensitive = False


class DashboardSettings(BaseModel):
    """Complete dashboard settings configuration"""
    
    redis: RedisConfig = Field(default_factory=RedisConfig)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    
    # Environment settings
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    testing: bool = Field(default=False, description="Testing mode")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_environments = ['development', 'staging', 'production', 'testing']
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v
    
    @validator('debug')
    def validate_debug_in_production(cls, v, values):
        environment = values.get('environment', 'development')
        if environment == 'production' and v:
            logger.warning("Debug mode enabled in production environment")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ServiceHealthStatus(BaseModel):
    """Service health status model"""
    
    service_name: str = Field(..., description="Service name")
    is_healthy: bool = Field(..., description="Service health status")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    last_check: str = Field(..., description="Last health check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    version: Optional[str] = Field(None, description="Service version")


class ConfigurationManager:
    """Configuration manager for dashboard settings"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Optional configuration file path
        """
        self.config_file = config_file
        self._settings: Optional[DashboardSettings] = None
        self._service_health: Dict[str, ServiceHealthStatus] = {}
        
        logger.info("ConfigurationManager initialized", config_file=config_file)
    
    def get_settings(self) -> DashboardSettings:
        """
        Get dashboard settings
        
        Returns:
            Dashboard settings instance
        """
        if self._settings is None:
            self._settings = DashboardSettings()
            logger.info("Dashboard settings loaded", environment=self._settings.environment)
        
        return self._settings
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return self.get_settings().redis
    
    def get_aws_config(self) -> AWSConfig:
        """Get AWS configuration"""
        return self.get_settings().aws
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.get_settings().database
    
    def get_external_services_config(self) -> ExternalServicesConfig:
        """Get external services configuration"""
        return self.get_settings().external_services
    
    def get_dashboard_config(self) -> DashboardConfig:
        """Get dashboard configuration"""
        return self.get_settings().dashboard
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.get_settings().environment == "production"
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get_settings().debug
    
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.get_settings().testing
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealthStatus]:
        """Get service health status"""
        return self._service_health.get(service_name)
    
    def set_service_health(self, service_name: str, health_status: ServiceHealthStatus):
        """Set service health status"""
        self._service_health[service_name] = health_status
    
    def get_all_service_health(self) -> Dict[str, ServiceHealthStatus]:
        """Get all service health statuses"""
        return self._service_health.copy()
    
    def validate_configuration(self) -> List[str]:
        """
        Validate configuration settings
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        settings = self.get_settings()
        
        try:
            # Validate Redis configuration
            redis_config = settings.redis
            if not redis_config.redis_host:
                errors.append("Redis host is required")
            if redis_config.redis_port <= 0 or redis_config.redis_port > 65535:
                errors.append("Redis port must be between 1 and 65535")
            
            # Validate database configuration
            db_config = settings.database
            if not db_config.database_host:
                errors.append("Database host is required")
            if db_config.database_port <= 0 or db_config.database_port > 65535:
                errors.append("Database port must be between 1 and 65535")
            
            # Validate AWS configuration in production
            if settings.environment == "production":
                aws_config = settings.aws
                if not aws_config.cognito_user_pool_id:
                    errors.append("Cognito User Pool ID is required in production")
                if not aws_config.cognito_client_id:
                    errors.append("Cognito Client ID is required in production")
            
            # Validate external services configuration
            ext_config = settings.external_services
            required_services = [
                ("detection_engine_url", ext_config.detection_engine_url),
                ("analytics_service_url", ext_config.analytics_service_url),
                ("monitoring_service_url", ext_config.monitoring_service_url),
                ("blockchain_service_url", ext_config.blockchain_service_url)
            ]
            
            for service_name, service_url in required_services:
                if not service_url:
                    errors.append(f"{service_name} is required")
            
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
        
        if errors:
            logger.warning("Configuration validation errors", errors=errors)
        else:
            logger.info("Configuration validation passed")
        
        return errors
    
    def reload_configuration(self):
        """Reload configuration from environment"""
        self._settings = None
        logger.info("Configuration reloaded")
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get environment configuration summary"""
        settings = self.get_settings()
        
        return {
            "environment": settings.environment,
            "debug": settings.debug,
            "testing": settings.testing,
            "redis_url": settings.redis.redis_url,
            "database_url": settings.database.database_url,
            "external_services": {
                "detection_engine": settings.external_services.detection_engine_url,
                "analytics": settings.external_services.analytics_service_url,
                "monitoring": settings.external_services.monitoring_service_url,
                "blockchain": settings.external_services.blockchain_service_url
            },
            "dashboard_config": {
                "max_response_time_ms": settings.dashboard.max_response_time_ms,
                "enable_caching": settings.dashboard.enable_caching,
                "enable_authentication": settings.dashboard.enable_authentication
            }
        }


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager()
        
        # Validate configuration on first load
        errors = _config_manager.validate_configuration()
        if errors:
            logger.warning("Configuration validation errors on startup", errors=errors)
    
    return _config_manager


def get_settings() -> DashboardSettings:
    """Get dashboard settings"""
    return get_config_manager().get_settings()


def get_redis_config() -> RedisConfig:
    """Get Redis configuration"""
    return get_config_manager().get_redis_config()


def get_aws_config() -> AWSConfig:
    """Get AWS configuration"""
    return get_config_manager().get_aws_config()


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config_manager().get_database_config()


def get_external_services_config() -> ExternalServicesConfig:
    """Get external services configuration"""
    return get_config_manager().get_external_services_config()


def get_dashboard_config() -> DashboardConfig:
    """Get dashboard configuration"""
    return get_config_manager().get_dashboard_config()
