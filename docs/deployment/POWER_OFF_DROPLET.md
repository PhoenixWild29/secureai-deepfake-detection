# How to Power Off DigitalOcean Droplet for Resize

## Quick Steps

1. **Go to Your Droplet**
   - In DigitalOcean dashboard, click on your droplet: `first-project`
   - Or go to: Droplets → Click on your droplet name

2. **Power Off the Droplet**
   - In the left sidebar, click **"Power"**
   - Click **"Power Off"** button
   - Confirm if prompted
   - Wait for droplet to power off (status will show "Off")

3. **Now You Can Resize**
   - Go back to **"Resize"** in the left sidebar
   - Select "CPU and RAM only"
   - Choose 8 GB RAM plan
   - Click "Resize"

4. **After Resize**
   - Droplet will automatically power back on
   - Or you can manually power it on from "Power" menu

## Alternative: Power Off via SSH

If you prefer command line:

```bash
# SSH into your droplet
ssh root@64.225.57.145

# Power off gracefully
sudo shutdown -h now
```

Then resize from DigitalOcean dashboard.

## Important Notes

- ⚠️ **Your site will be down** while droplet is powered off
- ⚠️ **Resize takes 1-3 minutes** (droplet will auto power on)
- ✅ **All data is preserved** during resize
- ✅ **Same IP address** (usually)

## After Power Off

Once droplet shows status "Off":
1. Go to "Resize" in left sidebar
2. Select "CPU and RAM only" ✅
3. Choose 8 GB RAM plan
4. Click "Resize"
5. Wait 1-3 minutes
6. Droplet powers back on automatically

---

**Ready? Power off first, then resize!** 🚀
