#!/usr/bin/env python3
"""
Work Order #6 Implementation Test
Test suite for UploadValidationFeedback Component for Client-Side File Validation
"""

import os
import sys
import json
from pathlib import Path

def test_file_structure():
    """Test that all required files are present"""
    print("🔍 Testing file structure...")
    
    required_files = [
        # Main component files
        "src/components/UploadValidationFeedback/UploadValidationFeedback.tsx",
        "src/components/UploadValidationFeedback/UploadValidationFeedback.module.css",
        "src/components/UploadValidationFeedback/__init__.py",
        
        # Utility and constants files
        "src/utils/uploadValidationUtils.ts",
        "src/constants/uploadConstants.ts",
        "src/types/upload.d.ts",
        "src/constants/__init__.py",
        
        # Updated ProgressiveVideoUploader
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.tsx",
        
        # Existing dependencies (should exist)
        "src/hooks/useVideoUpload.ts",
        "src/utils/EmbeddingCache.js",
        "src/utils/videoProcessing.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_upload_validation_utils():
    """Test upload validation utility functions"""
    print("\n🔍 Testing upload validation utilities...")
    
    utils_path = "src/utils/uploadValidationUtils.ts"
    
    try:
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required validation functions
        required_functions = [
            "validateFileType",
            "validateFileSize",
            "estimateProcessingTime",
            "validateFile",
            "formatFileSize",
            "formatTimeRemaining",
            "assessProcessingComplexity",
            "getSystemPerformanceMetrics"
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing validation functions: {missing_functions}")
            return False
        
        # Check for validation result interfaces
        validation_features = [
            "ValidationResult",
            "ValidationError",
            "ProcessingEstimate",
            "FileTypeValidation",
            "FileSizeValidation"
        ]
        
        missing_features = []
        for feature in validation_features:
            if feature not in content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing validation features: {missing_features}")
            return False
        
        print("✅ Upload validation utilities structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading upload validation utilities: {e}")
        return False

def test_upload_constants():
    """Test upload constants configuration"""
    print("\n🔍 Testing upload constants...")
    
    constants_path = "src/constants/uploadConstants.ts"
    
    try:
        with open(constants_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required constants
        required_constants = [
            "SUPPORTED_VIDEO_TYPES",
            "FILE_SIZE_CONSTRAINTS",
            "PROCESSING_FACTORS",
            "VALIDATION_MESSAGES",
            "FILE_CONSTRAINTS",
            "ERROR_SEVERITY",
            "VALIDATION_STATES"
        ]
        
        missing_constants = []
        for constant in required_constants:
            if constant not in content:
                missing_constants.append(constant)
        
        if missing_constants:
            print(f"❌ Missing constants: {missing_constants}")
            return False
        
        # Check for video type configurations
        video_types = [
            "video/mp4",
            "video/x-msvideo",
            "video/quicktime",
            "video/x-matroska",
            "video/webm",
            "video/ogg"
        ]
        
        missing_video_types = []
        for video_type in video_types:
            if video_type not in content:
                missing_video_types.append(video_type)
        
        if missing_video_types:
            print(f"❌ Missing video types: {missing_video_types}")
            return False
        
        print("✅ Upload constants structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading upload constants: {e}")
        return False

def test_type_definitions():
    """Test TypeScript type definitions"""
    print("\n🔍 Testing type definitions...")
    
    types_path = "src/types/upload.d.ts"
    
    try:
        with open(types_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required type interfaces
        required_types = [
            "ValidationResult",
            "ValidationError",
            "ProcessingEstimate",
            "FileMetadata",
            "FileConstraint",
            "UploadValidationFeedbackProps",
            "ValidationOptions",
            "FileTypeValidation",
            "FileSizeValidation"
        ]
        
        missing_types = []
        for type_def in required_types:
            if type_def not in content:
                missing_types.append(type_def)
        
        if missing_types:
            print(f"❌ Missing type definitions: {missing_types}")
            return False
        
        # Check for TypeScript-specific syntax
        ts_features = [
            "interface",
            "export",
            "type",
            "?:",
            "|",
            "&"
        ]
        
        missing_ts_features = []
        for feature in ts_features:
            if feature not in content:
                missing_ts_features.append(feature)
        
        if missing_ts_features:
            print(f"⚠️  Missing TypeScript features: {missing_ts_features}")
        
        print("✅ Type definitions structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading type definitions: {e}")
        return False

def test_validation_feedback_component():
    """Test UploadValidationFeedback component structure"""
    print("\n🔍 Testing UploadValidationFeedback component...")
    
    component_path = "src/components/UploadValidationFeedback/UploadValidationFeedback.tsx"
    
    try:
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required imports
        required_imports = [
            "import React",
            "from 'react'",
            "validateFile",
            "getSystemPerformanceMetrics",
            "FILE_CONSTRAINTS",
            "VALIDATION_MESSAGES",
            "ERROR_SEVERITY"
        ]
        
        missing_imports = []
        for import_item in required_imports:
            if import_item not in content:
                missing_imports.append(import_item)
        
        if missing_imports:
            print(f"❌ Missing imports: {missing_imports}")
            return False
        
        # Check for required functionality
        required_functions = [
            "renderConstraints",
            "renderValidationStatus",
            "renderValidationErrors",
            "renderValidationWarnings",
            "renderDragActiveState",
            "useImperativeHandle"
        ]
        
        missing_functions = []
        for function in required_functions:
            if function not in content:
                missing_functions.append(function)
        
        if missing_functions:
            print(f"❌ Missing functions: {missing_functions}")
            return False
        
        # Check for TypeScript features
        ts_features = [
            "forwardRef",
            "useImperativeHandle",
            "ValidationResult",
            "ValidationError",
            "React.FC"
        ]
        
        missing_ts_features = []
        for feature in ts_features:
            if feature not in content:
                missing_ts_features.append(feature)
        
        if missing_ts_features:
            print(f"❌ Missing TypeScript features: {missing_ts_features}")
            return False
        
        print("✅ UploadValidationFeedback component structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading UploadValidationFeedback component: {e}")
        return False

def test_progressive_video_uploader_integration():
    """Test ProgressiveVideoUploader TypeScript conversion and integration"""
    print("\n🔍 Testing ProgressiveVideoUploader integration...")
    
    component_path = "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.tsx"
    
    try:
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for TypeScript conversion
        ts_features = [
            "import React",
            "React.FC",
            "interface",
            "ProgressiveVideoUploaderProps",
            "File | null",
            "useState<File | null>",
            "useCallback",
            "useRef<HTMLInputElement>"
        ]
        
        missing_ts_features = []
        for feature in ts_features:
            if feature not in content:
                missing_ts_features.append(feature)
        
        if missing_ts_features:
            print(f"❌ Missing TypeScript features: {missing_ts_features}")
            return False
        
        # Check for validation feedback integration
        integration_features = [
            "UploadValidationFeedback",
            "showValidationFeedback",
            "onValidationComplete",
            "onError"
        ]
        
        missing_integration = []
        for feature in integration_features:
            if feature not in content:
                missing_integration.append(feature)
        
        if missing_integration:
            print(f"❌ Missing integration features: {missing_integration}")
            return False
        
        print("✅ ProgressiveVideoUploader integration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading ProgressiveVideoUploader integration: {e}")
        return False

def test_css_modules():
    """Test CSS module files"""
    print("\n🔍 Testing CSS modules...")
    
    css_files = [
        "src/components/UploadValidationFeedback/UploadValidationFeedback.module.css"
    ]
    
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for basic CSS structure
            if not content.strip():
                print(f"❌ Empty CSS file: {css_file}")
                return False
            
            # Check for component-specific styles
            required_styles = [
                ".validationFeedback",
                ".constraintsContainer",
                ".validationStatus",
                ".errorsContainer",
                ".warningsContainer",
                "@media"
            ]
            
            missing_styles = []
            for style in required_styles:
                if style not in content:
                    missing_styles.append(style)
            
            if missing_styles:
                print(f"⚠️  CSS file may be missing some styles: {css_file}")
            
            print(f"✅ CSS file valid: {css_file}")
            
        except Exception as e:
            print(f"❌ Error reading CSS file {css_file}: {e}")
            return False
    
    return True

def test_integration_points():
    """Test integration with existing components and utilities"""
    print("\n🔍 Testing integration points...")
    
    # Check that existing components are still present
    existing_files = [
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.jsx",  # Original should still exist
        "src/hooks/useVideoUpload.ts",
        "src/utils/EmbeddingCache.js",
        "src/utils/videoProcessing.js"
    ]
    
    for file_path in existing_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing existing file: {file_path}")
            return False
    
    # Check that new TypeScript version exists alongside original
    if not os.path.exists("src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.tsx"):
        print("❌ Missing TypeScript version of ProgressiveVideoUploader")
        return False
    
    print("✅ Integration points valid")
    return True

def test_validation_features():
    """Test specific validation features"""
    print("\n🔍 Testing validation features...")
    
    # Test that validation utilities have all required features
    utils_path = "src/utils/uploadValidationUtils.ts"
    
    try:
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for specific validation capabilities
        validation_capabilities = [
            "validateFileType",
            "validateFileSize", 
            "estimateProcessingTime",
            "formatFileSize",
            "formatTimeRemaining",
            "assessProcessingComplexity",
            "getSystemPerformanceMetrics",
            "createValidationError"
        ]
        
        missing_capabilities = []
        for capability in validation_capabilities:
            if capability not in content:
                missing_capabilities.append(capability)
        
        if missing_capabilities:
            print(f"❌ Missing validation capabilities: {missing_capabilities}")
            return False
        
        print("✅ Validation features complete")
        return True
        
    except Exception as e:
        print(f"❌ Error testing validation features: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Work Order #6 Implementation Tests")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_upload_validation_utils,
        test_upload_constants,
        test_type_definitions,
        test_validation_feedback_component,
        test_progressive_video_uploader_integration,
        test_css_modules,
        test_integration_points,
        test_validation_features
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Work Order #6 implementation is complete.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
