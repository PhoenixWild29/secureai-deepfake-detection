# Squarespace DNS Setup for SecureAI Guardian

Step-by-step guide to add a subdomain DNS record in Squarespace.

## Current Status
- ✅ You're logged into Squarespace
- ✅ You're on the DNS Settings page
- ✅ You can see existing DNS records

## Step-by-Step: Add A Record for Subdomain

### Step 1: Click "ADD PRESET" Button

On the DNS Settings page, look for the **"ADD PRESET"** button (black button, top right of the DNS records section).

**OR** if you don't see "ADD PRESET", look for:
- **"Add Record"** button
- **"Custom Record"** option
- **"+"** icon

### Step 2: Select Record Type

1. Click **"ADD PRESET"** (or equivalent)
2. You'll see options like:
   - **A Record**
   - **CNAME Record**
   - **MX Record**
   - etc.

3. **Select "A Record"** (or "A")

### Step 3: Fill in the A Record Details

Fill in the following information:

- **HOST** (or **Name**): `guardian`
  - This creates `guardian.secureai.dev`
  
- **TYPE** (or **Record Type**): `A` (should already be selected)

- **DATA** (or **Value** or **Points to**): `64.225.57.145`
  - This is your server IP address

- **TTL** (Time to Live): `4 hrs` (or leave as default)
  - Squarespace typically uses "4 hrs" as default

- **PRIORITY**: Leave blank or `0` (not needed for A records)

### Step 4: Save the Record

1. Click **"Save"** or **"Add Record"** button
2. The new A record should appear in your DNS records list

### Step 5: Verify the Record

You should now see a new record in your DNS Settings:
- **HOST**: `guardian`
- **TYPE**: `A`
- **DATA**: `64.225.57.145`
- **TTL**: `4 hrs`

## Visual Guide

Your DNS Settings page should show:

```
Squarespace Domain Connect
[existing records...]

Google Workspace
[existing records...]

Custom Records (or similar section)
guardian | A | - | 4 hrs | 64.225.57.145
```

## Important Notes

1. **DNS Propagation**: Wait 5-60 minutes for DNS to propagate
2. **Don't Delete Existing Records**: Keep your Google Workspace and Squarespace records
3. **Only Add One Record**: Just add the `guardian` A record

## After Adding the Record

1. **Wait 5-60 minutes** for DNS to propagate
2. **Verify DNS is working:**
   ```powershell
   nslookup guardian.secureai.dev
   ```
   Should return: `64.225.57.145`

3. **Run HTTPS setup on your server:**
   ```bash
   sudo bash setup-https.sh
   ```
   When prompted, enter: `guardian.secureai.dev`

## Troubleshooting

### Can't Find "ADD PRESET" Button
- Look for "Add Record" or "+" icon
- Check if you need to scroll down
- Try clicking on "Custom Records" section if visible

### Record Not Saving
- Make sure HOST is just `guardian` (not `guardian.secureai.dev`)
- Verify IP address is correct: `64.225.57.145`
- Check for any error messages

### DNS Not Resolving After Adding
- Wait longer (can take up to 24 hours, usually 5-60 minutes)
- Verify the record is saved correctly in Squarespace
- Clear your DNS cache:
  - Windows: `ipconfig /flushdns`
  - Mac/Linux: `sudo dscacheutil -flushcache`

## Next Steps

Once DNS is verified:
1. ✅ Run HTTPS setup script on your server
2. ✅ Access your app at: `https://guardian.secureai.dev`
3. ✅ Add a link from your Squarespace website to the new subdomain

## Need Help?

If you're stuck:
1. Take a screenshot of what you see after clicking "ADD PRESET"
2. Check if there's an "Add Record" or "Custom Record" option
3. Look for any help/guide links in Squarespace

