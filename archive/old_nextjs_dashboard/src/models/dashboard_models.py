#!/usr/bin/env python3
"""
Dashboard Data Models
Additional models for dashboard data aggregation and response formatting
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field


class RecentAnalysis(BaseModel):
    """Model for recent analysis data"""
    id: str = Field(..., description="Analysis ID")
    video_id: str = Field(..., description="Video ID")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Analysis status")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    confidence_score: Optional[Decimal] = Field(None, description="Confidence score")
    processing_time: Optional[Decimal] = Field(None, description="Processing time in seconds")
    file_size: int = Field(0, description="File size in bytes")
    duration: Optional[Decimal] = Field(None, description="Video duration")
    detection_type: str = Field(..., description="Detection method used")
    is_deepfake: bool = Field(False, description="Detection result")


class AnalysisStatistics(BaseModel):
    """Model for analysis statistics"""
    total_analyses: int = Field(0, description="Total number of analyses")
    completed_analyses: int = Field(0, description="Number of completed analyses")
    failed_analyses: int = Field(0, description="Number of failed analyses")
    processing_analyses: int = Field(0, description="Number of processing analyses")
    avg_processing_time: Optional[Decimal] = Field(None, description="Average processing time")
    avg_confidence: Optional[Decimal] = Field(None, description="Average confidence score")
    last_analysis: Optional[datetime] = Field(None, description="Last analysis timestamp")
    total_file_size: int = Field(0, description="Total file size processed")
    unique_videos: int = Field(0, description="Number of unique videos")
    success_rate: float = Field(0.0, description="Success rate percentage")


class SystemStatus(BaseModel):
    """Model for system status"""
    overall_status: str = Field(..., description="Overall system status")
    cpu_usage: float = Field(0.0, description="CPU usage percentage")
    memory_usage: float = Field(0.0, description="Memory usage percentage")
    disk_usage: float = Field(0.0, description="Disk usage percentage")
    gpu_usage: Optional[float] = Field(None, description="GPU usage percentage")
    active_analyses: int = Field(0, description="Number of active analyses")
    queue_length: int = Field(0, description="Processing queue length")
    last_updated: datetime = Field(..., description="Last update timestamp")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="System alerts")
    maintenance_mode: bool = Field(False, description="Whether in maintenance mode")


class UserPreferences(BaseModel):
    """Model for user preferences"""
    user_id: str = Field(..., description="User ID")
    theme: str = Field("light", description="UI theme")
    language: str = Field("en", description="Language preference")
    timezone: str = Field("UTC", description="Timezone")
    notifications_enabled: bool = Field(True, description="Notifications enabled")
    email_notifications: bool = Field(False, description="Email notifications")
    dashboard_layout: str = Field("default", description="Dashboard layout")
    auto_refresh_interval: int = Field(30, description="Auto refresh interval in seconds")
    data_privacy_level: str = Field("standard", description="Data privacy level")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class PerformanceMetrics(BaseModel):
    """Model for performance metrics"""
    avg_response_time: float = Field(0.0, description="Average response time")
    throughput: float = Field(0.0, description="Throughput per hour")
    error_rate: float = Field(0.0, description="Error rate percentage")
    uptime: float = Field(0.0, description="System uptime percentage")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate")
    database_performance: Dict[str, Any] = Field(default_factory=dict, description="Database performance")
    api_performance: Dict[str, Any] = Field(default_factory=dict, description="API performance")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class UserEngagementMetrics(BaseModel):
    """Model for user engagement metrics"""
    active_users: int = Field(0, description="Number of active users")
    new_users: int = Field(0, description="Number of new users")
    user_retention_rate: float = Field(0.0, description="User retention rate")
    avg_session_duration: float = Field(0.0, description="Average session duration")
    feature_usage: Dict[str, Any] = Field(default_factory=dict, description="Feature usage statistics")
    user_satisfaction_score: float = Field(0.0, description="User satisfaction score")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class DetectionPerformanceMetrics(BaseModel):
    """Model for detection performance metrics"""
    total_detections: int = Field(0, description="Total number of detections")
    deepfake_detections: int = Field(0, description="Number of deepfake detections")
    authentic_detections: int = Field(0, description="Number of authentic detections")
    avg_detection_confidence: float = Field(0.0, description="Average detection confidence")
    max_confidence: float = Field(0.0, description="Maximum confidence score")
    min_confidence: float = Field(0.0, description="Minimum confidence score")
    detection_types_count: int = Field(0, description="Number of detection types used")
    avg_deepfake_confidence: float = Field(0.0, description="Average deepfake confidence")
    avg_authentic_confidence: float = Field(0.0, description="Average authentic confidence")
    accuracy_rate: float = Field(0.0, description="Detection accuracy rate")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class SystemUtilizationMetrics(BaseModel):
    """Model for system utilization metrics"""
    cpu_utilization: float = Field(0.0, description="CPU utilization percentage")
    memory_utilization: float = Field(0.0, description="Memory utilization percentage")
    disk_utilization: float = Field(0.0, description="Disk utilization percentage")
    gpu_utilization: Optional[float] = Field(None, description="GPU utilization percentage")
    network_utilization: float = Field(0.0, description="Network utilization percentage")
    processing_capacity: float = Field(0.0, description="Processing capacity percentage")
    queue_utilization: float = Field(0.0, description="Queue utilization percentage")
    resource_efficiency: float = Field(0.0, description="Resource efficiency score")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class TrendAnalysis(BaseModel):
    """Model for trend analysis data"""
    trends: List[Dict[str, Any]] = Field(default_factory=list, description="Trend data points")
    trend_direction: str = Field("stable", description="Overall trend direction")
    growth_rate: float = Field(0.0, description="Growth rate percentage")
    seasonality_detected: bool = Field(False, description="Whether seasonality is detected")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class AnonymizedAnalytics(BaseModel):
    """Model for anonymized analytics data"""
    anonymized_user_count: int = Field(0, description="Number of anonymized users")
    aggregated_metrics: Dict[str, Any] = Field(default_factory=dict, description="Aggregated metrics")
    privacy_compliant_data: Dict[str, Any] = Field(default_factory=dict, description="Privacy compliant data")
    data_retention_compliance: bool = Field(True, description="Data retention compliance")
    anonymization_method: str = Field("k_anonymity", description="Anonymization method used")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
