from celery import Celery
from helpdesk_agent.config.settings import settings

# Create Celery application
celery_app = Celery(
    "helpdesk_agent",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,  # 30 seconds max
    task_soft_time_limit=25,  # 25 seconds soft limit
    worker_prefetch_multiplier=1,  # Fair task distribution
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject if worker dies
)

# Optional: Configure task routing
celery_app.conf.task_routes = {
    "helpdesk_agent.queue.tasks.create_escalation_ticket_async": {"queue": "tickets"},
    "helpdesk_agent.queue.tasks.*": {"queue": "default"},
}

# Optional: Configure rate limits
celery_app.conf.task_annotations = {
    "helpdesk_agent.queue.tasks.create_escalation_ticket_async": {"rate_limit": "10/m"}
}


# For development: auto-discover tasks
celery_app.autodiscover_tasks(["helpdesk_agent.queue"])