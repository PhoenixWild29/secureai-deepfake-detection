# Create S3 Buckets - Quick Guide

## Step 1: Navigate to S3

1. **Go to AWS Console** → **S3** (search for "S3" in the top search bar)
2. Click **"Create bucket"** button

---

## Step 2: Create First Bucket (Videos)

### General Configuration:
- **Bucket name**: `secureai-deepfake-videos`
  - ⚠️ **If this name is taken**, add random numbers: `secureai-deepfake-videos-12345`
  - Bucket names must be globally unique across all AWS accounts
- **AWS Region**: Choose closest to you
  - Examples: `us-east-1` (N. Virginia), `us-west-2` (Oregon), `eu-west-1` (Ireland)

### Object Ownership:
- Select **"ACLs disabled (recommended)"**

### Block Public Access:
- **Uncheck** "Block all public access" ✓
  - Or leave it checked and configure CORS later (we'll do this)

### Bucket Versioning:
- **Disable** (unless you need version history)

### Default Encryption:
- **Enable** "Server-side encryption with Amazon S3 managed keys (SSE-S3)" ✓

### Advanced Settings:
- Leave defaults

Click **"Create bucket"**

---

## Step 3: Create Second Bucket (Results)

1. Click **"Create bucket"** again

### General Configuration:
- **Bucket name**: `secureai-deepfake-results`
  - ⚠️ **If this name is taken**, add random numbers: `secureai-deepfake-results-12345`
- **AWS Region**: **Same region** as the first bucket

### Object Ownership:
- Select **"ACLs disabled (recommended)"**

### Block Public Access:
- **Uncheck** "Block all public access" ✓

### Bucket Versioning:
- **Disable**

### Default Encryption:
- **Enable** "Server-side encryption with Amazon S3 managed keys (SSE-S3)" ✓

Click **"Create bucket"**

---

## Step 4: Note Your Bucket Names

**Write down the exact bucket names you created:**
- Videos bucket: `secureai-deepfake-videos`
- Results bucket: `secureai-deepfake-results`
- Region: `US East (Ohio) us-east-2`

You'll need these for the `.env` file!

---

## Next Steps

After buckets are created:
1. Configure `.env` file with credentials and bucket names
2. Test S3 connection
3. Proceed to Step 4: Sentry setup

