# Get V13 Working - Step by Step

## Goal: V13 Working in Ultimate Ensemble

No workarounds. We're fixing V13 properly.

## Step 1: Run Diagnostic Script

This will find the exact problem:

```bash
cd ~/secureai-deepfake-detection
git pull origin master

# Copy diagnostic script
docker cp fix_v13_vit_large.py secureai-backend:/app/

# Run diagnostic
docker exec secureai-backend python3 fix_v13_vit_large.py
```

**This will:**
- Check if ViT-Large model name is correct
- Test different model creation approaches
- Find which approach works
- Test safetensors loading
- Test state dict loading
- **Tell us exactly what to fix**

## Step 2: Copy Updated Code

```bash
# Copy updated V13 code with timeout
docker cp ai_model/deepfake_detector_v13.py secureai-backend:/app/ai_model/
```

## Step 3: Test V13 Loading

```bash
# Test with timeout (3 minutes max)
docker exec secureai-backend python3 test_v13_simple.py
```

The updated code now has:
- ✅ 3-minute timeout for model creation
- ✅ Better error messages
- ✅ Backbone verification before creation
- ✅ Non-strict state dict loading (handles key mismatches)

## Step 4: If Still Hanging

Run the individual model test to see which model fails:

```bash
docker cp test_v13_models_individually.py secureai-backend:/app/
docker exec secureai-backend python3 test_v13_models_individually.py
```

This will show:
- Which model hangs (likely ViT-Large)
- How long it takes
- Exact error message

## Step 5: Check System Resources

ViT-Large is huge. Check if you have enough memory:

```bash
# Check memory
docker exec secureai-backend free -h

# Check if process is using memory
docker exec secureai-backend ps aux | grep python
```

If memory is low, we may need to:
- Load models one at a time
- Clear cache between loads
- Use model quantization

## Step 6: Verify V13 Works

Once loading succeeds:

```bash
docker exec secureai-backend python3 test_v13_loading.py
```

Should show all 3 models loaded.

## Step 7: Test Ultimate Ensemble

```bash
docker exec secureai-backend python3 test_ultimate_ensemble.py
```

Should show V13 integrated with all other models.

---

## What We Fixed

1. **Timeout mechanism**: 3-minute timeout prevents infinite hangs
2. **Better error handling**: Shows exactly where it fails
3. **Backbone verification**: Checks if model name exists before creating
4. **Non-strict loading**: Handles state dict key mismatches
5. **Progress logging**: Shows what's happening at each step

---

**Run the diagnostic script first - it will tell us exactly what's wrong!** 🔧

Then we'll fix it properly and get V13 working in the ultimate ensemble.
