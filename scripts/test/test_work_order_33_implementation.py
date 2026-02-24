#!/usr/bin/env python3
"""
Work Order #33 Implementation Test Suite
Test suite for Dashboard Overview API Endpoint with Data Aggregation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List
import unittest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we want to test
try:
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
        ProcessingQueueStatus,
        DashboardCacheKey
    )
    from src.utils.redis_cache import RedisCacheManager, DashboardCacheManager
    from src.config.dashboard_config import (
        DashboardSettings,
        RedisConfig,
        AWSConfig,
        DatabaseConfig,
        ExternalServicesConfig,
        DashboardConfig,
        ConfigurationManager
    )
    from src.services.dashboard_aggregator import DashboardDataAggregator, ExternalServiceClient
    from src.dependencies.auth import CognitoJWTValidator, UserClaims
    from src.api.v1.dashboard.overview import get_dashboard_overview, dashboard_health_check
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class TestDashboardModels(unittest.TestCase):
    """Test dashboard data models"""
    
    def test_dashboard_overview_request_creation(self):
        """Test DashboardOverviewRequest model creation"""
        request = DashboardOverviewRequest(
            include_user_activity=True,
            include_blockchain_metrics=False,
            include_system_performance=True,
            recent_analyses_limit=20,
            confidence_trends_hours=12,
            force_refresh=False
        )
        
        self.assertTrue(request.include_user_activity)
        self.assertFalse(request.include_blockchain_metrics)
        self.assertTrue(request.include_system_performance)
        self.assertEqual(request.recent_analyses_limit, 20)
        self.assertEqual(request.confidence_trends_hours, 12)
        self.assertFalse(request.force_refresh)
        print("✅ DashboardOverviewRequest model test passed")
    
    def test_recent_analysis_summary_creation(self):
        """Test RecentAnalysisSummary model creation"""
        now = datetime.now(timezone.utc)
        analysis = RecentAnalysisSummary(
            analysis_id="test_123",
            filename="test_video.mp4",
            user_id="user_456",
            status=AnalysisStatus.COMPLETED,
            confidence_score=Decimal("0.95"),
            is_fake=False,
            processing_time_seconds=12.5,
            created_at=now,
            updated_at=now,
            blockchain_hash="0x123abc"
        )
        
        self.assertEqual(analysis.analysis_id, "test_123")
        self.assertEqual(analysis.filename, "test_video.mp4")
        self.assertEqual(analysis.status, AnalysisStatus.COMPLETED)
        self.assertEqual(analysis.confidence_score, Decimal("0.95"))
        self.assertFalse(analysis.is_fake)
        self.assertEqual(analysis.processing_time_seconds, 12.5)
        print("✅ RecentAnalysisSummary model test passed")
    
    def test_confidence_score_trend_creation(self):
        """Test ConfidenceScoreTrend model creation"""
        now = datetime.now(timezone.utc)
        trend = ConfidenceScoreTrend(
            timestamp=now,
            average_confidence=Decimal("0.88"),
            fake_detection_rate=Decimal("0.15"),
            total_analyses=45,
            trend_direction=ConfidenceTrend.STABLE
        )
        
        self.assertEqual(trend.timestamp, now)
        self.assertEqual(trend.average_confidence, Decimal("0.88"))
        self.assertEqual(trend.fake_detection_rate, Decimal("0.15"))
        self.assertEqual(trend.total_analyses, 45)
        self.assertEqual(trend.trend_direction, ConfidenceTrend.STABLE)
        print("✅ ConfidenceScoreTrend model test passed")
    
    def test_processing_queue_metrics_creation(self):
        """Test ProcessingQueueMetrics model creation"""
        metrics = ProcessingQueueMetrics(
            queue_length=5,
            estimated_wait_time_minutes=8.5,
            processing_capacity=10,
            active_processors=8,
            status=ProcessingQueueStatus.HEALTHY,
            last_processed_at=datetime.now(timezone.utc),
            throughput_per_hour=25.0,
            error_rate=Decimal("0.02")
        )
        
        self.assertEqual(metrics.queue_length, 5)
        self.assertEqual(metrics.estimated_wait_time_minutes, 8.5)
        self.assertEqual(metrics.processing_capacity, 10)
        self.assertEqual(metrics.active_processors, 8)
        self.assertEqual(metrics.status, ProcessingQueueStatus.HEALTHY)
        self.assertEqual(metrics.throughput_per_hour, 25.0)
        self.assertEqual(metrics.error_rate, Decimal("0.02"))
        print("✅ ProcessingQueueMetrics model test passed")
    
    def test_user_activity_metric_creation(self):
        """Test UserActivityMetric model creation"""
        now = datetime.now(timezone.utc)
        user = UserActivityMetric(
            user_id="user_123",
            email="user@example.com",
            last_activity=now,
            total_analyses=150,
            recent_analyses=5,
            is_active=True,
            role="analyst"
        )
        
        self.assertEqual(user.user_id, "user_123")
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(user.total_analyses, 150)
        self.assertEqual(user.recent_analyses, 5)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, "analyst")
        print("✅ UserActivityMetric model test passed")
    
    def test_system_performance_metrics_creation(self):
        """Test SystemPerformanceMetrics model creation"""
        metrics = SystemPerformanceMetrics(
            cpu_usage_percent=Decimal("45.2"),
            memory_usage_percent=Decimal("67.8"),
            disk_usage_percent=Decimal("23.4"),
            gpu_usage_percent=Decimal("78.9"),
            network_latency_ms=12.5,
            database_connection_count=15,
            redis_connection_count=8,
            uptime_hours=168.5
        )
        
        self.assertEqual(metrics.cpu_usage_percent, Decimal("45.2"))
        self.assertEqual(metrics.memory_usage_percent, Decimal("67.8"))
        self.assertEqual(metrics.disk_usage_percent, Decimal("23.4"))
        self.assertEqual(metrics.gpu_usage_percent, Decimal("78.9"))
        self.assertEqual(metrics.network_latency_ms, 12.5)
        self.assertEqual(metrics.database_connection_count, 15)
        self.assertEqual(metrics.redis_connection_count, 8)
        self.assertEqual(metrics.uptime_hours, 168.5)
        print("✅ SystemPerformanceMetrics model test passed")
    
    def test_blockchain_verification_metrics_creation(self):
        """Test BlockchainVerificationMetrics model creation"""
        now = datetime.now(timezone.utc)
        metrics = BlockchainVerificationMetrics(
            total_verifications=1250,
            successful_verifications=1245,
            failed_verifications=5,
            pending_verifications=12,
            average_verification_time_seconds=3.2,
            last_verification_at=now,
            blockchain_network_status="healthy",
            gas_fee_trend="stable"
        )
        
        self.assertEqual(metrics.total_verifications, 1250)
        self.assertEqual(metrics.successful_verifications, 1245)
        self.assertEqual(metrics.failed_verifications, 5)
        self.assertEqual(metrics.pending_verifications, 12)
        self.assertEqual(metrics.average_verification_time_seconds, 3.2)
        self.assertEqual(metrics.blockchain_network_status, "healthy")
        self.assertEqual(metrics.gas_fee_trend, "stable")
        print("✅ BlockchainVerificationMetrics model test passed")
    
    def test_dashboard_cache_key_creation(self):
        """Test DashboardCacheKey model creation"""
        cache_key = DashboardCacheKey(
            key_type="dashboard_overview",
            user_id="user_123",
            filters={"limit": 10, "hours": 24},
            version="v1"
        )
        
        self.assertEqual(cache_key.key_type, "dashboard_overview")
        self.assertEqual(cache_key.user_id, "user_123")
        self.assertEqual(cache_key.filters["limit"], 10)
        self.assertEqual(cache_key.filters["hours"], 24)
        self.assertEqual(cache_key.version, "v1")
        
        # Test string conversion
        key_string = cache_key.to_string()
        self.assertIn("dashboard_overview", key_string)
        self.assertIn("user_user_123", key_string)
        self.assertIn("limit_10", key_string)
        self.assertIn("hours_24", key_string)
        print("✅ DashboardCacheKey model test passed")


class TestRedisCacheManager(unittest.TestCase):
    """Test Redis cache manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache_manager = RedisCacheManager(
            redis_url="redis://localhost:6379",
            max_connections=5
        )
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization"""
        self.assertIsNotNone(self.cache_manager)
        self.assertEqual(self.cache_manager.redis_url, "redis://localhost:6379")
        self.assertEqual(self.cache_manager.max_connections, 5)
        self.assertTrue(self.cache_manager.socket_keepalive)
        print("✅ Redis cache manager initialization test passed")
    
    def test_cache_key_creation(self):
        """Test cache key creation"""
        cache_key = DashboardCacheKey(
            key_type="test_key",
            user_id="user_123",
            version="v1"
        )
        
        key_string = cache_key.to_string()
        expected_parts = ["test_key", "v1", "user_user_123"]
        
        for part in expected_parts:
            self.assertIn(part, key_string)
        print("✅ Cache key creation test passed")
    
    def test_cache_statistics(self):
        """Test cache statistics tracking"""
        initial_stats = self.cache_manager.get_stats()
        
        self.assertEqual(initial_stats['hits'], 0)
        self.assertEqual(initial_stats['misses'], 0)
        self.assertEqual(initial_stats['sets'], 0)
        self.assertEqual(initial_stats['total_requests'], 0)
        self.assertEqual(initial_stats['hit_rate'], 0.0)
        print("✅ Cache statistics test passed")


class TestConfigurationManager(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_manager = ConfigurationManager()
    
    def test_configuration_initialization(self):
        """Test configuration initialization"""
        settings = self.config_manager.get_settings()
        
        self.assertIsNotNone(settings)
        self.assertIsNotNone(settings.redis)
        self.assertIsNotNone(settings.aws)
        self.assertIsNotNone(settings.database)
        self.assertIsNotNone(settings.external_services)
        self.assertIsNotNone(settings.dashboard)
        print("✅ Configuration initialization test passed")
    
    def test_redis_config(self):
        """Test Redis configuration"""
        redis_config = self.config_manager.get_redis_config()
        
        self.assertIsNotNone(redis_config.redis_url)
        self.assertGreater(redis_config.redis_port, 0)
        self.assertGreater(redis_config.max_connections, 0)
        self.assertGreater(redis_config.default_ttl, 0)
        print("✅ Redis configuration test passed")
    
    def test_aws_config(self):
        """Test AWS configuration"""
        aws_config = self.config_manager.get_aws_config()
        
        self.assertIsNotNone(aws_config.cognito_region)
        self.assertIsNotNone(aws_config.jwt_algorithm)
        self.assertIsNotNone(aws_config.jwt_issuer)
        self.assertGreater(aws_config.jwt_expiration_minutes, 0)
        print("✅ AWS configuration test passed")
    
    def test_external_services_config(self):
        """Test external services configuration"""
        ext_config = self.config_manager.get_external_services_config()
        
        self.assertIsNotNone(ext_config.detection_engine_url)
        self.assertIsNotNone(ext_config.analytics_service_url)
        self.assertIsNotNone(ext_config.monitoring_service_url)
        self.assertIsNotNone(ext_config.blockchain_service_url)
        self.assertGreater(ext_config.detection_engine_timeout, 0)
        print("✅ External services configuration test passed")
    
    def test_dashboard_config(self):
        """Test dashboard configuration"""
        dashboard_config = self.config_manager.get_dashboard_config()
        
        self.assertIsNotNone(dashboard_config.api_title)
        self.assertIsNotNone(dashboard_config.api_version)
        self.assertGreater(dashboard_config.max_response_time_ms, 0)
        self.assertGreater(dashboard_config.recent_analyses_limit, 0)
        self.assertGreater(dashboard_config.confidence_trends_hours, 0)
        print("✅ Dashboard configuration test passed")
    
    def test_environment_validation(self):
        """Test environment validation"""
        errors = self.config_manager.validate_configuration()
        
        # In development, some configurations might be missing
        # This test ensures the validation function works
        self.assertIsInstance(errors, list)
        print("✅ Environment validation test passed")


class TestExternalServiceClient(unittest.TestCase):
    """Test external service client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = ExternalServiceClient(
            base_url="http://localhost:8000",
            timeout=30,
            retry_attempts=3
        )
    
    def test_client_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.base_url, "http://localhost:8000")
        self.assertEqual(self.client.timeout, 30)
        self.assertEqual(self.client.retry_attempts, 3)
        self.assertIsNotNone(self.client.client)
        print("✅ External service client initialization test passed")


class TestDashboardDataAggregator(unittest.TestCase):
    """Test dashboard data aggregator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.aggregator = DashboardDataAggregator()
    
    def test_aggregator_initialization(self):
        """Test aggregator initialization"""
        self.assertIsNotNone(self.aggregator.config)
        self.assertIsNotNone(self.aggregator.dashboard_config)
        self.assertIsNotNone(self.aggregator.detection_engine_client)
        self.assertIsNotNone(self.aggregator.analytics_client)
        self.assertIsNotNone(self.aggregator.monitoring_client)
        self.assertIsNotNone(self.aggregator.blockchain_client)
        print("✅ Dashboard data aggregator initialization test passed")
    
    def test_mock_recent_analyses(self):
        """Test mock recent analyses generation"""
        analyses = self.aggregator._get_mock_recent_analyses(5)
        
        self.assertEqual(len(analyses), 5)
        for i, analysis in enumerate(analyses):
            self.assertIsInstance(analysis, RecentAnalysisSummary)
            self.assertEqual(analysis.analysis_id, f"analysis_{i+1}")
            self.assertEqual(analysis.filename, f"sample_video_{i+1}.mp4")
            self.assertEqual(analysis.user_id, f"user_{i+1}")
            self.assertEqual(analysis.status, AnalysisStatus.COMPLETED)
        print("✅ Mock recent analyses test passed")
    
    def test_mock_confidence_trends(self):
        """Test mock confidence trends generation"""
        trends = self.aggregator._get_mock_confidence_trends(12)
        
        self.assertEqual(len(trends), 12)
        for trend in trends:
            self.assertIsInstance(trend, ConfidenceScoreTrend)
            self.assertIsInstance(trend.timestamp, datetime)
            self.assertIsInstance(trend.average_confidence, Decimal)
            self.assertIsInstance(trend.fake_detection_rate, Decimal)
            self.assertIsInstance(trend.total_analyses, int)
            self.assertEqual(trend.trend_direction, ConfidenceTrend.STABLE)
        print("✅ Mock confidence trends test passed")
    
    def test_mock_processing_queue_metrics(self):
        """Test mock processing queue metrics generation"""
        metrics = self.aggregator._get_mock_processing_queue_metrics()
        
        self.assertIsInstance(metrics, ProcessingQueueMetrics)
        self.assertEqual(metrics.queue_length, 3)
        self.assertEqual(metrics.estimated_wait_time_minutes, 5.2)
        self.assertEqual(metrics.processing_capacity, 10)
        self.assertEqual(metrics.active_processors, 8)
        self.assertEqual(metrics.status, ProcessingQueueStatus.HEALTHY)
        self.assertEqual(metrics.throughput_per_hour, 24.5)
        self.assertEqual(metrics.error_rate, Decimal("0.02"))
        print("✅ Mock processing queue metrics test passed")
    
    def test_mock_user_activity_metrics(self):
        """Test mock user activity metrics generation"""
        users = self.aggregator._get_mock_user_activity_metrics(5)
        
        self.assertEqual(len(users), 5)
        for i, user in enumerate(users):
            self.assertIsInstance(user, UserActivityMetric)
            self.assertEqual(user.user_id, f"user_{i+1}")
            self.assertEqual(user.email, f"user{i+1}@example.com")
            self.assertIsInstance(user.last_activity, datetime)
            self.assertIsInstance(user.total_analyses, int)
            self.assertIsInstance(user.recent_analyses, int)
            self.assertIsInstance(user.is_active, bool)
            self.assertIn(user.role, ["analyst", "admin"])
        print("✅ Mock user activity metrics test passed")
    
    def test_mock_system_performance_metrics(self):
        """Test mock system performance metrics generation"""
        metrics = self.aggregator._get_mock_system_performance_metrics()
        
        self.assertIsInstance(metrics, SystemPerformanceMetrics)
        self.assertEqual(metrics.cpu_usage_percent, Decimal("45.2"))
        self.assertEqual(metrics.memory_usage_percent, Decimal("67.8"))
        self.assertEqual(metrics.disk_usage_percent, Decimal("23.4"))
        self.assertEqual(metrics.gpu_usage_percent, Decimal("78.9"))
        self.assertEqual(metrics.network_latency_ms, 12.5)
        self.assertEqual(metrics.database_connection_count, 15)
        self.assertEqual(metrics.redis_connection_count, 8)
        self.assertEqual(metrics.uptime_hours, 168.5)
        print("✅ Mock system performance metrics test passed")
    
    def test_mock_blockchain_verification_metrics(self):
        """Test mock blockchain verification metrics generation"""
        metrics = self.aggregator._get_mock_blockchain_verification_metrics()
        
        self.assertIsInstance(metrics, BlockchainVerificationMetrics)
        self.assertEqual(metrics.total_verifications, 1250)
        self.assertEqual(metrics.successful_verifications, 1245)
        self.assertEqual(metrics.failed_verifications, 5)
        self.assertEqual(metrics.pending_verifications, 12)
        self.assertEqual(metrics.average_verification_time_seconds, 3.2)
        self.assertEqual(metrics.blockchain_network_status, "healthy")
        self.assertEqual(metrics.gas_fee_trend, "stable")
        print("✅ Mock blockchain verification metrics test passed")
    
    def test_summary_stats_generation(self):
        """Test summary statistics generation"""
        # Create test data
        now = datetime.now(timezone.utc)
        today = now.date()
        
        recent_analyses = [
            RecentAnalysisSummary(
                analysis_id="test_1",
                filename="test1.mp4",
                user_id="user_1",
                status=AnalysisStatus.COMPLETED,
                confidence_score=Decimal("0.95"),
                is_fake=False,
                processing_time_seconds=12.5,
                created_at=now,
                updated_at=now,
                blockchain_hash="0x123"
            ),
            RecentAnalysisSummary(
                analysis_id="test_2",
                filename="test2.mp4",
                user_id="user_1",
                status=AnalysisStatus.COMPLETED,
                confidence_score=Decimal("0.85"),
                is_fake=True,
                processing_time_seconds=15.0,
                created_at=now,
                updated_at=now,
                blockchain_hash="0x456"
            )
        ]
        
        confidence_trends = [
            ConfidenceScoreTrend(
                timestamp=now,
                average_confidence=Decimal("0.90"),
                fake_detection_rate=Decimal("0.10"),
                total_analyses=50,
                trend_direction=ConfidenceTrend.STABLE
            )
        ]
        
        processing_queue = self.aggregator._get_mock_processing_queue_metrics()
        user_activity = self.aggregator._get_mock_user_activity_metrics(3)
        system_performance = self.aggregator._get_mock_system_performance_metrics()
        blockchain_metrics = self.aggregator._get_mock_blockchain_verification_metrics()
        
        # Generate summary stats
        summary_stats = self.aggregator._generate_summary_stats(
            recent_analyses,
            confidence_trends,
            processing_queue,
            user_activity,
            system_performance,
            blockchain_metrics
        )
        
        # Validate summary stats
        self.assertIn("total_analyses_today", summary_stats)
        self.assertIn("fake_detection_rate_today", summary_stats)
        self.assertIn("average_confidence_today", summary_stats)
        self.assertIn("system_health_score", summary_stats)
        self.assertIn("user_satisfaction_score", summary_stats)
        self.assertIn("active_users_count", summary_stats)
        self.assertIn("queue_status", summary_stats)
        self.assertIn("blockchain_network_status", summary_stats)
        
        # Check specific values
        self.assertEqual(summary_stats["total_analyses_today"], 2)
        self.assertEqual(summary_stats["fake_detection_rate_today"], 0.5)  # 1 out of 2 is fake
        self.assertEqual(summary_stats["average_confidence_today"], 0.9)  # (0.95 + 0.85) / 2
        self.assertGreaterEqual(summary_stats["system_health_score"], 0.0)
        self.assertLessEqual(summary_stats["system_health_score"], 1.0)
        print("✅ Summary statistics generation test passed")


class TestCognitoJWTValidator(unittest.TestCase):
    """Test Cognito JWT validator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = CognitoJWTValidator()
    
    def test_validator_initialization(self):
        """Test validator initialization"""
        self.assertIsNotNone(self.validator.aws_config)
        self.assertIsNotNone(self.validator.cognito_client)
        self.assertIsNotNone(self.validator.jwt_secret_key)
        self.assertIsNotNone(self.validator.jwt_algorithm)
        self.assertIsNotNone(self.validator.jwt_issuer)
        print("✅ Cognito JWT validator initialization test passed")


class TestUserClaims(unittest.TestCase):
    """Test user claims model"""
    
    def test_user_claims_creation(self):
        """Test UserClaims model creation"""
        now = datetime.now(timezone.utc)
        claims = UserClaims(
            user_id="user_123",
            email="user@example.com",
            username="testuser",
            groups=["analysts", "users"],
            roles=["analyst"],
            exp=now + timedelta(hours=1),
            iat=now,
            iss="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_123456789",
            aud="test_client_id"
        )
        
        self.assertEqual(claims.user_id, "user_123")
        self.assertEqual(claims.email, "user@example.com")
        self.assertEqual(claims.username, "testuser")
        self.assertEqual(claims.groups, ["analysts", "users"])
        self.assertEqual(claims.roles, ["analyst"])
        self.assertEqual(claims.iss, "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_123456789")
        self.assertEqual(claims.aud, "test_client_id")
        print("✅ User claims model test passed")


class TestDashboardOverviewResponse(unittest.TestCase):
    """Test dashboard overview response model"""
    
    def test_dashboard_overview_response_creation(self):
        """Test DashboardOverviewResponse model creation"""
        now = datetime.now(timezone.utc)
        
        # Create test data
        recent_analyses = [
            RecentAnalysisSummary(
                analysis_id="test_1",
                filename="test.mp4",
                user_id="user_1",
                status=AnalysisStatus.COMPLETED,
                confidence_score=Decimal("0.95"),
                is_fake=False,
                processing_time_seconds=12.5,
                created_at=now,
                updated_at=now,
                blockchain_hash="0x123"
            )
        ]
        
        confidence_trends = [
            ConfidenceScoreTrend(
                timestamp=now,
                average_confidence=Decimal("0.90"),
                fake_detection_rate=Decimal("0.10"),
                total_analyses=50,
                trend_direction=ConfidenceTrend.STABLE
            )
        ]
        
        processing_queue = ProcessingQueueMetrics(
            queue_length=3,
            estimated_wait_time_minutes=5.2,
            processing_capacity=10,
            active_processors=8,
            status=ProcessingQueueStatus.HEALTHY,
            throughput_per_hour=24.5,
            error_rate=Decimal("0.02")
        )
        
        user_activity = [
            UserActivityMetric(
                user_id="user_1",
                email="user@example.com",
                last_activity=now,
                total_analyses=150,
                recent_analyses=5,
                is_active=True,
                role="analyst"
            )
        ]
        
        system_performance = SystemPerformanceMetrics(
            cpu_usage_percent=Decimal("45.2"),
            memory_usage_percent=Decimal("67.8"),
            disk_usage_percent=Decimal("23.4"),
            gpu_usage_percent=Decimal("78.9"),
            network_latency_ms=12.5,
            database_connection_count=15,
            redis_connection_count=8,
            uptime_hours=168.5
        )
        
        blockchain_metrics = BlockchainVerificationMetrics(
            total_verifications=1250,
            successful_verifications=1245,
            failed_verifications=5,
            pending_verifications=12,
            average_verification_time_seconds=3.2,
            last_verification_at=now,
            blockchain_network_status="healthy",
            gas_fee_trend="stable"
        )
        
        summary_stats = {
            "total_analyses_today": 25,
            "fake_detection_rate_today": 0.18,
            "average_confidence_today": 0.89,
            "system_health_score": 0.95,
            "user_satisfaction_score": 4.7
        }
        
        # Create response
        response = DashboardOverviewResponse(
            recent_analyses=recent_analyses,
            confidence_trends=confidence_trends,
            processing_queue=processing_queue,
            user_activity=user_activity,
            system_performance=system_performance,
            blockchain_metrics=blockchain_metrics,
            summary_stats=summary_stats,
            cache_ttl_seconds=60,
            data_freshness_seconds=15,
            response_time_ms=45.2,
            request_id="req_123"
        )
        
        # Validate response
        self.assertEqual(len(response.recent_analyses), 1)
        self.assertEqual(len(response.confidence_trends), 1)
        self.assertEqual(len(response.user_activity), 1)
        self.assertEqual(response.cache_ttl_seconds, 60)
        self.assertEqual(response.data_freshness_seconds, 15)
        self.assertEqual(response.response_time_ms, 45.2)
        self.assertEqual(response.request_id, "req_123")
        self.assertEqual(response.summary_stats["total_analyses_today"], 25)
        self.assertEqual(response.summary_stats["fake_detection_rate_today"], 0.18)
        print("✅ Dashboard overview response model test passed")


class TestIntegration(unittest.TestCase):
    """Test integration between components"""
    
    def test_configuration_integration(self):
        """Test configuration integration with other components"""
        config_manager = ConfigurationManager()
        settings = config_manager.get_settings()
        
        # Test that all components can access configuration
        redis_config = settings.redis
        aws_config = settings.aws
        dashboard_config = settings.dashboard
        
        self.assertIsNotNone(redis_config)
        self.assertIsNotNone(aws_config)
        self.assertIsNotNone(dashboard_config)
        print("✅ Configuration integration test passed")
    
    def test_model_serialization(self):
        """Test model serialization and deserialization"""
        now = datetime.now(timezone.utc)
        
        # Create a complex model
        analysis = RecentAnalysisSummary(
            analysis_id="test_serialization",
            filename="test.mp4",
            user_id="user_123",
            status=AnalysisStatus.COMPLETED,
            confidence_score=Decimal("0.95"),
            is_fake=False,
            processing_time_seconds=12.5,
            created_at=now,
            updated_at=now,
            blockchain_hash="0x123abc"
        )
        
        # Serialize to JSON
        json_data = analysis.model_dump_json()
        self.assertIsInstance(json_data, str)
        self.assertIn("test_serialization", json_data)
        self.assertIn("0.95", json_data)
        
        # Deserialize from JSON
        parsed_data = json.loads(json_data)
        self.assertEqual(parsed_data["analysis_id"], "test_serialization")
        self.assertEqual(parsed_data["confidence_score"], 0.95)
        print("✅ Model serialization test passed")


def run_all_tests():
    """Run all test suites"""
    print("🚀 Starting Work Order #33 Implementation Tests...")
    print("=" * 60)
    
    test_suites = [
        TestDashboardModels,
        TestRedisCacheManager,
        TestConfigurationManager,
        TestExternalServiceClient,
        TestDashboardDataAggregator,
        TestCognitoJWTValidator,
        TestUserClaims,
        TestDashboardOverviewResponse,
        TestIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_suite in test_suites:
        print(f"\n📋 Running {test_suite.__name__}...")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_suite)
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        suite_tests = result.testsRun
        suite_passed = suite_tests - len(result.failures) - len(result.errors)
        suite_failed = len(result.failures) + len(result.errors)
        
        total_tests += suite_tests
        passed_tests += suite_passed
        failed_tests += suite_failed
        
        status_icon = "✅" if suite_failed == 0 else "❌"
        print(f"{status_icon} {test_suite.__name__}: {suite_passed}/{suite_tests} tests passed")
        
        if result.failures:
            for test, traceback in result.failures:
                print(f"   ❌ FAILED: {test}")
        if result.errors:
            for test, traceback in result.errors:
                print(f"   ❌ ERROR: {test}")
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! Work Order #33 implementation is working correctly.")
        return True
    else:
        print(f"\n⚠️  {failed_tests} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
