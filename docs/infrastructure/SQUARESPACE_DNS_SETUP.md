# Squarespace DNS Setup for SecureAI Guardian

Step-by-step guide to add a subdomain DNS record in Squarespace.

## Current Status
- ✅ You're logged into Squarespace
- ✅ You're on the DNS Settings page
- ✅ You can see existing DNS records

## Step-by-Step: Add A Record for Subdomain

### ⚠️ Important: Don't Use "ADD PRESET"

The "ADD PRESET" button is for email service configurations (Google Workspace, Zoho Mail, etc.). We need to add a **custom A record** instead.

### Step 1: Look for "Add Record" or Custom Record Option

On the DNS Settings page, look for one of these options:

1. **"Add Record"** button (separate from "ADD PRESET")
2. **"Custom Record"** link or button
3. **"+"** icon (plus sign) next to existing records
4. A section labeled **"Custom Records"** or **"Additional Records"**

**Where to look:**
- Below the existing DNS record sections
- In the same area as "ADD PRESET" but a different button
- Sometimes in a separate "Custom Records" section

### Step 2: Select "A Record" Type

1. Click **"Add Record"** or **"Custom Record"**
2. You'll see a form or dropdown to select record type
3. **Select "A Record"** (or "A") from the type dropdown

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

### Can't Find "Add Record" Button
- **Scroll down** on the DNS Settings page - it might be below the preset sections
- Look for a **"Custom Records"** section - it might be collapsed or at the bottom
- Check if there's a **"+"** icon or **"Add"** link next to existing records
- Try clicking on the existing record sections to see if there's an "Add" option

### Only See "ADD PRESET" (Email Presets)
- **Don't use "ADD PRESET"** - that's only for email services
- Look for a separate **"Add Record"** button or **"Custom Record"** option
- The custom record option might be:
  - Below the preset sections
  - In a separate "Custom Records" area
  - As a small "+" or "Add" link

### Alternative: Check Squarespace Help
If you can't find the custom record option:
1. Look for a **"?"** help icon on the DNS Settings page
2. Search Squarespace help for "add custom DNS record"
3. Or try this direct link format (if Squarespace supports it):
   - Look for any "Manage" or "Edit" options near existing records

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

