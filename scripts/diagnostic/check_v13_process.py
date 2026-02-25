#!/usr/bin/env python3
"""
Check if V13 loading process is still running
"""
import subprocess
import sys

print("Checking for running V13 processes...")
print()

try:
    # Check for Python processes
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    
    # Look for V13 or test processes
    v13_processes = []
    for line in result.stdout.split('\n'):
        if 'python' in line.lower() and ('v13' in line.lower() or 'test_v13' in line.lower() or 'deepfake_detector' in line.lower()):
            v13_processes.append(line)
    
    if v13_processes:
        print("⚠️  Found running processes:")
        for proc in v13_processes:
            print(f"   {proc}")
        print()
        print("The V13 loading might still be running.")
        print("Wait a few more minutes, or kill the process if stuck.")
    else:
        print("✅ No V13 processes found")
        print("The process has completed (or failed).")
        
except Exception as e:
    print(f"Error checking processes: {e}")

print()
print("To check V13 status, run:")
print("  docker exec secureai-backend python3 check_v13_status.py")
