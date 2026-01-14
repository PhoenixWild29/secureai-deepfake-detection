# How to Test the Ensemble Detector

## Quick Test (Easiest Method)

### Option 1: Run the Test Script (Recommended)

```cmd
python test_ensemble_detector.py
```

This will:
- Automatically find test videos in your project directory
- Run detection on each video
- Show detailed results

**Expected Output:**
```
Testing Enhanced Ensemble Detector (Priority 1 MVP)
======================================================================
✓ Successfully imported EnhancedDetector
✓ Detector initialized on device: cuda (or cpu)
✓ CLIP model: Loaded
✓ LAA-Net: Not available (submodule setup required)

Found 3 test video(s)

Test 1/3: sample_video.mp4
----------------------------------------------------------------------
  Method: clip_only
  Is Deepfake: False
  Ensemble Probability: 0.3245
  CLIP Probability: 0.3245
  LAA-Net Probability: 0.5000
  Frames Analyzed: 16
  LAA-Net Available: False
```

---

### Option 2: Quick Python Test

Open Python and run:

```python
from ai_model.enhanced_detector import EnhancedDetector

# Initialize detector
detector = EnhancedDetector()

# Test with a video
result = detector.detect('sample_video.mp4')

# Print results
print(f"Is Deepfake: {result['is_deepfake']}")
print(f"Confidence: {result['ensemble_fake_probability']:.4f}")
print(f"CLIP Score: {result['clip_fake_probability']:.4f}")
```

---

### Option 3: Test with Your Own Video

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()
result = detector.detect('path/to/your/video.mp4')
print(result)
```

---

## Step-by-Step Testing

### Step 1: Verify Installation

First, make sure everything is installed:

```cmd
python -c "import open_clip; print('✓ open-clip-torch installed')"
python -c "from ai_model.enhanced_detector import EnhancedDetector; print('✓ Detector can be imported')"
```

### Step 2: Initialize Detector

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()
```

**Expected:** 
- CLIP model loads (first time downloads ~600MB)
- Detector initializes on CPU or CUDA
- May take 1-2 minutes on first run

### Step 3: Test Detection

```python
# Test with sample video
result = detector.detect('sample_video.mp4', num_frames=16)

# View results
print("Detection Results:")
print(f"  Method: {result['method']}")
print(f"  Is Deepfake: {result['is_deepfake']}")
print(f"  Ensemble Probability: {result['ensemble_fake_probability']:.4f}")
print(f"  CLIP Probability: {result['clip_fake_probability']:.4f}")
print(f"  LAA-Net Probability: {result['laa_fake_probability']:.4f}")
print(f"  Frames Analyzed: {result['num_frames_analyzed']}")
```

---

## Understanding the Results

### Result Dictionary Structure

```python
{
    'ensemble_fake_probability': 0.75,  # Combined score (0=real, 1=fake)
    'clip_fake_probability': 0.70,      # CLIP-only score
    'laa_fake_probability': 0.50,      # LAA-Net score (0.5 = neutral if unavailable)
    'is_deepfake': True,                # Boolean prediction (>0.5 = fake)
    'method': 'clip_only',              # or 'ensemble_clip_laa' if LAA-Net available
    'num_frames_analyzed': 16,          # Number of frames processed
    'laa_available': False              # Whether LAA-Net is loaded
}
```

### Interpreting Scores

- **ensemble_fake_probability < 0.5**: Likely REAL
- **ensemble_fake_probability > 0.5**: Likely FAKE
- **ensemble_fake_probability ≈ 0.5**: Uncertain

Higher values (closer to 1.0) = higher confidence it's fake
Lower values (closer to 0.0) = higher confidence it's real

---

## Test Videos Available

The test script automatically looks for:
- `sample_video.mp4`
- `test_video_1.mp4`
- `test_video_2.mp4`
- `test_video_3.mp4`

If these exist in your project directory, they'll be tested automatically.

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'open_clip'"

**Solution:** Install open-clip-torch:
```cmd
python -m pip install open-clip-torch>=2.20.0
```

### Issue: "CLIP model download fails"

**Solution:** 
- Check internet connection
- First run downloads ~600MB
- May take several minutes

### Issue: "No test videos found"

**Solution:**
- Use your own video: `detector.detect('path/to/video.mp4')`
- Or download test videos to project directory

### Issue: "CUDA out of memory" or slow on CPU

**Solution:**
- Reduce frames: `detector.detect('video.mp4', num_frames=8)`
- Use CPU (automatic if CUDA unavailable)
- CLIP works on CPU, just slower

### Issue: "Video file not found"

**Solution:**
- Use full path: `detector.detect(r'C:\full\path\to\video.mp4')`
- Or use relative path from project directory

---

## Advanced Testing

### Test Multiple Videos

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()

videos = ['video1.mp4', 'video2.mp4', 'video3.mp4']

for video in videos:
    try:
        result = detector.detect(video)
        print(f"{video}: {'FAKE' if result['is_deepfake'] else 'REAL'} ({result['ensemble_fake_probability']:.3f})")
    except Exception as e:
        print(f"{video}: Error - {e}")
```

### Test with Different Frame Counts

```python
detector = EnhancedDetector()

# More frames = more accurate but slower
result_8 = detector.detect('video.mp4', num_frames=8)
result_16 = detector.detect('video.mp4', num_frames=16)
result_32 = detector.detect('video.mp4', num_frames=32)

print(f"8 frames: {result_8['ensemble_fake_probability']:.3f}")
print(f"16 frames: {result_16['ensemble_fake_probability']:.3f}")
print(f"32 frames: {result_32['ensemble_fake_probability']:.3f}")
```

---

## Quick Test Commands

```cmd
REM Test 1: Import check
python -c "from ai_model.enhanced_detector import EnhancedDetector; print('Import OK')"

REM Test 2: Initialization check
python -c "from ai_model.enhanced_detector import EnhancedDetector; d = EnhancedDetector(); print(f'Detector ready on {d.device}')"

REM Test 3: Full test
python test_ensemble_detector.py
```

---

## Expected First Run Behavior

1. **First import:** May take 10-30 seconds (loading CLIP)
2. **First detection:** Downloads CLIP weights (~600MB) - may take 5-10 minutes
3. **Subsequent runs:** Fast (weights cached)

---

## Success Indicators

✅ **Detector initializes:** "CLIP model loaded successfully"
✅ **Detection runs:** No errors, returns results dictionary
✅ **Results make sense:** Scores between 0.0 and 1.0
✅ **Method shows:** "clip_only" (or "ensemble_clip_laa" if LAA-Net set up)

---

## Next Steps After Testing

1. **If tests pass:** Ready to integrate with your API
2. **If LAA-Net needed:** Run `setup_laa_net_complete.bat`
3. **For production:** Integrate into `api.py` endpoints

---

**Ready to test?** Run: `python test_ensemble_detector.py`

