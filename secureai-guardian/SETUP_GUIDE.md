# 🚀 SecureAI Guardian - Setup Guide

## Quick Setup Instructions

### Prerequisites
- Node.js 18+ installed
- Python backend running (Flask or FastAPI)
- Google Gemini API key (for SecureSage)

---

## Step-by-Step Setup

### 1. Install Dependencies
```bash
cd secureai-guardian
npm install
```

This will install:
- React 19.2.3
- TypeScript
- Vite
- Recharts
- Axios (for API calls)
- Google GenAI SDK

### 2. Configure Environment

Create a `.env.local` file in the `secureai-guardian` directory:

```env
# Backend API URL
# For Flask: http://localhost:5000
# For FastAPI: http://localhost:8000
VITE_API_BASE_URL=http://localhost:5000

# Google Gemini API Key (for SecureSage AI)
# Get your API key from: https://aistudio.google.com/app/apikey
# See HOW_TO_GET_GEMINI_API_KEY.md for detailed instructions
GEMINI_API_KEY=AIzaSyBeQGYPy-mmlDppWYu6qr9I7Y9NbRN9yvE

# WebSocket URL (optional, for real-time updates)
VITE_WS_URL=ws://localhost:5000/ws
```

**Important:** Replace `your_actual_api_key_here` with your actual Gemini API key.

### 3. Start Backend Server

Make sure your Python backend is running:

**For Flask:**
```bash
python api.py
```

**For FastAPI:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

The backend should be accessible at the URL you configured in `.env.local`.

### 4. Start Frontend Development Server

```bash
npm run dev
```

The frontend will start on `http://localhost:3000`

### 5. Test the Integration

1. Open `http://localhost:3000` in your browser
2. Click "Initialize Neural Passport" to login
3. Navigate to "Forensic Laboratory" (Scanner)
4. Upload a video file
5. Watch the analysis progress
6. View the results

---

## Troubleshooting

### Backend Connection Issues

**Error: "Backend service unavailable"**

**Solutions:**
1. Check that your backend server is running
2. Verify the `VITE_API_BASE_URL` in `.env.local` matches your backend URL
3. Check backend logs for errors
4. Test backend health endpoint: `curl http://localhost:5000/api/health`

### CORS Errors

If you see CORS errors in the browser console:

**For Flask backend**, add CORS support:
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
```

**For FastAPI backend**, CORS should already be configured in `app/main.py`.

### Environment Variables Not Loading

**Solution:**
1. Make sure `.env.local` is in the `secureai-guardian` directory
2. Restart the dev server after changing `.env.local`
3. Check that variable names start with `VITE_` for Vite to expose them

### Analysis Fails

**Check:**
1. Backend logs for error messages
2. File format is supported (MP4, MKV, etc.)
3. File size is within limits
4. Backend has required ML models loaded

---

## Production Build

### Build for Production
```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Preview Production Build
```bash
npm run preview
```

### Deploy

The `dist/` folder contains the production-ready static files. Deploy to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Any static hosting service

**Remember to:**
- Set production environment variables
- Update `VITE_API_BASE_URL` to your production API URL
- Configure CORS on your backend for production domain

---

## Development Tips

### Hot Reload
The Vite dev server supports hot module replacement. Changes to components will update instantly.

### TypeScript Errors
If you see TypeScript errors:
```bash
npm run type-check  # Add this script to package.json if needed
```

### API Testing
Test the API directly:
```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "video=@test_video.mp4"
```

---

## File Structure

```
secureai-guardian/
├── components/          # React components
│   ├── Scanner.tsx      # ✅ Now uses real API
│   ├── Dashboard.tsx
│   ├── Results.tsx
│   └── ...
├── services/            # Service layer
│   ├── apiService.ts    # ✅ Backend API integration
│   ├── websocketService.ts  # ✅ WebSocket support
│   └── geminiService.ts     # Gemini AI
├── types.ts             # TypeScript definitions
├── .env.local          # Your environment config (create this)
├── vite.config.ts      # ✅ Updated with env support
└── package.json         # ✅ Updated with axios
```

---

## Next Steps

1. ✅ Integration complete
2. Test with real videos
3. Configure production environment
4. Enable WebSocket for real-time progress (when backend supports it)
5. Add blockchain verification integration

---

## Support

For issues or questions:
1. Check `INTEGRATION_EVALUATION.md` for technical details
2. Check `INTEGRATION_COMPLETE.md` for implementation summary
3. Review backend API documentation
4. Check browser console for error messages

---

**Happy coding!** 🎉

