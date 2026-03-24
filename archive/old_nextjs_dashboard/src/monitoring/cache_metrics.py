#!/usr/bin/env python3
"""
Dashboard Cache Metrics Monitoring Module
Cache hit/miss monitoring and performance metrics to ensure caching effectiveness meets dashboard performance requirements
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Union
from uuid import UUID
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics

# Import cache manager and dashboard components
from src.data_layer.cache_manager import cache_manager
from src.dashboard.cache_keys import DashboardCacheType, get_cache_key_ttl

# Configure logging
logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Enumeration of cache metric types"""
    HIT_RATE = "hit_rate"
    MISS_RATE = "miss_rate"
    RESPONSE_TIME = "response_time"
    CACHE_SIZE = "cache_size"
    INVALIDATION_COUNT = "invalidation_count"
    WARMING_SUCCESS = "warming_success"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class PerformanceThreshold(str, Enum):
    """Enumeration of performance thresholds"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


class CacheMetricsCollector:
    """
    Cache metrics collector for dashboard performance monitoring.
    Tracks cache hit/miss rates, response times, and other performance metrics.
    """
    
    def __init__(self, max_history_size: int = 1000):
        self.cache_manager = cache_manager
        self.max_history_size = max_history_size
        
        # Metrics storage
        self._metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._cache_type_metrics: Dict[DashboardCacheType, Dict[str, Any]] = defaultdict(dict)
        self._user_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Performance thresholds
        self._thresholds = {
            "response_time_ms": {
                PerformanceThreshold.EXCELLENT: 50,
                PerformanceThreshold.GOOD: 100,
                PerformanceThreshold.ACCEPTABLE: 200,
                PerformanceThreshold.POOR: 500,
                PerformanceThreshold.CRITICAL: 1000
            },
            "hit_rate_percent": {
                PerformanceThreshold.EXCELLENT: 95,
                PerformanceThreshold.GOOD: 85,
                PerformanceThreshold.ACCEPTABLE: 70,
                PerformanceThreshold.POOR: 50,
                PerformanceThreshold.CRITICAL: 30
            },
            "error_rate_percent": {
                PerformanceThreshold.EXCELLENT: 0,
                PerformanceThreshold.GOOD: 1,
                PerformanceThreshold.ACCEPTABLE: 5,
                PerformanceThreshold.POOR: 10,
                PerformanceThreshold.CRITICAL: 20
            }
        }
        
        # Start background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
    
    async def start_monitoring(self) -> None:
        """Start background metrics monitoring"""
        if self._is_monitoring:
            logger.warning("Cache metrics monitoring is already running")
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started cache metrics monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background metrics monitoring"""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped cache metrics monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while self._is_monitoring:
            try:
                # Collect current metrics
                await self._collect_system_metrics()
                
                # Analyze performance
                await self._analyze_performance()
                
                # Wait before next collection
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-wide cache metrics"""
        try:
            # Get cache manager metrics
            cache_metrics = self.cache_manager.get_cache_metrics()
            
            # Store metrics
            timestamp = datetime.now(timezone.utc)
            
            self._metrics_history["hit_rate"].append({
                "timestamp": timestamp,
                "value": cache_metrics.get("hit_rate_percent", 0)
            })
            
            self._metrics_history["response_time"].append({
                "timestamp": timestamp,
                "value": cache_metrics.get("avg_response_time_ms", 0)
            })
            
            self._metrics_history["total_requests"].append({
                "timestamp": timestamp,
                "value": cache_metrics.get("total_requests", 0)
            })
            
            self._metrics_history["errors"].append({
                "timestamp": timestamp,
                "value": cache_metrics.get("errors", 0)
            })
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _analyze_performance(self) -> None:
        """Analyze cache performance and detect issues"""
        try:
            # Analyze recent metrics
            recent_hit_rate = self._get_recent_average("hit_rate")
            recent_response_time = self._get_recent_average("response_time")
            recent_error_rate = self._get_recent_error_rate()
            
            # Check thresholds
            hit_rate_threshold = self._get_performance_threshold("hit_rate_percent", recent_hit_rate)
            response_time_threshold = self._get_performance_threshold("response_time_ms", recent_response_time)
            error_rate_threshold = self._get_performance_threshold("error_rate_percent", recent_error_rate)
            
            # Log performance issues
            if hit_rate_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
                logger.warning(f"Low cache hit rate: {recent_hit_rate:.2f}% (threshold: {hit_rate_threshold.value})")
            
            if response_time_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
                logger.warning(f"High cache response time: {recent_response_time:.2f}ms (threshold: {response_time_threshold.value})")
            
            if error_rate_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
                logger.warning(f"High cache error rate: {recent_error_rate:.2f}% (threshold: {error_rate_threshold.value})")
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
    
    def record_cache_operation(
        self,
        operation: str,
        cache_type: DashboardCacheType,
        user_id: Optional[Union[str, UUID]] = None,
        response_time_ms: float = 0.0,
        success: bool = True,
        **kwargs
    ) -> None:
        """
        Record a cache operation for metrics tracking.
        
        Args:
            operation: Type of operation (hit, miss, set, delete, error)
            cache_type: Type of cache
            user_id: User identifier (if applicable)
            response_time_ms: Response time in milliseconds
            success: Whether operation was successful
            **kwargs: Additional operation data
        """
        timestamp = datetime.now(timezone.utc)
        
        # Record general metrics
        self._metrics_history[f"{operation}_count"].append({
            "timestamp": timestamp,
            "value": 1
        })
        
        if response_time_ms > 0:
            self._metrics_history[f"{operation}_response_time"].append({
                "timestamp": timestamp,
                "value": response_time_ms
            })
        
        # Record cache type specific metrics
        if cache_type not in self._cache_type_metrics:
            self._cache_type_metrics[cache_type] = {
                "operations": deque(maxlen=self.max_history_size),
                "response_times": deque(maxlen=self.max_history_size),
                "success_rate": deque(maxlen=self.max_history_size)
            }
        
        self._cache_type_metrics[cache_type]["operations"].append({
            "timestamp": timestamp,
            "operation": operation,
            "success": success,
            "response_time_ms": response_time_ms,
            **kwargs
        })
        
        if response_time_ms > 0:
            self._cache_type_metrics[cache_type]["response_times"].append(response_time_ms)
        
        self._cache_type_metrics[cache_type]["success_rate"].append(success)
        
        # Record user specific metrics
        if user_id:
            user_key = str(user_id)
            if user_key not in self._user_metrics:
                self._user_metrics[user_key] = {
                    "operations": deque(maxlen=self.max_history_size),
                    "response_times": deque(maxlen=self.max_history_size),
                    "cache_types": defaultdict(int)
                }
            
            self._user_metrics[user_key]["operations"].append({
                "timestamp": timestamp,
                "operation": operation,
                "cache_type": cache_type.value,
                "success": success,
                "response_time_ms": response_time_ms
            })
            
            if response_time_ms > 0:
                self._user_metrics[user_key]["response_times"].append(response_time_ms)
            
            self._user_metrics[user_key]["cache_types"][cache_type.value] += 1
    
    def _get_recent_average(self, metric_name: str, minutes: int = 5) -> float:
        """Get average value for a metric over recent time period"""
        if metric_name not in self._metrics_history:
            return 0.0
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_values = [
            entry["value"] for entry in self._metrics_history[metric_name]
            if entry["timestamp"] >= cutoff_time
        ]
        
        return statistics.mean(recent_values) if recent_values else 0.0
    
    def _get_recent_error_rate(self, minutes: int = 5) -> float:
        """Get recent error rate percentage"""
        total_operations = self._get_recent_average("total_requests", minutes)
        errors = self._get_recent_average("errors", minutes)
        
        if total_operations == 0:
            return 0.0
        
        return (errors / total_operations) * 100
    
    def _get_performance_threshold(self, metric_name: str, value: float) -> PerformanceThreshold:
        """Get performance threshold for a metric value"""
        if metric_name not in self._thresholds:
            return PerformanceThreshold.ACCEPTABLE
        
        thresholds = self._thresholds[metric_name]
        
        for threshold in [
            PerformanceThreshold.EXCELLENT,
            PerformanceThreshold.GOOD,
            PerformanceThreshold.ACCEPTABLE,
            PerformanceThreshold.POOR,
            PerformanceThreshold.CRITICAL
        ]:
            if value <= thresholds[threshold]:
                return threshold
        
        return PerformanceThreshold.CRITICAL
    
    def get_cache_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive cache performance summary.
        
        Returns:
            Dict[str, Any]: Performance summary
        """
        try:
            # Get recent metrics
            recent_hit_rate = self._get_recent_average("hit_rate", 5)
            recent_response_time = self._get_recent_average("response_time", 5)
            recent_error_rate = self._get_recent_error_rate(5)
            
            # Get cache manager metrics
            cache_metrics = self.cache_manager.get_cache_metrics()
            
            # Calculate performance thresholds
            hit_rate_threshold = self._get_performance_threshold("hit_rate_percent", recent_hit_rate)
            response_time_threshold = self._get_performance_threshold("response_time_ms", recent_response_time)
            error_rate_threshold = self._get_performance_threshold("error_rate_percent", recent_error_rate)
            
            # Calculate cache type performance
            cache_type_performance = {}
            for cache_type, metrics in self._cache_type_metrics.items():
                if metrics["response_times"]:
                    avg_response_time = statistics.mean(metrics["response_times"])
                    success_rate = sum(metrics["success_rate"]) / len(metrics["success_rate"]) * 100
                    
                    cache_type_performance[cache_type.value] = {
                        "avg_response_time_ms": round(avg_response_time, 2),
                        "success_rate_percent": round(success_rate, 2),
                        "operations_count": len(metrics["operations"]),
                        "performance_threshold": self._get_performance_threshold("response_time_ms", avg_response_time).value
                    }
            
            return {
                "overall_performance": {
                    "hit_rate_percent": round(recent_hit_rate, 2),
                    "avg_response_time_ms": round(recent_response_time, 2),
                    "error_rate_percent": round(recent_error_rate, 2),
                    "total_requests": cache_metrics.get("total_requests", 0),
                    "hits": cache_metrics.get("hits", 0),
                    "misses": cache_metrics.get("misses", 0),
                    "errors": cache_metrics.get("errors", 0)
                },
                "performance_thresholds": {
                    "hit_rate": hit_rate_threshold.value,
                    "response_time": response_time_threshold.value,
                    "error_rate": error_rate_threshold.value
                },
                "cache_type_performance": cache_type_performance,
                "recommendations": self._get_performance_recommendations(
                    hit_rate_threshold, response_time_threshold, error_rate_threshold
                ),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache performance summary: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_performance_recommendations(
        self,
        hit_rate_threshold: PerformanceThreshold,
        response_time_threshold: PerformanceThreshold,
        error_rate_threshold: PerformanceThreshold
    ) -> List[str]:
        """Get performance improvement recommendations"""
        recommendations = []
        
        if hit_rate_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
            recommendations.append("Consider increasing cache TTL values for frequently accessed data")
            recommendations.append("Implement cache warming for critical dashboard components")
            recommendations.append("Review cache key patterns for optimal hit rates")
        
        if response_time_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
            recommendations.append("Optimize Redis configuration for better response times")
            recommendations.append("Consider Redis clustering for improved performance")
            recommendations.append("Review network latency between application and Redis")
        
        if error_rate_threshold in [PerformanceThreshold.POOR, PerformanceThreshold.CRITICAL]:
            recommendations.append("Investigate Redis connection stability")
            recommendations.append("Implement retry mechanisms for failed cache operations")
            recommendations.append("Monitor Redis server health and resources")
        
        if not recommendations:
            recommendations.append("Cache performance is within acceptable thresholds")
        
        return recommendations
    
    def get_user_cache_metrics(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Get cache metrics for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict[str, Any]: User cache metrics
        """
        user_key = str(user_id)
        
        if user_key not in self._user_metrics:
            return {
                "user_id": user_key,
                "message": "No cache metrics available for this user",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        user_metrics = self._user_metrics[user_key]
        
        # Calculate user-specific metrics
        total_operations = len(user_metrics["operations"])
        avg_response_time = statistics.mean(user_metrics["response_times"]) if user_metrics["response_times"] else 0
        
        # Count operations by type
        operation_counts = defaultdict(int)
        success_count = 0
        
        for operation in user_metrics["operations"]:
            operation_counts[operation["operation"]] += 1
            if operation["success"]:
                success_count += 1
        
        success_rate = (success_count / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "user_id": user_key,
            "total_operations": total_operations,
            "avg_response_time_ms": round(avg_response_time, 2),
            "success_rate_percent": round(success_rate, 2),
            "operation_counts": dict(operation_counts),
            "cache_type_usage": dict(user_metrics["cache_types"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_cache_type_metrics(self, cache_type: DashboardCacheType) -> Dict[str, Any]:
        """
        Get metrics for a specific cache type.
        
        Args:
            cache_type: Cache type
            
        Returns:
            Dict[str, Any]: Cache type metrics
        """
        if cache_type not in self._cache_type_metrics:
            return {
                "cache_type": cache_type.value,
                "message": "No metrics available for this cache type",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        metrics = self._cache_type_metrics[cache_type]
        
        # Calculate metrics
        total_operations = len(metrics["operations"])
        avg_response_time = statistics.mean(metrics["response_times"]) if metrics["response_times"] else 0
        success_rate = sum(metrics["success_rate"]) / len(metrics["success_rate"]) * 100 if metrics["success_rate"] else 0
        
        # Count operations by type
        operation_counts = defaultdict(int)
        for operation in metrics["operations"]:
            operation_counts[operation["operation"]] += 1
        
        return {
            "cache_type": cache_type.value,
            "total_operations": total_operations,
            "avg_response_time_ms": round(avg_response_time, 2),
            "success_rate_percent": round(success_rate, 2),
            "operation_counts": dict(operation_counts),
            "ttl_seconds": get_cache_key_ttl(cache_type),
            "performance_threshold": self._get_performance_threshold("response_time_ms", avg_response_time).value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_historical_metrics(
        self,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics for a specific metric.
        
        Args:
            metric_name: Name of the metric
            hours: Number of hours to look back
            
        Returns:
            List[Dict[str, Any]]: Historical metric data
        """
        if metric_name not in self._metrics_history:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            {
                "timestamp": entry["timestamp"].isoformat(),
                "value": entry["value"]
            }
            for entry in self._metrics_history[metric_name]
            if entry["timestamp"] >= cutoff_time
        ]
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics"""
        self._metrics_history.clear()
        self._cache_type_metrics.clear()
        self._user_metrics.clear()
        logger.info("Cleared all cache metrics")


# Global metrics collector instance
metrics_collector = CacheMetricsCollector()


# Utility functions for cache metrics
async def start_cache_metrics_monitoring() -> Dict[str, Any]:
    """
    Start cache metrics monitoring.
    
    Returns:
        Dict[str, Any]: Monitoring startup results
    """
    try:
        await metrics_collector.start_monitoring()
        
        return {
            "success": True,
            "message": "Cache metrics monitoring started",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting cache metrics monitoring: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def stop_cache_metrics_monitoring() -> Dict[str, Any]:
    """
    Stop cache metrics monitoring.
    
    Returns:
        Dict[str, Any]: Monitoring stop results
    """
    try:
        await metrics_collector.stop_monitoring()
        
        return {
            "success": True,
            "message": "Cache metrics monitoring stopped",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping cache metrics monitoring: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_cache_metrics_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive cache metrics for dashboard display.
    
    Returns:
        Dict[str, Any]: Dashboard metrics
    """
    try:
        performance_summary = metrics_collector.get_cache_performance_summary()
        
        # Add additional dashboard-specific metrics
        dashboard_metrics = {
            "performance_summary": performance_summary,
            "monitoring_status": {
                "is_monitoring": metrics_collector._is_monitoring,
                "metrics_collected": len(metrics_collector._metrics_history),
                "cache_types_tracked": len(metrics_collector._cache_type_metrics),
                "users_tracked": len(metrics_collector._user_metrics)
            },
            "historical_data": {
                "hit_rate_24h": metrics_collector.get_historical_metrics("hit_rate", 24),
                "response_time_24h": metrics_collector.get_historical_metrics("response_time", 24),
                "error_rate_24h": metrics_collector.get_historical_metrics("errors", 24)
            },
            "cache_type_breakdown": {
                cache_type.value: metrics_collector.get_cache_type_metrics(cache_type)
                for cache_type in DashboardCacheType
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return dashboard_metrics
        
    except Exception as e:
        logger.error(f"Error getting cache metrics dashboard: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def record_dashboard_cache_operation(
    operation: str,
    cache_type: DashboardCacheType,
    user_id: Optional[Union[str, UUID]] = None,
    response_time_ms: float = 0.0,
    success: bool = True,
    **kwargs
) -> None:
    """
    Record a dashboard cache operation for metrics tracking.
    
    Args:
        operation: Type of operation (hit, miss, set, delete, error)
        cache_type: Type of cache
        user_id: User identifier (if applicable)
        response_time_ms: Response time in milliseconds
        success: Whether operation was successful
        **kwargs: Additional operation data
    """
    metrics_collector.record_cache_operation(
        operation=operation,
        cache_type=cache_type,
        user_id=user_id,
        response_time_ms=response_time_ms,
        success=success,
        **kwargs
    )


def get_cache_performance_alerts() -> List[Dict[str, Any]]:
    """
    Get cache performance alerts based on current metrics.
    
    Returns:
        List[Dict[str, Any]]: Performance alerts
    """
    alerts = []
    
    try:
        performance_summary = metrics_collector.get_cache_performance_summary()
        overall_performance = performance_summary.get("overall_performance", {})
        performance_thresholds = performance_summary.get("performance_thresholds", {})
        
        # Check hit rate
        hit_rate = overall_performance.get("hit_rate_percent", 0)
        hit_rate_threshold = performance_thresholds.get("hit_rate", "acceptable")
        
        if hit_rate_threshold in ["poor", "critical"]:
            alerts.append({
                "type": "warning",
                "metric": "hit_rate",
                "value": hit_rate,
                "threshold": hit_rate_threshold,
                "message": f"Cache hit rate is {hit_rate:.1f}% ({hit_rate_threshold})",
                "recommendation": "Consider increasing cache TTL or implementing cache warming"
            })
        
        # Check response time
        response_time = overall_performance.get("avg_response_time_ms", 0)
        response_time_threshold = performance_thresholds.get("response_time", "acceptable")
        
        if response_time_threshold in ["poor", "critical"]:
            alerts.append({
                "type": "warning",
                "metric": "response_time",
                "value": response_time,
                "threshold": response_time_threshold,
                "message": f"Cache response time is {response_time:.1f}ms ({response_time_threshold})",
                "recommendation": "Optimize Redis configuration or check network latency"
            })
        
        # Check error rate
        error_rate = overall_performance.get("error_rate_percent", 0)
        error_rate_threshold = performance_thresholds.get("error_rate", "acceptable")
        
        if error_rate_threshold in ["poor", "critical"]:
            alerts.append({
                "type": "error",
                "metric": "error_rate",
                "value": error_rate,
                "threshold": error_rate_threshold,
                "message": f"Cache error rate is {error_rate:.1f}% ({error_rate_threshold})",
                "recommendation": "Investigate Redis connection stability and implement retry mechanisms"
            })
        
        # Add timestamp
        for alert in alerts:
            alert["timestamp"] = datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        logger.error(f"Error getting cache performance alerts: {e}")
        alerts.append({
            "type": "error",
            "message": f"Error generating alerts: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    return alerts
