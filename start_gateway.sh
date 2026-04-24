#!/bin/bash
cd gateway_node
export REDIS_HOST=localhost
export REDIS_PORT=6379
export RANKER_URL="http://localhost:8002"
export SCRAPER_URL="http://localhost:8001"
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
