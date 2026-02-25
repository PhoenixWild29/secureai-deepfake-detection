# Finding LAA-Net Pretrained Weights

## Quick Commands to Run on Your Server

Run these commands to clone the repository and find the pretrained weights download links:

```bash
# 1. Navigate to project directory
cd ~/secureai-deepfake-detection
git pull origin master

# 2. Create external directory
mkdir -p external

# 3. Clone LAA-Net repository
cd external
git clone https://github.com/10Ring/LAA-Net laa_net
cd laa_net

# 4. Check README for weights information
cat README.md | grep -i -A 5 -B 5 "pretrained\|weight\|download\|google.*drive"

# 5. List all files to see structure
ls -la

# 6. Check for pretrained/weights directories
ls -la pretrained/ 2>/dev/null || echo "No pretrained directory"
ls -la weights/ 2>/dev/null || echo "No weights directory"
ls -la checkpoints/ 2>/dev/null || echo "No checkpoints directory"

# 7. Save README to a file for review
cat README.md > ~/laa_net_readme.txt
echo "README saved to ~/laa_net_readme.txt"
```

## Alternatively: Use Python Script

Copy the script to your server and run it:

```bash
# On your server
cd ~/secureai-deepfake-detection
git pull origin master

# Copy script to container or run directly
docker cp find_laa_net_weights.py secureai-backend:/app/
docker exec secureai-backend python3 /app/find_laa_net_weights.py

# OR run locally if Python is available
python3 find_laa_net_weights.py
```

## What to Look For

The LAA-Net repository README typically contains:

1. **"LAA-Net Pre-trained Models" section** - Lists download links
2. **Google Drive links** - Usually for downloading pretrained weights
3. **Weights file names** - Like `laa_net_best.pth`, `efn_*.pth`, etc.

Common patterns in README:
- `https://drive.google.com/...` (Google Drive links)
- `pretrained/` directory references
- Model checkpoint filenames (`.pth`, `.pkl`, `.ckpt`)

## After Finding Weights

Once you find the download link(s), download the weights:

```bash
# Download from Google Drive (example - replace with actual link)
# Option 1: Use gdown (if installed)
pip install gdown
gdown <GOOGLE_DRIVE_ID> -O external/laa_net/weights/laa_net_best.pth

# Option 2: Use wget/curl (if direct link available)
wget <DOWNLOAD_LINK> -O external/laa_net/weights/laa_net_best.pth

# Option 3: Manual download
# Download from browser, then upload to server via scp/sftp
```

## Share Results

After running the commands, share:
1. Any Google Drive links found
2. Weight file names mentioned
3. Directory structure (`ls -la` output)
4. Relevant README sections

Then I'll help you:
- Download the correct weights
- Configure the code to load them
- Integrate LAA-Net into your ensemble
