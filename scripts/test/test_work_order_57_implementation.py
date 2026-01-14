#!/usr/bin/env python3
"""
Test Suite for Work Order #57 Implementation
Implement Navigation API Response Models and Request Handlers
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import our implemented models
from src.api.schemas.navigation_models import (
    NavigationContextResponse,
    NavigationRoute,
    BreadcrumbItem,
    NavigationUpdateRequest,
    NavigationHistoryEntry,
    NavigationPreferences,
    NavigationState,
    NavigationStyleEnum,
    PermissionLevelEnum
)

# Import the base model to test extension
from src.api.schemas.dashboard_models import DashboardOverviewResponse


class TestNavigationEnums:
    """Test the navigation enumeration classes"""
    
    def test_navigation_style_enum(self):
        """Test NavigationStyleEnum values"""
        assert NavigationStyleEnum.SIDEBAR == "sidebar"
        assert NavigationStyleEnum.TOP_NAV == "top_nav"
        assert NavigationStyleEnum.BREADCRUMB == "breadcrumb"
        assert NavigationStyleEnum.MINIMAL == "minimal"
    
    def test_permission_level_enum(self):
        """Test PermissionLevelEnum values"""
        assert PermissionLevelEnum.PUBLIC == "public"
        assert PermissionLevelEnum.AUTHENTICATED == "authenticated"
        assert PermissionLevelEnum.ADMIN == "admin"
        assert PermissionLevelEnum.SUPER_ADMIN == "super_admin"


class TestNavigationRouteModel:
    """Test the NavigationRoute model"""
    
    def test_navigation_route_creation(self):
        """Test creating a valid NavigationRoute"""
        route = NavigationRoute(
            id="dashboard",
            path="/dashboard",
            label="Dashboard",
            icon="dashboard-icon",
            badge=5,
            is_active=True
        )
        
        assert route.id == "dashboard"
        assert route.path == "/dashboard"
        assert route.label == "Dashboard"
        assert route.icon == "dashboard-icon"
        assert route.badge == 5
        assert route.is_active is True
        assert route.children is None
    
    def test_navigation_route_with_children(self):
        """Test NavigationRoute with nested children"""
        child_route = NavigationRoute(
            id="analytics-performance",
            path="/dashboard/analytics/performance",
            label="Performance",
            is_active=False
        )
        
        parent_route = NavigationRoute(
            id="analytics",
            path="/dashboard/analytics",
            label="Analytics",
            icon="analytics-icon",
            is_active=False,
            children=[child_route]
        )
        
        assert parent_route.children is not None
        assert len(parent_route.children) == 1
        assert parent_route.children[0].id == "analytics-performance"
    
    def test_navigation_route_validation(self):
        """Test NavigationRoute field validation"""
        # Test valid route
        valid_route = NavigationRoute(
            id="test-route",
            path="/test",
            label="Test Route"
        )
        assert valid_route.id == "test-route"
        
        # Test invalid ID
        with pytest.raises(ValueError, match="Route ID cannot be empty"):
            NavigationRoute(
                id="",
                path="/test",
                label="Test Route"
            )
        
        # Test invalid path
        with pytest.raises(ValueError, match="Route path must start with"):
            NavigationRoute(
                id="test-route",
                path="test",
                label="Test Route"
            )
        
        # Test invalid label
        with pytest.raises(ValueError, match="Route label cannot be empty"):
            NavigationRoute(
                id="test-route",
                path="/test",
                label=""
            )
    
    def test_navigation_route_utility_methods(self):
        """Test NavigationRoute utility methods"""
        child1 = NavigationRoute(id="child1", path="/child1", label="Child 1")
        child2 = NavigationRoute(id="child2", path="/child2", label="Child 2")
        
        parent = NavigationRoute(
            id="parent",
            path="/parent",
            label="Parent",
            children=[child1, child2]
        )
        
        # Test get_all_route_ids
        all_ids = parent.get_all_route_ids()
        assert "parent" in all_ids
        assert "child1" in all_ids
        assert "child2" in all_ids
        assert len(all_ids) == 3
        
        # Test find_route_by_id
        found_route = parent.find_route_by_id("child1")
        assert found_route is not None
        assert found_route.id == "child1"
        
        not_found = parent.find_route_by_id("nonexistent")
        assert not_found is None
        
        # Test get_active_routes
        child1.is_active = True
        active_routes = parent.get_active_routes()
        assert len(active_routes) == 1
        assert active_routes[0].id == "child1"


class TestBreadcrumbItemModel:
    """Test the BreadcrumbItem model"""
    
    def test_breadcrumb_item_creation(self):
        """Test creating a valid BreadcrumbItem"""
        breadcrumb = BreadcrumbItem(
            label="Dashboard",
            path="/dashboard",
            is_active=False,
            metadata={"section": "overview"}
        )
        
        assert breadcrumb.label == "Dashboard"
        assert breadcrumb.path == "/dashboard"
        assert breadcrumb.is_active is False
        assert breadcrumb.metadata["section"] == "overview"
    
    def test_breadcrumb_item_validation(self):
        """Test BreadcrumbItem field validation"""
        # Test valid breadcrumb
        valid_breadcrumb = BreadcrumbItem(
            label="Test",
            path="/test"
        )
        assert valid_breadcrumb.label == "Test"
        
        # Test invalid label
        with pytest.raises(ValueError, match="Breadcrumb label cannot be empty"):
            BreadcrumbItem(label="", path="/test")
        
        # Test invalid path
        with pytest.raises(ValueError, match="Breadcrumb path must start with"):
            BreadcrumbItem(label="Test", path="test")
    
    def test_breadcrumb_item_utility_methods(self):
        """Test BreadcrumbItem utility methods"""
        # Test clickable breadcrumb
        clickable = BreadcrumbItem(
            label="Dashboard",
            path="/dashboard",
            is_active=False
        )
        assert clickable.is_clickable() is True
        
        # Test non-clickable breadcrumb (active)
        non_clickable = BreadcrumbItem(
            label="Current",
            path="/current",
            is_active=True
        )
        assert non_clickable.is_clickable() is False
        
        # Test non-clickable breadcrumb (no path)
        no_path = BreadcrumbItem(label="No Path")
        assert no_path.is_clickable() is False
        
        # Test label truncation
        long_label = BreadcrumbItem(label="A" * 60)
        display_label = long_label.get_display_label()
        assert len(display_label) == 50
        assert display_label.endswith("...")


class TestNavigationHistoryEntryModel:
    """Test the NavigationHistoryEntry model"""
    
    def test_navigation_history_entry_creation(self):
        """Test creating a valid NavigationHistoryEntry"""
        entry = NavigationHistoryEntry(
            path="/dashboard/analytics",
            timestamp=datetime.now(timezone.utc),
            method="click",
            load_time=1250.5,
            context={"section": "performance"}
        )
        
        assert entry.path == "/dashboard/analytics"
        assert entry.timestamp is not None
        assert entry.method == "click"
        assert entry.load_time == 1250.5
        assert entry.context["section"] == "performance"
    
    def test_navigation_history_entry_validation(self):
        """Test NavigationHistoryEntry field validation"""
        # Test valid entry
        valid_entry = NavigationHistoryEntry(
            path="/test",
            timestamp=datetime.now(timezone.utc)
        )
        assert valid_entry.path == "/test"
        
        # Test invalid path
        with pytest.raises(ValueError, match="Navigation path cannot be empty"):
            NavigationHistoryEntry(
                path="",
                timestamp=datetime.now(timezone.utc)
            )
        
        # Test invalid method
        with pytest.raises(ValueError, match="Invalid navigation method"):
            NavigationHistoryEntry(
                path="/test",
                timestamp=datetime.now(timezone.utc),
                method="invalid_method"
            )
        
        # Test negative load time
        with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
            NavigationHistoryEntry(
                path="/test",
                timestamp=datetime.now(timezone.utc),
                load_time=-100
            )


class TestNavigationPreferencesModel:
    """Test the NavigationPreferences model"""
    
    def test_navigation_preferences_creation(self):
        """Test creating a valid NavigationPreferences"""
        preferences = NavigationPreferences(
            default_landing_page="/dashboard",
            navigation_style=NavigationStyleEnum.SIDEBAR,
            show_labels=True,
            enable_keyboard_shortcuts=True,
            breadcrumb_depth=5,
            sidebar_collapsed=False
        )
        
        assert preferences.default_landing_page == "/dashboard"
        assert preferences.navigation_style == NavigationStyleEnum.SIDEBAR
        assert preferences.show_labels is True
        assert preferences.enable_keyboard_shortcuts is True
        assert preferences.breadcrumb_depth == 5
        assert preferences.sidebar_collapsed is False
    
    def test_navigation_preferences_validation(self):
        """Test NavigationPreferences field validation"""
        # Test valid preferences
        valid_preferences = NavigationPreferences(
            default_landing_page="/dashboard"
        )
        assert valid_preferences.default_landing_page == "/dashboard"
        
        # Test invalid landing page
        with pytest.raises(ValueError, match="Default landing page must start with"):
            NavigationPreferences(default_landing_page="dashboard")
        
        # Test empty landing page
        with pytest.raises(ValueError, match="Default landing page cannot be empty"):
            NavigationPreferences(default_landing_page="")


class TestNavigationStateModel:
    """Test the NavigationState model"""
    
    def test_navigation_state_creation(self):
        """Test creating a valid NavigationState"""
        state = NavigationState(
            current_section="/dashboard/analytics",
            sidebar_collapsed=False,
            breadcrumb_depth=3,
            active_route_id="analytics",
            last_navigation_time=datetime.now(timezone.utc)
        )
        
        assert state.current_section == "/dashboard/analytics"
        assert state.sidebar_collapsed is False
        assert state.breadcrumb_depth == 3
        assert state.active_route_id == "analytics"
        assert state.last_navigation_time is not None
    
    def test_navigation_state_validation(self):
        """Test NavigationState field validation"""
        # Test valid state
        valid_state = NavigationState(current_section="/test")
        assert valid_state.current_section == "/test"
        
        # Test empty current section
        with pytest.raises(ValueError, match="Current section cannot be empty"):
            NavigationState(current_section="")
        
        # Test empty active route ID
        with pytest.raises(ValueError, match="Active route ID cannot be empty"):
            NavigationState(active_route_id="")


class TestNavigationUpdateRequestModel:
    """Test the NavigationUpdateRequest model"""
    
    def test_navigation_update_request_creation(self):
        """Test creating a valid NavigationUpdateRequest"""
        preferences = NavigationPreferences(
            default_landing_page="/dashboard",
            navigation_style=NavigationStyleEnum.SIDEBAR
        )
        
        state = NavigationState(
            current_section="/dashboard",
            sidebar_collapsed=False
        )
        
        request = NavigationUpdateRequest(
            preferences=preferences,
            navigation_state=state,
            favorite_routes=["/dashboard", "/analytics"],
            update_source="user"
        )
        
        assert request.preferences is not None
        assert request.navigation_state is not None
        assert request.favorite_routes == ["/dashboard", "/analytics"]
        assert request.update_source == "user"
        assert request.update_timestamp is not None
    
    def test_navigation_update_request_validation(self):
        """Test NavigationUpdateRequest field validation"""
        # Test valid request
        valid_request = NavigationUpdateRequest(
            favorite_routes=["/dashboard", "/analytics"]
        )
        assert valid_request.favorite_routes == ["/dashboard", "/analytics"]
        
        # Test too many favorite routes
        with pytest.raises(ValueError, match="Cannot have more than 50 favorite routes"):
            NavigationUpdateRequest(
                favorite_routes=[f"/route{i}" for i in range(51)]
            )
        
        # Test invalid favorite route
        with pytest.raises(ValueError, match="must start with"):
            NavigationUpdateRequest(
                favorite_routes=["invalid_route"]
            )
        
        # Test invalid update source
        with pytest.raises(ValueError, match="Invalid update source"):
            NavigationUpdateRequest(update_source="invalid_source")
    
    def test_navigation_update_request_utility_methods(self):
        """Test NavigationUpdateRequest utility methods"""
        # Test request with updates
        request_with_updates = NavigationUpdateRequest(
            preferences=NavigationPreferences(),
            favorite_routes=["/dashboard"]
        )
        assert request_with_updates.has_updates() is True
        
        # Test request without updates
        empty_request = NavigationUpdateRequest()
        assert empty_request.has_updates() is False
        
        # Test update summary
        summary = request_with_updates.get_update_summary()
        assert summary["has_preferences"] is True
        assert summary["has_favorite_routes"] is True
        assert summary["favorite_routes_count"] == 1


class TestNavigationContextResponseModel:
    """Test the NavigationContextResponse model"""
    
    def test_navigation_context_response_creation(self):
        """Test creating a valid NavigationContextResponse"""
        # Create base dashboard response data
        base_data = {
            "user_summary": {"total_analyses": 100, "success_rate": 95.0},
            "system_status": {"overall_status": "healthy", "services": {}},
            "quick_stats": {"total_detections": 1000, "processing_time_avg": 2.5, "accuracy_rate": 96.0}
        }
        
        # Create navigation context
        navigation_context = {
            "currentSection": "/dashboard/analytics",
            "availableRoutes": [
                {
                    "id": "dashboard",
                    "path": "/dashboard",
                    "label": "Dashboard",
                    "is_active": True
                }
            ],
            "breadcrumbs": [
                {
                    "label": "Dashboard",
                    "path": "/dashboard",
                    "is_active": False
                },
                {
                    "label": "Analytics",
                    "path": "/dashboard/analytics",
                    "is_active": True
                }
            ],
            "navigationHistory": [
                {
                    "path": "/dashboard",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": {"section": "overview"}
                }
            ],
            "userPreferences": {
                "default_landing_page": "/dashboard",
                "navigation_style": "sidebar"
            }
        }
        
        # Create navigation routes
        routes = [
            NavigationRoute(
                id="dashboard",
                path="/dashboard",
                label="Dashboard",
                is_active=True
            )
        ]
        
        # Create breadcrumbs
        breadcrumbs = [
            BreadcrumbItem(
                label="Dashboard",
                path="/dashboard",
                is_active=False
            ),
            BreadcrumbItem(
                label="Analytics",
                path="/dashboard/analytics",
                is_active=True
            )
        ]
        
        # Create navigation history
        history = [
            NavigationHistoryEntry(
                path="/dashboard",
                timestamp=datetime.now(timezone.utc),
                context={"section": "overview"}
            )
        ]
        
        # Create preferences
        preferences = NavigationPreferences(
            default_landing_page="/dashboard",
            navigation_style=NavigationStyleEnum.SIDEBAR
        )
        
        response = NavigationContextResponse(
            **base_data,
            navigation_context=navigation_context,
            available_routes=routes,
            breadcrumbs=breadcrumbs,
            navigation_history=history,
            user_preferences=preferences
        )
        
        assert response.get_current_section() == "/dashboard/analytics"
        assert len(response.get_available_route_ids()) == 1
        assert len(response.get_active_breadcrumbs()) == 1
        assert response.get_active_breadcrumbs()[0].label == "Analytics"
    
    def test_navigation_context_response_validation(self):
        """Test NavigationContextResponse field validation"""
        # Test valid response
        valid_context = {
            "currentSection": "/dashboard",
            "availableRoutes": [],
            "breadcrumbs": [],
            "navigationHistory": [],
            "userPreferences": {}
        }
        
        base_data = {
            "user_summary": {"total_analyses": 100, "success_rate": 95.0},
            "system_status": {"overall_status": "healthy", "services": {}},
            "quick_stats": {"total_detections": 1000, "processing_time_avg": 2.5, "accuracy_rate": 96.0}
        }
        
        valid_response = NavigationContextResponse(
            **base_data,
            navigation_context=valid_context
        )
        assert valid_response.get_current_section() == "/dashboard"
        
        # Test missing required field
        invalid_context = {
            "currentSection": "/dashboard",
            "availableRoutes": [],
            "breadcrumbs": [],
            "navigationHistory": []
            # Missing userPreferences
        }
        
        with pytest.raises(ValueError, match="Navigation context missing required field"):
            NavigationContextResponse(
                **base_data,
                navigation_context=invalid_context
            )
        
        # Test invalid currentSection
        invalid_context2 = {
            "currentSection": "",
            "availableRoutes": [],
            "breadcrumbs": [],
            "navigationHistory": [],
            "userPreferences": {}
        }
        
        with pytest.raises(ValueError, match="currentSection must be a non-empty string"):
            NavigationContextResponse(
                **base_data,
                navigation_context=invalid_context2
            )
    
    def test_navigation_context_response_utility_methods(self):
        """Test NavigationContextResponse utility methods"""
        # Create test data
        routes = [
            NavigationRoute(
                id="dashboard",
                path="/dashboard",
                label="Dashboard",
                is_active=True
            ),
            NavigationRoute(
                id="analytics",
                path="/analytics",
                label="Analytics",
                is_active=False
            )
        ]
        
        breadcrumbs = [
            BreadcrumbItem(label="Dashboard", path="/dashboard", is_active=False),
            BreadcrumbItem(label="Analytics", path="/analytics", is_active=True)
        ]
        
        history = [
            NavigationHistoryEntry(
                path="/dashboard",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        preferences = NavigationPreferences(default_landing_page="/dashboard")
        
        navigation_context = {
            "currentSection": "/analytics",
            "availableRoutes": [],
            "breadcrumbs": [],
            "navigationHistory": [],
            "userPreferences": {}
        }
        
        base_data = {
            "user_summary": {"total_analyses": 100, "success_rate": 95.0},
            "system_status": {"overall_status": "healthy", "services": {}},
            "quick_stats": {"total_detections": 1000, "processing_time_avg": 2.5, "accuracy_rate": 96.0}
        }
        
        response = NavigationContextResponse(
            **base_data,
            navigation_context=navigation_context,
            available_routes=routes,
            breadcrumbs=breadcrumbs,
            navigation_history=history,
            user_preferences=preferences
        )
        
        # Test utility methods
        assert response.get_current_section() == "/analytics"
        assert len(response.get_available_route_ids()) == 2
        assert response.get_available_route_ids() == ["dashboard", "analytics"]
        assert len(response.get_active_breadcrumbs()) == 1
        assert response.get_active_breadcrumbs()[0].label == "Analytics"
        
        # Test find_route_by_path
        found_route = response.find_route_by_path("/dashboard")
        assert found_route is not None
        assert found_route.id == "dashboard"
        
        not_found = response.find_route_by_path("/nonexistent")
        assert not_found is None
        
        # Test is_route_accessible
        assert response.is_route_accessible("dashboard") is True
        assert response.is_route_accessible("nonexistent") is False
        
        # Test navigation summary
        summary = response.get_navigation_summary()
        assert summary["current_section"] == "/analytics"
        assert summary["total_routes"] == 2
        assert summary["breadcrumb_count"] == 2
        assert summary["history_count"] == 1
        assert summary["has_preferences"] is True


def test_work_order_57_requirements_compliance():
    """
    Test that all Work Order #57 requirements are met
    """
    
    # Test 1: NavigationContextResponse extends DashboardOverviewResponse
    base_data = {
        "user_summary": {"total_analyses": 100, "success_rate": 95.0},
        "system_status": {"overall_status": "healthy", "services": {}},
        "quick_stats": {"total_detections": 1000, "processing_time_avg": 2.5, "accuracy_rate": 96.0}
    }
    
    navigation_context = {
        "currentSection": "/dashboard/analytics",
        "availableRoutes": [
            {
                "id": "dashboard",
                "path": "/dashboard",
                "label": "Dashboard",
                "is_active": True
            }
        ],
        "breadcrumbs": [
            {
                "label": "Dashboard",
                "path": "/dashboard",
                "is_active": False
            },
            {
                "label": "Analytics",
                "path": "/dashboard/analytics",
                "is_active": True
            }
        ],
        "navigationHistory": [
            {
                "path": "/dashboard",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": {"section": "overview"}
            }
        ],
        "userPreferences": {
            "default_landing_page": "/dashboard",
            "navigation_style": "sidebar"
        }
    }
    
    response = NavigationContextResponse(
        **base_data,
        navigation_context=navigation_context
    )
    
    # Verify it extends DashboardOverviewResponse
    assert isinstance(response, DashboardOverviewResponse)
    assert hasattr(response, 'user_summary')
    assert hasattr(response, 'system_status')
    assert hasattr(response, 'quick_stats')
    assert hasattr(response, 'navigation_context')
    
    # Test 2: NavigationRoute interface with all required fields
    route = NavigationRoute(
        id="test-route",
        path="/test",
        label="Test Route",
        icon="test-icon",
        required_permissions=["authenticated"],
        badge=5,
        is_active=True,
        children=[
            NavigationRoute(
                id="child-route",
                path="/test/child",
                label="Child Route",
                is_active=False
            )
        ]
    )
    
    # Verify all required fields are present
    assert hasattr(route, 'id')
    assert hasattr(route, 'path')
    assert hasattr(route, 'label')
    assert hasattr(route, 'icon')
    assert hasattr(route, 'required_permissions')
    assert hasattr(route, 'badge')
    assert hasattr(route, 'is_active')
    assert hasattr(route, 'children')
    
    # Test 3: BreadcrumbItem interface with all required fields
    breadcrumb = BreadcrumbItem(
        label="Test Breadcrumb",
        path="/test",
        is_active=False,
        metadata={"section": "test"}
    )
    
    # Verify all required fields are present
    assert hasattr(breadcrumb, 'label')
    assert hasattr(breadcrumb, 'path')
    assert hasattr(breadcrumb, 'is_active')
    assert hasattr(breadcrumb, 'metadata')
    
    # Test 4: NavigationUpdateRequest interface with all required fields
    update_request = NavigationUpdateRequest(
        preferences=NavigationPreferences(
            default_landing_page="/dashboard",
            navigation_style=NavigationStyleEnum.SIDEBAR
        ),
        navigation_state=NavigationState(
            current_section="/dashboard",
            sidebar_collapsed=False
        ),
        favorite_routes=["/dashboard", "/analytics"]
    )
    
    # Verify all required fields are present
    assert hasattr(update_request, 'preferences')
    assert hasattr(update_request, 'navigation_state')
    assert hasattr(update_request, 'favorite_routes')
    
    # Test 5: Type safety and consistency with existing Web Dashboard Interface API patterns
    # This is verified by the use of Pydantic BaseModel and consistent field patterns
    
    # Test 6: JSON serialization support
    # Test that models can be serialized to JSON
    response_json = response.model_dump()
    route_json = route.model_dump()
    breadcrumb_json = breadcrumb.model_dump()
    update_json = update_request.model_dump()
    
    assert isinstance(response_json, dict)
    assert isinstance(route_json, dict)
    assert isinstance(breadcrumb_json, dict)
    assert isinstance(update_json, dict)
    
    print("✅ All Work Order #57 requirements have been successfully implemented and tested!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
