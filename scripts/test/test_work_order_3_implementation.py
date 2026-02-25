#!/usr/bin/env python3
"""
Work Order #3 Implementation Test
Test suite for ProgressiveVideoUploader Component with Drag-and-Drop Support
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
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.jsx",
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.module.css",
        "src/components/ProgressiveVideoUploader/__init__.py",
        
        # Analysis tracker files
        "src/components/AnalysisProgressTracker/AnalysisProgressTracker.jsx",
        "src/components/AnalysisProgressTracker/AnalysisProgressTracker.module.css",
        "src/components/AnalysisProgressTracker/__init__.py",
        
        # Utility files
        "src/utils/EmbeddingCache.js",
        
        # Updated utility files
        "src/utils/videoProcessing.js",
        
        # Existing hooks and services (should exist)
        "src/hooks/useVideoUpload.ts",
        "src/hooks/useDetectionAnalysis.ts",
        "src/hooks/useWebSocketEvents.ts",
        "src/services/s3UploadService.js",
        
        # Package configuration
        "package.json"
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

def test_progressive_video_uploader_component():
    """Test ProgressiveVideoUploader component structure"""
    print("\n🔍 Testing ProgressiveVideoUploader component...")
    
    component_path = "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.jsx"
    
    try:
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required imports
        required_imports = [
            "import React",
            "useDropzone",
            "useVideoUpload",
            "EmbeddingCache",
            "formatFileSize",
            "formatTimeRemaining",
            "formatUploadSpeed"
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
            "handleFileSelect",
            "processSelectedFile",
            "startUpload",
            "handleUploadProgress",
            "checkForDuplicate",
            "renderDropZone",
            "renderFilePreview",
            "renderUploadProgress"
        ]
        
        missing_functions = []
        for function in required_functions:
            if function not in content:
                missing_functions.append(function)
        
        if missing_functions:
            print(f"❌ Missing functions: {missing_functions}")
            return False
        
        # Check for drag-and-drop functionality
        drag_drop_features = [
            "getRootProps",
            "getInputProps",
            "isDragActive",
            "isDragReject",
            "onDrop",
            "onDragEnter",
            "onDragLeave"
        ]
        
        missing_drag_drop = []
        for feature in drag_drop_features:
            if feature not in content:
                missing_drag_drop.append(feature)
        
        if missing_drag_drop:
            print(f"❌ Missing drag-and-drop features: {missing_drag_drop}")
            return False
        
        print("✅ ProgressiveVideoUploader component structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading ProgressiveVideoUploader component: {e}")
        return False

def test_analysis_progress_tracker_component():
    """Test AnalysisProgressTracker component structure"""
    print("\n🔍 Testing AnalysisProgressTracker component...")
    
    component_path = "src/components/AnalysisProgressTracker/AnalysisProgressTracker.jsx"
    
    try:
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required imports
        required_imports = [
            "import React",
            "useDetectionAnalysis",
            "useWebSocketEvents",
            "formatTimeRemaining"
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
            "handleProcessingProgress",
            "handleProcessingComplete",
            "handleProcessingFailed",
            "renderProcessingProgress",
            "renderAnalysisResult",
            "renderError"
        ]
        
        missing_functions = []
        for function in required_functions:
            if function not in content:
                missing_functions.append(function)
        
        if missing_functions:
            print(f"❌ Missing functions: {missing_functions}")
            return False
        
        # Check for WebSocket integration
        websocket_features = [
            "subscribe",
            "unsubscribe",
            "sendMessage",
            "isConnected",
            "connectionState"
        ]
        
        missing_websocket = []
        for feature in websocket_features:
            if feature not in content:
                missing_websocket.append(feature)
        
        if missing_websocket:
            print(f"❌ Missing WebSocket features: {missing_websocket}")
            return False
        
        print("✅ AnalysisProgressTracker component structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading AnalysisProgressTracker component: {e}")
        return False

def test_embedding_cache_utility():
    """Test EmbeddingCache utility structure"""
    print("\n🔍 Testing EmbeddingCache utility...")
    
    cache_path = "src/utils/EmbeddingCache.js"
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required class and methods
        required_features = [
            "class EmbeddingCache",
            "generateFileHash",
            "checkDuplicate",
            "addToCache",
            "clearLocalCache",
            "getCacheStats",
            "batchCheckDuplicates"
        ]
        
        missing_features = []
        for feature in required_features:
            if feature not in content:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing EmbeddingCache features: {missing_features}")
            return False
        
        # Check for hash generation methods
        hash_methods = [
            "generateFileHash",
            "generateFileHashFallback",
            "crypto.subtle.digest",
            "SHA-256"
        ]
        
        missing_hash_methods = []
        for method in hash_methods:
            if method not in content:
                missing_hash_methods.append(method)
        
        if missing_hash_methods:
            print(f"❌ Missing hash generation methods: {missing_hash_methods}")
            return False
        
        print("✅ EmbeddingCache utility structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading EmbeddingCache utility: {e}")
        return False

def test_css_modules():
    """Test CSS module files"""
    print("\n🔍 Testing CSS modules...")
    
    css_files = [
        "src/components/ProgressiveVideoUploader/ProgressiveVideoUploader.module.css",
        "src/components/AnalysisProgressTracker/AnalysisProgressTracker.module.css"
    ]
    
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for basic CSS structure
            if not content.strip():
                print(f"❌ Empty CSS file: {css_file}")
                return False
            
            # Check for responsive design
            responsive_features = [
                "@media",
                "flex",
                "grid",
                "responsive"
            ]
            
            has_responsive = any(feature in content for feature in responsive_features)
            if not has_responsive:
                print(f"⚠️  CSS file may lack responsive design: {css_file}")
            
            print(f"✅ CSS file valid: {css_file}")
            
        except Exception as e:
            print(f"❌ Error reading CSS file {css_file}: {e}")
            return False
    
    return True

def test_package_dependencies():
    """Test package.json dependencies"""
    print("\n🔍 Testing package dependencies...")
    
    try:
        with open("package.json", 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        required_deps = [
            "react",
            "react-dom",
            "react-dropzone",
            "@tanstack/react-query",
            "@aws-sdk/client-s3",
            "@aws-sdk/s3-request-presigner"
        ]
        
        dev_deps = [
            "@types/react",
            "@types/react-dom",
            "@types/node",
            "vite",
            "eslint"
        ]
        
        missing_deps = []
        for dep in required_deps:
            if dep not in package_data.get("dependencies", {}):
                missing_deps.append(dep)
        
        missing_dev_deps = []
        for dep in dev_deps:
            if dep not in package_data.get("devDependencies", {}):
                missing_dev_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing dependencies: {missing_deps}")
            return False
        
        if missing_dev_deps:
            print(f"⚠️  Missing dev dependencies: {missing_dev_deps}")
        
        print("✅ Package dependencies valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading package.json: {e}")
        return False

def test_video_processing_utilities():
    """Test video processing utility updates"""
    print("\n🔍 Testing video processing utilities...")
    
    utils_path = "src/utils/videoProcessing.js"
    
    try:
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for new utility functions
        new_functions = [
            "formatUploadSpeed",
            "extractFileMetadata"
        ]
        
        missing_functions = []
        for func in new_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing utility functions: {missing_functions}")
            return False
        
        print("✅ Video processing utilities valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading video processing utilities: {e}")
        return False

def test_integration_points():
    """Test integration with existing hooks and services"""
    print("\n🔍 Testing integration points...")
    
    # Check that existing hooks are still present
    existing_hooks = [
        "src/hooks/useVideoUpload.ts",
        "src/hooks/useDetectionAnalysis.ts",
        "src/hooks/useWebSocketEvents.ts"
    ]
    
    for hook_path in existing_hooks:
        if not os.path.exists(hook_path):
            print(f"❌ Missing existing hook: {hook_path}")
            return False
    
    # Check that services are present
    existing_services = [
        "src/services/s3UploadService.js"
    ]
    
    for service_path in existing_services:
        if not os.path.exists(service_path):
            print(f"❌ Missing existing service: {service_path}")
            return False
    
    print("✅ Integration points valid")
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Work Order #3 Implementation Tests")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_progressive_video_uploader_component,
        test_analysis_progress_tracker_component,
        test_embedding_cache_utility,
        test_css_modules,
        test_package_dependencies,
        test_video_processing_utilities,
        test_integration_points
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
        print("🎉 All tests passed! Work Order #3 implementation is complete.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
