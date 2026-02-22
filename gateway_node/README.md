# Gateway Node

API Gateway service that orchestrates requests between scraper and ranker microservices.

## Features

- Routes requests to appropriate microservices
- Health monitoring for all services
- Inter-service communication with error handling
- Future: Redis caching, rate limiting, authentication

## Endpoints

### `GET /`
Service information and configuration

### `GET /health`
Health check for gateway service

### `GET /services/health`
Check health status of all downstream services (scraper, ranker)

### `GET /scrape-and-rank`
Complete workflow that:
1. Calls scraper service to extract data from URL
2. Sends scraped data to ranker service
3. Returns ranked results

**Parameters:**
- `url` (query param): URL to scrape

**Example:**
```bash
curl "http://localhost:8000/scrape-and-rank?url=https://example.com"
```

## Environment Variables

- `SCRAPER_URL` - Scraper service URL (default: `http://localhost:8001`)
- `RANKER_URL` - Ranker service URL (default: `http://localhost:8002`)
- `REDIS_HOST` - Redis host (default: `localhost`)

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client for inter-service communication
- `redis` - Redis client (for future caching)

## Development

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```
