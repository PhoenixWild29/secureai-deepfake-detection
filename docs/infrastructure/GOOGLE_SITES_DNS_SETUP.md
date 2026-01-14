# DNS Setup for Google Sites Users

If you're using **Google Sites** (sites.google.com) for your website, you need to understand:

1. **Google Sites** = Website builder/hosting (where you edit your site)
2. **DNS Provider** = Where you manage domain records (different from Google Sites)

## Finding Your DNS Provider

Your `secureai.dev` domain's DNS is managed by one of these:

### Option 1: Google Domains (Most Likely)
If you bought your domain through Google:
1. Go to: https://domains.google.com
2. Sign in with your Google account
3. Click on `secureai.dev`
4. Go to "DNS" tab

### Option 2: Another Registrar
Common registrars:
- **Namecheap**
- **GoDaddy**
- **Cloudflare**
- **AWS Route 53**
- **Name.com**

**How to find out:**
- Check your email for domain purchase/renewal emails
- Look for DNS management emails
- Check your credit card statements for domain registrar charges

### Option 3: Check Current DNS Settings
You can check who manages your DNS:

1. **On Windows (PowerShell):**
   ```powershell
   nslookup -type=NS secureai.dev
   ```

2. **Online Tool:**
   - Visit: https://lookup.icann.org
   - Enter: `secureai.dev`
   - Look for "Name Servers" - this tells you who manages DNS

## Step-by-Step: Adding Subdomain DNS Record

### If Using Google Domains:

1. **Go to Google Domains:**
   - Visit: https://domains.google.com
   - Sign in with your Google account

2. **Select Your Domain:**
   - Click on `secureai.dev`

3. **Open DNS Settings:**
   - Click on "DNS" in the left sidebar
   - Scroll to "Custom resource records"

4. **Add A Record:**
   - Click "Manage custom records"
   - Click "Add new record"
   - Fill in:
     - **Name**: `guardian`
     - **Type**: A
     - **Data**: `64.225.57.145` (your server IP)
     - **TTL**: 3600
   - Click "Save"

5. **Verify:**
   - Wait 5-60 minutes
   - Check: `nslookup guardian.secureai.dev`

### If Using Cloudflare:

1. **Log in to Cloudflare:**
   - Visit: https://dash.cloudflare.com
   - Select `secureai.dev`

2. **Go to DNS:**
   - Click "DNS" → "Records"

3. **Add Record:**
   - Click "Add record"
   - Fill in:
     - **Type**: A
     - **Name**: `guardian`
     - **IPv4 address**: `64.225.57.145`
     - **Proxy status**: ⚠️ **Turn OFF** (gray cloud) for SSL setup
     - **TTL**: Auto
   - Click "Save"

**Important:** Keep proxy OFF (gray cloud) until SSL is set up, then you can enable it.

### If Using Namecheap:

1. **Log in to Namecheap:**
   - Visit: https://www.namecheap.com
   - Go to "Domain List"

2. **Manage Domain:**
   - Click "Manage" next to `secureai.dev`
   - Go to "Advanced DNS" tab

3. **Add Record:**
   - Click "Add New Record"
   - Select:
     - **Type**: A Record
     - **Host**: `guardian`
     - **Value**: `64.225.57.145`
     - **TTL**: Automatic
   - Click the checkmark to save

### If Using GoDaddy:

1. **Log in to GoDaddy:**
   - Visit: https://www.godaddy.com
   - Go to "My Products"

2. **Manage DNS:**
   - Find `secureai.dev`
   - Click "DNS" or "Manage DNS"

3. **Add Record:**
   - Click "Add" in the "Records" section
   - Fill in:
     - **Type**: A
     - **Name**: `guardian`
     - **Value**: `64.225.57.145`
     - **TTL**: 600 (or default)
   - Click "Save"

## Linking Your Google Site to the Subdomain

After setting up the subdomain and HTTPS, you can link from your Google Site:

### Option 1: Add a Button/Link
1. Edit your Google Site
2. Add a button or text link
3. Link to: `https://guardian.secureai.dev`

### Option 2: Create a Navigation Menu Item
1. In Google Sites, go to "Pages"
2. Add a new page or section
3. Add a link to: `https://guardian.secureai.dev`

### Option 3: Embed (Advanced)
You can embed the app in an iframe (though this may have limitations):
1. In Google Sites, add an "Embed" element
2. Use: `<iframe src="https://guardian.secureai.dev" width="100%" height="800"></iframe>`

## Quick Checklist

- [ ] Find your DNS provider (Google Domains, Cloudflare, etc.)
- [ ] Add A record: `guardian` → `64.225.57.145`
- [ ] Wait 5-60 minutes for DNS propagation
- [ ] Verify DNS: `nslookup guardian.secureai.dev`
- [ ] Run HTTPS setup script on server
- [ ] Add link to your Google Site

## Still Can't Find Your DNS Provider?

Try these steps:

1. **Check Your Email:**
   - Search for "domain", "DNS", "secureai.dev"
   - Look for setup/renewal emails

2. **Check Domain WHOIS:**
   - Visit: https://whois.net
   - Enter: `secureai.dev`
   - Look for "Registrar" and "Name Servers"

3. **Common Name Servers:**
   - `ns1.google.com` / `ns2.google.com` = Google Domains
   - `*.cloudflare.com` = Cloudflare
   - `*.namecheap.com` = Namecheap
   - `*.godaddy.com` = GoDaddy

## Next Steps After DNS is Set Up

1. **Wait for DNS propagation** (5-60 minutes)
2. **Verify DNS works:**
   ```powershell
   nslookup guardian.secureai.dev
   ```
3. **Run HTTPS setup on your server:**
   ```bash
   sudo bash setup-https.sh
   ```
4. **Update your Google Site** to link to the new subdomain

## Need Help?

If you can't find your DNS provider, share:
- Where you bought the domain
- Any emails you received about the domain
- The name servers (from `nslookup -type=NS secureai.dev`)

And I can provide specific instructions!

