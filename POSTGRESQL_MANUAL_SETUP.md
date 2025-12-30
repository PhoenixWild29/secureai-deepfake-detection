# PostgreSQL Manual Setup Guide

## Quick Setup Steps

Since the automated script had authentication issues, let's set up PostgreSQL manually using pgAdmin (the GUI tool that came with PostgreSQL).

---

## Step 1: Open pgAdmin 4

1. **Start pgAdmin 4** from Windows Start Menu
   - Search for "pgAdmin 4"
   - It should open in your web browser

2. **Connect to Server** (if not already connected):
   - You should see "Servers" in the left panel
   - Click on it and enter password: `RNYZa9z8`
   - If prompted, this is the postgres superuser password

---

## Step 2: Create Database

1. **Right-click** on "Databases" → **Create** → **Database**

2. **General Tab**:
   - **Name**: `secureai_db`
   - Click **Save**

---

## Step 3: Create User

1. **Expand** "Login/Group Roles" (under your server)

2. **Right-click** → **Create** → **Login/Group Role**

3. **General Tab**:
   - **Name**: `secureai`

4. **Definition Tab**:
   - **Password**: `SecureAI2024!DB`
   - (Remember this password - we'll use it in .env)

5. **Privileges Tab**:
   - Check: **Can login?** ✓
   - Check: **Create databases?** ✓

6. Click **Save**

---

## Step 4: Grant Permissions

1. **Right-click** on `secureai_db` database → **Query Tool**

2. **Paste and run** this SQL:

```sql
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;

\c secureai_db

GRANT ALL ON SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;
```

3. Click **Execute** (or press F5)

---

## Step 5: Configure .env File

Add this line to your `.env` file (create it if it doesn't exist):

```bash
DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
```

---

## Step 6: Initialize Database Schema

Run this command:

```bash
py -c "from database.db_session import init_db; init_db()"
```

Expected output:
```
OK: Database tables created successfully
```

---

## Step 7: Test Connection

Run this to verify:

```bash
py -c "from database.db_session import get_db; db = next(get_db()); print('OK: Database connected!')"
```

---

## Alternative: Command Line Setup

If you prefer command line, open **Command Prompt** and run:

```bash
cd "C:\Program Files\PostgreSQL\15\bin"
```

(Adjust version number if different)

Then run:

```bash
psql -U postgres
```

Enter password: `RNYZa9z8`

Then run these SQL commands:

```sql
CREATE DATABASE secureai_db;
CREATE USER secureai WITH ENCRYPTED PASSWORD 'SecureAI2024!DB';
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
\c secureai_db
GRANT ALL ON SCHEMA public TO secureai;
\q
```

---

## Troubleshooting

### "Password authentication failed"
- Verify the postgres password is correct: `RNYZa9z8`
- Check PostgreSQL service is running (Services → postgresql-x64-15)

### "Database already exists"
- Either drop it: `DROP DATABASE secureai_db;`
- Or use a different name

### "Permission denied"
- Make sure you granted all privileges in Step 4
- Verify user `secureai` can login

---

## Next Steps

Once database is set up:
1. ✅ Database created
2. ✅ User created
3. ✅ Permissions granted
4. ✅ .env configured
5. ✅ Schema initialized

**Proceed to Step 3: AWS S3 Setup**

