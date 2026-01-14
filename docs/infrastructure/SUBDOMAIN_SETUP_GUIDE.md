# Subdomain Setup Guide for SecureAI Guardian

This guide will help you create a subdomain for your SecureAI DeepFake Detection application using your existing `secureai.dev` domain.

## Recommended Subdomain Names

Choose one of these subdomain names:
- **`guardian.secureai.dev`** - Recommended (matches "SecureAI Guardian")
- **`app.secureai.dev`** - Simple and clear
- **`deepfake.secureai.dev`** - Descriptive
- **`detect.secureai.dev`** - Action-oriented
- **`api.secureai.dev`** - If you want to separate API

## Step 1: Access Your Domain Registrar/DNS Provider

You need to log in to where you manage your `secureai.dev` domain. Common providers:
- **Cloudflare** (most common for .dev domains)
- **Google Domains** (if purchased there)
- **Namecheap**
- **GoDaddy**
- **AWS Route 53**

## Step 2: Find Your DNS Management

Look for:
- "DNS Management"
- "DNS Settings"
- "DNS Records"
- "Manage DNS"

## Step 3: Create an A Record for Your Subdomain

1. **Click "Add Record" or "Create Record"**

2. **Select Record Type: A**

3. **Enter the following:**
   - **Name/Host**: `guardian` (or your chosen subdomain name)
     - This will create `guardian.secureai.dev`
   - **Type**: A
   - **Value/IP Address**: `64.225.57.145` (your server IP)
   - **TTL**: 3600 (or Auto/Default)

4. **Save the record**

## Step 4: Verify DNS Propagation

After creating the record, wait 5-60 minutes for DNS to propagate, then verify:

### On Windows (PowerShell):
```powershell
nslookup guardian.secureai.dev
```

### On Linux/Mac:
```bash
dig guardian.secureai.dev
# or
nslookup guardian.secureai.dev
```

### Online Tools:
- Visit: https://dnschecker.org
- Enter: `guardian.secureai.dev`
- Select "A" record type
- Check if it resolves to `64.225.57.145`

## Step 5: Proceed with HTTPS Setup

Once DNS is verified, proceed with the HTTPS setup using your new subdomain.

---

## Cloudflare-Specific Instructions

If your domain is managed by Cloudflare:

1. **Log in to Cloudflare Dashboard**
2. **Select your domain** (`secureai.dev`)
3. **Go to "DNS" → "Records"**
4. **Click "Add record"**
5. **Fill in:**
   - **Type**: A
   - **Name**: `guardian`
   - **IPv4 address**: `64.225.57.145`
   - **Proxy status**: ⚠️ **Turn OFF proxy** (gray cloud) for SSL certificate generation
     - You can enable it later after SSL is set up
   - **TTL**: Auto
6. **Save**

**Important for Cloudflare:**
- For Let's Encrypt to work, the proxy must be **OFF** (gray cloud) initially
- After SSL is set up, you can enable Cloudflare proxy (orange cloud) for DDoS protection

---

## Google Domains Instructions

1. **Log in to Google Domains**
2. **Click on your domain** (`secureai.dev`)
3. **Go to "DNS" tab**
4. **Scroll to "Custom resource records"**
5. **Add record:**
   - **Name**: `guardian`
   - **Type**: A
   - **Data**: `64.225.57.145`
   - **TTL**: 3600
6. **Save**

---

## Namecheap Instructions

1. **Log in to Namecheap**
2. **Go to "Domain List"**
3. **Click "Manage" next to `secureai.dev`**
4. **Go to "Advanced DNS" tab**
5. **Click "Add New Record"**
6. **Select:**
   - **Type**: A Record
   - **Host**: `guardian`
   - **Value**: `64.225.57.145`
   - **TTL**: Automatic
7. **Save**

---

## Troubleshooting

### DNS Not Resolving
- Wait longer (can take up to 24 hours, but usually 5-60 minutes)
- Clear your DNS cache:
  - Windows: `ipconfig /flushdns`
  - Mac/Linux: `sudo dscacheutil -flushcache`
- Try a different DNS server (8.8.8.8)

### Wrong IP Address
- Double-check your server IP: `curl ifconfig.me` (on your server)
- Verify the A record value matches exactly

### Cloudflare Proxy Issues
- Make sure proxy is OFF (gray cloud) for initial SSL setup
- Let's Encrypt needs direct access to your server

---

## Next Steps

After DNS is verified:
1. Follow `HTTPS_SETUP_GUIDE.md`
2. Use your subdomain (e.g., `guardian.secureai.dev`) instead of the IP
3. Your site will be accessible at: `https://guardian.secureai.dev`

