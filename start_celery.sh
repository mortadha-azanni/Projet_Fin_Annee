#!/bin/bash
cd ranker_node
export REDIS_HOST=localhost
export REDIS_PORT=6379
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi
uv run celery -A celery_app worker --loglevel=info
