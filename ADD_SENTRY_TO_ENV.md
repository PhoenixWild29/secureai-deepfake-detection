# Add Sentry DSN to .env File

## Your Sentry DSN

From the Sentry configuration page, copy your DSN. It should look like:

```
https://717bfe28ac24ae69df5764c9223d1235@04510624487374848.ingest.us.sentry.io/4510624491307008
```

---

## Add to .env File

Open your `.env` file and add these lines:

```bash
# Sentry Error Tracking
SENTRY_DSN=https://717bfe28ac24ae69df5764c9223d1235@04510624487374848.ingest.us.sentry.io/4510624491307008
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0
```

**Important:** Replace the DSN above with your actual DSN from the Sentry page!

---

## How to Get Your DSN

1. **On the Sentry page** you're viewing
2. **Look for the code block** with `sentry_sdk.init(`
3. **Find the line**: `dsn="https://..."`
4. **Copy the entire URL** (everything between the quotes)
5. **Paste it** in your `.env` file

---

## After Adding DSN

Once you've added the DSN to `.env`:
1. The application will automatically use Sentry
2. Errors will appear in your Sentry dashboard
3. No code changes needed - it's already integrated!

---

## Optional: Adjust Sample Rates

- `SENTRY_TRACES_SAMPLE_RATE=0.1` - Tracks 10% of transactions (for performance)
- `SENTRY_PROFILES_SAMPLE_RATE=0.1` - Profiles 10% of transactions
- Lower values = fewer events = lower cost
- Higher values = more data = better monitoring

For production, `0.1` (10%) is a good balance.

