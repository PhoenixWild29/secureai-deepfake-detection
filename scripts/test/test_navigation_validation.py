#!/usr/bin/env python3
"""
Navigation Data Validation Test Suite
Comprehensive tests for navigation validation functions and error handling
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.navigation_validation import (
    ValidationResult,
    NavigationNavigationValidationError,
    ValidationSeverity,
    NavigationPreferences,
    NavigationContext,
    validate_navigation_route,
    validate_navigation_preferences,
    validate_navigation_context,
    validate_route_security,
    get_allowed_routes,
    is_route_allowed,
    ALLOWED_DASHBOARD_ROUTES,
    ROUTE_PATTERNS
)


class TestNavigationRouteValidation:
    """Test cases for navigation route validation"""
    
    def test_valid_dashboard_routes(self):
        """Test validation of valid dashboard routes"""
        valid_routes = [
            '/dashboard/upload',
            '/dashboard/results',
            '/dashboard/history',
            '/dashboard/reports',
            '/dashboard/analytics',
            '/dashboard/settings',
            '/dashboard/profile',
            '/dashboard/notifications',
            '/dashboard/system',
            '/dashboard/help',
            '/dashboard/docs',
            '/dashboard/api'
        ]
        
        for route in valid_routes:
            result = validate_navigation_route(route)
            assert result.is_valid, f"Route {route} should be valid: {result.errors}"
            assert len(result.errors) == 0, f"Route {route} should have no errors"
    
    def test_valid_dynamic_routes(self):
        """Test validation of valid dynamic routes"""
        valid_dynamic_routes = [
            '/dashboard/results/123',
            '/dashboard/history/456',
            '/dashboard/reports/monthly',
            '/dashboard/settings/profile',
            '/dashboard/profile/security'
        ]
        
        for route in valid_dynamic_routes:
            result = validate_navigation_route(route)
            assert result.is_valid, f"Dynamic route {route} should be valid: {result.errors}"
    
    def test_invalid_route_prefixes(self):
        """Test validation of routes with invalid prefixes"""
        invalid_routes = [
            '/upload',
            '/results',
            '/admin/dashboard',
            '/api/dashboard',
            'dashboard/upload',
            'dashboard/results'
        ]
        
        for route in invalid_routes:
            result = validate_navigation_route(route)
            assert not result.is_valid, f"Route {route} should be invalid"
            assert len(result.errors) > 0, f"Route {route} should have errors"
            assert any(error.code == "INVALID_ROUTE_PREFIX" for error in result.errors)
    
    def test_path_traversal_attempts(self):
        """Test validation of path traversal attempts"""
        malicious_routes = [
            '/dashboard/../upload',
            '/dashboard/../../etc/passwd',
            '/dashboard/results/../../../admin',
            '/dashboard//upload',
            '/dashboard/results//history'
        ]
        
        for route in malicious_routes:
            result = validate_navigation_route(route)
            assert not result.is_valid, f"Malicious route {route} should be invalid"
            assert any(error.code == "PATH_TRAVERSAL_ATTEMPT" for error in result.errors)
    
    def test_query_parameters_and_fragments(self):
        """Test validation of routes with query parameters or fragments"""
        invalid_routes = [
            '/dashboard/upload?param=value',
            '/dashboard/results#section',
            '/dashboard/history?filter=recent&sort=date',
            '/dashboard/reports#chart'
        ]
        
        for route in invalid_routes:
            result = validate_navigation_route(route)
            assert not result.is_valid, f"Route {route} should be invalid"
            assert any(error.code == "INVALID_ROUTE_FORMAT" for error in result.errors)
    
    def test_invalid_route_types(self):
        """Test validation of invalid route types"""
        invalid_inputs = [
            None,
            '',
            123,
            [],
            {},
            True
        ]
        
        for invalid_input in invalid_inputs:
            result = validate_navigation_route(invalid_input)
            assert not result.is_valid, f"Input {invalid_input} should be invalid"
            assert any(error.code == "INVALID_ROUTE_TYPE" for error in result.errors)
    
    def test_route_not_allowed(self):
        """Test validation of routes not in allowed list"""
        invalid_routes = [
            '/dashboard/invalid',
            '/dashboard/unknown',
            '/dashboard/test',
            '/dashboard/admin',
            '/dashboard/root'
        ]
        
        for route in invalid_routes:
            result = validate_navigation_route(route)
            assert not result.is_valid, f"Route {route} should be invalid"
            assert any(error.code == "ROUTE_NOT_ALLOWED" for error in result.errors)
    
    def test_long_route_warning(self):
        """Test warning for unusually long routes"""
        long_route = '/dashboard/' + 'a' * 200
        result = validate_navigation_route(long_route)
        assert len(result.warnings) > 0, "Long route should generate warning"
        assert any(warning.code == "ROUTE_TOO_LONG" for warning in result.warnings)


class TestNavigationPreferencesValidation:
    """Test cases for navigation preferences validation"""
    
    def test_valid_preferences(self):
        """Test validation of valid navigation preferences"""
        valid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": ["/dashboard/upload", "/dashboard/results", "/dashboard/history"],
            "favorite_routes": ["/dashboard/upload", "/dashboard/results"],
            "recent_routes": ["/dashboard/history", "/dashboard/reports"],
            "show_breadcrumbs": True,
            "sidebar_collapsed": False,
            "navigation_style": "sidebar",
            "max_recent_routes": 10,
            "max_favorite_routes": 20
        }
        
        result = validate_navigation_preferences(valid_preferences)
        assert result.is_valid, f"Valid preferences should pass: {result.errors}"
        assert result.validated_data is not None
    
    def test_invalid_default_landing_page(self):
        """Test validation of invalid default landing page"""
        invalid_preferences = {
            "default_landing_page": "/invalid/route",
            "custom_navigation_order": [],
            "favorite_routes": [],
            "recent_routes": []
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Invalid default landing page should fail"
        assert any(error.code == "INVALID_DEFAULT_LANDING_PAGE" for error in result.errors)
    
    def test_invalid_custom_navigation_order(self):
        """Test validation of invalid custom navigation order"""
        invalid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": ["/dashboard/upload", "/invalid/route"],
            "favorite_routes": [],
            "recent_routes": []
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Invalid custom navigation order should fail"
        assert any(error.code == "INVALID_CUSTOM_NAVIGATION_ROUTE" for error in result.errors)
    
    def test_duplicate_routes_in_order(self):
        """Test validation of duplicate routes in custom navigation order"""
        invalid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": ["/dashboard/upload", "/dashboard/results", "/dashboard/upload"],
            "favorite_routes": [],
            "recent_routes": []
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Duplicate routes should fail"
        assert any(error.code == "DUPLICATE_ROUTES_IN_ORDER" for error in result.errors)
    
    def test_duplicate_favorite_routes(self):
        """Test validation of duplicate favorite routes"""
        invalid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": [],
            "favorite_routes": ["/dashboard/upload", "/dashboard/results", "/dashboard/upload"],
            "recent_routes": []
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Duplicate favorite routes should fail"
        assert any(error.code == "DUPLICATE_FAVORITE_ROUTES" for error in result.errors)
    
    def test_route_limits_exceeded(self):
        """Test validation of route limits"""
        invalid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": [],
            "favorite_routes": ["/dashboard/upload"] * 25,  # Exceeds max_favorite_routes (20)
            "recent_routes": [],
            "max_favorite_routes": 20
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Exceeding route limits should fail"
        assert any(error.code == "FAVORITE_ROUTES_LIMIT_EXCEEDED" for error in result.errors)
    
    def test_invalid_navigation_style(self):
        """Test validation of invalid navigation style"""
        invalid_preferences = {
            "default_landing_page": "/dashboard/upload",
            "custom_navigation_order": [],
            "favorite_routes": [],
            "recent_routes": [],
            "navigation_style": "invalid_style"
        }
        
        result = validate_navigation_preferences(invalid_preferences)
        assert not result.is_valid, "Invalid navigation style should fail"
    
    def test_pydantic_model_validation(self):
        """Test validation using Pydantic model directly"""
        preferences = NavigationPreferences(
            default_landing_page="/dashboard/upload",
            custom_navigation_order=["/dashboard/results", "/dashboard/history"],
            favorite_routes=["/dashboard/upload"],
            recent_routes=["/dashboard/reports"]
        )
        
        result = validate_navigation_preferences(preferences)
        assert result.is_valid, f"Pydantic model should be valid: {result.errors}"


class TestNavigationContextValidation:
    """Test cases for navigation context validation"""
    
    def test_valid_context(self):
        """Test validation of valid navigation context"""
        valid_context = {
            "current_path": "/dashboard/upload",
            "navigation_history": [
                {"path": "/dashboard/results", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"path": "/dashboard/history", "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "breadcrumbs": [
                {"label": "Dashboard", "path": "/dashboard"},
                {"label": "Upload", "path": "/dashboard/upload"}
            ],
            "active_route": "/dashboard/upload",
            "previous_route": "/dashboard/results",
            "user_permissions": ["read", "write"]
        }
        
        result = validate_navigation_context(valid_context)
        assert result.is_valid, f"Valid context should pass: {result.errors}"
        assert result.validated_data is not None
    
    def test_invalid_current_path(self):
        """Test validation of invalid current path"""
        invalid_context = {
            "current_path": "/invalid/route",
            "navigation_history": [],
            "breadcrumbs": []
        }
        
        result = validate_navigation_context(invalid_context)
        assert not result.is_valid, "Invalid current path should fail"
        assert any(error.code == "INVALID_CURRENT_PATH" for error in result.errors)
    
    def test_invalid_navigation_history(self):
        """Test validation of invalid navigation history"""
        invalid_context = {
            "current_path": "/dashboard/upload",
            "navigation_history": [
                {"path": "/invalid/route", "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "breadcrumbs": []
        }
        
        result = validate_navigation_context(invalid_context)
        assert not result.is_valid, "Invalid navigation history should fail"
        assert any(error.code == "INVALID_HISTORY_PATH" for error in result.errors)
    
    def test_invalid_breadcrumbs(self):
        """Test validation of invalid breadcrumbs"""
        invalid_context = {
            "current_path": "/dashboard/upload",
            "navigation_history": [],
            "breadcrumbs": [
                {"label": "Dashboard", "path": "/invalid/route"}
            ]
        }
        
        result = validate_navigation_context(invalid_context)
        assert not result.is_valid, "Invalid breadcrumbs should fail"
        assert any(error.code == "INVALID_BREADCRUMB_PATH" for error in result.errors)
    
    def test_breadcrumb_path_mismatch_warning(self):
        """Test warning for breadcrumb path mismatch"""
        context_with_mismatch = {
            "current_path": "/dashboard/upload",
            "navigation_history": [],
            "breadcrumbs": [
                {"label": "Dashboard", "path": "/dashboard"},
                {"label": "Results", "path": "/dashboard/results"}  # Mismatch with current_path
            ]
        }
        
        result = validate_navigation_context(context_with_mismatch)
        assert result.is_valid, "Context should be valid despite mismatch"
        assert len(result.warnings) > 0, "Should have warning for path mismatch"
        assert any(warning.code == "BREADCRUMB_PATH_MISMATCH" for warning in result.warnings)
    
    def test_large_navigation_history_warning(self):
        """Test warning for large navigation history"""
        large_history = []
        for i in range(60):  # Exceeds reasonable limit
            large_history.append({
                "path": f"/dashboard/results/{i}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        context_with_large_history = {
            "current_path": "/dashboard/upload",
            "navigation_history": large_history,
            "breadcrumbs": []
        }
        
        result = validate_navigation_context(context_with_large_history)
        assert result.is_valid, "Context should be valid despite large history"
        assert len(result.warnings) > 0, "Should have warning for large history"
        assert any(warning.code == "LARGE_NAVIGATION_HISTORY" for warning in result.warnings)


class TestRouteSecurityValidation:
    """Test cases for route security validation"""
    
    def test_sql_injection_patterns(self):
        """Test detection of SQL injection patterns"""
        malicious_routes = [
            "/dashboard/results' OR '1'='1",
            "/dashboard/history UNION SELECT * FROM users",
            "/dashboard/upload; DROP TABLE users",
            "/dashboard/reports' AND '1'='1"
        ]
        
        for route in malicious_routes:
            result = validate_route_security(route)
            assert not result.is_valid, f"Route {route} should be flagged as malicious"
            assert any(error.code == "SQL_INJECTION_PATTERN" for error in result.errors)
    
    def test_xss_patterns(self):
        """Test detection of XSS patterns"""
        malicious_routes = [
            "/dashboard/results<script>alert('xss')</script>",
            "/dashboard/history/javascript:alert('xss')",
            "/dashboard/upload onload=alert('xss')",
            "/dashboard/reports<iframe src='evil.com'>"
        ]
        
        for route in malicious_routes:
            result = validate_route_security(route)
            assert not result.is_valid, f"Route {route} should be flagged as malicious"
            assert any(error.code == "XSS_PATTERN" for error in result.errors)
    
    def test_command_injection_patterns(self):
        """Test detection of command injection patterns"""
        malicious_routes = [
            "/dashboard/results; rm -rf /",
            "/dashboard/history | cat /etc/passwd",
            "/dashboard/upload && whoami",
            "/dashboard/reports$(rm -rf /)"
        ]
        
        for route in malicious_routes:
            result = validate_route_security(route)
            assert not result.is_valid, f"Route {route} should be flagged as malicious"
            assert any(error.code == "COMMAND_INJECTION_PATTERN" for error in result.errors)
    
    def test_suspicious_characters_warning(self):
        """Test warning for suspicious characters"""
        routes_with_suspicious_chars = [
            "/dashboard/results<test>",
            "/dashboard/history\"test\"",
            "/dashboard/upload'test'",
            "/dashboard/reports&test"
        ]
        
        for route in routes_with_suspicious_chars:
            result = validate_route_security(route)
            assert result.is_valid, f"Route {route} should be valid but with warning"
            assert len(result.warnings) > 0, f"Route {route} should have warning"
            assert any(warning.code == "SUSPICIOUS_CHARACTERS" for warning in result.warnings)
    
    def test_clean_routes(self):
        """Test that clean routes pass security validation"""
        clean_routes = [
            "/dashboard/upload",
            "/dashboard/results",
            "/dashboard/history",
            "/dashboard/reports/123",
            "/dashboard/settings/profile"
        ]
        
        for route in clean_routes:
            result = validate_route_security(route)
            assert result.is_valid, f"Clean route {route} should pass security validation"
            assert len(result.errors) == 0, f"Clean route {route} should have no errors"


class TestUtilityFunctions:
    """Test cases for utility functions"""
    
    def test_get_allowed_routes(self):
        """Test getting allowed routes"""
        allowed_routes = get_allowed_routes()
        assert isinstance(allowed_routes, list), "Should return a list"
        assert len(allowed_routes) > 0, "Should have allowed routes"
        assert "/dashboard/upload" in allowed_routes, "Should include upload route"
        assert "/dashboard/results" in allowed_routes, "Should include results route"
    
    def test_is_route_allowed(self):
        """Test quick route allowed check"""
        assert is_route_allowed("/dashboard/upload"), "Upload route should be allowed"
        assert is_route_allowed("/dashboard/results"), "Results route should be allowed"
        assert not is_route_allowed("/invalid/route"), "Invalid route should not be allowed"
        assert not is_route_allowed("/dashboard/invalid"), "Invalid dashboard route should not be allowed"


class TestErrorHandling:
    """Test cases for error handling and edge cases"""
    
    def test_empty_input_handling(self):
        """Test handling of empty inputs"""
        empty_inputs = [None, "", "   "]
        
        for empty_input in empty_inputs:
            result = validate_navigation_route(empty_input)
            assert not result.is_valid, f"Empty input {empty_input} should be invalid"
            assert len(result.errors) > 0, f"Empty input {empty_input} should have errors"
    
    def test_malformed_data_handling(self):
        """Test handling of malformed data"""
        malformed_preferences = {
            "default_landing_page": 123,  # Wrong type
            "custom_navigation_order": "not_a_list",  # Wrong type
            "favorite_routes": None,  # Wrong type
        }
        
        result = validate_navigation_preferences(malformed_preferences)
        assert not result.is_valid, "Malformed preferences should be invalid"
        assert len(result.errors) > 0, "Malformed preferences should have errors"
    
    def test_exception_handling(self):
        """Test handling of unexpected exceptions"""
        # This test ensures that unexpected exceptions are caught and handled gracefully
        # We'll test with a context that might cause an unexpected error
        try:
            result = validate_navigation_context({"invalid": "data"})
            # Should not raise an exception, but might be invalid
            assert isinstance(result, ValidationResult), "Should return ValidationResult"
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")


def run_validation_tests():
    """Run all validation tests"""
    print("Running Navigation Data Validation Tests...")
    
    # Test route validation
    print("\n1. Testing Route Validation...")
    route_tests = TestNavigationRouteValidation()
    route_tests.test_valid_dashboard_routes()
    route_tests.test_valid_dynamic_routes()
    route_tests.test_invalid_route_prefixes()
    route_tests.test_path_traversal_attempts()
    route_tests.test_query_parameters_and_fragments()
    route_tests.test_invalid_route_types()
    route_tests.test_route_not_allowed()
    route_tests.test_long_route_warning()
    print("   ✓ Route validation tests passed")
    
    # Test preferences validation
    print("\n2. Testing Preferences Validation...")
    pref_tests = TestNavigationPreferencesValidation()
    pref_tests.test_valid_preferences()
    pref_tests.test_invalid_default_landing_page()
    pref_tests.test_invalid_custom_navigation_order()
    pref_tests.test_duplicate_routes_in_order()
    pref_tests.test_duplicate_favorite_routes()
    pref_tests.test_route_limits_exceeded()
    pref_tests.test_invalid_navigation_style()
    pref_tests.test_pydantic_model_validation()
    print("   ✓ Preferences validation tests passed")
    
    # Test context validation
    print("\n3. Testing Context Validation...")
    context_tests = TestNavigationContextValidation()
    context_tests.test_valid_context()
    context_tests.test_invalid_current_path()
    context_tests.test_invalid_navigation_history()
    context_tests.test_invalid_breadcrumbs()
    context_tests.test_breadcrumb_path_mismatch_warning()
    context_tests.test_large_navigation_history_warning()
    print("   ✓ Context validation tests passed")
    
    # Test security validation
    print("\n4. Testing Security Validation...")
    security_tests = TestRouteSecurityValidation()
    security_tests.test_sql_injection_patterns()
    security_tests.test_xss_patterns()
    security_tests.test_command_injection_patterns()
    security_tests.test_suspicious_characters_warning()
    security_tests.test_clean_routes()
    print("   ✓ Security validation tests passed")
    
    # Test utility functions
    print("\n5. Testing Utility Functions...")
    util_tests = TestUtilityFunctions()
    util_tests.test_get_allowed_routes()
    util_tests.test_is_route_allowed()
    print("   ✓ Utility function tests passed")
    
    # Test error handling
    print("\n6. Testing Error Handling...")
    error_tests = TestErrorHandling()
    error_tests.test_empty_input_handling()
    error_tests.test_malformed_data_handling()
    error_tests.test_exception_handling()
    print("   ✓ Error handling tests passed")
    
    print("\n🎉 All Navigation Data Validation Tests Passed!")
    print("\nSummary:")
    print("- Route validation: ✓")
    print("- Preferences validation: ✓")
    print("- Context validation: ✓")
    print("- Security validation: ✓")
    print("- Utility functions: ✓")
    print("- Error handling: ✓")


if __name__ == "__main__":
    run_validation_tests()
