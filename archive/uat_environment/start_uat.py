#!/usr/bin/env python3
"""
UAT Startup Script for SecureAI DeepFake Detection System
Simple script to start the UAT process
"""

import sys
import json
from pathlib import Path

def main():
    """Main startup function"""
    print("🚀 Starting SecureAI DeepFake Detection System UAT")
    print("=" * 60)
    
    # Check if UAT environment exists
    uat_dir = Path("uat_environment")
    if not uat_dir.exists():
        print("❌ UAT environment not found!")
        print("Please run: python uat_setup.py first")
        return False
    
    # Check configuration
    config_file = uat_dir / "config" / "uat_config.json"
    if not config_file.exists():
        print("❌ UAT configuration not found!")
        return False
    
    # Load and display configuration
    with open(config_file, "r") as f:
        config = json.load(f)
    
    print("📋 UAT Configuration:")
    print(f"  • Environment: {config['test_environment']['name']}")
    print(f"  • Base URL: {config['test_environment']['base_url']}")
    print(f"  • API Version: {config['test_environment']['api_version']}")
    
    print("\n👥 Enabled Personas:")
    for persona, persona_config in config["personas"].items():
        if persona_config["enabled"]:
            print(f"  ✅ {persona.replace('_', ' ').title()}")
    
    print("\n🎯 Performance Requirements:")
    perf_req = config["performance_requirements"]
    print(f"  • Max Processing Time: {perf_req['max_processing_time_seconds']}s")
    print(f"  • Min Detection Accuracy: {perf_req['min_detection_accuracy']:.1%}")
    print(f"  • Max False Positive Rate: {perf_req['max_false_positive_rate']:.1%}")
    print(f"  • Min System Uptime: {perf_req['min_system_uptime']:.1%}")
    
    print("\n🚀 Starting UAT Test Runner...")
    print("=" * 60)
    
    # Import and run the test runner
    try:
        from uat_test_runner import UATTestRunner
        
        runner = UATTestRunner()
        success = runner.run_complete_uat()
        
        if success:
            print("\n✅ UAT Execution Completed Successfully!")
            print("🎉 System approved for deployment!")
        else:
            print("\n❌ UAT Execution Failed!")
            print("🔧 Please address issues before deployment.")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import UAT test runner: {e}")
        print("Please ensure uat_test_runner.py is in the current directory")
        return False
    except Exception as e:
        print(f"❌ UAT execution error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
