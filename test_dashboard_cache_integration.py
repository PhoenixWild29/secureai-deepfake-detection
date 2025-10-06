#!/usr/bin/env python3
"""
Dashboard Cache Integration Test Suite
Comprehensive testing for dashboard real-time caching integration with Redis
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import UUID

# Import all caching components
from src.data_layer.cache_manager import cache_manager
from src.dashboard.cache_keys import (
    DashboardCacheType,
    WidgetType,
    get_dashboard_overview_cache_key,
    get_dashboard_analytics_cache_key,
    get_user_preferences_cache_key,
    get_cache_key_ttl
)
from src.dashboard.services import dashboard_service
from src.dashboard.models import (
    CachedDashboardOverviewResponse,
    CachedDashboardAnalyticsResponse,
    CachedUserPreferencesRequest
)
from src.dashboard.cache_invalidation import cache_invalidator, InvalidationTrigger
from src.dashboard.cache_warming import cache_warmer, WarmingPriority
from src.monitoring.cache_metrics import (
    metrics_collector,
    record_dashboard_cache_operation,
    get_cache_performance_alerts
)
from src.integration.detection_cache_integration import detection_cache_integration

# Configure logging
logger = logging.getLogger(__name__)


class DashboardCacheIntegrationTester:
    """
    Comprehensive test suite for dashboard cache integration.
    Tests all components and verifies sub-100ms response times.
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_threshold_ms = 100
        self.test_user_id = str(uuid.uuid4())
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all cache integration tests.
        
        Returns:
            Dict[str, Any]: Comprehensive test results
        """
        logger.info("Starting comprehensive dashboard cache integration tests")
        
        test_suite = {
            "cache_manager_tests": await self._test_cache_manager(),
            "cache_keys_tests": await self._test_cache_keys(),
            "dashboard_services_tests": await self._test_dashboard_services(),
            "dashboard_models_tests": await self._test_dashboard_models(),
            "cache_invalidation_tests": await self._test_cache_invalidation(),
            "cache_warming_tests": await self._test_cache_warming(),
            "cache_metrics_tests": await self._test_cache_metrics(),
            "detection_integration_tests": await self._test_detection_integration(),
            "performance_tests": await self._test_performance(),
            "integration_tests": await self._test_full_integration()
        }
        
        # Calculate overall results
        total_tests = sum(len(tests) for tests in test_suite.values())
        passed_tests = sum(
            sum(1 for test in tests.values() if test.get("passed", False))
            for tests in test_suite.values()
        )
        
        overall_success = passed_tests / total_tests if total_tests > 0 else 0
        
        self.test_results = {
            "overall_results": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": round(overall_success * 100, 2),
                "overall_status": "PASS" if overall_success >= 0.8 else "FAIL"
            },
            "test_suite": test_suite,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Test suite completed: {passed_tests}/{total_tests} tests passed")
        return self.test_results
    
    async def _test_cache_manager(self) -> Dict[str, Dict[str, Any]]:
        """Test cache manager functionality"""
        tests = {}
        
        # Test cache manager initialization
        start_time = time.time()
        try:
            health_check = cache_manager.health_check()
            response_time = (time.time() - start_time) * 1000
            
            tests["cache_manager_init"] = {
                "passed": health_check.get("status") == "healthy",
                "response_time_ms": round(response_time, 2),
                "health_status": health_check.get("status"),
                "meets_performance_target": response_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["cache_manager_init"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test cache operations
        test_key = f"test_key_{int(time.time())}"
        test_data = {"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        # Test cache set
        start_time = time.time()
        try:
            set_success = await cache_manager.set_to_cache_async(
                test_key, test_data, ttl=60, data_type='test'
            )
            set_response_time = (time.time() - start_time) * 1000
            
            tests["cache_set"] = {
                "passed": set_success,
                "response_time_ms": round(set_response_time, 2),
                "meets_performance_target": set_response_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["cache_set"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test cache get
        start_time = time.time()
        try:
            cached_data = await cache_manager.get_from_cache_async(test_key, 'test')
            get_response_time = (time.time() - start_time) * 1000
            
            tests["cache_get"] = {
                "passed": cached_data is not None and cached_data == test_data,
                "response_time_ms": round(get_response_time, 2),
                "meets_performance_target": get_response_time < self.performance_threshold_ms,
                "data_matches": cached_data == test_data
            }
        except Exception as e:
            tests["cache_get"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test cache invalidation
        start_time = time.time()
        try:
            invalidate_success = await cache_manager.invalidate_cache_async(test_key)
            invalidate_response_time = (time.time() - start_time) * 1000
            
            tests["cache_invalidate"] = {
                "passed": invalidate_success,
                "response_time_ms": round(invalidate_response_time, 2),
                "meets_performance_target": invalidate_response_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["cache_invalidate"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_cache_keys(self) -> Dict[str, Dict[str, Any]]:
        """Test cache key generation"""
        tests = {}
        
        # Test overview cache key generation
        start_time = time.time()
        try:
            overview_key = get_dashboard_overview_cache_key(self.test_user_id)
            key_gen_time = (time.time() - start_time) * 1000
            
            tests["overview_cache_key"] = {
                "passed": overview_key.startswith("dash:overview:user:"),
                "response_time_ms": round(key_gen_time, 2),
                "meets_performance_target": key_gen_time < self.performance_threshold_ms,
                "key_format": overview_key
            }
        except Exception as e:
            tests["overview_cache_key"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test analytics cache key generation
        start_time = time.time()
        try:
            analytics_key = get_dashboard_analytics_cache_key(
                self.test_user_id, "30d", {"type": "confidence"}
            )
            key_gen_time = (time.time() - start_time) * 1000
            
            tests["analytics_cache_key"] = {
                "passed": analytics_key.startswith("dash:analytics:"),
                "response_time_ms": round(key_gen_time, 2),
                "meets_performance_target": key_gen_time < self.performance_threshold_ms,
                "key_format": analytics_key
            }
        except Exception as e:
            tests["analytics_cache_key"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test preferences cache key generation
        start_time = time.time()
        try:
            preferences_key = get_user_preferences_cache_key(self.test_user_id)
            key_gen_time = (time.time() - start_time) * 1000
            
            tests["preferences_cache_key"] = {
                "passed": preferences_key.startswith("dash:user_preferences:user:"),
                "response_time_ms": round(key_gen_time, 2),
                "meets_performance_target": key_gen_time < self.performance_threshold_ms,
                "key_format": preferences_key
            }
        except Exception as e:
            tests["preferences_cache_key"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_dashboard_services(self) -> Dict[str, Dict[str, Any]]:
        """Test dashboard services with caching"""
        tests = {}
        
        # Test dashboard overview service
        start_time = time.time()
        try:
            overview_data = await dashboard_service.get_dashboard_overview(self.test_user_id)
            service_response_time = (time.time() - start_time) * 1000
            
            tests["dashboard_overview_service"] = {
                "passed": overview_data is not None,
                "response_time_ms": round(service_response_time, 2),
                "meets_performance_target": service_response_time < self.performance_threshold_ms,
                "data_type": type(overview_data).__name__
            }
        except Exception as e:
            tests["dashboard_overview_service"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test dashboard analytics service
        start_time = time.time()
        try:
            analytics_data = await dashboard_service.get_dashboard_analytics(
                self.test_user_id, "30d"
            )
            service_response_time = (time.time() - start_time) * 1000
            
            tests["dashboard_analytics_service"] = {
                "passed": analytics_data is not None,
                "response_time_ms": round(service_response_time, 2),
                "meets_performance_target": service_response_time < self.performance_threshold_ms,
                "data_type": type(analytics_data).__name__
            }
        except Exception as e:
            tests["dashboard_analytics_service"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test user preferences service
        start_time = time.time()
        try:
            preferences_data = await dashboard_service.get_user_preferences(self.test_user_id)
            service_response_time = (time.time() - start_time) * 1000
            
            tests["user_preferences_service"] = {
                "passed": preferences_data is not None,
                "response_time_ms": round(service_response_time, 2),
                "meets_performance_target": service_response_time < self.performance_threshold_ms,
                "data_type": type(preferences_data).__name__
            }
        except Exception as e:
            tests["user_preferences_service"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_dashboard_models(self) -> Dict[str, Dict[str, Any]]:
        """Test dashboard models with caching methods"""
        tests = {}
        
        # Test cached overview model
        start_time = time.time()
        try:
            overview_model = CachedDashboardOverviewResponse(
                user_summary={"total_analyses": 0, "success_rate": 100.0},
                recent_analyses=[],
                system_status={"overall_status": "healthy", "services": {}},
                quick_stats={"total_detections": 0, "processing_time_avg": 0.0, "accuracy_rate": 100.0},
                notifications=[],
                preferences={}
            )
            
            cache_success = await overview_model.cache_data(self.test_user_id)
            model_response_time = (time.time() - start_time) * 1000
            
            tests["cached_overview_model"] = {
                "passed": cache_success,
                "response_time_ms": round(model_response_time, 2),
                "meets_performance_target": model_response_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["cached_overview_model"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test cached analytics model
        start_time = time.time()
        try:
            analytics_model = CachedDashboardAnalyticsResponse(
                performance_trends={"processing_time_trend": {"data_points": []}},
                usage_metrics={"total_users": 0, "active_users": 0, "analyses_count": 0},
                confidence_distribution={"bins": {}, "statistics": {"mean": 0.0, "median": 0.0, "std_dev": 0.0}},
                processing_metrics={"average_processing_time": 0.0, "throughput": 0.0, "success_rate": 100.0}
            )
            
            cache_success = await analytics_model.cache_data(
                self.test_user_id, "30d"
            )
            model_response_time = (time.time() - start_time) * 1000
            
            tests["cached_analytics_model"] = {
                "passed": cache_success,
                "response_time_ms": round(model_response_time, 2),
                "meets_performance_target": model_response_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["cached_analytics_model"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_cache_invalidation(self) -> Dict[str, Dict[str, Any]]:
        """Test cache invalidation functionality"""
        tests = {}
        
        # Test detection result created invalidation
        start_time = time.time()
        try:
            invalidation_result = await cache_invalidator.on_detection_result_created(
                user_id=self.test_user_id,
                detection_result={"test": "data"}
            )
            invalidation_time = (time.time() - start_time) * 1000
            
            tests["detection_created_invalidation"] = {
                "passed": invalidation_result.get("success", False),
                "response_time_ms": round(invalidation_time, 2),
                "meets_performance_target": invalidation_time < self.performance_threshold_ms,
                "invalidated_count": invalidation_result.get("total_invalidated", 0)
            }
        except Exception as e:
            tests["detection_created_invalidation"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test user analysis completed invalidation
        start_time = time.time()
        try:
            invalidation_result = await cache_invalidator.on_user_analysis_completed(
                user_id=self.test_user_id,
                analysis_data={"test": "data"}
            )
            invalidation_time = (time.time() - start_time) * 1000
            
            tests["user_analysis_invalidation"] = {
                "passed": invalidation_result.get("success", False),
                "response_time_ms": round(invalidation_time, 2),
                "meets_performance_target": invalidation_time < self.performance_threshold_ms,
                "invalidated_count": invalidation_result.get("total_invalidated", 0)
            }
        except Exception as e:
            tests["user_analysis_invalidation"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_cache_warming(self) -> Dict[str, Dict[str, Any]]:
        """Test cache warming functionality"""
        tests = {}
        
        # Test user dashboard warming
        start_time = time.time()
        try:
            warming_result = await cache_warmer.warm_user_dashboard(
                user_id=self.test_user_id,
                priority=WarmingPriority.HIGH
            )
            warming_time = (time.time() - start_time) * 1000
            
            tests["user_dashboard_warming"] = {
                "passed": len(warming_result) > 0,
                "response_time_ms": round(warming_time, 2),
                "meets_performance_target": warming_time < self.performance_threshold_ms,
                "warmed_caches": list(warming_result.keys())
            }
        except Exception as e:
            tests["user_dashboard_warming"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test system status warming
        start_time = time.time()
        try:
            warming_result = await cache_warmer.warm_system_status()
            warming_time = (time.time() - start_time) * 1000
            
            tests["system_status_warming"] = {
                "passed": warming_result.get("status") == "completed",
                "response_time_ms": round(warming_time, 2),
                "meets_performance_target": warming_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["system_status_warming"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_cache_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Test cache metrics monitoring"""
        tests = {}
        
        # Test metrics collection
        start_time = time.time()
        try:
            # Record a test operation
            record_dashboard_cache_operation(
                operation="test_operation",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=self.test_user_id,
                response_time_ms=50.0,
                success=True
            )
            
            performance_summary = metrics_collector.get_cache_performance_summary()
            metrics_time = (time.time() - start_time) * 1000
            
            tests["cache_metrics_collection"] = {
                "passed": performance_summary is not None,
                "response_time_ms": round(metrics_time, 2),
                "meets_performance_target": metrics_time < self.performance_threshold_ms,
                "has_overall_performance": "overall_performance" in performance_summary
            }
        except Exception as e:
            tests["cache_metrics_collection"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test performance alerts
        start_time = time.time()
        try:
            alerts = get_cache_performance_alerts()
            alerts_time = (time.time() - start_time) * 1000
            
            tests["performance_alerts"] = {
                "passed": isinstance(alerts, list),
                "response_time_ms": round(alerts_time, 2),
                "meets_performance_target": alerts_time < self.performance_threshold_ms,
                "alerts_count": len(alerts)
            }
        except Exception as e:
            tests["performance_alerts"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_detection_integration(self) -> Dict[str, Dict[str, Any]]:
        """Test detection cache integration"""
        tests = {}
        
        # Test detection completion integration
        start_time = time.time()
        try:
            await detection_cache_integration.on_detection_completed(
                detection_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                detection_result={"test": "data"},
                processing_time_ms=1000
            )
            integration_time = (time.time() - start_time) * 1000
            
            tests["detection_completion_integration"] = {
                "passed": True,  # If no exception, it passed
                "response_time_ms": round(integration_time, 2),
                "meets_performance_target": integration_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["detection_completion_integration"] = {
                "passed": False,
                "error": str(e)
            }
        
        # Test batch analysis integration
        start_time = time.time()
        try:
            await detection_cache_integration.on_batch_analysis_completed(
                batch_id=str(uuid.uuid4()),
                batch_results=[{"test": "data"}],
                total_processing_time_ms=5000
            )
            integration_time = (time.time() - start_time) * 1000
            
            tests["batch_analysis_integration"] = {
                "passed": True,  # If no exception, it passed
                "response_time_ms": round(integration_time, 2),
                "meets_performance_target": integration_time < self.performance_threshold_ms
            }
        except Exception as e:
            tests["batch_analysis_integration"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    async def _test_performance(self) -> Dict[str, Dict[str, Any]]:
        """Test performance benchmarks"""
        tests = {}
        
        # Test cache hit performance
        test_key = f"perf_test_{int(time.time())}"
        test_data = {"perf": "test", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        # Set test data
        await cache_manager.set_to_cache_async(test_key, test_data, ttl=60)
        
        # Test multiple cache hits
        hit_times = []
        for i in range(10):
            start_time = time.time()
            await cache_manager.get_from_cache_async(test_key, 'test')
            hit_times.append((time.time() - start_time) * 1000)
        
        avg_hit_time = sum(hit_times) / len(hit_times)
        max_hit_time = max(hit_times)
        
        tests["cache_hit_performance"] = {
            "passed": avg_hit_time < self.performance_threshold_ms,
            "avg_response_time_ms": round(avg_hit_time, 2),
            "max_response_time_ms": round(max_hit_time, 2),
            "meets_performance_target": avg_hit_time < self.performance_threshold_ms,
            "hit_times": [round(t, 2) for t in hit_times]
        }
        
        # Test cache miss performance
        miss_times = []
        for i in range(5):
            start_time = time.time()
            await cache_manager.get_from_cache_async(f"miss_test_{i}", 'test')
            miss_times.append((time.time() - start_time) * 1000)
        
        avg_miss_time = sum(miss_times) / len(miss_times)
        
        tests["cache_miss_performance"] = {
            "passed": avg_miss_time < self.performance_threshold_ms,
            "avg_response_time_ms": round(avg_miss_time, 2),
            "meets_performance_target": avg_miss_time < self.performance_threshold_ms,
            "miss_times": [round(t, 2) for t in miss_times]
        }
        
        # Clean up
        await cache_manager.invalidate_cache_async(test_key)
        
        return tests
    
    async def _test_full_integration(self) -> Dict[str, Dict[str, Any]]:
        """Test full end-to-end integration"""
        tests = {}
        
        # Test complete dashboard data flow
        start_time = time.time()
        try:
            # 1. Warm cache
            await cache_warmer.warm_user_dashboard(self.test_user_id)
            
            # 2. Get dashboard data (should be cached)
            overview_data = await dashboard_service.get_dashboard_overview(self.test_user_id)
            
            # 3. Simulate detection completion
            await detection_cache_integration.on_detection_completed(
                detection_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                detection_result={"test": "data"},
                processing_time_ms=1000
            )
            
            # 4. Get updated dashboard data (should be fresh)
            updated_overview = await dashboard_service.get_dashboard_overview(
                self.test_user_id, force_refresh=True
            )
            
            integration_time = (time.time() - start_time) * 1000
            
            tests["full_integration_flow"] = {
                "passed": overview_data is not None and updated_overview is not None,
                "response_time_ms": round(integration_time, 2),
                "meets_performance_target": integration_time < self.performance_threshold_ms * 2,  # Allow more time for full flow
                "overview_data_valid": overview_data is not None,
                "updated_overview_valid": updated_overview is not None
            }
        except Exception as e:
            tests["full_integration_flow"] = {
                "passed": False,
                "error": str(e)
            }
        
        return tests
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get test summary with performance analysis"""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Analyze performance results
        performance_results = []
        for test_category, tests in self.test_results.get("test_suite", {}).items():
            for test_name, test_result in tests.items():
                if "response_time_ms" in test_result:
                    performance_results.append({
                        "category": test_category,
                        "test": test_name,
                        "response_time_ms": test_result["response_time_ms"],
                        "meets_target": test_result.get("meets_performance_target", False)
                    })
        
        # Calculate performance statistics
        response_times = [r["response_time_ms"] for r in performance_results]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        meets_target_count = sum(1 for r in performance_results if r["meets_target"])
        performance_success_rate = meets_target_count / len(performance_results) if performance_results else 0
        
        return {
            "test_summary": self.test_results.get("overall_results", {}),
            "performance_analysis": {
                "total_performance_tests": len(performance_results),
                "avg_response_time_ms": round(avg_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2),
                "performance_success_rate": round(performance_success_rate * 100, 2),
                "meets_sub_100ms_target": performance_success_rate >= 0.8
            },
            "performance_details": performance_results,
            "recommendations": self._get_performance_recommendations(performance_results)
        }
    
    def _get_performance_recommendations(self, performance_results: List[Dict[str, Any]]) -> List[str]:
        """Get performance improvement recommendations"""
        recommendations = []
        
        # Find slow operations
        slow_operations = [r for r in performance_results if r["response_time_ms"] > self.performance_threshold_ms]
        
        if slow_operations:
            recommendations.append(f"Optimize {len(slow_operations)} operations exceeding {self.performance_threshold_ms}ms threshold")
            
            # Group by category
            slow_categories = {}
            for op in slow_operations:
                category = op["category"]
                if category not in slow_categories:
                    slow_categories[category] = []
                slow_categories[category].append(op)
            
            for category, ops in slow_categories.items():
                recommendations.append(f"Focus optimization on {category}: {len(ops)} slow operations")
        
        # Check success rate
        meets_target_count = sum(1 for r in performance_results if r["meets_target"])
        success_rate = meets_target_count / len(performance_results) if performance_results else 0
        
        if success_rate < 0.8:
            recommendations.append(f"Improve performance success rate: currently {success_rate*100:.1f}%, target: 80%")
        
        if not recommendations:
            recommendations.append("Performance meets all targets - no optimization needed")
        
        return recommendations


# Global test instance
cache_integration_tester = DashboardCacheIntegrationTester()


# Utility functions for testing
async def run_cache_integration_tests() -> Dict[str, Any]:
    """
    Run comprehensive cache integration tests.
    
    Returns:
        Dict[str, Any]: Test results
    """
    try:
        logger.info("Starting cache integration tests")
        test_results = await cache_integration_tester.run_all_tests()
        
        logger.info("Cache integration tests completed")
        return test_results
        
    except Exception as e:
        logger.error(f"Error running cache integration tests: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_test_summary() -> Dict[str, Any]:
    """
    Get test summary with performance analysis.
    
    Returns:
        Dict[str, Any]: Test summary
    """
    return cache_integration_tester.get_test_summary()


async def verify_sub_100ms_performance() -> Dict[str, Any]:
    """
    Verify that the caching integration meets sub-100ms performance targets.
    
    Returns:
        Dict[str, Any]: Performance verification results
    """
    try:
        # Run performance-focused tests
        performance_tests = await cache_integration_tester._test_performance()
        
        # Analyze results
        meets_target = True
        slow_operations = []
        
        for test_name, test_result in performance_tests.items():
            if not test_result.get("meets_performance_target", False):
                meets_target = False
                slow_operations.append({
                    "test": test_name,
                    "response_time_ms": test_result.get("response_time_ms", 0)
                })
        
        return {
            "meets_sub_100ms_target": meets_target,
            "performance_tests": performance_tests,
            "slow_operations": slow_operations,
            "recommendations": [
                "Optimize Redis configuration for better performance" if slow_operations else "Performance meets targets",
                "Consider Redis clustering for high-load scenarios" if len(slow_operations) > 2 else "Current setup is adequate"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error verifying sub-100ms performance: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
