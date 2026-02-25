# 🔧 Mobile Access Troubleshooting Guide

## Quick Diagnosis

Run `CHECK_MOBILE_ACCESS.bat` to automatically check:
- ✅ Network IP addresses
- ✅ Port status (3000, 5000)
- ✅ Vite configuration
- ✅ Firewall rules

---

## Common Issues & Fixes

### Issue 1: "Site can't be reached" on Mobile

**Symptoms:**
- Works on laptop (`localhost:3000`)
- Doesn't work on phone

**Fix:**
1. **Check Vite shows Network URL:**
   ```
   ➜  Local:   http://localhost:3000/
   ➜  Network: http://10.0.0.168:3000/  ← Must see this!
   ```
   If you DON'T see "Network", restart the frontend server.

2. **Use Network IP on phone:**
   - Don't use `localhost:3000` on phone
   - Use the Network IP from Vite output: `http://10.0.0.168:3000`

3. **Check firewall:**
   - Run `FIX_FIREWALL.bat` as Administrator
   - Or manually allow ports 3000 and 5000

---

### Issue 2: Frontend loads but API calls fail

**Symptoms:**
- Page loads on mobile
- But shows "Backend service unavailable" or API errors

**Fix:**
1. **Verify backend is running:**
   - Check backend terminal shows: `Running on http://0.0.0.0:5000`
   - Test from phone: `http://10.0.0.168:5000/api/health`

2. **Check Vite proxy:**
   - The proxy should forward `/api` requests to backend
   - Make sure `vite.config.ts` has correct proxy config

3. **Verify API service uses relative URLs:**
   - `apiService.ts` should use `''` (empty string) in dev mode
   - This makes requests go through Vite proxy

---

### Issue 3: Works sometimes, not others

**Symptoms:**
- Mobile access works after restart
- Stops working later

**Possible causes:**
1. **Network IP changed:**
   - Wi-Fi reconnection changed your IP
   - Solution: Check new IP with `ipconfig` or `CHECK_MOBILE_ACCESS.bat`

2. **Servers crashed:**
   - Backend or frontend stopped
   - Solution: Restart both servers

3. **Firewall reset:**
   - Windows update or security software reset rules
   - Solution: Run `FIX_FIREWALL.bat` again

---

## Step-by-Step Fix

### Step 1: Check Current Status
```cmd
cd secureai-guardian
CHECK_MOBILE_ACCESS.bat
```

### Step 2: Fix Firewall (if needed)
Right-click `FIX_FIREWALL.bat` → "Run as Administrator"

### Step 3: Restart Servers
```cmd
ROBUST_START_SERVERS.bat
```

### Step 4: Verify Network URL
Look in frontend terminal for:
```
➜  Network: http://10.0.0.168:3000/
```

### Step 5: Test on Mobile
Use the Network URL from Step 4 on your phone.

---

## Configuration Files

### `vite.config.ts`
```typescript
server: {
  host: '0.0.0.0',  // ✅ Must be 0.0.0.0 for network access
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:5000',  // ✅ localhost is correct here
      changeOrigin: true,
    }
  }
}
```

### `api.py`
```python
app.run(debug=True, host='0.0.0.0', port=5000)  # ✅ Must be 0.0.0.0
```

### `services/apiService.ts`
```typescript
const API_BASE_URL = import.meta.env.DEV 
  ? ''  // ✅ Empty string = relative URL = goes through Vite proxy
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000');
```

---

## Verification Checklist

- [ ] Backend running on `0.0.0.0:5000`
- [ ] Frontend running on `0.0.0.0:3000`
- [ ] Vite shows "Network" URL in output
- [ ] Firewall allows ports 3000 and 5000
- [ ] Phone and laptop on same Wi-Fi network
- [ ] Using Network IP (not localhost) on phone
- [ ] API service uses relative URLs in dev mode

---

## Still Not Working?

1. **Check network connectivity:**
   - Ping phone from laptop: `ping <phone-ip>`
   - Ping laptop from phone (if possible)

2. **Check for VPN:**
   - VPN might isolate devices
   - Disable VPN and try again

3. **Check router settings:**
   - Some routers block device-to-device communication
   - Check "AP Isolation" or "Client Isolation" settings

4. **Try different network:**
   - Test on different Wi-Fi network
   - Or use mobile hotspot

---

## Quick Commands

**Get Network IP:**
```cmd
ipconfig | findstr IPv4
```

**Check if ports are listening:**
```cmd
netstat -an | findstr ":3000"
netstat -an | findstr ":5000"
```

**Test backend from phone:**
Open in phone browser: `http://<your-ip>:5000/api/health`

---

**Need more help?** Run `CHECK_MOBILE_ACCESS.bat` and share the output!

