from fastapi import FastAPI, Websocket, WebSocketDisconnect
from enum import Enum

app = FastAPI(title="Scraper Node")

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
async def websocket_progress(websocket: WebSocket):
    """Admin connects here to receivereal time scraping progress updates"""
    await websocket.accept()
    active_connections.append(websocket)
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

#ETL control endpoints --------------------------------
@app.post("/scrape/launch")
async def launch_scraping():
    if scraping_status["state"] == ScrapingState.RUNNING:
        return {"state": "error", "message": "Scraping is already running"}
    
    scraping_status["state"] = ScrapingState.RUNNING
    scraping_status["message"] = "Scraping started"
    scraping_status["urls_scraped"] = 0

    await broadcast_progress(scraping_status)
    return{"state": "running", "message": "Scraping launched sucessfully"}

@app.post("/scrape/pause")
async def pause_scraping():
    if scraping_status["state"] != ScrapingState.RUNNING:
        return {"state": "error", "message": "No scraping process is currently running"}
    
    scraping_status["state"] = ScrapingState.PAUSED
    scraping_status["message"] = "Scraping paused by admin"

    await broadcast_progress(scraping_status)
    return {"state": "paused", "message": "Scraping paused successfully"}

@app.post("/scrape/resume")
async def resume_scraping():
    if scraping_status["state"] != ScrapingState.PAUSED:
        return {"state": "error", "message": "Scraping is not currently paused"}
    
    scraping_status["state"] = ScrapingState.RUNNING
    scraping_status["message"] = "Scraping resumed by admin"

    await broadcast_progress(scraping_status)
    return {"state": "running", "message": "Scraping resumed successfully"}

@app.post("/scrape/stop")
async def stop_scraping():
    if scraping_status["state"] != ScrapingState.RUNNING:
        return {"state": "error", "message": "No scraping process is currently running"}
    
    scraping_status["state"] = ScrapingState.IDLE
    scraping_status["message"] = "Scraping stopped by admin"
    await broadcast_progress(scraping_status)

    await broadcast_progress(scraping_status)
    return {"state": "idle", "message": "Scraping stopped successfully"}

@app.get("/scrape/status")
async def get_scraping_status():
    return scraping_status
>>>>>>> Stashed changes
