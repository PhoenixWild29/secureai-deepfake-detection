# Step 2: Activate LAA-Net - Complete Setup Guide

## Goal: Achieve World-Class Deepfake Detection (>95% Accuracy)

LAA-Net (Look-At-Artifact Network) will add 5-10% accuracy boost to your ensemble, targeting **95%+ accuracy** - making it one of the best deepfake detection models in the world.

---

## Step 2A: Set Up LAA-Net Repository

### On Your Server:

```bash
# 1. Navigate to project directory
cd ~/secureai-deepfake-detection

# 2. Pull latest code
git pull origin master

# 3. Create external directory if needed
mkdir -p external

# 4. Clone LAA-Net repository
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd laa_net

# 5. Check repository structure
ls -la
```

---

## Step 2B: Install LAA-Net Dependencies

### Inside Docker Container:

```bash
# Copy LAA-Net to container (if not already there)
docker cp external/laa_net secureai-backend:/app/external/

# Install LAA-Net dependencies inside container
docker exec secureai-backend bash -c "cd /app/external/laa_net && pip install -r requirements.txt"
```

### Check for Requirements File:

```bash
# Check if requirements.txt exists
docker exec secureai-backend ls -la /app/external/laa_net/

# If requirements.txt exists, install:
docker exec secureai-backend bash -c "cd /app/external/laa_net && pip install -r requirements.txt"
```

---

## Step 2C: Download Pretrained Weights

LAA-Net requires pretrained model weights. These are typically available from:

1. **Official Repository**: Check the LAA-Net GitHub repository for download links
2. **Google Drive**: Often linked in the repository README
3. **Releases**: Check the "Releases" section of the GitHub repo

### Typical Locations:
- Google Drive link (provided in repository README)
- Model weights file (usually `.pth` or `.pkl` format)
- Place in: `external/laa_net/weights/` or `ai_model/`

### After Downloading Weights:

```bash
# Copy weights to container
docker cp <weights_file_path> secureai-backend:/app/external/laa_net/weights/
# OR
docker cp <weights_file_path> secureai-backend:/app/ai_model/
```

---

## Step 2D: Update Code to Load LAA-Net

Once you have:
1. ✅ LAA-Net repository cloned
2. ✅ Dependencies installed
3. ✅ Pretrained weights downloaded

**Share with me:**
- Where the weights file is located
- Any errors from setup
- The repository structure (what files/folders are in `external/laa_net/`)

Then I'll update the code to:
- Import LAA-Net model
- Load pretrained weights
- Enable LAA-Net in the ensemble

---

## Expected Improvements

After activation:
- **Current**: 88-93% accuracy (CLIP + ResNet)
- **With LAA-Net**: **93-98% accuracy** ⭐
- **Target**: >95% accuracy (world-class)

---

## Troubleshooting

### If Repository Clone Fails:
```bash
# Try manual clone
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
```

### If Dependencies Fail:
Check the LAA-Net repository README for specific installation instructions

### If Weights Not Found:
- Check the repository README for download links
- Look in "Releases" section
- Check for Google Drive links

---

## Next Steps After Setup

Once LAA-Net is set up, I'll:
1. Update `ai_model/enhanced_detector.py` to load LAA-Net
2. Enable LAA-Net in the ensemble detector
3. Test the full ensemble (CLIP + ResNet + LAA-Net)
4. Verify improved accuracy

---

## Current Progress

- ✅ Step 1: ResNet50 verified (100% test accuracy)
- ⏳ Step 2A: Set up repository
- ⏳ Step 2B: Install dependencies  
- ⏳ Step 2C: Download weights
- ⏳ Step 2D: Update code

**Ready to start!** Run the commands in Step 2A and let me know the results.
