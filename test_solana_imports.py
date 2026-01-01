#!/usr/bin/env python3
"""Test script to verify Solana Python SDK imports"""

print("Testing Solana Python SDK imports...")

# Test 1: Try importing solana package
try:
    import solana
    print(f"✅ solana package imported: {solana.__version__ if hasattr(solana, '__version__') else 'version unknown'}")
    print(f"   Package location: {solana.__file__}")
    print(f"   Available attributes: {dir(solana)[:10]}...")
except ImportError as e:
    print(f"❌ Failed to import solana: {e}")

# Test 2: Try importing solders
try:
    import solders
    print(f"✅ solders package imported")
    print(f"   Package location: {solders.__file__}")
except ImportError as e:
    print(f"❌ Failed to import solders: {e}")

# Test 3: Try different import paths
import_paths = [
    "solana.rpc.api",
    "solana.keypair",
    "solana.transaction",
    "solana.system_program",
    "solders.rpc.api",
    "solders.keypair",
    "solders.transaction",
]

print("\nTesting specific import paths:")
for path in import_paths:
    try:
        module = __import__(path, fromlist=[''])
        print(f"✅ {path} - OK")
    except ImportError as e:
        print(f"❌ {path} - {e}")

# Test 4: Check what's actually in solana package
try:
    import solana
    print(f"\nContents of solana package:")
    for item in dir(solana):
        if not item.startswith('_'):
            print(f"  - {item}")
except:
    pass

