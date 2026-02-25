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
    # List all available models using the official API
    # Reference: https://ai.google.dev/api/models
    models = genai.list_models()
    models_list = list(models)
    
    print(f"Found {len(models_list)} models:\n")
    
    # Filter models that support generateContent
    generate_content_models = []
    for model in models_list:
        name = model.name.replace('models/', '')
        # Try to get base_model_id from the model object
        base_model_id = getattr(model, 'base_model_id', None)
        if not base_model_id:
            # Fallback: extract from name (remove version suffixes like -001, -preview, etc.)
            parts = name.split('-')
            if len(parts) >= 3:
                # For names like "gemini-2.5-flash-001", use "gemini-2.5-flash"
                base_model_id = '-'.join(parts[:3])
            elif len(parts) >= 2:
                # For names like "gemini-pro", use as-is
                base_model_id = '-'.join(parts[:2])
            else:
                base_model_id = name
        
        display_name = getattr(model, 'display_name', getattr(model, 'displayName', 'N/A'))
        supported_methods = getattr(model, 'supported_generation_methods', getattr(model, 'supportedGenerationMethods', []))
        
        # Check if model supports generateContent
        supports_generate = False
        if supported_methods:
            # Check both the list and string representations
            methods_str = ' '.join(str(m) for m in supported_methods).lower()
            supports_generate = 'generatecontent' in methods_str or any('generatecontent' in str(m).lower() for m in supported_methods)
        
        print(f"Model Name: {name}")
        print(f"  Base Model ID (use this): {base_model_id}")
        if display_name != 'N/A':
            print(f"  Display Name: {display_name}")
        if supported_methods:
            print(f"  Supported Methods: {', '.join(supported_methods)}")
        if supports_generate:
            print(f"  ✓ Supports generateContent - CAN USE FOR SECURESAGE")
            generate_content_models.append(base_model_id)
        print()
    
    print("=" * 60)
    print("Models that support generateContent (use these for SecureSage):")
    print("=" * 60)
    for model_id in generate_content_models:
        print(f"  - {model_id}")
    print()
    print("=" * 60)
    print("Recommended models for SecureSage (in order of preference):")
    print("=" * 60)
    # Prioritize based on common patterns
    priority_models = [
        'gemini-3-pro',
        'gemini-3-flash',
        'gemini-2.5-pro',
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash',
        'gemini-pro',
    ]
    for model_id in priority_models:
        if model_id in generate_content_models:
            print(f"  ✓ {model_id} - Available and recommended")
        else:
            print(f"  ✗ {model_id} - Not available")
    print("=" * 60)
    
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
