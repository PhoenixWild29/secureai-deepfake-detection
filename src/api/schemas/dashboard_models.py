#!/usr/bin/env python3
"""
Dashboard API Response Models for Data Integration
Pydantic models for dashboard data formatting and configuration management
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class DashboardWidgetType(str, Enum):
    """Enumeration of supported dashboard widget types"""
    OVERVIEW = "overview"
    ANALYTICS = "analytics"
    RECENT_ACTIVITY = "recent_activity"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_METRICS = "performance_metrics"
    CONFIDENCE_DISTRIBUTION = "confidence_distribution"
    PROCESSING_TRENDS = "processing_trends"
    USER_STATISTICS = "user_statistics"


class NotificationType(str, Enum):
    """Enumeration of notification types for dashboard alerts"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM_UPDATE = "system_update"
    MAINTENANCE = "maintenance"


class ThemeType(str, Enum):
    """Enumeration of supported dashboard themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    HIGH_CONTRAST = "high_contrast"


class DashboardOverviewResponse(BaseModel):
    """
    Response model for dashboard overview data.
    Aggregates data from existing Core Detection Engine tables for dashboard consumption.
    """
    
    # User summary and statistics
    user_summary: Dict[str, Any] = Field(
        ..., 
        description="User account summary including total analyses, success rate, and account metrics"
    )
    
    # Recent analysis results
    recent_analyses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of recent analysis results with key metrics and status information"
    )
    
    # System operational status
    system_status: Dict[str, Any] = Field(
        ..., 
        description="System health status including service availability, performance metrics, and operational status"
    )
    
    # Key performance indicators
    quick_stats: Dict[str, Any] = Field(
        ..., 
        description="Quick statistics and key performance indicators for dashboard widgets"
    )
    
    # User notifications and alerts
    notifications: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="User notifications, alerts, and system messages for dashboard display"
    )
    
    # User dashboard preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User dashboard preferences including layout, theme, and display settings"
    )
    
    # Metadata
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the dashboard data was last updated"
    )
    
    @field_validator('user_summary')
    @classmethod
    def validate_user_summary(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user summary contains required fields"""
        required_fields = ['total_analyses', 'success_rate']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"user_summary missing required field: {field}")
        
        # Validate numeric fields
        if not isinstance(v.get('total_analyses'), int) or v['total_analyses'] < 0:
            raise ValueError("total_analyses must be a non-negative integer")
        
        success_rate = v.get('success_rate')
        if not isinstance(success_rate, (int, float)) or not (0.0 <= success_rate <= 100.0):
            raise ValueError("success_rate must be a number between 0.0 and 100.0")
        
        return v
    
    @field_validator('recent_analyses')
    @classmethod
    def validate_recent_analyses(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate recent analyses structure"""
        for i, analysis in enumerate(v):
            if not isinstance(analysis, dict):
                raise ValueError(f"recent_analyses[{i}] must be a dictionary")
            
            required_fields = ['analysis_id', 'status', 'created_at']
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"recent_analyses[{i}] missing required field: {field}")
            
            # Validate status
            valid_statuses = ['queued', 'processing', 'completed', 'failed']
            if analysis.get('status') not in valid_statuses:
                raise ValueError(f"recent_analyses[{i}] status must be one of: {valid_statuses}")
        
        return v
    
    @field_validator('system_status')
    @classmethod
    def validate_system_status(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system status structure"""
        required_fields = ['overall_status', 'services']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"system_status missing required field: {field}")
        
        # Validate overall status
        valid_statuses = ['healthy', 'degraded', 'down', 'maintenance']
        if v.get('overall_status') not in valid_statuses:
            raise ValueError(f"overall_status must be one of: {valid_statuses}")
        
        # Validate services
        services = v.get('services', {})
        if not isinstance(services, dict):
            raise ValueError("services must be a dictionary")
        
        return v
    
    @field_validator('quick_stats')
    @classmethod
    def validate_quick_stats(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate quick stats structure"""
        required_fields = ['total_detections', 'processing_time_avg', 'accuracy_rate']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"quick_stats missing required field: {field}")
        
        # Validate numeric fields
        if not isinstance(v.get('total_detections'), int) or v['total_detections'] < 0:
            raise ValueError("total_detections must be a non-negative integer")
        
        processing_time = v.get('processing_time_avg')
        if not isinstance(processing_time, (int, float)) or processing_time < 0:
            raise ValueError("processing_time_avg must be a non-negative number")
        
        accuracy = v.get('accuracy_rate')
        if not isinstance(accuracy, (int, float)) or not (0.0 <= accuracy <= 100.0):
            raise ValueError("accuracy_rate must be a number between 0.0 and 100.0")
        
        return v
    
    @field_validator('notifications')
    @classmethod
    def validate_notifications(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate notifications structure"""
        for i, notification in enumerate(v):
            if not isinstance(notification, dict):
                raise ValueError(f"notifications[{i}] must be a dictionary")
            
            required_fields = ['id', 'type', 'message', 'timestamp']
            for field in required_fields:
                if field not in notification:
                    raise ValueError(f"notifications[{i}] missing required field: {field}")
            
            # Validate notification type
            valid_types = [nt.value for nt in NotificationType]
            if notification.get('type') not in valid_types:
                raise ValueError(f"notifications[{i}] type must be one of: {valid_types}")
        
        return v
    
    def get_total_notifications(self) -> int:
        """Get total number of notifications"""
        return len(self.notifications)
    
    def get_unread_notifications(self) -> int:
        """Get number of unread notifications"""
        return len([n for n in self.notifications if not n.get('read', False)])
    
    def get_recent_analyses_count(self) -> int:
        """Get count of recent analyses"""
        return len(self.recent_analyses)
    
    def is_system_healthy(self) -> bool:
        """Check if system is in healthy state"""
        return self.system_status.get('overall_status') == 'healthy'


class DashboardAnalyticsResponse(BaseModel):
    """
    Response model for dashboard analytics data.
    Leverages Data Layer analytics patterns for comprehensive dashboard insights.
    """
    
    # Performance trends and historical data
    performance_trends: Dict[str, Any] = Field(
        ..., 
        description="Performance trends including processing times, accuracy rates, and system metrics over time"
    )
    
    # Usage statistics and patterns
    usage_metrics: Dict[str, Any] = Field(
        ..., 
        description="Usage statistics including user activity, analysis frequency, and feature utilization"
    )
    
    # Confidence score distribution analysis
    confidence_distribution: Dict[str, Any] = Field(
        ..., 
        description="Confidence score distribution analysis with statistical metrics and visualization data"
    )
    
    # Processing performance metrics
    processing_metrics: Dict[str, Any] = Field(
        ..., 
        description="Processing performance metrics including throughput, latency, and resource utilization"
    )
    
    # Available export formats
    export_options: List[str] = Field(
        default_factory=lambda: ["pdf", "json", "csv", "xlsx"],
        description="Available export formats for analytics data"
    )
    
    # Metadata
    analytics_period: str = Field(
        default="30d",
        description="Time period covered by the analytics data"
    )
    
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when analytics data was generated"
    )
    
    @field_validator('performance_trends')
    @classmethod
    def validate_performance_trends(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance trends structure"""
        required_fields = ['processing_time_trend', 'accuracy_trend']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"performance_trends missing required field: {field}")
        
        # Validate trend data structure
        for trend_name, trend_data in v.items():
            if isinstance(trend_data, dict) and 'data_points' in trend_data:
                data_points = trend_data['data_points']
                if not isinstance(data_points, list):
                    raise ValueError(f"{trend_name} data_points must be a list")
                
                for i, point in enumerate(data_points):
                    if not isinstance(point, dict) or 'timestamp' not in point or 'value' not in point:
                        raise ValueError(f"{trend_name} data_points[{i}] must have timestamp and value")
        
        return v
    
    @field_validator('usage_metrics')
    @classmethod
    def validate_usage_metrics(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate usage metrics structure"""
        required_fields = ['total_users', 'active_users', 'analyses_count']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"usage_metrics missing required field: {field}")
        
        # Validate numeric fields
        for field in ['total_users', 'active_users', 'analyses_count']:
            value = v.get(field)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        
        return v
    
    @field_validator('confidence_distribution')
    @classmethod
    def validate_confidence_distribution(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate confidence distribution structure"""
        required_fields = ['bins', 'statistics']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"confidence_distribution missing required field: {field}")
        
        # Validate bins structure
        bins = v.get('bins', {})
        if not isinstance(bins, dict):
            raise ValueError("confidence_distribution bins must be a dictionary")
        
        # Validate statistics
        stats = v.get('statistics', {})
        if not isinstance(stats, dict):
            raise ValueError("confidence_distribution statistics must be a dictionary")
        
        required_stats = ['mean', 'median', 'std_dev']
        for stat in required_stats:
            if stat in stats:
                value = stats[stat]
                if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
                    raise ValueError(f"confidence_distribution statistics.{stat} must be between 0.0 and 1.0")
        
        return v
    
    @field_validator('processing_metrics')
    @classmethod
    def validate_processing_metrics(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate processing metrics structure"""
        required_fields = ['average_processing_time', 'throughput', 'success_rate']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"processing_metrics missing required field: {field}")
        
        # Validate numeric fields
        avg_time = v.get('average_processing_time')
        if not isinstance(avg_time, (int, float)) or avg_time < 0:
            raise ValueError("average_processing_time must be a non-negative number")
        
        throughput = v.get('throughput')
        if not isinstance(throughput, (int, float)) or throughput < 0:
            raise ValueError("throughput must be a non-negative number")
        
        success_rate = v.get('success_rate')
        if not isinstance(success_rate, (int, float)) or not (0.0 <= success_rate <= 100.0):
            raise ValueError("success_rate must be a number between 0.0 and 100.0")
        
        return v
    
    @field_validator('export_options')
    @classmethod
    def validate_export_options(cls, v: List[str]) -> List[str]:
        """Validate export options"""
        valid_formats = ['pdf', 'json', 'csv', 'xlsx', 'xml']
        for i, format_name in enumerate(v):
            if format_name not in valid_formats:
                raise ValueError(f"export_options[{i}] must be one of: {valid_formats}")
        return v
    
    @field_validator('analytics_period')
    @classmethod
    def validate_analytics_period(cls, v: str) -> str:
        """Validate analytics period format"""
        valid_periods = ['1d', '7d', '30d', '90d', '1y', 'all']
        if v not in valid_periods:
            raise ValueError(f"analytics_period must be one of: {valid_periods}")
        return v
    
    def get_total_data_points(self) -> int:
        """Get total number of data points across all trends"""
        total = 0
        for trend_data in self.performance_trends.values():
            if isinstance(trend_data, dict) and 'data_points' in trend_data:
                total += len(trend_data['data_points'])
        return total
    
    def get_available_export_formats(self) -> List[str]:
        """Get list of available export formats"""
        return self.export_options.copy()
    
    def get_confidence_statistics(self) -> Dict[str, float]:
        """Get confidence distribution statistics"""
        return self.confidence_distribution.get('statistics', {})
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of key performance metrics"""
        return {
            'average_processing_time': self.processing_metrics.get('average_processing_time', 0),
            'throughput': self.processing_metrics.get('throughput', 0),
            'success_rate': self.processing_metrics.get('success_rate', 0),
            'total_users': self.usage_metrics.get('total_users', 0),
            'active_users': self.usage_metrics.get('active_users', 0)
        }


class UserPreferencesRequest(BaseModel):
    """
    Request model for user dashboard preferences and configuration.
    Manages layout, notifications, theme, and analytics filtering preferences.
    """
    
    # Dashboard layout configuration
    layout_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dashboard layout configuration including widget positions, sizes, and visibility"
    )
    
    # Notification settings and preferences
    notification_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Notification preferences including types, frequency, and delivery methods"
    )
    
    # UI theme and appearance settings
    theme_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="UI theme preferences including color scheme, font size, and accessibility options"
    )
    
    # Analytics filtering preferences
    analytics_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analytics filtering preferences including date ranges, metrics, and visualization options"
    )
    
    # Additional metadata
    user_id: Optional[UUID] = Field(
        default=None,
        description="User ID for preference association"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when preferences were last updated"
    )
    
    @field_validator('layout_config')
    @classmethod
    def validate_layout_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate layout configuration structure"""
        if not isinstance(v, dict):
            raise ValueError("layout_config must be a dictionary")
        
        # Validate widget configurations if present
        if 'widgets' in v:
            widgets = v['widgets']
            if not isinstance(widgets, list):
                raise ValueError("layout_config.widgets must be a list")
            
            for i, widget in enumerate(widgets):
                if not isinstance(widget, dict):
                    raise ValueError(f"layout_config.widgets[{i}] must be a dictionary")
                
                required_widget_fields = ['type', 'position']
                for field in required_widget_fields:
                    if field not in widget:
                        raise ValueError(f"layout_config.widgets[{i}] missing required field: {field}")
                
                # Validate widget type
                valid_types = [wt.value for wt in DashboardWidgetType]
                if widget.get('type') not in valid_types:
                    raise ValueError(f"layout_config.widgets[{i}] type must be one of: {valid_types}")
                
                # Validate position
                position = widget.get('position')
                if not isinstance(position, dict) or 'x' not in position or 'y' not in position:
                    raise ValueError(f"layout_config.widgets[{i}] position must have x and y coordinates")
        
        return v
    
    @field_validator('notification_settings')
    @classmethod
    def validate_notification_settings(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate notification settings structure"""
        if not isinstance(v, dict):
            raise ValueError("notification_settings must be a dictionary")
        
        # Validate notification types if present
        if 'enabled_types' in v:
            enabled_types = v['enabled_types']
            if not isinstance(enabled_types, list):
                raise ValueError("notification_settings.enabled_types must be a list")
            
            valid_types = [nt.value for nt in NotificationType]
            for i, notification_type in enumerate(enabled_types):
                if notification_type not in valid_types:
                    raise ValueError(f"notification_settings.enabled_types[{i}] must be one of: {valid_types}")
        
        # Validate frequency settings
        if 'frequency' in v:
            frequency = v['frequency']
            valid_frequencies = ['immediate', 'hourly', 'daily', 'weekly', 'disabled']
            if frequency not in valid_frequencies:
                raise ValueError(f"notification_settings.frequency must be one of: {valid_frequencies}")
        
        return v
    
    @field_validator('theme_preferences')
    @classmethod
    def validate_theme_preferences(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate theme preferences structure"""
        if not isinstance(v, dict):
            raise ValueError("theme_preferences must be a dictionary")
        
        # Validate theme type if present
        if 'theme' in v:
            theme = v['theme']
            valid_themes = [tt.value for tt in ThemeType]
            if theme not in valid_themes:
                raise ValueError(f"theme_preferences.theme must be one of: {valid_themes}")
        
        # Validate font size if present
        if 'font_size' in v:
            font_size = v['font_size']
            if not isinstance(font_size, (int, float)) or not (10 <= font_size <= 24):
                raise ValueError("theme_preferences.font_size must be between 10 and 24")
        
        # Validate color scheme if present
        if 'color_scheme' in v:
            color_scheme = v['color_scheme']
            valid_schemes = ['default', 'high_contrast', 'colorblind_friendly', 'dark_mode']
            if color_scheme not in valid_schemes:
                raise ValueError(f"theme_preferences.color_scheme must be one of: {valid_schemes}")
        
        return v
    
    @field_validator('analytics_filters')
    @classmethod
    def validate_analytics_filters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analytics filters structure"""
        if not isinstance(v, dict):
            raise ValueError("analytics_filters must be a dictionary")
        
        # Validate date range if present
        if 'date_range' in v:
            date_range = v['date_range']
            if not isinstance(date_range, dict):
                raise ValueError("analytics_filters.date_range must be a dictionary")
            
            valid_periods = ['1d', '7d', '30d', '90d', '1y', 'custom']
            if 'period' in date_range and date_range['period'] not in valid_periods:
                raise ValueError(f"analytics_filters.date_range.period must be one of: {valid_periods}")
        
        # Validate metrics selection if present
        if 'selected_metrics' in v:
            selected_metrics = v['selected_metrics']
            if not isinstance(selected_metrics, list):
                raise ValueError("analytics_filters.selected_metrics must be a list")
            
            valid_metrics = ['processing_time', 'accuracy', 'throughput', 'confidence', 'user_activity']
            for i, metric in enumerate(selected_metrics):
                if metric not in valid_metrics:
                    raise ValueError(f"analytics_filters.selected_metrics[{i}] must be one of: {valid_metrics}")
        
        return v
    
    @model_validator(mode='after')
    def validate_preferences_consistency(self) -> 'UserPreferencesRequest':
        """Validate overall preferences consistency"""
        # Check for conflicting settings
        if 'theme' in self.theme_preferences and 'color_scheme' in self.theme_preferences:
            theme = self.theme_preferences['theme']
            color_scheme = self.theme_preferences['color_scheme']
            
            if theme == 'dark' and color_scheme == 'default':
                # This is valid, but we could add a warning
                pass
        
        return self
    
    def get_enabled_notification_types(self) -> List[str]:
        """Get list of enabled notification types"""
        return self.notification_settings.get('enabled_types', [])
    
    def get_selected_widgets(self) -> List[Dict[str, Any]]:
        """Get list of selected dashboard widgets"""
        return self.layout_config.get('widgets', [])
    
    def get_theme_settings(self) -> Dict[str, Any]:
        """Get current theme settings"""
        return {
            'theme': self.theme_preferences.get('theme', 'light'),
            'font_size': self.theme_preferences.get('font_size', 14),
            'color_scheme': self.theme_preferences.get('color_scheme', 'default')
        }
    
    def get_analytics_date_range(self) -> str:
        """Get selected analytics date range"""
        return self.analytics_filters.get('date_range', {}).get('period', '30d')
    
    def is_notification_enabled(self, notification_type: str) -> bool:
        """Check if specific notification type is enabled"""
        enabled_types = self.get_enabled_notification_types()
        return notification_type in enabled_types
    
    def has_widget(self, widget_type: str) -> bool:
        """Check if specific widget type is included in layout"""
        widgets = self.get_selected_widgets()
        return any(widget.get('type') == widget_type for widget in widgets)


class DashboardConfigurationResponse(BaseModel):
    """
    Response model for dashboard configuration data.
    Provides configuration options and current settings for dashboard customization.
    """
    
    # Available widget types
    available_widgets: List[Dict[str, Any]] = Field(
        ..., 
        description="List of available dashboard widgets with configuration options"
    )
    
    # Default layout configuration
    default_layout: Dict[str, Any] = Field(
        ..., 
        description="Default dashboard layout configuration"
    )
    
    # Theme options
    theme_options: List[Dict[str, Any]] = Field(
        ..., 
        description="Available theme options and customization settings"
    )
    
    # Notification configuration options
    notification_options: Dict[str, Any] = Field(
        ..., 
        description="Available notification types and configuration options"
    )
    
    # Analytics filter options
    analytics_options: Dict[str, Any] = Field(
        ..., 
        description="Available analytics filters and configuration options"
    )
    
    # Metadata
    configuration_version: str = Field(
        default="1.0",
        description="Version of the dashboard configuration"
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when configuration was last updated"
    )
    
    @field_validator('available_widgets')
    @classmethod
    def validate_available_widgets(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate available widgets structure"""
        for i, widget in enumerate(v):
            if not isinstance(widget, dict):
                raise ValueError(f"available_widgets[{i}] must be a dictionary")
            
            required_fields = ['type', 'name', 'description']
            for field in required_fields:
                if field not in widget:
                    raise ValueError(f"available_widgets[{i}] missing required field: {field}")
            
            # Validate widget type
            valid_types = [wt.value for wt in DashboardWidgetType]
            if widget.get('type') not in valid_types:
                raise ValueError(f"available_widgets[{i}] type must be one of: {valid_types}")
        
        return v
    
    def get_widget_by_type(self, widget_type: str) -> Optional[Dict[str, Any]]:
        """Get widget configuration by type"""
        for widget in self.available_widgets:
            if widget.get('type') == widget_type:
                return widget
        return None
    
    def get_available_widget_types(self) -> List[str]:
        """Get list of available widget types"""
        return [widget.get('type') for widget in self.available_widgets if widget.get('type') is not None]
    
    def get_theme_by_name(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Get theme configuration by name"""
        for theme in self.theme_options:
            if theme.get('name') == theme_name:
                return theme
        return None
