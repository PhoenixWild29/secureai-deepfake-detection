#!/usr/bin/env python3
"""
Navigation Context API Tests
Comprehensive test suite for the navigation context API endpoint
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.dashboard.navigation_context import router
from src.services.navigation_service import NavigationService
from src.services.user_preferences_service import UserPreferencesService
from src.models.navigation import (
    NavigationState,
    NavigationSection,
    NavigationItem,
    NavigationItemType,
    NavigationPermission,
    CurrentRouteContext,
    NavigationPreferences,
    BreadcrumbItem
)
from src.dependencies.auth import UserClaims


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestNavigationContextAPI:
    """Test suite for navigation context API endpoint"""
    
    @pytest.fixture
    def mock_user_claims(self):
        """Mock user claims for testing"""
        return UserClaims(
            user_id="test_user_123",
            email="test@example.com",
            username="testuser",
            groups=["analyst"],
            roles=["analyst"],
            exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc),
            iss="test_issuer",
            aud="test_audience"
        )
    
    @pytest.fixture
    def mock_navigation_state(self):
        """Mock navigation state for testing"""
        return NavigationState(
            current_context=CurrentRouteContext(
                path="/dashboard/analytics",
                section_id="dashboard",
                page_id="analytics",
                breadcrumbs=[
                    BreadcrumbItem(
                        label="Home",
                        path="/dashboard",
                        is_active=False,
                        icon=None,
                        metadata=None
                    ),
                    BreadcrumbItem(
                        label="Analytics",
                        path="/dashboard/analytics",
                        is_active=True,
                        icon=None,
                        metadata=None
                    )
                ],
                page_title="Analytics",
                page_description="Analytics and insights",
                metadata=None
            ),
            available_sections=[
                NavigationSection(
                    id="dashboard",
                    label="Dashboard",
                    icon="home",
                    description="Main dashboard overview",
                    order=1,
                    items=[
                        NavigationItem(
                            id="analytics",
                            label="Analytics",
                            path="/dashboard/analytics",
                            type=NavigationItemType.PAGE,
                            icon="bar-chart",
                            description="Analytics and insights",
                            required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None,
                            badge=None,
                            metadata=None
                        )
                    ],
                    metadata=None
                )
            ],
            user_preferences=NavigationPreferences(
                user_id="test_user_123",
                sidebar_collapsed=False,
                sidebar_width=280,
                show_breadcrumbs=True,
                show_page_titles=True,
                navigation_style="default",
                favorite_items=[],
                recent_items=["/dashboard", "/dashboard/analytics"],
                custom_sections=[],
                last_updated=datetime.now(timezone.utc)
            ),
            quick_actions=[],
            recent_navigation=[],
            suggested_items=[],
            notifications_count=0
        )
    
    @pytest.fixture
    def mock_navigation_history(self):
        """Mock navigation history for testing"""
        return [
            {
                "route_path": "/dashboard/analytics",
                "route_title": "Analytics",
                "timestamp": "2024-01-15T10:30:00Z",
                "user_agent": "dashboard",
                "session_id": "session_test_user_123_1705315800"
            },
            {
                "route_path": "/dashboard",
                "route_title": "Dashboard Overview",
                "timestamp": "2024-01-15T10:25:00Z",
                "user_agent": "dashboard",
                "session_id": "session_test_user_123_1705315500"
            }
        ]
    
    @pytest.fixture
    def mock_navigation_patterns(self):
        """Mock navigation patterns for testing"""
        return {
            "most_visited_routes": [
                {"route": "/dashboard", "count": 15},
                {"route": "/dashboard/analytics", "count": 8},
                {"route": "/dashboard/upload", "count": 5}
            ],
            "navigation_frequency": {
                "/dashboard": 15,
                "/dashboard/analytics": 8,
                "/dashboard/upload": 5
            },
            "average_session_duration": 24,
            "common_navigation_paths": [
                {"path": "/dashboard -> /dashboard/analytics", "frequency": 6},
                {"path": "/dashboard/analytics -> /dashboard", "frequency": 4}
            ],
            "total_navigation_events": 28,
            "last_analyzed": "2024-01-15T10:30:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_get_navigation_context_success(self, mock_user_claims, mock_navigation_state, mock_navigation_history, mock_navigation_patterns):
        """Test successful navigation context retrieval"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.return_value = {
                "navigation_state": mock_navigation_state,
                "navigation_history": mock_navigation_history,
                "navigation_patterns": mock_navigation_patterns,
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "test_user_123"
            }
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.get(
                    "/api/v1/dashboard/navigation/context",
                    params={
                        "current_path": "/dashboard/analytics",
                        "include_history": True,
                        "include_patterns": True
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "navigation_state" in data
            assert "navigation_history" in data
            assert "navigation_patterns" in data
            assert "timestamp" in data
            assert "user_id" in data
            assert "response_time_ms" in data
            assert "request_id" in data
            assert "cache_info" in data
            
            # Verify navigation state
            nav_state = data["navigation_state"]
            assert nav_state["current_context"]["path"] == "/dashboard/analytics"
            assert nav_state["current_context"]["page_title"] == "Analytics"
            assert len(nav_state["current_context"]["breadcrumbs"]) == 2
            
            # Verify navigation history
            history = data["navigation_history"]
            assert len(history) == 2
            assert history[0]["route_path"] == "/dashboard/analytics"
            
            # Verify navigation patterns
            patterns = data["navigation_patterns"]
            assert len(patterns["most_visited_routes"]) == 3
            assert patterns["total_navigation_events"] == 28
    
    @pytest.mark.asyncio
    async def test_get_navigation_context_anonymous_user(self, mock_navigation_state):
        """Test navigation context for anonymous user"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.return_value = {
                "navigation_state": mock_navigation_state,
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "anonymous"
            }
            mock_get_service.return_value = mock_service
            
            # Mock no authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=None):
                response = client.get(
                    "/api/v1/dashboard/navigation/context",
                    params={"current_path": "/dashboard"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify anonymous user response
            assert data["user_id"] == "anonymous"
            assert "navigation_history" not in data
            assert "navigation_patterns" not in data
    
    @pytest.mark.asyncio
    async def test_get_navigation_context_without_history(self, mock_user_claims, mock_navigation_state):
        """Test navigation context without history"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.return_value = {
                "navigation_state": mock_navigation_state,
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "test_user_123"
            }
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.get(
                    "/api/v1/dashboard/navigation/context",
                    params={
                        "current_path": "/dashboard/analytics",
                        "include_history": False,
                        "include_patterns": False
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify no history or patterns included
            assert "navigation_history" not in data
            assert "navigation_patterns" not in data
    
    @pytest.mark.asyncio
    async def test_get_navigation_context_error_handling(self):
        """Test error handling in navigation context endpoint"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock service to raise exception
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.side_effect = Exception("Service error")
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=None):
                response = client.get("/api/v1/dashboard/navigation/context")
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Internal server error" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_track_navigation_event_success(self, mock_user_claims):
        """Test successful navigation event tracking"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.track_navigation_event.return_value = True
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.post(
                    "/api/v1/dashboard/navigation/track",
                    params={
                        "route_path": "/dashboard/analytics",
                        "route_title": "Analytics"
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "Navigation event tracked successfully" in data["message"]
            assert "request_id" in data
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_track_navigation_event_unauthorized(self):
        """Test navigation event tracking without authentication"""
        with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=None):
            response = client.post(
                "/api/v1/dashboard/navigation/track",
                params={"route_path": "/dashboard/analytics"}
            )
        
        assert response.status_code == 401
        data = response.json()
        assert "Authentication required" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_navigation_history_success(self, mock_user_claims, mock_navigation_history):
        """Test successful navigation history retrieval"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_navigation_history.return_value = mock_navigation_history
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.get(
                    "/api/v1/dashboard/navigation/history",
                    params={"limit": 10}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "history" in data
            assert "total_entries" in data
            assert "returned_entries" in data
            assert len(data["history"]) == 2
            assert data["total_entries"] == 2
            assert data["returned_entries"] == 2
    
    @pytest.mark.asyncio
    async def test_get_navigation_patterns_success(self, mock_user_claims, mock_navigation_patterns):
        """Test successful navigation patterns retrieval"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_navigation_patterns.return_value = mock_navigation_patterns
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.get("/api/v1/dashboard/navigation/patterns")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "patterns" in data
            assert "request_id" in data
            assert "timestamp" in data
            
            patterns = data["patterns"]
            assert len(patterns["most_visited_routes"]) == 3
            assert patterns["total_navigation_events"] == 28
    
    @pytest.mark.asyncio
    async def test_invalidate_navigation_cache_success(self, mock_user_claims):
        """Test successful navigation cache invalidation"""
        with patch('src.api.v1.dashboard.navigation_context.get_dashboard_cache_manager') as mock_get_cache:
            # Mock cache manager
            mock_cache_manager = AsyncMock()
            mock_cache_manager.invalidate_navigation_cache.return_value = None
            mock_get_cache.return_value = mock_cache_manager
            
            # Mock authentication with admin role
            admin_claims = UserClaims(
                user_id="admin_user",
                email="admin@example.com",
                username="admin",
                groups=["admin"],
                roles=["admin"],
                exp=datetime.now(timezone.utc),
                iat=datetime.now(timezone.utc),
                iss="test_issuer",
                aud="test_audience"
            )
            
            with patch('src.api.v1.dashboard.navigation_context.require_permission', return_value=admin_claims):
                response = client.post(
                    "/api/v1/dashboard/navigation/cache/invalidate",
                    params={"user_id": "test_user_123"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "Navigation cache invalidated for user test_user_123" in data["message"]
    
    @pytest.mark.asyncio
    async def test_navigation_context_performance(self, mock_user_claims, mock_navigation_state):
        """Test navigation context response time performance"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.return_value = {
                "navigation_state": mock_navigation_state,
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "test_user_123"
            }
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                response = client.get("/api/v1/dashboard/navigation/context")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response time is reasonable (should be under 100ms in real scenario)
            response_time = data["response_time_ms"]
            assert response_time >= 0
            assert response_time < 1000  # Allow some margin for test environment
    
    @pytest.mark.asyncio
    async def test_navigation_context_caching(self, mock_user_claims, mock_navigation_state):
        """Test navigation context caching behavior"""
        with patch('src.api.v1.dashboard.navigation_context.get_navigation_service') as mock_get_service:
            # Mock navigation service
            mock_service = AsyncMock()
            mock_service.get_enhanced_navigation_context.return_value = {
                "navigation_state": mock_navigation_state,
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "test_user_123"
            }
            mock_get_service.return_value = mock_service
            
            # Mock authentication
            with patch('src.api.v1.dashboard.navigation_context.get_current_user_optional', return_value=mock_user_claims):
                # First request
                response1 = client.get("/api/v1/dashboard/navigation/context")
                assert response1.status_code == 200
                
                # Second request (should potentially use cache)
                response2 = client.get("/api/v1/dashboard/navigation/context")
                assert response2.status_code == 200
                
                # Verify cache info is present
                data1 = response1.json()
                data2 = response2.json()
                
                assert "cache_info" in data1
                assert "cache_info" in data2
                assert "cache_hit" in data1["cache_info"]
                assert "cache_hit" in data2["cache_info"]


class TestNavigationServiceIntegration:
    """Integration tests for navigation service"""
    
    @pytest.mark.asyncio
    async def test_navigation_service_tracking_integration(self):
        """Test navigation service tracking integration"""
        # This would test the actual service integration
        # For now, we'll mock the dependencies
        pass
    
    @pytest.mark.asyncio
    async def test_user_preferences_service_integration(self):
        """Test user preferences service integration"""
        # This would test the actual service integration
        # For now, we'll mock the dependencies
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
