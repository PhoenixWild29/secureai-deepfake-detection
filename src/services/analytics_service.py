#!/usr/bin/env python3
"""
Analytics Service
Business logic for retrieving, aggregating, and processing analytics data from the Data Layer
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import structlog
from statistics import mean, median, stdev
import numpy as np
from scipy import stats
import pandas as pd

from src.models.analytics_data import (
    AnalyticsRequest,
    AnalyticsResponse,
    AnalyticsDateRange,
    AnalyticsFilter,
    DetectionPerformanceMetric,
    UserEngagementMetric,
    SystemUtilizationMetric,
    TrendAnalysis,
    PredictiveAnalytics,
    AnalyticsInsight,
    TrendDirection,
    DataClassification
)
from src.models.dashboard import (
    RecentAnalysisSummary,
    ConfidenceScoreTrend,
    ProcessingQueueMetrics,
    UserActivityMetric,
    SystemPerformanceMetrics,
    BlockchainVerificationMetrics
)
from src.utils.redis_cache import get_dashboard_cache_manager
from src.config.dashboard_config import get_external_services_config

logger = structlog.get_logger(__name__)


class DataLayerIntegration:
    """
    Integration with existing Data Layer for analytics data retrieval
    Follows established Data Layer patterns for privacy compliance
    """
    
    def __init__(self):
        """Initialize Data Layer integration"""
        self.cache_manager = None
        self.external_config = get_external_services_config()
        
        logger.info("DataLayerIntegration initialized")
    
    async def _initialize_cache_manager(self):
        """Initialize cache manager if not already done"""
        if self.cache_manager is None:
            self.cache_manager = await get_dashboard_cache_manager()
    
    async def get_detection_performance_data(
        self,
        date_range: AnalyticsDateRange,
        filters: List[AnalyticsFilter]
    ) -> List[DetectionPerformanceMetric]:
        """
        Get detection performance data from Data Layer
        
        Args:
            date_range: Date range for data retrieval
            filters: Additional filters to apply
            
        Returns:
            List of detection performance metrics
        """
        try:
            # In production, this would integrate with actual Data Layer
            # For now, we'll use mock data that follows the established patterns
            
            logger.info("Retrieving detection performance data", date_range=date_range.type)
            
            # Calculate date boundaries
            start_date, end_date = self._calculate_date_boundaries(date_range)
            
            # Mock detection performance data
            metrics = []
            current_date = start_date
            
            while current_date <= end_date:
                # Generate realistic performance metrics
                accuracy_metric = DetectionPerformanceMetric(
                    metric_name="accuracy_rate",
                    value=Decimal("94.2") + Decimal(str(np.random.normal(0, 1))),
                    unit="percent",
                    timestamp=current_date,
                    confidence_interval={
                        "lower": Decimal("93.1"),
                        "upper": Decimal("95.3")
                    },
                    metadata={
                        "model_version": "v2.1",
                        "dataset": "celebrity_df_plus_plus",
                        "sample_size": 1000
                    }
                )
                metrics.append(accuracy_metric)
                
                precision_metric = DetectionPerformanceMetric(
                    metric_name="precision_rate",
                    value=Decimal("92.8") + Decimal(str(np.random.normal(0, 1))),
                    unit="percent",
                    timestamp=current_date,
                    confidence_interval={
                        "lower": Decimal("91.5"),
                        "upper": Decimal("94.1")
                    },
                    metadata={
                        "model_version": "v2.1",
                        "threshold": 0.5
                    }
                )
                metrics.append(precision_metric)
                
                recall_metric = DetectionPerformanceMetric(
                    metric_name="recall_rate",
                    value=Decimal("95.6") + Decimal(str(np.random.normal(0, 1))),
                    unit="percent",
                    timestamp=current_date,
                    confidence_interval={
                        "lower": Decimal("94.2"),
                        "upper": Decimal("97.0")
                    },
                    metadata={
                        "model_version": "v2.1",
                        "threshold": 0.5
                    }
                )
                metrics.append(recall_metric)
                
                current_date += timedelta(hours=1)
            
            # Apply filters
            filtered_metrics = self._apply_filters(metrics, filters)
            
            logger.info("Retrieved detection performance data", count=len(filtered_metrics))
            return filtered_metrics
            
        except Exception as e:
            logger.error("Failed to retrieve detection performance data", error=str(e))
            return []
    
    async def get_user_engagement_data(
        self,
        date_range: AnalyticsDateRange,
        filters: List[AnalyticsFilter]
    ) -> List[UserEngagementMetric]:
        """
        Get user engagement data from Data Layer
        
        Args:
            date_range: Date range for data retrieval
            filters: Additional filters to apply
            
        Returns:
            List of user engagement metrics
        """
        try:
            logger.info("Retrieving user engagement data", date_range=date_range.type)
            
            start_date, end_date = self._calculate_date_boundaries(date_range)
            
            # Mock user engagement data
            metrics = []
            current_date = start_date
            
            # Generate user IDs
            user_ids = [f"user_{i:03d}" for i in range(1, 51)]
            
            while current_date <= end_date:
                for user_id in user_ids[:10]:  # Limit to first 10 users for demo
                    # Analyses performed metric
                    analyses_metric = UserEngagementMetric(
                        user_id=user_id,
                        metric_name="analyses_performed",
                        value=Decimal(str(np.random.poisson(5))),  # Poisson distribution for count data
                        timestamp=current_date,
                        session_id=f"session_{user_id}_{int(current_date.timestamp())}",
                        feature_used="video_analysis",
                        duration_seconds=np.random.randint(60, 300)
                    )
                    metrics.append(analyses_metric)
                    
                    # Session duration metric
                    session_metric = UserEngagementMetric(
                        user_id=user_id,
                        metric_name="session_duration",
                        value=Decimal(str(np.random.normal(180, 60))),  # Average 3 minutes
                        timestamp=current_date,
                        session_id=f"session_{user_id}_{int(current_date.timestamp())}",
                        feature_used="dashboard_view",
                        duration_seconds=np.random.randint(120, 480)
                    )
                    metrics.append(session_metric)
                
                current_date += timedelta(hours=2)
            
            # Apply filters
            filtered_metrics = self._apply_filters(metrics, filters)
            
            logger.info("Retrieved user engagement data", count=len(filtered_metrics))
            return filtered_metrics
            
        except Exception as e:
            logger.error("Failed to retrieve user engagement data", error=str(e))
            return []
    
    async def get_system_utilization_data(
        self,
        date_range: AnalyticsDateRange,
        filters: List[AnalyticsFilter]
    ) -> List[SystemUtilizationMetric]:
        """
        Get system utilization data from Data Layer
        
        Args:
            date_range: Date range for data retrieval
            filters: Additional filters to apply
            
        Returns:
            List of system utilization metrics
        """
        try:
            logger.info("Retrieving system utilization data", date_range=date_range.type)
            
            start_date, end_date = self._calculate_date_boundaries(date_range)
            
            # Mock system utilization data
            metrics = []
            current_date = start_date
            
            while current_date <= end_date:
                # CPU utilization
                cpu_metric = SystemUtilizationMetric(
                    resource_type="cpu",
                    metric_name="usage_percentage",
                    value=Decimal(str(np.random.normal(65, 15))),
                    unit="percent",
                    timestamp=current_date,
                    node_id="node_1",
                    threshold_warning=Decimal("80.0"),
                    threshold_critical=Decimal("90.0")
                )
                metrics.append(cpu_metric)
                
                # Memory utilization
                memory_metric = SystemUtilizationMetric(
                    resource_type="memory",
                    metric_name="usage_percentage",
                    value=Decimal(str(np.random.normal(70, 10))),
                    unit="percent",
                    timestamp=current_date,
                    node_id="node_1",
                    threshold_warning=Decimal("85.0"),
                    threshold_critical=Decimal("95.0")
                )
                metrics.append(memory_metric)
                
                # GPU utilization
                gpu_metric = SystemUtilizationMetric(
                    resource_type="gpu",
                    metric_name="usage_percentage",
                    value=Decimal(str(np.random.normal(45, 20))),
                    unit="percent",
                    timestamp=current_date,
                    node_id="node_1",
                    threshold_warning=Decimal("80.0"),
                    threshold_critical=Decimal("95.0")
                )
                metrics.append(gpu_metric)
                
                # Disk utilization
                disk_metric = SystemUtilizationMetric(
                    resource_type="disk",
                    metric_name="usage_percentage",
                    value=Decimal(str(np.random.normal(30, 5))),
                    unit="percent",
                    timestamp=current_date,
                    node_id="node_1",
                    threshold_warning=Decimal("80.0"),
                    threshold_critical=Decimal("90.0")
                )
                metrics.append(disk_metric)
                
                current_date += timedelta(minutes=15)
            
            # Apply filters
            filtered_metrics = self._apply_filters(metrics, filters)
            
            logger.info("Retrieved system utilization data", count=len(filtered_metrics))
            return filtered_metrics
            
        except Exception as e:
            logger.error("Failed to retrieve system utilization data", error=str(e))
            return []
    
    def _calculate_date_boundaries(self, date_range: AnalyticsDateRange) -> Tuple[datetime, datetime]:
        """Calculate start and end dates based on date range type"""
        now = datetime.now(timezone.utc)
        
        if date_range.type.value == "custom":
            return date_range.start_date, date_range.end_date
        elif date_range.type.value == "last_24_hours":
            return now - timedelta(hours=24), now
        elif date_range.type.value == "last_7_days":
            return now - timedelta(days=7), now
        elif date_range.type.value == "last_30_days":
            return now - timedelta(days=30), now
        elif date_range.type.value == "last_90_days":
            return now - timedelta(days=90), now
        elif date_range.type.value == "last_year":
            return now - timedelta(days=365), now
        else:  # all_time
            return now - timedelta(days=365), now
    
    def _apply_filters(self, metrics: List[Any], filters: List[AnalyticsFilter]) -> List[Any]:
        """Apply filters to metrics data"""
        filtered_metrics = metrics
        
        for filter_obj in filters:
            if filter_obj.type.value == "confidence_level":
                # Filter by confidence level
                if filter_obj.operator == "gte":
                    filtered_metrics = [
                        m for m in filtered_metrics
                        if hasattr(m, 'value') and float(m.value) >= float(filter_obj.value)
                    ]
            elif filter_obj.type.value == "detection_result":
                # Filter by detection result
                if filter_obj.operator == "eq":
                    filtered_metrics = [
                        m for m in filtered_metrics
                        if hasattr(m, 'metadata') and m.metadata.get('result') == filter_obj.value
                    ]
            # Add more filter types as needed
        
        return filtered_metrics


class AnalyticsService:
    """
    Analytics service for processing and aggregating analytics data
    Implements business logic for trend analysis, predictions, and insights
    """
    
    def __init__(self):
        """Initialize analytics service"""
        self.data_layer = DataLayerIntegration()
        
        logger.info("AnalyticsService initialized")
    
    async def get_analytics_data(
        self,
        request: AnalyticsRequest,
        user_id: Optional[str] = None
    ) -> AnalyticsResponse:
        """
        Get comprehensive analytics data based on request parameters
        
        Args:
            request: Analytics request parameters
            user_id: User ID for personalized data and access control
            
        Returns:
            Complete analytics response
        """
        start_time = time.time()
        request_id = f"analytics_req_{int(time.time() * 1000)}"
        
        logger.info(
            "Processing analytics request",
            request_id=request_id,
            user_id=user_id,
            date_range=request.date_range.type,
            filters_count=len(request.filters)
        )
        
        try:
            # Get data from Data Layer
            detection_performance = await self.data_layer.get_detection_performance_data(
                request.date_range, request.filters
            )
            
            user_engagement = await self.data_layer.get_user_engagement_data(
                request.date_range, request.filters
            )
            
            system_utilization = await self.data_layer.get_system_utilization_data(
                request.date_range, request.filters
            )
            
            # Generate trend analysis if requested
            trends = []
            if request.include_trends:
                trends = await self._generate_trend_analysis(
                    detection_performance, user_engagement, system_utilization
                )
            
            # Generate predictive analytics if requested
            predictions = []
            if request.include_predictions:
                predictions = await self._generate_predictive_analytics(
                    detection_performance, user_engagement, system_utilization
                )
            
            # Generate insights and recommendations
            insights = await self._generate_analytics_insights(
                detection_performance, user_engagement, system_utilization, trends
            )
            
            # Calculate total records
            total_records = (
                len(detection_performance) +
                len(user_engagement) +
                len(system_utilization) +
                len(trends) +
                len(predictions) +
                len(insights)
            )
            
            # Determine data classification based on user access level
            data_classification = self._determine_data_classification(user_id, request)
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000
            
            # Create response
            response = AnalyticsResponse(
                detection_performance=detection_performance,
                user_engagement=user_engagement,
                system_utilization=system_utilization,
                trends=trends,
                predictions=predictions,
                insights=insights,
                total_records=total_records,
                date_range=request.date_range,
                filters_applied=request.filters,
                data_classification=data_classification,
                export_available=True,
                export_formats=["csv", "json", "pdf", "excel"],
                query_execution_time_ms=execution_time,
                data_freshness_minutes=5  # Data is considered fresh if less than 5 minutes old
            )
            
            logger.info(
                "Analytics request completed",
                request_id=request_id,
                execution_time_ms=execution_time,
                total_records=total_records,
                trends_count=len(trends),
                insights_count=len(insights)
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Analytics request failed",
                request_id=request_id,
                error=str(e)
            )
            raise
    
    async def _generate_trend_analysis(
        self,
        detection_performance: List[DetectionPerformanceMetric],
        user_engagement: List[UserEngagementMetric],
        system_utilization: List[SystemUtilizationMetric]
    ) -> List[TrendAnalysis]:
        """Generate trend analysis from analytics data"""
        trends = []
        
        try:
            # Analyze detection performance trends
            if detection_performance:
                # Group by metric name
                metric_groups = {}
                for metric in detection_performance:
                    if metric.metric_name not in metric_groups:
                        metric_groups[metric.metric_name] = []
                    metric_groups[metric.metric_name].append(metric)
                
                for metric_name, metrics in metric_groups.items():
                    if len(metrics) >= 5:  # Need at least 5 data points for trend analysis
                        values = [float(m.value) for m in metrics]
                        timestamps = [m.timestamp for m in metrics]
                        
                        # Calculate trend
                        trend_direction, change_percentage = self._calculate_trend(values)
                        
                        # Calculate correlation coefficient
                        x = np.arange(len(values))
                        correlation = np.corrcoef(x, values)[0, 1] if len(values) > 1 else 0
                        
                        trend = TrendAnalysis(
                            metric_name=metric_name,
                            trend_direction=trend_direction,
                            change_percentage=Decimal(str(change_percentage)),
                            period_start=min(timestamps),
                            period_end=max(timestamps),
                            data_points=[Decimal(str(v)) for v in values],
                            correlation_coefficient=Decimal(str(correlation)) if not np.isnan(correlation) else None,
                            significance_level=Decimal("0.95")  # Mock significance level
                        )
                        trends.append(trend)
            
            # Analyze user engagement trends
            if user_engagement:
                engagement_metrics = {}
                for metric in user_engagement:
                    key = f"{metric.metric_name}_{metric.user_id}"
                    if key not in engagement_metrics:
                        engagement_metrics[key] = []
                    engagement_metrics[key].append(metric)
                
                for key, metrics in list(engagement_metrics.items())[:5]:  # Limit to 5 trends
                    if len(metrics) >= 3:
                        values = [float(m.value) for m in metrics]
                        timestamps = [m.timestamp for m in metrics]
                        
                        trend_direction, change_percentage = self._calculate_trend(values)
                        
                        trend = TrendAnalysis(
                            metric_name=key,
                            trend_direction=trend_direction,
                            change_percentage=Decimal(str(change_percentage)),
                            period_start=min(timestamps),
                            period_end=max(timestamps),
                            data_points=[Decimal(str(v)) for v in values]
                        )
                        trends.append(trend)
            
            logger.info("Generated trend analysis", trends_count=len(trends))
            return trends
            
        except Exception as e:
            logger.error("Failed to generate trend analysis", error=str(e))
            return []
    
    async def _generate_predictive_analytics(
        self,
        detection_performance: List[DetectionPerformanceMetric],
        user_engagement: List[UserEngagementMetric],
        system_utilization: List[SystemUtilizationMetric]
    ) -> List[PredictiveAnalytics]:
        """Generate predictive analytics from historical data"""
        predictions = []
        
        try:
            # Simple linear regression prediction for detection performance
            if detection_performance:
                # Group by metric name
                metric_groups = {}
                for metric in detection_performance:
                    if metric.metric_name not in metric_groups:
                        metric_groups[metric.metric_name] = []
                    metric_groups[metric.metric_name].append(metric)
                
                for metric_name, metrics in metric_groups.items():
                    if len(metrics) >= 10:  # Need sufficient data for prediction
                        values = [float(m.value) for m in metrics]
                        
                        # Simple linear trend prediction
                        x = np.arange(len(values))
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
                        
                        # Predict next value
                        next_x = len(values)
                        predicted_value = slope * next_x + intercept
                        
                        # Calculate confidence based on R-squared
                        confidence = abs(r_value) if not np.isnan(r_value) else 0.5
                        
                        prediction = PredictiveAnalytics(
                            metric_name=metric_name,
                            predicted_value=Decimal(str(predicted_value)),
                            confidence_score=Decimal(str(confidence)),
                            prediction_date=datetime.now(timezone.utc) + timedelta(hours=1),
                            model_used="linear_regression",
                            historical_accuracy=Decimal(str(confidence * 0.9)),  # Mock accuracy
                            prediction_interval={
                                "lower": Decimal(str(predicted_value - 2 * std_err)),
                                "upper": Decimal(str(predicted_value + 2 * std_err))
                            }
                        )
                        predictions.append(prediction)
            
            logger.info("Generated predictive analytics", predictions_count=len(predictions))
            return predictions
            
        except Exception as e:
            logger.error("Failed to generate predictive analytics", error=str(e))
            return []
    
    async def _generate_analytics_insights(
        self,
        detection_performance: List[DetectionPerformanceMetric],
        user_engagement: List[UserEngagementMetric],
        system_utilization: List[SystemUtilizationMetric],
        trends: List[TrendAnalysis]
    ) -> List[AnalyticsInsight]:
        """Generate analytics insights and recommendations"""
        insights = []
        
        try:
            # Performance insights
            if detection_performance:
                accuracy_metrics = [m for m in detection_performance if m.metric_name == "accuracy_rate"]
                if accuracy_metrics:
                    avg_accuracy = mean([float(m.value) for m in accuracy_metrics])
                    
                    if avg_accuracy > 95:
                        insight = AnalyticsInsight(
                            title="Excellent Detection Performance",
                            description=f"Detection accuracy is consistently high at {avg_accuracy:.1f}%",
                            insight_type="performance",
                            severity="info",
                            affected_metrics=["accuracy_rate"],
                            recommended_actions=[
                                "Continue monitoring performance",
                                "Consider expanding to additional datasets"
                            ],
                            confidence=Decimal("0.95")
                        )
                        insights.append(insight)
                    elif avg_accuracy < 90:
                        insight = AnalyticsInsight(
                            title="Detection Performance Needs Attention",
                            description=f"Detection accuracy is below optimal at {avg_accuracy:.1f}%",
                            insight_type="performance",
                            severity="warning",
                            affected_metrics=["accuracy_rate"],
                            recommended_actions=[
                                "Review model performance",
                                "Consider model retraining",
                                "Investigate data quality issues"
                            ],
                            confidence=Decimal("0.90")
                        )
                        insights.append(insight)
            
            # System utilization insights
            if system_utilization:
                cpu_metrics = [m for m in system_utilization if m.resource_type == "cpu"]
                if cpu_metrics:
                    avg_cpu = mean([float(m.value) for m in cpu_metrics])
                    
                    if avg_cpu > 80:
                        insight = AnalyticsInsight(
                            title="High CPU Utilization",
                            description=f"Average CPU utilization is {avg_cpu:.1f}%, approaching warning threshold",
                            insight_type="system",
                            severity="warning",
                            affected_metrics=["cpu_usage_percentage"],
                            recommended_actions=[
                                "Monitor system performance closely",
                                "Consider scaling resources",
                                "Optimize processing workflows"
                            ],
                            confidence=Decimal("0.85")
                        )
                        insights.append(insight)
            
            # Trend-based insights
            for trend in trends:
                if trend.trend_direction == TrendDirection.DECREASING:
                    insight = AnalyticsInsight(
                        title=f"Declining {trend.metric_name.replace('_', ' ').title()}",
                        description=f"{trend.metric_name.replace('_', ' ').title()} has decreased by {abs(float(trend.change_percentage)):.1f}%",
                        insight_type="trend",
                        severity="warning",
                        affected_metrics=[trend.metric_name],
                        recommended_actions=[
                            "Investigate cause of decline",
                            "Review recent changes",
                            "Monitor closely for further changes"
                        ],
                        confidence=Decimal("0.80")
                    )
                    insights.append(insight)
            
            logger.info("Generated analytics insights", insights_count=len(insights))
            return insights
            
        except Exception as e:
            logger.error("Failed to generate analytics insights", error=str(e))
            return []
    
    def _calculate_trend(self, values: List[float]) -> Tuple[TrendDirection, float]:
        """Calculate trend direction and percentage change"""
        if len(values) < 2:
            return TrendDirection.STABLE, 0.0
        
        # Simple trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = mean(first_half)
        second_avg = mean(second_half)
        
        change_percentage = ((second_avg - first_avg) / first_avg) * 100 if first_avg != 0 else 0
        
        if abs(change_percentage) < 1:
            return TrendDirection.STABLE, change_percentage
        elif change_percentage > 0:
            return TrendDirection.INCREASING, change_percentage
        else:
            return TrendDirection.DECREASING, change_percentage
    
    def _determine_data_classification(
        self,
        user_id: Optional[str],
        request: AnalyticsRequest
    ) -> DataClassification:
        """Determine data classification based on user access and request parameters"""
        
        # If user is not authenticated, return public data only
        if not user_id:
            return DataClassification.PUBLIC
        
        # Check if request includes sensitive filters
        sensitive_filters = ["user_group", "analysis_type"]
        has_sensitive_filters = any(
            f.type.value in sensitive_filters for f in request.filters
        )
        
        if has_sensitive_filters:
            return DataClassification.CONFIDENTIAL
        
        # Default to internal for authenticated users
        return DataClassification.INTERNAL


# Global analytics service instance
_analytics_service: Optional[AnalyticsService] = None


async def get_analytics_service() -> AnalyticsService:
    """Get global analytics service instance"""
    global _analytics_service
    
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    
    return _analytics_service
