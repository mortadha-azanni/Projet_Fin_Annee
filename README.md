# PFA - Distributed E-commerce Search Platform

This repository contains a microservices-based product search platform built with FastAPI, Celery, Redis, PostgreSQL/pgvector, and React + Vite.

## Architecture

```text
Browser (React/Vite :5173)
        |
        | REST + WebSocket
        v
Gateway Node (:8000)
   |          |            |
   |          |            +--> Redis (:6380 local -> 6379 container)
   |          |
   |          +--> Ranker API (:8002 local -> 8000 container)
   |                    |
   |                    +--> Celery Worker (ranker_node/celery_app.py)
   |
   +--> Scraper API (:8001 local -> 8000 container)
                        |
                        +--> Celery Worker (scraper_node/celery_app.py)
```

## Services

- gateway_node: public backend entrypoint, auth endpoints, proxy endpoints, chat websocket.
- ranker_node: async search task execution and websocket task status.
- scraper_node: ETL/scraping control endpoints and progress websocket.
- my-react-app: chat UI and admin surface.
- redis: Celery broker and lightweight cache/history store.

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Node.js 18+ and npm
- 4-8 GB RAM available for Docker (ranker models are memory-heavy)

### 1) Start backend services

```bash
cp .env.example .env
# Fill required values in .env (at minimum GEMINI_API_KEY and DB variables)

docker compose build
docker compose up -d
docker compose ps
```

### 2) Start frontend

```bash
cd my-react-app
npm install
npm run dev
```

## Frontend Environment Variables

Create my-react-app/.env with:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Main API Surface (Gateway)

- GET /health
- GET /services/health
- POST /auth/register
- POST /auth/login
- POST /auth/admin/login
- WS /ws/chat/{user_id}?token=<jwt>
- POST /search
- WS /ws/status/{task_id}
- POST /scrape/launch (admin token required)
- POST /scrape/pause (admin token required)
- POST /scrape/resume (admin token required)
- POST /scrape/stop (admin token required)
- GET /scrape/status (admin token required)
- WS /websocket_progress

OpenAPI docs: http://localhost:8000/docs

## Repository Structure

- gateway_node/: API gateway + auth + proxying.
- ranker_node/: hybrid search pipeline, async ranking task handling.
- scraper_node/: scraper orchestration and ETL controls.
- my-react-app/: React frontend.
- docker-compose.yml: complete local stack.

## Operational Notes

- Ranker and scraper async workers rely on Redis health.
- Ranker startup can be slow on first run due to model downloads.
- If workers are killed with SIGKILL, increase Docker memory.

## Development

Backend logs:

```bash
docker compose logs -f gateway ranker scraper celery_worker scraper_worker
```

Stop services:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```
