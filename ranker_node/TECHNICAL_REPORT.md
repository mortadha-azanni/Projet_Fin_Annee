# Ranker Node Technical Report

## Purpose

Ranker Node provides asynchronous product search and ranking with websocket status streaming for frontend progress updates.

## Service Architecture

- API layer: main.py (FastAPI)
- Task execution: Celery worker from celery_app.py
- Task broker/backend: Redis
- Search modules:
  - BM25/
  - Hybrid/
  - LLM/
  - NER/
  - SementicSearch/

## Runtime Sequence

1. API receives POST /search with query.
2. Celery task Search.perform_search is enqueued.
3. Client subscribes to WS /ws/status/{task_id}.
4. Ranker emits state updates every 500 ms.
5. On SUCCESS, returns ranked results and final_response markdown.

## API Behavior Summary

- GET /: metadata
- GET /health: liveness
- POST /search: start async search task
- WS /ws/status/{task_id}: stream task state and final payload
- POST /rank: markdown formatting helper for ranked item lists

## Core Design Characteristics

- Non-blocking search request path using Celery.
- WebSocket-first status model for responsive UX.
- Separation between orchestration endpoint and search implementation modules.
- Final response generation decoupled in LLM.FLLM.MarkdownDescription.

## Operational Considerations

- First worker startup may download model artifacts and increase cold-start time.
- Redis availability is required for task dispatch/status retrieval.
- Concurrency in docker-compose is set to 1 for the ranker celery worker to reduce memory pressure.

## Integration Notes

- Gateway proxies both POST /search and WS /ws/status/{task_id}.
- Frontend hook useChat.js currently relies on this task-and-status workflow.