#!/usr/bin/env python3
"""
Celery Configuration
Configuration settings for Celery workers, tasks, and distributed processing
"""

import os
from typing import Dict, Any, List
from celery import Celery
from celery.schedules import crontab

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Celery Configuration
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Task Configuration
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Worker Configuration
CELERY_WORKER_CONCURRENCY = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))

# Task Execution Configuration
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_EAGER_RESULT = True

# Retry Configuration
CELERY_TASK_DEFAULT_RETRY_DELAY = int(os.getenv('CELERY_TASK_DEFAULT_RETRY_DELAY', '60'))
CELERY_TASK_MAX_RETRIES = int(os.getenv('CELERY_TASK_MAX_RETRIES', '3'))

# Rate Limiting Configuration
CELERY_TASK_ANNOTATIONS = {
    'celery_app.tasks.detect_video': {
        'rate_limit': '10/m',  # 10 tasks per minute
        'time_limit': 1800,   # 30 minutes max execution time
        'soft_time_limit': 1500,  # 25 minutes soft limit
        'max_retries': 3,
        'default_retry_delay': 60,
        'retry_backoff': True,
        'retry_backoff_max': 300,  # Max 5 minutes between retries
        'retry_jitter': True,
    }
}

# Result Backend Configuration
CELERY_RESULT_EXPIRES = int(os.getenv('CELERY_RESULT_EXPIRES', '3600'))  # 1 hour
CELERY_RESULT_CACHE_MAX = int(os.getenv('CELERY_RESULT_CACHE_MAX', '10000'))

# Monitoring Configuration
CELERY_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_DIRECT = True

# Security Configuration
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_LOG_COLOR = False
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Beat Schedule Configuration (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-results': {
        'task': 'celery_app.tasks.cleanup_expired_results',
        'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
    },
    'health-check': {
        'task': 'celery_app.tasks.health_check',
        'schedule': 60.0,  # Every minute
    },
    'monitor-gpu-usage': {
        'task': 'celery_app.tasks.monitor_gpu_usage',
        'schedule': 30.0,  # Every 30 seconds
    },
}

# GPU Configuration
CUDA_VISIBLE_DEVICES = os.getenv('CUDA_VISIBLE_DEVICES', '0')
GPU_MEMORY_FRACTION = float(os.getenv('GPU_MEMORY_FRACTION', '0.8'))
MIG_ENABLED = os.getenv('MIG_ENABLED', 'false').lower() == 'true'

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/deepfake_detection')
DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '10'))
DATABASE_MAX_OVERFLOW = int(os.getenv('DATABASE_MAX_OVERFLOW', '20'))

# Cache Configuration
CACHE_TTL_EMBEDDINGS = int(os.getenv('CACHE_TTL_EMBEDDINGS', '86400'))  # 24 hours
CACHE_TTL_RESULTS = int(os.getenv('CACHE_TTL_RESULTS', '3600'))  # 1 hour
CACHE_KEY_PREFIX = os.getenv('CACHE_KEY_PREFIX', 'deepfake')

# Video Processing Configuration
VIDEO_PROCESSING_TIMEOUT = int(os.getenv('VIDEO_PROCESSING_TIMEOUT', '1800'))  # 30 minutes
MAX_VIDEO_SIZE_MB = int(os.getenv('MAX_VIDEO_SIZE_MB', '500'))
SUPPORTED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm']

# ML Model Configuration
MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', '/tmp/models')
RESNET50_MODEL_PATH = os.getenv('RESNET50_MODEL_PATH', 'resnet50_pretrained.pth')
CLIP_MODEL_NAME = os.getenv('CLIP_MODEL_NAME', 'ViT-B/32')
ENSEMBLE_WEIGHTS = {
    'resnet50': float(os.getenv('ENSEMBLE_WEIGHT_RESNET50', '0.6')),
    'clip': float(os.getenv('ENSEMBLE_WEIGHT_CLIP', '0.4')),
}

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', '/var/log/celery_worker.log')

# Error Handling Configuration
MAX_CONCURRENT_FAILURES = int(os.getenv('MAX_CONCURRENT_FAILURES', '10'))
FAILURE_COOLDOWN_SECONDS = int(os.getenv('FAILURE_COOLDOWN_SECONDS', '300'))  # 5 minutes

# Performance Monitoring
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
METRICS_INTERVAL = int(os.getenv('METRICS_INTERVAL', '60'))  # seconds

# Configuration validation
def validate_configuration() -> Dict[str, Any]:
    """
    Validate Celery configuration settings.
    
    Returns:
        Dict containing validation results
    """
    validation_results = {
        'redis_connection': {
            'valid': True,
            'host': REDIS_HOST,
            'port': REDIS_PORT,
            'db': REDIS_DB
        },
        'celery_settings': {
            'valid': True,
            'broker_url': CELERY_BROKER_URL,
            'result_backend': CELERY_RESULT_BACKEND,
            'worker_concurrency': CELERY_WORKER_CONCURRENCY
        },
        'task_settings': {
            'valid': True,
            'max_retries': CELERY_TASK_MAX_RETRIES,
            'retry_delay': CELERY_TASK_DEFAULT_RETRY_DELAY,
            'rate_limit': '10/m'
        },
        'gpu_settings': {
            'valid': True,
            'cuda_devices': CUDA_VISIBLE_DEVICES,
            'memory_fraction': GPU_MEMORY_FRACTION,
            'mig_enabled': MIG_ENABLED
        },
        'database_settings': {
            'valid': True,
            'pool_size': DATABASE_POOL_SIZE,
            'max_overflow': DATABASE_MAX_OVERFLOW
        },
        'cache_settings': {
            'valid': True,
            'embeddings_ttl': CACHE_TTL_EMBEDDINGS,
            'results_ttl': CACHE_TTL_RESULTS,
            'key_prefix': CACHE_KEY_PREFIX
        }
    }
    
    # Overall validation
    overall_valid = all(
        section.get('valid', False) for section in validation_results.values()
        if isinstance(section, dict)
    )
    validation_results['overall_valid'] = {'valid': overall_valid}
    
    return validation_results


# Create Celery app instance
def create_celery_app() -> Celery:
    """
    Create and configure Celery application instance.
    
    Returns:
        Configured Celery app
    """
    app = Celery('deepfake_detection')
    
    # Update configuration
    app.conf.update(
        broker_url=CELERY_BROKER_URL,
        result_backend=CELERY_RESULT_BACKEND,
        task_serializer=CELERY_TASK_SERIALIZER,
        result_serializer=CELERY_RESULT_SERIALIZER,
        accept_content=CELERY_ACCEPT_CONTENT,
        timezone=CELERY_TIMEZONE,
        enable_utc=CELERY_ENABLE_UTC,
        worker_concurrency=CELERY_WORKER_CONCURRENCY,
        worker_prefetch_multiplier=CELERY_WORKER_PREFETCH_MULTIPLIER,
        worker_max_tasks_per_child=CELERY_WORKER_MAX_TASKS_PER_CHILD,
        task_always_eager=CELERY_TASK_ALWAYS_EAGER,
        task_eager_propagates=CELERY_TASK_EAGER_PROPAGATES,
        task_ignore_result=CELERY_TASK_IGNORE_RESULT,
        task_store_eager_result=CELERY_TASK_STORE_EAGER_RESULT,
        task_default_retry_delay=CELERY_TASK_DEFAULT_RETRY_DELAY,
        task_max_retries=CELERY_TASK_MAX_RETRIES,
        task_annotations=CELERY_TASK_ANNOTATIONS,
        result_expires=CELERY_RESULT_EXPIRES,
        result_cache_max=CELERY_RESULT_CACHE_MAX,
        send_task_events=CELERY_SEND_TASK_EVENTS,
        task_send_sent_event=CELERY_TASK_SEND_SENT_EVENT,
        worker_send_task_events=CELERY_WORKER_SEND_TASK_EVENTS,
        worker_direct=CELERY_WORKER_DIRECT,
        worker_hijack_root_logger=CELERY_WORKER_HIJACK_ROOT_LOGGER,
        worker_log_color=CELERY_WORKER_LOG_COLOR,
        worker_log_format=CELERY_WORKER_LOG_FORMAT,
        worker_task_log_format=CELERY_WORKER_TASK_LOG_FORMAT,
        beat_schedule=CELERY_BEAT_SCHEDULE,
    )
    
    return app


# Export configuration
__all__ = [
    'create_celery_app',
    'validate_configuration',
    'CELERY_BROKER_URL',
    'CELERY_RESULT_BACKEND',
    'CELERY_TASK_ANNOTATIONS',
    'CACHE_TTL_EMBEDDINGS',
    'CACHE_TTL_RESULTS',
    'CACHE_KEY_PREFIX',
    'DATABASE_URL',
    'CUDA_VISIBLE_DEVICES',
    'GPU_MEMORY_FRACTION',
    'MIG_ENABLED',
    'ENSEMBLE_WEIGHTS',
    'SUPPORTED_VIDEO_FORMATS',
    'MAX_VIDEO_SIZE_MB',
    'VIDEO_PROCESSING_TIMEOUT'
]
