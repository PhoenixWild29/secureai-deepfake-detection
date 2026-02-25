# PowerShell script to set up SecureAI Guardian as Windows Services
# This will make the backend and frontend run automatically on Windows startup
# Run this script as Administrator

param(
    [string]$AppPath = $PSScriptRoot,
    [string]$FrontendPath = "$PSScriptRoot\secureai-guardian"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SecureAI Guardian - Windows Service Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if NSSM is available
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    Write-Host "NSSM (Non-Sucking Service Manager) is required but not found." -ForegroundColor Yellow
    Write-Host "Downloading NSSM..." -ForegroundColor Yellow
    
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmDir = "$env:TEMP\nssm"
    
    try {
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath $nssmDir -Force
        $nssmExe = Get-ChildItem -Path $nssmDir -Filter "nssm.exe" -Recurse | Select-Object -First 1
        if ($nssmExe) {
            $nssmPath = $nssmExe.FullName
            Write-Host "NSSM downloaded successfully" -ForegroundColor Green
        } else {
            throw "NSSM executable not found in downloaded archive"
        }
    } catch {
        Write-Host "Failed to download NSSM: $_" -ForegroundColor Red
        Write-Host "Please download NSSM manually from https://nssm.cc/download" -ForegroundColor Yellow
        Write-Host "Extract it and add the 64-bit or 32-bit folder to your PATH" -ForegroundColor Yellow
        exit 1
    }
} else {
    $nssmPath = $nssmPath.Source
}

Write-Host ""
Write-Host "NSSM found at: $nssmPath" -ForegroundColor Green
Write-Host ""

# Find Python executable
$pythonExe = $null
if (Test-Path "$AppPath\.venv\Scripts\python.exe") {
    $pythonExe = "$AppPath\.venv\Scripts\python.exe"
    Write-Host "Found Python in virtual environment: $pythonExe" -ForegroundColor Green
} elseif (Test-Path "$AppPath\venv\Scripts\python.exe") {
    $pythonExe = "$AppPath\venv\Scripts\python.exe"
    Write-Host "Found Python in virtual environment: $pythonExe" -ForegroundColor Green
} else {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        Write-Host "Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Found Python: $pythonExe" -ForegroundColor Green
}

# Find Node.js executable
$nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $nodeExe) {
    Write-Host "WARNING: Node.js not found!" -ForegroundColor Yellow
    Write-Host "Frontend service will not be created" -ForegroundColor Yellow
    $createFrontend = $false
} else {
    Write-Host "Found Node.js: $nodeExe" -ForegroundColor Green
    $createFrontend = $true
}

Write-Host ""
Write-Host "Application paths:" -ForegroundColor Cyan
Write-Host "  Backend:  $AppPath" -ForegroundColor White
Write-Host "  Frontend: $FrontendPath" -ForegroundColor White
Write-Host ""

# Remove existing services if they exist
Write-Host "Checking for existing services..." -ForegroundColor Yellow
$backendService = Get-Service -Name "SecureAI-Backend" -ErrorAction SilentlyContinue
$frontendService = Get-Service -Name "SecureAI-Frontend" -ErrorAction SilentlyContinue

if ($backendService) {
    Write-Host "Removing existing SecureAI-Backend service..." -ForegroundColor Yellow
    Stop-Service -Name "SecureAI-Backend" -ErrorAction SilentlyContinue
    & $nssmPath remove "SecureAI-Backend" confirm
}

if ($frontendService) {
    Write-Host "Removing existing SecureAI-Frontend service..." -ForegroundColor Yellow
    Stop-Service -Name "SecureAI-Frontend" -ErrorAction SilentlyContinue
    & $nssmPath remove "SecureAI-Frontend" confirm
}

Write-Host ""
Write-Host "Creating SecureAI-Backend service..." -ForegroundColor Cyan

# Create backend service
& $nssmPath install "SecureAI-Backend" "$pythonExe" "$AppPath\api.py"
& $nssmPath set "SecureAI-Backend" AppDirectory "$AppPath"
& $nssmPath set "SecureAI-Backend" DisplayName "SecureAI Guardian Backend"
& $nssmPath set "SecureAI-Backend" Description "SecureAI DeepFake Detection Backend API Server"
& $nssmPath set "SecureAI-Backend" Start SERVICE_AUTO_START
& $nssmPath set "SecureAI-Backend" AppStdout "$AppPath\logs\backend-stdout.log"
& $nssmPath set "SecureAI-Backend" AppStderr "$AppPath\logs\backend-stderr.log"
& $nssmPath set "SecureAI-Backend" AppRotateFiles 1
& $nssmPath set "SecureAI-Backend" AppRotateOnline 1
& $nssmPath set "SecureAI-Backend" AppRotateSeconds 86400
& $nssmPath set "SecureAI-Backend" AppRotateBytes 10485760

# Set environment variables
$envFile = "$AppPath\.env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from .env file..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            & $nssmPath set "SecureAI-Backend" AppEnvironmentExtra "$key=$value"
        }
    }
}

Write-Host "Backend service created successfully!" -ForegroundColor Green

if ($createFrontend) {
    Write-Host ""
    Write-Host "Creating SecureAI-Frontend service..." -ForegroundColor Cyan
    
    # Find npm (usually in same directory as node.exe)
    $nodeDir = Split-Path -Parent $nodeExe
    $npmPath = Join-Path $nodeDir "npm.cmd"
    if (-not (Test-Path $npmPath)) {
        $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
    }
    
    if (-not $npmPath) {
        Write-Host "WARNING: npm not found, skipping frontend service" -ForegroundColor Yellow
        $createFrontend = $false
    } else {
        # Create frontend service - use cmd.exe to run npm
        $cmdExe = "$env:SystemRoot\System32\cmd.exe"
        & $nssmPath install "SecureAI-Frontend" "$cmdExe" "/c `"$npmPath run dev`""
        & $nssmPath set "SecureAI-Frontend" AppDirectory "$FrontendPath"
    & $nssmPath set "SecureAI-Frontend" DisplayName "SecureAI Guardian Frontend"
    & $nssmPath set "SecureAI-Frontend" Description "SecureAI DeepFake Detection Frontend Development Server"
    & $nssmPath set "SecureAI-Frontend" Start SERVICE_AUTO_START
    & $nssmPath set "SecureAI-Frontend" AppStdout "$AppPath\logs\frontend-stdout.log"
    & $nssmPath set "SecureAI-Frontend" AppStderr "$AppPath\logs\frontend-stderr.log"
    & $nssmPath set "SecureAI-Frontend" AppRotateFiles 1
    & $nssmPath set "SecureAI-Frontend" AppRotateOnline 1
    & $nssmPath set "SecureAI-Frontend" AppRotateSeconds 86400
    & $nssmPath set "SecureAI-Frontend" AppRotateBytes 10485760
    
        Write-Host "Frontend service created successfully!" -ForegroundColor Green
    }
}

# Create logs directory
$logsDir = "$AppPath\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Host "Created logs directory: $logsDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Service Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services created:" -ForegroundColor Yellow
Write-Host "  - SecureAI-Backend" -ForegroundColor White
if ($createFrontend) {
    Write-Host "  - SecureAI-Frontend" -ForegroundColor White
}
Write-Host ""
Write-Host "Service Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service SecureAI-Backend" -ForegroundColor White
Write-Host "  Stop:    Stop-Service SecureAI-Backend" -ForegroundColor White
Write-Host "  Status:  Get-Service SecureAI-Backend" -ForegroundColor White
Write-Host "  Logs:    Get-Content $logsDir\backend-stdout.log -Tail 50" -ForegroundColor White
Write-Host ""
Write-Host "Or use Services.msc (Windows Services Manager)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting services now..." -ForegroundColor Cyan

Start-Service -Name "SecureAI-Backend" -ErrorAction SilentlyContinue
if ($createFrontend) {
    Start-Service -Name "SecureAI-Frontend" -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
Get-Service -Name "SecureAI-Backend" | Format-Table -AutoSize
if ($createFrontend) {
    Get-Service -Name "SecureAI-Frontend" | Format-Table -AutoSize
}

Write-Host ""
Write-Host "✅ Services are now configured to start automatically on Windows boot!" -ForegroundColor Green
Write-Host ""

