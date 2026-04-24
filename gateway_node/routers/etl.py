from fastapi import APIRouter, HTTPException, Depends, WebSocket, Query
import httpx
import logging
import websockets
from core.config import settings
from auth.dependencies import get_current_admin
from auth.models import TokenData

router = APIRouter()
logger = logging.getLogger(__name__)


# ── HTTP proxy helpers ────────────────────────────────────────────────────────

async def _scraper_request(method: str, path: str) -> dict:
    """Call scraper and bubble up errors cleanly."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, f"{settings.SCRAPER_URL}{path}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Scraper error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Scraper unreachable: {str(e)}")


# ── ETL control endpoints (admin only) ───────────────────────────────────────

@router.post("/launch")
async def launch_scraping(admin: TokenData = Depends(get_current_admin)):
    """POST /scrape/launch — Start the scraper. Contract §3A."""
    return await _scraper_request("POST", "/scrape/launch")


@router.post("/pause")
async def pause_scraping(admin: TokenData = Depends(get_current_admin)):
    """POST /scrape/pause — Pause the scraper. Contract §3A."""
    return await _scraper_request("POST", "/scrape/pause")


@router.post("/resume")
async def resume_scraping(admin: TokenData = Depends(get_current_admin)):
    """POST /scrape/resume — Resume the scraper. Contract §3A."""
    return await _scraper_request("POST", "/scrape/resume")


@router.post("/stop")
async def stop_scraping(admin: TokenData = Depends(get_current_admin)):
    """POST /scrape/stop — Stop the scraper. Contract §3A."""
    return await _scraper_request("POST", "/scrape/stop")


@router.get("/status")
async def proxy_scraping_status(admin: TokenData = Depends(get_current_admin)):
    """
    GET /scrape/status — Contract §3A.
    Expected response shape:
    {
      "state": "idle" | "running" | "paused" | "error",
      "last_sync": "ISO timestamp",
      "total_records": 14200000,
      "index_latency_ms": 42,
      "pipeline_health": "Healthy"
    }
    """
    return await _scraper_request("GET", "/scrape/status")


@router.get("/db-count")
async def proxy_database_count():
    """GET /scrape/db-count — Proxy scraper database count endpoint."""
    return await _scraper_get("/scrape/db-count")


# ── ETL log WebSocket (admin only) ───────────────────────────────────────────

@router.websocket("/progress")
async def proxy_websocket_progress(
    websocket: WebSocket,
    token: str = Query(..., description="Admin JWT token"),
):
    """
    WS /scrape/progress — Contract §3B.
    Proxies real-time scraper log lines to the AdminETLPanel console.
    Requires admin token passed as ?token=<jwt>.

    Message format: {"time": "...", "level": "INFO|WARN|ERROR|WORK", "message": "..."}
    """
    # Validate admin token before accepting upgrade
    try:
        from core.security import decode_token
        token_data = decode_token(token)
        if token_data.role != "admin":
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    scraper_ws_uri = f"{settings.scraper_ws_url}/websocket_progress"

    try:
        async with websockets.connect(scraper_ws_uri) as scraper_ws:
            while True:
                message = await scraper_ws.recv()
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="ignore")
                await websocket.send_text(message)

    except websockets.exceptions.ConnectionClosed:
        logger.info("Scraper WS closed — ETL progress stream ended")

    except Exception as exc:
        logger.error("ETL WS proxy error: %s", exc)
        try:
            await websocket.send_json({
                "time": "00:00:00",
                "level": "ERROR",
                "message": f"Gateway proxy error: {str(exc)}",
            })
        except Exception:
            pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
