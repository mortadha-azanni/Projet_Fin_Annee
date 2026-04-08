# Gateway Node Details

## Overview
The Gateway Node is developed using FastAPI (`gateway_node/main.py`). It acts as a reverse proxy/facade that simplifies traffic to downstream microservices seamlessly.

## Key Features
- **Routing**: Abstracts direct connections to the Ranker (`localhost:8002`) and Scraper (`localhost:8001`) services.
- **WebSockets**: Acts as a WebSocket proxy orchestrating messages between the backend processing streams (e.g., job statuses) and the frontend seamlessly.
- **CORS Handling**: `CORSMiddleware` is configured broadly to permit cross-origin requests from the React frontend interface.
- **Resilience**: Operates within a `pfa-network` to transparently map environment variables like `SCRAPER_URL` and `RANKER_URL` into actionable REST boundaries.

## Build configuration
Running via `uv run uvicorn`, built with `Dockerfile` and managed with `pyproject.toml` dependencies.