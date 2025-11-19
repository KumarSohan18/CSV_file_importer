from celery import Celery
from celery.signals import worker_ready
from app.config import settings
import redis
import sys

def clear_redis_keys():
    """Clear corrupted Celery result keys from Redis"""
    try:
        r = redis.from_url(settings.CELERY_RESULT_BACKEND, decode_responses=False)
        # Clear ALL Celery-related keys
        patterns = ['celery-task-meta-*']
        total_cleared = 0
        for pattern in patterns:
            keys = r.keys(pattern)
            if keys:
                r.delete(*keys)
                total_cleared += len(keys)
        if total_cleared > 0:
            print(f"Cleared {total_cleared} Celery keys")
    except Exception as e:
        print(f"Warning: Could not clear Redis: {e}")

# Clear at import time (backup)
if 'celery' in sys.argv[0].lower() or 'worker' in ' '.join(sys.argv).lower():
    clear_redis_keys()

celery_app = Celery(
    "product_importer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.import_tasks"]
)

# Clear corrupted Celery results when worker is ready (primary clearing point)
@worker_ready.connect
def clear_corrupted_results(sender=None, **kwargs):
    """Clear all Celery result keys when worker starts to prevent corruption errors"""
    clear_redis_keys()

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Optimize for large file processing
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Process one task at a time for large imports
    task_time_limit=3600,  # 1 hour timeout for large files
    task_soft_time_limit=3300,  # 55 minutes soft limit
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # Results expire after 1 hour
    # Increase message size limits for large file uploads (500MB max)
    broker_transport_options={
        'max_connections': 10,
        'visibility_timeout': 3600,
    },
    # For Redis backend, increase max message size
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_policy': {
            'timeout': 5.0
        }
    },
)

