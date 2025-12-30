# PostgreSQL Setup - Complete Guide

## Current Status
- ✅ PostgreSQL installed
- ⚠️ Password authentication needs verification
- 📋 Ready for manual setup via pgAdmin

---

## Recommended: Use pgAdmin (Easiest Method)

### Step 1: Open pgAdmin 4

1. Press **Windows Key**
2. Type: `pgAdmin 4`
3. Click on **pgAdmin 4**
4. It will open in your default web browser

### Step 2: Connect to PostgreSQL Server

1. In the left panel, you'll see **"Servers"**
2. Click on it to expand
3. You should see your PostgreSQL server (e.g., "PostgreSQL 15")
4. **Click on it** - it will ask for password
5. Enter password: `RNYZa9z8`
6. Check "Save Password" if you want
7. Click **OK**

**If connection fails:**
- The password might be different
- Try the password you set during installation
- Or reset it (see troubleshooting below)

### Step 3: Create Database

1. **Right-click** on **"Databases"** (under your server)
2. Select **Create** → **Database**
3. In the **General** tab:
   - **Database name**: `secureai_db`
4. Click **Save**

### Step 4: Create User

1. Expand **"Login/Group Roles"** (under your server)
2. **Right-click** → **Create** → **Login/Group Role**
3. **General** tab:
   - **Name**: `secureai`
4. **Definition** tab:
   - **Password**: `SecureAI2024!DB`
   - **Password expiration**: Leave blank
5. **Privileges** tab:
   - ✓ **Can login?**
   - ✓ **Create databases?**
6. Click **Save**

### Step 5: Grant Permissions

1. **Right-click** on `secureai_db` database
2. Select **Query Tool**
3. **Paste this SQL** and click **Execute** (F5):

```sql
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;

\c secureai_db

GRANT ALL ON SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;
```

4. You should see: **"Query returned successfully"**

---

## Configure Application

### Update .env File

Add this line to your `.env` file (in the project root):

```bash
DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
```

**If .env doesn't exist**, create it with just this line.

---

## Initialize Database Schema

Run this command:

```bash
py -c "from database.db_session import init_db; init_db()"
```

**Expected output:**
```
OK: Database tables created successfully
```

---

## Test Connection

Verify everything works:

```bash
py -c "from database.db_session import get_db; db = next(get_db()); print('OK: Database connected successfully!')"
```

---

## Troubleshooting

### Password Authentication Failed

**Option 1: Verify Password**
- Open pgAdmin
- Try connecting with password: `RNYZa9z8`
- If it fails, the password might be different

**Option 2: Reset Password via pgAdmin**
1. Connect to server (use Windows authentication if available)
2. Right-click server → **Properties** → **Connection**
3. Or use Query Tool:
   ```sql
   ALTER USER postgres WITH PASSWORD 'RNYZa9z8';
   ```

**Option 3: Use Windows Authentication**
- In pgAdmin, try connecting without password
- If you're logged in as Windows admin, it might work

### PostgreSQL Service Not Running

1. Press **Windows Key + R**
2. Type: `services.msc`
3. Find **postgresql-x64-15** (or your version)
4. Right-click → **Start**

### Database Already Exists

If `secureai_db` already exists:
- Either drop it: Right-click → **Delete/Drop**
- Or use a different name

---

## Alternative: Command Line Setup

If you prefer command line:

1. Open **Command Prompt** (as Administrator)

2. Navigate to PostgreSQL bin:
   ```bash
   cd "C:\Program Files\PostgreSQL\15\bin"
   ```
   (Adjust version number)

3. Connect:
   ```bash
   psql -U postgres
   ```

4. Enter password when prompted

5. Run SQL:
   ```sql
   CREATE DATABASE secureai_db;
   CREATE USER secureai WITH ENCRYPTED PASSWORD 'SecureAI2024!DB';
   GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
   \c secureai_db
   GRANT ALL ON SCHEMA public TO secureai;
   \q
   ```

---

## Verification Checklist

- [ ] PostgreSQL service is running
- [ ] Can connect to server in pgAdmin
- [ ] Database `secureai_db` created
- [ ] User `secureai` created
- [ ] Permissions granted
- [ ] `.env` file has `DATABASE_URL`
- [ ] Schema initialized successfully
- [ ] Connection test passes

---

## Next Steps

Once all checkboxes are complete:

1. ✅ **Step 1: Redis** - COMPLETE
2. ✅ **Step 2: PostgreSQL** - IN PROGRESS
3. ⏳ **Step 3: AWS S3** - PENDING
4. ⏳ **Step 4: Sentry** - PENDING
5. ⏳ **Step 5: Final Verification** - PENDING

---

## Quick Reference

**Database Details:**
- Database: `secureai_db`
- User: `secureai`
- Password: `SecureAI2024!DB`
- Host: `localhost`
- Port: `5432`

**Connection String:**
```
postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
```

---

**Need Help?** If you encounter any issues, let me know and I'll help troubleshoot!

