"""
Dashboard Data Service
Orchestrates data retrieval, aggregation, and transformation for dashboard views
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import asyncpg
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.core_detection import Video, Analysis, DetectionResult, FrameAnalysis
from ..models.dashboard import DashboardOverviewResponse, DashboardAnalyticsResponse
from ..data_integration.query_optimizer import QueryOptimizer
from ..data_integration.data_aggregators import DataAggregator
from ..data_integration.analytics_integration import AnalyticsIntegration
from ..data_integration.cognito_user_preferences import CognitoUserPreferences
from ..data_integration.gdpr_anonymization import GDPRAnonymizer

logger = logging.getLogger(__name__)


class DashboardDataError(Exception):
    """Custom exception for dashboard data operations"""
    pass


class DataSource(Enum):
    """Available data sources for dashboard"""
    CORE_DETECTION = "core_detection"
    ANALYTICS = "analytics"
    USER_PREFERENCES = "user_preferences"
    SYSTEM_METRICS = "system_metrics"


@dataclass
class DashboardQueryParams:
    """Parameters for dashboard data queries"""
    user_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    analysis_status: Optional[str] = None
    video_type: Optional[str] = None
    include_anonymized: bool = True
    timezone: str = "UTC"
    limit: int = 1000
    offset: int = 0


@dataclass
class DashboardCacheConfig:
    """Configuration for dashboard data caching"""
    enable_cache: bool = True
    cache_ttl: int = 300  # 5 minutes
    cache_key_prefix: str = "dashboard"
    enable_redis: bool = True


class DashboardDataService:
    """
    Main service for orchestrating dashboard data operations
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        query_optimizer: QueryOptimizer,
        data_aggregator: DataAggregator,
        analytics_integration: AnalyticsIntegration,
        cognito_preferences: CognitoUserPreferences,
        gdpr_anonymizer: GDPRAnonymizer,
        cache_config: Optional[DashboardCacheConfig] = None
    ):
        self.db_session = db_session
        self.query_optimizer = query_optimizer
        self.data_aggregator = data_aggregator
        self.analytics_integration = analytics_integration
        self.cognito_preferences = cognito_preferences
        self.gdpr_anonymizer = gdpr_anonymizer
        self.cache_config = cache_config or DashboardCacheConfig()
        
        # Initialize cache if enabled
        self._cache = {} if self.cache_config.enable_cache else None
        
    async def get_dashboard_overview(
        self, 
        params: DashboardQueryParams
    ) -> DashboardOverviewResponse:
        """
        Get comprehensive dashboard overview data
        
        Args:
            params: Query parameters for dashboard data
            
        Returns:
            DashboardOverviewResponse with aggregated data
            
        Raises:
            DashboardDataError: If data retrieval fails
        """
        try:
            logger.info(f"Fetching dashboard overview for user {params.user_id}")
            
            # Check cache first
            cache_key = self._get_cache_key("overview", params)
            if self._cache and cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=self.cache_config.cache_ttl):
                    logger.debug("Returning cached dashboard overview")
                    return cached_data
            
            # Fetch data from multiple sources in parallel
            tasks = [
                self._get_recent_analyses(params),
                self._get_analysis_statistics(params),
                self._get_system_status(params),
                self._get_user_preferences(params.user_id),
                self._get_performance_metrics(params)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            recent_analyses = self._extract_result(results[0])
            analysis_stats = self._extract_result(results[1])
            system_status = self._extract_result(results[2])
            user_preferences = self._extract_result(results[3])
            performance_metrics = self._extract_result(results[4])
            
            # Aggregate data into response model
            overview_response = await self.data_aggregator.aggregate_overview_data(
                recent_analyses=recent_analyses,
                analysis_statistics=analysis_stats,
                system_status=system_status,
                user_preferences=user_preferences,
                performance_metrics=performance_metrics,
                params=params
            )
            
            # Cache the result
            if self._cache:
                self._cache[cache_key] = (overview_response, datetime.now())
            
            logger.info(f"Successfully fetched dashboard overview for user {params.user_id}")
            return overview_response
            
        except Exception as e:
            logger.error(f"Failed to fetch dashboard overview: {str(e)}")
            raise DashboardDataError(f"Dashboard overview fetch failed: {str(e)}")
    
    async def get_dashboard_analytics(
        self, 
        params: DashboardQueryParams
    ) -> DashboardAnalyticsResponse:
        """
        Get detailed analytics data for dashboard
        
        Args:
            params: Query parameters for analytics data
            
        Returns:
            DashboardAnalyticsResponse with analytics data
            
        Raises:
            DashboardDataError: If analytics retrieval fails
        """
        try:
            logger.info(f"Fetching dashboard analytics for user {params.user_id}")
            
            # Check cache first
            cache_key = self._get_cache_key("analytics", params)
            if self._cache and cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=self.cache_config.cache_ttl):
                    logger.debug("Returning cached dashboard analytics")
                    return cached_data
            
            # Fetch analytics data from multiple sources
            tasks = [
                self._get_user_engagement_metrics(params),
                self._get_detection_performance_metrics(params),
                self._get_system_utilization_metrics(params),
                self._get_trend_analysis(params),
                self._get_anonymized_analytics(params)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            user_engagement = self._extract_result(results[0])
            detection_performance = self._extract_result(results[1])
            system_utilization = self._extract_result(results[2])
            trend_analysis = self._extract_result(results[3])
            anonymized_analytics = self._extract_result(results[4])
            
            # Aggregate analytics data
            analytics_response = await self.data_aggregator.aggregate_analytics_data(
                user_engagement=user_engagement,
                detection_performance=detection_performance,
                system_utilization=system_utilization,
                trend_analysis=trend_analysis,
                anonymized_analytics=anonymized_analytics,
                params=params
            )
            
            # Cache the result
            if self._cache:
                self._cache[cache_key] = (analytics_response, datetime.now())
            
            logger.info(f"Successfully fetched dashboard analytics for user {params.user_id}")
            return analytics_response
            
        except Exception as e:
            logger.error(f"Failed to fetch dashboard analytics: {str(e)}")
            raise DashboardDataError(f"Dashboard analytics fetch failed: {str(e)}")
    
    async def _get_recent_analyses(self, params: DashboardQueryParams) -> List[Dict[str, Any]]:
        """Get recent analyses with optimized query"""
        try:
            query = await self.query_optimizer.build_recent_analyses_query(params)
            result = await self.db_session.execute(query)
            analyses = result.fetchall()
            
            # Convert to dictionaries and apply anonymization if needed
            analyses_data = []
            for analysis in analyses:
                analysis_dict = dict(analysis._mapping)
                if params.include_anonymized:
                    analysis_dict = await self.gdpr_anonymizer.anonymize_analysis_data(analysis_dict)
                analyses_data.append(analysis_dict)
            
            return analyses_data
            
        except Exception as e:
            logger.error(f"Failed to fetch recent analyses: {str(e)}")
            return []
    
    async def _get_analysis_statistics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get analysis statistics with optimized aggregation"""
        try:
            query = await self.query_optimizer.build_analysis_statistics_query(params)
            result = await self.db_session.execute(query)
            stats = result.fetchone()
            
            if stats:
                stats_dict = dict(stats._mapping)
                # Apply anonymization to statistics
                if params.include_anonymized:
                    stats_dict = await self.gdpr_anonymizer.anonymize_statistics_data(stats_dict)
                return stats_dict
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to fetch analysis statistics: {str(e)}")
            return {}
    
    async def _get_system_status(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get system status from analytics integration"""
        try:
            return await self.analytics_integration.get_system_status(params)
        except Exception as e:
            logger.error(f"Failed to fetch system status: {str(e)}")
            return {}
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences from AWS Cognito"""
        try:
            return await self.cognito_preferences.get_user_preferences(user_id)
        except Exception as e:
            logger.error(f"Failed to fetch user preferences: {str(e)}")
            return {}
    
    async def _get_performance_metrics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get performance metrics from analytics integration"""
        try:
            return await self.analytics_integration.get_performance_metrics(params)
        except Exception as e:
            logger.error(f"Failed to fetch performance metrics: {str(e)}")
            return {}
    
    async def _get_user_engagement_metrics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get user engagement metrics"""
        try:
            return await self.analytics_integration.get_user_engagement_metrics(params)
        except Exception as e:
            logger.error(f"Failed to fetch user engagement metrics: {str(e)}")
            return {}
    
    async def _get_detection_performance_metrics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get detection performance metrics"""
        try:
            query = await self.query_optimizer.build_detection_performance_query(params)
            result = await self.db_session.execute(query)
            metrics = result.fetchone()
            
            if metrics:
                metrics_dict = dict(metrics._mapping)
                if params.include_anonymized:
                    metrics_dict = await self.gdpr_anonymizer.anonymize_performance_data(metrics_dict)
                return metrics_dict
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to fetch detection performance metrics: {str(e)}")
            return {}
    
    async def _get_system_utilization_metrics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get system utilization metrics"""
        try:
            return await self.analytics_integration.get_system_utilization_metrics(params)
        except Exception as e:
            logger.error(f"Failed to fetch system utilization metrics: {str(e)}")
            return {}
    
    async def _get_trend_analysis(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get trend analysis data"""
        try:
            query = await self.query_optimizer.build_trend_analysis_query(params)
            result = await self.db_session.execute(query)
            trends = result.fetchall()
            
            trends_data = []
            for trend in trends:
                trend_dict = dict(trend._mapping)
                if params.include_anonymized:
                    trend_dict = await self.gdpr_anonymizer.anonymize_trend_data(trend_dict)
                trends_data.append(trend_dict)
            
            return {"trends": trends_data}
            
        except Exception as e:
            logger.error(f"Failed to fetch trend analysis: {str(e)}")
            return {"trends": []}
    
    async def _get_anonymized_analytics(self, params: DashboardQueryParams) -> Dict[str, Any]:
        """Get anonymized analytics data"""
        try:
            # Get raw analytics data
            raw_analytics = await self.analytics_integration.get_analytics_data(params)
            
            # Apply GDPR anonymization
            anonymized_analytics = await self.gdpr_anonymizer.anonymize_analytics_data(raw_analytics)
            
            return anonymized_analytics
            
        except Exception as e:
            logger.error(f"Failed to fetch anonymized analytics: {str(e)}")
            return {}
    
    def _extract_result(self, result: Any) -> Any:
        """Extract result from asyncio.gather, handling exceptions"""
        if isinstance(result, Exception):
            logger.warning(f"Task failed with exception: {str(result)}")
            return None
        return result
    
    def _get_cache_key(self, data_type: str, params: DashboardQueryParams) -> str:
        """Generate cache key for dashboard data"""
        key_parts = [
            self.cache_config.cache_key_prefix,
            data_type,
            params.user_id,
            params.start_date.isoformat() if params.start_date else "none",
            params.end_date.isoformat() if params.end_date else "none",
            str(params.include_anonymized)
        ]
        return ":".join(key_parts)
    
    async def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear dashboard data cache"""
        if not self._cache:
            return
        
        if user_id:
            # Clear cache for specific user
            keys_to_remove = [key for key in self._cache.keys() if user_id in key]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared cache for user {user_id}")
        else:
            # Clear all cache
            self._cache.clear()
            logger.info("Cleared all dashboard cache")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache:
            return {"enabled": False}
        
        total_keys = len(self._cache)
        expired_keys = 0
        current_time = datetime.now()
        
        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp >= timedelta(seconds=self.cache_config.cache_ttl):
                expired_keys += 1
        
        return {
            "enabled": True,
            "total_keys": total_keys,
            "expired_keys": expired_keys,
            "cache_ttl": self.cache_config.cache_ttl,
            "hit_ratio": "N/A"  # Would need hit/miss tracking
        }


# Factory function for creating dashboard data service
async def create_dashboard_data_service(
    db_session: AsyncSession,
    cache_config: Optional[DashboardCacheConfig] = None
) -> DashboardDataService:
    """
    Factory function to create a configured DashboardDataService
    
    Args:
        db_session: Database session
        cache_config: Optional cache configuration
        
    Returns:
        Configured DashboardDataService instance
    """
    # Initialize all required components
    query_optimizer = QueryOptimizer()
    data_aggregator = DataAggregator()
    analytics_integration = AnalyticsIntegration()
    cognito_preferences = CognitoUserPreferences()
    gdpr_anonymizer = GDPRAnonymizer()
    
    return DashboardDataService(
        db_session=db_session,
        query_optimizer=query_optimizer,
        data_aggregator=data_aggregator,
        analytics_integration=analytics_integration,
        cognito_preferences=cognito_preferences,
        gdpr_anonymizer=gdpr_anonymizer,
        cache_config=cache_config
    )
