# ⚡ Performance Optimization Guide

## Overview

This guide covers performance optimization strategies for SecureAI Guardian.

## Caching Strategy

### Redis Caching

**Setup:**
```bash
# Install Redis
sudo apt-get install redis-server

# Configure in .env
REDIS_URL=redis://localhost:6379/0
```

**Usage:**
```python
from performance.caching import cached, invalidate_cache

@cached(ttl=300)  # Cache for 5 minutes
def get_dashboard_stats():
    # Expensive computation
    return stats

# Invalidate when data changes
invalidate_cache('dashboard_stats')
```

### Cache Keys

- Dashboard stats: `cache:dashboard_stats:*`
- Analysis results: `cache:analysis:*`
- User data: `cache:user:*`

---

## Database Optimization

### Indexes

Already configured in models:
- `analyses.created_at` - For sorting
- `analyses.user_id` - For user queries
- `analyses.verdict` - For filtering
- `analyses.blockchain_tx` - For blockchain lookups

### Query Optimization

**Use Eager Loading:**
```python
# Good: Single query
analyses = db.query(Analysis).options(
    joinedload(Analysis.user)
).all()

# Bad: N+1 queries
analyses = db.query(Analysis).all()
for a in analyses:
    user = a.user  # Separate query for each
```

**Limit Results:**
```python
# Always limit large queries
analyses = db.query(Analysis).limit(100).all()
```

**Use Pagination:**
```python
page = request.args.get('page', 1, type=int)
per_page = 100
analyses = db.query(Analysis).offset(
    (page - 1) * per_page
).limit(per_page).all()
```

---

## Frontend Optimization

### Code Splitting

Already configured in Vite. Components load on demand.

### Asset Optimization

**Build with optimizations:**
```bash
npm run build
# Minifies, tree-shakes, and optimizes
```

### CDN Configuration

**For S3 files:**
```python
# Use CloudFront CDN URL
CDN_URL = "https://d1234567890.cloudfront.net"
```

---

## API Response Optimization

### Compression

Nginx automatically compresses responses (configured in `nginx.conf`).

### Response Caching

```python
from flask import make_response
from functools import wraps

def cache_response(max_age=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            response = make_response(f(*args, **kwargs))
            response.cache_control.max_age = max_age
            response.cache_control.public = True
            return response
        return wrapper
    return decorator
```

---

## Video Processing Optimization

### Async Processing

Use Celery for background processing:

```python
from celery import Celery

celery = Celery('secureai')

@celery.task
def process_video_async(video_path):
    # Long-running video processing
    return result
```

### Batch Processing

Process multiple videos in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_video, path) for path in videos]
    results = [f.result() for f in futures]
```

---

## Monitoring Performance

### Application Metrics

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper
```

### Database Query Monitoring

Enable SQLAlchemy query logging:
```python
# In .env
SQL_DEBUG=true
```

---

## Load Testing

Run performance tests:
```bash
chmod +x tests/run_all_tests.sh
./tests/run_all_tests.sh
```

---

## Recommended Settings

### Small Scale (< 1000 users/day)
- Workers: 2-4
- Database: PostgreSQL on same server
- Cache: Redis (optional)
- Storage: Local or S3

### Medium Scale (1000-10000 users/day)
- Workers: 4-8
- Database: Separate PostgreSQL server
- Cache: Redis required
- Storage: S3 with CDN
- Load Balancer: Nginx

### Large Scale (> 10000 users/day)
- Workers: 8+
- Database: PostgreSQL cluster
- Cache: Redis cluster
- Storage: S3 with CloudFront
- Load Balancer: Multiple Nginx instances
- Auto-scaling: Kubernetes or similar

---

## Performance Checklist

- [ ] Redis caching enabled
- [ ] Database indexes created
- [ ] Query optimization applied
- [ ] Frontend assets minified
- [ ] CDN configured (if using S3)
- [ ] Gzip compression enabled
- [ ] Response caching configured
- [ ] Async processing for heavy tasks
- [ ] Monitoring and alerting set up

