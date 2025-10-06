#!/usr/bin/env python3
"""
Dashboard Data Models
Pydantic models for dashboard overview API endpoint data structures
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel, Field, validator

# Import navigation models
from src.models.navigation import (
    NavigationState,
    PrefetchStrategy,
    NavigationAnalytics,
    NavigationPerformanceMetrics
)


class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceTrend(str, Enum):
    """Confidence trend direction"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class ProcessingQueueStatus(str, Enum):
    """Processing queue status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class UserActivityMetric(BaseModel):
    """User activity metric for dashboard"""
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    total_analyses: int = Field(ge=0, description="Total analyses performed")
    recent_analyses: int = Field(ge=0, description="Analyses in last 24 hours")
    is_active: bool = Field(..., description="Whether user is currently active")
    role: Optional[str] = Field(None, description="User role/permissions")


class RecentAnalysisSummary(BaseModel):
    """Recent analysis summary for dashboard"""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    filename: str = Field(..., description="Original video filename")
    user_id: str = Field(..., description="User who initiated analysis")
    status: AnalysisStatus = Field(..., description="Current analysis status")
    confidence_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="Confidence score if completed")
    is_fake: Optional[bool] = Field(None, description="Detection result if completed")
    processing_time_seconds: Optional[float] = Field(None, ge=0, description="Processing time if completed")
    created_at: datetime = Field(..., description="Analysis creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain verification hash if completed")
    
    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        if v is not None:
            return round(float(v), 4)
        return v


class ConfidenceScoreTrend(BaseModel):
    """Confidence score trend data"""
    timestamp: datetime = Field(..., description="Trend data point timestamp")
    average_confidence: Decimal = Field(ge=0.0, le=1.0, description="Average confidence score")
    fake_detection_rate: Decimal = Field(ge=0.0, le=1.0, description="Rate of fake detections")
    total_analyses: int = Field(ge=0, description="Total analyses at this timestamp")
    trend_direction: ConfidenceTrend = Field(..., description="Trend direction")
    
    @validator('average_confidence', 'fake_detection_rate')
    def validate_decimal_precision(cls, v):
        return round(float(v), 4)


class ProcessingQueueMetrics(BaseModel):
    """Processing queue status and metrics"""
    queue_length: int = Field(ge=0, description="Current queue length")
    estimated_wait_time_minutes: float = Field(ge=0, description="Estimated wait time in minutes")
    processing_capacity: int = Field(ge=0, description="Current processing capacity")
    active_processors: int = Field(ge=0, description="Number of active processors")
    status: ProcessingQueueStatus = Field(..., description="Overall queue status")
    last_processed_at: Optional[datetime] = Field(None, description="Last processing completion time")
    throughput_per_hour: float = Field(ge=0, description="Average throughput per hour")
    error_rate: Decimal = Field(ge=0.0, le=1.0, description="Current error rate")
    
    @validator('error_rate')
    def validate_error_rate(cls, v):
        return round(float(v), 4)


class SystemPerformanceMetrics(BaseModel):
    """System performance metrics"""
    cpu_usage_percent: Decimal = Field(ge=0.0, le=100.0, description="CPU usage percentage")
    memory_usage_percent: Decimal = Field(ge=0.0, le=100.0, description="Memory usage percentage")
    disk_usage_percent: Decimal = Field(ge=0.0, le=100.0, description="Disk usage percentage")
    gpu_usage_percent: Optional[Decimal] = Field(None, ge=0.0, le=100.0, description="GPU usage percentage")
    network_latency_ms: float = Field(ge=0, description="Average network latency in milliseconds")
    database_connection_count: int = Field(ge=0, description="Active database connections")
    redis_connection_count: int = Field(ge=0, description="Active Redis connections")
    uptime_hours: float = Field(ge=0, description="System uptime in hours")
    last_restart: Optional[datetime] = Field(None, description="Last system restart timestamp")
    
    @validator('cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent', 'gpu_usage_percent')
    def validate_usage_percent(cls, v):
        if v is not None:
            return round(float(v), 2)
        return v


class BlockchainVerificationMetrics(BaseModel):
    """Blockchain verification metrics"""
    total_verifications: int = Field(ge=0, description="Total blockchain verifications")
    successful_verifications: int = Field(ge=0, description="Successful verifications")
    failed_verifications: int = Field(ge=0, description="Failed verifications")
    pending_verifications: int = Field(ge=0, description="Pending verifications")
    average_verification_time_seconds: float = Field(ge=0, description="Average verification time")
    last_verification_at: Optional[datetime] = Field(None, description="Last verification timestamp")
    blockchain_network_status: str = Field(..., description="Blockchain network status")
    gas_fee_trend: str = Field(..., description="Recent gas fee trend")
    
    @validator('successful_verifications', 'failed_verifications', 'pending_verifications')
    def validate_verification_counts(cls, v, values):
        total = values.get('total_verifications', 0)
        if v > total:
            raise ValueError("Individual verification counts cannot exceed total")
        return v


class DashboardOverviewResponse(BaseModel):
    """Complete dashboard overview response with navigation context"""
    # Recent analysis summaries (last 10)
    recent_analyses: List[RecentAnalysisSummary] = Field(..., description="Recent analysis summaries")
    
    # Confidence score trends (last 24 hours, hourly data points)
    confidence_trends: List[ConfidenceScoreTrend] = Field(..., description="Confidence score trends")
    
    # Processing queue status
    processing_queue: ProcessingQueueMetrics = Field(..., description="Processing queue status")
    
    # User activity metrics (active users)
    user_activity: List[UserActivityMetric] = Field(..., description="User activity metrics")
    
    # System performance metrics
    system_performance: SystemPerformanceMetrics = Field(..., description="System performance metrics")
    
    # Blockchain verification metrics
    blockchain_metrics: BlockchainVerificationMetrics = Field(..., description="Blockchain verification metrics")
    
    # Summary statistics
    summary_stats: Dict[str, Any] = Field(..., description="Summary statistics for dashboard widgets")
    
    # Navigation context (NEW)
    navigation_context: Optional[NavigationState] = Field(None, description="Navigation context and state")
    prefetch_strategy: Optional[PrefetchStrategy] = Field(None, description="Prefetch strategy configuration")
    navigation_analytics: Optional[NavigationAnalytics] = Field(None, description="Navigation analytics data")
    navigation_performance: Optional[NavigationPerformanceMetrics] = Field(None, description="Navigation performance metrics")
    
    # Cache metadata
    cache_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Cache timestamp")
    cache_ttl_seconds: int = Field(60, description="Cache time-to-live in seconds")
    data_freshness_seconds: int = Field(..., description="Data freshness in seconds")
    
    # API metadata
    response_time_ms: float = Field(..., description="API response time in milliseconds")
    request_id: str = Field(..., description="Unique request identifier")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
        schema_extra = {
            "example": {
                "recent_analyses": [
                    {
                        "analysis_id": "analysis_123",
                        "filename": "sample_video.mp4",
                        "user_id": "user_456",
                        "status": "completed",
                        "confidence_score": 0.95,
                        "is_fake": False,
                        "processing_time_seconds": 12.5,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:12Z",
                        "blockchain_hash": "0x123abc..."
                    }
                ],
                "confidence_trends": [
                    {
                        "timestamp": "2024-01-15T09:00:00Z",
                        "average_confidence": 0.92,
                        "fake_detection_rate": 0.15,
                        "total_analyses": 45,
                        "trend_direction": "stable"
                    }
                ],
                "processing_queue": {
                    "queue_length": 3,
                    "estimated_wait_time_minutes": 5.2,
                    "processing_capacity": 10,
                    "active_processors": 8,
                    "status": "healthy",
                    "throughput_per_hour": 24.5,
                    "error_rate": 0.02
                },
                "user_activity": [
                    {
                        "user_id": "user_456",
                        "email": "user@example.com",
                        "last_activity": "2024-01-15T10:25:00Z",
                        "total_analyses": 150,
                        "recent_analyses": 5,
                        "is_active": True,
                        "role": "analyst"
                    }
                ],
                "system_performance": {
                    "cpu_usage_percent": 45.2,
                    "memory_usage_percent": 67.8,
                    "disk_usage_percent": 23.4,
                    "gpu_usage_percent": 78.9,
                    "network_latency_ms": 12.5,
                    "database_connection_count": 15,
                    "redis_connection_count": 8,
                    "uptime_hours": 168.5
                },
                "blockchain_metrics": {
                    "total_verifications": 1250,
                    "successful_verifications": 1245,
                    "failed_verifications": 5,
                    "pending_verifications": 12,
                    "average_verification_time_seconds": 3.2,
                    "last_verification_at": "2024-01-15T10:28:00Z",
                    "blockchain_network_status": "healthy",
                    "gas_fee_trend": "stable"
                },
                "summary_stats": {
                    "total_analyses_today": 125,
                    "fake_detection_rate_today": 0.18,
                    "average_confidence_today": 0.89,
                    "system_health_score": 0.95,
                    "user_satisfaction_score": 4.7
                },
                "cache_timestamp": "2024-01-15T10:30:00Z",
                "cache_ttl_seconds": 60,
                "data_freshness_seconds": 15,
                "response_time_ms": 45.2,
                "request_id": "req_789"
            }
        }


class DashboardOverviewRequest(BaseModel):
    """Dashboard overview request parameters"""
    include_user_activity: bool = Field(True, description="Include user activity metrics")
    include_blockchain_metrics: bool = Field(True, description="Include blockchain verification metrics")
    include_system_performance: bool = Field(True, description="Include system performance metrics")
    recent_analyses_limit: int = Field(10, ge=1, le=50, description="Limit for recent analyses")
    confidence_trends_hours: int = Field(24, ge=1, le=168, description="Hours of confidence trends to include")
    force_refresh: bool = Field(False, description="Force refresh from cache")


class DashboardCacheKey(BaseModel):
    """Dashboard cache key structure"""
    key_type: str = Field("dashboard_overview", description="Cache key type")
    user_id: Optional[str] = Field(None, description="User ID for personalized data")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Request filters")
    version: str = Field("v1", description="Cache version")
    
    def to_string(self) -> str:
        """Convert to Redis cache key string"""
        key_parts = [self.key_type, self.version]
        if self.user_id:
            key_parts.append(f"user_{self.user_id}")
        if self.filters:
            filter_str = "_".join(f"{k}_{v}" for k, v in sorted(self.filters.items()))
            key_parts.append(filter_str)
        return ":".join(key_parts)


class DashboardMetricsUpdate(BaseModel):
    """Real-time dashboard metrics update"""
    update_type: str = Field(..., description="Type of metrics update")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(..., description="Updated metrics data")
    affected_metrics: List[str] = Field(..., description="List of affected metric names")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
