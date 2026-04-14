from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import httpx
import os
import json

from core.config import settings
from auth.router import router as auth_router
from routers.users import router as users_router
from routers.etl import router as etl_router
from routers.search import router as search_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API Gateway for scraper and ranker microservices",
    version=settings.VERSION
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(users_router, prefix="/user", tags=["User"])
app.include_router(etl_router, prefix="/scrape", tags=["ETL"])
app.include_router(search_router, prefix="/search", tags=["Search"])

# ─── Basic Endpoints ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "gateway-node",
        "status": "running",
        "version": settings.VERSION
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/services/health")
async def check_services_health():
    health_status = {
        "gateway": "healthy",
        "scraper": "unknown",
        "ranker": "unknown"
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{settings.SCRAPER_URL}/health")
            health_status["scraper"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["scraper"] = f"error: {str(e)}"
        try:
            response = await client.get(f"{settings.RANKER_URL}/health")
            health_status["ranker"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["ranker"] = f"error: {str(e)}"
    return health_status

# Legacy websocket progress proxy if still needed at root, 
# though it's now also in etl_router under /scrape/progress
@app.websocket("/websocket_progress")
async def legacy_proxy_websocket_progress(websocket: WebSocket):
    from routers.etl import proxy_websocket_progress
    await proxy_websocket_progress(websocket)

# Legacy status websocket proxy if still needed at root
@app.websocket("/ws/status/{task_id}")
async def legacy_status_websocket(websocket: WebSocket, task_id: str):
    from routers.search import status_websocket
    await status_websocket(websocket, task_id)
