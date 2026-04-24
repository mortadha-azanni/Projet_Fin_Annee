import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
from scraper import runScrapers
from src.core.control import (
    SCRAPER_CONTROL_STATE_KEY,
    SCRAPER_PROGRESS_CHANNEL,
    SCRAPER_TASK_ID_KEY,
)
import redis.asyncio as redis  #type: ignore
from src.database.session import getProductsCount

# Redis Configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"
logger = logging.getLogger(__name__)


def apply_server_state(data: dict) -> None:
    scraping_status.update({
        "state": data.get("state", scraping_status["state"]),
        "message": data.get("message", scraping_status["message"]),
        "urls_scraped": data.get("urls_scraped", scraping_status["urls_scraped"]),
    })

async def redis_listener():
    """Background task to listen for progress updates from Celery via Redis Pub/Sub"""
    r = redis.from_url(redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(SCRAPER_PROGRESS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                update_scraping_status(
                    state=data.get("state", scraping_status["state"]),
                    message=data.get("message", scraping_status["message"]),
                    urls_scraped=data.get("urls_scraped", scraping_status["urls_scraped"]),
                    last_sync=data.get("last_sync", scraping_status["last_sync"]),
                    total_records=data.get("total_records", scraping_status["total_records"]),
                    index_latency_ms=data.get("index_latency_ms", scraping_status["index_latency_ms"]),
                    pipeline_health=data.get("pipeline_health", scraping_status["pipeline_health"]),
                )
                # Broadcast to connected WS clients
                await broadcast_progress(scraping_status)
    except asyncio.CancelledError:
        await pubsub.unsubscribe("scraper_progress")
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global r_client
    r_client = redis.from_url(redis_url, decode_responses=True)
    
    # Always boot in idle state; scraping must be started explicitly by /scrape/launch.
    await r_client.set("scraper_control_state", ScrapingState.IDLE.value)
    await r_client.delete("current_scraper_task_id")
    apply_server_state({
        "state": ScrapingState.IDLE.value,
        "message": "Scraping is idle",
        "urls_scraped": 0,
    })

    # Start Redis listener background task
    listener_task = asyncio.create_task(redis_listener())
    yield
    # Shutdown cleanup
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    finally:
        if r_client:
            await r_client.aclose()


app = FastAPI(title="Scraper Node", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track scraping state
scraping_status = {
    "state": "idle",
    "message": "Scraping is idle",
    "urls_scraped": 0,
    "last_sync": None,
    "total_records": 0,
    "index_latency_ms": None,
    "pipeline_health": "Healthy",
}

# WebSocket clients
active_connections: list[WebSocket] = []

class ScrapingState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"

# WebSocket helper --------------------------------
def update_scraping_status(**updates) -> None:
    scraping_status.update(updates)


# WebSocket helper --------------------------------
async def broadcast_progress(message: dict):
    stale_connections = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            stale_connections.append(connection)

    for connection in stale_connections:
        if connection in active_connections:
            active_connections.remove(connection)

#WebSocket Endpoint --------------------------------
@app.websocket("/websocket_progress")
async def websocket_progress(websocket: WebSocket):
    """Admin connects here to receive real time scraping progress updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send initial state immediately
    await websocket.send_json(scraping_status)
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Basic endpoints --------------------------------
@app.get("/")
async def root():
    return {
        "service": "scraper-node",
        "status": "running"
    }
@app.get("/health")
async def health():
    return {"status": "healthy"}

# ET controllers
r_client: redis.Redis | None = None

@app.post("/scrape/launch")
async def launch_scraping():
    if scraping_status["state"] == ScrapingState.RUNNING:
        return {"state": "error", "message": "Scraping is already running"}
    
    update_scraping_status(
        state=ScrapingState.RUNNING,
        message="Scraping started - queueing background task",
        urls_scraped=0,
        pipeline_health="Running",
    )

    await broadcast_progress(scraping_status)
    
    # Launch Celery background task
    await r_client.set(SCRAPER_CONTROL_STATE_KEY, "running")
    task = runScrapers.delay()
    logger.info("Scraping launched manually, task_id=%s", task.id)
    await r_client.set("current_scraper_task_id", task.id)
    
    return {"state": "running", "message": "Scraping launched successfully"}

@app.post("/scrape/pause")
async def pause_scraping():
    if scraping_status["state"] != ScrapingState.RUNNING:
        return {"state": "error", "message": "No scraping process is currently running"}
    
    # Let background tasks know it should sleep loops
    await r_client.set(SCRAPER_CONTROL_STATE_KEY, "paused")
    
    update_scraping_status(
        state=ScrapingState.PAUSED,
        message="Scraping paused by admin",
        pipeline_health="Paused",
    )

    await broadcast_progress(scraping_status)
    return {"state": "paused", "message": "Scraping paused successfully"}

@app.post("/scrape/resume")
async def resume_scraping():
    if scraping_status["state"] != ScrapingState.PAUSED:
        return {"state": "error", "message": "Scraping is not currently paused"}
    
    # Wake up background tasks
    await r_client.set(SCRAPER_CONTROL_STATE_KEY, "running")
    
    update_scraping_status(
        state=ScrapingState.RUNNING,
        message="Scraping resumed by admin",
        pipeline_health="Running",
    )

    await broadcast_progress(scraping_status)
    return {"state": "running", "message": "Scraping resumed successfully"}

@app.post("/scrape/stop")
async def stop_scraping():
    if scraping_status["state"] not in [ScrapingState.RUNNING, ScrapingState.PAUSED]:
        return {"state": "error", "message": "No scraping process is currently running or paused"}
    
    await r_client.set(SCRAPER_CONTROL_STATE_KEY, "stopped")
    
    # Optional: Hard revoke from celery just in case it's ignoring loops
    task_id = await r_client.get(SCRAPER_TASK_ID_KEY)
    if task_id:
        from celery_app import app as celery_app
        celery_app.control.revoke(task_id, terminate=True)
    
    update_scraping_status(
        state=ScrapingState.IDLE,
        message="Scraping stopped by admin",
        pipeline_health="Stopped",
    )
    
    await broadcast_progress(scraping_status)
    return {"state": "idle", "message": "Scraping stopped successfully"}

@app.get("/scrape/status")
async def get_scraping_status():
    return scraping_status


@app.get("/scrape/db-count")
async def get_scrape_db_count():
    try:
        products_in_db = await asyncio.to_thread(getProductsCount)
        return {"products_in_db": products_in_db}
    except Exception as error:
        logger.exception("Failed reading products count from database")
        return {"products_in_db": 0, "error": str(error)}
