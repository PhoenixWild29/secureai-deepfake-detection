# Fix: pgAdmin SQL Error

## The Problem

You got this error:
```
ERROR: syntax error at or near "\"
LINE 2: \c secureai_db
```

## Why This Happened

The `\c` command is a **psql command-line tool command**, NOT a SQL command. It doesn't work in pgAdmin's Query Tool.

**Good news:** Since you opened the Query Tool by right-clicking on `secureai_db`, you're **already connected** to that database! You don't need `\c` at all.

---

## ✅ Corrected SQL Commands

**Delete everything in the Query Tool** and paste **ONLY these commands**:

```sql
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
GRANT ALL ON SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;
```

**Then click "Execute" (or press F5)**

You should see "Query returned successfully" for each command.

---

## Step-by-Step Fix

1. **In the Query Tool**, select all the text (Ctrl+A)
2. **Delete it** (Delete key)
3. **Paste the corrected SQL above** (without the `\c` line)
4. **Click "Execute"** button (or press F5)
5. **Check the Messages tab** - you should see success messages

---

## What Each Command Does

1. `GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;`
   - Gives the user full access to the database

2. `GRANT ALL ON SCHEMA public TO secureai;`
   - Gives the user full access to the public schema

3. `GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;`
   - Gives the user full access to all existing tables

4. `GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;`
   - Gives the user full access to all sequences (for auto-increment IDs)

5. `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;`
   - Ensures future tables will have full access

6. `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;`
   - Ensures future sequences will have full access

---

## After Running the Commands

Once all commands execute successfully:

1. **Update your `.env` file** with:
   ```
   DATABASE_URL=postgresql://secureai:SecureAI2024!DB@localhost:5432/secureai_db
   ```

2. **Initialize the database schema**:
   ```bash
   py -c "from database.db_session import init_db; init_db()"
   ```

3. **Test the connection**:
   ```bash
   py -c "from database.db_session import get_db; db = next(get_db()); print('OK: Database connected!')"
   ```

---

## Quick Reference

**Remember:**
- ✅ `\c` is for **psql command line** only
- ✅ In **pgAdmin Query Tool**, you're already connected to the database you selected
- ✅ Use **pure SQL commands** only in pgAdmin

---

**Try the corrected SQL commands above and let me know if it works!**

