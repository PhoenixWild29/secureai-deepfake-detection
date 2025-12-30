# 🔒 HTTPS Setup Guide for SecureAI Guardian

This guide walks you through setting up HTTPS/SSL for your SecureAI Guardian application using Let's Encrypt and Nginx.

## Prerequisites

- A Linux server (Ubuntu 20.04+ recommended)
- Domain name pointing to your server's IP address
- Root or sudo access
- Ports 80 and 443 open in firewall

## Step 1: Install Nginx and Certbot

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

## Step 2: Configure Domain DNS

Ensure your domain's A record points to your server's IP address:

```bash
# Check if DNS is configured
dig your-domain.com +short
# Should return your server's IP address
```

## Step 3: Update Nginx Configuration

1. Edit `nginx.conf` and replace `your-domain.com` with your actual domain
2. Copy the configuration:

```bash
sudo cp nginx.conf /etc/nginx/sites-available/secureai-guardian
sudo ln -s /etc/nginx/sites-available/secureai-guardian /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

3. Test the configuration:

```bash
sudo nginx -t
```

4. Start Nginx:

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

## Step 4: Obtain SSL Certificate

Run the automated setup script:

```bash
chmod +x setup-https.sh
sudo ./setup-https.sh
```

Or manually:

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts:
- Enter your email address
- Agree to terms of service
- Choose to redirect HTTP to HTTPS

## Step 5: Verify SSL Certificate

1. Check certificate status:

```bash
sudo certbot certificates
```

2. Test automatic renewal:

```bash
sudo certbot renew --dry-run
```

3. Visit your site: `https://your-domain.com`

## Step 6: Build and Deploy Frontend

1. Build the frontend:

```bash
cd secureai-guardian
npm run build
```

2. Copy build to Nginx directory:

```bash
sudo mkdir -p /var/www/secureai-guardian
sudo cp -r dist/* /var/www/secureai-guardian/
sudo chown -R www-data:www-data /var/www/secureai-guardian
```

## Step 7: Configure Backend

Ensure your backend is running on `127.0.0.1:5000` (localhost only, not publicly accessible).

The Nginx configuration will proxy requests from HTTPS to your backend.

## Step 8: Restart Services

```bash
sudo systemctl restart nginx
# Restart your backend service if using systemd
```

## Automatic Certificate Renewal

Certbot automatically sets up a systemd timer for renewal. Verify it's active:

```bash
sudo systemctl status certbot.timer
```

Certificates are renewed automatically 30 days before expiration.

## Troubleshooting

### Certificate Not Obtaining

1. **Check DNS**: Ensure domain points to your server
   ```bash
   dig your-domain.com +short
   ```

2. **Check Port 80**: Ensure it's open
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Check Nginx**: Ensure it's running
   ```bash
   sudo systemctl status nginx
   ```

### SSL Certificate Expired

Renew manually:
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Nginx Configuration Errors

Test configuration:
```bash
sudo nginx -t
```

Check logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

## Security Checklist

- ✅ HTTPS redirects HTTP traffic
- ✅ HSTS header enabled
- ✅ Strong SSL/TLS protocols (TLS 1.2+)
- ✅ Security headers configured
- ✅ Automatic certificate renewal active

## Next Steps

After HTTPS is set up:
1. Configure production server (Gunicorn)
2. Set up security headers
3. Implement rate limiting
4. Configure monitoring

See `PRODUCTION_READINESS_ROADMAP.md` for complete production setup.

