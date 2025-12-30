# Fix Database Password Authentication

## Issue
Password authentication is failing for user `secureai`. This means either:
1. The password is incorrect
2. The user wasn't created properly

## Solution: Verify/Reset Password in pgAdmin

### Option 1: Check Current Password

1. **Open pgAdmin**
2. **Connect to PostgreSQL 18** (or 15)
3. **Expand** "Login/Group Roles"
4. **Right-click** on `secureai` → **Properties**
5. **Go to "Definition" tab** - you can see if password is set (but not the actual password)

### Option 2: Reset Password

1. **In pgAdmin**, right-click on `secureai` user → **Properties**
2. **Go to "Definition" tab**
3. **Enter new password**: `SecureAI2024!DB`
4. **Click "Save"**

### Option 3: Recreate User (If needed)

If the user doesn't exist or is corrupted:

1. **Right-click** "Login/Group Roles" → **Create** → **Login/Group Role**
2. **General tab**: Name = `secureai`
3. **Definition tab**: Password = `SecureAI2024!DB`
4. **Privileges tab**: Check "Can login?" and "Create databases?"
5. **Click Save**

Then re-run the GRANT permissions SQL in the Query Tool for `secureai_db`.

---

## After Fixing Password

Once password is correct, the schema initialization should work:

```bash
py -c "from database.db_session import init_db; init_db()"
```

---

## Alternative: Use postgres User Temporarily

If you want to proceed while fixing the secureai user, you can temporarily use the postgres superuser:

Update `.env`:
```
DATABASE_URL=postgresql://postgres:RNYZa9z8@localhost:5432/secureai_db
```

But it's better to fix the `secureai` user for security reasons.

