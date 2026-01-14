# Troubleshooting: Console/Logs Stuck

## If Console is Stuck

If your terminal/console appears to be stuck or hanging:

### 1. **If running `docker logs -f` (following logs)**

Press `Ctrl + C` to exit the log following mode.

### 2. **If a command is hanging**

Press `Ctrl + C` to cancel the current command.

### 3. **Check if process is actually running**

Open a **new terminal window** and check:

```bash
# Check if containers are running
docker ps

# Check container status
docker stats
```

### 4. **If backend is stuck during startup**

```bash
# Check logs (without following)
docker logs secureai-backend --tail 50

# Restart if needed
docker compose -f docker-compose.https.yml restart secureai-backend
```

### 5. **If pulling/rebuilding is stuck**

```bash
# Cancel with Ctrl+C, then check network
ping google.com

# Try again with timeout
timeout 300 docker compose -f docker-compose.https.yml build secureai-backend
```

## Common Issues

### "Command not responding"
- Usually means it's waiting for input or processing
- Press `Ctrl + C` to cancel
- Check if it's actually working in another terminal

### "Logs not updating"
- If using `docker logs -f`, it will keep following
- Press `Ctrl + C` to stop following
- Use `docker logs secureai-backend --tail 50` for one-time view

### "Build taking forever"
- Docker builds can take 10-30 minutes
- Check with `docker ps` in another terminal
- Monitor with `docker stats`

