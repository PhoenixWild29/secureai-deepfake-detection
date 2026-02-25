#!/usr/bin/env python3
"""
Demo script for the new professional interface
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 60)
    print("🎉 NEW PROFESSIONAL INTERFACE READY!")
    print("=" * 60)
    print()
    print("✅ Features of the new interface:")
    print("   • Modern dark mode design")
    print("   • Professional cybersecurity aesthetic")
    print("   • Drag & drop file upload")
    print("   • Real-time progress tracking")
    print("   • Interactive confidence gauge")
    print("   • Detailed forensic breakdown")
    print("   • Export functionality")
    print("   • Fully responsive design")
    print()
    print("🚀 Starting server...")
    print("   Open your browser to: http://localhost:5000")
    print("   The new interface will load automatically!")
    print()
    print("=" * 60)
    
    try:
        from api import app
        import os
        # Use environment variable for debug mode, default to False for security
        debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        app.run(debug=debug_mode, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == '__main__':
    main()
