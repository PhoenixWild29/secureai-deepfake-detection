# 🔒 SecureSage Secure Setup Guide

## ⚠️ Security Issue Fixed

**IMPORTANT:** The API key is now stored securely on the backend server, NOT in the frontend code. This prevents the key from being exposed in browser JavaScript files.

## Backend Setup

### 1. Install Google Generative AI Package

On your server, install the required package:

```bash
pip install google-generativeai>=0.3.0
```

Or add to `requirements.txt` (already added):
```
google-generativeai>=0.3.0
```

### 2. Set Environment Variable

**For Local Development:**

Create or update `.env` file in the project root:
```bash
GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE
```

**For Docker/Production:**

Add to `docker-compose.https.yml` under `secureai-backend` environment:
```yaml
environment:
  - GEMINI_API_KEY=${GEMINI_API_KEY}
```

Then create a `.env` file in the project root (same directory as docker-compose.https.yml):
```bash
GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE
```

**For Direct Server Deployment:**

Export the environment variable:
```bash
export GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE
```

Or add to your system environment (e.g., `/etc/environment` or `~/.bashrc`).

### 3. Restart Backend

After setting the environment variable:

**Docker:**
```bash
docker compose -f docker-compose.https.yml restart secureai-backend
```

**Direct:**
```bash
# Stop the current server (Ctrl+C)
# Then restart:
python api.py
```

## Frontend Changes

✅ **No changes needed!** The frontend now automatically calls the secure backend endpoint `/api/sage/chat` instead of directly calling Gemini.

The API key is **never** sent to the frontend or exposed in browser code.

## Verification

1. Start the backend server
2. Open the frontend
3. Try SecureSage - it should work without any API key warnings
4. Check browser DevTools → Network tab → You should see requests to `/api/sage/chat` (not direct Gemini API calls)

## Security Benefits

✅ API key stored only on backend (server-side)  
✅ API key never exposed in frontend JavaScript  
✅ API key never sent to browser  
✅ Rate limiting on backend endpoint (30 requests/minute)  
✅ All requests go through your secure backend  

## Troubleshooting

### "GEMINI_API_KEY not configured on server"

- Check that `GEMINI_API_KEY` is set in your backend environment
- Restart the backend after setting the variable
- For Docker: Make sure the `.env` file is in the same directory as `docker-compose.https.yml`

### "google-generativeai package not installed"

- Run: `pip install google-generativeai>=0.3.0`
- Or rebuild Docker container: `docker compose -f docker-compose.https.yml build secureai-backend`

### SecureSage still shows errors

- Check backend logs for detailed error messages
- Verify the API key is valid at: https://aistudio.google.com/app/apikey
- Ensure the backend endpoint `/api/sage/chat` is accessible

---

**Security Note:** Never commit your `.env` file or API keys to Git. The `.env` file should be in `.gitignore`.
