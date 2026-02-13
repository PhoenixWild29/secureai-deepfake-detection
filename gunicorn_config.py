# Gunicorn Configuration for SecureAI Guardian Production Server
# Run with: gunicorn -c gunicorn_config.py api:app

import os
# Disable NNPACK before any other imports so PyTorch (loaded by app) does not spam "Unsupported hardware"
os.environ.setdefault('USE_NNPACK', '0')

import multiprocessing

# Server socket - Use environment variable or default to 0.0.0.0:8000 for Docker
bind = os.getenv('GUNICORN_BIND', "0.0.0.0:8000")
backlog = 2048

# Worker processes - Use environment variable or default
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', "gevent")
worker_connections = 1000
timeout = int(os.getenv('GUNICORN_TIMEOUT', '300'))  # 5 minutes for video processing
keepalive = 5

# Logging - Use /app/logs for Docker compatibility
log_dir = os.getenv('LOG_DIR', '/app/logs')
os.makedirs(log_dir, exist_ok=True)
accesslog = os.path.join(log_dir, "access.log")
errorlog = os.path.join(log_dir, "error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "secureai-guardian"

# Server mechanics
daemon = False
# Disable pidfile for Docker (not needed in containers, and app user can't write to /var/run/)
pidfile = None
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

def post_worker_init(worker):
    """Start worker immediately; load ensemble in background so /api/health works and container stays healthy."""
    import threading

    def _load_ensemble():
        try:
            worker.log.info("Background: loading full ensemble (2-5 min or more on low RAM)...")
            from ai_model.ensemble_detector import init_ensemble_blocking
            d = init_ensemble_blocking()
            if d is not None:
                worker.log.info("Ensemble loaded in worker; every scan will use the full ensemble.")
            else:
                worker.log.error("Ensemble failed to load. Scans will return 503 until it loads or worker restarts.")
        except Exception as e:
            worker.log.exception(f"Ensemble load failed: {e}")

    t = threading.Thread(target=_load_ensemble, daemon=True)
    t.start()
    worker.log.info("Worker bound and accepting connections. Ensemble loading in background; /api/health is live.")

# Preload app for better performance
preload_app = True

# Max requests per worker before restart (helps prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Graceful timeout for worker restart
graceful_timeout = 30

