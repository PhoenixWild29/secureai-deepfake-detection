# Gunicorn Configuration for SecureAI Guardian Production Server
# Run with: gunicorn -c gunicorn_config.py api:app

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 300  # 5 minutes for video processing
keepalive = 5

# Logging
accesslog = "/var/log/secureai/access.log"
errorlog = "/var/log/secureai/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "secureai-guardian"

# Server mechanics
daemon = False
pidfile = "/var/run/secureai-guardian.pid"
umask = 0
user = None
group = None
tmp_redirect = False

# SSL (if running directly with SSL, but we recommend using Nginx as reverse proxy)
# keyfile = None
# certfile = None

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting SecureAI Guardian server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading SecureAI Guardian server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("SecureAI Guardian server is ready. Spawning workers...")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down SecureAI Guardian server...")

# Preload app for better performance
preload_app = True

# Max requests per worker before restart (helps prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Graceful timeout for worker restart
graceful_timeout = 30

