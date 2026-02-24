# AWS S3 Setup Guide

## Step 1: Create AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the signup process

## Step 2: Create IAM User

1. Go to AWS Console → IAM → Users
2. Click "Add users"
3. Username: `secureai-s3-user`
4. Access type: "Programmatic access"
5. Click "Next: Permissions"

## Step 3: Attach S3 Policy

1. Click "Attach existing policies directly"
2. Search for "S3" and select: `AmazonS3FullAccess`
3. Click "Next: Tags" (optional)
4. Click "Next: Review"
5. Click "Create user"

## Step 4: Save Credentials

**IMPORTANT:** Save these credentials immediately (you won't see them again):

- Access Key ID: `AKIA...`
- Secret Access Key: `...`

## Step 5: Create S3 Buckets

1. Go to AWS Console → S3
2. Click "Create bucket"

### Bucket 1: Videos
- Bucket name: `secureai-deepfake-videos` (must be globally unique)
- Region: Choose closest to you (e.g., `us-east-1`)
- Uncheck "Block all public access" (or configure CORS later)
- Click "Create bucket"

### Bucket 2: Results
- Bucket name: `secureai-deepfake-results` (must be globally unique)
- Region: Same as above
- Uncheck "Block all public access"
- Click "Create bucket"

## Step 6: Configure CORS (Optional)

For each bucket:
1. Click on bucket name
2. Go to "Permissions" tab
3. Scroll to "Cross-origin resource sharing (CORS)"
4. Click "Edit" and add:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

## Step 7: Add to .env

Add these to your `.env` file:

```bash
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

## Step 8: Test Connection

Run:
```bash
py -c "from storage.s3_manager import s3_manager; print('S3 Available:', s3_manager.is_available())"
```

Should output: `S3 Available: True`

## Cost Estimate

- **Free Tier**: 5GB storage, 20,000 GET requests, 2,000 PUT requests per month
- **After Free Tier**: ~$0.023 per GB storage, $0.0004 per 1,000 requests
- **Typical Usage**: < $5/month for moderate use

## Security Best Practices

1. ✅ Use IAM user (not root account)
2. ✅ Attach minimal required permissions
3. ✅ Rotate access keys regularly
4. ✅ Enable MFA for AWS account
5. ✅ Use bucket policies for access control

## Troubleshooting

### Error: Access Denied
- Check IAM user has `AmazonS3FullAccess` policy
- Verify access keys are correct

### Error: Bucket not found
- Check bucket name is correct (case-sensitive)
- Verify region matches

### Error: Invalid credentials
- Regenerate access keys in IAM
- Update `.env` file

