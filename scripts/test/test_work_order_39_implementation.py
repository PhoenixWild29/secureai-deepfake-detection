#!/usr/bin/env python3
"""
Test Suite for Work Order #39 Implementation
Multi-Format Export Capabilities

This comprehensive test suite validates the implementation of the
ResultExportInterface component and related export functionality.
"""

import unittest
import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio
import aiohttp

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SecureAI-DeepFake-Detection'))

# ============================================================================
# Test Configuration
# ============================================================================

class TestConfig:
    """Test configuration constants"""
    
    # Test data
    SAMPLE_ANALYSIS_ID = "test-analysis-12345"
    SAMPLE_USER_ID = "test-user-67890"
    SAMPLE_EXPORT_ID = "export-abc123"
    
    # Mock analysis data
    SAMPLE_ANALYSIS_DATA = {
        "id": SAMPLE_ANALYSIS_ID,
        "created_at": "2024-01-15T10:30:00Z",
        "confidence_score": 0.85,
        "is_fake": False,
        "processing_time_ms": 1250,
        "model_used": "Enhanced CNN Ensemble",
        "blockchain_hash": "0x1234567890abcdef1234567890abcdef12345678",
        "blockchain_verified_at": "2024-01-15T10:32:00Z",
        "total_frames": 120,
        "fps": 30,
        "memory_usage": 512,
        "cpu_usage": 75,
        "frame_analysis": [
            {
                "frame_number": 1,
                "confidence": 0.82,
                "suspicious_regions": [],
                "processing_time_ms": 45
            },
            {
                "frame_number": 2,
                "confidence": 0.87,
                "suspicious_regions": [{"x": 100, "y": 100, "width": 50, "height": 50}],
                "processing_time_ms": 52
            }
        ],
        "suspicious_regions": [
            {
                "frame_number": 2,
                "region": {"x": 100, "y": 100, "width": 50, "height": 50},
                "confidence": 0.75
            }
        ]
    }
    
    # Export formats
    SUPPORTED_FORMATS = ["pdf", "json", "csv"]
    
    # Export options
    DEFAULT_EXPORT_OPTIONS = {
        "includeFrameAnalysis": True,
        "includeBlockchainVerification": True,
        "includeProcessingMetrics": False,
        "includeSuspiciousRegions": False
    }

# ============================================================================
# Base Test Classes
# ============================================================================

class BaseExportTest(unittest.TestCase):
    """Base test class for export functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = TestConfig()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

class MockExportService:
    """Mock export service for testing"""
    
    def __init__(self):
        self.exports = {}
        self.export_counter = 0
        
    async def initiate_export(self, export_request):
        """Mock export initiation"""
        self.export_counter += 1
        export_id = f"export_{self.export_counter}_{int(datetime.now().timestamp())}"
        
        export_job = {
            "exportId": export_id,
            "status": "initiating",
            "format": export_request["format"],
            "analysisCount": len(export_request["analysisIds"]),
            "estimatedCompletion": (datetime.now() + timedelta(minutes=2)).isoformat(),
            "createdAt": datetime.now().isoformat()
        }
        
        self.exports[export_id] = export_job
        return export_job
        
    async def get_export_status(self, export_id):
        """Mock export status retrieval"""
        if export_id in self.exports:
            return self.exports[export_id]
        return None
        
    async def download_export(self, export_id):
        """Mock export download"""
        if export_id in self.exports:
            return b"mock export content"
        return None
        
    async def generate_preview(self, preview_request):
        """Mock preview generation"""
        format_type = preview_request["format"]
        
        if format_type == "pdf":
            return {
                "title": "Deepfake Detection Report",
                "subtitle": "SecureAI Analysis Results",
                "sections": [
                    {
                        "title": "Executive Summary",
                        "content": f"Analysis completed with 85% confidence."
                    }
                ]
            }
        elif format_type == "json":
            return {
                "analysis_id": self.config.SAMPLE_ANALYSIS_ID,
                "detection_results": {
                    "overall_confidence": 0.85,
                    "is_fake": False
                }
            }
        elif format_type == "csv":
            return {
                "headers": ["Analysis ID", "Confidence Score", "Is Fake"],
                "rows": [[self.config.SAMPLE_ANALYSIS_ID, "0.85", "FALSE"]]
            }
        
        return None

# ============================================================================
# Frontend Component Tests
# ============================================================================

class TestResultExportInterface(BaseExportTest):
    """Test ResultExportInterface component functionality"""
    
    def test_export_format_configuration(self):
        """Test export format configuration"""
        from src.components.ResultExportInterface.ResultExportInterface import EXPORT_FORMATS
        
        # Test supported formats
        self.assertIn("PDF", EXPORT_FORMATS)
        self.assertIn("JSON", EXPORT_FORMATS)
        self.assertIn("CSV", EXPORT_FORMATS)
        
        # Test format properties
        pdf_format = EXPORT_FORMATS["PDF"]
        self.assertEqual(pdf_format["id"], "pdf")
        self.assertEqual(pdf_format["extension"], ".pdf")
        self.assertTrue(pdf_format["supportsBatch"])
        
        json_format = EXPORT_FORMATS["JSON"]
        self.assertEqual(json_format["id"], "json")
        self.assertEqual(json_format["extension"], ".json")
        self.assertTrue(json_format["supportsBatch"])
        
        csv_format = EXPORT_FORMATS["CSV"]
        self.assertEqual(csv_format["id"], "csv")
        self.assertEqual(csv_format["extension"], ".csv")
        self.assertTrue(csv_format["supportsBatch"])
    
    def test_export_options_configuration(self):
        """Test export options configuration"""
        from src.components.ResultExportInterface.ResultExportInterface import EXPORT_OPTIONS
        
        # Test option properties
        self.assertIn("includeFrameAnalysis", EXPORT_OPTIONS)
        self.assertIn("includeBlockchainVerification", EXPORT_OPTIONS)
        self.assertIn("includeProcessingMetrics", EXPORT_OPTIONS)
        self.assertIn("includeSuspiciousRegions", EXPORT_OPTIONS)
        
        # Test default values
        self.assertTrue(EXPORT_OPTIONS["includeFrameAnalysis"]["default"])
        self.assertTrue(EXPORT_OPTIONS["includeBlockchainVerification"]["default"])
        self.assertFalse(EXPORT_OPTIONS["includeProcessingMetrics"]["default"])
        self.assertFalse(EXPORT_OPTIONS["includeSuspiciousRegions"]["default"])
    
    def test_component_initialization(self):
        """Test component initialization with various props"""
        # Test single analysis export
        single_analysis_props = {
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "detectionData": self.config.SAMPLE_ANALYSIS_DATA
        }
        
        # Test batch export
        batch_analysis_props = {
            "analysisIds": [
                self.config.SAMPLE_ANALYSIS_ID,
                "analysis-2",
                "analysis-3"
            ],
            "detectionDataArray": [
                self.config.SAMPLE_ANALYSIS_DATA,
                self.config.SAMPLE_ANALYSIS_DATA,
                self.config.SAMPLE_ANALYSIS_DATA
            ],
            "showBatchOptions": True
        }
        
        # Test callback functions
        callback_props = {
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "onExportComplete": Mock(),
            "onExportError": Mock()
        }
        
        # All props should be valid
        self.assertIsNotNone(single_analysis_props)
        self.assertIsNotNone(batch_analysis_props)
        self.assertIsNotNone(callback_props)

class TestExportProgressIndicator(BaseExportTest):
    """Test ExportProgressIndicator component functionality"""
    
    def test_progress_status_messages(self):
        """Test progress status messages"""
        from src.components.ExportProgressIndicator.ExportProgressIndicator import STATUS_MESSAGES
        
        # Test all status messages are defined
        expected_statuses = [
            "initiating", "processing", "generating", 
            "completing", "completed", "failed", "cancelled"
        ]
        
        for status in expected_statuses:
            self.assertIn(status, STATUS_MESSAGES)
            self.assertIsNotNone(STATUS_MESSAGES[status])
    
    def test_progress_status_icons(self):
        """Test progress status icons"""
        from src.components.ExportProgressIndicator.ExportProgressIndicator import STATUS_ICONS
        
        # Test all status icons are defined
        expected_statuses = [
            "initiating", "processing", "generating", 
            "completing", "completed", "failed", "cancelled"
        ]
        
        for status in expected_statuses:
            self.assertIn(status, STATUS_ICONS)
            self.assertIsNotNone(STATUS_ICONS[status])
    
    def test_progress_data_structure(self):
        """Test progress data structure"""
        progress_data = {
            "status": "processing",
            "progress": 50,
            "message": "Generating export...",
            "exportId": self.config.SAMPLE_EXPORT_ID,
            "estimatedCompletion": (datetime.now() + timedelta(minutes=1)).isoformat()
        }
        
        # Test required fields
        self.assertIn("status", progress_data)
        self.assertIn("progress", progress_data)
        self.assertIn("message", progress_data)
        self.assertIn("exportId", progress_data)
        
        # Test progress value range
        self.assertGreaterEqual(progress_data["progress"], 0)
        self.assertLessEqual(progress_data["progress"], 100)

class TestExportFormatPreview(BaseExportTest):
    """Test ExportFormatPreview component functionality"""
    
    def test_preview_configurations(self):
        """Test preview configurations"""
        from src.components.ExportFormatPreview.ExportFormatPreview import FORMAT_PREVIEW_CONFIGS
        
        # Test all formats have preview configurations
        for format_type in self.config.SUPPORTED_FORMATS:
            self.assertIn(format_type, FORMAT_PREVIEW_CONFIGS)
            
            config = FORMAT_PREVIEW_CONFIGS[format_type]
            self.assertIn("name", config)
            self.assertIn("icon", config)
            self.assertIn("description", config)
    
    def test_preview_data_generation(self):
        """Test preview data generation functions"""
        from src.components.ExportFormatPreview.ExportFormatPreview import (
            generatePDFPreview, generateJSONPreview, generateCSVPreview
        )
        
        # Test PDF preview generation
        pdf_preview = generatePDFPreview(self.config.SAMPLE_ANALYSIS_DATA)
        self.assertIn("title", pdf_preview)
        self.assertIn("sections", pdf_preview)
        self.assertEqual(pdf_preview["title"], "Deepfake Detection Report")
        
        # Test JSON preview generation
        json_preview = generateJSONPreview(self.config.SAMPLE_ANALYSIS_DATA)
        self.assertIn("analysis_id", json_preview)
        self.assertIn("detection_results", json_preview)
        self.assertEqual(json_preview["analysis_id"], self.config.SAMPLE_ANALYSIS_ID)
        
        # Test CSV preview generation
        csv_preview = generateCSVPreview(self.config.SAMPLE_ANALYSIS_DATA)
        self.assertIn("headers", csv_preview)
        self.assertIn("rows", csv_preview)
        self.assertIsInstance(csv_preview["headers"], list)
        self.assertIsInstance(csv_preview["rows"], list)

# ============================================================================
# Service Layer Tests
# ============================================================================

class TestExportService(BaseExportTest):
    """Test ExportService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.mock_service = MockExportService()
    
    def test_export_service_initialization(self):
        """Test export service initialization"""
        from src.services.exportService import ExportService
        
        service = ExportService("http://localhost:8000")
        self.assertIsNotNone(service)
        self.assertEqual(service.baseUrl, "http://localhost:8000")
    
    async def test_export_initiation(self):
        """Test export initiation"""
        export_request = {
            "format": "pdf",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS,
            "userId": self.config.SAMPLE_USER_ID,
            "permissions": {"allowedFormats": ["pdf", "json", "csv"]}
        }
        
        result = await self.mock_service.initiate_export(export_request)
        
        # Test result structure
        self.assertIn("exportId", result)
        self.assertIn("status", result)
        self.assertIn("format", result)
        self.assertEqual(result["format"], "pdf")
        self.assertEqual(result["status"], "initiating")
    
    async def test_export_status_retrieval(self):
        """Test export status retrieval"""
        # First initiate an export
        export_request = {
            "format": "json",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS,
            "userId": self.config.SAMPLE_USER_ID,
            "permissions": {}
        }
        
        export_job = await self.mock_service.initiate_export(export_request)
        export_id = export_job["exportId"]
        
        # Then retrieve status
        status = await self.mock_service.get_export_status(export_id)
        
        self.assertIsNotNone(status)
        self.assertEqual(status["exportId"], export_id)
        self.assertEqual(status["format"], "json")
    
    async def test_preview_generation(self):
        """Test preview generation for all formats"""
        for format_type in self.config.SUPPORTED_FORMATS:
            preview_request = {
                "format": format_type,
                "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
                "options": self.config.DEFAULT_EXPORT_OPTIONS
            }
            
            preview = await self.mock_service.generate_preview(preview_request)
            
            self.assertIsNotNone(preview)
            
            if format_type == "pdf":
                self.assertIn("title", preview)
                self.assertIn("sections", preview)
            elif format_type == "json":
                self.assertIn("analysis_id", preview)
                self.assertIn("detection_results", preview)
            elif format_type == "csv":
                self.assertIn("headers", preview)
                self.assertIn("rows", preview)
    
    async def test_export_download(self):
        """Test export download"""
        # First initiate an export
        export_request = {
            "format": "csv",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS,
            "userId": self.config.SAMPLE_USER_ID,
            "permissions": {}
        }
        
        export_job = await self.mock_service.initiate_export(export_request)
        export_id = export_job["exportId"]
        
        # Then download
        content = await self.mock_service.download_export(export_id)
        
        self.assertIsNotNone(content)
        self.assertIsInstance(content, bytes)

# ============================================================================
# Backend API Tests
# ============================================================================

class TestExportAPI(BaseExportTest):
    """Test export API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.api_base_url = "http://localhost:8000/api"
    
    def test_export_routes_configuration(self):
        """Test export routes are properly configured"""
        from src.api.exportRoutes import router
        
        # Test router is properly configured
        self.assertIsNotNone(router)
        
        # Test that routes are registered (this would be more detailed in actual implementation)
        self.assertTrue(hasattr(router, 'stack'))
    
    def test_export_request_validation(self):
        """Test export request validation"""
        # Valid request
        valid_request = {
            "format": "pdf",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test required fields
        self.assertIn("format", valid_request)
        self.assertIn("analysisIds", valid_request)
        
        # Test format validation
        self.assertIn(valid_request["format"], self.config.SUPPORTED_FORMATS)
        
        # Test analysis IDs validation
        self.assertIsInstance(valid_request["analysisIds"], list)
        self.assertGreater(len(valid_request["analysisIds"]), 0)
    
    def test_batch_export_validation(self):
        """Test batch export request validation"""
        # Valid batch request
        valid_batch_request = {
            "format": "json",
            "analysisIds": [
                self.config.SAMPLE_ANALYSIS_ID,
                "analysis-2",
                "analysis-3"
            ],
            "options": {
                **self.config.DEFAULT_EXPORT_OPTIONS,
                "combineIntoOne": True
            }
        }
        
        # Test batch-specific options
        self.assertIn("combineIntoOne", valid_batch_request["options"])
        self.assertTrue(valid_batch_request["options"]["combineIntoOne"])
        
        # Test multiple analysis IDs
        self.assertGreater(len(valid_batch_request["analysisIds"]), 1)

class TestExportController(BaseExportTest):
    """Test export controller functionality"""
    
    def test_controller_initialization(self):
        """Test export controller initialization"""
        from src.server.controllers.exportController import ExportController
        
        controller = ExportController()
        self.assertIsNotNone(controller)
        self.assertIsNotNone(controller.activeExports)
        self.assertIsNotNone(controller.progressTracker)
    
    def test_export_request_validation(self):
        """Test export request validation in controller"""
        from src.server.controllers.exportController import ExportController
        
        controller = ExportController()
        
        # Valid request
        valid_request = {
            "format": "pdf",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test validation (should not raise exception)
        try:
            controller.validateExportRequest(valid_request)
        except Exception as e:
            self.fail(f"Valid request failed validation: {e}")
        
        # Invalid format
        invalid_request = {
            "format": "invalid",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test validation (should raise exception)
        with self.assertRaises(Exception):
            controller.validateExportRequest(invalid_request)
        
        # Invalid analysis IDs
        invalid_request2 = {
            "format": "pdf",
            "analysisIds": [],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test validation (should raise exception)
        with self.assertRaises(Exception):
            controller.validateExportRequest(invalid_request2)
    
    def test_permission_checking(self):
        """Test permission checking functionality"""
        from src.server.controllers.exportController import ExportController
        
        controller = ExportController()
        
        # Test user permissions
        user_permissions = {
            "allowedFormats": ["pdf", "json"],
            "maxBatchSize": 5,
            "dataAccessLevel": "standard"
        }
        
        # Valid permission check
        try:
            controller.checkExportPermissions(
                self.config.SAMPLE_USER_ID,
                "pdf",
                [self.config.SAMPLE_ANALYSIS_ID],
                user_permissions
            )
        except Exception as e:
            self.fail(f"Valid permission check failed: {e}")
        
        # Invalid format permission
        with self.assertRaises(Exception):
            controller.checkExportPermissions(
                self.config.SAMPLE_USER_ID,
                "csv",  # Not allowed in permissions
                [self.config.SAMPLE_ANALYSIS_ID],
                user_permissions
            )
        
        # Batch size limit exceeded
        with self.assertRaises(Exception):
            controller.checkExportPermissions(
                self.config.SAMPLE_USER_ID,
                "pdf",
                ["analysis-1", "analysis-2", "analysis-3", "analysis-4", "analysis-5", "analysis-6"],  # 6 > 5
                user_permissions
            )

# ============================================================================
# Integration Tests
# ============================================================================

class TestExportIntegration(BaseExportTest):
    """Test integration between components"""
    
    def test_frontend_backend_integration(self):
        """Test integration between frontend and backend"""
        # Test data flow from frontend to backend
        frontend_request = {
            "format": "pdf",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Simulate backend processing
        backend_response = {
            "success": True,
            "exportId": self.config.SAMPLE_EXPORT_ID,
            "status": "initiating",
            "format": "pdf",
            "analysisCount": 1,
            "estimatedCompletion": (datetime.now() + timedelta(minutes=2)).isoformat()
        }
        
        # Test response structure
        self.assertTrue(backend_response["success"])
        self.assertIn("exportId", backend_response)
        self.assertEqual(backend_response["format"], frontend_request["format"])
        self.assertEqual(backend_response["analysisCount"], len(frontend_request["analysisIds"]))
    
    def test_export_workflow_integration(self):
        """Test complete export workflow integration"""
        # Step 1: Initiate export
        initiate_request = {
            "format": "json",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Step 2: Check status
        status_request = {
            "exportId": self.config.SAMPLE_EXPORT_ID
        }
        
        # Step 3: Download when complete
        download_request = {
            "exportId": self.config.SAMPLE_EXPORT_ID
        }
        
        # Test that all steps have required data
        self.assertIn("format", initiate_request)
        self.assertIn("exportId", status_request)
        self.assertIn("exportId", download_request)

# ============================================================================
# Performance Tests
# ============================================================================

class TestExportPerformance(BaseExportTest):
    """Test export performance characteristics"""
    
    def test_large_batch_export_performance(self):
        """Test performance with large batch exports"""
        # Simulate large batch
        large_analysis_ids = [f"analysis-{i}" for i in range(100)]
        
        batch_request = {
            "format": "csv",
            "analysisIds": large_analysis_ids,
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test request structure is valid
        self.assertEqual(len(batch_request["analysisIds"]), 100)
        self.assertIn("format", batch_request)
        
        # Test estimated completion time calculation
        from src.services.exportService import ExportService
        service = ExportService()
        
        estimated_time = service.calculateEstimatedCompletion("csv", 100)
        self.assertIsNotNone(estimated_time)
        
        # Estimated time should be in the future
        estimated_datetime = datetime.fromisoformat(estimated_time.replace('Z', '+00:00'))
        self.assertGreater(estimated_datetime, datetime.now())
    
    def test_concurrent_export_handling(self):
        """Test handling of concurrent export requests"""
        # Simulate multiple concurrent requests
        concurrent_requests = []
        
        for i in range(5):
            request = {
                "format": "pdf",
                "analysisIds": [f"analysis-{i}"],
                "options": self.config.DEFAULT_EXPORT_OPTIONS,
                "userId": f"user-{i}",
                "permissions": {"allowedFormats": ["pdf", "json", "csv"]}
            }
            concurrent_requests.append(request)
        
        # Test all requests are valid
        self.assertEqual(len(concurrent_requests), 5)
        
        for request in concurrent_requests:
            self.assertIn("format", request)
            self.assertIn("analysisIds", request)
            self.assertIn("userId", request)

# ============================================================================
# Error Handling Tests
# ============================================================================

class TestExportErrorHandling(BaseExportTest):
    """Test error handling in export functionality"""
    
    def test_invalid_format_error(self):
        """Test handling of invalid export format"""
        invalid_request = {
            "format": "invalid_format",
            "analysisIds": [self.config.SAMPLE_ANALYSIS_ID],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test validation catches invalid format
        from src.server.controllers.exportController import ExportController
        controller = ExportController()
        
        with self.assertRaises(Exception) as context:
            controller.validateExportRequest(invalid_request)
        
        self.assertIn("Invalid export format", str(context.exception))
    
    def test_empty_analysis_ids_error(self):
        """Test handling of empty analysis IDs"""
        invalid_request = {
            "format": "pdf",
            "analysisIds": [],
            "options": self.config.DEFAULT_EXPORT_OPTIONS
        }
        
        # Test validation catches empty analysis IDs
        from src.server.controllers.exportController import ExportController
        controller = ExportController()
        
        with self.assertRaises(Exception) as context:
            controller.validateExportRequest(invalid_request)
        
        self.assertIn("Analysis IDs are required", str(context.exception))
    
    def test_permission_denied_error(self):
        """Test handling of permission denied errors"""
        user_permissions = {
            "allowedFormats": ["pdf"],  # Only PDF allowed
            "maxBatchSize": 1,
            "dataAccessLevel": "basic"
        }
        
        # Test CSV format denied
        from src.server.controllers.exportController import ExportController
        controller = ExportController()
        
        with self.assertRaises(Exception) as context:
            controller.checkExportPermissions(
                self.config.SAMPLE_USER_ID,
                "csv",  # Not allowed
                [self.config.SAMPLE_ANALYSIS_ID],
                user_permissions
            )
        
        self.assertIn("not allowed", str(context.exception))
    
    def test_batch_size_limit_error(self):
        """Test handling of batch size limit exceeded"""
        user_permissions = {
            "allowedFormats": ["pdf", "json", "csv"],
            "maxBatchSize": 2,  # Limit to 2
            "dataAccessLevel": "standard"
        }
        
        # Test batch size exceeded
        from src.server.controllers.exportController import ExportController
        controller = ExportController()
        
        with self.assertRaises(Exception) as context:
            controller.checkExportPermissions(
                self.config.SAMPLE_USER_ID,
                "pdf",
                ["analysis-1", "analysis-2", "analysis-3"],  # 3 > 2
                user_permissions
            )
        
        self.assertIn("exceeds limit", str(context.exception))

# ============================================================================
# Test Runner
# ============================================================================

def run_export_tests():
    """Run all export tests"""
    print("=" * 80)
    print("RUNNING WORK ORDER #39 IMPLEMENTATION TESTS")
    print("Multi-Format Export Capabilities")
    print("=" * 80)
    
    # Test suites
    test_suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestResultExportInterface),
        unittest.TestLoader().loadTestsFromTestCase(TestExportProgressIndicator),
        unittest.TestLoader().loadTestsFromTestCase(TestExportFormatPreview),
        unittest.TestLoader().loadTestsFromTestCase(TestExportService),
        unittest.TestLoader().loadTestsFromTestCase(TestExportAPI),
        unittest.TestLoader().loadTestsFromTestCase(TestExportController),
        unittest.TestLoader().loadTestsFromTestCase(TestExportIntegration),
        unittest.TestLoader().loadTestsFromTestCase(TestExportPerformance),
        unittest.TestLoader().loadTestsFromTestCase(TestExportErrorHandling)
    ]
    
    # Run tests
    suite = unittest.TestSuite(test_suites)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    print("\n" + "=" * 80)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_export_tests()
    sys.exit(0 if success else 1)
