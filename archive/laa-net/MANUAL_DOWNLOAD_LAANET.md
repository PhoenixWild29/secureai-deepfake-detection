# Manual Download: LAA-Net Pretrained Weights

## ⚠️ Issue: Dropbox Shared Folder Link

The Dropbox link in the README is a **shared folder link**, not a direct download link. This requires manual download from a browser.

---

## Step-by-Step Manual Download

### Step 1: Open Dropbox Link

Open this link in your **web browser** (not command line):
```
https://www.dropbox.com/scl/fo/dzmldaytujdeuJeky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=0
```

### Step 2: Download Weight Files

In the Dropbox folder, you should see files like:
- `efn4_fpn_hm_adv_best.pth` (BI model - ~50-200 MB)
- `efn4_fpn_hm_adv_sbi_best.pth` (SBI model - ~50-200 MB)
- Or similar checkpoint files (`.pth` format)

**Download ALL `.pth` files** from the folder.

### Step 3: Upload to Server

#### Option A: Using SCP (from your local machine)

```bash
# From your local machine (Windows/Mac/Linux)
scp <downloaded_files> root@<your-server-ip>:/root/secureai-deepfake-detection/external/laa_net/weights/
```

Example:
```bash
scp efn4_fpn_hm_adv_best.pth root@your-server-ip:/root/secureai-deepfake-detection/external/laa_net/weights/
```

#### Option B: Using Docker Copy (if files are on server)

```bash
# On your server, if you uploaded files to a temporary location
docker cp /tmp/efn4_fpn_hm_adv_best.pth secureai-backend:/app/external/laa_net/weights/
```

#### Option C: Using FileZilla/WinSCP (GUI)

1. Connect to your server via SFTP
2. Navigate to: `/root/secureai-deepfake-detection/external/laa_net/weights/`
3. Upload the `.pth` files

### Step 4: Verify Files

```bash
# Check files in container
docker exec secureai-backend ls -lah /app/external/laa_net/weights/

# Expected output:
# -rw-r--r-- 1 root root 150M ... efn4_fpn_hm_adv_best.pth
# -rw-r--r-- 1 root root 150M ... efn4_fpn_hm_adv_sbi_best.pth
```

**File sizes should be 50-200 MB each** (not 0.21 MB like the HTML file).

---

## After Download

Once you have the `.pth` files in the weights directory:

1. **Share the file names** you downloaded
2. **Share the file sizes** (to verify complete download)
3. I'll then:
   - Update the code to load LAA-Net
   - Configure the correct weight file path
   - Integrate LAA-Net into your ensemble
   - Test for >95% accuracy

---

## Quick Commands Summary

```bash
# 1. Create weights directory (if needed)
docker exec secureai-backend mkdir -p /app/external/laa_net/weights

# 2. Copy files to container (adjust path)
docker cp <local_weight_file.pth> secureai-backend:/app/external/laa_net/weights/

# 3. Verify files
docker exec secureai-backend ls -lah /app/external/laa_net/weights/
```

---

## Expected Files

Based on LAA-Net documentation, you should download:
- **BI model**: `efn4_fpn_hm_adv_best.pth` or similar
- **SBI model**: `efn4_fpn_hm_adv_sbi_best.pth` or similar

**Note**: You only need **one** of these models (BI is recommended for general use).
