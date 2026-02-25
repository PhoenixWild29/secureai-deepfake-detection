#!/usr/bin/env python3
"""
Simple server starter without Unicode characters
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from api import app
    print("Starting SecureAI DeepFake Detection API...")
    print("Web Interface: http://localhost:5000")
    print("API Endpoints: http://localhost:5000/api/*")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    print(f"Error starting server: {e}")
    input("Press Enter to continue...")
