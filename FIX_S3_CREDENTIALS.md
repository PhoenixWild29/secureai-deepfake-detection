# Fix AWS S3 Credentials Configuration

## Problem

You're seeing: `WARNING:storage.s3_manager: AWS credentials not configured. S3 operations will fail.`

This means the AWS credentials are not in the `.env` file on your server.

## Solution: Add AWS Credentials to .env File

### Step 1: Find Your AWS Credentials

You should have saved these when you set up AWS S3:
- **Access Key ID**: `AKIA...` (starts with AKIA)
- **Secret Access Key**: `...` (long string, from the CSV file you downloaded)
- **Region**: e.g., `us-east-1`, `us-east-2`, etc.
- **Bucket Names**: The exact names you created (e.g., `secureai-deepfake-videos-12345`)

**If you don't have them:**
1. Go to AWS Console → IAM → Users
2. Click on your user (e.g., `secureai-s3-user`)
3. Go to "Security credentials" tab
4. If you see "Create access key", you need to create new ones (old ones might be deleted)
5. If you see existing keys, you can't view the secret again - you'll need to create new ones

### Step 2: Edit .env File on Server

**On your cloud server**, run:

```bash
cd ~/secureai-deepfake-detection

# Edit the .env file
nano .env
```

### Step 3: Add AWS Credentials

Add these lines to your `.env` file (replace with your actual values):

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

**Important:**
- Replace `AKIAXXXXXXXXXXXXXXXX` with your actual Access Key ID
- Replace `your_secret_access_key_here` with your actual Secret Access Key
- Replace `us-east-1` with your actual region (e.g., `us-east-2`, `us-west-1`, etc.)
- Replace bucket names with your actual bucket names (they might have numbers at the end)

### Step 4: Save and Exit

- Press `Ctrl + O` to save
- Press `Enter` to confirm
- Press `Ctrl + X` to exit

### Step 5: Restart Backend Container

The Docker container needs to be restarted to load the new environment variables:

```bash
docker compose -f docker-compose.https.yml restart secureai-backend
```

### Step 6: Verify S3 Connection

Check the logs to see if S3 is now connected:

```bash
docker logs secureai-backend --tail 30 | grep -i s3
```

**Success indicators:**
- `✅ S3 connection established. Bucket: secureai-deepfake-videos`
- No more "AWS credentials not configured" warnings

**If you still see errors:**
- Double-check the credentials are correct (no extra spaces, correct region)
- Verify the bucket names match exactly what you created in AWS
- Check that the IAM user has S3 permissions

## Example .env File

Here's what a complete `.env` file might look like:

```bash
# Secret Key
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://secureai:SecureAI2024!DB@postgres:5432/secureai_db
DB_PASSWORD=SecureAI2024!DB

# Redis
REDIS_URL=redis://redis:6379/0

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos-12345
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results-67890

# Solana (if configured)
SOLANA_NETWORK=devnet
SOLANA_WALLET_PATH=/app/wallet/id.json
```

## Troubleshooting

### "Access Denied" Error

If you see access denied errors:
1. Check IAM user has `AmazonS3FullAccess` policy attached
2. Verify bucket names are correct
3. Check region matches where buckets were created

### "Bucket Not Found" Error

If you see bucket not found:
1. Go to AWS Console → S3
2. Verify bucket names match exactly (case-sensitive)
3. Check the region matches

### Still Not Working?

1. **Verify credentials work:**
   ```bash
   docker exec secureai-backend python -c "import boto3; import os; from dotenv import load_dotenv; load_dotenv(); client = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), region_name=os.getenv('AWS_DEFAULT_REGION')); print('Buckets:', [b['Name'] for b in client.list_buckets()['Buckets']])"
   ```

2. **Check environment variables are loaded:**
   ```bash
   docker exec secureai-backend env | grep AWS
   ```

3. **Check S3 manager logs:**
   ```bash
   docker logs secureai-backend 2>&1 | grep -i "s3\|aws" | tail -20
   ```

## Security Reminder

⚠️ **Never commit `.env` file to git!** It contains sensitive credentials.

The `.env` file should already be in `.gitignore`, but double-check it's not being tracked:
```bash
git check-ignore .env
```

If it returns nothing, add it to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

