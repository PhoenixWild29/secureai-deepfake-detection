# PowerShell script to organize documentation files

# Create directories
New-Item -ItemType Directory -Force -Path "docs\deployment", "docs\setup", "docs\v13", "docs\troubleshooting", "docs\models", "docs\infrastructure" | Out-Null
New-Item -ItemType Directory -Force -Path "archive\v13", "archive\laa-net", "archive\cuda", "archive\old-setup" | Out-Null
New-Item -ItemType Directory -Force -Path "scripts\test", "scripts\diagnostic", "scripts\deployment" | Out-Null

Write-Host "Created directory structure" -ForegroundColor Green

# Move V13 current docs
$v13Current = @("V13_SUCCESS_SUMMARY.md", "UPGRADE_DIGITALOCEAN_RAM.md", "V13_ROOT_CAUSE_ANALYSIS.md")
foreach ($file in $v13Current) {
    if (Test-Path $file) {
        git mv $file "docs\v13\" 2>$null
        Write-Host "Moved $file to docs/v13/" -ForegroundColor Yellow
    }
}

# Move model docs
$modelDocs = @("INSTALL_BEST_MODELS.md", "QUICK_START_BEST_MODELS.md", "BUILD_BEST_MODEL_PLAN.md", "ULTIMATE_MODEL_IMPLEMENTATION_PLAN.md", "BEST_MODEL_ON_PLANET.md", "BEST_MODEL_WITHOUT_LAANET.md")
foreach ($file in $modelDocs) {
    if (Test-Path $file) {
        git mv $file "docs\models\" 2>$null
        Write-Host "Moved $file to docs/models/" -ForegroundColor Yellow
    }
}

# Move deployment docs
$deploymentPatterns = @("DEPLOYMENT*.md", "QUICK_DEPLOY*.md", "PRODUCTION_DEPLOYMENT*.md", "DIGITALOCEAN_SETUP_GUIDE.md", "CREATE_CLOUD_SERVER.md", "DOCKER_QUICK_START.md", "QUICK_DOCKER_DEPLOY.md", "POWER_OFF_DROPLET.md")
foreach ($pattern in $deploymentPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "docs\deployment\" 2>$null
        Write-Host "Moved $($file.Name) to docs/deployment/" -ForegroundColor Yellow
    }
}

# Move setup docs
$setupPatterns = @("SETUP_*.md", "QUICK_SETUP_*.md", "STEP_BY_STEP_*.md", "GET_STARTED_*.md", "START_HERE.md", "GETTING_STARTED.md")
foreach ($pattern in $setupPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "docs\setup\" 2>$null
        Write-Host "Moved $($file.Name) to docs/setup/" -ForegroundColor Yellow
    }
}

# Move infrastructure docs
$infraPatterns = @("S3_*.md", "REDIS_*.md", "POSTGRESQL_*.md", "HTTPS_SETUP_*.md", "SUBDOMAIN_SETUP_*.md", "*DNS_SETUP*.md", "QUICK_HTTPS_SETUP.md")
foreach ($pattern in $infraPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "docs\infrastructure\" 2>$null
        Write-Host "Moved $($file.Name) to docs/infrastructure/" -ForegroundColor Yellow
    }
}

# Archive V13 troubleshooting
$v13ArchivePatterns = @("FIX_V13_*.md", "DEBUG_V13_*.md", "GET_V13_WORKING.md", "V13_DOWNLOAD_*.md", "V13_PROGRESS_UPDATE.md", "TEST_V13_FIXED.md", "FIX_BACKBONE_NAMES.md", "FIX_VIT_LARGE_HANG_FINAL.md", "FIX_V13_THREADING_ISSUE.md")
foreach ($pattern in $v13ArchivePatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "archive\v13\" 2>$null
        Write-Host "Archived $($file.Name) to archive/v13/" -ForegroundColor Cyan
    }
}

# Archive LAA-Net
$laaNetPatterns = @("*LAANET*.md", "DOWNLOAD_LAANET_*.md", "FIND_LAANET_*.md", "GET_LAANET_*.md", "STEP_2_*.md", "EXTRACT_LAANET_*.md", "MANUAL_DOWNLOAD_LAANET.md", "contact_laa_net_maintainers.md", "FINAL_LAANET_DECISION.md", "NEXT_STEPS_LAANET.md")
foreach ($pattern in $laaNetPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "archive\laa-net\" 2>$null
        Write-Host "Archived $($file.Name) to archive/laa-net/" -ForegroundColor Cyan
    }
}

# Archive CUDA
$cudaPatterns = @("CUDA_*.md", "FIX_CUDA_*.md", "APPLY_CUDA_FIX_*.md", "FINAL_CUDA_FIX.md", "SUPPRESS_CUDA_ERRORS.md")
foreach ($pattern in $cudaPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "archive\cuda\" 2>$null
        Write-Host "Archived $($file.Name) to archive/cuda/" -ForegroundColor Cyan
    }
}

# Move test scripts
$testPatterns = @("test_v13_*.py", "test_convnext_*.py", "test_vit_large_*.py", "test_ultimate_ensemble.py", "test_comprehensive.py")
foreach ($pattern in $testPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "scripts\test\" 2>$null
        Write-Host "Moved $($file.Name) to scripts/test/" -ForegroundColor Yellow
    }
}

# Move diagnostic scripts
$diagPatterns = @("check_v13_*.py", "diagnose_*.py", "fix_v13_*.py", "CHECK_MODEL_STATUS.py")
foreach ($pattern in $diagPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "scripts\diagnostic\" 2>$null
        Write-Host "Moved $($file.Name) to scripts/diagnostic/" -ForegroundColor Yellow
    }
}

# Move deployment scripts
$deployPatterns = @("test_v13_after_upgrade.sh", "deploy*.sh", "setup-*.sh", "quick-deploy*.sh")
foreach ($pattern in $deployPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        git mv $file.Name "scripts\deployment\" 2>$null
        Write-Host "Moved $($file.Name) to scripts/deployment/" -ForegroundColor Yellow
    }
}

Write-Host "`nDocumentation organization complete!" -ForegroundColor Green
Write-Host "Run 'git status' to see all changes" -ForegroundColor Cyan
