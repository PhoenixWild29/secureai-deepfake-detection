# Proxy Error Fix

## Issue
Vite proxy was logging `ECONNREFUSED` errors every 30 seconds when the backend server wasn't running, causing console spam.

## Solution Applied

### 1. Dashboard Component (`Dashboard.tsx`)
- **Stopped automatic retries**: Dashboard now only tries to fetch stats once on mount
- **No polling interval**: Removed the 30-second polling that was causing repeated errors
- **Graceful fallback**: Uses local history data when backend is unavailable
- **Silent error handling**: Connection errors are handled silently without console spam

### 2. Vite Configuration (`vite.config.ts`)
- **Reduced log level**: Set `logLevel: 'warn'` to suppress info-level proxy errors
- **Error suppression**: Override proxy error handler to prevent `ECONNREFUSED` errors from being logged
- **Shorter timeout**: Reduced timeout to 3 seconds to fail faster
- **503 response**: Returns proper 503 response instead of crashing

### 3. Backend Dependency (`requirements.txt`)
- **Flask-SocketIO installed**: Fixed missing `flask_socketio` module error
- Run `INSTALL_FLASK_SOCKETIO.bat` or `py -m pip install Flask-SocketIO python-socketio` if needed

## Result

✅ **No more console spam** - Proxy errors are suppressed when backend is not running
✅ **Dashboard works offline** - Uses local data when backend is unavailable  
✅ **Backend can start** - Flask-SocketIO dependency is now installed

## Testing

1. **Without backend running**: Dashboard should load with local data, no errors in console
2. **With backend running**: Dashboard should fetch and display real stats
3. **Backend startup**: Should start without `ModuleNotFoundError` for flask_socketio

## Next Steps

1. Start backend: `py api.py`
2. Refresh frontend: The Dashboard will automatically fetch real stats when backend is available
3. No action needed if backend is not running - Dashboard will work with local data

