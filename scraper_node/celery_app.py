import os
from celery import Celery

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
broker_url = f"redis://{redis_host}:{redis_port}/0"

app = Celery(
    "scraper_tasks",
    broker=broker_url,
    backend=broker_url,
    include=["scraper"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
