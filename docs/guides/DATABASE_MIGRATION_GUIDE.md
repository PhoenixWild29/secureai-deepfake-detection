# 🗄️ Database Migration Guide

This guide walks you through migrating from file-based storage to PostgreSQL database.

## Prerequisites

- PostgreSQL 12+ installed
- Python dependencies: `sqlalchemy`, `psycopg2-binary`, `alembic`
- Existing data in `results/` folder (JSON files)

## Step 1: Install PostgreSQL

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

### macOS:
```bash
brew install postgresql
brew services start postgresql
```

### Windows:
Download from [PostgreSQL website](https://www.postgresql.org/download/windows/)

## Step 2: Create Database

Run the setup script:
```bash
chmod +x database/setup_database.sh
sudo ./database/setup_database.sh
```

Or manually:
```bash
sudo -u postgres psql
CREATE DATABASE secureai_db;
CREATE USER secureai WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
\q
```

## Step 3: Configure Environment

Add to your `.env` file:
```bash
DATABASE_URL=postgresql://secureai:your_password@localhost:5432/secureai_db
```

## Step 4: Install Python Dependencies

```bash
pip install sqlalchemy psycopg2-binary alembic python-json-logger
```

## Step 5: Initialize Database Schema

```bash
python -c "from database.db_session import init_db; init_db()"
```

Or run migrations:
```bash
cd database
alembic upgrade head
```

## Step 6: Migrate Existing Data

```bash
python database/migrate_from_files.py
```

This will:
- Migrate all analysis results from `results/*.json` to database
- Migrate users from `users.json` to database
- Preserve all data and relationships

## Step 7: Update API to Use Database

The API needs to be updated to use database sessions instead of file operations. See `database/api_integration_example.py` for reference.

## Verification

Check migration:
```bash
psql -U secureai -d secureai_db -c "SELECT COUNT(*) FROM analyses;"
psql -U secureai -d secureai_db -c "SELECT COUNT(*) FROM users;"
```

## Rollback

If you need to rollback:
```bash
# Drop database (WARNING: This deletes all data)
psql -U postgres -c "DROP DATABASE secureai_db;"
```

## Troubleshooting

### Connection Error
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `.env`
- Check firewall rules

### Migration Errors
- Ensure JSON files are valid
- Check file permissions
- Review error logs

### Performance
- Add indexes for frequently queried fields
- Use connection pooling (already configured)
- Monitor query performance

## Next Steps

After migration:
1. Update `api.py` to use database queries
2. Remove file-based storage code
3. Set up database backups
4. Configure monitoring

