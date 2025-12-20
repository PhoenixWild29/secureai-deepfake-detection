# Quick Start: Ensemble Detector

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Test CLIP-Only Detection (Works Immediately)
```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()
result = detector.detect('your_video.mp4')

print(f"Is Deepfake: {result['is_deepfake']}")
print(f"Confidence: {result['ensemble_fake_probability']:.4f}")
```

### Step 3: (Optional) Add LAA-Net for Full Ensemble
```bash
python setup_laa_net.py
# Then download weights and update code (see ENSEMBLE_DETECTOR_SETUP.md)
```

## 📊 Result Format

```python
{
    'ensemble_fake_probability': 0.75,  # Combined score (0=real, 1=fake)
    'clip_fake_probability': 0.70,     # CLIP-only score
    'laa_fake_probability': 0.80,      # LAA-Net score (0.5 if unavailable)
    'is_deepfake': True,               # Boolean prediction
    'method': 'ensemble_clip_laa',     # or 'clip_only'
    'num_frames_analyzed': 16
}
```

## 🔗 Integration with API

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()

@app.route('/api/detect', methods=['POST'])
def detect():
    video = request.files['video']
    video_path = save_upload(video)
    result = detector.detect(video_path)
    return jsonify(result)
```

## 📚 Full Documentation

- **Setup Guide**: `ENSEMBLE_DETECTOR_SETUP.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **LAA-Net Setup**: `external/README.md`

## ⚡ Key Features

- ✅ **CLIP Zero-Shot**: Works immediately, no training needed
- ✅ **LAA-Net Ready**: Structure prepared for integration
- ✅ **Face Detection**: Automatic face cropping included
- ✅ **Backward Compatible**: Works with existing code

## 🎯 What's Next?

1. Test with your videos
2. Set up LAA-Net for full ensemble (optional)
3. Integrate with your API
4. Fine-tune for your use case

---

**Ready to use!** The detector works with CLIP-only mode right now.

