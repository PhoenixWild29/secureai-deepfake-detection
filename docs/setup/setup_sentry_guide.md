# Sentry Error Tracking Setup Guide

## Step 1: Create Sentry Account

1. Go to https://sentry.io/signup/
2. Sign up with email or GitHub
3. Verify your email

## Step 2: Create Project

1. After login, click "Create Project"
2. Select platform: **Python**
3. Select framework: **Flask**
4. Project name: `SecureAI Guardian`
5. Click "Create Project"

## Step 3: Get DSN

1. After project creation, you'll see "Configure Flask"
2. Copy the DSN (looks like):
   ```
   https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```
3. **Save this DSN** - you'll need it for configuration

## Step 4: Configure in .env

Add to your `.env` file:

```bash
SENTRY_DSN=https://your-dsn-here@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0
```

### Configuration Options:

- `SENTRY_DSN`: Your project DSN (required)
- `SENTRY_TRACES_SAMPLE_RATE`: 0.0-1.0 (0.1 = 10% of transactions)
- `SENTRY_PROFILES_SAMPLE_RATE`: 0.0-1.0 (0.1 = 10% profiling)
- `ENVIRONMENT`: `development`, `staging`, or `production`
- `APP_VERSION`: Your app version (e.g., `1.0.0`)

## Step 5: Test Integration

Run your application and trigger an error. It should appear in Sentry dashboard within seconds.

## Step 6: Configure Alerts (Optional)

1. Go to Sentry → Settings → Alerts
2. Create alert rules:
   - New issues
   - High priority errors
   - Performance degradation

## Features

### Error Tracking
- Real-time error notifications
- Stack traces with context
- User impact analysis

### Performance Monitoring
- Transaction tracing
- Slow query detection
- Performance metrics

### Release Tracking
- Deploy notifications
- Version comparison
- Regression detection

## Pricing

- **Developer Plan**: Free (5,000 events/month)
- **Team Plan**: $26/month (50,000 events/month)
- **Business Plan**: $80/month (Unlimited events)

## Best Practices

1. ✅ Set appropriate sample rates (0.1 = 10%)
2. ✅ Filter sensitive data (already configured)
3. ✅ Use different DSNs for dev/staging/prod
4. ✅ Set up alert rules
5. ✅ Review and resolve issues regularly

## Troubleshooting

### Errors not appearing
- Check DSN is correct
- Verify `sentry-sdk[flask]` is installed
- Check Sentry dashboard for rate limits

### Too many events
- Reduce `SENTRY_TRACES_SAMPLE_RATE`
- Filter out non-critical errors
- Upgrade plan if needed

