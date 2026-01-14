@echo off
echo ========================================
echo SecureAI Guardian - Complete Services Setup
echo ========================================
echo.
echo This script will guide you through setting up:
echo   1. Redis (Caching)
echo   2. PostgreSQL Database
echo   3. AWS S3 Storage
echo   4. Sentry Error Tracking
echo.
echo Let's begin!
echo.
pause

echo.
echo ========================================
echo STEP 1: Redis Setup
echo ========================================
echo.
call setup_redis_windows.bat

echo.
echo ========================================
echo STEP 2: PostgreSQL Database Setup
echo ========================================
echo.
call setup_database_windows.bat

echo.
echo ========================================
echo STEP 3: AWS S3 Setup
echo ========================================
echo.
echo Please follow the guide in: setup_s3_guide.md
echo.
echo After completing AWS setup, add to .env:
echo   AWS_ACCESS_KEY_ID=your_key
echo   AWS_SECRET_ACCESS_KEY=your_secret
echo   AWS_DEFAULT_REGION=us-east-1
echo   S3_BUCKET_NAME=secureai-deepfake-videos
echo   S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
echo.
pause

echo.
echo ========================================
echo STEP 4: Sentry Setup
echo ========================================
echo.
echo Please follow the guide in: setup_sentry_guide.md
echo.
echo After completing Sentry setup, add to .env:
echo   SENTRY_DSN=https://your-dsn@sentry.io/project-id
echo   SENTRY_TRACES_SAMPLE_RATE=0.1
echo   SENTRY_PROFILES_SAMPLE_RATE=0.1
echo   ENVIRONMENT=production
echo   APP_VERSION=1.0.0
echo.
pause

echo.
echo ========================================
echo STEP 5: Verification
echo ========================================
echo.
echo Running integration test...
py test_integration.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo All services have been configured.
echo Review the test results above to verify everything is working.
echo.
pause

