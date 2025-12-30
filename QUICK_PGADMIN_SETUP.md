# Quick pgAdmin Setup - Visual Guide

## The Problem
You see **red X icons** next to PostgreSQL servers - they're not connected yet.

## The Solution
Connect first, then create database.

---

## 🎯 Quick Steps

### 1️⃣ Connect to Server
- **Click** on **"PostgreSQL 15"** in left panel
- **Right-click** → **"Connect Server"**
- **Enter password**: `RNYZa9z8`
- **Click OK**
- ✅ Red X should disappear

### 2️⃣ Create Database
- **Expand** "PostgreSQL 15" (click arrow)
- **Right-click** on **"Databases"**
- **Create** → **Database...**
- **Name**: `secureai_db`
- **Click Save**

### 3️⃣ Create User
- **Right-click** on **"Login/Group Roles"**
- **Create** → **Login/Group Role...**
- **General tab**: Name = `secureai`
- **Definition tab**: Password = `SecureAI2024!DB`
- **Privileges tab**: Check "Can login?" and "Create databases?"
- **Click Save**

### 4️⃣ Grant Permissions
- **Right-click** on `secureai_db` → **Query Tool**
- **Paste and run** (F5) - **DO NOT include `\c` command**:
  ```sql
  GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
  GRANT ALL ON SCHEMA public TO secureai;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;
  ```

### 5️⃣ Configure App
- Add to `.env`:
  ```
  DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
  ```

### 6️⃣ Initialize
```bash
py -c "from database.db_session import init_db; init_db()"
```

---

**That's it!** See `PGADMIN_STEP_BY_STEP.md` for detailed instructions.

