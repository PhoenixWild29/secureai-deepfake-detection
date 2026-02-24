# 📱 Mobile Network Access Troubleshooting

## Problem
The app works on your laptop but shows "site can't be reached" on your mobile phone.

## Quick Fixes

### 1. ✅ Check Vite Server is Running with Network Access

When you start the frontend with `npm run dev`, you should see output like:
```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

**If you DON'T see the "Network" line**, the server might not be binding to `0.0.0.0`.

### 2. 🔍 Get Your Computer's IP Address

**Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" under your active network adapter (usually Wi-Fi or Ethernet).

**Example output:**
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . . : 192.168.1.100
```

### 3. 🌐 Use the Network IP on Your Phone

Instead of `localhost:3000`, use your computer's IP address:
- **On laptop:** `http://localhost:3000` ✅
- **On phone:** `http://192.168.1.100:3000` ✅ (use YOUR IP)

### 4. 🔥 Check Windows Firewall

Windows Firewall might be blocking port 3000.

**Quick Fix:**
1. Press `Win + R`
2. Type `wf.msc` and press Enter
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter port `3000` → Next
6. Select "Allow the connection" → Next
7. Check all profiles → Next
8. Name it "Vite Dev Server" → Finish

**Or use PowerShell (Run as Administrator):**
```powershell
New-NetFirewallRule -DisplayName "Vite Dev Server" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### 5. 🔄 Restart the Dev Server

After checking firewall, restart the frontend server:
```cmd
cd secureai-guardian
npm run dev
```

Make sure you see the "Network" URL in the output.

### 6. 📱 Verify Phone is on Same Network

- Phone and laptop must be on the **same Wi-Fi network**
- Don't use mobile data on your phone
- Don't use a VPN that might isolate devices

### 7. 🧪 Test Backend Access Too

If the frontend loads but API calls fail, check backend network access:

**Backend should also bind to 0.0.0.0:**
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

Then access backend from phone: `http://192.168.1.100:5000/api/health`

---

## Quick Checklist

- [ ] Vite shows "Network" URL when starting
- [ ] Using network IP (192.168.x.x) not localhost on phone
- [ ] Windows Firewall allows port 3000
- [ ] Phone and laptop on same Wi-Fi network
- [ ] Backend also accessible from network (if needed)
- [ ] Restarted dev server after changes

---

## Still Not Working?

### Check Vite Config
Make sure `vite.config.ts` has:
```typescript
server: {
  port: 3000,
  host: '0.0.0.0',  // ← This is important!
}
```

### Check Backend Config
Make sure `api.py` has:
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### Test Connection from Phone
On your phone's browser, try:
- `http://YOUR_IP:3000` (frontend)
- `http://YOUR_IP:5000/api/health` (backend health check)

If backend health check works but frontend doesn't, it's a Vite/frontend issue.
If neither works, it's a firewall/network issue.

---

## Alternative: Use ngrok (Tunneling)

If you can't get local network access working, use ngrok:

1. **Install ngrok:** https://ngrok.com/download
2. **Start your frontend:** `npm run dev` (on localhost:3000)
3. **Create tunnel:**
   ```cmd
   ngrok http 3000
   ```
4. **Use the ngrok URL** on your phone (works from anywhere!)

Example ngrok output:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:3000
```

Use `https://abc123.ngrok.io` on your phone.

