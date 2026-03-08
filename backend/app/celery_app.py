from celery import Celery

from app.config import settings

celery = Celery("stock_tracer")

celery.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
)

# Auto-discover tasks in app/tasks/
celery.autodiscover_tasks(["app.tasks"])
