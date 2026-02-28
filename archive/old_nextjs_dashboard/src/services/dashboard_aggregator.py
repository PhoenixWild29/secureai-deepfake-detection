#!/usr/bin/env python3
"""
Dashboard Data Aggregation Service
Centralized service for aggregating data from multiple sources for dashboard overview
"""

import asyncio
import httpx
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models.dashboard import (
    DashboardOverviewResponse,
    DashboardOverviewRequest,
    RecentAnalysisSummary,
    ConfidenceScoreTrend,
    ProcessingQueueMetrics,
    UserActivityMetric,
    SystemPerformanceMetrics,
    BlockchainVerificationMetrics,
    AnalysisStatus,
    ConfidenceTrend,
    ProcessingQueueStatus
)
from src.config.dashboard_config import get_external_services_config, get_dashboard_config
from src.utils.redis_cache import get_dashboard_cache_manager
from src.config.dashboard_config import ServiceHealthStatus

logger = structlog.get_logger(__name__)


class ExternalServiceClient:
    """Client for external service communication"""
    
    def __init__(self, base_url: str, timeout: int = 30, retry_attempts: int = 3):
        """
        Initialize external service client
        
        Args:
            base_url: Base URL for the service
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.client = httpx.AsyncClient(timeout=timeout)
        
        logger.info("ExternalServiceClient initialized", base_url=base_url, timeout=timeout)
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to external service
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                start_time = time.time()
                response = await self.client.get(url, params=params)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(
                        "External service request successful",
                        url=url,
                        attempt=attempt + 1,
                        response_time_ms=response_time
                    )
                    return data
                else:
                    logger.warning(
                        "External service request failed",
                        url=url,
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    
            except Exception as e:
                last_exception = e
                logger.warning(
                    "External service request error",
                    url=url,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All attempts failed
        logger.error(
            "External service request failed after all attempts",
            url=url,
            attempts=self.retry_attempts,
            error=str(last_exception)
        )
        raise last_exception or Exception("External service request failed")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class DashboardDataAggregator:
    """
    Dashboard data aggregation service
    Orchestrates data retrieval from multiple sources and aggregates into unified dashboard view
    """
    
    def __init__(self):
        """Initialize dashboard data aggregator"""
        self.config = get_external_services_config()
        self.dashboard_config = get_dashboard_config()
        self.cache_manager = None
        
        # Initialize external service clients
        self.detection_engine_client = ExternalServiceClient(
            self.config.detection_engine_url,
            self.config.detection_engine_timeout,
            self.config.detection_engine_retry_attempts
        )
        
        self.analytics_client = ExternalServiceClient(
            self.config.analytics_service_url,
            self.config.analytics_service_timeout,
            self.config.analytics_service_retry_attempts
        )
        
        self.monitoring_client = ExternalServiceClient(
            self.config.monitoring_service_url,
            self.config.monitoring_service_timeout,
            self.config.monitoring_service_retry_attempts
        )
        
        self.blockchain_client = ExternalServiceClient(
            self.config.blockchain_service_url,
            self.config.blockchain_service_timeout,
            self.config.blockchain_service_retry_attempts
        )
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealthStatus] = {}
        
        logger.info("DashboardDataAggregator initialized")
    
    async def _initialize_cache_manager(self):
        """Initialize cache manager if not already done"""
        if self.cache_manager is None:
            self.cache_manager = await get_dashboard_cache_manager()
    
    async def _check_service_health(self, client: ExternalServiceClient, service_name: str) -> ServiceHealthStatus:
        """
        Check service health
        
        Args:
            client: Service client
            service_name: Name of the service
            
        Returns:
            Service health status
        """
        start_time = time.time()
        
        try:
            # Try to make a health check request
            await client.get("/health")
            response_time = (time.time() - start_time) * 1000
            
            health_status = ServiceHealthStatus(
                service_name=service_name,
                is_healthy=True,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc).isoformat()
            )
            
            logger.debug("Service health check passed", service=service_name, response_time_ms=response_time)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            health_status = ServiceHealthStatus(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc).isoformat(),
                error_message=str(e)
            )
            
            logger.warning("Service health check failed", service=service_name, error=str(e))
        
        self.service_health[service_name] = health_status
        return health_status
    
    async def get_recent_analyses(self, limit: int = 10) -> List[RecentAnalysisSummary]:
        """
        Get recent analysis summaries from Core Detection Engine
        
        Args:
            limit: Maximum number of analyses to return
            
        Returns:
            List of recent analysis summaries
        """
        try:
            data = await self.detection_engine_client.get(
                "/api/v1/analyses/recent",
                params={"limit": limit}
            )
            
            analyses = []
            for item in data.get("analyses", []):
                analysis = RecentAnalysisSummary(
                    analysis_id=item["id"],
                    filename=item["filename"],
                    user_id=item["user_id"],
                    status=AnalysisStatus(item["status"]),
                    confidence_score=Decimal(str(item.get("confidence_score", 0))) if item.get("confidence_score") else None,
                    is_fake=item.get("is_fake"),
                    processing_time_seconds=item.get("processing_time_seconds"),
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                    blockchain_hash=item.get("blockchain_hash")
                )
                analyses.append(analysis)
            
            logger.debug("Retrieved recent analyses", count=len(analyses), limit=limit)
            return analyses
            
        except Exception as e:
            logger.error("Failed to get recent analyses", error=str(e))
            # Return mock data for development
            return self._get_mock_recent_analyses(limit)
    
    async def get_confidence_trends(self, hours: int = 24) -> List[ConfidenceScoreTrend]:
        """
        Get confidence score trends from Core Detection Engine
        
        Args:
            hours: Number of hours of trend data to retrieve
            
        Returns:
            List of confidence score trends
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            data = await self.detection_engine_client.get(
                "/api/v1/analyses/confidence-trends",
                params={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "interval": "hour"
                }
            )
            
            trends = []
            for item in data.get("trends", []):
                trend = ConfidenceScoreTrend(
                    timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                    average_confidence=Decimal(str(item["average_confidence"])),
                    fake_detection_rate=Decimal(str(item["fake_detection_rate"])),
                    total_analyses=item["total_analyses"],
                    trend_direction=ConfidenceTrend(item["trend_direction"])
                )
                trends.append(trend)
            
            logger.debug("Retrieved confidence trends", count=len(trends), hours=hours)
            return trends
            
        except Exception as e:
            logger.error("Failed to get confidence trends", error=str(e))
            # Return mock data for development
            return self._get_mock_confidence_trends(hours)
    
    async def get_processing_queue_metrics(self) -> ProcessingQueueMetrics:
        """
        Get processing queue metrics from Core Detection Engine
        
        Returns:
            Processing queue metrics
        """
        try:
            data = await self.detection_engine_client.get("/api/v1/queue/metrics")
            
            metrics = ProcessingQueueMetrics(
                queue_length=data["queue_length"],
                estimated_wait_time_minutes=data["estimated_wait_time_minutes"],
                processing_capacity=data["processing_capacity"],
                active_processors=data["active_processors"],
                status=ProcessingQueueStatus(data["status"]),
                last_processed_at=datetime.fromisoformat(data["last_processed_at"].replace("Z", "+00:00")) if data.get("last_processed_at") else None,
                throughput_per_hour=data["throughput_per_hour"],
                error_rate=Decimal(str(data["error_rate"]))
            )
            
            logger.debug("Retrieved processing queue metrics", queue_length=metrics.queue_length)
            return metrics
            
        except Exception as e:
            logger.error("Failed to get processing queue metrics", error=str(e))
            # Return mock data for development
            return self._get_mock_processing_queue_metrics()
    
    async def get_user_activity_metrics(self, limit: int = 50) -> List[UserActivityMetric]:
        """
        Get user activity metrics from User Analytics Service
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of user activity metrics
        """
        try:
            data = await self.analytics_client.get(
                "/api/v1/users/activity",
                params={"limit": limit}
            )
            
            users = []
            for item in data.get("users", []):
                user = UserActivityMetric(
                    user_id=item["user_id"],
                    email=item["email"],
                    last_activity=datetime.fromisoformat(item["last_activity"].replace("Z", "+00:00")),
                    total_analyses=item["total_analyses"],
                    recent_analyses=item["recent_analyses"],
                    is_active=item["is_active"],
                    role=item.get("role")
                )
                users.append(user)
            
            logger.debug("Retrieved user activity metrics", count=len(users), limit=limit)
            return users
            
        except Exception as e:
            logger.error("Failed to get user activity metrics", error=str(e))
            # Return mock data for development
            return self._get_mock_user_activity_metrics(limit)
    
    async def get_system_performance_metrics(self) -> SystemPerformanceMetrics:
        """
        Get system performance metrics from System Monitoring Service
        
        Returns:
            System performance metrics
        """
        try:
            data = await self.monitoring_client.get("/api/v1/system/metrics")
            
            metrics = SystemPerformanceMetrics(
                cpu_usage_percent=Decimal(str(data["cpu_usage_percent"])),
                memory_usage_percent=Decimal(str(data["memory_usage_percent"])),
                disk_usage_percent=Decimal(str(data["disk_usage_percent"])),
                gpu_usage_percent=Decimal(str(data["gpu_usage_percent"])) if data.get("gpu_usage_percent") else None,
                network_latency_ms=data["network_latency_ms"],
                database_connection_count=data["database_connection_count"],
                redis_connection_count=data["redis_connection_count"],
                uptime_hours=data["uptime_hours"],
                last_restart=datetime.fromisoformat(data["last_restart"].replace("Z", "+00:00")) if data.get("last_restart") else None
            )
            
            logger.debug("Retrieved system performance metrics")
            return metrics
            
        except Exception as e:
            logger.error("Failed to get system performance metrics", error=str(e))
            # Return mock data for development
            return self._get_mock_system_performance_metrics()
    
    async def get_blockchain_verification_metrics(self) -> BlockchainVerificationMetrics:
        """
        Get blockchain verification metrics from Blockchain Service
        
        Returns:
            Blockchain verification metrics
        """
        try:
            data = await self.blockchain_client.get("/api/v1/verifications/metrics")
            
            metrics = BlockchainVerificationMetrics(
                total_verifications=data["total_verifications"],
                successful_verifications=data["successful_verifications"],
                failed_verifications=data["failed_verifications"],
                pending_verifications=data["pending_verifications"],
                average_verification_time_seconds=data["average_verification_time_seconds"],
                last_verification_at=datetime.fromisoformat(data["last_verification_at"].replace("Z", "+00:00")) if data.get("last_verification_at") else None,
                blockchain_network_status=data["blockchain_network_status"],
                gas_fee_trend=data["gas_fee_trend"]
            )
            
            logger.debug("Retrieved blockchain verification metrics")
            return metrics
            
        except Exception as e:
            logger.error("Failed to get blockchain verification metrics", error=str(e))
            # Return mock data for development
            return self._get_mock_blockchain_verification_metrics()
    
    async def aggregate_dashboard_data(
        self,
        request: DashboardOverviewRequest,
        user_id: Optional[str] = None
    ) -> DashboardOverviewResponse:
        """
        Aggregate dashboard data from all sources
        
        Args:
            request: Dashboard overview request parameters
            user_id: User ID for personalized data
            
        Returns:
            Complete dashboard overview response
        """
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(
            "Starting dashboard data aggregation",
            request_id=request_id,
            user_id=user_id,
            force_refresh=request.force_refresh
        )
        
        try:
            # Check cache first if not forcing refresh
            await self._initialize_cache_manager()
            
            if not request.force_refresh:
                cached_data = await self.cache_manager.get_dashboard_overview(user_id)
                if cached_data:
                    logger.info("Returning cached dashboard data", request_id=request_id)
                    return cached_data
            
            # Aggregate data from all sources concurrently
            aggregation_tasks = []
            
            # Always include recent analyses and confidence trends
            aggregation_tasks.append(self.get_recent_analyses(request.recent_analyses_limit))
            aggregation_tasks.append(self.get_confidence_trends(request.confidence_trends_hours))
            aggregation_tasks.append(self.get_processing_queue_metrics())
            
            # Include optional data based on request parameters
            if request.include_user_activity:
                aggregation_tasks.append(self.get_user_activity_metrics())
            else:
                aggregation_tasks.append(asyncio.create_task(self._get_empty_user_activity()))
            
            if request.include_system_performance:
                aggregation_tasks.append(self.get_system_performance_metrics())
            else:
                aggregation_tasks.append(asyncio.create_task(self._get_empty_system_performance()))
            
            if request.include_blockchain_metrics:
                aggregation_tasks.append(self.get_blockchain_verification_metrics())
            else:
                aggregation_tasks.append(asyncio.create_task(self._get_empty_blockchain_metrics()))
            
            # Wait for all data aggregation tasks to complete
            results = await asyncio.gather(*aggregation_tasks, return_exceptions=True)
            
            # Process results
            recent_analyses = results[0] if not isinstance(results[0], Exception) else []
            confidence_trends = results[1] if not isinstance(results[1], Exception) else []
            processing_queue = results[2] if not isinstance(results[2], Exception) else self._get_mock_processing_queue_metrics()
            user_activity = results[3] if not isinstance(results[3], Exception) else []
            system_performance = results[4] if not isinstance(results[4], Exception) else self._get_mock_system_performance_metrics()
            blockchain_metrics = results[5] if not isinstance(results[5], Exception) else self._get_mock_blockchain_verification_metrics()
            
            # Generate summary statistics
            summary_stats = self._generate_summary_stats(
                recent_analyses,
                confidence_trends,
                processing_queue,
                user_activity,
                system_performance,
                blockchain_metrics
            )
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Create dashboard overview response
            dashboard_response = DashboardOverviewResponse(
                recent_analyses=recent_analyses,
                confidence_trends=confidence_trends,
                processing_queue=processing_queue,
                user_activity=user_activity,
                system_performance=system_performance,
                blockchain_metrics=blockchain_metrics,
                summary_stats=summary_stats,
                cache_ttl_seconds=self.dashboard_config.dashboard.dashboard_ttl,
                data_freshness_seconds=int(time.time() - start_time),
                response_time_ms=response_time,
                request_id=request_id
            )
            
            # Cache the response
            if self.cache_manager:
                await self.cache_manager.set_dashboard_overview(dashboard_response, user_id)
            
            logger.info(
                "Dashboard data aggregation completed",
                request_id=request_id,
                response_time_ms=response_time,
                recent_analyses_count=len(recent_analyses),
                confidence_trends_count=len(confidence_trends)
            )
            
            return dashboard_response
            
        except Exception as e:
            logger.error("Dashboard data aggregation failed", request_id=request_id, error=str(e))
            raise
    
    def _generate_summary_stats(
        self,
        recent_analyses: List[RecentAnalysisSummary],
        confidence_trends: List[ConfidenceScoreTrend],
        processing_queue: ProcessingQueueMetrics,
        user_activity: List[UserActivityMetric],
        system_performance: SystemPerformanceMetrics,
        blockchain_metrics: BlockchainVerificationMetrics
    ) -> Dict[str, Any]:
        """Generate summary statistics for dashboard widgets"""
        
        # Calculate today's statistics
        today = datetime.now(timezone.utc).date()
        today_analyses = [
            analysis for analysis in recent_analyses
            if analysis.created_at.date() == today
        ]
        
        total_analyses_today = len(today_analyses)
        fake_detections_today = len([a for a in today_analyses if a.is_fake is True])
        fake_detection_rate_today = fake_detections_today / total_analyses_today if total_analyses_today > 0 else 0
        
        # Calculate average confidence for today
        confidence_scores_today = [float(a.confidence_score) for a in today_analyses if a.confidence_score is not None]
        average_confidence_today = sum(confidence_scores_today) / len(confidence_scores_today) if confidence_scores_today else 0
        
        # Calculate system health score (0-1)
        system_health_score = 1.0
        if system_performance.cpu_usage_percent > 80:
            system_health_score -= 0.2
        if system_performance.memory_usage_percent > 85:
            system_health_score -= 0.2
        if system_performance.disk_usage_percent > 90:
            system_health_score -= 0.2
        if processing_queue.error_rate > 0.05:
            system_health_score -= 0.2
        if blockchain_metrics.failed_verifications > blockchain_metrics.successful_verifications * 0.1:
            system_health_score -= 0.2
        
        system_health_score = max(0.0, system_health_score)
        
        # Calculate user satisfaction score (mock for now)
        active_users = len([u for u in user_activity if u.is_active])
        user_satisfaction_score = 4.5 + (active_users / 10) * 0.5  # Mock calculation
        
        return {
            "total_analyses_today": total_analyses_today,
            "fake_detection_rate_today": round(fake_detection_rate_today, 3),
            "average_confidence_today": round(average_confidence_today, 3),
            "system_health_score": round(system_health_score, 2),
            "user_satisfaction_score": round(user_satisfaction_score, 1),
            "active_users_count": active_users,
            "queue_status": processing_queue.status.value,
            "blockchain_network_status": blockchain_metrics.blockchain_network_status
        }
    
    async def _get_empty_user_activity(self) -> List[UserActivityMetric]:
        """Get empty user activity for when not requested"""
        return []
    
    async def _get_empty_system_performance(self) -> SystemPerformanceMetrics:
        """Get empty system performance for when not requested"""
        return self._get_mock_system_performance_metrics()
    
    async def _get_empty_blockchain_metrics(self) -> BlockchainVerificationMetrics:
        """Get empty blockchain metrics for when not requested"""
        return self._get_mock_blockchain_verification_metrics()
    
    def _get_mock_recent_analyses(self, limit: int) -> List[RecentAnalysisSummary]:
        """Get mock recent analyses data for development"""
        mock_analyses = []
        for i in range(min(limit, 5)):
            analysis = RecentAnalysisSummary(
                analysis_id=f"analysis_{i+1}",
                filename=f"sample_video_{i+1}.mp4",
                user_id=f"user_{i+1}",
                status=AnalysisStatus.COMPLETED,
                confidence_score=Decimal("0.85") + Decimal(str(i * 0.02)),
                is_fake=i % 3 == 0,  # Every third is fake
                processing_time_seconds=12.5 + i * 2.0,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=i * 15),
                updated_at=datetime.now(timezone.utc) - timedelta(minutes=i * 14),
                blockchain_hash=f"0x{'a' * 64}{i:02x}"
            )
            mock_analyses.append(analysis)
        
        return mock_analyses
    
    def _get_mock_confidence_trends(self, hours: int) -> List[ConfidenceScoreTrend]:
        """Get mock confidence trends data for development"""
        trends = []
        for i in range(min(hours, 12)):  # Limit to 12 data points
            trend = ConfidenceScoreTrend(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=hours-i),
                average_confidence=Decimal("0.88") + Decimal(str(i * 0.001)),
                fake_detection_rate=Decimal("0.15") + Decimal(str(i * 0.002)),
                total_analyses=20 + i * 3,
                trend_direction=ConfidenceTrend.STABLE
            )
            trends.append(trend)
        
        return trends
    
    def _get_mock_processing_queue_metrics(self) -> ProcessingQueueMetrics:
        """Get mock processing queue metrics for development"""
        return ProcessingQueueMetrics(
            queue_length=3,
            estimated_wait_time_minutes=5.2,
            processing_capacity=10,
            active_processors=8,
            status=ProcessingQueueStatus.HEALTHY,
            last_processed_at=datetime.now(timezone.utc) - timedelta(minutes=2),
            throughput_per_hour=24.5,
            error_rate=Decimal("0.02")
        )
    
    def _get_mock_user_activity_metrics(self, limit: int) -> List[UserActivityMetric]:
        """Get mock user activity metrics for development"""
        users = []
        for i in range(min(limit, 5)):
            user = UserActivityMetric(
                user_id=f"user_{i+1}",
                email=f"user{i+1}@example.com",
                last_activity=datetime.now(timezone.utc) - timedelta(minutes=i * 10),
                total_analyses=50 + i * 25,
                recent_analyses=5 + i,
                is_active=i < 3,  # First 3 users are active
                role="analyst" if i % 2 == 0 else "admin"
            )
            users.append(user)
        
        return users
    
    def _get_mock_system_performance_metrics(self) -> SystemPerformanceMetrics:
        """Get mock system performance metrics for development"""
        return SystemPerformanceMetrics(
            cpu_usage_percent=Decimal("45.2"),
            memory_usage_percent=Decimal("67.8"),
            disk_usage_percent=Decimal("23.4"),
            gpu_usage_percent=Decimal("78.9"),
            network_latency_ms=12.5,
            database_connection_count=15,
            redis_connection_count=8,
            uptime_hours=168.5,
            last_restart=datetime.now(timezone.utc) - timedelta(days=7)
        )
    
    def _get_mock_blockchain_verification_metrics(self) -> BlockchainVerificationMetrics:
        """Get mock blockchain verification metrics for development"""
        return BlockchainVerificationMetrics(
            total_verifications=1250,
            successful_verifications=1245,
            failed_verifications=5,
            pending_verifications=12,
            average_verification_time_seconds=3.2,
            last_verification_at=datetime.now(timezone.utc) - timedelta(minutes=2),
            blockchain_network_status="healthy",
            gas_fee_trend="stable"
        )
    
    async def close(self):
        """Close all external service clients"""
        await self.detection_engine_client.close()
        await self.analytics_client.close()
        await self.monitoring_client.close()
        await self.blockchain_client.close()
        
        logger.info("DashboardDataAggregator closed")


# Global aggregator instance
_aggregator: Optional[DashboardDataAggregator] = None


async def get_dashboard_aggregator() -> DashboardDataAggregator:
    """Get global dashboard data aggregator instance"""
    global _aggregator
    
    if _aggregator is None:
        _aggregator = DashboardDataAggregator()
    
    return _aggregator
