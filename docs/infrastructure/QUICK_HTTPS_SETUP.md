# Quick HTTPS Setup for SecureAI Guardian

This is a streamlined guide to get HTTPS working with your `secureai.dev` domain.

## Your Current Setup
- **Domain**: `secureai.dev` (www.secureai.dev)
- **Server IP**: `64.225.57.145`
- **Recommended Subdomain**: `guardian.secureai.dev`

## Quick Start (3 Steps)

### Step 1: Create Subdomain DNS Record

1. **Log in to your DNS provider** (where you manage `secureai.dev`)
2. **Add an A record:**
   - **Name**: `guardian`
   - **Type**: A
   - **Value**: `64.225.57.145`
   - **TTL**: Auto or 3600
3. **Save the record**

**⚠️ Important for Cloudflare users:**
- Turn OFF the proxy (gray cloud icon) for initial SSL setup
- You can enable it later after SSL is working

### Step 2: Verify DNS (Wait 5-60 minutes)

Check if DNS is working:
```bash
# On Windows PowerShell
nslookup guardian.secureai.dev

# On Linux/Mac
dig guardian.secureai.dev
```

Or use online tool: https://dnschecker.org

### Step 3: Run HTTPS Setup Script

On your server, run:

```bash
# Pull latest changes
git pull origin master

# Make script executable
chmod +x setup-https.sh

# Run the setup (replace with your subdomain)
sudo bash setup-https.sh
```

When prompted, enter: `guardian.secureai.dev`

---

## What Happens Next

The script will:
1. ✅ Check DNS configuration
2. ✅ Install certbot (if needed)
3. ✅ Request SSL certificate from Let's Encrypt
4. ✅ Copy certificates to your project
5. ✅ Set up auto-renewal
6. ✅ Start services with HTTPS

---

## After Setup

Your site will be available at:
- **HTTPS**: `https://guardian.secureai.dev`
- HTTP will automatically redirect to HTTPS

---

## Troubleshooting

### "DNS not resolving"
- Wait longer (up to 24 hours, usually 5-60 minutes)
- Verify the A record is correct in your DNS provider
- Check if Cloudflare proxy is OFF (gray cloud)

### "Certificate request failed"
- Ensure port 80 is open: `sudo ufw allow 80`
- Verify DNS is resolving: `nslookup guardian.secureai.dev`
- Make sure Nginx container is stopped during certificate request

### "Nginx can't read certificates"
- Check file permissions: `ls -la certs/`
- Ensure certificates exist: `ls -la certs/*.pem`

---

## Need Help?

- **Subdomain setup**: See `SUBDOMAIN_SETUP_GUIDE.md`
- **Detailed HTTPS guide**: See `HTTPS_SETUP_GUIDE.md`
- **Manual setup**: Follow the manual steps in `HTTPS_SETUP_GUIDE.md`

---

## Next Steps After HTTPS

1. ✅ Test your site: `https://guardian.secureai.dev`
2. ✅ Update your main website (`www.secureai.dev`) to link to the app
3. ✅ Consider enabling Cloudflare proxy for DDoS protection
4. ✅ Set up monitoring for certificate expiration

