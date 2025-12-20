#!/usr/bin/env python3
"""
Setup script for LAA-Net integration.
This script helps set up the LAA-Net submodule and prepares the environment.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {cmd}")
        print(f"  Error: {e.stderr}")
        return False

def setup_laa_net():
    """Set up LAA-Net as a git submodule."""
    project_root = Path(__file__).parent
    external_dir = project_root / "external"
    laa_net_dir = external_dir / "laa_net"
    
    print("Setting up LAA-Net integration...")
    print("=" * 60)
    
    # Create external directory if it doesn't exist
    external_dir.mkdir(exist_ok=True)
    print(f"✓ Created external directory: {external_dir}")
    
    # Check if LAA-Net already exists
    if laa_net_dir.exists():
        print(f"✓ LAA-Net directory already exists: {laa_net_dir}")
        print("  To reinstall, delete this directory and run this script again.")
        return True
    
    # Try to add as git submodule
    print("\nAttempting to add LAA-Net as git submodule...")
    success = run_command(
        f'git submodule add https://github.com/10Ring/LAA-Net external/laa_net',
        cwd=project_root
    )
    
    if not success:
        print("\nGit submodule add failed. Trying manual clone...")
        success = run_command(
            f'git clone https://github.com/10Ring/LAA-Net {laa_net_dir}',
            cwd=external_dir
        )
    
    if success:
        print("\n✓ LAA-Net repository cloned successfully!")
        print("\nNext steps:")
        print("1. Install LAA-Net dependencies:")
        print(f"   cd {laa_net_dir}")
        print("   pip install -r requirements.txt")
        print("\n2. Download pre-trained weights from LAA-Net repository")
        print("   (Check their README for download links)")
        print("\n3. Update ai_model/enhanced_detector.py with LAA-Net imports")
        print("   (See external/README.md for details)")
    else:
        print("\n✗ Failed to set up LAA-Net repository.")
        print("  You can manually clone it:")
        print(f"  cd {external_dir}")
        print("  git clone https://github.com/10Ring/LAA-Net laa_net")
    
    return success

if __name__ == "__main__":
    setup_laa_net()

