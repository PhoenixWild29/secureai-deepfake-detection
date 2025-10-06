#!/usr/bin/env python3
"""
Work Order #36 Implementation Test Suite
Comprehensive testing for Dashboard Analytics API Endpoint with Visualization Support
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Test imports
try:
    from src.models.analytics_data import (
        AnalyticsRequest, AnalyticsResponse, AnalyticsDateRange, DateRangeType,
        AnalyticsFilter, AnalyticsFilterType, DetectionPerformanceMetric,
        UserEngagementMetric, SystemUtilizationMetric, TrendAnalysis,
        PredictiveAnalytics, AnalyticsInsight, TrendDirection, DataClassification,
        ExportFormat, AnalyticsExportRequest, AnalyticsExportResult
    )
    from src.services.analytics_service import AnalyticsService, DataLayerIntegration
    from src.utils.data_exporter import DataExporter
    from src.middleware.auth_middleware import AnalyticsPermissionManager, AnalyticsAuthMiddleware
    from src.config.analytics_config import (
        AnalyticsConfig, AnalyticsThresholds, AnalyticsEndpoints,
        AnalyticsDataSources, AnalyticsPermissions
    )
    from src.api.v1.dashboard.analytics import router
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_SUCCESSFUL = False


class TestAnalyticsDataModels(unittest.TestCase):
    """Test analytics data models"""
    
    def test_analytics_date_range_creation(self):
        """Test AnalyticsDateRange model creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        # Test predefined date range
        date_range = AnalyticsDateRange(type=DateRangeType.LAST_30_DAYS)
        self.assertEqual(date_range.type, DateRangeType.LAST_30_DAYS)
        self.assertIsNone(date_range.start_date)
        self.assertIsNone(date_range.end_date)
        
        # Test custom date range
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=7)
        custom_range = AnalyticsDateRange(
            type=DateRangeType.CUSTOM,
            start_date=start_date,
            end_date=end_date
        )
        self.assertEqual(custom_range.type, DateRangeType.CUSTOM)
        self.assertEqual(custom_range.start_date, start_date)
        self.assertEqual(custom_range.end_date, end_date)
    
    def test_analytics_filter_creation(self):
        """Test AnalyticsFilter model creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        filter_obj = AnalyticsFilter(
            type=AnalyticsFilterType.CONFIDENCE_LEVEL,
            value=0.8,
            operator="gte"
        )
        self.assertEqual(filter_obj.type, AnalyticsFilterType.CONFIDENCE_LEVEL)
        self.assertEqual(filter_obj.value, 0.8)
        self.assertEqual(filter_obj.operator, "gte")
    
    def test_analytics_request_creation(self):
        """Test AnalyticsRequest model creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        date_range = AnalyticsDateRange(type=DateRangeType.LAST_7_DAYS)
        request = AnalyticsRequest(
            date_range=date_range,
            include_trends=True,
            include_predictions=False,
            limit=100
        )
        self.assertEqual(request.date_range.type, DateRangeType.LAST_7_DAYS)
        self.assertTrue(request.include_trends)
        self.assertFalse(request.include_predictions)
        self.assertEqual(request.limit, 100)
    
    def test_detection_performance_metric(self):
        """Test DetectionPerformanceMetric model"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        metric = DetectionPerformanceMetric(
            metric_name="accuracy_rate",
            value=Decimal("94.5"),
            unit="percent",
            timestamp=datetime.now(timezone.utc),
            confidence_interval={"lower": Decimal("93.0"), "upper": Decimal("96.0")},
            metadata={"model_version": "v2.1"}
        )
        self.assertEqual(metric.metric_name, "accuracy_rate")
        self.assertEqual(metric.value, Decimal("94.5"))
        self.assertEqual(metric.unit, "percent")
        self.assertIsNotNone(metric.timestamp)
        self.assertIsNotNone(metric.confidence_interval)
        self.assertIsNotNone(metric.metadata)
    
    def test_trend_analysis_creation(self):
        """Test TrendAnalysis model creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        trend = TrendAnalysis(
            metric_name="accuracy_rate",
            trend_direction=TrendDirection.INCREASING,
            change_percentage=Decimal("2.5"),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=30),
            data_points=[Decimal("92.0"), Decimal("93.5"), Decimal("94.5")]
        )
        self.assertEqual(trend.metric_name, "accuracy_rate")
        self.assertEqual(trend.trend_direction, TrendDirection.INCREASING)
        self.assertEqual(trend.change_percentage, Decimal("2.5"))
        self.assertIsNotNone(trend.data_points)


class TestAnalyticsService(unittest.TestCase):
    """Test analytics service functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        self.service = AnalyticsService()
    
    @patch('src.services.analytics_service.get_dashboard_cache_manager')
    def test_service_initialization(self, mock_cache):
        """Test analytics service initialization"""
        mock_cache.return_value = AsyncMock()
        service = AnalyticsService()
        self.assertIsNotNone(service)
        self.assertIsNotNone(service.data_layer)
    
    @patch('src.services.analytics_service.get_dashboard_cache_manager')
    async def test_get_analytics_data(self, mock_cache):
        """Test getting analytics data"""
        mock_cache.return_value = AsyncMock()
        
        date_range = AnalyticsDateRange(type=DateRangeType.LAST_7_DAYS)
        request = AnalyticsRequest(
            date_range=date_range,
            include_trends=True,
            include_predictions=False
        )
        
        # Mock the data layer methods
        with patch.object(self.service.data_layer, 'get_detection_performance_data') as mock_detection, \
             patch.object(self.service.data_layer, 'get_user_engagement_data') as mock_engagement, \
             patch.object(self.service.data_layer, 'get_system_utilization_data') as mock_utilization:
            
            # Setup mock returns
            mock_detection.return_value = [
                DetectionPerformanceMetric(
                    metric_name="accuracy_rate",
                    value=Decimal("94.5"),
                    unit="percent",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
            mock_engagement.return_value = []
            mock_utilization.return_value = []
            
            # Test the method
            result = await self.service.get_analytics_data(request, "test_user")
            
            self.assertIsInstance(result, AnalyticsResponse)
            self.assertGreater(len(result.detection_performance), 0)
            self.assertEqual(result.data_classification, DataClassification.INTERNAL)


class TestDataExporter(unittest.TestCase):
    """Test data export functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        self.exporter = DataExporter("test_exports")
    
    def test_exporter_initialization(self):
        """Test data exporter initialization"""
        self.assertIsNotNone(self.exporter)
        self.assertEqual(self.exporter.export_directory.name, "test_exports")
        self.assertIsNotNone(self.exporter.stats)
    
    def test_export_statistics(self):
        """Test export statistics tracking"""
        stats = self.exporter.get_export_statistics()
        self.assertIn('total_exports', stats)
        self.assertIn('successful_exports', stats)
        self.assertIn('failed_exports', stats)
        self.assertIn('success_rate', stats)
    
    def test_file_checksum_calculation(self):
        """Test file checksum calculation"""
        import tempfile
        import os
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content for checksum")
            temp_file_path = temp_file.name
        
        try:
            # Test checksum calculation
            checksum = self.exporter._calculate_file_checksum(temp_file_path)
            self.assertIsNotNone(checksum)
            self.assertEqual(len(checksum), 64)  # SHA-256 hex length
        finally:
            # Clean up
            os.unlink(temp_file_path)


class TestAnalyticsPermissionManager(unittest.TestCase):
    """Test analytics permission management"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        self.permission_manager = AnalyticsPermissionManager()
    
    def test_permission_manager_initialization(self):
        """Test permission manager initialization"""
        self.assertIsNotNone(self.permission_manager)
        self.assertIsNotNone(self.permission_manager.role_permissions)
        self.assertIsNotNone(self.permission_manager.resource_permissions)
    
    def test_role_permissions_structure(self):
        """Test role permissions structure"""
        expected_roles = ["admin", "analyst", "viewer", "system_admin"]
        for role in expected_roles:
            self.assertIn(role, self.permission_manager.role_permissions)
            self.assertIn("read", self.permission_manager.role_permissions[role])
    
    def test_resource_permissions_structure(self):
        """Test resource permissions structure"""
        expected_resources = [
            "detection_performance",
            "user_engagement",
            "system_utilization",
            "blockchain_metrics"
        ]
        for resource in expected_resources:
            self.assertIn(resource, self.permission_manager.resource_permissions)
    
    def test_data_access_level_determination(self):
        """Test data access level determination"""
        # Mock user claims
        mock_user_claims = Mock()
        mock_user_claims.roles = ["admin"]
        mock_user_claims.groups = []
        
        access_level = self.permission_manager.get_user_data_access_level(mock_user_claims)
        self.assertEqual(access_level, DataClassification.CONFIDENTIAL)
        
        # Test unauthenticated user
        access_level_unauth = self.permission_manager.get_user_data_access_level(None)
        self.assertEqual(access_level_unauth, DataClassification.PUBLIC)


class TestAnalyticsConfiguration(unittest.TestCase):
    """Test analytics configuration"""
    
    def test_analytics_config_creation(self):
        """Test analytics configuration creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        config = AnalyticsConfig()
        self.assertIsNotNone(config)
        self.assertTrue(config.analytics_enabled)
        self.assertEqual(config.analytics_version, "1.0.0")
        self.assertTrue(config.cache_enabled)
    
    def test_analytics_thresholds(self):
        """Test analytics thresholds"""
        thresholds = AnalyticsThresholds()
        self.assertIsNotNone(thresholds)
        self.assertGreater(thresholds.MAX_QUERY_EXECUTION_TIME_MS, 0)
        self.assertGreater(thresholds.MIN_CONFIDENCE_SCORE, 0)
        self.assertLessEqual(thresholds.MIN_CONFIDENCE_SCORE, 1.0)
    
    def test_analytics_endpoints(self):
        """Test analytics endpoints configuration"""
        endpoints = AnalyticsEndpoints()
        self.assertIsNotNone(endpoints)
        self.assertTrue(endpoints.ANALYTICS_BASE_PATH.startswith("/api/v1/dashboard/analytics"))
        self.assertIn("json", endpoints.SUPPORTED_RESPONSE_FORMATS)
        self.assertGreater(endpoints.DEFAULT_PAGE_SIZE, 0)
    
    def test_analytics_data_sources(self):
        """Test analytics data sources configuration"""
        data_sources = AnalyticsDataSources()
        self.assertIsNotNone(data_sources)
        self.assertIsNotNone(data_sources.DETECTION_PERFORMANCE_SOURCE)
        self.assertGreater(data_sources.DETECTION_PERFORMANCE_REFRESH, 0)
    
    def test_analytics_permissions(self):
        """Test analytics permissions configuration"""
        permissions = AnalyticsPermissions()
        self.assertIsNotNone(permissions)
        self.assertIn("admin", permissions.ROLE_HIERARCHY)
        self.assertIn("analyst", permissions.ROLE_HIERARCHY)
        self.assertIn("viewer", permissions.ROLE_HIERARCHY)


class TestAnalyticsAPIEndpoints(unittest.TestCase):
    """Test analytics API endpoints"""
    
    def test_router_creation(self):
        """Test analytics router creation"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        self.assertIsNotNone(router)
        self.assertEqual(router.prefix, "/analytics")
        self.assertIn("analytics", router.tags)
    
    def test_router_responses(self):
        """Test router response definitions"""
        self.assertIn(404, router.responses)
        self.assertIn(403, router.responses)
        self.assertIn(500, router.responses)
        self.assertEqual(router.responses[404]["description"], "Not found")
        self.assertEqual(router.responses[403]["description"], "Forbidden")


class TestWorkOrder36Integration(unittest.TestCase):
    """Integration tests for Work Order #36"""
    
    def test_analytics_models_integration(self):
        """Test integration between analytics models"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        # Create a complete analytics request
        date_range = AnalyticsDateRange(type=DateRangeType.LAST_30_DAYS)
        filters = [
            AnalyticsFilter(
                type=AnalyticsFilterType.CONFIDENCE_LEVEL,
                value=0.8,
                operator="gte"
            )
        ]
        
        request = AnalyticsRequest(
            date_range=date_range,
            filters=filters,
            include_trends=True,
            include_predictions=True,
            export_format=ExportFormat.CSV
        )
        
        # Verify request structure
        self.assertEqual(request.date_range.type, DateRangeType.LAST_30_DAYS)
        self.assertEqual(len(request.filters), 1)
        self.assertTrue(request.include_trends)
        self.assertTrue(request.include_predictions)
        self.assertEqual(request.export_format, ExportFormat.CSV)
    
    def test_export_workflow(self):
        """Test export workflow integration"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        # Create mock analytics data
        detection_metric = DetectionPerformanceMetric(
            metric_name="accuracy_rate",
            value=Decimal("94.5"),
            unit="percent",
            timestamp=datetime.now(timezone.utc)
        )
        
        response = AnalyticsResponse(
            detection_performance=[detection_metric],
            user_engagement=[],
            system_utilization=[],
            total_records=1,
            date_range=AnalyticsDateRange(type=DateRangeType.LAST_7_DAYS),
            filters_applied=[],
            data_classification=DataClassification.INTERNAL,
            query_execution_time_ms=100.0,
            data_freshness_minutes=5
        )
        
        # Create export request
        export_request = AnalyticsExportRequest(
            export_format=ExportFormat.JSON,
            data_classification=DataClassification.INTERNAL
        )
        
        # Verify structures are compatible
        self.assertEqual(len(response.detection_performance), 1)
        self.assertEqual(export_request.export_format, ExportFormat.JSON)
        self.assertEqual(response.data_classification, export_request.data_classification)
    
    def test_permission_workflow(self):
        """Test permission workflow integration"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Imports not successful")
        
        permission_manager = AnalyticsPermissionManager()
        
        # Mock user claims
        mock_user_claims = Mock()
        mock_user_claims.user_id = "test_user"
        mock_user_claims.roles = ["analyst"]
        mock_user_claims.groups = []
        
        # Test permission check
        has_permission = permission_manager.check_permission(
            mock_user_claims,
            "read",
            "detection_performance",
            DataClassification.INTERNAL
        )
        
        # Should have permission for internal data as analyst
        self.assertTrue(has_permission)
        
        # Test data access level
        access_level = permission_manager.get_user_data_access_level(mock_user_claims)
        self.assertEqual(access_level, DataClassification.INTERNAL)


def run_work_order_36_tests():
    """Run all Work Order #36 tests"""
    print("=" * 80)
    print("WORK ORDER #36 IMPLEMENTATION TEST SUITE")
    print("Dashboard Analytics API Endpoint with Visualization Support")
    print("=" * 80)
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ CRITICAL: Import errors detected!")
        print("   Some required modules could not be imported.")
        print("   This may indicate missing dependencies or incorrect file paths.")
        return False
    
    print("✅ All imports successful")
    print()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAnalyticsDataModels,
        TestAnalyticsService,
        TestDataExporter,
        TestAnalyticsPermissionManager,
        TestAnalyticsConfiguration,
        TestAnalyticsAPIEndpoints,
        TestWorkOrder36Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"⏭️  Skipped: {skipped}")
    
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Print detailed results
    if failures > 0:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Overall assessment
    print("\n" + "=" * 80)
    print("OVERALL ASSESSMENT")
    print("=" * 80)
    
    if failures == 0 and errors == 0:
        print("🎉 WORK ORDER #36 IMPLEMENTATION: PASSED")
        print("   All core functionality is working correctly!")
        print("   The Dashboard Analytics API Endpoint is ready for deployment.")
        return True
    else:
        print("⚠️  WORK ORDER #36 IMPLEMENTATION: NEEDS ATTENTION")
        print(f"   {failures} failures and {errors} errors need to be addressed.")
        print("   Please review the test results above.")
        return False


if __name__ == "__main__":
    success = run_work_order_36_tests()
    sys.exit(0 if success else 1)
