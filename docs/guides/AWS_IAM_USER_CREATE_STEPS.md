# AWS IAM User Creation - Current Interface Steps

## Step-by-Step for Current AWS Console

### Step 1: Navigate to IAM Users
1. Go to **AWS Console** → **IAM** → **Users**
2. Click **"Create user"** or **"Add users"** button

### Step 2: Specify User Details
1. **User name**: `secureai-s3-user` (type or it may be pre-filled)
2. **Provide user access to the AWS Management Console**: 
   - **Leave this UNCHECKED** ✓
   - This creates a user for programmatic access only (what we need)
3. You'll see a blue info box: "If you are creating programmatic access through access keys..."
4. Click **"Next"** (orange button at bottom right)

### Step 3: Set Permissions
1. Select **"Attach policies directly"** tab (if not already selected)
2. In the search box, type: `S3`
3. Find and check: **`AmazonS3FullAccess`** ✓
4. Click **"Next"** button

### Step 4: Review and Create
1. Review the summary:
   - User name: `secureai-s3-user`
   - Permissions: `AmazonS3FullAccess`
2. Click **"Create user"** button

### Step 5: Create Access Keys (IMPORTANT!)
1. After user is created, you'll see a success page
2. **Click "Create access key"** button (or find it in the user details page)
3. **Use case**: Select **"Application running outside AWS"** or **"Other"**
4. Click **"Next"**
5. **Optional**: Add description tag (e.g., "SecureAI S3 Access")
6. Click **"Create access key"**
7. **⚠️ CRITICAL: Save these immediately:**
   - **Access Key ID**: `AKIA...` (starts with AKIA)
   - **Secret Access Key**: `...` (long random string)
8. Click **"Download .csv"** to save securely
9. **Or manually copy both** to a secure location
10. Click **"Done"**

---

## Important Notes

- **Console access is NOT needed** - Leave it unchecked
- **Access keys are created AFTER** the user is created (not during)
- **Secret Access Key is shown only once** - Save it immediately!
- You can create multiple access keys per user if needed

---

## What You'll Need

After completing these steps, you'll have:
- ✅ IAM User: `secureai-s3-user`
- ✅ Access Key ID: `AKIA...`
- ✅ Secret Access Key: `...`
- ✅ Permission: `AmazonS3FullAccess`

These will be added to your `.env` file in the next step.

