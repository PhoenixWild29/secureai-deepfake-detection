# Ensemble Detector Setup Guide

## Priority 1 MVP Implementation

This guide covers the setup and usage of the new **Enhanced Ensemble Detector** that combines:
1. **CLIP Zero-Shot Detection** - Generalizable, works out-of-the-box
2. **LAA-Net** - Quality-agnostic artifact attention model (CVPR 2024)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key new dependencies:
- `open-clip-torch` - For CLIP zero-shot detection
- `albumentations`, `imgaug`, `scikit-image` - For LAA-Net
- `mtcnn` - For face detection (fallback if LAA-Net utils unavailable)

### 2. Test CLIP-Only Detection (Immediate)

The detector works immediately with CLIP-only mode:

```python
from ai_model.enhanced_detector import EnhancedDetector

# Initialize detector (CLIP will load automatically)
detector = EnhancedDetector()

# Detect deepfake in video
result = detector.detect('path/to/video.mp4', num_frames=16)

print(f"Is Deepfake: {result['is_deepfake']}")
print(f"Confidence: {result['ensemble_fake_probability']:.4f}")
print(f"CLIP Score: {result['clip_fake_probability']:.4f}")
```

### 3. Set Up LAA-Net (Optional but Recommended)

For full ensemble detection with LAA-Net:

#### Option A: Using Git Submodule (Recommended)

```bash
# Run the setup script
python setup_laa_net.py

# Or manually:
git submodule add https://github.com/10Ring/LAA-Net external/laa_net
git submodule update --init --recursive
```

#### Option B: Manual Clone

```bash
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd laa_net
pip install -r requirements.txt
```

#### Download Pre-trained Weights

1. Check the LAA-Net repository for download links (usually Google Drive)
2. Download the pre-trained weights
3. Place them in a known location (e.g., `external/laa_net/weights/`)

#### Update the Detector Code

After setting up LAA-Net, update `ai_model/enhanced_detector.py`:

1. Uncomment the LAA-Net import section at the top
2. Adjust imports based on actual LAA-Net repository structure
3. Update the `__init__` method to load the LAA-Net model
4. Implement the `laa_detect_frames` method with actual inference code

Example (adjust based on actual LAA-Net structure):
```python
# At the top of enhanced_detector.py
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'external', 'laa_net'))
from models import LAANet  # Adjust based on actual structure

# In __init__:
if laa_weights_path and os.path.exists(laa_weights_path):
    self.laa_model = LAANet(...)  # Initialize with actual parameters
    self.laa_model.load_state_dict(torch.load(laa_weights_path, map_location=self.device))
    self.laa_model.to(self.device)
    self.laa_model.eval()
    self.laa_available = True
```

## Usage Examples

### Basic Detection

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector(
    laa_weights_path='path/to/laa_weights.pth'  # Optional
)

result = detector.detect('video.mp4', num_frames=16)

# Result structure:
# {
#     'ensemble_fake_probability': 0.75,  # Combined score
#     'clip_fake_probability': 0.70,       # CLIP-only score
#     'laa_fake_probability': 0.80,        # LAA-Net score (or 0.5 if unavailable)
#     'is_deepfake': True,
#     'method': 'ensemble_clip_laa',       # or 'clip_only'
#     'num_frames_analyzed': 16,
#     'laa_available': True
# }
```

### Backward Compatibility

The old function interface still works:

```python
from ai_model.enhanced_detector import detect_fake_enhanced

result = detect_fake_enhanced('video.mp4')
# Returns format compatible with existing code
```

### Integration with API

The detector can be used in `api.py`:

```python
from ai_model.enhanced_detector import EnhancedDetector

detector = EnhancedDetector()

@app.route('/api/detect', methods=['POST'])
def detect():
    video_path = ...  # Get from upload
    result = detector.detect(video_path)
    return jsonify(result)
```

## Architecture

### CLIP Zero-Shot Detection
- **Model**: ViT-B-32 with LAION-2B pre-training
- **Prompts**: Optimized for real vs. fake detection
- **Advantages**: 
  - Works immediately, no training needed
  - Generalizes to unseen deepfake types
  - Excellent for diffusion-based deepfakes

### LAA-Net Detection
- **Model**: Localized Artifact Attention Network (CVPR 2024)
- **Preprocessing**: Face detection and cropping required
- **Advantages**:
  - Quality-agnostic (works on compressed/low-quality videos)
  - Focuses on subtle manipulation artifacts
  - Strong performance on benchmark datasets

### Ensemble Fusion
- **Current**: Simple average of CLIP and LAA-Net scores
- **Future**: Can add adaptive weighting based on video characteristics

## Face Detection

The detector includes a `FaceDetector` class that:
- Uses MTCNN (if available) for accurate face detection
- Falls back to OpenCV Haar cascades if MTCNN unavailable
- Automatically crops and resizes faces for LAA-Net input

## Testing

Test the implementation:

```bash
# Run the detector test
python ai_model/enhanced_detector.py

# Or use in your code
python -c "from ai_model.enhanced_detector import EnhancedDetector; d = EnhancedDetector(); print(d.detect('test_video.mp4'))"
```

## Troubleshooting

### CLIP Model Loading Issues
- Ensure `open-clip-torch` is installed: `pip install open-clip-torch`
- Check internet connection (first run downloads model weights)
- Verify CUDA availability if using GPU

### LAA-Net Not Available
- The detector works in CLIP-only mode if LAA-Net is not set up
- Check `result['laa_available']` to see if LAA-Net is loaded
- Follow setup steps above to integrate LAA-Net

### Face Detection Issues
- Install MTCNN: `pip install mtcnn`
- OpenCV Haar cascades are included but less accurate
- Ensure faces are visible in video frames

## Next Steps

1. **Test with sample videos** - Try real and deepfake videos
2. **Integrate LAA-Net** - Follow setup steps for full ensemble
3. **Add to API** - Integrate with your web interface
4. **Fine-tune prompts** - Adjust CLIP prompts for your use case
5. **Add adaptive weighting** - Improve ensemble fusion logic

## Performance Notes

- **CLIP-only**: Fast, works immediately, good generalization
- **Full ensemble**: More accurate, requires LAA-Net setup
- **Frame sampling**: Default 16 frames balances speed and accuracy
- **GPU recommended**: Significantly faster on GPU

## References

- CLIP: [OpenAI CLIP](https://github.com/openai/CLIP)
- Open-CLIP: [Open CLIP](https://github.com/mlfoundations/open_clip)
- LAA-Net: [LAA-Net Repository](https://github.com/10Ring/LAA-Net)

