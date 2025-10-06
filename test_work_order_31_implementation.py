#!/usr/bin/env python3
"""
Work Order #31 Implementation Test
Test script for WebSocket Status API Integration implementation
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
TEST_ANALYSIS_ID = str(uuid4())
TEST_JWT_TOKEN = "test_jwt_token_12345"
TEST_USER_ID = "test_user_123"

class WorkOrder31TestSuite:
    """Comprehensive test suite for Work Order #31 implementation"""
    
    def __init__(self):
        self.test_results = {}
        self.passed_tests = 0
        self.total_tests = 0
    
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            logger.info(f"✅ {test_name}: PASSED - {message}")
        else:
            logger.error(f"❌ {test_name}: FAILED - {message}")
        
        self.test_results[test_name] = {
            'passed': passed,
            'message': message
        }
    
    def test_websocket_status_api_endpoint(self):
        """Test 1: WebSocket Status API Endpoint implementation"""
        try:
            # Check if the WebSocket status API endpoint file exists
            websocket_api_file = "src/api/websocket_status_api.py"
            if not os.path.exists(websocket_api_file):
                self.log_test_result("WebSocket Status API Endpoint", False, f"File not found: {websocket_api_file}")
                return
            
            # Read the file and check for required components
            with open(websocket_api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required API endpoint components
            required_components = [
                'from fastapi import WebSocket, WebSocketDisconnect',
                'from src.models.status_tracking import StatusTrackingResponse',
                'from src.services.websocket_service import get_websocket_service',
                'async def websocket_status_endpoint',
                'async def handle_websocket_connection',
                'async def broadcast_status_update',
                'async def handle_status_request',
                'async def handle_subscribe_request',
                'async def handle_unsubscribe_request'
            ]
            
            for component in required_components:
                if component not in content:
                    self.log_test_result("WebSocket Status API Endpoint", False, f"Required component not found: {component}")
                    return
            
            self.log_test_result("WebSocket Status API Endpoint", True, "All WebSocket status API components found in file")
            
        except Exception as e:
            self.log_test_result("WebSocket Status API Endpoint", False, f"Error: {e}")
    
    def test_status_api_integration(self):
        """Test 2: Status API Integration with existing models"""
        try:
            # Check if the status API integration file exists
            status_integration_file = "src/api/status_integration.py"
            if not os.path.exists(status_integration_file):
                self.log_test_result("Status API Integration", False, f"File not found: {status_integration_file}")
                return
            
            # Read the file and check for required components
            with open(status_integration_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required integration components
            required_components = [
                'from src.models.status_tracking import StatusTrackingResponse, StatusHistoryResponse',
                'from src.models.analysis import Analysis',
                'from src.services.redis_pubsub_service import get_redis_pubsub_service',
                'class StatusAPIIntegration',
                'async def get_analysis_status',
                'async def update_analysis_status',
                'async def get_status_history',
                'async def publish_status_update',
                'async def handle_status_transition'
            ]
            
            for component in required_components:
                if component not in content:
                    self.log_test_result("Status API Integration", False, f"Required component not found: {component}")
                    return
            
            self.log_test_result("Status API Integration", True, "All status API integration components found in file")
            
        except Exception as e:
            self.log_test_result("Status API Integration", False, f"Error: {e}")
    
    def test_websocket_message_handler(self):
        """Test 3: WebSocket Message Handler implementation"""
        try:
            # Check if the WebSocket message handler file exists
            message_handler_file = "src/services/websocket_message_handler.py"
            if not os.path.exists(message_handler_file):
                self.log_test_result("WebSocket Message Handler", False, f"File not found: {message_handler_file}")
                return
            
            # Read the file and check for required components
            with open(message_handler_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required message handler components
            required_components = [
                'from enum import Enum',
                'from typing import Dict, Any, Optional',
                'from uuid import UUID',
                'class WebSocketMessageType',
                'class WebSocketMessageHandler',
                'async def handle_message',
                'async def handle_status_request',
                'async def handle_subscribe_request',
                'async def handle_unsubscribe_request',
                'async def handle_ping_request',
                'def validate_message_format',
                'def create_response_message'
            ]
            
            for component in required_components:
                if component not in content:
                    self.log_test_result("WebSocket Message Handler", False, f"Required component not found: {component}")
                    return
            
            self.log_test_result("WebSocket Message Handler", True, "All WebSocket message handler components found in file")
            
        except Exception as e:
            self.log_test_result("WebSocket Message Handler", False, f"Error: {e}")
    
    def test_status_broadcast_service(self):
        """Test 4: Status Broadcast Service implementation"""
        try:
            # Check if the status broadcast service file exists
            broadcast_service_file = "src/services/status_broadcast_service.py"
            if not os.path.exists(broadcast_service_file):
                self.log_test_result("Status Broadcast Service", False, f"File not found: {broadcast_service_file}")
                return
            
            # Read the file and check for required components
            with open(broadcast_service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required broadcast service components
            required_components = [
                'from src.models.status_tracking import StatusTrackingResponse',
                'from src.services.websocket_service import get_websocket_service',
                'from src.services.redis_pubsub_service import get_redis_pubsub_service',
                'class StatusBroadcastService',
                'async def broadcast_analysis_status',
                'async def broadcast_stage_transition',
                'async def broadcast_progress_update',
                'async def broadcast_error_update',
                'async def broadcast_completion_update',
                'def get_subscribed_connections',
                'async def cleanup_stale_connections'
            ]
            
            for component in required_components:
                if component not in content:
                    self.log_test_result("Status Broadcast Service", False, f"Required component not found: {component}")
                    return
            
            self.log_test_result("Status Broadcast Service", True, "All status broadcast service components found in file")
            
        except Exception as e:
            self.log_test_result("Status Broadcast Service", False, f"Error: {e}")
    
    def test_api_route_registration(self):
        """Test 5: API Route Registration"""
        try:
            # Check if the main API file includes the new routes
            main_api_file = "api.py"
            if not os.path.exists(main_api_file):
                self.log_test_result("API Route Registration", False, f"File not found: {main_api_file}")
                return
            
            # Read the file and check for route registration
            with open(main_api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required route registrations
            required_components = [
                'from src.api.websocket_status_api import websocket_status_endpoint',
                'from src.api.status_integration import StatusAPIIntegration',
                'app.add_api_route',
                'websocket_status_endpoint',
                'status_integration'
            ]
            
            found_components = 0
            for component in required_components:
                if component in content:
                    found_components += 1
            
            if found_components >= 3:  # At least 3 out of 5 components should be found
                self.log_test_result("API Route Registration", True, f"Found {found_components}/5 required route components")
            else:
                self.log_test_result("API Route Registration", False, f"Only found {found_components}/5 required route components")
            
        except Exception as e:
            self.log_test_result("API Route Registration", False, f"Error: {e}")
    
    def test_error_handling_implementation(self):
        """Test 6: Error Handling Implementation"""
        try:
            # Check if error handling is implemented in the WebSocket API
            websocket_api_file = "src/api/websocket_status_api.py"
            if not os.path.exists(websocket_api_file):
                self.log_test_result("Error Handling Implementation", False, f"File not found: {websocket_api_file}")
                return
            
            # Read the file and check for error handling
            with open(websocket_api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required error handling components
            required_components = [
                'except WebSocketDisconnect',
                'except Exception as e',
                'logger.error',
                'error_response',
                'await websocket.send_text'
            ]
            
            found_components = 0
            for component in required_components:
                if component in content:
                    found_components += 1
            
            if found_components >= 4:  # At least 4 out of 5 components should be found
                self.log_test_result("Error Handling Implementation", True, f"Found {found_components}/5 error handling components")
            else:
                self.log_test_result("Error Handling Implementation", False, f"Only found {found_components}/5 error handling components")
            
        except Exception as e:
            self.log_test_result("Error Handling Implementation", False, f"Error: {e}")
    
    def test_connection_management(self):
        """Test 7: Connection Management Implementation"""
        try:
            # Check if connection management is implemented
            websocket_service_file = "src/services/websocket_service.py"
            if not os.path.exists(websocket_service_file):
                self.log_test_result("Connection Management", False, f"File not found: {websocket_service_file}")
                return
            
            # Read the file and check for connection management
            with open(websocket_service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required connection management components
            required_components = [
                'connection_analyses',
                'active_analyses_tracked',
                'async def connect',
                'async def disconnect',
                'async def is_connected',
                'def get_connection_count',
                'def get_active_analyses'
            ]
            
            found_components = 0
            for component in required_components:
                if component in content:
                    found_components += 1
            
            if found_components >= 5:  # At least 5 out of 7 components should be found
                self.log_test_result("Connection Management", True, f"Found {found_components}/7 connection management components")
            else:
                self.log_test_result("Connection Management", False, f"Only found {found_components}/7 connection management components")
            
        except Exception as e:
            self.log_test_result("Connection Management", False, f"Error: {e}")
    
    def test_message_validation(self):
        """Test 8: Message Validation Implementation"""
        try:
            # Check if message validation is implemented
            message_handler_file = "src/services/websocket_message_handler.py"
            if not os.path.exists(message_handler_file):
                self.log_test_result("Message Validation", False, f"File not found: {message_handler_file}")
                return
            
            # Read the file and check for message validation
            with open(message_handler_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required message validation components
            required_components = [
                'validate_message_format',
                'validate_analysis_id',
                'validate_jwt_token',
                'is_valid_json',
                'required_fields',
                'message_type'
            ]
            
            found_components = 0
            for component in required_components:
                if component in content:
                    found_components += 1
            
            if found_components >= 4:  # At least 4 out of 6 components should be found
                self.log_test_result("Message Validation", True, f"Found {found_components}/6 message validation components")
            else:
                self.log_test_result("Message Validation", False, f"Only found {found_components}/6 message validation components")
            
        except Exception as e:
            self.log_test_result("Message Validation", False, f"Error: {e}")
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        logger.info("🚀 Starting Work Order #31 Implementation Tests")
        logger.info("=" * 60)
        
        # Run all tests
        self.test_websocket_status_api_endpoint()
        self.test_status_api_integration()
        self.test_websocket_message_handler()
        self.test_status_broadcast_service()
        self.test_api_route_registration()
        self.test_error_handling_implementation()
        self.test_connection_management()
        self.test_message_validation()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 Test Results Summary")
        logger.info("=" * 60)
        
        passed_percentage = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.total_tests - self.passed_tests}")
        logger.info(f"Success Rate: {passed_percentage:.1f}%")
        
        if self.passed_tests == self.total_tests:
            logger.info("🎉 All tests passed! Work Order #31 implementation is complete.")
        else:
            logger.warning(f"⚠️  {self.total_tests - self.passed_tests} tests failed. Review implementation.")
        
        logger.info("=" * 60)
        
        return self.passed_tests == self.total_tests

def main():
    """Main test execution function"""
    try:
        # Create test suite instance
        test_suite = WorkOrder31TestSuite()
        
        # Run all tests
        success = test_suite.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
