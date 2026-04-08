import os
from celery import Celery

# Use the Redis from docker-compose, or fallback to localhost
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/1"

celery_app = Celery(
    "ranker_worker",
    broker=redis_url,
    backend=redis_url,
    include=["Search"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_memory_per_child=2000000, # 1.5GB
)
