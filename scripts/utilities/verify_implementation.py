#!/usr/bin/env python3
"""
Verification script to check that all implementation components are complete.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status."""
    exists = os.path.isdir(dirpath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {dirpath}")
    return exists

def verify_implementation():
    """Verify all implementation components."""
    print("=" * 70)
    print("VERIFYING ENSEMBLE DETECTOR IMPLEMENTATION")
    print("=" * 70)
    print()
    
    project_root = Path(__file__).parent
    all_good = True
    
    # Core implementation files
    print("CORE IMPLEMENTATION FILES:")
    print("-" * 70)
    files_to_check = [
        ("ai_model/enhanced_detector.py", "Main detector implementation"),
        ("requirements.txt", "Updated requirements file"),
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(project_root / filepath, description):
            all_good = False
    
    print()
    
    # Installation scripts
    print("INSTALLATION SCRIPTS:")
    print("-" * 70)
    scripts = [
        ("install_ensemble_dependencies.bat", "Batch installation script"),
        ("install_ensemble_dependencies.ps1", "PowerShell installation script"),
        ("install_ensemble_dependencies_fixed.bat", "Fixed installation script"),
    ]
    
    for filepath, description in scripts:
        if not check_file_exists(project_root / filepath, description):
            all_good = False
    
    print()
    
    # Test scripts
    print("TEST SCRIPTS:")
    print("-" * 70)
    test_files = [
        ("test_ensemble_detector.py", "Main test script"),
    ]
    
    for filepath, description in test_files:
        if not check_file_exists(project_root / filepath, description):
            all_good = False
    
    print()
    
    # Setup scripts
    print("SETUP SCRIPTS:")
    print("-" * 70)
    setup_files = [
        ("setup_laa_net.py", "LAA-Net setup script"),
        ("setup_laa_net_complete.bat", "Complete LAA-Net setup script"),
    ]
    
    for filepath, description in setup_files:
        if not check_file_exists(project_root / filepath, description):
            all_good = False
    
    print()
    
    # Documentation files
    print("DOCUMENTATION FILES:")
    print("-" * 70)
    docs = [
        ("ENSEMBLE_DETECTOR_SETUP.md", "Main setup guide"),
        ("IMPLEMENTATION_SUMMARY.md", "Implementation summary"),
        ("QUICK_START_ENSEMBLE.md", "Quick start guide"),
        ("STEP_BY_STEP_SETUP.md", "Step-by-step setup"),
        ("READY_TO_RUN.md", "Ready to run guide"),
        ("FIX_INSTALLATION_ISSUES.md", "Installation fixes guide"),
        ("QUICK_FIX_INSTALL.txt", "Quick fix reference"),
        ("external/README.md", "LAA-Net setup guide"),
    ]
    
    for filepath, description in docs:
        if not check_file_exists(project_root / filepath, description):
            all_good = False
    
    print()
    
    # Directory structure
    print("DIRECTORY STRUCTURE:")
    print("-" * 70)
    dirs = [
        ("external", "External dependencies directory"),
        ("ai_model", "AI model directory"),
    ]
    
    for dirpath, description in dirs:
        if not check_directory_exists(project_root / dirpath, description):
            all_good = False
    
    print()
    
    # Check requirements.txt content
    print("REQUIREMENTS.TXT CONTENT CHECK:")
    print("-" * 70)
    req_file = project_root / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text()
        checks = [
            ("open-clip-torch", "open-clip-torch dependency"),
            ("albumentations", "albumentations dependency"),
            ("imgaug", "imgaug dependency"),
            ("scikit-image", "scikit-image dependency"),
            ("tensorboardX", "tensorboardX dependency"),
            ("mtcnn", "mtcnn dependency"),
        ]
        
        for keyword, description in checks:
            found = keyword in content
            status = "✓" if found else "✗"
            print(f"{status} {description}")
            if not found:
                all_good = False
    else:
        print("✗ requirements.txt not found")
        all_good = False
    
    print()
    
    # Check enhanced_detector.py key components
    print("DETECTOR CODE COMPONENTS:")
    print("-" * 70)
    detector_file = project_root / "ai_model" / "enhanced_detector.py"
    if detector_file.exists():
        content = detector_file.read_text()
        components = [
            ("class EnhancedDetector", "EnhancedDetector class"),
            ("class FaceDetector", "FaceDetector class"),
            ("open_clip", "CLIP import"),
            ("clip_detect_frames", "CLIP detection method"),
            ("laa_detect_frames", "LAA-Net detection method"),
            ("def detect", "Main detect method"),
        ]
        
        for keyword, description in components:
            found = keyword in content
            status = "✓" if found else "✗"
            print(f"{status} {description}")
            if not found:
                all_good = False
    else:
        print("✗ enhanced_detector.py not found")
        all_good = False
    
    print()
    
    # Summary
    print("=" * 70)
    if all_good:
        print("✓ ALL CHECKS PASSED - Implementation is complete!")
        print()
        print("Next steps:")
        print("1. Run: install_ensemble_dependencies_fixed.bat")
        print("2. Run: python test_ensemble_detector.py")
        print("3. (Optional) Run: setup_laa_net_complete.bat")
    else:
        print("✗ SOME CHECKS FAILED - Please review missing components")
    print("=" * 70)
    
    return all_good

if __name__ == "__main__":
    success = verify_implementation()
    sys.exit(0 if success else 1)

