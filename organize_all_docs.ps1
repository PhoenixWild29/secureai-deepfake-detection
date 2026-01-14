# PowerShell script to organize ALL remaining documentation files

Write-Host "Organizing ALL remaining documentation files..." -ForegroundColor Green

# Create additional directories if needed
New-Item -ItemType Directory -Force -Path "docs\troubleshooting", "docs\guides", "docs\testing", "archive\old-setup", "archive\completed" | Out-Null

# Function to move files safely
function Move-DocFile {
    param($file, $destination)
    if (Test-Path $file) {
        git mv $file $destination 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Moved $file to $destination" -ForegroundColor Yellow
        }
    }
}

# Troubleshooting docs
$troubleshootingPatterns = @("FIX_*.md", "TROUBLESHOOT*.md", "DEBUG*.md", "*ERROR*.md", "*ISSUE*.md")
foreach ($pattern in $troubleshootingPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*V13*" -and $_.Name -notlike "*CUDA*" -and $_.Name -notlike "*LAANET*" }
    foreach ($file in $files) {
        Move-DocFile $file.Name "docs\troubleshooting\"
    }
}

# Testing docs
$testingPatterns = @("TEST_*.md", "RUN_*.md", "*TEST*.md", "VERIFY*.md", "CHECK*.md")
foreach ($pattern in $testingPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*V13*" }
    foreach ($file in $files) {
        Move-DocFile $file.Name "docs\testing\"
    }
}

# Guide docs
$guidePatterns = @("*GUIDE*.md", "*HOW*.md", "*QUICK*.md", "*STEP*.md", "*TUTORIAL*.md")
foreach ($pattern in $guidePatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { 
        $_.Name -notlike "*V13*" -and 
        $_.Name -notlike "*LAANET*" -and
        $_.Name -notlike "*SETUP*" -and
        $_.Name -notlike "*DEPLOYMENT*" -and
        $_.Name -notlike "*HTTPS*" -and
        $_.Name -notlike "*DNS*" -and
        $_.Name -notlike "*POSTGRESQL*" -and
        $_.Name -notlike "*S3*" -and
        $_.Name -notlike "*REDIS*"
    }
    foreach ($file in $files) {
        Move-DocFile $file.Name "docs\guides\"
    }
}

# Status/Summary docs (archive completed ones)
$statusPatterns = @("*STATUS*.md", "*SUMMARY*.md", "*COMPLETE*.md", "*FINAL*.md", "*READY*.md")
foreach ($pattern in $statusPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { 
        $_.Name -notlike "*V13*" -and 
        $_.Name -notlike "*CUDA*" -and
        $_.Name -notlike "*LAANET*" -and
        $_.Name -notlike "*POSTGRESQL*" -and
        $_.Name -notlike "*S3*" -and
        $_.Name -notlike "*REDIS*" -and
        $_.Name -notlike "*DEPLOYMENT*"
    }
    foreach ($file in $files) {
        Move-DocFile $file.Name "archive\completed\"
    }
}

# Old setup docs
$oldSetupPatterns = @("STEP_*.md", "*INITIAL*.md")
foreach ($pattern in $oldSetupPatterns) {
    $files = Get-ChildItem -Filter $pattern -ErrorAction SilentlyContinue | Where-Object { 
        $_.Name -notlike "*STEP_2*" -and
        $_.Name -notlike "*STEP_BY_STEP*"
    }
    foreach ($file in $files) {
        Move-DocFile $file.Name "archive\old-setup\"
    }
}

# Move specific remaining files
$specificMoves = @{
    "API_Documentation.md" = "docs\guides\"
    "Technical_Documentation.md" = "docs\guides\"
    "README.md" = "."  # Keep in root
    "START_HERE.md" = "docs\setup\"  # If still exists
    "GETTING_STARTED.md" = "docs\setup\"  # If still exists
    "QUICK_REFERENCE.md" = "docs\guides\"
    "USAGE_GUIDE.md" = "docs\guides\"
    "HOW_DEEPFAKE_DETECTION_WORKS.md" = "docs\guides\"
    "HOW_LOGIN_WORKS.md" = "docs\guides\"
    "HOW_TO_TEST.md" = "docs\testing\"
    "HOW_TO_OPEN_ENV_FILE.md" = "docs\guides\"
    "RUN_ALL_TESTS.md" = "docs\testing\"
    "TEST_ULTIMATE_ENSEMBLE.md" = "docs\testing\"
    "TEST_ENSEMBLE_INSTRUCTIONS.md" = "docs\testing\"
    "TEST_RESULTS_ANALYSIS.md" = "docs\testing\"
    "TEST_EVERYTHING.md" = "docs\testing\"
    "VERIFY_MODEL_TRAINING.md" = "docs\testing\"
    "RUN_RESNET50_VERIFICATION.md" = "docs\testing\"
    "RUN_ENSEMBLE_TEST.md" = "docs\testing\"
    "RUN_ENSEMBLE_TEST_FULL_OUTPUT.md" = "docs\testing\"
    "RUN_VERIFICATION_ON_SERVER.md" = "docs\testing\"
    "RUN_STEPS_1_AND_2.md" = "docs\testing\"
    "STEP_1_VERIFY_RESNET.md" = "docs\testing\"
    "STEP_1_RESULTS_SUMMARY.md" = "docs\testing\"
    "STEP_4_FIX_VIDEOS.md" = "docs\troubleshooting\"
    "FIX_DATABASE_PASSWORD.md" = "docs\troubleshooting\"
    "FIX_DISK_SPACE.md" = "docs\troubleshooting\"
    "FIX_GENERATOR_ERROR_COMPLETE.md" = "archive\completed\"
    "FIX_INSTALLATION_ISSUES.md" = "docs\troubleshooting\"
    "FIX_PGADMIN_SQL_ERROR.md" = "docs\troubleshooting\"
    "FIX_SECURITY_ISSUES.md" = "docs\troubleshooting\"
    "FIX_SITE_DOWN.md" = "docs\troubleshooting\"
    "FIX_UPLOADS_MOUNT.md" = "docs\troubleshooting\"
    "FIX_VIDEO_PATHS.md" = "docs\troubleshooting\"
    "FIX_YT_DLP_VENV.md" = "docs\troubleshooting\"
    "RESTART_BACKEND_GUIDE.md" = "docs\troubleshooting\"
    "RESTORE_NGINX.md" = "docs\troubleshooting\"
    "START_NGINX_NOW.md" = "docs\troubleshooting\"
    "TROUBLESHOOT_SITE_DOWN.md" = "docs\troubleshooting\"
    "TROUBLESHOOTING_CONSOLE.md" = "docs\troubleshooting\"
    "CHECK_VIDEOS_IN_CONTAINER.md" = "docs\troubleshooting\"
    "LONG_TERM_VIDEO_MANAGEMENT.md" = "docs\guides\"
    "ALTERNATIVE_APPROACHES.md" = "archive\old-setup\"
    "BEST_MODEL_ON_PLANET.md" = "docs\models\"  # If still in root
    "BEST_MODEL_WITHOUT_LAANET.md" = "docs\models\"  # If still in root
    "CHECK_README_FOR_LINKS.md" = "archive\laa-net\"  # If still in root
    "TRY_DROPBOX_LINK_FIXES.md" = "archive\laa-net\"  # If still in root
}

foreach ($file in $specificMoves.Keys) {
    Move-DocFile $file $specificMoves[$file]
}

# Move remaining test scripts
$testScripts = Get-ChildItem -Filter "test_*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*v13*" -and $_.Name -notlike "*convnext*" -and $_.Name -notlike "*vit_large*" -and $_.Name -notlike "*ultimate_ensemble*" -and $_.Name -notlike "*comprehensive*" }
foreach ($file in $testScripts) {
    Move-DocFile $file.Name "scripts\test\"
}

# Move remaining check/diagnostic scripts
$diagScripts = Get-ChildItem -Filter "check_*.py", "diagnose_*.py", "fix_*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*v13*" }
foreach ($file in $diagScripts) {
    Move-DocFile $file.Name "scripts\diagnostic\"
}

# Move remaining shell scripts
$shellScripts = Get-ChildItem -Filter "*.sh" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*deploy*" -and $_.Name -notlike "*setup*" -and $_.Name -notlike "*test_v13*" }
foreach ($file in $shellScripts) {
    Move-DocFile $file.Name "scripts\deployment\"
}

# Move .txt documentation files
$txtDocs = Get-ChildItem -Filter "*.txt" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "requirements*" -and $_.Name -notlike "*.bat" }
foreach ($file in $txtDocs) {
    Move-DocFile $file.Name "docs\guides\"
}

Write-Host "`nOrganization complete! Remaining .md files in root:" -ForegroundColor Green
Get-ChildItem -Filter "*.md" -ErrorAction SilentlyContinue | Select-Object Name
