# Fix Backbone Names - Get V13 Working

## Problem Found!

The diagnostic showed:
- ✅ **ViT-Large works!** (`vit_large_patch16_224` is correct)
- ❌ **ConvNeXt-Large fails!** (`convnext_large.fb_in22k_ft_in1k` NOT found in timm)

## Solution: Find Correct Backbone Names

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy script to find correct names
docker cp find_correct_backbone_names.py secureai-backend:/app/

# Run it to find correct backbone names
docker exec secureai-backend python3 find_correct_backbone_names.py
```

This will show:
- All available ConvNeXt-Large models
- All available ViT-Large models (we know this works)
- All available Swin-Large models
- **Recommended model names to use**

## Then Update Code

Once we know the correct names, we'll update `deepfake_detector_v13.py` with the correct backbone names.

## Quick Fix: Try Common Alternatives

Based on timm naming conventions, try these:

**ConvNeXt-Large alternatives:**
- `convnext_large` (simplest)
- `convnext_large.fb_in22k`
- `convnext_large_in22k`

**Swin-Large alternatives:**
- `swin_large_patch4_window7_224_in22k`
- `swin_large_patch4_window7_224`

---

**Run the script to find the exact correct names, then we'll update the code!** 🔧
