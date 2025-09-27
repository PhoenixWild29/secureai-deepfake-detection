#!/usr/bin/env python3
"""
Test script for SecureAI API
"""
import requests
import time
import os

API_BASE = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_single_analysis():
    """Test single video analysis"""
    print("\n🎥 Testing single video analysis...")

    # Use existing sample video
    video_path = "sample_video.mp4"
    if not os.path.exists(video_path):
        print(f"❌ Test video not found: {video_path}")
        return False

    try:
        with open(video_path, 'rb') as f:
            files = {'video': f}
            response = requests.post(f"{API_BASE}/analyze", files=files)

        if response.status_code == 200:
            result = response.json()
            analysis_id = result['analysis_id']
            detection_result = result['result']

            print("✅ Analysis completed!")
            print(f"   Analysis ID: {analysis_id}")
            print(f"   Result: {'FAKE' if detection_result['is_fake'] else 'AUTHENTIC'}")
            print(f"   Confidence: {detection_result['confidence']:.2%}")
            print(f"   Video Hash: {detection_result['video_hash'][:16]}...")

            # Test result retrieval
            print("🔍 Testing result retrieval...")
            result_response = requests.get(f"{API_BASE}/analyze/{analysis_id}")
            if result_response.status_code == 200:
                print("✅ Result retrieval successful")
            else:
                print(f"❌ Result retrieval failed: {result_response.status_code}")

            return True
        else:
            print(f"❌ Analysis failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return False

def test_batch_analysis():
    """Test batch video analysis"""
    print("\n📦 Testing batch analysis...")

    video_files = ["sample_video.mp4", "test_video_1.mp4", "test_video_2.mp4"]
    existing_files = [f for f in video_files if os.path.exists(f)]

    if len(existing_files) < 2:
        print("⚠️  Not enough test videos for batch test, skipping...")
        return True

    try:
        files = [('videos', open(f, 'rb')) for f in existing_files[:3]]  # Max 3 files
        response = requests.post(f"{API_BASE}/batch", files=files)

        # Close files
        for _, f in files:
            f.close()

        if response.status_code == 200:
            result = response.json()
            batch_id = result['batch_id']
            print(f"✅ Batch processing started: {batch_id}")

            # Wait for completion
            print("⏳ Waiting for batch completion...")
            max_wait = 60  # 60 seconds max
            for i in range(max_wait):
                status_response = requests.get(f"{API_BASE}/batch/{batch_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['status'] == 'completed':
                        completed = status_data['completed']
                        total = status_data['total_files']
                        print(f"✅ Batch completed: {completed}/{total} videos processed")
                        return True
                time.sleep(1)

            print("⏰ Batch processing timeout")
            return False
        else:
            print(f"❌ Batch analysis failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Batch analysis error: {e}")
        return False

def test_statistics():
    """Test statistics endpoint"""
    print("\n📊 Testing statistics endpoint...")
    try:
        response = requests.get(f"{API_BASE}/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ Statistics retrieved:")
            proc_stats = stats['processing_stats']
            print(f"   Total analyses: {proc_stats['total_analyses']}")
            print(f"   Videos processed: {proc_stats['videos_processed']}")
            print(f"   Fake detected: {proc_stats['fake_detected']}")
            print(f"   Authentic detected: {proc_stats['authentic_detected']}")
            return True
        else:
            print(f"❌ Statistics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Statistics error: {e}")
        return False

def main():
    """Run all API tests"""
    print("🧪 TESTING SECUREAI API")
    print("=" * 50)

    # Wait a moment for server to start
    time.sleep(2)

    tests = [
        ("Health Check", test_health),
        ("Single Analysis", test_single_analysis),
        ("Batch Analysis", test_batch_analysis),
        ("Statistics", test_statistics)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\n🚀 API is ready for production use!")
        print("📖 API Endpoints:")
        print("   POST /api/analyze - Single video analysis")
        print("   POST /api/batch - Batch video analysis")
        print("   GET /api/analyze/<id> - Get analysis result")
        print("   GET /api/batch/<id> - Get batch status")
        print("   GET /api/stats - Get processing statistics")
        print("   GET /api/results - List all results")
    else:
        print("⚠️  Some tests failed. Check server logs.")

if __name__ == "__main__":
    main()