#!/usr/bin/env python3
"""
Navigation Configuration
Configuration settings for navigation context and prefetching
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NavigationConfig(BaseModel):
    """Navigation-specific configuration"""
    cache_ttl_seconds: int = Field(default=300, ge=60, description="Navigation cache TTL in seconds")
    max_navigation_items: int = Field(default=50, ge=10, description="Maximum navigation items per section")
    enable_breadcrumbs: bool = Field(default=True, description="Enable breadcrumb navigation")
    enable_quick_actions: bool = Field(default=True, description="Enable quick action items")
    enable_recent_navigation: bool = Field(default=True, description="Enable recent navigation tracking")
    enable_suggestions: bool = Field(default=True, description="Enable navigation suggestions")
    max_breadcrumb_depth: int = Field(default=5, ge=1, le=10, description="Maximum breadcrumb depth")
    navigation_analytics_enabled: bool = Field(default=True, description="Enable navigation analytics")
    user_preferences_cache_ttl: int = Field(default=3600, ge=300, description="User preferences cache TTL")


class PrefetchConfig(BaseModel):
    """Prefetch-specific configuration"""
    enabled: bool = Field(default=True, description="Enable prefetching")
    max_concurrent_prefetches: int = Field(default=3, ge=1, le=10, description="Maximum concurrent prefetches")
    prefetch_threshold_ms: int = Field(default=50, ge=0, le=200, description="Response time threshold for triggering prefetch")
    user_pattern_analysis: bool = Field(default=True, description="Enable user pattern analysis")
    global_cache_ttl_seconds: int = Field(default=300, ge=60, description="Global prefetch cache TTL")
    route_mapping_enabled: bool = Field(default=True, description="Enable route-based prefetch mapping")
    analytics_integration: bool = Field(default=True, description="Enable analytics integration for prefetching")
    performance_monitoring: bool = Field(default=True, description="Enable prefetch performance monitoring")


class NavigationServiceConfig(BaseModel):
    """Navigation service configuration"""
    navigation: NavigationConfig = Field(default_factory=NavigationConfig)
    prefetch: PrefetchConfig = Field(default_factory=PrefetchConfig)
    
    # External service configurations
    detection_engine_url: str = Field(default="http://localhost:8001", description="Core Detection Engine URL")
    analytics_service_url: str = Field(default="http://localhost:8002", description="Analytics service URL")
    monitoring_service_url: str = Field(default="http://localhost:8003", description="Monitoring service URL")
    
    # Performance settings
    max_response_time_ms: int = Field(default=100, ge=50, le=500, description="Maximum allowed response time")
    enable_performance_logging: bool = Field(default=True, description="Enable performance logging")
    enable_cache_statistics: bool = Field(default=True, description="Enable cache statistics")
    
    # Security settings
    enable_role_based_filtering: bool = Field(default=True, description="Enable role-based navigation filtering")
    require_authentication_for_preferences: bool = Field(default=True, description="Require authentication for preferences")
    allowed_external_domains: list = Field(default_factory=list, description="Allowed external domains for navigation")
    
    # Development settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    mock_external_services: bool = Field(default=False, description="Use mock external services")


class NavigationConfigManager:
    """Navigation configuration manager"""
    
    def __init__(self):
        self._config: Optional[NavigationServiceConfig] = None
    
    def get_config(self) -> NavigationServiceConfig:
        """Get navigation configuration"""
        if self._config is None:
            self._config = NavigationServiceConfig(
                # Override with environment variables if present
                detection_engine_url=os.getenv("DETECTION_ENGINE_URL", "http://localhost:8001"),
                analytics_service_url=os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8002"),
                monitoring_service_url=os.getenv("MONITORING_SERVICE_URL", "http://localhost:8003"),
                debug_mode=os.getenv("NAVIGATION_DEBUG", "false").lower() == "true",
                mock_external_services=os.getenv("MOCK_EXTERNAL_SERVICES", "false").lower() == "true"
            )
        return self._config
    
    def reload_config(self):
        """Reload configuration from environment"""
        self._config = None
        return self.get_config()


# Global configuration instance
_navigation_config_manager: Optional[NavigationConfigManager] = None


def get_navigation_config() -> NavigationServiceConfig:
    """Get navigation configuration singleton"""
    global _navigation_config_manager
    if _navigation_config_manager is None:
        _navigation_config_manager = NavigationConfigManager()
    return _navigation_config_manager.get_config()


def reload_navigation_config() -> NavigationServiceConfig:
    """Reload navigation configuration"""
    global _navigation_config_manager
    if _navigation_config_manager is None:
        _navigation_config_manager = NavigationConfigManager()
    return _navigation_config_manager.reload_config()
