from celery import Celery
from app.config import settings

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
)

