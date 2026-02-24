# 🐳 DigitalOcean Server Setup - Visual Guide

**Step-by-step with screenshots descriptions for creating your first server**

## 📸 Step-by-Step with Descriptions

### Step 1: Create Account

1. Go to **digitalocean.com**
2. Click **"Sign Up"** (top right corner)
3. Enter your email and create password
4. Verify your email (check inbox)

### Step 2: Add Payment

1. After login, you'll see the dashboard
2. Click **"Billing"** in left sidebar
3. Click **"Add Payment Method"**
4. Enter credit card or PayPal
5. **Note**: You won't be charged until you create a server

### Step 3: Create Droplet (Server)

1. Click the big **"Create"** button (top right, usually green/blue)
2. Select **"Droplets"** from dropdown

### Step 4: Choose Configuration

**You'll see several sections:**

#### A. Choose a Region
- **What to pick**: Closest to you
- **Options**: New York, San Francisco, Amsterdam, etc.
- **Why**: Lower latency = faster connection

#### B. Choose an Image
- **Click**: "Ubuntu" tab
- **Select**: **Ubuntu 22.04 (LTS)** or **24.04 (LTS)**
- **Important**: Must be Ubuntu, not Debian or other!

#### C. Choose a Plan
- **Select**: "Regular Intel with SSD" (Basic plan)
- **Size Options**:
  - **$12/month**: 2GB RAM, 1 vCPU (minimum)
  - **$24/month**: 4GB RAM, 2 vCPU ⭐ **RECOMMENDED**
  - **$48/month**: 8GB RAM, 4 vCPU (if budget allows)

#### D. Authentication
- **Option 1: SSH Keys** (if you have them)
  - Click "New SSH Key"
  - Paste your public key
- **Option 2: Password** (easier for beginners) ⭐
  - Click "Password"
  - Enter a strong password
  - **SAVE THIS PASSWORD!** You'll need it to log in

#### E. Finalize
- **Hostname**: Leave default or name it "secureai"
- **Backups**: Skip (costs extra)
- **Monitoring**: Optional (free)

### Step 5: Create!

1. Scroll down
2. Click **"Create Droplet"** button
3. Wait 1-2 minutes (you'll see progress)

### Step 6: Get Your IP Address

1. After creation, you'll see your new droplet
2. **Copy the IP address** (looks like numbers: `157.230.123.45`)
3. **Save this IP!** You'll need it

---

## 🔑 Connect to Your Server

### On Windows (PowerShell):

1. **Open PowerShell**
   - Press `Win + X`
   - Select "Windows PowerShell" or "Terminal"

2. **Type this command** (replace with YOUR IP):
   ```powershell
   ssh root@157.230.123.45
   ```

3. **First time?** You'll see:
   ```
   The authenticity of host '157.230.123.45' can't be established.
   Are you sure you want to continue connecting (yes/no/[fingerprint])?
   ```
   Type: **`yes`** and press Enter

4. **Enter password**:
   - Type your password (won't show as you type - that's normal!)
   - Press Enter

5. **Success!** You should see:
   ```
   root@secureai:~#
   ```
   This means you're connected! 🎉

---

## ✅ Test Your Connection

Once connected, try these commands:

```bash
# See where you are
pwd
# Should show: /root

# Check system info
uname -a
# Should show Linux information

# Check Ubuntu version
lsb_release -a
# Should show Ubuntu 22.04 or 24.04
```

---

## 🎯 What You Should See

**In DigitalOcean Dashboard:**
- Your droplet listed
- Status: "Active" (green)
- IP address visible

**In Your Terminal (after SSH):**
- Prompt showing: `root@your-server-name:~#`
- You can type commands and they work

---

## 🆘 Common Issues

### Issue: "ssh: command not found"
**Solution**: Use PowerShell or install Git Bash

### Issue: "Connection refused"
**Solutions**:
- Wait 2-3 minutes after creating droplet
- Check IP address is correct
- Make sure droplet shows "Active" in dashboard

### Issue: "Permission denied"
**Solutions**:
- Check password is correct
- Try resetting password in DigitalOcean dashboard
- Make sure you're using `root` as username

### Issue: Can't remember password
**Solution**: 
1. Go to DigitalOcean dashboard
2. Click your droplet
3. Click "Access" tab
4. Click "Reset Root Password"
5. Check email for new password

---

## 📋 Quick Checklist

- [ ] DigitalOcean account created
- [ ] Payment method added
- [ ] Droplet created (Ubuntu 22.04 or 24.04)
- [ ] IP address copied
- [ ] Password saved
- [ ] Successfully connected via SSH
- [ ] Can run commands on server

---

## 🚀 Next: Install Docker

Once you're connected and can run commands, install Docker:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify
docker --version
docker compose version
```

Then you're ready to deploy! See `GET_STARTED_DEPLOYMENT.md`

---

## 💡 Pro Tips

1. **Save your IP address** in a text file
2. **Save your password** in a password manager
3. **Take a screenshot** of your droplet in DigitalOcean (shows IP)
4. **Test connection** before moving to next steps
5. **Keep terminal open** - you'll need it for deployment

---

**You're all set! Once you can connect to your server, you're ready to deploy your app!** 🎉

