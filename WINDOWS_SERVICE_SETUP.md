# Windows Service Setup Guide

This guide explains how to set up SecureAI Guardian to run automatically as Windows services, so the application starts whenever your computer boots up.

## Overview

Instead of manually running `START_SERVERS.bat` every time you start your computer, you can configure Windows services that will:
- ✅ Start automatically when Windows boots
- ✅ Restart automatically if the service crashes
- ✅ Run in the background without visible windows
- ✅ Log output to files for troubleshooting

## Prerequisites

1. **Administrator Access**: You need to run the setup script as Administrator
2. **Python**: Installed and accessible (preferably in a virtual environment)
3. **Node.js**: Installed for the frontend service (optional)
4. **NSSM**: Will be downloaded automatically if not present

## Quick Setup

### Option 1: Automated Setup (Recommended)

1. **Right-click** on `setup-windows-services.bat`
2. Select **"Run as Administrator"**
3. Follow the prompts
4. The script will:
   - Download NSSM if needed
   - Create Windows services for backend and frontend
   - Configure automatic startup
   - Start the services

### Option 2: Manual PowerShell Setup

1. Open **PowerShell as Administrator**
2. Navigate to the project directory:
   ```powershell
   cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
   ```
3. Run the setup script:
   ```powershell
   .\setup-windows-services.ps1
   ```

## What Gets Created

The setup script creates two Windows services:

1. **SecureAI-Backend**
   - Runs `api.py` using your Python environment
   - Starts automatically on boot
   - Logs to `logs\backend-stdout.log` and `logs\backend-stderr.log`

2. **SecureAI-Frontend** (if Node.js is available)
   - Runs `npm run dev` in the `secureai-guardian` directory
   - Starts automatically on boot
   - Logs to `logs\frontend-stdout.log` and `logs\frontend-stderr.log`

## Managing Services

### Using PowerShell (Recommended)

```powershell
# Start services
Start-Service SecureAI-Backend
Start-Service SecureAI-Frontend

# Stop services
Stop-Service SecureAI-Backend
Stop-Service SecureAI-Frontend

# Check status
Get-Service SecureAI-Backend
Get-Service SecureAI-Frontend

# View logs
Get-Content logs\backend-stdout.log -Tail 50
Get-Content logs\frontend-stdout.log -Tail 50
```

### Using Windows Services Manager

1. Press `Win + R`
2. Type `services.msc` and press Enter
3. Find "SecureAI-Backend" and "SecureAI-Frontend"
4. Right-click to Start, Stop, Restart, or view Properties

### Using Command Prompt

```cmd
REM Start services
net start SecureAI-Backend
net start SecureAI-Frontend

REM Stop services
net stop SecureAI-Backend
net stop SecureAI-Frontend

REM Check status
sc query SecureAI-Backend
sc query SecureAI-Frontend
```

## Service Configuration

### Automatic Startup

Services are configured to start automatically (`SERVICE_AUTO_START`). This means:
- They start when Windows boots
- They restart automatically if they crash
- They don't require user login

### Logging

Logs are automatically rotated:
- New log file created daily
- Logs rotate when they reach 10MB
- Old logs are kept for troubleshooting

Log locations:
- Backend: `logs\backend-stdout.log` and `logs\backend-stderr.log`
- Frontend: `logs\frontend-stdout.log` and `logs\frontend-stderr.log`

### Environment Variables

If a `.env` file exists in the project root, environment variables are automatically loaded into the backend service.

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```powershell
   Get-Content logs\backend-stderr.log -Tail 50
   ```

2. **Check service status**:
   ```powershell
   Get-Service SecureAI-Backend
   ```

3. **Check Windows Event Viewer**:
   - Press `Win + X` → Event Viewer
   - Navigate to Windows Logs → Application
   - Look for errors related to "SecureAI"

### Service Starts But App Doesn't Work

1. **Verify Python/Node paths are correct**:
   - The service uses the Python/Node found during setup
   - If you moved or reinstalled Python/Node, you may need to rerun setup

2. **Check if ports are in use**:
   ```powershell
   netstat -ano | findstr ":5000"
   netstat -ano | findstr ":3000"
   ```

3. **Test manually**:
   - Stop the services
   - Run `START_SERVERS.bat` manually to see error messages

### Removing Services

If you want to remove the services and go back to manual startup:

```powershell
# Run as Administrator
Stop-Service SecureAI-Backend -ErrorAction SilentlyContinue
Stop-Service SecureAI-Frontend -ErrorAction SilentlyContinue

# If NSSM is in PATH
nssm remove SecureAI-Backend confirm
nssm remove SecureAI-Frontend confirm

# Or use the full path to NSSM
# C:\path\to\nssm.exe remove SecureAI-Backend confirm
```

## Alternative: Task Scheduler (Simpler but Less Robust)

If you prefer not to use NSSM, you can use Windows Task Scheduler:

1. Open **Task Scheduler** (`Win + R` → `taskschd.msc`)
2. Create Basic Task:
   - Name: "SecureAI Backend"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: Path to your Python executable
   - Arguments: `api.py`
   - Start in: Project directory
3. Repeat for frontend with `npm run dev`

**Note**: Task Scheduler is simpler but doesn't provide automatic restart on failure or as robust logging as NSSM.

## Production Considerations

For a production Windows server, consider:

1. **Use Gunicorn instead of Flask dev server**:
   - Modify the service to run: `gunicorn -c gunicorn_config.py api:app`
   - This provides better performance and stability

2. **Build frontend for production**:
   - Run `npm run build` in `secureai-guardian`
   - Serve static files with Nginx or IIS instead of Vite dev server

3. **Use IIS or Nginx as reverse proxy**:
   - Provides better security, SSL termination, and load balancing

4. **Set up proper monitoring**:
   - Use Windows Performance Monitor
   - Integrate with monitoring tools (e.g., Sentry, which is already configured)

## Next Steps

After setting up services:

1. ✅ Reboot your computer to verify services start automatically
2. ✅ Check that the app is accessible at `http://localhost:3000`
3. ✅ Monitor logs for the first few days to ensure stability
4. ✅ Consider setting up production deployment (see `PRODUCTION_SETUP_COMPLETE.md`)

## Support

If you encounter issues:

1. Check the logs in `logs\` directory
2. Review Windows Event Viewer for system errors
3. Verify Python and Node.js are correctly installed
4. Ensure all dependencies are installed (`pip install -r requirements.txt`)

---

**Note**: The services will continue running even when you're not logged in, which is perfect for a server or always-on computer. If you want the services to only run when you're logged in, you can change the service login account in the service properties.

