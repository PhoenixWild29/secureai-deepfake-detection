# External Dependencies

This directory contains external repositories and dependencies for the deepfake detection system.

**LAA-Net is optional and not used in the live pipeline by default.** The detector runs with CLIP (and ResNet50 in the full ensemble) until you set up the LAA-Net repo and weights; then it is used automatically (see below).

**Quick setup:** Clone [10Ring/LAA-Net](https://github.com/10Ring/LAA-Net) into `external/laa_net`, download pretrained weights into `external/laa_net/weights/`, and install their `requirements.txt`. See **docs/guides/LAA_NET_SETUP.md** for step-by-step instructions.

## LAA-Net Integration

### Setting up LAA-Net Submodule

To integrate the official LAA-Net repository:

```bash
# From the project root directory
cd SecureAI-DeepFake-Detection

# Add LAA-Net as a git submodule
git submodule add https://github.com/10Ring/LAA-Net external/laa_net

# Initialize and update submodules
git submodule update --init --recursive
```

### Alternative: Manual Setup

If you prefer not to use git submodules:

```bash
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd laa_net
```

### Installing LAA-Net Dependencies

Follow the LAA-Net repository's README for installation instructions. Typically:

1. Install their requirements:
   ```bash
   cd external/laa_net
   pip install -r requirements.txt
   ```

2. Download pre-trained weights:
   - Check the LAA-Net repository for download links (usually Google Drive)
   - Place weights in `external/laa_net/weights/` or a location you specify
   - Update `laa_weights_path` in `EnhancedDetector` initialization

### Updating the Enhanced Detector

After setting up LAA-Net, update `ai_model/enhanced_detector.py`:

1. Uncomment and adjust the LAA-Net imports at the top of the file
2. Update the model loading code in `__init__` method
3. Implement the `laa_detect_frames` method with actual LAA-Net inference
4. Add the proper preprocessing transform for LAA-Net input

Example import structure (adjust based on actual LAA-Net repo structure):
```python
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'external', 'laa_net'))
from models import LAANet  # Adjust based on actual structure
from utils.face_utils import preprocess_face  # If available
```

### Notes

- LAA-Net requires face-cropped inputs, which is handled by the `FaceDetector` class
- The detector will work with CLIP-only mode until LAA-Net is fully integrated
- Check LAA-Net's repository for the latest model architecture and inference code

