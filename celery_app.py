from celery import Celery
from app.config import settings
import redis
import sys

# Clear corrupted Celery results on worker startup
if 'celery' in sys.argv[0].lower() or 'worker' in ' '.join(sys.argv).lower():
    try:
        r = redis.from_url(settings.CELERY_RESULT_BACKEND, decode_responses=False)
        # Clear only Celery result keys
        keys = r.keys('celery-task-meta-*')
        if keys:
            r.delete(*keys)
            print(f"Cleared {len(keys)} corrupted Celery result keys")
    except Exception as e:
        print(f"Warning: Could not clear Redis: {e}")

celery_app = Celery(
    "product_importer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.import_tasks"]

)

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
)

