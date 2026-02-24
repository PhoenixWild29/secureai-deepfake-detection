# Morpheus Security Monitoring Setup Guide

## Current Status

Your application shows: `⚠️ Morpheus not available, using rule-based monitoring`

This is **normal** - the app works with enhanced rule-based monitoring as a fallback.

## What is NVIDIA Morpheus?

NVIDIA Morpheus is a GPU-accelerated cybersecurity AI framework that provides:
- Real-time anomaly detection
- AI-powered threat analysis
- GPU-accelerated inference
- Advanced pattern recognition

## Option 1: Enhanced Rule-Based Monitoring (Current - Recommended)

The application now uses **Enhanced Rule-Based Monitoring** which provides:
- ✅ Statistical anomaly detection
- ✅ Pattern recognition
- ✅ Multi-feature correlation
- ✅ Temporal analysis
- ✅ Adaptive thresholds
- ✅ Works without GPU infrastructure

**This is already active and working!** The warning message is informational.

## Option 2: Install NVIDIA Morpheus (Advanced)

NVIDIA Morpheus requires:
- **NVIDIA GPU** with CUDA support
- **CUDA Toolkit** (11.0+)
- **Docker** or **Conda** environment
- **Triton Inference Server** (optional but recommended)

### Installation Steps

#### Method 1: Docker (Recommended)

```bash
# Pull Morpheus Docker image
docker pull nvcr.io/nvidia/morpheus/morpheus:latest

# Run Morpheus container
docker run --gpus all -it --rm \
  -v $(pwd):/workspace \
  nvcr.io/nvidia/morpheus/morpheus:latest
```

#### Method 2: Conda

```bash
# Create conda environment
conda create -n morpheus python=3.10
conda activate morpheus

# Install Morpheus
conda install -c conda-forge -c rapidsai -c nvidia morpheus
```

#### Method 3: From Source

```bash
# Clone Morpheus repository
git clone https://github.com/NVIDIA/Morpheus.git
cd Morpheus

# Install dependencies
pip install -r requirements.txt

# Build and install
python setup.py install
```

### Configure Environment

After installation, set environment variables:

```bash
# In your .env file or environment
MORPHEUS_AVAILABLE=true
CUDA_VISIBLE_DEVICES=0  # Specify GPU device
```

### Verify Installation

```python
# Test import
python -c "import morpheus; print('Morpheus installed successfully')"
```

## Option 3: Enable Enhanced Monitoring (Already Active)

The enhanced monitoring is **already enabled** by default. It provides Morpheus-like functionality without requiring GPU infrastructure.

To verify it's working:

```bash
# Check logs
docker logs secureai-backend | grep -i "monitoring\|morpheus"
```

You should see:
- `✅ Enhanced rule-based security monitoring initialized (Morpheus-like)`

## Current Implementation

The application uses:

1. **Enhanced Anomaly Detection:**
   - Statistical analysis with adaptive thresholds
   - Pattern recognition
   - Multi-feature correlation

2. **Threat Pattern Matching:**
   - Suspicious pattern detection
   - Behavioral analysis
   - Confidence scoring

3. **Real-time Monitoring:**
   - Continuous threat scanning
   - Queue-based threat processing
   - Alert generation

## Recommendation

**For most use cases, the Enhanced Rule-Based Monitoring is sufficient** and provides:
- ✅ No GPU requirements
- ✅ Lower infrastructure costs
- ✅ Good performance
- ✅ Morpheus-like capabilities

**Install actual Morpheus only if:**
- You have NVIDIA GPUs available
- You need GPU-accelerated inference
- You're processing very high volumes
- You have specialized cybersecurity requirements

## Troubleshooting

### "Morpheus not available" Warning

This is **normal** and expected if:
- Morpheus is not installed
- No GPU is available
- Running in CPU-only environment

The app will automatically use enhanced monitoring.

### Enable Enhanced Monitoring Explicitly

Add to `.env`:
```env
ENABLE_ENHANCED_MONITORING=true
```

### Check Monitoring Status

```bash
# Check if monitoring is active
docker exec secureai-backend python -c "
from ai_model.morpheus_security import get_security_status
import json
print(json.dumps(get_security_status(), indent=2))
"
```

## Summary

- ✅ **Enhanced monitoring is active** - provides Morpheus-like functionality
- ✅ **No action needed** - the app works great with enhanced monitoring
- ⚠️ **Warning is informational** - doesn't affect functionality
- 🚀 **Install Morpheus only if** you have GPU infrastructure and need GPU acceleration

Your security monitoring is working! The warning just indicates that the full NVIDIA Morpheus framework isn't installed, but the enhanced fallback provides similar capabilities.

