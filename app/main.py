#!/usr/bin/env python3
"""
Detection API Main Application
FastAPI application entry point for video detection API with comprehensive error handling and middleware
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import our detection components
from app.api.v1.endpoints.detect import router as detect_router
from app.core.exceptions import DetectionAPIError
from app.core.config import detection_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="SecureAI DeepFake Detection API",
    description="Enterprise-grade deepfake detection API with real-time processing and blockchain verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=detection_settings.api.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configure trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include API routers
app.include_router(detect_router)

# Include WebSocket router for real-time analysis updates
from app.api.websockets import router as websocket_router
app.include_router(websocket_router)


# Global exception handlers
@app.exception_handler(DetectionAPIError)
async def detection_api_error_handler(request: Request, exc: DetectionAPIError) -> JSONResponse:
    """
    Handle DetectionAPIError exceptions.
    
    Args:
        request: FastAPI request object
        exc: DetectionAPIError instance
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Detection API error: {exc.message}", extra={
        'error_code': exc.error_code,
        'analysis_id': str(exc.analysis_id) if exc.analysis_id else None,
        'status_code': exc.status_code,
        'details': exc.details
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "analysis_id": str(exc.analysis_id) if exc.analysis_id else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": exc.details
            }
        },
        headers={
            "X-Error-Code": exc.error_code,
            "X-Analysis-ID": str(exc.analysis_id) if exc.analysis_id else ""
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException instances.
    
    Args:
        request: FastAPI request object
        exc: HTTPException instance
        
    Returns:
        JSONResponse with error details
    """
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle RequestValidationError instances.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError instance
        
    Returns:
        JSONResponse with validation error details
    """
    logger.warning(f"Validation error: {exc.errors()}")
    
    # Format validation errors
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": formatted_errors,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic Exception instances.
    
    Args:
        request: FastAPI request object
        exc: Generic Exception instance
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )


# Health check endpoint
@app.get(
    "/health",
    summary="Health Check",
    description="Check API health and service status"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        # Get service stats
        from app.services.video_processing import get_video_processing_service
        processing_service = get_video_processing_service()
        stats = processing_service.get_service_stats()
        
        # Check configuration validity
        config_valid = detection_settings.validate_configuration()['overall_valid']
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "service_stats": stats,
            "configuration_valid": config_valid,
            "uptime": "N/A"  # Could be implemented with startup time tracking
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }


# Root endpoint
@app.get(
    "/",
    summary="API Root",
    description="API root endpoint with basic information"
)
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing API information.
    
    Returns:
        Dict[str, Any]: API information
    """
    return {
        "name": "SecureAI DeepFake Detection API",
        "version": "1.0.0",
        "description": "Enterprise-grade deepfake detection API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    Initialize services and validate configuration.
    """
    logger.info("Starting SecureAI DeepFake Detection API")
    
    # Validate configuration
    config_valid = detection_settings.validate_configuration()
    if not config_valid['overall_valid']:
        logger.error("Configuration validation failed", extra=config_valid)
        raise Exception("Invalid configuration")
    
    # Create necessary directories
    upload_folder = detection_settings.detection.upload_folder
    results_folder = detection_settings.detection.results_folder
    temp_folder = detection_settings.detection.temp_folder
    
    for folder in [upload_folder, results_folder, temp_folder]:
        os.makedirs(folder, exist_ok=True)
        logger.info(f"Created directory: {folder}")
    
    # Initialize Redis connection for WebSocket updates
    try:
        from app.core.redis_manager import redis_manager
        redis_connected = await redis_manager.connect()
        if redis_connected:
            logger.info("Redis connection established for WebSocket updates")
        else:
            logger.warning("Failed to establish Redis connection - WebSocket updates may not work")
    except Exception as e:
        logger.error(f"Error initializing Redis connection: {str(e)}")
    
    logger.info("SecureAI DeepFake Detection API started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    Clean up resources and connections.
    """
    logger.info("Shutting down SecureAI DeepFake Detection API")
    
    # Clean up any ongoing analyses
    try:
        from app.services.video_processing import get_video_processing_service
        processing_service = get_video_processing_service()
        
        # Cancel all active analyses
        for analysis_id in list(processing_service.tracker.active_analyses):
            await processing_service.cancel_analysis(analysis_id)
        
        logger.info("Cleaned up active analyses")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
    
    # Clean up Redis connections
    try:
        from app.core.redis_manager import redis_manager
        await redis_manager.disconnect()
        logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {str(e)}")
    
    logger.info("SecureAI DeepFake Detection API shutdown complete")


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests for monitoring and debugging.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/handler
        
    Returns:
        Response from next handler
    """
    start_time = datetime.now(timezone.utc)
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}", extra={
        "method": request.method,
        "path": request.url.path,
        "query_params": str(request.query_params),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    })
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} ({process_time:.3f}s)", extra={
        "status_code": response.status_code,
        "process_time": process_time
    })
    
    return response


# Export app for uvicorn
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("API_DEBUG", "false").lower() == "true"
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
