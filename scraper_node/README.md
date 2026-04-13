# Scraper Node

Scraper Node manages ETL scraping lifecycle and publishes live progress updates.

## What It Does

- Launches scraping in Celery background tasks.
- Supports pause, resume, and stop control flow.
- Exposes current scraping status.
- Streams progress updates to websocket clients.

## Runtime Architecture

- FastAPI app in main.py handles control endpoints.
- Celery task is triggered via runScrapers.delay().
- Redis stores control state and task id.
- A Redis Pub/Sub listener forwards scraper progress events to connected websocket clients.

## API Endpoints

### GET /
Returns service metadata.

### GET /health
Returns service health.

### POST /scrape/launch
Starts a scraping run if no active run is in progress.

### POST /scrape/pause
Sets scraper control state to paused.

### POST /scrape/resume
Resumes a paused scraping run.

### POST /scrape/stop
Stops scraping and revokes current Celery task when available.

### GET /scrape/status
Returns in-memory status payload:

```json
{
  "state": "idle|running|paused|stopping|completed|error",
  "message": "status details",
  "urls_scraped": 0
}
```

### WS /websocket_progress
Pushes live status updates to connected clients.

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
- Exposed locally as port 8001.
