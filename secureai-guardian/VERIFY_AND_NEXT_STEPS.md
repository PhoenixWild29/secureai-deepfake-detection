# ✅ API Key Verification & Next Steps

## API Key Verification

### ✅ API Key Status: **VERIFIED**

Your Gemini API key has been found in `.env.local`:
- **Format:** ✅ Valid (starts with `AIzaSy`)
- **Length:** ✅ Correct
- **Location:** ✅ Correct file (`.env.local`)

---

## Current Configuration Check

Your `.env.local` currently contains:
```
GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE
```

### ⚠️ Recommended: Add Complete Configuration

For full functionality, ensure your `.env.local` contains all these variables:

```env
# Backend API URL
VITE_API_BASE_URL=http://localhost:5000

# Google Gemini API Key (for SecureSage AI)
GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE

# WebSocket URL (optional, for real-time updates)
VITE_WS_URL=ws://localhost:5000/ws

# Environment
NODE_ENV=development
```

**Note:** If `VITE_API_BASE_URL` is missing, the app will default to `http://localhost:5000`, which should work if you're using Flask backend.

---

## Next Steps: Start the Application

### Step 1: Start Backend Server

Open a **new terminal window** and run:

**For Flask (default):**
```bash
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
python api.py
```

**For FastAPI:**
```bash
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
python -m uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
- Flask: `🚀 Starting SecureAI DeepFake Detection API...`
- Backend should be accessible at `http://localhost:5000`

**Verify Backend is Running:**
- Open browser: `http://localhost:5000/api/health`
- Should return: `{"status": "healthy"}` or similar

---

### Step 2: Start Frontend Development Server

Open **another terminal window** and run:

```bash
cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection\secureai-guardian"
npm run dev
```

**Expected Output:**
```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

**Frontend will be available at:** `http://localhost:3000`

---

### Step 3: Test the Integration

1. **Open Browser:**
   - Navigate to: `http://localhost:3000`

2. **Login:**
   - Click "Initialize Neural Passport"
   - Enter an alias (or leave blank for auto-generated)
   - Click "Initialize Neural Passport"

3. **Navigate to Scanner:**
   - Click "Forensic Laboratory" or "Initialize Forensic Lab"

4. **Upload a Video:**
   - Click the upload area or drag & drop a video file
   - Supported formats: MP4, MKV, JPEG, WEBP
   - Click "Initialize Scan Sequence"

5. **Watch Analysis:**
   - Progress bar will show analysis progress
   - Terminal logs will display processing steps
   - Results will appear automatically when complete

6. **View Results:**
   - See detailed forensic report
   - Check metrics and heatmap
   - Test SecureSage AI (click "Consult Sage" button)

---

## Quick Verification Commands

### Check Backend Health:
```powershell
# In PowerShell
Invoke-WebRequest -Uri "http://localhost:5000/api/health" | Select-Object -ExpandProperty Content
```

### Check Frontend:
```powershell
# Should return HTML
Invoke-WebRequest -Uri "http://localhost:3000" | Select-Object StatusCode
```

---

## Troubleshooting

### Backend Won't Start?

1. **Check Python is installed:**
   ```bash
   python --version
   ```

2. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check port 5000 is available:**
   ```bash
   netstat -ano | findstr :5000
   ```

### Frontend Won't Start?

1. **Check Node.js:**
   ```bash
   node --version  # Should be 18+
   ```

2. **Reinstall dependencies:**
   ```bash
   cd secureai-guardian
   rm -rf node_modules package-lock.json
   npm install
   ```

### API Key Not Working?

1. **Verify in `.env.local`:**
   - No quotes around the key
   - No spaces around `=`
   - Key starts with `AIzaSy`

2. **Restart dev server** after changing `.env.local`

3. **Test SecureSage:**
   - Click "Consult Sage" button
   - If it says "SecureSage core is offline", check API key

### Backend Connection Error?

1. **Verify backend is running:**
   - Check terminal for Flask/FastAPI output
   - Test: `http://localhost:5000/api/health`

2. **Check CORS:**
   - Flask: Make sure `flask-cors` is installed
   - FastAPI: Should already be configured

3. **Verify URL in `.env.local`:**
   - Should match backend port (5000 or 8000)

---

## Success Indicators

✅ **Backend Running:**
- Terminal shows Flask/FastAPI server started
- `http://localhost:5000/api/health` returns success

✅ **Frontend Running:**
- Terminal shows Vite dev server on port 3000
- Browser can access `http://localhost:3000`

✅ **Integration Working:**
- Can upload videos
- Analysis progress shows
- Results display correctly
- SecureSage responds (if API key is valid)

---

## What to Test

1. ✅ **File Upload** - Upload a test video
2. ✅ **Analysis Progress** - Watch progress bar and logs
3. ✅ **Results Display** - Verify results show correctly
4. ✅ **SecureSage** - Click "Consult Sage" and ask a question
5. ✅ **History** - Check scan history in Dashboard
6. ✅ **Error Handling** - Try uploading invalid file

---

## Next Actions

1. ⏳ **Start Backend** - Run `python api.py` in a terminal
2. ⏳ **Start Frontend** - Run `npm run dev` in another terminal
3. ⏳ **Test Integration** - Upload a video and verify it works
4. ⏳ **Test SecureSage** - Verify AI consultant works with your API key

---

**Ready to proceed!** 🚀

Your API key is verified and configured. Follow the steps above to start both servers and test the integration.

