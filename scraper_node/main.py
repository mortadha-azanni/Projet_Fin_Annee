import os
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
from scraper import runScrapers
import redis.asyncio as redis  #type: ignore

# Redis Configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"

async def redis_listener():
    """Background task to listen for progress updates from Celery via Redis Pub/Sub"""
    r = redis.from_url(redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("scraper_progress")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                # Update local global state
                scraping_status.update({
                    "state": data.get("state", scraping_status["state"]),
                    "message": data.get("message", scraping_status["message"]),
                    "urls_scraped": data.get("urls_scraped", scraping_status["urls_scraped"]),
                })
                # Broadcast to connected WS clients
                await broadcast_progress(scraping_status)
    except asyncio.CancelledError:
        await pubsub.unsubscribe("scraper_progress")
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Redis listener background task
    listener_task = asyncio.create_task(redis_listener())
    yield
    # Shutdown cleanup
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Scraper Node", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Track scraping state
scraping_status={
    "state": "idle",
    "message": "Scraping is idle",
    "urls_scraped": 0
}

#WebSocket clients
active_connections : list[WebSocket] = []

class ScrapingState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"



@app.get("/")
async def root():
    return {
        "service": "scraper-node",
        "status": "running"
    }

#WebSocket helper --------------------------------
async def broadcast_progress(message: dict):
    for connection in active_connections:
        await connection.send_json(message)

#WebSocket Endpoint --------------------------------
@app.websocket("/websocket_progress")
async def websocket_progress(websocket: WebSocket):
    """Admin connects here to receivereal time scraping progress updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send initial state immediately
    await websocket.send_json(scraping_status)
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)

#Basic endpoints --------------------------------
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
r_client = redis.Redis.from_url(redis_url, decode_responses=True)

@app.post("/scrape/launch")
async def launch_scraping():
    if scraping_status["state"] == ScrapingState.RUNNING:
        return {"state": "error", "message": "Scraping is already running"}
    
    scraping_status["state"] = ScrapingState.RUNNING
    scraping_status["message"] = "Scraping started - queueing background task"
    scraping_status["urls_scraped"] = 0

    await broadcast_progress(scraping_status)
    
    # Launch Celery background task
    await r_client.set("scraper_control_state", "running")
    task = runScrapers.delay()
    await r_client.set("current_scraper_task_id", task.id)
    
    return {"state": "running", "message": "Scraping launched successfully"}

@app.post("/scrape/pause")
async def pause_scraping():
    if scraping_status["state"] != ScrapingState.RUNNING:
        return {"state": "error", "message": "No scraping process is currently running"}
    
    # Let background tasks know it should sleep loops
    await r_client.set("scraper_control_state", "paused")
    
    scraping_status["state"] = ScrapingState.PAUSED
    scraping_status["message"] = "Scraping paused by admin"

    await broadcast_progress(scraping_status)
    return {"state": "paused", "message": "Scraping paused successfully"}

@app.post("/scrape/resume")
async def resume_scraping():
    if scraping_status["state"] != ScrapingState.PAUSED:
        return {"state": "error", "message": "Scraping is not currently paused"}
    
    # Wake up background tasks
    await r_client.set("scraper_control_state", "running")
    
    scraping_status["state"] = ScrapingState.RUNNING
    scraping_status["message"] = "Scraping resumed by admin"

    await broadcast_progress(scraping_status)
    return {"state": "running", "message": "Scraping resumed successfully"}

@app.post("/scrape/stop")
async def stop_scraping():
    if scraping_status["state"] not in [ScrapingState.RUNNING, ScrapingState.PAUSED]:
        return {"state": "error", "message": "No scraping process is currently running or paused"}
    
    await r_client.set("scraper_control_state", "stopped")
    
    # Optional: Hard revoke from celery just in case it's ignoring loops
    task_id = await r_client.get("current_scraper_task_id")
    if task_id:
        from celery_app import app as celery_app
        celery_app.control.revoke(task_id, terminate=True)
    
    scraping_status["state"] = ScrapingState.IDLE
    scraping_status["message"] = "Scraping stopped by admin"
    
    await broadcast_progress(scraping_status)
    return {"state": "idle", "message": "Scraping stopped successfully"}

@app.get("/scrape/status")
async def get_scraping_status():
    return scraping_status
