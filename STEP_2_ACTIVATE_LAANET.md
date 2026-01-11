# Step 2: Activate LAA-Net (5-10% Accuracy Boost)

## Overview

LAA-Net (Look-At-Artifact Network) is a quality-agnostic artifact attention model that can improve detection accuracy by 5-10%. Currently, it's not active in the system.

## Prerequisites

Before starting, you need:
1. LAA-Net repository URL (GitHub link)
2. Pretrained weights file (`.pth` or `.pkl` format)
3. Python dependencies (usually handled automatically)

## Step-by-Step Setup

### Option A: If LAA-Net is a Git Repository

```bash
# 1. Navigate to project directory
cd ~/secureai-deepfake-detection

# 2. Add LAA-Net as a git submodule
# Replace <LAA-NET-REPO-URL> with actual repository URL
git submodule add <LAA-NET-REPO-URL> external/laa_net

# 3. Initialize and update submodule
git submodule update --init --recursive

# 4. Download pretrained weights (if not included in repo)
# Place weights file in: external/laa_net/weights/ or ai_model/
# Example: external/laa_net/weights/laa_net_best.pth
```

### Option B: Manual Installation

```bash
# 1. Clone LAA-Net repository manually
cd ~/secureai-deepfake-detection
mkdir -p external
cd external
git clone <LAA-NET-REPO-URL> laa_net
cd laa_net

# 2. Install LAA-Net dependencies (if requirements.txt exists)
pip install -r requirements.txt

# 3. Download pretrained weights
# Follow LAA-Net repository instructions for downloading weights
```

## Update Code to Load LAA-Net

After setting up the repository and weights, we need to update the code:

### 1. Update `ai_model/enhanced_detector.py`

The code needs to be updated to:
- Import LAA-Net model class
- Load pretrained weights
- Set `LAA_NET_AVAILABLE = True`

**Current Status**: Code structure exists but is commented out (lines 380-401)

### 2. Provide LAA-Net Repository Information

To proceed, I need:
- **LAA-Net repository URL** (GitHub link)
- **Weights file location** (where to download/store weights)
- **Model class name** (e.g., `LAANet`, `LAA_Net`, etc.)

## Quick Check: Do You Have LAA-Net Repository?

If you already have LAA-Net set up or know the repository URL, provide it and I can:
1. Update the import paths
2. Configure weight loading
3. Enable LAA-Net in the system

## Alternative: Skip LAA-Net for Now

If you don't have LAA-Net repository access or want to proceed without it:
- ✅ System works fine with CLIP + ResNet (88-93% accuracy)
- ⚠️ Missing 5-10% potential accuracy boost
- Can be added later when repository/weights are available

## Verification After Setup

Once LAA-Net is activated, verify it's working:

```bash
# Check if LAA-Net is loaded
docker exec secureai-backend python3 -c "
from ai_model.enhanced_detector import EnhancedDetector
detector = EnhancedDetector()
print(f'LAA-Net available: {detector.laa_available}')
"
```

Expected output: `LAA-Net available: True`
