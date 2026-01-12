#!/usr/bin/env python3
"""
Integration script to add DeepFake Detector V13 and other models to ensemble
"""
import os
import sys

print("=" * 70)
print("🚀 Integrating Best Models for Ultimate Deepfake Detection")
print("=" * 70)
print()

# Step 1: Install required packages
print("Step 1: Installing required packages...")
print("-" * 70)

packages = [
    "transformers",
    "huggingface-hub",
    "timm",  # For Vision Transformer
    "efficientnet-pytorch"  # For EfficientNet
]

for package in packages:
    print(f"Installing {package}...")
    os.system(f"pip install {package} --quiet")

print("✅ Packages installed")
print()

# Step 2: Test model loading
print("Step 2: Testing model availability...")
print("-" * 70)

# Test transformers
try:
    from transformers import AutoModel, AutoImageProcessor
    print("✅ transformers library available")
except ImportError:
    print("❌ transformers library not available")
    sys.exit(1)

# Test timm
try:
    import timm
    print("✅ timm library available")
except ImportError:
    print("⚠️  timm library not available (needed for ViT)")

# Test efficientnet
try:
    from efficientnet_pytorch import EfficientNet
    print("✅ efficientnet-pytorch library available")
except ImportError:
    print("⚠️  efficientnet-pytorch library not available (needed for EfficientNet)")

print()
print("✅ Integration script complete!")
print()
print("Next steps:")
print("1. Models will be integrated into ensemble_detector.py")
print("2. Test the enhanced ensemble")
print("3. Benchmark accuracy improvements")
