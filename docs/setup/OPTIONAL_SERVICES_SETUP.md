# 🚀 Optional Services Setup Guide

This guide will help you configure the optional services to enhance SecureAI Guardian.

## Services Overview

1. **PostgreSQL Database** - Scalable data storage (recommended for production)
2. **Redis** - High-performance caching (recommended for performance)
3. **AWS S3** - Cloud file storage (recommended for scalability)
4. **Sentry** - Error tracking and monitoring (recommended for production)

---

## Priority Order

### Recommended Setup Order:
1. **Redis** (Easiest, immediate performance boost)
2. **Database** (PostgreSQL - Better data management)
3. **S3** (Cloud storage - Scalability)
4. **Sentry** (Error tracking - Production monitoring)

---

## Service 1: Redis (Caching) ⚡

**Benefits:**
- Faster API responses
- Reduced database load
- Better user experience

**Setup Time:** ~5 minutes

### Windows Setup:
1. Download Redis from: https://github.com/microsoftarchive/redis/releases
2. Or use WSL: `wsl sudo apt-get install redis-server`
3. Or use Docker: `docker run -d -p 6379:6379 redis`

### Configuration:
Add to `.env`:
```bash
REDIS_URL=redis://localhost:6379/0
```

### Verification:
```bash
py -c "from performance.caching import REDIS_AVAILABLE; print('Redis:', REDIS_AVAILABLE)"
```

---

## Service 2: PostgreSQL Database 🗄️

**Benefits:**
- Scalable data storage
- Better query performance
- ACID transactions
- Data integrity

**Setup Time:** ~15 minutes

### Windows Setup:
1. Download PostgreSQL: https://www.postgresql.org/download/windows/
2. Install with default settings
3. Remember the postgres user password

### Database Creation:
```sql
CREATE DATABASE secureai_db;
CREATE USER secureai WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
```

### Configuration:
Add to `.env`:
```bash
DATABASE_URL=postgresql://secureai:your_password@localhost:5432/secureai_db
```

### Initialize & Migrate:
```bash
# Initialize database schema
py -c "from database.db_session import init_db; init_db()"

# Migrate existing data
py database/migrate_from_files.py
```

---

## Service 3: AWS S3 Storage ☁️

**Benefits:**
- Scalable file storage
- Reduced server disk usage
- CDN integration
- Automatic backups

**Setup Time:** ~10 minutes

### AWS Setup:
1. Create AWS account: https://aws.amazon.com/
2. Go to IAM → Users → Create User
3. Attach policy: `AmazonS3FullAccess`
4. Create Access Key (save credentials)

### S3 Bucket Creation:
1. Go to S3 → Create Bucket
2. Name: `secureai-deepfake-videos`
3. Region: Choose closest to you
4. Uncheck "Block all public access" (or configure CORS)

### Configuration:
Add to `.env`:
```bash
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

### Verification:
```bash
py -c "from storage.s3_manager import s3_manager; print('S3 Available:', s3_manager.is_available())"
```

---

## Service 4: Sentry (Error Tracking) 📊

**Benefits:**
- Real-time error tracking
- Performance monitoring
- Production debugging
- Alert notifications

**Setup Time:** ~5 minutes

### Sentry Setup:
1. Create account: https://sentry.io/signup/
2. Create new project → Python → Flask
3. Copy DSN (looks like: `https://xxx@xxx.ingest.sentry.io/xxx`)

### Configuration:
Add to `.env`:
```bash
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
ENVIRONMENT=production
APP_VERSION=1.0.0
```

### Verification:
```bash
py -c "import os; print('Sentry DSN:', 'Set' if os.getenv('SENTRY_DSN') else 'Not Set')"
```

---

## Quick Setup Script

I'll create automated setup scripts for each service. Which would you like to start with?

1. **Redis** - Quick performance boost
2. **PostgreSQL** - Better data management
3. **AWS S3** - Cloud storage
4. **Sentry** - Error tracking

Or we can set up all of them! Let me know which you'd like to configure first.

