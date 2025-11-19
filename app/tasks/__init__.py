# Import tasks to register them with Celery
from app.tasks.import_tasks import import_products_task

__all__ = ['import_products_task']

