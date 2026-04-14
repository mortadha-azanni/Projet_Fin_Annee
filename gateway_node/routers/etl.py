from fastapi import APIRouter, HTTPException, Depends, WebSocket
import httpx
import websockets
from core.config import settings
from auth.dependencies import get_current_admin
from auth.models import TokenData

router = APIRouter()

@router.post("/launch")
async def launch_scraping(current_admin: TokenData = Depends(get_current_admin)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.SCRAPER_URL}/scrape/launch")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")

@router.post("/pause")
async def pause_scraping(admin: TokenData = Depends(get_current_admin)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.SCRAPER_URL}/scrape/pause")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")

@router.post("/resume")
async def resume_scraping(admin: TokenData = Depends(get_current_admin)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.SCRAPER_URL}/scrape/resume")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")

@router.post("/stop")
async def stop_scraping(admin: TokenData = Depends(get_current_admin)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.SCRAPER_URL}/scrape/stop")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")

@router.get("/status")
async def proxy_scraping_status(admin: TokenData = Depends(get_current_admin)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{settings.SCRAPER_URL}/scrape/status")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")

@router.websocket("/progress")
async def proxy_websocket_progress(websocket: WebSocket):
    await websocket.accept()
    scraper_ws_uri = f"{settings.scraper_ws_url}/websocket_progress"
    try:
        async with websockets.connect(scraper_ws_uri) as scraper_ws:
            while True:
                message = await scraper_ws.recv()
                # Ensure message format matches contract if needed
                await websocket.send_text(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"state": "error", "message": f"Gateway Websocket Error: {str(e)}"})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
