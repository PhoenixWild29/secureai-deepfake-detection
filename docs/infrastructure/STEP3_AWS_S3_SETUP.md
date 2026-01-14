# Step 3: AWS S3 Setup ☁️

## Overview

AWS S3 will provide scalable cloud storage for:
- Video uploads
- Analysis results
- Large file handling

---

## Prerequisites

- AWS Account (free tier available)
- Credit card (for verification, but free tier covers most usage)

---

## Step 1: Create AWS Account (If Needed)

1. Go to: https://aws.amazon.com/
2. Click **"Create an AWS Account"**
3. Follow the signup process
4. Verify your email and phone number
5. Add payment method (required for verification, but free tier available)

---

## Step 2: Create IAM User

1. **Go to AWS Console** → **IAM** → **Users**
2. Click **"Add users"** or **"Create user"**
3. **Step 1: Specify user details:**
   - **User name**: `secureai-s3-user` (already filled in)
   - **Provide user access to the AWS Management Console**: **Leave this UNCHECKED** ✓
     - This means the user will have programmatic access only (which is what we want)
   - You'll see a blue info box explaining that access keys can be generated after creating the user
4. Click **"Next"** button (orange button at bottom right)

5. **Step 2: Set permissions:**
   - Select **"Attach policies directly"** or **"Attach existing policies directly"**
   - In the search box, type: `S3`
   - Check the box next to: **`AmazonS3FullAccess`** ✓
   - Click **"Next"** button

6. **Step 3: Review and create:**
   - Review the user details and permissions
   - Click **"Create user"** button

7. **⚠️ IMPORTANT: Save Credentials**
   - After creating the user, you'll see a success page
   - **Click "Create access key"** or look for the access key section
   - **Use case**: Select **"Application running outside AWS"** or **"Other"**
   - Click **"Next"** → **"Create access key"**
   - **Access Key ID**: `AKIA...` (copy this immediately!)
   - **Secret Access Key**: `...` (copy this immediately - you won't see it again!)
   - Click **"Download .csv"** to save credentials securely
   - **Or manually copy both values** to a secure location
   - Click **"Done"**

---

## Step 3: Create S3 Buckets

1. **Go to AWS Console** → **S3**
2. Click **"Create bucket"**

### Bucket 1: Videos

- **Bucket name**: `secureai-deepfake-videos` 
  - ⚠️ Must be globally unique - add random numbers if taken (e.g., `secureai-deepfake-videos-12345`)
- **AWS Region**: Choose closest to you (e.g., `us-east-1`)
- **Object Ownership**: ACLs disabled (recommended)
- **Block Public Access**: **Uncheck** "Block all public access" (or configure CORS later)
- **Bucket Versioning**: Disable (unless needed)
- **Default encryption**: Server-side encryption with Amazon S3 managed keys (SSE-S3)
- Click **"Create bucket"**

### Bucket 2: Results

- **Bucket name**: `secureai-deepfake-results`
  - ⚠️ Must be globally unique - add random numbers if taken
- **AWS Region**: Same as above
- **Object Ownership**: ACLs disabled (recommended)
- **Block Public Access**: **Uncheck** "Block all public access"
- **Bucket Versioning**: Disable
- **Default encryption**: Server-side encryption with Amazon S3 managed keys (SSE-S3)
- Click **"Create bucket"**

---

## Step 4: Configure CORS (Optional but Recommended)

For each bucket:

1. **Click on bucket name**
2. Go to **"Permissions"** tab
3. Scroll to **"Cross-origin resource sharing (CORS)"**
4. Click **"Edit"**
5. **Paste this configuration:**

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000
    }
]
```

6. Click **"Save changes"**

---

## Step 5: Configure Application

Add these to your `.env` file:

```bash
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

**Replace:**
- `your_access_key_id_here` with your Access Key ID
- `your_secret_access_key_here` with your Secret Access Key
- `us-east-1` with your chosen region
- Bucket names with your actual bucket names (if you added numbers)

---

## Step 6: Test S3 Connection

Run this command:

```bash
py -c "from storage.s3_manager import s3_manager; print('S3 Available:', s3_manager.is_available())"
```

**Expected output:** `S3 Available: True`

---

## Cost Estimate

### Free Tier (First 12 Months)
- **5 GB** storage
- **20,000 GET** requests
- **2,000 PUT** requests
- **100 GB** data transfer out

### After Free Tier
- **Storage**: ~$0.023 per GB/month
- **Requests**: ~$0.0004 per 1,000 requests
- **Data Transfer**: First 100 GB free, then ~$0.09 per GB

### Typical Usage
- **Small deployment**: < $5/month
- **Moderate use**: $5-20/month
- **Heavy use**: $20-50/month

---

## Security Best Practices

1. ✅ **Use IAM user** (not root account)
2. ✅ **Attach minimal required permissions** (S3 only)
3. ✅ **Rotate access keys** regularly (every 90 days)
4. ✅ **Enable MFA** for AWS account
5. ✅ **Use bucket policies** for access control
6. ✅ **Enable versioning** for critical data (optional)
7. ✅ **Set up lifecycle policies** to delete old files (optional)

---

## Troubleshooting

### Error: Access Denied
- Check IAM user has `AmazonS3FullAccess` policy
- Verify access keys are correct in `.env`
- Check bucket names match exactly (case-sensitive)

### Error: Bucket not found
- Verify bucket name is correct
- Check region matches `AWS_DEFAULT_REGION`
- Ensure bucket exists in AWS Console

### Error: Invalid credentials
- Regenerate access keys in IAM
- Update `.env` file with new keys
- Restart application

### Error: CORS policy
- Configure CORS on buckets (see Step 4)
- Check AllowedOrigins includes your domain

---

## Next Steps

Once S3 is configured and tested:

1. ✅ **Step 1: Redis** - COMPLETE
2. ✅ **Step 2: PostgreSQL** - COMPLETE
3. ✅ **Step 3: AWS S3** - IN PROGRESS
4. ⏳ **Step 4: Sentry** - PENDING
5. ⏳ **Step 5: Final Verification** - PENDING

---

## Quick Reference

**Bucket Names:**
- Videos: `secureai-deepfake-videos` (or with numbers)
- Results: `secureai-deepfake-results` (or with numbers)

**Region:** Choose closest to you (e.g., `us-east-1`, `us-west-2`, `eu-west-1`)

**IAM User:** `secureai-s3-user` with `AmazonS3FullAccess` policy

---

**Ready to start?** Follow the steps above and let me know when you've created the IAM user and buckets!

