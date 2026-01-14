#!/usr/bin/env python3
"""
Find correct backbone names for V13 models in timm
"""
import timm

print("=" * 70)
print("🔍 Finding Correct Backbone Names for V13")
print("=" * 70)
print()

all_models = timm.list_models(pretrained=False)

# Find ConvNeXt-Large models
print("1️⃣  ConvNeXt-Large models:")
print("-" * 70)
convnext_models = [m for m in all_models if 'convnext' in m.lower() and 'large' in m.lower()]
for model in convnext_models[:15]:
    print(f"   - {model}")

# Find the one that matches our pattern
target_convnext = 'convnext_large.fb_in22k_ft_in1k'
if target_convnext in all_models:
    print(f"\n   ✅ Exact match found: {target_convnext}")
else:
    print(f"\n   ❌ Exact match NOT found: {target_convnext}")
    # Try alternatives
    alternatives = [
        'convnext_large',
        'convnext_large.fb_in22k',
        'convnext_large_in22k',
    ]
    for alt in alternatives:
        matches = [m for m in convnext_models if alt in m]
        if matches:
            print(f"   ✅ Alternative found: {matches[0]}")
            break

print()

# Find ViT-Large models
print("2️⃣  ViT-Large models:")
print("-" * 70)
vit_models = [m for m in all_models if 'vit_large' in m.lower() and 'patch16' in m.lower()]
for model in vit_models[:10]:
    print(f"   - {model}")

target_vit = 'vit_large_patch16_224'
if target_vit in all_models:
    print(f"\n   ✅ Exact match found: {target_vit}")
else:
    print(f"\n   ❌ Exact match NOT found: {target_vit}")

print()

# Find Swin-Large models
print("3️⃣  Swin-Large models:")
print("-" * 70)
swin_models = [m for m in all_models if 'swin' in m.lower() and 'large' in m.lower() and 'patch4' in m.lower()]
for model in swin_models[:15]:
    print(f"   - {model}")

target_swin = 'swin_large_patch4_window7_224'
if target_swin in all_models:
    print(f"\n   ✅ Exact match found: {target_swin}")
else:
    print(f"\n   ❌ Exact match NOT found: {target_swin}")
    # Try alternatives
    alternatives = [
        'swin_large_patch4',
        'swin_large',
    ]
    for alt in alternatives:
        matches = [m for m in swin_models if alt in m]
        if matches:
            print(f"   ✅ Alternative found: {matches[0]}")
            break

print()
print("=" * 70)
print("📋 Recommended Model Names:")
print("=" * 70)

# Get best matches
convnext_best = [m for m in convnext_models if 'convnext_large' in m and ('fb_in22k' in m or 'in22k' in m)]
vit_best = [m for m in vit_models if 'vit_large_patch16_224' in m]
swin_best = [m for m in swin_models if 'swin_large_patch4_window7_224' in m]

print(f"ConvNeXt-Large: {convnext_best[0] if convnext_best else convnext_models[0] if convnext_models else 'NOT FOUND'}")
print(f"ViT-Large: {vit_best[0] if vit_best else vit_models[0] if vit_models else 'NOT FOUND'}")
print(f"Swin-Large: {swin_best[0] if swin_best else swin_models[0] if swin_models else 'NOT FOUND'}")
