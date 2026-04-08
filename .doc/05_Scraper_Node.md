# Scraper Node Details

## Overview
The Scraper node (`scraper_node/main.py`) controls ingestion routines. Built with FastAPI, it coordinates processes to extract web data to be analyzed later.

## Execution and State
Scraping can be quite intensive and stateful. The FastAPI application exposes:
- **State Trackers**: A `ScrapingState` enum tracks states exactly through: `IDLE`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, and `ERROR`.
- **Global Status**: `scraping_status` map holds real-time tracking (e.g., `urls_scraped`).

## WebSockets
It manages an active broadcast system.
- Endpoint `websocket_progress` is exposed for listening to job updates.
- Functions like `broadcast_progress` fan out JSON payloads to all connected admin panels informing them instantly when web entities are retrieved or states change.

## Lifecycle
It runs on port `8001` via unbuffered python execution ensuring stdout logs are captured actively by `docker compose logs`.