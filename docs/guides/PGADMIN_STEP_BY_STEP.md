# pgAdmin Step-by-Step Guide - Creating Database

## Current Situation
You see **PostgreSQL 15** and **PostgreSQL 18** with **red X icons** - this means they're not connected yet.

---

## Step 1: Connect to PostgreSQL Server

1. **In the left panel (Object Explorer)**, find **"PostgreSQL 15"** (or **"PostgreSQL 18"** if that's the one you installed)

2. **Click on "PostgreSQL 15"** (single click to select it)

3. **Right-click on "PostgreSQL 15"** → Select **"Connect Server"**

4. **Enter Password Dialog** will appear:
   - **Password**: Enter `RNYZa9z8` (the password you set during installation)
   - **Save password?**: Check this box if you want (optional)
   - Click **"OK"**

5. **Wait a moment** - the red X should disappear and the server icon should change to show it's connected

**If password is wrong:**
- Try the password you remember setting during PostgreSQL installation
- If you forgot, you may need to reset it (see troubleshooting below)

---

## Step 2: Expand the Server

1. **Click the arrow/triangle** next to **"PostgreSQL 15"** to expand it
2. You should now see:
   - **Databases**
   - **Login/Group Roles**
   - **Tablespaces**
   - And other items

---

## Step 3: Create the Database

1. **Find "Databases"** in the expanded list (under PostgreSQL 15)

2. **Right-click on "Databases"**

3. **Select "Create"** → **"Database..."**

4. **Database Dialog** will open with tabs at the top

5. **In the "General" tab:**
   - **Database**: Type `secureai_db`
   - Leave other fields as default

6. **Click "Save"** at the bottom

7. **You should see** `secureai_db` appear under "Databases" in the left panel

---

## Step 4: Create the User

1. **Find "Login/Group Roles"** in the expanded list (under PostgreSQL 15)

2. **Right-click on "Login/Group Roles"**

3. **Select "Create"** → **"Login/Group Role..."**

4. **Login/Group Role Dialog** will open

5. **In the "General" tab:**
   - **Name**: Type `secureai`

6. **Click on "Definition" tab:**
   - **Password**: Type `SecureAI2024!DB`
   - Leave other fields as default

7. **Click on "Privileges" tab:**
   - Check the box: **"Can login?"** ✓
   - Check the box: **"Create databases?"** ✓
   - Leave other checkboxes as they are

8. **Click "Save"** at the bottom

9. **You should see** `secureai` appear under "Login/Group Roles"

---

## Step 5: Grant Permissions to the User

1. **In the left panel**, find and **expand "Databases"**

2. **Click on `secureai_db`** (the database you just created)

3. **Right-click on `secureai_db`** → Select **"Query Tool"**

4. **A new tab** will open on the right side with a SQL editor

5. **Copy and paste** this SQL code into the editor (ALL AT ONCE):

```sql
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
GRANT ALL ON SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;
```

**IMPORTANT:** Do NOT include `\c secureai_db` - that's a command-line command that doesn't work in pgAdmin. Since you opened the Query Tool from `secureai_db`, you're already connected to it!

6. **Click the "Execute" button** (or press **F5**)

7. **You should see** "Query returned successfully" messages in the Messages tab

---

## Step 6: Verify Everything is Set Up

**Check your left panel - you should see:**

```
Servers (2)
  └─ PostgreSQL 15 (connected - no red X)
      ├─ Databases
      │   └─ secureai_db  ← Your new database
      ├─ Login/Group Roles
      │   └─ secureai  ← Your new user
      └─ ... (other items)
```

---

## Visual Guide - What You Should See

### Before Connecting:
- **PostgreSQL 15** with **red X** ❌

### After Connecting:
- **PostgreSQL 15** with **green checkmark** or **no icon** ✅
- Can expand to see Databases, Login/Group Roles, etc.

### After Creating Database:
- Under **Databases**: `secureai_db` appears

### After Creating User:
- Under **Login/Group Roles**: `secureai` appears

---

## Troubleshooting

### "Password authentication failed"
- The password might be different than `RNYZa9z8`
- Try the password you remember setting during installation
- If you're not sure, you can try connecting without a password (if Windows authentication is enabled)

### "Cannot connect to server"
1. Check if PostgreSQL service is running:
   - Press **Windows Key + R**
   - Type: `services.msc`
   - Find **postgresql-x64-15** (or your version)
   - Make sure it says "Running"
   - If not, right-click → **Start**

2. Try connecting to **PostgreSQL 18** instead (if you have both installed)

### "Database already exists"
- If `secureai_db` already exists, you can either:
  - Use it as-is (skip creation)
  - Or delete it: Right-click → **Delete/Drop** → Confirm

### "Permission denied" when running SQL
- Make sure you're connected as the `postgres` user (superuser)
- The connection should work with password `RNYZa9z8`

---

## Next Steps After Database is Created

Once you've completed all steps above:

1. **Update .env file** - Add this line:
   ```
   DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
   ```

2. **Initialize database schema** - Run:
   ```bash
   py -c "from database.db_session import init_db; init_db()"
   ```

3. **Test connection** - Run:
   ```bash
   py -c "from database.db_session import get_db; db = next(get_db()); print('OK: Database connected!')"
   ```

---

## Quick Checklist

- [ ] Connected to PostgreSQL 15 (no red X)
- [ ] Created database `secureai_db`
- [ ] Created user `secureai` with password `SecureAI2024!DB`
- [ ] Granted all permissions via SQL
- [ ] Updated .env file
- [ ] Initialized schema
- [ ] Tested connection

---

**Need Help?** If you get stuck at any step, let me know what you see and I'll help troubleshoot!

