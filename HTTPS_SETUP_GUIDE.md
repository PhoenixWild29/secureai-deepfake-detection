# HTTPS/SSL Setup Guide for SecureAI Guardian

This guide will help you set up HTTPS/SSL certificates using Let's Encrypt for your SecureAI Guardian deployment.

## Prerequisites

1. **Domain Name**: You need a domain name or subdomain (e.g., `guardian.secureai.dev`) that points to your server's IP address
2. **DNS Configuration**: Your domain's A record should point to your server IP
3. **Ports Open**: Ports 80 (HTTP) and 443 (HTTPS) must be open in your firewall

## Step 1: Set Up Your Subdomain

**If you already have a domain (like `secureai.dev`):**
- Follow `SUBDOMAIN_SETUP_GUIDE.md` to create a subdomain (e.g., `guardian.secureai.dev`)
- Recommended subdomain: `guardian.secureai.dev`

**If you need to set up DNS:**
1. Log in to your domain registrar (e.g., GoDaddy, Namecheap, Cloudflare)
2. Create an A record:
   - **Type**: A
   - **Name**: `guardian` (or your chosen subdomain)
   - **Value**: Your server IP address (e.g., `64.225.57.145`)
   - **TTL**: 3600 (or default)

3. Wait for DNS propagation (can take a few minutes to 24 hours)
4. Verify DNS is working:
   ```bash
   nslookup guardian.secureai.dev
   # or
   dig guardian.secureai.dev
   ```

## Step 2: Install Certbot on Your Server

SSH into your server and run:

```bash
# Update package list
sudo apt update

# Install certbot
sudo apt install certbot -y

# Verify installation
certbot --version
```

## Step 3: Stop Nginx Container Temporarily

We need to stop the Nginx container so certbot can use port 80 for verification:

```bash
cd /root/secureai-deepfake-detection  # or wherever you cloned the repo
docker compose -f docker-compose.quick.yml stop nginx
```

## Step 4: Get SSL Certificate

Run certbot to get your certificate (replace `yourdomain.com` with your actual domain):

```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

**Note**: If you only have a subdomain, use:
```bash
sudo certbot certonly --standalone -d secureai.yourdomain.com
```

Follow the prompts:
- Enter your email address (for renewal notifications)
- Agree to terms of service
- Optionally share email with EFF

Certbot will:
1. Start a temporary web server on port 80
2. Verify you own the domain
3. Download and save certificates to `/etc/letsencrypt/live/yourdomain.com/`

## Step 5: Create Certificate Directory Structure

```bash
# Create directory for certificates in your project
mkdir -p certs

# Copy certificates (we'll use these in Docker)
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/

# Set proper permissions
sudo chmod 644 certs/fullchain.pem
sudo chmod 600 certs/privkey.pem
sudo chown $USER:$USER certs/*.pem
```

## Step 6: Update Docker Compose for HTTPS

The `docker-compose.quick.yml` file needs to be updated to:
1. Expose port 443
2. Mount the certificates
3. Use the HTTPS nginx configuration

We'll create an updated version. See the next steps.

## Step 7: Update Nginx Configuration for HTTPS

We'll create an HTTPS-enabled nginx configuration that:
- Redirects HTTP to HTTPS
- Serves the frontend over HTTPS
- Proxies API requests securely

## Step 8: Restart Services

```bash
# Start all services with HTTPS
docker compose -f docker-compose.quick.yml up -d

# Check status
docker compose -f docker-compose.quick.yml ps

# Check logs
docker compose -f docker-compose.quick.yml logs nginx
```

## Step 9: Test HTTPS

1. Open your browser and go to: `https://yourdomain.com`
2. You should see a padlock icon indicating the connection is secure
3. Test the API: `https://yourdomain.com/api/health`

## Step 10: Set Up Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up auto-renewal:

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Certbot automatically sets up a systemd timer, but we need to handle Docker
# Create a renewal script
sudo nano /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

Add this content:
```bash
#!/bin/bash
cd /root/secureai-deepfake-detection  # Update with your actual path
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
docker compose -f docker-compose.quick.yml restart nginx
```

Make it executable:
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

## Troubleshooting

### Certificate Not Found
- Verify DNS is pointing to your server: `nslookup yourdomain.com`
- Ensure port 80 is open: `sudo ufw allow 80`
- Check certbot logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log`

### Nginx Can't Read Certificates
- Check file permissions: `ls -la certs/`
- Ensure certificates are mounted in docker-compose

### Certificate Renewal Fails
- Ensure the renewal hook script is executable
- Test manually: `sudo certbot renew --dry-run`

### Mixed Content Warnings
- Ensure your frontend uses HTTPS for API calls
- Check browser console for HTTP requests

## Security Best Practices

1. **HSTS**: Already configured in nginx config
2. **Strong Ciphers**: Modern TLS 1.2/1.3 only
3. **Auto-Renewal**: Set up and test renewal
4. **Firewall**: Only open ports 80 and 443
5. **Regular Updates**: Keep certbot and nginx updated

## Next Steps

After HTTPS is set up:
1. Update your frontend API base URL to use HTTPS
2. Configure CORS if needed
3. Set up monitoring for certificate expiration
4. Consider adding a CDN for better performance
