#!/usr/bin/env python3
"""
Basic Implementation Test for Work Order #5: S3 Presigned URL Generation Endpoint
Simple test to verify the implementation without requiring AWS credentials
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_file_structure():
    """Test that all required files are present."""
    print("Testing file structure...")
    
    required_files = [
        "src/services/s3_presigned_service.py",
        "src/middleware/cognito_auth.py", 
        "src/utils/file_validation.py",
        "src/errors/api_errors.py",
        "src/middleware/error_handler.py",
        "src/config/aws_config.py",
        "src/api/v1/upload.py",
        "api/schemas.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files are present")
        return True


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting imports...")
    
    try:
        # Test error handling imports
        from src.errors.api_errors import ValidationError, AuthenticationError, FileValidationError
        print("✅ Error handling classes imported successfully")
        
        # Test file validation imports
        from src.utils.file_validation import validate_video_file, FileValidator
        print("✅ File validation utilities imported successfully")
        
        # Test configuration imports
        from src.config.aws_config import get_aws_config, validate_aws_config
        print("✅ AWS configuration imported successfully")
        
        # Test S3 service imports
        from src.services.s3_presigned_service import S3PresignedService
        print("✅ S3 presigned service imported successfully")
        
        # Test middleware imports
        from src.middleware.error_handler import ErrorHandler
        print("✅ Error handler middleware imported successfully")
        
        # Test API imports
        from src.api.v1.upload import router
        print("✅ Upload API router imported successfully")
        
        # Test schema imports
        from api.schemas import PresignedUrlRequest, PresignedUrlResponse
        print("✅ API schemas imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without AWS credentials."""
    print("\nTesting basic functionality...")
    
    try:
        # Test file validation
        from src.utils.file_validation import validate_video_file
        
        result = validate_video_file(
            filename="test.mp4",
            content_type="video/mp4", 
            file_size=1024 * 1024
        )
        
        if result['is_valid']:
            print("✅ File validation works correctly")
        else:
            print(f"❌ File validation failed: {result['errors']}")
            return False
        
        # Test error creation
        from src.errors.api_errors import ValidationError
        
        try:
            raise ValidationError("Test error", field="test_field")
        except ValidationError as e:
            if e.error_code == "VALIDATION_ERROR":
                print("✅ Error handling works correctly")
            else:
                print(f"❌ Error handling failed: {e.error_code}")
                return False
        
        # Test S3 key generation
        from src.services.s3_presigned_service import S3PresignedService
        
        service = S3PresignedService.__new__(S3PresignedService)
        s3_key = service.generate_s3_key("test.mp4", "user123", "uploads")
        
        if s3_key and "uploads" in s3_key and "test.mp4" in s3_key:
            print("✅ S3 key generation works correctly")
        else:
            print(f"❌ S3 key generation failed: {s3_key}")
            return False
        
        # Test schema validation
        from api.schemas import PresignedUrlRequest
        
        request = PresignedUrlRequest(
            filename="test.mp4",
            content_type="video/mp4",
            file_size=1024000,
            expires_in=3600
        )
        
        if request.filename == "test.mp4":
            print("✅ Schema validation works correctly")
        else:
            print("❌ Schema validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_api_routes():
    """Test that API routes are properly configured."""
    print("\nTesting API routes...")
    
    try:
        from src.api.v1.upload import router
        
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
            return True
        else:
            print(f"❌ Missing API routes: {missing_routes}")
            return False
            
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        return False


def main():
    """Run all basic tests."""
    print("🧪 Basic Implementation Test for Work Order #5")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_imports,
        test_basic_functionality,
        test_api_routes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed! The implementation is working correctly.")
        print("\nNext steps:")
        print("1. Set up AWS credentials and S3 bucket")
        print("2. Configure Cognito User Pool")
        print("3. Set environment variables")
        print("4. Test with real AWS services")
    else:
        print(f"❌ {total - passed} tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
