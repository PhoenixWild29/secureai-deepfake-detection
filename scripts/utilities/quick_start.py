#!/usr/bin/env python3
"""
SecureAI DeepFake Detection - Quick Start
Simple script to get the system up and running quickly
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if critical dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing = []
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            print(f"  ✓ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("  ⚠ CUDA not available - using CPU (slower)")
    except ImportError:
        missing.append("torch")
    
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__}")
    except ImportError:
        missing.append("opencv-python")
    
    try:
        import flask
        print(f"✓ Flask {flask.__version__}")
    except ImportError:
        missing.append("flask")
    
    try:
        import numpy
        print(f"✓ NumPy {numpy.__version__}")
    except ImportError:
        missing.append("numpy")
    
    if missing:
        print("\n❌ Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall them with: pip install -r requirements.txt")
        return False
    
    print("✓ All critical dependencies installed!\n")
    return True

def check_models():
    """Check if trained models are available"""
    print("🔍 Checking for trained models...")
    
    model_files = [
        "ai_model/deepfake_classifier_best.pth",
        "ai_model/resnet_resnet50_best.pth",
        "yolov8n.pt"
    ]
    
    found_models = []
    for model_path in model_files:
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"✓ Found: {model_path} ({size_mb:.1f} MB)")
            found_models.append(model_path)
        else:
            print(f"⚠ Not found: {model_path}")
    
    if found_models:
        print(f"\n✓ Found {len(found_models)} trained model(s)!\n")
        return True
    else:
        print("\n⚠ No trained models found. The system will use default models.\n")
        return True  # Continue anyway

def check_test_videos():
    """Check for test videos"""
    print("🔍 Checking for test videos...")
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    test_videos = []
    
    # Check for specific test videos
    test_files = ['sample_video.mp4', 'test_video_1.mp4', 'test_video_2.mp4', 'test_video_3.mp4']
    for video in test_files:
        if os.path.exists(video):
            size_mb = os.path.getsize(video) / (1024 * 1024)
            print(f"✓ Found: {video} ({size_mb:.1f} MB)")
            test_videos.append(video)
    
    # Check uploads folder
    if os.path.exists('uploads'):
        for file in os.listdir('uploads'):
            if any(file.endswith(ext) for ext in video_extensions):
                test_videos.append(os.path.join('uploads', file))
    
    if test_videos:
        print(f"\n✓ Found {len(test_videos)} test video(s)!\n")
    else:
        print("\n⚠ No test videos found. You can upload videos through the web interface.\n")
    
    return test_videos

def create_directories():
    """Create necessary directories"""
    print("📁 Creating necessary directories...")
    
    dirs = ['uploads', 'results', 'static', 'templates']
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ {directory}/")
    
    print()

def test_detection(video_path=None):
    """Test the detection system"""
    if not video_path:
        # Find a test video
        test_videos = check_test_videos()
        if not test_videos:
            print("⚠ No test videos found. Skipping detection test.")
            return
        video_path = test_videos[0]
    
    print(f"🧪 Testing detection with: {video_path}")
    print("This may take a minute...\n")
    
    try:
        from ai_model.detect import detect_fake
        
        result = detect_fake(video_path, model_type='resnet')
        
        print("✓ Detection completed!")
        print(f"  Result: {'🚨 FAKE' if result.get('is_fake') else '✓ AUTHENTIC'}")
        print(f"  Confidence: {result.get('confidence', 0) * 100:.1f}%")
        print(f"  Processing time: {result.get('processing_time', 0):.2f}s")
        print(f"  Method: {result.get('method', 'unknown')}\n")
        
        return True
    except Exception as e:
        print(f"❌ Detection test failed: {e}\n")
        return False

def start_web_interface():
    """Start the Flask web interface"""
    print("🚀 Starting Web Interface...")
    print("=" * 60)
    print("📊 Web Interface will be available at: http://localhost:5000")
    print("🔗 API Documentation: http://localhost:5000/api/health")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Import and run the Flask app
        from api import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure port 5000 is not already in use")
        print("2. Check that all dependencies are installed")
        print("3. Try running: python api.py directly")

def main():
    """Main entry point"""
    print("=" * 60)
    print("🎯 SecureAI DeepFake Detection - Quick Start")
    print("=" * 60)
    print()
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first:")
        print("   pip install -r requirements.txt\n")
        return
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Check models
    check_models()
    
    # Step 4: Check test videos
    test_videos = check_test_videos()
    
    # Step 5: Ask user what they want to do
    print("What would you like to do?")
    print("1. Start web interface (recommended)")
    print("2. Test detection on a video")
    print("3. Both (test then start web interface)")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            start_web_interface()
        elif choice == '2':
            if test_videos:
                test_detection(test_videos[0])
            else:
                video_path = input("Enter path to video file: ").strip()
                if os.path.exists(video_path):
                    test_detection(video_path)
                else:
                    print(f"❌ Video not found: {video_path}")
        elif choice == '3':
            if test_videos:
                test_detection(test_videos[0])
            input("\nPress Enter to start web interface...")
            start_web_interface()
        elif choice == '4':
            print("\n👋 Goodbye!")
        else:
            print("\n❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

if __name__ == '__main__':
    main()


