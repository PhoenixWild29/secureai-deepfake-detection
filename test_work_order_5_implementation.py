#!/usr/bin/env python3
"""
Test Implementation for Work Order #5: S3 Presigned URL Generation Endpoint
Comprehensive test suite for the new upload functionality
"""

import os
import sys
import json
import asyncio
import requests
from typing import Dict, Any
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration_loading():
    """Test AWS configuration loading."""
    print("Testing AWS configuration loading...")
    
    try:
        from src.config.aws_config import get_aws_config, validate_aws_config, check_required_env_vars
        
        # Check required environment variables
        missing_vars = check_required_env_vars()
        if missing_vars:
            print(f"⚠️  Missing required environment variables: {missing_vars}")
            print("   Please set these environment variables before testing:")
            for var in missing_vars:
                print(f"   export {var}=your_value_here")
        else:
            print("✅ All required environment variables are set")
        
        # Test configuration loading
        try:
            config = get_aws_config()
            print(f"✅ AWS configuration loaded successfully")
            print(f"   S3 Bucket: {config.s3.bucket_name}")
            print(f"   Cognito User Pool: {config.cognito.user_pool_id}")
            print(f"   CORS Origins: {config.cors.allowed_origins}")
        except Exception as e:
            print(f"❌ Failed to load AWS configuration: {e}")
        
        # Test configuration validation
        validation_results = validate_aws_config()
        if validation_results['errors']:
            print(f"❌ Configuration validation errors: {validation_results['errors']}")
        if validation_results['warnings']:
            print(f"⚠️  Configuration validation warnings: {validation_results['warnings']}")
        if not validation_results['errors']:
            print("✅ Configuration validation passed")
            
    except ImportError as e:
        print(f"❌ Failed to import configuration modules: {e}")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")


def test_file_validation():
    """Test file validation utilities."""
    print("\nTesting file validation utilities...")
    
    try:
        from src.utils.file_validation import validate_video_file, FileValidator
        
        # Test valid video file
        result = validate_video_file(
            filename="test_video.mp4",
            content_type="video/mp4",
            file_size=1024 * 1024  # 1MB
        )
        
        if result['is_valid']:
            print("✅ Valid video file validation passed")
        else:
            print(f"❌ Valid video file validation failed: {result['errors']}")
        
        # Test invalid file type
        result = validate_video_file(
            filename="test_document.pdf",
            content_type="application/pdf",
            file_size=1024 * 1024
        )
        
        if not result['is_valid']:
            print("✅ Invalid file type rejection works")
        else:
            print("❌ Invalid file type should have been rejected")
        
        # Test file size limit
        result = validate_video_file(
            filename="large_video.mp4",
            content_type="video/mp4",
            file_size=600 * 1024 * 1024  # 600MB (exceeds default 500MB limit)
        )
        
        if not result['is_valid']:
            print("✅ File size limit enforcement works")
        else:
            print("❌ File size limit should have been enforced")
        
        # Test FileValidator class
        validator = FileValidator(max_file_size=10 * 1024 * 1024)  # 10MB limit
        result = validator.validate_file(
            filename="test.mp4",
            content_type="video/mp4",
            file_size=5 * 1024 * 1024  # 5MB
        )
        
        if result['is_valid']:
            print("✅ Custom FileValidator works correctly")
        else:
            print(f"❌ Custom FileValidator failed: {result['errors']}")
            
    except ImportError as e:
        print(f"❌ Failed to import file validation modules: {e}")
    except Exception as e:
        print(f"❌ File validation test failed: {e}")


def test_error_handling():
    """Test error handling classes."""
    print("\nTesting error handling classes...")
    
    try:
        from src.errors.api_errors import (
            ValidationError, AuthenticationError, FileValidationError,
            InvalidFileTypeError, FileSizeExceededError, S3ServiceError
        )
        
        # Test ValidationError
        try:
            raise ValidationError("Test validation error", field="test_field")
        except ValidationError as e:
            if e.error_code == "VALIDATION_ERROR" and e.status_code == 400:
                print("✅ ValidationError works correctly")
            else:
                print(f"❌ ValidationError incorrect: code={e.error_code}, status={e.status_code}")
        
        # Test FileValidationError
        try:
            raise FileValidationError("Test file error", filename="test.mp4")
        except FileValidationError as e:
            if e.error_code == "VALIDATION_ERROR" and "test.mp4" in e.details.get('filename', ''):
                print("✅ FileValidationError works correctly")
            else:
                print(f"❌ FileValidationError incorrect: {e.details}")
        
        # Test InvalidFileTypeError
        try:
            raise InvalidFileTypeError("application/pdf", ["video/mp4"], "test.pdf")
        except InvalidFileTypeError as e:
            if "Invalid file type" in e.message and "application/pdf" in e.message:
                print("✅ InvalidFileTypeError works correctly")
            else:
                print(f"❌ InvalidFileTypeError incorrect: {e.message}")
        
        # Test FileSizeExceededError
        try:
            raise FileSizeExceededError(1000000, 500000, "large.mp4")
        except FileSizeExceededError as e:
            if "File size" in e.message and "exceeds" in e.message:
                print("✅ FileSizeExceededError works correctly")
            else:
                print(f"❌ FileSizeExceededError incorrect: {e.message}")
                
    except ImportError as e:
        print(f"❌ Failed to import error handling modules: {e}")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


def test_s3_service():
    """Test S3 presigned service (without actual AWS calls)."""
    print("\nTesting S3 presigned service...")
    
    try:
        from src.services.s3_presigned_service import S3PresignedService
        
        # Test service initialization (this will fail without AWS credentials, which is expected)
        try:
            service = S3PresignedService(
                bucket_name="test-bucket",
                region="us-east-1"
            )
            print("❌ S3 service should have failed without credentials")
        except Exception as e:
            if "credentials" in str(e).lower() or "configuration" in str(e).lower():
                print("✅ S3 service correctly requires credentials")
            else:
                print(f"❌ S3 service failed with unexpected error: {e}")
        
        # Test S3 key generation (this should work without credentials)
        try:
            service = S3PresignedService.__new__(S3PresignedService)
            s3_key = service.generate_s3_key("test_video.mp4", "user123", "uploads")
            
            if s3_key and "uploads" in s3_key and "test_video.mp4" in s3_key:
                print("✅ S3 key generation works correctly")
                print(f"   Generated key: {s3_key}")
            else:
                print(f"❌ S3 key generation failed: {s3_key}")
        except Exception as e:
            print(f"❌ S3 key generation test failed: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import S3 service modules: {e}")
    except Exception as e:
        print(f"❌ S3 service test failed: {e}")


def test_api_endpoints():
    """Test API endpoint integration."""
    print("\nTesting API endpoint integration...")
    
    try:
        from src.api.v1.upload import router
        
        # Check if router has the expected routes
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/v1/upload/presigned-url",
            "/v1/upload/presigned-post", 
            "/v1/upload/verify/{s3_key:path}",
            "/v1/upload/config"
        ]
        
        missing_routes = []
        for expected_route in expected_routes:
            if expected_route not in routes:
                missing_routes.append(expected_route)
        
        if not missing_routes:
            print("✅ All expected API routes are registered")
            print(f"   Available routes: {routes}")
        else:
            print(f"❌ Missing API routes: {missing_routes}")
            
    except ImportError as e:
        print(f"❌ Failed to import API modules: {e}")
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")


def test_fastapi_integration():
    """Test FastAPI application integration."""
    print("\nTesting FastAPI application integration...")
    
    try:
        from api_fastapi import app
        
        # Check if the upload router is included
        routes = [route.path for route in app.routes]
        upload_routes = [route for route in routes if "/v1/upload" in route]
        
        if upload_routes:
            print("✅ Upload router is integrated with FastAPI")
            print(f"   Upload routes: {upload_routes}")
        else:
            print("❌ Upload router not found in FastAPI app")
        
        # Check if exception handlers are registered
        exception_handlers = list(app.exception_handlers.keys())
        if len(exception_handlers) > 0:
            print(f"✅ Exception handlers are registered: {exception_handlers}")
        else:
            print("❌ No exception handlers found")
            
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
    except Exception as e:
        print(f"❌ FastAPI integration test failed: {e}")


def test_schema_validation():
    """Test Pydantic schema validation."""
    print("\nTesting Pydantic schema validation...")
    
    try:
        from api.schemas import (
            PresignedUrlRequest, PresignedUrlResponse, PresignedUrlData,
            PresignedPostRequest, PresignedPostResponse, PresignedPostData,
            UploadConfigData
        )
        
        # Test PresignedUrlRequest validation
        try:
            request = PresignedUrlRequest(
                filename="test.mp4",
                content_type="video/mp4",
                file_size=1024000,
                expires_in=3600
            )
            print("✅ PresignedUrlRequest validation passed")
        except Exception as e:
            print(f"❌ PresignedUrlRequest validation failed: {e}")
        
        # Test invalid request
        try:
            request = PresignedUrlRequest(
                filename="",  # Invalid: empty filename
                content_type="video/mp4",
                file_size=1024000
            )
            print("❌ PresignedUrlRequest should have rejected empty filename")
        except Exception as e:
            print("✅ PresignedUrlRequest correctly rejects invalid data")
        
        # Test response models
        try:
            data = PresignedUrlData(
                presigned_url="https://example.com/presigned",
                upload_url="https://example.com/upload",
                s3_key="uploads/test.mp4",
                bucket="test-bucket",
                region="us-east-1",
                expires_at="2025-01-01T12:00:00Z",
                expires_in=3600,
                required_headers={"Content-Type": "video/mp4"},
                metadata={}
            )
            
            response = PresignedUrlResponse(
                success=True,
                data=data
            )
            print("✅ Response model validation passed")
        except Exception as e:
            print(f"❌ Response model validation failed: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import schema modules: {e}")
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")


def run_integration_test():
    """Run a basic integration test."""
    print("\nRunning integration test...")
    
    # Check if we can start the FastAPI app
    try:
        from api_fastapi import app
        print("✅ FastAPI app can be imported successfully")
        
        # Check if we can access the OpenAPI schema
        openapi_schema = app.openapi()
        if openapi_schema and "paths" in openapi_schema:
            paths = openapi_schema["paths"]
            upload_paths = [path for path in paths.keys() if "/v1/upload" in path]
            if upload_paths:
                print(f"✅ Upload endpoints found in OpenAPI schema: {upload_paths}")
            else:
                print("❌ Upload endpoints not found in OpenAPI schema")
        else:
            print("❌ Failed to generate OpenAPI schema")
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")


def print_environment_setup_instructions():
    """Print instructions for setting up the environment."""
    print("\n" + "="*60)
    print("ENVIRONMENT SETUP INSTRUCTIONS")
    print("="*60)
    print("To test the S3 presigned URL functionality, set these environment variables:")
    print()
    print("Required:")
    print("  export S3_BUCKET_NAME=your-s3-bucket-name")
    print("  export COGNITO_USER_POOL_ID=your-cognito-user-pool-id")
    print("  export COGNITO_CLIENT_ID=your-cognito-client-id")
    print()
    print("Optional:")
    print("  export AWS_DEFAULT_REGION=us-east-1")
    print("  export AWS_ACCESS_KEY_ID=your-access-key")
    print("  export AWS_SECRET_ACCESS_KEY=your-secret-key")
    print("  export CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com")
    print()
    print("To test with a real JWT token:")
    print("  export TEST_JWT_TOKEN=your-cognito-jwt-token")
    print()
    print("To run the FastAPI server:")
    print("  uvicorn api_fastapi:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("API Documentation will be available at:")
    print("  http://localhost:8000/docs")
    print("="*60)


def main():
    """Run all tests."""
    print("🧪 Testing Work Order #5 Implementation: S3 Presigned URL Generation Endpoint")
    print("="*80)
    
    # Run all tests
    test_configuration_loading()
    test_file_validation()
    test_error_handling()
    test_s3_service()
    test_api_endpoints()
    test_fastapi_integration()
    test_schema_validation()
    run_integration_test()
    
    # Print setup instructions
    print_environment_setup_instructions()
    
    print("\n🎉 Work Order #5 implementation testing completed!")
    print("Check the results above and set up the environment variables to test with real AWS services.")


if __name__ == "__main__":
    main()
