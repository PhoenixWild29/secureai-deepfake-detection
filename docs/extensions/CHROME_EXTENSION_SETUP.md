# SecureAI X Analyzer Chrome Extension

## Overview

The SecureAI X Analyzer Chrome extension allows users to analyze X/Twitter videos directly from the X website without needing to download or upload files manually. The extension leverages your authenticated browser session to extract video URLs and upload them to SecureAI for deepfake detection.

## Why This Extension?

X/Twitter restricts unauthenticated access to video media. The extension:
- Uses your authenticated browser session (you're already logged into X)
- Extracts the actual video URL from the page
- Uploads it directly to SecureAI for analysis
- Provides seamless UX - no manual download/upload needed

## Installation

### Step 1: Download/Clone the Extension

The extension is located in:
```
extensions/chrome-secureai-x-analyzer/
```

### Step 2: Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **"Load unpacked"**
4. Select the `extensions/chrome-secureai-x-analyzer/` folder
5. The extension should now appear in your extensions list

### Step 3: Verify Installation

1. Navigate to an X/Twitter post with a video
2. Click the SecureAI extension icon in your toolbar
3. You should see the "SecureAI X Analyzer" popup

## Usage

### Basic Usage

1. **Navigate to an X post with a video**
   - Open any X/Twitter post that contains a video
   - The post URL should be something like: `https://x.com/username/status/1234567890`

2. **Click the extension icon**
   - Click the SecureAI extension icon in your Chrome toolbar
   - The popup will open

3. **Click "Analyze this X video"**
   - The extension will:
     - Extract the video URL from the page
     - Download the video using your authenticated session
     - Upload it to SecureAI backend
     - Start the analysis

4. **View results**
   - The extension will show an `analysis_id` in the popup
   - Open SecureAI Guardian (`https://guardian.secureai.dev`)
   - The analysis should appear in your results (or you can search by ID)

### Advanced: Custom API Base

If you're running a local instance or using a different backend:

1. Open the extension popup
2. Enter your API base URL in the input field (e.g., `http://localhost:5000` or `https://your-domain.com`)
3. Click "Analyze this X video"

Default: `https://guardian.secureai.dev`

## How It Works

### Technical Flow

1. **Video Extraction** (`service_worker.js`):
   - Injects a script into the X page
   - Searches HTML for `video.twimg.com/*.mp4` URLs
   - Selects the highest quality variant (longest URL)

2. **Video Download** (`service_worker.js`):
   - Uses `fetch()` with `credentials: 'include'` to download the video
   - Your browser's authenticated session cookies are automatically included
   - Converts the response to a `File` object

3. **Upload to SecureAI** (`service_worker.js`):
   - Creates a `FormData` with the video file
   - Generates a unique `analysis_id`
   - POSTs to `/api/analyze` endpoint
   - Returns the `analysis_id` for tracking

4. **Analysis** (Backend):
   - SecureAI backend receives the video
   - Runs deepfake detection using V13 ensemble
   - Returns results via WebSocket or API

## Troubleshooting

### "No video.twimg.com MP4 URL found on page"

**Cause**: X's HTML structure may have changed, or the video format is different.

**Solutions**:
1. **Refresh the X page** and try again
2. **Check if the post actually has a video** (not just an image or GIF)
3. **Try a different X post** with a video
4. **Report the issue** - we may need to update the extraction logic

### "Failed to fetch MP4: 403 Forbidden"

**Cause**: Your browser session may have expired, or X is blocking the request.

**Solutions**:
1. **Refresh your X login** - log out and log back into X
2. **Check if you're logged into X** in the same browser
3. **Try a different X post**
4. **Clear browser cookies** for X and log back in

### "SecureAI analyze failed: 400/500"

**Cause**: Backend API issue or video format problem.

**Solutions**:
1. **Check backend status**: `curl https://guardian.secureai.dev/api/health`
2. **Verify API base URL** is correct in extension popup
3. **Check backend logs**: `docker logs secureai-backend`
4. **Try uploading the video directly** via SecureAI Guardian UI instead

### Extension Not Appearing

**Solutions**:
1. **Check if extension is enabled** in `chrome://extensions/`
2. **Reload the extension** (click the reload icon)
3. **Check for errors** in the extension's service worker (click "service worker" link in extensions page)
4. **Reinstall the extension** (remove and load unpacked again)

## Development

### File Structure

```
extensions/chrome-secureai-x-analyzer/
├── manifest.json          # Extension configuration
├── popup.html             # Extension popup UI
├── popup.js               # Popup logic
└── service_worker.js     # Background script (video extraction & upload)
```

### Updating Video Extraction Logic

If X changes their HTML structure, update `extractMp4FromPage()` in `service_worker.js`:

```javascript
// Current: searches for video.twimg.com URLs
const re = /https:\/\/video\.twimg\.com\/[^"'\\\s]+?\.mp4[^"'\\\s]*/g;

// You may need to:
// 1. Search for different URL patterns
// 2. Use DOM queries instead of regex
// 3. Check for video elements directly
```

### Testing

1. **Load extension in Chrome** (Developer mode)
2. **Open DevTools** for the extension:
   - Go to `chrome://extensions/`
   - Click "service worker" link under the extension
   - This opens the service worker console
3. **Test on an X post**:
   - Navigate to an X post with a video
   - Click extension icon
   - Check service worker console for errors
   - Check popup console (right-click popup → Inspect)

## Future Improvements

- [ ] Better video extraction (DOM queries instead of regex)
- [ ] Support for multiple videos in a thread
- [ ] Direct result display in extension popup
- [ ] Progress tracking in extension
- [ ] Support for other platforms (YouTube, TikTok, etc.)
- [ ] OAuth flow for server-side X authentication (alternative to extension)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review extension logs (service worker console)
3. Check backend logs: `docker logs secureai-backend`
4. Report issues with:
   - X post URL (if possible)
   - Browser version
   - Extension version
   - Error messages from console
