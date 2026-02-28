"""
Data Aggregators
Functions to aggregate data from various sources into dashboard response models
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from ..models.dashboard import (
    DashboardOverviewResponse, 
    DashboardAnalyticsResponse
)
from ..models.dashboard_models import (
    RecentAnalysis,
    AnalysisStatistics,
    SystemStatus,
    UserPreferences,
    PerformanceMetrics,
    UserEngagementMetrics,
    DetectionPerformanceMetrics,
    SystemUtilizationMetrics,
    TrendAnalysis,
    AnonymizedAnalytics
)
from ..data_integration.dashboard_data_service import DashboardQueryParams

logger = logging.getLogger(__name__)


class DataAggregationError(Exception):
    """Custom exception for data aggregation errors"""
    pass


@dataclass
class AggregationContext:
    """Context for data aggregation operations"""
    user_id: str
    timezone: str
    include_anonymized: bool
    aggregation_level: str = "user"  # user, system, global


class DataAggregator:
    """
    Aggregates data from various sources into dashboard response models
    """
    
    def __init__(self):
        self.aggregation_cache = {}
        self.performance_stats = {
            "total_aggregations": 0,
            "avg_processing_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def aggregate_overview_data(
        self,
        recent_analyses: List[Dict[str, Any]],
        analysis_statistics: Dict[str, Any],
        system_status: Dict[str, Any],
        user_preferences: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        params: DashboardQueryParams
    ) -> DashboardOverviewResponse:
        """
        Aggregate data into DashboardOverviewResponse
        
        Args:
            recent_analyses: List of recent analysis data
            analysis_statistics: Analysis statistics data
            system_status: System status data
            user_preferences: User preferences data
            performance_metrics: Performance metrics data
            params: Query parameters
            
        Returns:
            DashboardOverviewResponse with aggregated data
        """
        try:
            import time
            start_time = time.time()
            
            logger.debug(f"Aggregating overview data for user {params.user_id}")
            
            # Process recent analyses
            recent_analyses_processed = await self._process_recent_analyses(recent_analyses)
            
            # Process analysis statistics
            analysis_stats_processed = await self._process_analysis_statistics(analysis_statistics)
            
            # Process system status
            system_status_processed = await self._process_system_status(system_status)
            
            # Process user preferences
            user_prefs_processed = await self._process_user_preferences(user_preferences)
            
            # Process performance metrics
            perf_metrics_processed = await self._process_performance_metrics(performance_metrics)
            
            # Create response object
            overview_response = DashboardOverviewResponse(
                user_id=params.user_id,
                timestamp=datetime.now(),
                recent_analyses=recent_analyses_processed,
                analysis_statistics=analysis_stats_processed,
                system_status=system_status_processed,
                user_preferences=user_prefs_processed,
                performance_metrics=perf_metrics_processed,
                metadata={
                    "data_sources": ["core_detection", "analytics", "user_preferences"],
                    "aggregation_time": datetime.now(),
                    "timezone": params.timezone,
                    "include_anonymized": params.include_anonymized
                }
            )
            
            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)
            
            logger.info(f"Successfully aggregated overview data for user {params.user_id}")
            return overview_response
            
        except Exception as e:
            logger.error(f"Failed to aggregate overview data: {str(e)}")
            raise DataAggregationError(f"Overview data aggregation failed: {str(e)}")
    
    async def aggregate_analytics_data(
        self,
        user_engagement: Dict[str, Any],
        detection_performance: Dict[str, Any],
        system_utilization: Dict[str, Any],
        trend_analysis: Dict[str, Any],
        anonymized_analytics: Dict[str, Any],
        params: DashboardQueryParams
    ) -> DashboardAnalyticsResponse:
        """
        Aggregate data into DashboardAnalyticsResponse
        
        Args:
            user_engagement: User engagement metrics
            detection_performance: Detection performance metrics
            system_utilization: System utilization metrics
            trend_analysis: Trend analysis data
            anonymized_analytics: Anonymized analytics data
            params: Query parameters
            
        Returns:
            DashboardAnalyticsResponse with aggregated data
        """
        try:
            import time
            start_time = time.time()
            
            logger.debug(f"Aggregating analytics data for user {params.user_id}")
            
            # Process user engagement metrics
            user_engagement_processed = await self._process_user_engagement(user_engagement)
            
            # Process detection performance metrics
            detection_perf_processed = await self._process_detection_performance(detection_performance)
            
            # Process system utilization metrics
            system_util_processed = await self._process_system_utilization(system_utilization)
            
            # Process trend analysis
            trend_analysis_processed = await self._process_trend_analysis(trend_analysis)
            
            # Process anonymized analytics
            anonymized_analytics_processed = await self._process_anonymized_analytics(anonymized_analytics)
            
            # Create response object
            analytics_response = DashboardAnalyticsResponse(
                user_id=params.user_id,
                timestamp=datetime.now(),
                user_engagement=user_engagement_processed,
                detection_performance=detection_perf_processed,
                system_utilization=system_util_processed,
                trend_analysis=trend_analysis_processed,
                anonymized_analytics=anonymized_analytics_processed,
                metadata={
                    "data_sources": ["analytics", "core_detection", "system_metrics"],
                    "aggregation_time": datetime.now(),
                    "timezone": params.timezone,
                    "include_anonymized": params.include_anonymized,
                    "privacy_compliant": True
                }
            )
            
            # Update performance stats
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)
            
            logger.info(f"Successfully aggregated analytics data for user {params.user_id}")
            return analytics_response
            
        except Exception as e:
            logger.error(f"Failed to aggregate analytics data: {str(e)}")
            raise DataAggregationError(f"Analytics data aggregation failed: {str(e)}")
    
    async def _process_recent_analyses(self, analyses_data: List[Dict[str, Any]]) -> List[RecentAnalysis]:
        """Process recent analyses data into RecentAnalysis objects"""
        try:
            processed_analyses = []
            
            for analysis in analyses_data:
                try:
                    recent_analysis = RecentAnalysis(
                        id=analysis.get('id', ''),
                        video_id=analysis.get('video_id', ''),
                        filename=analysis.get('filename', ''),
                        status=analysis.get('status', 'unknown'),
                        created_at=self._parse_datetime(analysis.get('created_at')),
                        completed_at=self._parse_datetime(analysis.get('completed_at')),
                        confidence_score=self._parse_decimal(analysis.get('confidence_score')),
                        processing_time=self._parse_decimal(analysis.get('processing_time')),
                        file_size=analysis.get('file_size', 0),
                        duration=self._parse_decimal(analysis.get('duration')),
                        detection_type=analysis.get('detection_type', ''),
                        is_deepfake=analysis.get('is_deepfake', False)
                    )
                    processed_analyses.append(recent_analysis)
                    
                except Exception as e:
                    logger.warning(f"Failed to process analysis {analysis.get('id', 'unknown')}: {str(e)}")
                    continue
            
            return processed_analyses
            
        except Exception as e:
            logger.error(f"Failed to process recent analyses: {str(e)}")
            return []
    
    async def _process_analysis_statistics(self, stats_data: Dict[str, Any]) -> AnalysisStatistics:
        """Process analysis statistics data into AnalysisStatistics object"""
        try:
            return AnalysisStatistics(
                total_analyses=stats_data.get('total_analyses', 0),
                completed_analyses=stats_data.get('completed_analyses', 0),
                failed_analyses=stats_data.get('failed_analyses', 0),
                processing_analyses=stats_data.get('processing_analyses', 0),
                avg_processing_time=self._parse_decimal(stats_data.get('avg_processing_time')),
                avg_confidence=self._parse_decimal(stats_data.get('avg_confidence')),
                last_analysis=self._parse_datetime(stats_data.get('last_analysis')),
                total_file_size=stats_data.get('total_file_size', 0),
                unique_videos=stats_data.get('unique_videos', 0),
                success_rate=self._calculate_success_rate(
                    stats_data.get('completed_analyses', 0),
                    stats_data.get('total_analyses', 0)
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to process analysis statistics: {str(e)}")
            return AnalysisStatistics()
    
    async def _process_system_status(self, status_data: Dict[str, Any]) -> SystemStatus:
        """Process system status data into SystemStatus object"""
        try:
            return SystemStatus(
                overall_status=status_data.get('overall_status', 'unknown'),
                cpu_usage=status_data.get('cpu_usage', 0.0),
                memory_usage=status_data.get('memory_usage', 0.0),
                disk_usage=status_data.get('disk_usage', 0.0),
                gpu_usage=status_data.get('gpu_usage', 0.0),
                active_analyses=status_data.get('active_analyses', 0),
                queue_length=status_data.get('queue_length', 0),
                last_updated=self._parse_datetime(status_data.get('last_updated')),
                alerts=status_data.get('alerts', []),
                maintenance_mode=status_data.get('maintenance_mode', False)
            )
            
        except Exception as e:
            logger.error(f"Failed to process system status: {str(e)}")
            return SystemStatus()
    
    async def _process_user_preferences(self, prefs_data: Dict[str, Any]) -> UserPreferences:
        """Process user preferences data into UserPreferences object"""
        try:
            return UserPreferences(
                user_id=prefs_data.get('user_id', ''),
                theme=prefs_data.get('theme', 'light'),
                language=prefs_data.get('language', 'en'),
                timezone=prefs_data.get('timezone', 'UTC'),
                notifications_enabled=prefs_data.get('notifications_enabled', True),
                email_notifications=prefs_data.get('email_notifications', False),
                dashboard_layout=prefs_data.get('dashboard_layout', 'default'),
                auto_refresh_interval=prefs_data.get('auto_refresh_interval', 30),
                data_privacy_level=prefs_data.get('data_privacy_level', 'standard'),
                last_updated=self._parse_datetime(prefs_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process user preferences: {str(e)}")
            return UserPreferences()
    
    async def _process_performance_metrics(self, metrics_data: Dict[str, Any]) -> PerformanceMetrics:
        """Process performance metrics data into PerformanceMetrics object"""
        try:
            return PerformanceMetrics(
                avg_response_time=metrics_data.get('avg_response_time', 0.0),
                throughput=metrics_data.get('throughput', 0.0),
                error_rate=metrics_data.get('error_rate', 0.0),
                uptime=metrics_data.get('uptime', 0.0),
                cache_hit_rate=metrics_data.get('cache_hit_rate', 0.0),
                database_performance=metrics_data.get('database_performance', {}),
                api_performance=metrics_data.get('api_performance', {}),
                last_updated=self._parse_datetime(metrics_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process performance metrics: {str(e)}")
            return PerformanceMetrics()
    
    async def _process_user_engagement(self, engagement_data: Dict[str, Any]) -> UserEngagementMetrics:
        """Process user engagement metrics data"""
        try:
            return UserEngagementMetrics(
                active_users=engagement_data.get('active_users', 0),
                new_users=engagement_data.get('new_users', 0),
                user_retention_rate=engagement_data.get('user_retention_rate', 0.0),
                avg_session_duration=engagement_data.get('avg_session_duration', 0.0),
                feature_usage=engagement_data.get('feature_usage', {}),
                user_satisfaction_score=engagement_data.get('user_satisfaction_score', 0.0),
                last_updated=self._parse_datetime(engagement_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process user engagement: {str(e)}")
            return UserEngagementMetrics()
    
    async def _process_detection_performance(self, perf_data: Dict[str, Any]) -> DetectionPerformanceMetrics:
        """Process detection performance metrics data"""
        try:
            return DetectionPerformanceMetrics(
                total_detections=perf_data.get('total_detections', 0),
                deepfake_detections=perf_data.get('deepfake_detections', 0),
                authentic_detections=perf_data.get('authentic_detections', 0),
                avg_detection_confidence=perf_data.get('avg_detection_confidence', 0.0),
                max_confidence=perf_data.get('max_confidence', 0.0),
                min_confidence=perf_data.get('min_confidence', 0.0),
                detection_types_count=perf_data.get('detection_types_count', 0),
                avg_deepfake_confidence=perf_data.get('avg_deepfake_confidence', 0.0),
                avg_authentic_confidence=perf_data.get('avg_authentic_confidence', 0.0),
                accuracy_rate=self._calculate_accuracy_rate(perf_data),
                last_updated=self._parse_datetime(perf_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process detection performance: {str(e)}")
            return DetectionPerformanceMetrics()
    
    async def _process_system_utilization(self, util_data: Dict[str, Any]) -> SystemUtilizationMetrics:
        """Process system utilization metrics data"""
        try:
            return SystemUtilizationMetrics(
                cpu_utilization=util_data.get('cpu_utilization', 0.0),
                memory_utilization=util_data.get('memory_utilization', 0.0),
                disk_utilization=util_data.get('disk_utilization', 0.0),
                gpu_utilization=util_data.get('gpu_utilization', 0.0),
                network_utilization=util_data.get('network_utilization', 0.0),
                processing_capacity=util_data.get('processing_capacity', 0.0),
                queue_utilization=util_data.get('queue_utilization', 0.0),
                resource_efficiency=util_data.get('resource_efficiency', 0.0),
                last_updated=self._parse_datetime(util_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process system utilization: {str(e)}")
            return SystemUtilizationMetrics()
    
    async def _process_trend_analysis(self, trend_data: Dict[str, Any]) -> TrendAnalysis:
        """Process trend analysis data"""
        try:
            trends = trend_data.get('trends', [])
            processed_trends = []
            
            for trend in trends:
                processed_trend = {
                    'date': self._parse_datetime(trend.get('date')),
                    'analyses_count': trend.get('analyses_count', 0),
                    'completed_count': trend.get('completed_count', 0),
                    'avg_processing_time': self._parse_decimal(trend.get('avg_processing_time')),
                    'avg_confidence': self._parse_decimal(trend.get('avg_confidence')),
                    'unique_videos': trend.get('unique_videos', 0)
                }
                processed_trends.append(processed_trend)
            
            return TrendAnalysis(
                trends=processed_trends,
                trend_direction=self._calculate_trend_direction(processed_trends),
                growth_rate=self._calculate_growth_rate(processed_trends),
                seasonality_detected=self._detect_seasonality(processed_trends),
                last_updated=self._parse_datetime(trend_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process trend analysis: {str(e)}")
            return TrendAnalysis()
    
    async def _process_anonymized_analytics(self, analytics_data: Dict[str, Any]) -> AnonymizedAnalytics:
        """Process anonymized analytics data"""
        try:
            return AnonymizedAnalytics(
                anonymized_user_count=analytics_data.get('anonymized_user_count', 0),
                aggregated_metrics=analytics_data.get('aggregated_metrics', {}),
                privacy_compliant_data=analytics_data.get('privacy_compliant_data', {}),
                data_retention_compliance=analytics_data.get('data_retention_compliance', True),
                anonymization_method=analytics_data.get('anonymization_method', 'k_anonymity'),
                last_updated=self._parse_datetime(analytics_data.get('last_updated'))
            )
            
        except Exception as e:
            logger.error(f"Failed to process anonymized analytics: {str(e)}")
            return AnonymizedAnalytics()
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime value safely"""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.warning(f"Failed to parse datetime: {value}")
                    return None
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse decimal value safely"""
        if value is None:
            return None
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse decimal: {value}")
            return None
    
    def _calculate_success_rate(self, completed: int, total: int) -> float:
        """Calculate success rate percentage"""
        if total == 0:
            return 0.0
        return (completed / total) * 100.0
    
    def _calculate_accuracy_rate(self, perf_data: Dict[str, Any]) -> float:
        """Calculate detection accuracy rate"""
        total_detections = perf_data.get('total_detections', 0)
        if total_detections == 0:
            return 0.0
        
        # Simplified accuracy calculation
        # In practice, this would be more sophisticated
        avg_confidence = perf_data.get('avg_detection_confidence', 0.0)
        return min(avg_confidence * 100, 100.0)
    
    def _calculate_trend_direction(self, trends: List[Dict[str, Any]]) -> str:
        """Calculate overall trend direction"""
        if len(trends) < 2:
            return "insufficient_data"
        
        first_count = trends[0].get('analyses_count', 0)
        last_count = trends[-1].get('analyses_count', 0)
        
        if last_count > first_count:
            return "increasing"
        elif last_count < first_count:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_growth_rate(self, trends: List[Dict[str, Any]]) -> float:
        """Calculate growth rate percentage"""
        if len(trends) < 2:
            return 0.0
        
        first_count = trends[0].get('analyses_count', 0)
        last_count = trends[-1].get('analyses_count', 0)
        
        if first_count == 0:
            return 0.0
        
        return ((last_count - first_count) / first_count) * 100.0
    
    def _detect_seasonality(self, trends: List[Dict[str, Any]]) -> bool:
        """Detect if there's seasonality in the trends"""
        if len(trends) < 7:  # Need at least a week of data
            return False
        
        # Simple seasonality detection based on day-of-week patterns
        # In practice, this would use more sophisticated statistical methods
        weekday_counts = {}
        for trend in trends:
            if trend.get('date'):
                weekday = trend['date'].weekday()
                weekday_counts[weekday] = weekday_counts.get(weekday, 0) + trend.get('analyses_count', 0)
        
        # Check if there's significant variation by weekday
        if len(weekday_counts) >= 5:
            counts = list(weekday_counts.values())
            variance = sum((x - sum(counts)/len(counts))**2 for x in counts) / len(counts)
            return variance > 100  # Threshold for seasonality detection
        
        return False
    
    def _update_performance_stats(self, processing_time: float) -> None:
        """Update performance statistics"""
        self.performance_stats["total_aggregations"] += 1
        
        # Update average processing time
        total = self.performance_stats["total_aggregations"]
        current_avg = self.performance_stats["avg_processing_time"]
        self.performance_stats["avg_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            "aggregation_stats": self.performance_stats,
            "cache_stats": {
                "cache_hits": self.performance_stats["cache_hits"],
                "cache_misses": self.performance_stats["cache_misses"],
                "hit_rate": (
                    self.performance_stats["cache_hits"] / 
                    (self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"])
                    if (self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"]) > 0
                    else 0.0
                )
            }
        }
