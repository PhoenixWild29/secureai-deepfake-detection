# 🔧 Video Upload Error Fix - 400 Bad Request

## Problem
- Some videos return `400 Bad Request` error
- Frontend shows "Failed to fetch" without details
- Backend only accepts specific file formats

## Root Cause

### Backend File Format Restrictions
The backend only accepts these formats:
- `mp4`
- `avi`
- `mov`
- `mkv`
- `webm`

**Maximum file size:** 500MB

### Issues Found:
1. Frontend accepted `video/*,image/*` (all formats)
2. No client-side validation before upload
3. Error messages didn't show backend error details
4. File size not validated on frontend

---

## Fixes Applied

### ✅ 1. Updated File Input Accept Attribute
**Before:**
```html
accept="video/*,image/*"
```

**After:**
```html
accept=".mp4,.avi,.mov,.mkv,.webm"
```

### ✅ 2. Added Client-Side Validation
- Checks file extension before upload
- Validates file size (500MB limit)
- Shows clear error messages
- Prevents invalid files from being selected

### ✅ 3. Improved Error Messages
- Shows specific backend error messages
- Provides format requirements
- Shows file size limits
- Better user feedback

### ✅ 4. Updated UI Text
- Changed "SUPPORTED: MKV, MP4, JPEG, WEBP" 
- To: "SUPPORTED: MP4, AVI, MOV, MKV, WEBM // 500MB LIMIT"

---

## Supported File Formats

✅ **Allowed:**
- `.mp4` - MPEG-4 Video
- `.avi` - Audio Video Interleave
- `.mov` - QuickTime Movie
- `.mkv` - Matroska Video
- `.webm` - WebM Video

❌ **Not Allowed:**
- `.jpg`, `.jpeg`, `.png` (images)
- `.gif`, `.webp` (other image formats)
- `.wmv`, `.flv` (other video formats)
- Any other formats

---

## File Size Limits

- **Maximum:** 500MB (524,288,000 bytes)
- **Recommended:** Under 100MB for faster processing

---

## Error Messages

### Client-Side (Before Upload):
- `"Unsupported file format. Please use: MP4, AVI, MOV, MKV, WEBM"`
- `"File too large. Maximum size is 500MB. Your file is X.X MB"`

### Server-Side (After Upload):
- `"No video file provided. Please select a file to upload."`
- `"Unsupported file format. Please use: MP4, AVI, MOV, MKV, or WEBM."`
- `"File too large. Maximum size is 500MB."`
- `"Invalid request: [details]"`

---

## Testing

1. **Test Valid Files:**
   - Upload `.mp4` file → Should work
   - Upload `.mkv` file → Should work
   - Upload `.avi` file → Should work

2. **Test Invalid Files:**
   - Try `.jpg` image → Should show error immediately
   - Try `.wmv` video → Should show error immediately
   - Try file > 500MB → Should show size error

3. **Test Error Handling:**
   - Check error messages are clear
   - Verify errors appear in red banner
   - Confirm file input clears on error

---

## Next Steps

1. **Restart Frontend:**
   ```bash
   # Stop frontend (Ctrl+C)
   npm run dev
   ```

2. **Test Upload:**
   - Try uploading a valid `.mp4` file
   - Try uploading an invalid format (e.g., `.jpg`)
   - Verify error messages appear correctly

---

## Expected Behavior

✅ **Valid File:**
- File selected successfully
- No error message
- Upload button enabled
- Analysis proceeds normally

❌ **Invalid File:**
- Error message appears immediately
- File input cleared
- Upload button disabled
- Clear explanation of what's wrong

---

**Fix complete!** The frontend now validates files before upload and shows clear error messages. Restart the frontend and try uploading videos again.

