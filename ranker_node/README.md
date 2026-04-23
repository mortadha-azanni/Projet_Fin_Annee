# Ranker Node

Ranker Node exposes async search orchestration and task-status streaming.

## What It Does

- Accepts user search queries and schedules Celery tasks.
- Streams task lifecycle updates over WebSocket.
- Returns final ranked results and generated markdown response.
- Provides a helper endpoint to format ranked products into markdown.

## Runtime Architecture

- FastAPI app in main.py handles API and websocket traffic.
- Celery worker (celery_app.py) executes Search.perform_search tasks.
- Redis is used as broker/result backend for Celery task state.

## API Endpoints

### GET /
Returns service metadata.

### GET /health
Returns basic health status.

### POST /search
Starts a background search task.

Request body:

```json
{
  "query": "gaming laptop 16gb ram"
}
```

Response:

```json
{
  "task_id": "<celery-task-id>",
  "message": "Search task started"
}
```

### WS /ws/status/{task_id}
Streams task state updates until completion.

Success payload includes:

- state
- status
- results
- final_response
- cache_key

### POST /rank
Formats already-ranked items into a markdown response using LLM.FLLM.MarkdownDescription.

## Local Development

Install dependencies:

```bash
uv sync
```

Run API:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run worker:

```bash
uv run celery -A celery_app worker --loglevel=info
```

## Docker Mapping in Root Compose

- Container listens on 8000.
- Exposed locally as port 8002.

## Key Dependencies

- fastapi, uvicorn
- celery, redis
- sentence-transformers, gliner
- rank-bm25, pgvector, sqlalchemy
- google-genai

