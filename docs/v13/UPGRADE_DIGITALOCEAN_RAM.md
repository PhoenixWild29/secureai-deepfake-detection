# Upgrade DigitalOcean Droplet to 8 GB RAM

## Method 1: Resize Existing Droplet (Recommended)

This keeps your existing droplet and data.

### Steps:

1. **Log into DigitalOcean**
   - Go to https://cloud.digitalocean.com
   - Log in with your credentials

2. **Select Your Droplet**
   - Click on "Droplets" in the left sidebar
   - Find your droplet: `ubuntu-s-2vcpu-4gb-120gb-intel-nyc3-01`
   - Click on it to open details

3. **Resize the Droplet**
   - Click the **"Resize"** button (usually in the top right or under "Power" menu)
   - Select a plan with **8 GB RAM** (or more)
   - Recommended: **"Regular Intel with SSD"** → **"8 GB / 4 vCPUs"** ($48/month)
   - OR: **"Premium Intel with NVMe SSD"** → **"8 GB / 4 vCPUs"** ($60/month) - faster
   - Click **"Resize Droplet"**

4. **Confirm Resize**
   - DigitalOcean will warn you that the droplet will be powered off
   - Click **"Confirm"** or **"Resize"**
   - The droplet will:
     - Power off automatically
     - Resize (takes 1-2 minutes)
     - Power back on automatically

5. **Wait for Resize to Complete**
   - You'll see status: "Resizing..."
   - Usually takes 1-3 minutes
   - Droplet will automatically power back on

6. **Verify the Upgrade**
   ```bash
   # SSH into your droplet
   ssh root@your-droplet-ip
   
   # Check RAM
   free -h
   ```
   Should show: **~8 GB total RAM**

7. **Test V13 Loading**
   ```bash
   cd ~/secureai-deepfake-detection
   git pull origin master
   
   # Copy updated code
   docker cp ai_model/deepfake_detector_v13.py secureai-backend:/app/ai_model/
   
   # Test V13 loading
   docker cp test_v13_fixed.py secureai-backend:/app/
   docker exec secureai-backend python3 test_v13_fixed.py
   ```

## Method 2: Create New Droplet (If Resize Fails)

If resize doesn't work, create a new droplet and migrate:

1. **Create New Droplet**
   - Click "Create" → "Droplets"
   - Choose:
     - **Image**: Ubuntu 22.04 (same as current)
     - **Plan**: Regular Intel → **8 GB / 4 vCPUs**
     - **Region**: Same region (NYC3)
     - **Authentication**: SSH keys (same as current)
   - Click "Create Droplet"

2. **Migrate Your Data**
   ```bash
   # On your current droplet, backup everything
   cd ~
   tar -czf secureai-backup.tar.gz secureai-deepfake-detection/
   
   # Copy to new droplet
   scp secureai-backup.tar.gz root@new-droplet-ip:~/
   
   # On new droplet, restore
   cd ~
   tar -xzf secureai-backup.tar.gz
   ```

3. **Update DNS/IP**
   - Point your domain to the new droplet IP
   - Or update firewall rules if using IP whitelisting

## Cost Comparison

- **Current**: 4 GB / 2 vCPUs = ~$24/month
- **Upgrade to**: 8 GB / 4 vCPUs = ~$48/month
- **Difference**: +$24/month (~$0.80/day)

## What Happens During Resize

1. ✅ Droplet powers off (automatic)
2. ✅ RAM upgraded from 4 GB → 8 GB
3. ✅ vCPUs upgraded from 2 → 4 (bonus!)
4. ✅ All data preserved
5. ✅ Same IP address (usually)
6. ✅ Powers back on automatically

## After Upgrade - Expected Results

With 8 GB RAM:
- ✅ ViT-Large loads: ~2-3 GB
- ✅ **Available after ViT-Large: ~5-6 GB** (vs 0.1 GB before!)
- ✅ ConvNeXt-Large loads: ~1-2 GB
- ✅ **Available after ConvNeXt: ~3-4 GB**
- ✅ Swin-Large loads: ~1 GB
- ✅ **Final available: ~2-3 GB** ✅

**All 3 models will load successfully!** 🎉

## Troubleshooting

### If Resize Button is Grayed Out
- Make sure droplet is powered on
- Some droplets can't be resized (rare) - use Method 2

### If Resize Takes Too Long
- Normal: 1-3 minutes
- If > 10 minutes, check DigitalOcean status page
- Contact DigitalOcean support if stuck

### If Droplet Doesn't Power Back On
- Go to droplet → "Power" → "Power On"
- Check "Networking" → "IPv4" to verify IP didn't change

## Next Steps After Upgrade

1. ✅ Verify RAM: `free -h` (should show ~8 GB)
2. ✅ Test V13 loading (should work now!)
3. ✅ Verify all 3 models load successfully
4. ✅ Test video detection with full V13 ensemble

---

**Ready to upgrade? Follow Method 1 steps above!** 🚀
