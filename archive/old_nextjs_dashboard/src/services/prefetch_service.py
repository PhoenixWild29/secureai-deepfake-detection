#!/usr/bin/env python3
"""
Prefetch Service
Service for route-based data prefetching from Core Detection Engine, analysis results, and analytics
"""

import asyncio
import time
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models.navigation import (
    PrefetchTarget,
    PrefetchStrategy,
    NavigationAnalytics,
    NavigationPerformanceMetrics
)
from src.config.navigation_config import get_navigation_config
from src.utils.redis_cache import get_dashboard_cache_manager
from src.dependencies.auth import UserClaims

logger = structlog.get_logger(__name__)


class PrefetchService:
    """
    Service for route-based data prefetching
    Implements non-blocking prefetching to avoid impacting response times
    """
    
    def __init__(self):
        """Initialize prefetch service"""
        self.config = get_navigation_config()
        self._cache_manager = None
        self._http_client = None
        self._prefetch_executor = ThreadPoolExecutor(max_workers=self.config.prefetch.max_concurrent_prefetches)
        self._active_prefetches: Set[str] = set()
        self._prefetch_stats = {
            'total_prefetches': 0,
            'successful_prefetches': 0,
            'failed_prefetches': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("PrefetchService initialized")
    
    async def _get_cache_manager(self):
        """Get Redis cache manager"""
        if self._cache_manager is None:
            self._cache_manager = await get_dashboard_cache_manager()
        return self._cache_manager
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for external service calls"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
        return self._http_client
    
    def _get_default_prefetch_strategy(self) -> PrefetchStrategy:
        """Get default prefetch strategy"""
        return PrefetchStrategy(
            enabled=self.config.prefetch.enabled,
            max_concurrent_prefetches=self.config.prefetch.max_concurrent_prefetches,
            prefetch_threshold_ms=self.config.prefetch.prefetch_threshold_ms,
            user_pattern_analysis=self.config.prefetch.user_pattern_analysis,
            route_mapping=self._get_default_route_mapping(),
            global_cache_ttl_seconds=self.config.prefetch.global_cache_ttl_seconds
        )
    
    def _get_default_route_mapping(self) -> Dict[str, PrefetchTarget]:
        """Get default route to prefetch target mapping"""
        return {
            "/dashboard": PrefetchTarget(
                route_path="/dashboard",
                data_sources=["analytics", "system_performance", "user_activity"],
                priority=1,
                estimated_load_time_ms=80,
                cache_ttl_seconds=300,
                dependencies=[],
                metadata=None
            ),
            "/dashboard/analytics": PrefetchTarget(
                route_path="/dashboard/analytics",
                data_sources=["analytics", "confidence_trends", "user_engagement"],
                priority=2,
                estimated_load_time_ms=120,
                cache_ttl_seconds=300,
                dependencies=["/dashboard"],
                metadata=None
            ),
            "/dashboard/upload": PrefetchTarget(
                route_path="/dashboard/upload",
                data_sources=["detection_engine", "processing_queue"],
                priority=3,
                estimated_load_time_ms=60,
                cache_ttl_seconds=180,
                dependencies=[],
                metadata=None
            ),
            "/dashboard/history": PrefetchTarget(
                route_path="/dashboard/history",
                data_sources=["analysis_results", "user_activity"],
                priority=2,
                estimated_load_time_ms=100,
                cache_ttl_seconds=600,
                dependencies=[],
                metadata=None
            ),
            "/dashboard/results": PrefetchTarget(
                route_path="/dashboard/results",
                data_sources=["analysis_results", "blockchain_metrics"],
                priority=2,
                estimated_load_time_ms=90,
                cache_ttl_seconds=300,
                dependencies=[],
                metadata=None
            ),
            "/dashboard/blockchain": PrefetchTarget(
                route_path="/dashboard/blockchain",
                data_sources=["blockchain_metrics", "verification_status"],
                priority=3,
                estimated_load_time_ms=70,
                cache_ttl_seconds=180,
                dependencies=[],
                metadata=None
            ),
            "/dashboard/settings": PrefetchTarget(
                route_path="/dashboard/settings",
                data_sources=["user_preferences", "system_config"],
                priority=4,
                estimated_load_time_ms=50,
                cache_ttl_seconds=600,
                dependencies=[],
                metadata=None
            )
        }
    
    async def should_prefetch(
        self, 
        current_path: str, 
        response_time_ms: float,
        user_claims: Optional[UserClaims] = None
    ) -> bool:
        """
        Determine if prefetching should be triggered
        
        Args:
            current_path: Current route path
            response_time_ms: Response time of current request
            user_claims: User authentication claims
            
        Returns:
            True if prefetching should be triggered
        """
        if not self.config.prefetch.enabled:
            return False
        
        # Check if response time exceeds threshold
        if response_time_ms > self.config.prefetch.prefetch_threshold_ms:
            return False
        
        # Check if route has prefetch mapping
        strategy = self._get_default_prefetch_strategy()
        if current_path not in strategy.route_mapping:
            return False
        
        # Check concurrent prefetch limit
        if len(self._active_prefetches) >= self.config.prefetch.max_concurrent_prefetches:
            return False
        
        # Check if prefetch is already active for this route
        prefetch_key = f"{current_path}:{user_claims.user_id if user_claims else 'anonymous'}"
        if prefetch_key in self._active_prefetches:
            return False
        
        return True
    
    async def trigger_prefetch(
        self, 
        current_path: str,
        user_claims: Optional[UserClaims] = None,
        background_tasks: Optional[Any] = None
    ) -> bool:
        """
        Trigger prefetching for anticipated routes
        
        Args:
            current_path: Current route path
            user_claims: User authentication claims
            background_tasks: FastAPI background tasks (if available)
            
        Returns:
            True if prefetching was triggered
        """
        try:
            strategy = self._get_default_prefetch_strategy()
            
            # Get prefetch targets for current route
            if current_path not in strategy.route_mapping:
                return False
            
            current_target = strategy.route_mapping[current_path]
            
            # Get likely next routes based on user patterns
            next_routes = await self._get_likely_next_routes(current_path, user_claims)
            
            # Filter routes that have prefetch mappings
            prefetch_targets = [
                route for route in next_routes 
                if route in strategy.route_mapping
            ]
            
            if not prefetch_targets:
                return False
            
            # Trigger prefetching
            if background_tasks:
                # Use FastAPI background tasks
                background_tasks.add_task(
                    self._execute_prefetch_batch,
                    prefetch_targets,
                    user_claims
                )
            else:
                # Execute asynchronously
                asyncio.create_task(
                    self._execute_prefetch_batch(prefetch_targets, user_claims)
                )
            
            logger.info(
                "Prefetch triggered",
                current_path=current_path,
                prefetch_targets=prefetch_targets,
                user_id=user_claims.user_id if user_claims else None
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to trigger prefetch", error=str(e))
            return False
    
    async def _execute_prefetch_batch(
        self, 
        routes: List[str], 
        user_claims: Optional[UserClaims] = None
    ):
        """Execute prefetching for a batch of routes"""
        strategy = self._get_default_prefetch_strategy()
        user_id = user_claims.user_id if user_claims else "anonymous"
        
        for route in routes:
            try:
                prefetch_key = f"{route}:{user_id}"
                self._active_prefetches.add(prefetch_key)
                
                target = strategy.route_mapping[route]
                
                # Execute prefetch
                success = await self._prefetch_route_data(target, user_claims)
                
                if success:
                    self._prefetch_stats['successful_prefetches'] += 1
                else:
                    self._prefetch_stats['failed_prefetches'] += 1
                
                self._prefetch_stats['total_prefetches'] += 1
                
            except Exception as e:
                logger.error("Prefetch failed for route", route=route, error=str(e))
                self._prefetch_stats['failed_prefetches'] += 1
            finally:
                self._active_prefetches.discard(prefetch_key)
    
    async def _prefetch_route_data(
        self, 
        target: PrefetchTarget, 
        user_claims: Optional[UserClaims] = None
    ) -> bool:
        """
        Prefetch data for a specific route
        
        Args:
            target: Prefetch target configuration
            user_claims: User authentication claims
            
        Returns:
            True if prefetching was successful
        """
        try:
            cache_manager = await self._get_cache_manager()
            http_client = await self._get_http_client()
            
            prefetch_results = {}
            
            # Prefetch from each data source
            for data_source in target.data_sources:
                try:
                    data = await self._prefetch_from_source(
                        data_source, 
                        target.route_path, 
                        user_claims,
                        http_client
                    )
                    
                    if data:
                        prefetch_results[data_source] = data
                        
                        # Cache the prefetched data
                        cache_key = f"prefetch:{data_source}:{target.route_path}"
                        await cache_manager.set_prefetch_data(
                            data_source,
                            target.route_path,
                            data,
                            target.cache_ttl_seconds
                        )
                        
                except Exception as e:
                    logger.warning(
                        "Failed to prefetch from source",
                        data_source=data_source,
                        route=target.route_path,
                        error=str(e)
                    )
            
            # Cache combined results
            if prefetch_results:
                combined_cache_key = f"prefetch:combined:{target.route_path}"
                await cache_manager.set_prefetch_data(
                    "combined",
                    target.route_path,
                    prefetch_results,
                    target.cache_ttl_seconds
                )
                
                logger.debug(
                    "Prefetch completed",
                    route=target.route_path,
                    sources_prefetched=len(prefetch_results),
                    estimated_load_time_ms=target.estimated_load_time_ms
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("Prefetch failed", route=target.route_path, error=str(e))
            return False
    
    async def _prefetch_from_source(
        self, 
        data_source: str, 
        route_path: str,
        user_claims: Optional[UserClaims] = None,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Prefetch data from a specific source
        
        Args:
            data_source: Data source identifier
            route_path: Target route path
            user_claims: User authentication claims
            http_client: HTTP client for external calls
            
        Returns:
            Prefetched data or None if failed
        """
        try:
            if http_client is None:
                http_client = await self._get_http_client()
            
            # Map data sources to service endpoints
            source_mapping = {
                "analytics": f"{self.config.analytics_service_url}/api/v1/analytics/overview",
                "detection_engine": f"{self.config.detection_engine_url}/api/v1/status",
                "system_performance": f"{self.config.monitoring_service_url}/api/v1/metrics/system",
                "user_activity": f"{self.config.analytics_service_url}/api/v1/analytics/user-activity",
                "processing_queue": f"{self.config.detection_engine_url}/api/v1/queue/status",
                "analysis_results": f"{self.config.analytics_service_url}/api/v1/analytics/results",
                "blockchain_metrics": f"{self.config.monitoring_service_url}/api/v1/metrics/blockchain",
                "confidence_trends": f"{self.config.analytics_service_url}/api/v1/analytics/trends",
                "user_engagement": f"{self.config.analytics_service_url}/api/v1/analytics/engagement",
                "verification_status": f"{self.config.monitoring_service_url}/api/v1/blockchain/status",
                "user_preferences": f"{self.config.analytics_service_url}/api/v1/user/preferences",
                "system_config": f"{self.config.monitoring_service_url}/api/v1/config/system"
            }
            
            if data_source not in source_mapping:
                logger.warning("Unknown data source", data_source=data_source)
                return None
            
            endpoint = source_mapping[data_source]
            
            # Prepare request headers
            headers = {}
            if user_claims:
                # In a real implementation, you would get the token from user_claims
                # For now, we'll skip the authorization header
                pass
            
            # Make request with timeout
            response = await http_client.get(
                endpoint,
                headers=headers,
                timeout=5.0  # Short timeout for prefetching
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    "Prefetch request failed",
                    data_source=data_source,
                    status_code=response.status_code
                )
                return None
                
        except Exception as e:
            logger.warning(
                "Prefetch from source failed",
                data_source=data_source,
                error=str(e)
            )
            return None
    
    async def _get_likely_next_routes(
        self, 
        current_path: str, 
        user_claims: Optional[UserClaims] = None
    ) -> List[str]:
        """
        Get likely next routes based on user patterns and current route
        
        Args:
            current_path: Current route path
            user_claims: User authentication claims
            
        Returns:
            List of likely next routes
        """
        try:
            # Default route transitions based on common user flows
            route_transitions = {
                "/dashboard": ["/dashboard/analytics", "/dashboard/upload", "/dashboard/history"],
                "/dashboard/analytics": ["/dashboard", "/dashboard/results", "/dashboard/upload"],
                "/dashboard/upload": ["/dashboard/history", "/dashboard/results", "/dashboard"],
                "/dashboard/history": ["/dashboard/results", "/dashboard/analytics", "/dashboard"],
                "/dashboard/results": ["/dashboard/analytics", "/dashboard/blockchain", "/dashboard/history"],
                "/dashboard/blockchain": ["/dashboard/results", "/dashboard", "/dashboard/analytics"],
                "/dashboard/settings": ["/dashboard", "/dashboard/notifications"]
            }
            
            # Get default transitions
            likely_routes = route_transitions.get(current_path, [])
            
            # If user pattern analysis is enabled, enhance with user-specific patterns
            if self.config.prefetch.user_pattern_analysis and user_claims:
                user_patterns = await self._get_user_navigation_patterns(user_claims.user_id)
                if user_patterns:
                    # Combine default patterns with user-specific patterns
                    user_likely_routes = user_patterns.get(current_path, [])
                    likely_routes = list(set(likely_routes + user_likely_routes))
            
            return likely_routes[:3]  # Limit to top 3 most likely routes
            
        except Exception as e:
            logger.error("Failed to get likely next routes", error=str(e))
            return []
    
    async def _get_user_navigation_patterns(self, user_id: str) -> Dict[str, List[str]]:
        """Get user-specific navigation patterns"""
        try:
            cache_manager = await self._get_cache_manager()
            cache_key = f"nav_patterns:{user_id}"
            
            patterns = await cache_manager.get_prefetch_data("patterns", user_id)
            if patterns:
                return patterns
            
            # In a real implementation, this would analyze user navigation history
            # For now, return empty patterns
            return {}
            
        except Exception as e:
            logger.error("Failed to get user navigation patterns", error=str(e))
            return {}
    
    async def get_prefetch_performance_metrics(self) -> NavigationPerformanceMetrics:
        """Get prefetch performance metrics"""
        try:
            total_prefetches = self._prefetch_stats['total_prefetches']
            successful_prefetches = self._prefetch_stats['successful_prefetches']
            
            prefetch_success_rate = (
                successful_prefetches / total_prefetches 
                if total_prefetches > 0 else 0
            )
            
            return NavigationPerformanceMetrics(
                prefetch_success_rate=prefetch_success_rate,
                last_measured=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error("Failed to get prefetch performance metrics", error=str(e))
            return NavigationPerformanceMetrics()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self._http_client:
                await self._http_client.aclose()
            
            if self._prefetch_executor:
                self._prefetch_executor.shutdown(wait=True)
                
            logger.info("PrefetchService cleanup completed")
            
        except Exception as e:
            logger.error("PrefetchService cleanup failed", error=str(e))


# Singleton instance
_prefetch_service: Optional[PrefetchService] = None


async def get_prefetch_service() -> PrefetchService:
    """Get prefetch service singleton"""
    global _prefetch_service
    if _prefetch_service is None:
        _prefetch_service = PrefetchService()
    return _prefetch_service
