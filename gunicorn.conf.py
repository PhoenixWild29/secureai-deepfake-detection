# Gunicorn configuration for SecureAI DeepFake Detection API

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, this can help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "/var/log/secureai/access.log"
errorlog = "/var/log/secureai/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "secureai_api"

# Server mechanics
daemon = False
pidfile = "/var/run/secureai/gunicorn.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"

# Application
wsgi_module = "wsgi:app"
pythonpath = "/path/to/secureai-deepfake-detection"