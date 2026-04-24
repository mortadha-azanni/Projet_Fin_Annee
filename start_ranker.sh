#!/bin/bash
cd ranker_node
export REDIS_HOST=localhost
export REDIS_PORT=6379
# We need Gemini API key for Ranker
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi
uv run uvicorn main:app --host 0.0.0.0 --port 8002 --reload
