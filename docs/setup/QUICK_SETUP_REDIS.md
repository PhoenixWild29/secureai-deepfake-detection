# Quick Redis Setup Guide

## Option 1: Docker (Easiest - Recommended)

If you have Docker Desktop installed:

```bash
docker run -d -p 6379:6379 --name redis-secureai redis
```

Verify it's running:
```bash
docker ps
```

## Option 2: WSL (Windows Subsystem for Linux)

If you have WSL installed:

```bash
wsl
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

## Option 3: Manual Windows Installation

1. Download Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`
3. Keep the window open (Redis runs in foreground)

## Configuration

After Redis is running, add to your `.env` file:

```bash
REDIS_URL=redis://localhost:6379/0
```

## Test Connection

Run:
```bash
py -c "from performance.caching import REDIS_AVAILABLE; print('Redis Available:', REDIS_AVAILABLE)"
```

Should output: `Redis Available: True`

