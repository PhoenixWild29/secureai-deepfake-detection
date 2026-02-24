#!/usr/bin/env python3
"""
Analytics Data Models
Pydantic models for dashboard analytics API endpoint data structures
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel, Field, validator
import uuid


class DateRangeType(str, Enum):
    """Date range filter types"""
    CUSTOM = "custom"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


class AnalyticsFilterType(str, Enum):
    """Analytics filter types"""
    USER_GROUP = "user_group"
    ANALYSIS_TYPE = "analysis_type"
    CONFIDENCE_LEVEL = "confidence_level"
    DETECTION_RESULT = "detection_result"
    MODEL_VERSION = "model_version"
    PROCESSING_TIME = "processing_time"


class ExportFormat(str, Enum):
    """Export format options"""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"


class DataClassification(str, Enum):
    """Data classification levels for privacy compliance"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class TrendDirection(str, Enum):
    """Trend direction indicators"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnalyticsDateRange(BaseModel):
    """Date range specification for analytics queries"""
    type: DateRangeType = Field(..., description="Type of date range")
    start_date: Optional[datetime] = Field(None, description="Start date for custom range")
    end_date: Optional[datetime] = Field(None, description="End date for custom range")
    
    @validator('start_date', 'end_date')
    def validate_dates(cls, v, values):
        if v is not None:
            # Ensure dates are timezone-aware
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        start_date = values.get('start_date')
        if start_date and v and v < start_date:
            raise ValueError("End date must be after start date")
        return v


class AnalyticsFilter(BaseModel):
    """Analytics filter specification"""
    type: AnalyticsFilterType = Field(..., description="Type of filter")
    value: Union[str, int, float, List[str]] = Field(..., description="Filter value(s)")
    operator: str = Field(default="eq", description="Comparison operator")
    
    @validator('operator')
    def validate_operator(cls, v):
        allowed_operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in', 'contains', 'starts_with']
        if v not in allowed_operators:
            raise ValueError(f"Operator must be one of: {allowed_operators}")
        return v


class AnalyticsRequest(BaseModel):
    """Analytics API request parameters"""
    date_range: AnalyticsDateRange = Field(..., description="Date range for analytics data")
    filters: List[AnalyticsFilter] = Field(default_factory=list, description="Additional filters")
    group_by: List[str] = Field(default_factory=list, description="Grouping fields")
    aggregation_type: str = Field(default="sum", description="Aggregation type (sum, avg, count, max, min)")
    limit: int = Field(default=1000, ge=1, le=10000, description="Maximum number of records")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    include_trends: bool = Field(default=True, description="Include trend analysis")
    include_predictions: bool = Field(default=False, description="Include predictive analytics")
    export_format: Optional[ExportFormat] = Field(None, description="Export format if requesting export")
    
    @validator('group_by')
    def validate_group_by(cls, v):
        allowed_fields = [
            'user_id', 'analysis_type', 'model_version', 'date', 'hour', 'day', 'week', 'month',
            'confidence_level', 'detection_result', 'processing_time_bucket'
        ]
        for field in v:
            if field not in allowed_fields:
                raise ValueError(f"Group by field '{field}' not allowed. Allowed: {allowed_fields}")
        return v


class DetectionPerformanceMetric(BaseModel):
    """Detection performance metric"""
    metric_name: str = Field(..., description="Name of the metric")
    value: Decimal = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(..., description="Timestamp of the metric")
    confidence_interval: Optional[Dict[str, Decimal]] = Field(None, description="Confidence interval")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('value')
    def validate_value(cls, v):
        return round(float(v), 4)


class UserEngagementMetric(BaseModel):
    """User engagement metric"""
    user_id: str = Field(..., description="User identifier")
    metric_name: str = Field(..., description="Name of the engagement metric")
    value: Decimal = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Timestamp of the metric")
    session_id: Optional[str] = Field(None, description="Session identifier")
    feature_used: Optional[str] = Field(None, description="Feature that was used")
    duration_seconds: Optional[int] = Field(None, description="Duration of engagement")
    
    @validator('value')
    def validate_value(cls, v):
        return round(float(v), 4)


class SystemUtilizationMetric(BaseModel):
    """System utilization metric"""
    resource_type: str = Field(..., description="Type of resource (cpu, memory, gpu, disk)")
    metric_name: str = Field(..., description="Name of the utilization metric")
    value: Decimal = Field(..., description="Utilization value (0-100)")
    unit: str = Field(default="percent", description="Unit of measurement")
    timestamp: datetime = Field(..., description="Timestamp of the metric")
    node_id: Optional[str] = Field(None, description="Node identifier for distributed systems")
    threshold_warning: Optional[Decimal] = Field(None, description="Warning threshold")
    threshold_critical: Optional[Decimal] = Field(None, description="Critical threshold")
    
    @validator('value')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Utilization value must be between 0 and 100")
        return round(float(v), 2)


class TrendAnalysis(BaseModel):
    """Trend analysis result"""
    metric_name: str = Field(..., description="Name of the metric being analyzed")
    trend_direction: TrendDirection = Field(..., description="Direction of the trend")
    change_percentage: Decimal = Field(..., description="Percentage change over period")
    period_start: datetime = Field(..., description="Start of analysis period")
    period_end: datetime = Field(..., description="End of analysis period")
    data_points: List[Decimal] = Field(..., description="Data points for trend calculation")
    correlation_coefficient: Optional[Decimal] = Field(None, description="Correlation coefficient")
    significance_level: Optional[Decimal] = Field(None, description="Statistical significance level")
    
    @validator('change_percentage')
    def validate_percentage(cls, v):
        return round(float(v), 2)


class PredictiveAnalytics(BaseModel):
    """Predictive analytics result"""
    metric_name: str = Field(..., description="Name of the predicted metric")
    predicted_value: Decimal = Field(..., description="Predicted value")
    confidence_score: Decimal = Field(..., description="Confidence in prediction (0-1)")
    prediction_date: datetime = Field(..., description="Date for which prediction is made")
    model_used: str = Field(..., description="Model used for prediction")
    historical_accuracy: Decimal = Field(..., description="Historical accuracy of model")
    prediction_interval: Dict[str, Decimal] = Field(..., description="Prediction confidence interval")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return round(float(v), 4)


class AnalyticsInsight(BaseModel):
    """Analytics insight or recommendation"""
    insight_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique insight identifier")
    title: str = Field(..., description="Title of the insight")
    description: str = Field(..., description="Detailed description of the insight")
    insight_type: str = Field(..., description="Type of insight (performance, trend, anomaly, recommendation)")
    severity: str = Field(default="info", description="Severity level (info, warning, critical)")
    affected_metrics: List[str] = Field(..., description="Metrics affected by this insight")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    confidence: Decimal = Field(..., description="Confidence in the insight (0-1)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Insight creation timestamp")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Confidence must be between 0 and 1")
        return round(float(v), 4)


class AnalyticsExportRequest(BaseModel):
    """Analytics export request"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    export_format: ExportFormat = Field(..., description="Format for export")
    data_classification: DataClassification = Field(..., description="Classification level of data")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    compression: bool = Field(default=False, description="Compress exported file")
    password_protected: bool = Field(default=False, description="Password protect sensitive exports")
    expiration_hours: int = Field(default=24, ge=1, le=168, description="Export link expiration in hours")
    recipient_email: Optional[str] = Field(None, description="Email for export delivery")
    
    @validator('recipient_email')
    def validate_email(cls, v):
        if v is not None:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError("Invalid email format")
        return v


class AnalyticsExportResult(BaseModel):
    """Analytics export result"""
    export_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique export identifier")
    request_id: str = Field(..., description="Original request identifier")
    export_format: ExportFormat = Field(..., description="Export format")
    file_size_bytes: int = Field(..., description="Size of exported file in bytes")
    download_url: str = Field(..., description="URL for downloading the export")
    expires_at: datetime = Field(..., description="Export expiration timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Export creation timestamp")
    status: str = Field(default="completed", description="Export status")
    checksum: Optional[str] = Field(None, description="File integrity checksum")
    record_count: int = Field(..., description="Number of records exported")
    
    @validator('download_url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Download URL must be a valid HTTP/HTTPS URL")
        return v


class AnalyticsResponse(BaseModel):
    """Analytics API response"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    
    # Core analytics data
    detection_performance: List[DetectionPerformanceMetric] = Field(..., description="Detection performance metrics")
    user_engagement: List[UserEngagementMetric] = Field(..., description="User engagement metrics")
    system_utilization: List[SystemUtilizationMetric] = Field(..., description="System utilization metrics")
    
    # Analysis results
    trends: List[TrendAnalysis] = Field(default_factory=list, description="Trend analysis results")
    predictions: List[PredictiveAnalytics] = Field(default_factory=list, description="Predictive analytics results")
    insights: List[AnalyticsInsight] = Field(default_factory=list, description="Analytics insights and recommendations")
    
    # Metadata
    total_records: int = Field(..., description="Total number of records returned")
    date_range: AnalyticsDateRange = Field(..., description="Date range used for query")
    filters_applied: List[AnalyticsFilter] = Field(..., description="Filters applied to query")
    data_classification: DataClassification = Field(..., description="Classification of returned data")
    
    # Export information
    export_available: bool = Field(default=False, description="Whether export is available")
    export_formats: List[ExportFormat] = Field(default_factory=list, description="Available export formats")
    export_request: Optional[AnalyticsExportRequest] = Field(None, description="Export request details")
    
    # Performance metrics
    query_execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether data came from cache")
    data_freshness_minutes: int = Field(..., description="Age of data in minutes")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
        schema_extra = {
            "example": {
                "request_id": "req_123",
                "timestamp": "2024-01-15T10:30:00Z",
                "detection_performance": [
                    {
                        "metric_name": "accuracy_rate",
                        "value": 94.5,
                        "unit": "percent",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "confidence_interval": {"lower": 93.2, "upper": 95.8},
                        "metadata": {"model_version": "v2.1"}
                    }
                ],
                "user_engagement": [
                    {
                        "user_id": "user_123",
                        "metric_name": "analyses_performed",
                        "value": 25,
                        "timestamp": "2024-01-15T10:00:00Z",
                        "session_id": "session_456",
                        "feature_used": "batch_analysis",
                        "duration_seconds": 180
                    }
                ],
                "system_utilization": [
                    {
                        "resource_type": "cpu",
                        "metric_name": "usage_percentage",
                        "value": 65.2,
                        "unit": "percent",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "node_id": "node_1",
                        "threshold_warning": 80.0,
                        "threshold_critical": 90.0
                    }
                ],
                "trends": [
                    {
                        "metric_name": "accuracy_rate",
                        "trend_direction": "increasing",
                        "change_percentage": 2.3,
                        "period_start": "2024-01-01T00:00:00Z",
                        "period_end": "2024-01-15T10:00:00Z",
                        "data_points": [92.1, 92.5, 93.2, 93.8, 94.5],
                        "correlation_coefficient": 0.87,
                        "significance_level": 0.95
                    }
                ],
                "insights": [
                    {
                        "insight_id": "insight_123",
                        "title": "Performance Improvement Detected",
                        "description": "Detection accuracy has improved by 2.3% over the last 30 days",
                        "insight_type": "performance",
                        "severity": "info",
                        "affected_metrics": ["accuracy_rate", "confidence_score"],
                        "recommended_actions": ["Continue monitoring", "Consider model retraining"],
                        "confidence": 0.95,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total_records": 150,
                "date_range": {
                    "type": "last_30_days",
                    "start_date": "2023-12-16T10:30:00Z",
                    "end_date": "2024-01-15T10:30:00Z"
                },
                "filters_applied": [],
                "data_classification": "internal",
                "export_available": True,
                "export_formats": ["csv", "json", "pdf"],
                "query_execution_time_ms": 245.7,
                "cache_hit": False,
                "data_freshness_minutes": 5
            }
        }


class AnalyticsHealthCheck(BaseModel):
    """Analytics service health check"""
    service_name: str = Field(default="analytics", description="Service name")
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Health check timestamp")
    version: str = Field(default="1.0.0", description="Service version")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Service metrics")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalyticsPermission(BaseModel):
    """Analytics permission specification"""
    user_id: str = Field(..., description="User identifier")
    permission_type: str = Field(..., description="Type of permission")
    resource: str = Field(..., description="Resource being accessed")
    classification_level: DataClassification = Field(..., description="Required classification level")
    granted: bool = Field(..., description="Whether permission is granted")
    granted_by: str = Field(..., description="Who granted the permission")
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When permission was granted")
    expires_at: Optional[datetime] = Field(None, description="Permission expiration")
    
    @validator('permission_type')
    def validate_permission_type(cls, v):
        allowed_types = ['read', 'write', 'export', 'admin']
        if v not in allowed_types:
            raise ValueError(f"Permission type must be one of: {allowed_types}")
        return v
