#!/usr/bin/env python3
"""
List available Gemini models for your API key
Run this to see which models are available
"""

import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed")
    print("Install with: pip install google-generativeai")
    sys.exit(1)

# Get API key from environment
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("ERROR: GEMINI_API_KEY environment variable not set")
    print("Set it with: export GEMINI_API_KEY=your_key_here")
    sys.exit(1)

# Configure
genai.configure(api_key=api_key)

print("=" * 60)
print("Available Gemini Models")
print("=" * 60)
print()

try:
    # List all available models
    models = genai.list_models()
    
    print(f"Found {len(list(models))} models:\n")
    
    for model in models:
        name = model.name.replace('models/', '')
        display_name = getattr(model, 'display_name', 'N/A')
        supported_methods = getattr(model, 'supported_generation_methods', [])
        
        print(f"Model: {name}")
        if display_name != 'N/A':
            print(f"  Display Name: {display_name}")
        if supported_methods:
            print(f"  Supported Methods: {', '.join(supported_methods)}")
        print()
    
    print("=" * 60)
    print("Recommended models for SecureSage:")
    print("  - gemini-2.5-pro (most capable)")
    print("  - gemini-2.5-flash (faster, cheaper)")
    print("  - gemini-3-pro (latest, if available)")
    print("=" * 60)
    
except Exception as e:
    print(f"ERROR: Failed to list models: {e}")
    print("\nTrying common model names manually...")
    
    # Try common model names
    common_models = [
        'gemini-3-pro',
        'gemini-2.5-pro',
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash',
        'gemini-pro',
        'gemini-1.5-pro',
        'gemini-1.5-flash-latest',
    ]
    
    print("\nTesting common model names:")
    for model_name in common_models:
        try:
            model = genai.GenerativeModel(model_name)
            print(f"  ✓ {model_name} - Available")
        except Exception as err:
            print(f"  ✗ {model_name} - Not available: {str(err)[:50]}")
