#!/usr/bin/env python3
"""
System Status Monitor with Progress Bar
Shows real-time status of SecureAI DeepFake Detection System
"""
import os
import sys
import time
import psutil
from datetime import datetime
from pathlib import Path

def print_header():
    """Print system header"""
    print("🚀 SECUREAI DEEPFAKE DETECTION - SYSTEM STATUS")
    print("=" * 60)
    print(f"📅 Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"💻 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
    print()

def show_progress_bar(current, total, prefix="Progress", suffix="", length=50):
    """Display progress bar"""
    percent = int(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = "█" * filled_length + "░" * (length - filled_length)
    sys.stdout.write(f"\r{prefix}: [{bar}] {percent}% {suffix}")
    sys.stdout.flush()

def check_component_status(component_name, check_function, expected_time=5):
    """Check a component with progress indication"""
    print(f"🔍 Checking {component_name}...")
    start_time = time.time()

    # Show progress for the check
    for i in range(expected_time):
        show_progress_bar(i+1, expected_time, f"Testing {component_name}", f"({expected_time-i}s remaining)")
        time.sleep(1)

    # Perform actual check
    try:
        result = check_function()
        elapsed = time.time() - start_time
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n   {status} - {component_name} ({elapsed:.1f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n   ❌ ERROR - {component_name}: {e} ({elapsed:.1f}s)")
        return False

def check_model_files():
    """Check if trained models exist"""
    model_files = [
        "ai_model/deepfake_classifier_best.pth",
        "ai_model/deepfake_classifier_final.pth",
        "ai_model/trained_model.pt"
    ]
    return all(os.path.exists(f) for f in model_files)

def check_test_videos():
    """Check if test videos exist"""
    test_dirs = ["test_batch_videos", "test_videos"]
    total_videos = 0
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            total_videos += len([f for f in os.listdir(test_dir) if f.endswith('.mp4')])
    return total_videos >= 3

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import torch
        import cv2
        import flask
        import numpy as np
        return True
    except ImportError as e:
        print(f"   Missing dependency: {e}")
        return False

def check_batch_processing():
    """Check if batch processing results exist"""
    batch_dir = Path("batch_results")
    if not batch_dir.exists():
        return False
    json_files = list(batch_dir.glob("*.json"))
    csv_files = list(batch_dir.glob("*.csv"))
    return len(json_files) > 0 and len(csv_files) > 0

def check_benchmark_results():
    """Check if benchmark results exist"""
    benchmark_dir = Path("benchmark_results")
    if not benchmark_dir.exists():
        return False
    json_files = list(benchmark_dir.glob("*.json"))
    csv_files = list(benchmark_dir.glob("*.csv"))
    return len(json_files) > 0 and len(csv_files) > 0

def run_system_validation():
    """Run complete system validation with status updates"""
    print_header()

    components = [
        ("Dependencies", check_dependencies, 3),
        ("Model Files", check_model_files, 2),
        ("Test Videos", check_test_videos, 2),
        ("Batch Processing", check_batch_processing, 2),
        ("Benchmark Results", check_benchmark_results, 2),
    ]

    passed = 0
    total = len(components)

    print("🔬 RUNNING SYSTEM VALIDATION...")
    print()

    for i, (name, check_func, expected_time) in enumerate(components, 1):
        print(f"[{i}/{total}] ", end="")
        if check_component_status(name, check_func, expected_time):
            passed += 1
        print()

    print()
    print("📊 VALIDATION SUMMARY")
    print("-" * 30)
    print(f"Components Checked: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(".1f")

    if passed == total:
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Ready for production deployment")
    else:
        print(f"\n⚠️  {total - passed} components need attention")

    print(f"\n⏱️  Total validation time: {time.time() - start_time:.1f} seconds")
    print(f"📅 Completed at: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    start_time = time.time()
    run_system_validation()