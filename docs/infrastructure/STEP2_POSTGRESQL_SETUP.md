# Step 2: PostgreSQL Database Setup 🗄️

## Overview

PostgreSQL will replace file-based storage with a robust relational database for:
- User data
- Analysis results
- Processing statistics
- Better performance and scalability

---

## Installation Steps

### 1. Download PostgreSQL

1. Go to: https://www.postgresql.org/download/windows/
2. Click "Download the installer"
3. Download **PostgreSQL 15** (or latest version)
4. Run the installer

### 2. Installation Wizard

**Important Settings:**
- **Installation Directory**: Use default (`C:\Program Files\PostgreSQL\15`)
- **Data Directory**: Use default
- **Password**: **CREATE A STRONG PASSWORD** for the `postgres` superuser
  - ⚠️ **SAVE THIS PASSWORD** - you'll need it!
- **Port**: `5432` (default - keep this)
- **Advanced Options**: Use defaults
- **Stack Builder**: You can skip this (not needed)

### 3. Complete Installation

Wait for installation to finish. This may take a few minutes.

---

## Database Setup

### Option A: Using pgAdmin (GUI - Recommended)

1. **Open pgAdmin 4** (installed with PostgreSQL)
2. **Connect to Server**:
   - Right-click "Servers" → "Create" → "Server"
   - **General Tab**:
     - Name: `SecureAI Local`
   - **Connection Tab**:
     - Host: `localhost`
     - Port: `5432`
     - Username: `postgres`
     - Password: (your postgres password)
   - Click "Save"

3. **Create Database**:
   - Right-click "Databases" → "Create" → "Database"
   - Name: `secureai_db`
   - Click "Save"

4. **Create User**:
   - Expand "Login/Group Roles"
   - Right-click → "Create" → "Login/Group Role"
   - **General Tab**:
     - Name: `secureai`
   - **Definition Tab**:
     - Password: (create a secure password)
   - **Privileges Tab**:
     - Check "Can login?"
   - Click "Save"

5. **Grant Permissions**:
   - Right-click `secureai_db` → "Query Tool"
   - Run this SQL:
     ```sql
     GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
     \c secureai_db
     GRANT ALL ON SCHEMA public TO secureai;
     ```

### Option B: Using Command Line (psql)

1. **Open Command Prompt** (as Administrator)

2. **Navigate to PostgreSQL bin**:
   ```bash
   cd "C:\Program Files\PostgreSQL\15\bin"
   ```

3. **Connect to PostgreSQL**:
   ```bash
   psql -U postgres
   ```
   Enter your postgres password when prompted.

4. **Create Database and User**:
   ```sql
   CREATE DATABASE secureai_db;
   CREATE USER secureai WITH ENCRYPTED PASSWORD 'your_secure_password_here';
   GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
   \c secureai_db
   GRANT ALL ON SCHEMA public TO secureai;
   \q
   ```

---

## Configure Application

### Add to `.env` File

Add this line to your `.env` file (create it if it doesn't exist):

```bash
DATABASE_URL=postgresql://secureai:your_secure_password_here@localhost:5432/secureai_db
```

**Replace `your_secure_password_here` with the password you created for the `secureai` user!**

---

## Initialize Database Schema

Run this command to create the database tables:

```bash
py -c "from database.db_session import init_db; init_db()"
```

Expected output:
```
✅ Database initialized successfully
```

---

## Migrate Existing Data (Optional)

If you have existing analysis results in JSON files, migrate them:

```bash
py database/migrate_from_files.py
```

This will:
- Import all existing analysis results
- Preserve all historical data
- Create user records if needed

---

## Test Database Connection

Run this to verify everything works:

```bash
py -c "from database.db_session import get_db; db = next(get_db()); print('✅ Database connected!'); print('Tables:', db.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = \\'public\\'').fetchall())"
```

---

## Troubleshooting

### "psql: command not found"
- Add PostgreSQL bin to PATH, or use full path:
  ```bash
  "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres
  ```

### "Password authentication failed"
- Verify password is correct
- Check if PostgreSQL service is running:
  ```bash
  services.msc
  ```
  Look for "postgresql-x64-15" and ensure it's running

### "Database does not exist"
- Make sure you created `secureai_db`
- Verify the database name in `DATABASE_URL`

### "Permission denied"
- Make sure you granted permissions to the `secureai` user
- Verify the user can login (check pgAdmin → Login/Group Roles)

---

## Next Steps

Once PostgreSQL is configured and tested:
1. ✅ Database tables created
2. ✅ Connection verified
3. ✅ Migration complete (if applicable)

**Proceed to Step 3: AWS S3 Setup**

---

## Quick Reference

### Start PostgreSQL Service
```bash
net start postgresql-x64-15
```

### Stop PostgreSQL Service
```bash
net stop postgresql-x64-15
```

### Check Service Status
```bash
sc query postgresql-x64-15
```

### Connect via psql
```bash
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d secureai_db
```

