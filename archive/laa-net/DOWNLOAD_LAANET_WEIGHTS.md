# Download LAA-Net Pretrained Weights

## ✅ Found: Dropbox Link for Pretrained Weights

The LAA-Net README contains a Dropbox link for pretrained weights:

**Link**: `https://www.dropbox.com/scl/fo/dzmldaytujdeuJe ky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=0`

**Note**: The weights are for both **BI** (Basic Injection) and **SBI** (Selective Basic Injection) models.

---

## Step 1: Download Weights

### Option A: Download via Browser (Easier)

1. Open the Dropbox link in your browser:
   ```
   https://www.dropbox.com/scl/fo/dzmldaytujdeuJe ky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=0
   ```

2. Download all weight files from the Dropbox folder

3. Upload to your server:
   ```bash
   # From your local machine, upload to server
   scp <downloaded_files> root@<your-server-ip>:~/secureai-deepfake-detection/external/laa_net/weights/
   ```

### Option B: Download via Command Line (On Server)

```bash
# Install wget if not available
apt-get update && apt-get install -y wget

# Navigate to weights directory
cd ~/secureai-deepfake-detection/external/laa_net
mkdir -p weights
cd weights

# Download from Dropbox (replace <FILE_ID> with actual file IDs from the folder)
# Note: You may need to extract individual file links from the Dropbox folder
# Or use the Dropbox API/direct download links

# Alternative: Use curl with the Dropbox link
curl -L "https://www.dropbox.com/scl/fo/dzmldaytujdeuJe ky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=1" -o laa_net_weights.zip

# Extract if it's a zip file
unzip laa_net_weights.zip
```

### Option C: Use Python Script (Recommended)

```bash
# On your server
cd ~/secureai-deepfake-detection
git pull origin master

# Copy download script to container
docker cp download_laa_weights.py secureai-backend:/app/
docker exec secureai-backend python3 /app/download_laa_weights.py
```

---

## Step 2: Verify Weights Downloaded

```bash
# Check weights directory
ls -lah ~/secureai-deepfake-detection/external/laa_net/weights/

# Expected files (may vary):
# - efn4_fpn_hm_adv_best.pth (or similar)
# - efn4_fpn_hm_adv_sbi_best.pth (or similar)
# - Other checkpoint files
```

---

## Step 3: Copy Weights to Docker Container

```bash
# Copy weights to container
docker cp ~/secureai-deepfake-detection/external/laa_net/weights secureai-backend:/app/external/laa_net/

# Verify in container
docker exec secureai-backend ls -la /app/external/laa_net/weights/
```

---

## Step 4: Share Results

After downloading, share:
1. ✅ List of weight files downloaded
2. ✅ File sizes (to verify complete download)
3. ✅ Any errors encountered

Then I'll:
1. Update the code to load LAA-Net
2. Configure the correct weight file path
3. Integrate LAA-Net into your ensemble
4. Test for >95% accuracy

---

## Expected Weight Files

Based on LAA-Net documentation, you should see files like:
- `efn4_fpn_hm_adv_best.pth` (BI model)
- `efn4_fpn_hm_adv_sbi_best.pth` (SBI model)
- Or similar checkpoint files

**File sizes**: Typically 50-200 MB each
