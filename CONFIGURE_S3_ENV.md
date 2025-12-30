# Configure S3 in .env File

## What You Need

From your saved credentials:
- **Access Key ID**: `AKIA...`
- **Secret Access Key**: `...` (from CSV or your notes)
- **Bucket names**: The exact names you created
- **Region**: The region you selected (e.g., `us-east-1`)

---

## Add to .env File

Open your `.env` file and add these lines:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results
```

**Replace:**
- `your_access_key_id_here` with your actual Access Key ID
- `your_secret_access_key_here` with your actual Secret Access Key
- `us-east-1` with your actual region
- `secureai-deepfake-videos` with your actual videos bucket name
- `secureai-deepfake-results` with your actual results bucket name

---

## Example

If your credentials are:
- Access Key ID: `AKIAIOSFODNN7EXAMPLE`
- Secret Access Key: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- Region: `us-east-1`
- Videos bucket: `secureai-deepfake-videos-12345`
- Results bucket: `secureai-deepfake-results-67890`

Your `.env` would have:

```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos-12345
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results-67890
```

---

## Security Note

⚠️ **Never commit `.env` file to git!** It contains sensitive credentials.

---

## After Configuration

Once you've added these to `.env`, we'll test the connection!

