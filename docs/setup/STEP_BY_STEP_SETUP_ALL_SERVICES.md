# Step-by-Step Setup: All Optional Services

This guide will walk you through setting up all optional services in sequence.

---

## STEP 1: Redis Setup ⚡

### Option A: Docker (If Available)

1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. Start Docker Desktop
3. Run:
   ```bash
   docker run -d -p 6379:6379 --name redis-secureai redis
   ```

### Option B: WSL (If Available)

1. Open WSL terminal
2. Run:
   ```bash
   sudo apt-get update
   sudo apt-get install redis-server
   sudo service redis-server start
   ```

### Option C: Manual Windows Installation

1. Download: https://github.com/microsoftarchive/redis/releases
2. Download latest `Redis-x64-*.zip`
3. Extract to `C:\Redis`
4. Run `C:\Redis\redis-server.exe`
5. Keep the window open

### Configure Redis

Add to `.env` file:
```bash
REDIS_URL=redis://localhost:6379/0
```

### Test Redis

```bash
py -c "from performance.caching import REDIS_AVAILABLE; print('Redis:', REDIS_AVAILABLE)"
```

---

## STEP 2: PostgreSQL Database Setup 🗄️

### Installation

1. Download PostgreSQL: https://www.postgresql.org/download/windows/
2. Run installer
3. **Important**: Remember the postgres user password you set
4. Complete installation with default settings

### Create Database

1. Open Command Prompt
2. Navigate to PostgreSQL bin (usually `C:\Program Files\PostgreSQL\15\bin`)
3. Run:
   ```bash
   psql -U postgres
   ```
4. Enter your postgres password
5. Run these SQL commands:
   ```sql
   CREATE DATABASE secureai_db;
   CREATE USER secureai WITH ENCRYPTED PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
   \c secureai_db
   GRANT ALL ON SCHEMA public TO secureai;
   \q
   ```

### Configure Database

Add to `.env` file:
```bash
DATABASE_URL=postgresql://secureai:your_secure_password@localhost:5432/secureai_db
```

### Initialize Database

```bash
# Initialize schema
py -c "from database.db_session import init_db; init_db()"

# Migrate existing data
py database/migrate_from_files.py
```

### Test Database

```bash
py -c "from database.db_session import get_db; db = next(get_db()); print('Database connected!'); print('Analyses:', db.execute('SELECT COUNT(*) FROM analyses').scalar())"
```

---

## STEP 3: AWS S3 Setup ☁️

### Create AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Complete signup (requires credit card, but free tier available)

### Create IAM User

1. Go to AWS Console → IAM → Users
2. Click "Add users"
3. Username: `secureai-s3-user`
4. Access type: "Programmatic access"
5. Click "Next: Permissions"
6. Select "Attach existing policies directly"
7. Search and select: `AmazonS3FullAccess`
8. Click "Next" → "Create user"
9. **SAVE CREDENTIALS** (Access Key ID and Secret Access Key)

### Create S3 Buckets

1. Go to AWS Console → S3
2. Click "Create bucket"

**Bucket 1: Videos**
- Name: `secureai-deepfake-videos` (must be globally unique - add random numbers if taken)
- Region: Choose closest (e.g., `us-east-1`)
- Uncheck "Block all public access"
- Click "Create bucket"

**Bucket 2: Results**
- Name: `secureai-deepfake-results` (must be globally unique)
- Region: Same as above
- Uncheck "Block all public access"
- Click "Create bucket"

### Configure S3

Add to `.env` file:
```bash
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

### Test S3

```bash
py -c "from storage.s3_manager import s3_manager; print('S3 Available:', s3_manager.is_available())"
```

---

## STEP 4: Sentry Setup 📊

### Create Sentry Account

1. Go to https://sentry.io/signup/
2. Sign up (email or GitHub)
3. Verify email

### Create Project

1. Click "Create Project"
2. Select: **Python** → **Flask**
3. Project name: `SecureAI Guardian`
4. Click "Create Project"

### Get DSN

1. Copy the DSN (looks like: `https://xxx@xxx.ingest.sentry.io/xxx`)
2. Save it

### Configure Sentry

Add to `.env` file:
```bash
SENTRY_DSN=https://your-dsn-here@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0
```

### Test Sentry

The integration is automatic. Errors will appear in Sentry dashboard when they occur.

---

## STEP 5: Final Verification ✅

Run the integration test:

```bash
py test_integration.py
```

All services should show `[OK]` status.

---

## Quick Reference: .env File

Your complete `.env` file should include:

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql://secureai:password@localhost:5432/secureai_db

# S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results

# Sentry
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0

# Existing configurations
GEMINI_API_KEY=your_gemini_key
VITE_API_BASE_URL=http://localhost:5000
```

---

## Troubleshooting

### Redis not connecting
- Check Redis is running
- Verify port 6379 is not blocked
- Check `REDIS_URL` in `.env`

### Database connection failed
- Verify PostgreSQL is running
- Check password is correct
- Ensure database and user exist

### S3 access denied
- Verify IAM user has S3 permissions
- Check access keys are correct
- Verify bucket names match

### Sentry not tracking
- Verify DSN is correct
- Check `sentry-sdk[flask]` is installed
- Review Sentry dashboard for rate limits

---

## Next Steps

After setup:
1. Restart your application
2. Run `py test_integration.py` to verify
3. Check logs for any warnings
4. Test each service individually

All services are optional - the app works fine without them using fallbacks!

