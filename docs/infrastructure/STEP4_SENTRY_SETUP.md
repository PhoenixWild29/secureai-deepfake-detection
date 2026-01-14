# Step 4: Sentry Setup 📊

## Overview

Sentry provides real-time error tracking and monitoring for:
- Application errors and exceptions
- Performance monitoring
- Release tracking
- User feedback

---

## Step 1: Create Sentry Account

1. **Go to**: https://sentry.io/signup/
2. **Sign up** with:
   - Email address, or
   - GitHub account (recommended - faster)
3. **Verify your email** (if using email signup)

---

## Step 2: Create Project

1. **After login**, you'll see the "Create Project" screen
2. **Select platform**: **Python**
3. **Select framework**: **Flask**
4. **Project name**: `SecureAI Guardian`
5. **Team**: Use default or create new
6. Click **"Create Project"**

---

## Step 3: Get DSN (Data Source Name)

1. **After project creation**, you'll see setup instructions
2. **Copy the DSN** - it looks like:
   ```
   https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```
3. **Save this DSN** - you'll need it for `.env`

**Note:** You can also find the DSN later:
- Go to **Settings** → **Projects** → **SecureAI Guardian** → **Client Keys (DSN)**

---

## Step 4: Configure Application

Add these to your `.env` file:

```bash
# Sentry Error Tracking
SENTRY_DSN=https://your-dsn-here@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0
```

**Replace:**
- `https://your-dsn-here@sentry.io/project-id` with your actual DSN from Step 3

**Optional Settings:**
- `SENTRY_TRACES_SAMPLE_RATE=0.1` - 10% of transactions tracked (for performance)
- `SENTRY_PROFILES_SAMPLE_RATE=0.1` - 10% of transactions profiled
- `ENVIRONMENT=production` - Set to `development` for local testing
- `APP_VERSION=1.0.0` - Your app version

---

## Step 5: Test Sentry Integration

The integration is automatic once configured. To test:

1. **Restart your application**
2. **Trigger an error** (or wait for a real one)
3. **Check Sentry dashboard** - errors should appear within seconds

---

## Sentry Dashboard Features

Once set up, you'll see:
- **Issues** - All errors and exceptions
- **Performance** - Response times and slow queries
- **Releases** - Track deployments and versions
- **Alerts** - Get notified of critical errors

---

## Cost Estimate

### Free Tier
- **5,000 events/month** (errors, transactions)
- **1 project**
- **7 days** data retention
- **Community support**

### Paid Plans
- **Team**: $26/month - 50K events, 90 days retention
- **Business**: $80/month - 200K events, 90 days retention

**For most applications**: Free tier is sufficient!

---

## Security Best Practices

1. ✅ **Use environment variables** for DSN (never commit to git)
2. ✅ **Filter sensitive data** (passwords, tokens) from error reports
3. ✅ **Set up alerts** for critical errors
4. ✅ **Review errors regularly** and fix high-frequency issues
5. ✅ **Use releases** to track which version has issues

---

## Troubleshooting

### Errors not appearing in Sentry
- Check DSN is correct in `.env`
- Verify `sentry-sdk[flask]` is installed: `pip install sentry-sdk[flask]`
- Check Sentry dashboard for rate limits
- Review application logs for Sentry errors

### Too many events
- Reduce `SENTRY_TRACES_SAMPLE_RATE` (e.g., 0.01 for 1%)
- Filter out non-critical errors in code
- Upgrade to paid plan if needed

### DSN not working
- Regenerate DSN in Sentry dashboard
- Check for typos in `.env` file
- Ensure DSN starts with `https://`

---

## Next Steps

Once Sentry is configured:

1. ✅ **Step 1: Redis** - COMPLETE
2. ✅ **Step 2: PostgreSQL** - COMPLETE
3. ✅ **Step 3: AWS S3** - COMPLETE
4. ✅ **Step 4: Sentry** - IN PROGRESS
5. ⏳ **Step 5: Final Verification** - PENDING

---

## Quick Reference

**Sentry Dashboard**: https://sentry.io/

**DSN Format**: `https://xxxxx@xxxxx.ingest.sentry.io/xxxxx`

**Required in .env**:
- `SENTRY_DSN` (required)
- `SENTRY_TRACES_SAMPLE_RATE` (optional, default: 0.1)
- `ENVIRONMENT` (optional, default: production)

---

**Ready to start?** Create your Sentry account and project, then we'll configure it!

