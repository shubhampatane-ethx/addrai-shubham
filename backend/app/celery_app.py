"""
Celery Application Configuration
For background task processing
"""
from celery import Celery
from backend.app.core.config import settings

# Create Celery app
celery_app = Celery(
    "address_validation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['backend.app.tasks'])

# Batch processing tasks
from backend.app.tasks import validation_batch
