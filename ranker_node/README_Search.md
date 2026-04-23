# Ranker Search Pipeline (Implementation Guide)

This document explains how ranker_node search is structured and how it is consumed by the gateway/frontend.

## End-to-End Flow

1. Client sends query to gateway POST /search.
2. Gateway proxies to ranker POST /search.
3. Ranker enqueues Search.perform_search as a Celery task.
4. Client subscribes to WS /ws/status/{task_id} (usually through gateway proxy).
5. Ranker emits task states until SUCCESS/FAILURE.
6. On SUCCESS, payload includes results and final_response markdown.

## Search Pipeline Components

- NER/: entity extraction and normalization.
- LLM/: prompt-driven query expansion and response shaping.
- BM25/: lexical scoring logic.
- SementicSearch/: embedding utilities and semantic retrieval helpers.
- Hybrid/fusion.py: reciprocal rank fusion of lexical and semantic scores.

## Typical Retrieval Strategy

- Parse user intent and constraints (brand/spec/price).
- Generate semantic embedding context.
- Retrieve semantic candidates.
- Re-rank with BM25 to prioritize strict keyword matches.
- Fuse rankings into final ordered products.

## API Contracts Relevant to Search

### POST /search

Request:

```json
{
  "query": "ultrabook i7 16gb under 3000 dt"
}
```

Response:

```json
{
  "task_id": "<task-id>",
  "message": "Search task started"
}
```

### WS /ws/status/{task_id}

Possible states:

- PENDING
- PROGRESS
- SUCCESS
- FAILURE

SUCCESS payload includes:

- results: ranked products list
- final_response: markdown response text for chat UI
- cache_key: optional cache key

## Environment

Expected runtime variables include database, Redis, and model/API settings (configured through root .env and docker-compose).

## Local Execution

```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
uv run celery -A celery_app worker --loglevel=info
```
