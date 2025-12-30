# 🔑 How to Get Your Google Gemini API Key

This guide will walk you through getting a Gemini API key for the SecureSage AI consultant feature.

---

## Step-by-Step Instructions

### Step 1: Go to Google AI Studio

1. Open your web browser
2. Navigate to: **https://aistudio.google.com/**
3. You'll need to sign in with your Google account

### Step 2: Sign In

1. Click **"Sign in"** or **"Get started"**
2. Use your Google account credentials
3. Accept any terms of service if prompted

### Step 3: Create API Key

1. Once signed in, look for one of these options:
   - **"Get API Key"** button (usually in the top right or center)
   - **"Create API Key"** link
   - Navigate to: **https://aistudio.google.com/app/apikey**

2. Click **"Create API Key"** or **"Get API Key"**

3. You may be asked to:
   - Select a Google Cloud project (you can create a new one or use default)
   - Accept terms and conditions

### Step 4: Copy Your API Key

1. Your API key will be displayed (it looks like: `AIzaSy...`)
2. **IMPORTANT:** Copy the key immediately - you may not be able to see it again!
3. Click **"Copy"** or manually select and copy the entire key

### Step 5: Add to Your Project

1. Open the `.env.local` file in the `secureai-guardian` directory
2. Find the line: `GEMINI_API_KEY=your_actual_api_key_here`
3. Replace `your_actual_api_key_here` with your actual API key:
   ```
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
4. Save the file

---

## Alternative Method: Google Cloud Console

If the above doesn't work, you can also get the key from Google Cloud Console:

1. Go to: **https://console.cloud.google.com/**
2. Sign in with your Google account
3. Create a new project (or select existing)
4. Navigate to **"APIs & Services"** > **"Credentials"**
5. Click **"Create Credentials"** > **"API Key"**
6. Copy the generated key
7. (Optional) Restrict the API key to "Generative Language API" for security

---

## Important Notes

### ⚠️ Security Best Practices

1. **Never commit your API key to Git**
   - The `.env.local` file is already in `.gitignore`
   - Never share your API key publicly

2. **API Key Limits**
   - Free tier has rate limits
   - Monitor usage at: https://aistudio.google.com/app/apikey

3. **Key Restrictions (Optional but Recommended)**
   - You can restrict the key to specific APIs
   - Restrict to "Generative Language API" only
   - Add IP restrictions if needed

### 💰 Pricing

- **Free Tier:** 60 requests per minute
- **Paid Tier:** Available for higher usage
- Check current pricing: https://ai.google.dev/pricing

---

## Troubleshooting

### "API Key Invalid" Error

1. **Check the key is correct:**
   - No extra spaces
   - Complete key copied (starts with `AIzaSy`)
   - No line breaks

2. **Verify in `.env.local`:**
   ```
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
   (No quotes, no spaces around `=`)

3. **Restart the dev server** after changing `.env.local`:
   ```bash
   # Stop the server (Ctrl+C)
   # Then restart:
   npm run dev
   ```

### "Quota Exceeded" Error

- You've hit the free tier limit (60 requests/minute)
- Wait a minute and try again
- Or upgrade to paid tier

### "API Not Enabled" Error

1. Go to Google Cloud Console
2. Enable "Generative Language API"
3. Wait a few minutes for activation

---

## Quick Reference

**Get API Key:** https://aistudio.google.com/app/apikey

**API Documentation:** https://ai.google.dev/docs

**Usage Dashboard:** https://aistudio.google.com/app/apikey (view usage)

---

## After Getting Your Key

1. ✅ Copy your API key
2. ✅ Open `secureai-guardian/.env.local`
3. ✅ Replace `your_actual_api_key_here` with your key
4. ✅ Save the file
5. ✅ Restart your dev server (`npm run dev`)

---

## Test Your API Key

Once configured, you can test it by:

1. Starting the frontend: `npm run dev`
2. Opening `http://localhost:3000`
3. Logging in and clicking the "Consult Sage" button
4. If SecureSage responds, your API key is working! ✅

---

**Need Help?** Check the troubleshooting section above or visit: https://ai.google.dev/docs

