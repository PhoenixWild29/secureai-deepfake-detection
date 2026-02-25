# Quick Start: Run Step 1 and Step 2

## Step 1: Verify ResNet Training (5 minutes)

Run these commands on your server:

```bash
cd ~/secureai-deepfake-detection
git pull origin master
docker cp verify_resnet50_benchmark.py secureai-backend:/app/
docker exec secureai-backend python3 /app/verify_resnet50_benchmark.py
```

**What to look for:**
- ✅ "Trained for deepfake detection" = Model is ready
- ⚠️ "ImageNet pretrained only" = Needs training

**Share the output** and I'll help interpret the results.

---

## Step 2: Activate LAA-Net (Requires Repository Info)

### First, I Need Information:

**Do you have:**
1. LAA-Net repository URL? (GitHub link)
2. Pretrained weights file? (or know where to download it?)

### If You Have the Repository:

```bash
# On your server
cd ~/secureai-deepfake-detection

# Add as submodule (replace URL with actual LAA-Net repo)
git submodule add <LAA-NET-REPO-URL> external/laa_net
git submodule update --init --recursive

# Then share:
# - Repository URL
# - Weights file location
# - Model class name (if known)
```

### If You Don't Have LAA-Net Yet:

**Option 1**: Skip for now (system works without it)
- Current accuracy: 88-93% (CLIP + ResNet)
- Can add LAA-Net later when available

**Option 2**: Find LAA-Net repository
- Search for "LAA-Net deepfake detection" or "Look-At-Artifact Network"
- Common sources: GitHub, research paper repositories
- Share the repository URL and I'll help set it up

---

## Recommended Order

1. **Run Step 1 first** (quick verification, 5 minutes)
2. **Share Step 1 results** (I'll help interpret)
3. **Then proceed with Step 2** (if you have LAA-Net repository)

---

## Quick Commands Summary

```bash
# Step 1: Verify ResNet
cd ~/secureai-deepfake-detection
git pull origin master
docker cp verify_resnet50_benchmark.py secureai-backend:/app/
docker exec secureai-backend python3 /app/verify_resnet50_benchmark.py

# Step 2: Activate LAA-Net (after you have repository info)
# See STEP_2_ACTIVATE_LAANET.md for detailed instructions
```
