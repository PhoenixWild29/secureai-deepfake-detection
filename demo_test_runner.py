#!/usr/bin/env python3
"""
Simple Demo: Actually Testing Your Detection System
Shows the testing suite in action with your existing videos
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_detection_with_sample_video():
    """Actual test using your sample video"""
    print("=" * 70)
    print("Running Actual Detection Test on Your Video")
    print("=" * 70)
    
    try:
        # Import detection function
        from ai_model.detect import detect_fake
        
        # Test with your sample video
        video_path = "sample_video.mp4"
        
        if not Path(video_path).exists():
            print(f"ERROR: Video not found: {video_path}")
            return False
        
        print(f"\nTesting video: {video_path}")
        print("Running detection...")
        
        # Run detection
        result = detect_fake(video_path, model_type='resnet')
        
        # Display results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        
        is_fake = result.get('is_fake', False)
        confidence = result.get('confidence', 0) * 100
        
        if is_fake:
            print(f"Result: DEEPFAKE DETECTED")
        else:
            print(f"Result: AUTHENTIC VIDEO")
        
        print(f"Confidence: {confidence:.1f}%")
        print(f"Processing Time: {result.get('processing_time', 0):.2f}s")
        print(f"Method: {result.get('method', 'unknown')}")
        
        print("\n" + "=" * 70)
        print("TEST PASSED - Detection system working!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """Test API endpoint"""
    print("\n" + "=" * 70)
    print("Testing API Endpoint")
    print("=" * 70)
    
    try:
        import requests
        
        # Health check
        print("\n1. Testing health endpoint...")
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        response.raise_for_status()
        print("   [OK] API is healthy")
        
        # Analyze endpoint
        print("\n2. Testing analyze endpoint...")
        if Path("sample_video.mp4").exists():
            with open("sample_video.mp4", "rb") as f:
                files = {"video": f}
                response = requests.post(
                    "http://localhost:5000/api/analyze",
                    files=files,
                    timeout=120
                )
                response.raise_for_status()
                result = response.json()
                print("   [OK] API analysis successful")
                print(f"   Result: {'FAKE' if result['result']['is_fake'] else 'AUTHENTIC'}")
                return True
        else:
            print("   [WARN] Sample video not found, skipping API test")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   [FAIL] API server not running")
        print("   Start it with: python api.py")
        return False
    except Exception as e:
        print(f"   [FAIL] API test failed: {e}")
        return False


def main():
    """Main demo"""
    print("\n" + "=" * 70)
    print("SecureAI DeepFake Detection - ACTUAL TESTING DEMO")
    print("=" * 70)
    print("\nThis will test your actual detection system, not just the test suite!")
    
    results = []
    
    # Test 1: Direct detection
    print("\n[TEST 1] Direct Detection Function")
    results.append(("Direct Detection", test_detection_with_sample_video()))
    
    # Test 2: API endpoint
    print("\n[TEST 2] API Endpoint")
    results.append(("API Endpoint", test_api_endpoint()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TESTING SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name:25} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if passed == total:
        print("\nALL TESTS PASSED! Your detection system is working!")
    else:
        print("\nSome tests failed. Check the errors above.")
    
    print("=" * 70)


if __name__ == '__main__':
    main()

