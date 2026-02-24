# Initialize Database Schema in pgAdmin

## Quick Steps

Since password authentication from Python is having issues, let's initialize the schema directly in pgAdmin where you can already connect.

### Step 1: Open Query Tool

1. **In pgAdmin**, right-click on `secureai_db` database
2. Select **"Query Tool"**

### Step 2: Run SQL Script

1. **Open** the file `INITIALIZE_SCHEMA_IN_PGADMIN.sql`
2. **Copy all the SQL** from that file
3. **Paste** it into the Query Tool in pgAdmin
4. **Click "Execute"** (or press F5)

### Step 3: Verify

You should see:
- Multiple "Query returned successfully" messages
- A final message: "Database schema initialized successfully!"

### Step 4: Check Tables

1. **In pgAdmin**, expand `secureai_db` → **Schemas** → **public** → **Tables**
2. You should see:
   - `users`
   - `analyses`
   - `processing_stats`

---

## After Schema is Initialized

Once the schema is created, we can:
1. ✅ Test the database connection (using the correct password)
2. ✅ Proceed to AWS S3 setup
3. ✅ Continue with Sentry setup

---

## Password Note

The password authentication issue suggests the password might need URL encoding for special characters. After initializing the schema, we can test with the actual password you set in pgAdmin.

**What password did you set for the `secureai` user?** We'll need to make sure it matches in the `.env` file.

