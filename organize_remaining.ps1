# Organize ALL remaining files - no new docs, just organize

Write-Host "Organizing ALL remaining files..." -ForegroundColor Green

# Create additional directories
New-Item -ItemType Directory -Force -Path "docs\guides", "docs\testing", "docs\compliance", "docs\production", "scripts\setup", "scripts\utilities" | Out-Null

# Function to move files
function Move-File {
    param($file, $dest)
    if (Test-Path $file) {
        git mv $file $dest 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Host "Moved $file" -ForegroundColor Yellow }
    }
}

# Remaining .md files to organize
$remainingDocs = @{
    # Guides
    "ADD_SENTRY_TO_ENV.md" = "docs\guides\"
    "AISTORE_SETUP_GUIDE.md" = "docs\guides\"
    "COMPLETE_DEPLOYMENT_GUIDE.md" = "docs\deployment\"
    "CONFIGURE_S3_ENV.md" = "docs\infrastructure\"
    "CREATE_PR_INSTRUCTIONS.md" = "docs\guides\"
    "CREATE_S3_BUCKETS.md" = "docs\infrastructure\"
    "DEEPFAKE_VS_MORPHEUS_EXPLAINED.md" = "docs\guides\"
    "ENSEMBLE_DETECTOR_SETUP.md" = "docs\models\"
    "FORCE_REBUILD_JETSON_FIX.md" = "docs\troubleshooting\"
    "INSTALL_AISTORE.md" = "docs\guides\"
    "INSTALL_YT_DLP.md" = "docs\guides\"
    "MORPHEUS_SETUP_GUIDE.md" = "docs\guides\"
    "OPTIONAL_SERVICES_SETUP.md" = "docs\setup\"
    "Performance_Validation_Framework.md" = "docs\testing\"
    "Production_Infrastructure.md" = "docs\production\"
    "PRODUCTION_READINESS_PHASE2_PROGRESS.md" = "archive\completed\"
    "PRODUCTION_READINESS_ROADMAP.md" = "docs\production\"
    "PR_DESCRIPTION.md" = "docs\guides\"
    "QUICK_PGADMIN_SETUP.md" = "docs\infrastructure\"
    "Regulatory_Compliance_Framework.md" = "docs\compliance\"
    "Security_Audit_Framework.md" = "docs\compliance\"
    "SECURITY_FIXES_APPLIED.md" = "archive\completed\"
    "SENTRY_QUICK_SETUP.md" = "docs\infrastructure\"
    "SOLANA_SETUP_GUIDE.md" = "docs\guides\"
    "SOLANA_SETUP_WINDOWS.md" = "docs\guides\"
    "STEP2_POSTGRESQL_SETUP.md" = "docs\infrastructure\"
    "STEP3_AWS_S3_SETUP.md" = "docs\infrastructure\"
    "STEP4_SENTRY_SETUP.md" = "docs\infrastructure\"
    "UAT_Compliance_Officers.md" = "docs\testing\"
    "UAT_Content_Moderators.md" = "docs\testing\"
    "UAT_Framework.md" = "docs\testing\"
    "UAT_Security_Professionals.md" = "docs\testing\"
    "UPDATE_JETSON_MESSAGE.md" = "docs\troubleshooting\"
    "URL_MODE_IMPLEMENTATION.md" = "docs\guides\"
    "V13_FIX_COMPLETE.md" = "archive\v13\"
    "VERIFICATION_REPORT.md" = "docs\testing\"
    "WINDOWS_SERVICE_SETUP.md" = "docs\setup\"
    "YT_DLP_FIX.md" = "docs\troubleshooting\"
    "YT_DLP_INSTALLED.md" = "archive\completed\"
    "Compliance_Reports.md" = "docs\compliance\"
    "Disaster_Recovery_Plan.md" = "docs\production\"
}

foreach ($file in $remainingDocs.Keys) {
    Move-File $file $remainingDocs[$file]
}

# Move Python scripts
$setupScripts = @("setup_laa_net.py", "setup_laa_net_complete.bat", "setup_postgresql_database.py", "setup_postgresql_database.bat", "setup_redis_simple.bat", "setup_redis_windows.bat", "setup_database_windows.bat", "setup_video_management.py")
foreach ($script in $setupScripts) {
    Move-File $script "scripts\setup\"
}

$utilityScripts = @("download_laa_weights.py", "download_laa_weights_fixed.py", "extract_laa_weights.py", "find_laa_net_weights.py", "download_v13_manual.py", "find_correct_backbone_names.py", "integrate_v13_and_models.py", "download_additional_datasets.py", "create_test_video.py", "create_solana_wallet.py", "benchmark_models.py", "comprehensive_benchmarks.py", "optimize_inference_speed.py", "verify_resnet50_benchmark.py", "performance_monitor.py", "performance_validator.py", "security_auditor.py", "security_headers.py", "rate_limiter.py", "system_status.py", "Compliance_Assessment_Tool.py", "penetration_tester.py", "blockchain_integration_tester.py", "solana_integration_tester.py", "solana_program_tester.py", "batch_processor.py", "realtime_analysis.py", "quick_start.py", "simple_demo.py", "demo_enhanced_system.py", "demo_new_interface.py", "demo_test_runner.py", "start_server_simple.py", "train_resnet.py", "uat_setup.py", "uat_test_runner.py", "validate_work_order_3.py", "validate_work_order_6.py", "validate_work_order_9.py", "validate_work_order_33.py", "validate_work_order_36.py", "validate_work_order_43.py", "validate_work_order_49.py", "verify_implementation.py", "UAT_Test_Data_Generator.py", "Integration_Test_Runner.py")
foreach ($script in $utilityScripts) {
    Move-File $script "scripts\utilities\"
}

# Move batch files
$batchFiles = @("INSTALL_DEPENDENCIES.bat", "INSTALL_FLASK_SOCKETIO.bat", "INSTALL_YT_DLP_IN_VENV.bat", "QUICK_POSTGRESQL_SETUP.bat", "SETUP_ALL_SERVICES.bat", "START_NOW.bat", "START_SERVER.bat", "START_WEB_INTERFACE.bat", "START_WORKING.bat", "TEST_DETECTION.bat", "TEST_NOW.bat", "install_ensemble_dependencies.bat", "install_ensemble_dependencies_fixed.bat", "INITIALIZE_SCHEMA_WITH_POSTGRES.bat")
foreach ($file in $batchFiles) {
    Move-File $file "scripts\setup\"
}

# Move PowerShell scripts
$psScripts = @("install.ps1", "install_ensemble_dependencies.ps1", "setup-windows-services.ps1")
foreach ($script in $psScripts) {
    Move-File $script "scripts\setup\"
}

# Move shell scripts
$shellScripts = @("diagnose-deployment.sh")
foreach ($script in $shellScripts) {
    Move-File $script "scripts\deployment\"
}

# Move SQL files
$sqlFiles = @("CORRECTED_SQL_FOR_PGADMIN.sql", "INITIALIZE_SCHEMA_IN_PGADMIN.sql")
foreach ($file in $sqlFiles) {
    Move-File $file "docs\infrastructure\"
}

# Move config files to appropriate locations
$configFiles = @{
    "compliance_config.yaml" = "docs\compliance\"
    "integration_test_config.yaml" = "docs\testing\"
}

foreach ($file in $configFiles.Keys) {
    Move-File $file $configFiles[$file]
}

Write-Host "`nOrganization complete!" -ForegroundColor Green
