#!/usr/bin/env python3
"""
Navigation Data Validation and Route Verification
Pydantic models and validation functions for navigation data integrity and security
"""

import re
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError as PydanticValidationError
from urllib.parse import urlparse, parse_qs


class ValidationSeverity(str, Enum):
    """Validation error severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class NavigationValidationError(BaseModel):
    """Individual validation error"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    severity: ValidationSeverity = Field(default=ValidationSeverity.ERROR, description="Error severity")
    code: Optional[str] = Field(None, description="Error code for programmatic handling")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ValidationResult(BaseModel):
    """Result of validation operation"""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[NavigationValidationError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[NavigationValidationError] = Field(default_factory=list, description="List of validation warnings")
    validated_data: Optional[Dict[str, Any]] = Field(None, description="Validated and cleaned data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional validation metadata")


class NavigationPreferences(BaseModel):
    """Navigation preferences model with validation"""
    default_landing_page: str = Field(..., description="Default landing page route")
    custom_navigation_order: List[str] = Field(default_factory=list, description="Custom navigation order")
    show_breadcrumbs: bool = Field(default=True, description="Whether to show breadcrumbs")
    sidebar_collapsed: bool = Field(default=False, description="Whether sidebar is collapsed by default")
    theme_preference: Optional[str] = Field(None, description="Theme preference")
    language_preference: Optional[str] = Field(None, description="Language preference")
    favorite_routes: List[str] = Field(default_factory=list, description="User's favorite routes")
    recent_routes: List[str] = Field(default_factory=list, description="Recently visited routes")
    navigation_style: str = Field(default="sidebar", description="Navigation style preference")
    auto_save_preferences: bool = Field(default=True, description="Whether to auto-save preferences")
    max_recent_routes: int = Field(default=10, description="Maximum number of recent routes to store")
    max_favorite_routes: int = Field(default=20, description="Maximum number of favorite routes")

    @field_validator('default_landing_page')
    @classmethod
    def validate_default_landing_page(cls, v):
        """Validate default landing page route"""
        if not v or not isinstance(v, str):
            raise ValueError("Default landing page must be a non-empty string")
        
        # Check if it's a valid dashboard route
        if not v.startswith('/dashboard/'):
            raise ValueError("Default landing page must be a dashboard route starting with /dashboard/")
        
        return v

    @field_validator('custom_navigation_order')
    @classmethod
    def validate_custom_navigation_order(cls, v):
        """Validate custom navigation order"""
        if not isinstance(v, list):
            raise ValueError("Custom navigation order must be a list")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Custom navigation order cannot contain duplicates")
        
        # Validate each route in the order
        for route in v:
            if not isinstance(route, str) or not route.startswith('/dashboard/'):
                raise ValueError(f"Invalid route in custom navigation order: {route}")
        
        return v

    @field_validator('favorite_routes')
    @classmethod
    def validate_favorite_routes(cls, v):
        """Validate favorite routes"""
        if not isinstance(v, list):
            raise ValueError("Favorite routes must be a list")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Favorite routes cannot contain duplicates")
        
        # Validate each favorite route
        for route in v:
            if not isinstance(route, str) or not route.startswith('/dashboard/'):
                raise ValueError(f"Invalid favorite route: {route}")
        
        return v

    @field_validator('recent_routes')
    @classmethod
    def validate_recent_routes(cls, v):
        """Validate recent routes"""
        if not isinstance(v, list):
            raise ValueError("Recent routes must be a list")
        
        # Validate each recent route
        for route in v:
            if not isinstance(route, str) or not route.startswith('/dashboard/'):
                raise ValueError(f"Invalid recent route: {route}")
        
        return v

    @field_validator('navigation_style')
    @classmethod
    def validate_navigation_style(cls, v):
        """Validate navigation style"""
        valid_styles = ['sidebar', 'top_nav', 'breadcrumb', 'minimal']
        if v not in valid_styles:
            raise ValueError(f"Navigation style must be one of: {', '.join(valid_styles)}")
        return v

    @field_validator('max_recent_routes', 'max_favorite_routes')
    @classmethod
    def validate_max_routes(cls, v):
        """Validate maximum route limits"""
        if not isinstance(v, int) or v < 1 or v > 100:
            raise ValueError("Maximum routes must be an integer between 1 and 100")
        return v

    @model_validator(mode='after')
    def validate_route_limits(self):
        """Validate that route lists don't exceed maximum limits"""
        if len(self.favorite_routes) > self.max_favorite_routes:
            raise ValueError(f"Number of favorite routes ({len(self.favorite_routes)}) exceeds maximum ({self.max_favorite_routes})")
        
        if len(self.recent_routes) > self.max_recent_routes:
            raise ValueError(f"Number of recent routes ({len(self.recent_routes)}) exceeds maximum ({self.max_recent_routes})")
        
        return self


class NavigationContext(BaseModel):
    """Navigation context data model with validation"""
    current_path: str = Field(..., description="Current navigation path")
    navigation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Navigation history")
    breadcrumbs: List[Dict[str, Any]] = Field(default_factory=list, description="Current breadcrumbs")
    active_route: Optional[str] = Field(None, description="Currently active route")
    previous_route: Optional[str] = Field(None, description="Previous route")
    route_metadata: Dict[str, Any] = Field(default_factory=dict, description="Route metadata")
    user_permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="Session identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Context timestamp")

    @field_validator('current_path')
    @classmethod
    def validate_current_path(cls, v):
        """Validate current path"""
        if not v or not isinstance(v, str):
            raise ValueError("Current path must be a non-empty string")
        
        # Basic path validation
        if not v.startswith('/'):
            raise ValueError("Current path must start with /")
        
        # Check for path traversal attempts
        if '..' in v or '//' in v:
            raise ValueError("Current path contains invalid characters")
        
        return v

    @field_validator('navigation_history')
    @classmethod
    def validate_navigation_history(cls, v):
        """Validate navigation history"""
        if not isinstance(v, list):
            raise ValueError("Navigation history must be a list")
        
        # Validate each history entry
        for i, entry in enumerate(v):
            if not isinstance(entry, dict):
                raise ValueError(f"Navigation history entry {i} must be a dictionary")
            
            required_fields = ['path', 'timestamp']
            for field in required_fields:
                if field not in entry:
                    raise ValueError(f"Navigation history entry {i} missing required field: {field}")
            
            # Validate path in history entry
            if not isinstance(entry['path'], str) or not entry['path'].startswith('/'):
                raise ValueError(f"Invalid path in navigation history entry {i}")
        
        return v

    @field_validator('breadcrumbs')
    @classmethod
    def validate_breadcrumbs(cls, v):
        """Validate breadcrumbs"""
        if not isinstance(v, list):
            raise ValueError("Breadcrumbs must be a list")
        
        # Validate each breadcrumb
        for i, breadcrumb in enumerate(v):
            if not isinstance(breadcrumb, dict):
                raise ValueError(f"Breadcrumb {i} must be a dictionary")
            
            required_fields = ['label', 'path']
            for field in required_fields:
                if field not in breadcrumb:
                    raise ValueError(f"Breadcrumb {i} missing required field: {field}")
            
            # Validate breadcrumb path
            if not isinstance(breadcrumb['path'], str) or not breadcrumb['path'].startswith('/'):
                raise ValueError(f"Invalid path in breadcrumb {i}")
        
        return v

    @field_validator('user_permissions')
    @classmethod
    def validate_user_permissions(cls, v):
        """Validate user permissions"""
        if not isinstance(v, list):
            raise ValueError("User permissions must be a list")
        
        valid_permissions = ['read', 'write', 'admin', 'system_admin']
        for permission in v:
            if not isinstance(permission, str) or permission not in valid_permissions:
                raise ValueError(f"Invalid permission: {permission}")
        
        return v


# Allowed dashboard routes configuration
ALLOWED_DASHBOARD_ROUTES = {
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
}

# Route patterns for dynamic routes
ROUTE_PATTERNS = [
    r'^/dashboard/upload$',
    r'^/dashboard/results$',
    r'^/dashboard/history$',
    r'^/dashboard/reports$',
    r'^/dashboard/analytics$',
    r'^/dashboard/settings$',
    r'^/dashboard/profile$',
    r'^/dashboard/notifications$',
    r'^/dashboard/system$',
    r'^/dashboard/help$',
    r'^/dashboard/docs$',
    r'^/dashboard/api$',
    r'^/dashboard/results/\d+$',  # Results with ID
    r'^/dashboard/history/\d+$',  # History with ID
    r'^/dashboard/reports/\w+$',   # Reports with type
    r'^/dashboard/settings/\w+$',  # Settings with section
    r'^/dashboard/profile/\w+$',  # Profile with section
]


def validate_navigation_route(route: str) -> ValidationResult:
    """
    Validate navigation route against allowed dashboard paths
    
    Args:
        route: Route path to validate
        
    Returns:
        ValidationResult with validation status and any errors
    """
    errors = []
    warnings = []
    
    # Basic validation
    if not route or not isinstance(route, str):
        errors.append(NavigationValidationError(
            field="route",
            message="Route must be a non-empty string",
            severity=ValidationSeverity.ERROR,
            code="INVALID_ROUTE_TYPE",
            details=None
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    # Check if route starts with /dashboard/
    if not route.startswith('/dashboard/'):
        errors.append(NavigationValidationError(
            field="route",
            message="Route must start with /dashboard/",
            severity=ValidationSeverity.ERROR,
            code="INVALID_ROUTE_PREFIX",
            details=None
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    # Check for path traversal attempts
    if '..' in route or '//' in route:
        errors.append(NavigationValidationError(
            field="route",
            message="Route contains invalid characters (path traversal attempt)",
            severity=ValidationSeverity.ERROR,
            code="PATH_TRAVERSAL_ATTEMPT",
            details=None
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    # Check for query parameters or fragments (not allowed in navigation routes)
    if '?' in route or '#' in route:
        errors.append(NavigationValidationError(
            field="route",
            message="Route cannot contain query parameters or fragments",
            severity=ValidationSeverity.ERROR,
            code="INVALID_ROUTE_FORMAT",
            details=None
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    # Check against allowed routes
    if route in ALLOWED_DASHBOARD_ROUTES:
        return ValidationResult(is_valid=True, errors=[], warnings=[], validated_data=None, metadata=None)
    
    # Check against route patterns for dynamic routes
    route_matches_pattern = False
    for pattern in ROUTE_PATTERNS:
        if re.match(pattern, route):
            route_matches_pattern = True
            break
    
    if not route_matches_pattern:
        errors.append(NavigationValidationError(
            field="route",
            message=f"Route '{route}' is not in the allowed dashboard routes",
            severity=ValidationSeverity.ERROR,
            code="ROUTE_NOT_ALLOWED",
            details={"allowed_routes": list(ALLOWED_DASHBOARD_ROUTES)}
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    # Additional security checks
    if len(route) > 200:
        warnings.append(NavigationValidationError(
            field="route",
            message="Route is unusually long",
            severity=ValidationSeverity.WARNING,
            code="ROUTE_TOO_LONG",
            details=None
        ))
    
    return ValidationResult(is_valid=True, errors=[], warnings=warnings, validated_data=None, metadata=None)


def validate_navigation_preferences(preferences: Union[Dict[str, Any], NavigationPreferences]) -> ValidationResult:
    """
    Validate NavigationPreferences object
    
    Args:
        preferences: NavigationPreferences object or dictionary
        
    Returns:
        ValidationResult with validation status and any errors
    """
    errors = []
    warnings = []
    
    try:
        # Convert to NavigationPreferences model if it's a dict
        if isinstance(preferences, dict):
            preferences_model = NavigationPreferences(**preferences)
        else:
            preferences_model = preferences
        
        # Validate default landing page
        route_validation = validate_navigation_route(preferences_model.default_landing_page)
        if not route_validation.is_valid:
            for error in route_validation.errors:
                errors.append(NavigationValidationError(
                    field="default_landing_page",
                    message=f"Invalid default landing page: {error.message}",
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_DEFAULT_LANDING_PAGE",
                    details={"route_error": error.model_dump()}
                ))
        
        # Validate custom navigation order
        for i, route in enumerate(preferences_model.custom_navigation_order):
            route_validation = validate_navigation_route(route)
            if not route_validation.is_valid:
                for error in route_validation.errors:
                    errors.append(NavigationValidationError(
                        field=f"custom_navigation_order[{i}]",
                        message=f"Invalid route in custom navigation order: {error.message}",
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CUSTOM_NAVIGATION_ROUTE",
                        details={"route_error": error.model_dump()}
                    ))
        
        # Validate favorite routes
        for i, route in enumerate(preferences_model.favorite_routes):
            route_validation = validate_navigation_route(route)
            if not route_validation.is_valid:
                for error in route_validation.errors:
                    errors.append(NavigationValidationError(
                        field=f"favorite_routes[{i}]",
                        message=f"Invalid favorite route: {error.message}",
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_FAVORITE_ROUTE",
                        details={"route_error": error.model_dump()}
                    ))
        
        # Validate recent routes
        for i, route in enumerate(preferences_model.recent_routes):
            route_validation = validate_navigation_route(route)
            if not route_validation.is_valid:
                for error in route_validation.errors:
                    errors.append(NavigationValidationError(
                        field=f"recent_routes[{i}]",
                        message=f"Invalid recent route: {error.message}",
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_RECENT_ROUTE",
                        details={"route_error": error.model_dump()}
                    ))
        
        # Check for route limits
        if len(preferences_model.favorite_routes) > preferences_model.max_favorite_routes:
            errors.append(NavigationValidationError(
                field="favorite_routes",
                message=f"Number of favorite routes ({len(preferences_model.favorite_routes)}) exceeds maximum ({preferences_model.max_favorite_routes})",
                severity=ValidationSeverity.ERROR,
                code="FAVORITE_ROUTES_LIMIT_EXCEEDED",
                details=None
            ))
        
        if len(preferences_model.recent_routes) > preferences_model.max_recent_routes:
            errors.append(NavigationValidationError(
                field="recent_routes",
                message=f"Number of recent routes ({len(preferences_model.recent_routes)}) exceeds maximum ({preferences_model.max_recent_routes})",
                severity=ValidationSeverity.ERROR,
                code="RECENT_ROUTES_LIMIT_EXCEEDED",
                details=None
            ))
        
        # Check for duplicate routes in custom navigation order
        if len(preferences_model.custom_navigation_order) != len(set(preferences_model.custom_navigation_order)):
            errors.append(NavigationValidationError(
                field="custom_navigation_order",
                message="Custom navigation order contains duplicate routes",
                severity=ValidationSeverity.ERROR,
                code="DUPLICATE_ROUTES_IN_ORDER",
                details=None
            ))
        
        # Check for duplicate favorite routes
        if len(preferences_model.favorite_routes) != len(set(preferences_model.favorite_routes)):
            errors.append(NavigationValidationError(
                field="favorite_routes",
                message="Favorite routes contain duplicates",
                severity=ValidationSeverity.ERROR,
                code="DUPLICATE_FAVORITE_ROUTES",
                details=None
            ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=preferences_model.model_dump() if is_valid else None,
            metadata={
                "total_routes_validated": len(preferences_model.custom_navigation_order) + 
                                        len(preferences_model.favorite_routes) + 
                                        len(preferences_model.recent_routes) + 1,  # +1 for default_landing_page
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except PydanticValidationError as e:
        errors.append(NavigationValidationError(
            field="preferences",
            message=f"Pydantic validation error: {str(e)}",
            severity=ValidationSeverity.ERROR,
            code="PYDANTIC_VALIDATION_ERROR",
            details={"pydantic_error": str(e)}
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    except Exception as e:
        errors.append(NavigationValidationError(
            field="preferences",
            message=f"Unexpected validation error: {str(e)}",
            severity=ValidationSeverity.ERROR,
            code="UNEXPECTED_VALIDATION_ERROR",
            details={"error": str(e)}
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)


def validate_navigation_context(context: Union[Dict[str, Any], NavigationContext]) -> ValidationResult:
    """
    Validate navigation context data
    
    Args:
        context: NavigationContext object or dictionary
        
    Returns:
        ValidationResult with validation status and any errors
    """
    errors = []
    warnings = []
    
    try:
        # Convert to NavigationContext model if it's a dict
        if isinstance(context, dict):
            context_model = NavigationContext(**context)
        else:
            context_model = context
        
        # Validate current path
        route_validation = validate_navigation_route(context_model.current_path)
        if not route_validation.is_valid:
            for error in route_validation.errors:
                errors.append(NavigationValidationError(
                    field="current_path",
                    message=f"Invalid current path: {error.message}",
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_CURRENT_PATH",
                    details={"route_error": error.model_dump()}
                ))
        
        # Validate active route if present
        if context_model.active_route:
            route_validation = validate_navigation_route(context_model.active_route)
            if not route_validation.is_valid:
                for error in route_validation.errors:
                    errors.append(NavigationValidationError(
                        field="active_route",
                        message=f"Invalid active route: {error.message}",
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_ACTIVE_ROUTE",
                        details={"route_error": error.model_dump()}
                    ))
        
        # Validate previous route if present
        if context_model.previous_route:
            route_validation = validate_navigation_route(context_model.previous_route)
            if not route_validation.is_valid:
                for error in route_validation.errors:
                    errors.append(NavigationValidationError(
                        field="previous_route",
                        message=f"Invalid previous route: {error.message}",
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_PREVIOUS_ROUTE",
                        details={"route_error": error.model_dump()}
                    ))
        
        # Validate navigation history
        for i, entry in enumerate(context_model.navigation_history):
            if 'path' in entry:
                route_validation = validate_navigation_route(entry['path'])
                if not route_validation.is_valid:
                    for error in route_validation.errors:
                        errors.append(NavigationValidationError(
                            field=f"navigation_history[{i}].path",
                            message=f"Invalid path in navigation history: {error.message}",
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_HISTORY_PATH",
                            details={"route_error": error.model_dump()}
                        ))
        
        # Validate breadcrumbs
        for i, breadcrumb in enumerate(context_model.breadcrumbs):
            if 'path' in breadcrumb:
                route_validation = validate_navigation_route(breadcrumb['path'])
                if not route_validation.is_valid:
                    for error in route_validation.errors:
                        errors.append(NavigationValidationError(
                            field=f"breadcrumbs[{i}].path",
                            message=f"Invalid path in breadcrumb: {error.message}",
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_BREADCRUMB_PATH",
                            details={"route_error": error.model_dump()}
                        ))
        
        # Check for consistency between current path and breadcrumbs
        if context_model.breadcrumbs:
            last_breadcrumb_path = context_model.breadcrumbs[-1].get('path')
            if last_breadcrumb_path != context_model.current_path:
                warnings.append(NavigationValidationError(
                    field="breadcrumbs",
                    message="Last breadcrumb path does not match current path",
                    severity=ValidationSeverity.WARNING,
                    code="BREADCRUMB_PATH_MISMATCH",
                    details={
                        "current_path": context_model.current_path,
                        "last_breadcrumb_path": last_breadcrumb_path
                    }
                ))
        
        # Check for reasonable navigation history size
        if len(context_model.navigation_history) > 50:
            warnings.append(NavigationValidationError(
                field="navigation_history",
                message="Navigation history is unusually large",
                severity=ValidationSeverity.WARNING,
                code="LARGE_NAVIGATION_HISTORY",
                details=None
            ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_data=context_model.model_dump() if is_valid else None,
            metadata={
                "history_entries_validated": len(context_model.navigation_history),
                "breadcrumbs_validated": len(context_model.breadcrumbs),
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except PydanticValidationError as e:
        errors.append(NavigationValidationError(
            field="context",
            message=f"Pydantic validation error: {str(e)}",
            severity=ValidationSeverity.ERROR,
            code="PYDANTIC_VALIDATION_ERROR",
            details={"pydantic_error": str(e)}
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)
    
    except Exception as e:
        errors.append(NavigationValidationError(
            field="context",
            message=f"Unexpected validation error: {str(e)}",
            severity=ValidationSeverity.ERROR,
            code="UNEXPECTED_VALIDATION_ERROR",
            details={"error": str(e)}
        ))
        return ValidationResult(is_valid=False, errors=errors, warnings=[], validated_data=None, metadata=None)


def validate_route_security(route: str) -> ValidationResult:
    """
    Additional security validation for routes
    
    Args:
        route: Route path to validate for security issues
        
    Returns:
        ValidationResult with security validation status
    """
    errors = []
    warnings = []
    
    # Check for SQL injection patterns
    sql_patterns = [
        r"'.*'.*or.*'.*'",
        r"union.*select",
        r"drop.*table",
        r"delete.*from",
        r"insert.*into",
        r"update.*set"
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, route, re.IGNORECASE):
            errors.append(NavigationValidationError(
                field="route",
                message="Route contains potential SQL injection pattern",
                severity=ValidationSeverity.ERROR,
                code="SQL_INJECTION_PATTERN",
                details=None
            ))
            break
    
    # Check for XSS patterns
    xss_patterns = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed"
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, route, re.IGNORECASE):
            errors.append(NavigationValidationError(
                field="route",
                message="Route contains potential XSS pattern",
                severity=ValidationSeverity.ERROR,
                code="XSS_PATTERN",
                details=None
            ))
            break
    
    # Check for command injection patterns
    cmd_patterns = [
        r";\s*\w+",
        r"\|\s*\w+",
        r"&&\s*\w+",
        r"\$\(",
        r"`.*`"
    ]
    
    for pattern in cmd_patterns:
        if re.search(pattern, route):
            errors.append(NavigationValidationError(
                field="route",
                message="Route contains potential command injection pattern",
                severity=ValidationSeverity.ERROR,
                code="COMMAND_INJECTION_PATTERN",
                details=None
            ))
            break
    
    # Check for suspicious characters
    suspicious_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')']
    found_chars = [char for char in suspicious_chars if char in route]
    
    if found_chars:
        warnings.append(NavigationValidationError(
            field="route",
            message=f"Route contains suspicious characters: {', '.join(found_chars)}",
            severity=ValidationSeverity.WARNING,
            code="SUSPICIOUS_CHARACTERS",
            details={"suspicious_chars": found_chars}
        ))
    
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        validated_data=None,
        metadata={
            "security_checks_performed": len(sql_patterns) + len(xss_patterns) + len(cmd_patterns),
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def get_allowed_routes() -> List[str]:
    """
    Get list of all allowed dashboard routes
    
    Returns:
        List of allowed route patterns
    """
    return list(ALLOWED_DASHBOARD_ROUTES)


def is_route_allowed(route: str) -> bool:
    """
    Quick check if a route is allowed
    
    Args:
        route: Route to check
        
    Returns:
        True if route is allowed, False otherwise
    """
    validation_result = validate_navigation_route(route)
    return validation_result.is_valid
