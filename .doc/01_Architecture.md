# Project Architecture

## Overview
The system is built as a microservices architecture utilizing Docker and Docker Compose for orchestration. It consists of multiple nodes handles different responsibilities orchestrating a complete application from web scraping to processing (ranking/AI search) and serving an interactive frontend.

## Services
According to `docker-compose.yml`, the application runs the following services:

1. **Gateway (`gateway`)**: Serves as the API Gateway pointing API requests from the frontend client to the Scraper and Ranker nodes. Maps port `:8000`.
2. **Scraper (`scraper`)**: A Python-based FastAPI service responsible for fetching and parsing web data. Communicates scraping states through a WebSocket. Maps port `:8001`.
3. **Ranker (`ranker`)**: A Python-based FastAPI service that runs complex search, ranking, and NLP operations like Semantic Search, BM25, and LLM functionality. Maps port `:8002`.
4. **Celery Worker (`celery_worker`)**: Operates asynchronous workers based on the Ranker node's image to handle background tasks effortlessly without blocking HTTP requests.
5. **Redis (`redis`)**: Serves as the message broker for Celery tasks in the Ranker node and as a fast in-memory store.

## Networking
All services are connected via a shared Docker network `pfa-network`, allowing internal routing via service names (e.g., `http://ranker:8000`).

## Volumes
Various volumes are mounted to preserve virtual environments (`_venv`), caching (`uv_cache`, `python_cache`), and ML model caching (`huggingface_cache` for the ranker).