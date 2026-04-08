# Ranker Node Details

## Overview
The Ranker Node holds the critical AI, information retrieval, and search logic of the architecture. It is implemented in FastAPI (`ranker_node/main.py`) paired with Celery for background asynchronous task processing (`celery_app.py`).

## Core Modules
Located within `ranker_node/`:
- **BM25**: Runs Best Matching 25 logic (`BM25Engine.py`) for sparse keyword-based retrieval.
- **SemanticSearch**: Utilizes transformer embeddings to achieve conceptually rich dense search capability (`SementicEngine.py`).
- **Hybrid**: Merges results (via `fusion.py`) from dense and sparse retrieval ensuring optimal ranking metrics.
- **NER (Named Entity Recognition)**: Extracts structure efficiently out of unstructured chunks (`entity_extractor.py`, `normalizer.py`).
- **LLM**: Large Language Model connectors to build descriptive outputs and summaries (`LLM.py`, `FLLM.py`).

## Architecture
- **API Endpoint**: `POST /search` triggers `perform_search.delay(...)` sending the query job to Redis. It returns a `task_id` rather than blocking.
- **Real-time Status**: Implements a `/ws/status/{task_id}` WebSocket to allow the frontend/gateway to track the Celery job's precise state incrementally.