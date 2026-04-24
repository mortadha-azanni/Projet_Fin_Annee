# Gateway Node

API Gateway service that handles authentication, caching, and orchestrates requests between microservices.

## Features

- JWT authentication for users and admins
- WebSocket chat with token-by-token streaming
- Redis caching (TTL 30min) and conversation history (last 5)
- Routes requests to scraper and brain microservices
- Health monitoring for all services

## Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service information |
| GET | `/health` | Gateway health check |
| GET | `/services/health` | Health check for all downstream services |
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and get JWT token |
| POST | `/auth/admin/login` | Admin login and get JWT token |

### User Protected (JWT required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/chat/{user_id}?token=xxx` | Main chat WebSocket with streaming |

### Admin Protected (Admin JWT required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scrape/launch` | Trigger scraping process |
| POST | `/scrape/pause` | Pause scraping process |
| POST | `/scrape/resume` | Resume scraping process |
| POST | `/scrape/stop` | Force stop scraping process |
| GET | `/scrape/status` | Check scraping status |
| POST | `/search` | Forward search request to ranker |

### WebSocket Proxies

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/scrape/progress` | Proxies scraper progress to admin |
| WS | `/ws/status/{task_id}` | Proxies ranker status to client |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SCRAPER_URL` | Scraper service URL | `http://localhost:8001` |
| `RANKER_URL` | Ranker service URL | `http://localhost:8002` |
| `BRAIN_URL` | Brain service URL | `http://brain:8001` |
| `REDIS_HOST` | Redis host | `localhost` |
| `SUPABASE_URL` | Supabase project URL | required |
| `SUPABASE_KEY` | Supabase anon key | required |
| `JWT_SECRET_KEY` | Secret key for JWT signing | required |

## Auth Folder Structure

    auth/
    ├── __init__.py
    ├── router.py        ← register, login, admin login endpoints
    ├── jwt.py           ← JWT token creation and validation
    ├── dependencies.py  ← get_current_user, get_current_admin
    └── models.py        ← Pydantic models

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client for inter-service communication
- `redis` - Redis client for caching and history
- `supabase` - Supabase client for user storage
- `python-jose` - JWT token handling
- `passlib` - Password hashing
- `websockets` - WebSocket proxying

## Development

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```