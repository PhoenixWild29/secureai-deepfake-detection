# 🔧 Fix Mobile Network Access - Quick Guide

## Your Network IP Addresses
Based on your system, you have:
- `10.5.0.2` (likely VPN/virtual network)
- `10.0.0.168` (likely your main Wi-Fi network) ← **Try this one first**

## Quick Fix Steps

### 1. ✅ Check Windows Firewall (Most Common Issue!)

Windows Firewall is likely blocking ports 3000 and 5000.

**Quick Fix - Run PowerShell as Administrator:**
```powershell
New-NetFirewallRule -DisplayName "Vite Dev Server" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Flask Backend" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

**Or manually:**
1. Press `Win + R`, type `wf.msc`, press Enter
2. Click "Inbound Rules" → "New Rule"
3. Select "Port" → Next → "TCP" → Enter `3000` → Next
4. "Allow the connection" → Next → Next → Next
5. Name: "Vite Dev Server" → Finish
6. Repeat for port `5000` (name: "Flask Backend")

### 2. 🔄 Restart Both Servers

**Stop both servers** (Ctrl+C), then restart:

**Backend:**
```cmd
cd ..
py api.py
```

**Frontend:**
```cmd
cd secureai-guardian
npm run dev
```

### 3. 📱 Use Network IP on Your Phone

**On your phone's browser, try:**
- `http://10.0.0.168:3000` ← Main Wi-Fi IP
- `http://10.5.0.2:3000` ← If first doesn't work

**NOT:** `http://localhost:3000` (won't work on phone!)

### 4. ✅ Verify Vite Shows Network URL

When you start `npm run dev`, you should see:
```
  ➜  Local:   http://localhost:3000/
  ➜  Network: http://10.0.0.168:3000/  ← This line!
```

**If you DON'T see "Network"**, the server isn't binding correctly.

### 5. 🧪 Test Backend from Phone

On your phone, try: `http://10.0.0.168:5000/api/health`

If this works but frontend doesn't → Frontend/Vite issue
If neither works → Firewall/network issue

---

## Configuration Check

### ✅ Vite Config (Already Correct)
Your `vite.config.ts` has:
```typescript
host: '0.0.0.0',  // ✅ Correct!
```

### ✅ Backend Config (Already Correct)
Your `api.py` has:
```python
app.run(debug=True, host='0.0.0.0', port=5000)  // ✅ Correct!
```

---

## Common Issues & Solutions

### Issue 1: "Site can't be reached"
- ✅ **Solution:** Use network IP (`10.0.0.168:3000`) not localhost
- ✅ **Solution:** Check Windows Firewall (Step 1 above)

### Issue 2: Frontend loads but API calls fail
- ✅ **Solution:** Backend also needs firewall rule (port 5000)
- ✅ **Solution:** Update `.env.local` if needed:
  ```
  VITE_API_BASE_URL=http://10.0.0.168:5000
  ```

### Issue 3: Phone and laptop on different networks
- ✅ **Solution:** Both must be on same Wi-Fi network
- ✅ **Solution:** Disable VPN if it isolates devices

---

## Quick Checklist

- [ ] Windows Firewall allows port 3000
- [ ] Windows Firewall allows port 5000
- [ ] Restarted both servers after firewall changes
- [ ] Vite shows "Network" URL in output
- [ ] Using network IP (`10.0.0.168:3000`) on phone
- [ ] Phone and laptop on same Wi-Fi network
- [ ] Tested backend: `http://10.0.0.168:5000/api/health`

---

## Still Not Working?

### Option 1: Check Which IP is Active
Run this to see active connections:
```cmd
netstat -an | findstr "3000"
netstat -an | findstr "5000"
```

### Option 2: Use ngrok (Works from Anywhere)
1. Download: https://ngrok.com/download
2. Run: `ngrok http 3000`
3. Use the HTTPS URL on your phone

---

**Most likely fix: Windows Firewall blocking the ports!** 🔥

Follow Step 1 above to allow ports 3000 and 5000, then restart servers.
