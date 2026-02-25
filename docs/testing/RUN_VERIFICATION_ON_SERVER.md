# Run ResNet50 Verification on Server - Step by Step

## Step 1: Pull Latest Changes

First, make sure you have the latest code on your server:

```bash
# SSH into your server
ssh root@your-server-ip

# Navigate to your project directory
cd /path/to/your/project  # Usually something like /root/secureai-deepfake-detection

# Pull latest changes from GitHub
git pull origin master
```

## Step 2: Copy Script to Docker Container

```bash
# Copy the verification script into the container
docker cp verify_resnet50_benchmark.py secureai-backend:/app/
```

## Step 3: Run Verification

```bash
# Run the verification script inside the container
docker exec secureai-backend python /app/verify_resnet50_benchmark.py
```

## Alternative: Run Directly from Project Directory

If the script is in the project directory that's mounted in the container:

```bash
# Check if script exists in container
docker exec secureai-backend ls -la /app/verify_resnet50_benchmark.py

# If it exists, run it
docker exec secureai-backend python /app/verify_resnet50_benchmark.py

# If it doesn't exist, copy it first
docker cp verify_resnet50_benchmark.py secureai-backend:/app/
docker exec secureai-backend python /app/verify_resnet50_benchmark.py
```

## Troubleshooting

### If "no such file or directory" error:

1. **Check if file exists on server:**
   ```bash
   ls -la verify_resnet50_benchmark.py
   ```

2. **If file doesn't exist, pull from GitHub:**
   ```bash
   git pull origin master
   ```

3. **Verify file is there:**
   ```bash
   ls -la verify_resnet50_benchmark.py
   ```

4. **Then copy to container:**
   ```bash
   docker cp verify_resnet50_benchmark.py secureai-backend:/app/
   ```

### If script can't find model file:

The script looks for the model in these locations:
- `ai_model/resnet_resnet50_final.pth`
- `ai_model/resnet_resnet50_best.pth`

Check if model exists:
```bash
docker exec secureai-backend ls -la /app/ai_model/resnet*.pth
```

### If script can't find test data:

The script will still run but skip benchmarking. Test data should be in:
- `datasets/train/real/` and `datasets/train/fake/`
- `datasets/val/real/` and `datasets/val/fake/`

Check if test data exists:
```bash
docker exec secureai-backend ls -la /app/datasets/train/
```

