import os
from celery import Celery
import redis

# Use the Redis from docker-compose, or fallback to localhost
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_url = f"redis://{redis_host}:{redis_port}/1"

# Synchronous redis client for Gateway Pub/Sub (DB 0)
pubsub_redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=0,
    decode_responses=True
)

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
