from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
import websockets   #type: ignore
import httpx
import os
import json
from auth.router import router as auth_router
from auth.dependencies import get_current_admin
from auth.jwt import decode_token
from auth.models import TokenData
import redis.asyncio as aioredis


app = FastAPI(
    title="Gateway Node",
    description="API Gateway for scraper and ranker microservices",
    version="0.1.0"
)
app.include_router(auth_router, prefix="/auth", tags=["Auth"]) 

# Add CORS Middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str

SCRAPER_URL = os.getenv("SCRAPER_URL", "http://localhost:8001")
SCRAPER_WS_URL = SCRAPER_URL.replace("http://", "ws://").replace("https://", "wss://")
RANKER_URL = os.getenv("RANKER_URL", "http://localhost:8002")
RANKER_WS_URL = RANKER_URL.replace("http://", "ws://").replace("https://", "wss://")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")


CACHE_TTL = 1800  # 30mins
HISTORY_LIMIT = 5
BRAIN_URL = os.getenv("BRAIN_URL", "http://brain:8001")


async def get_redis():
    """Return async Redis client. Returns None if unavailable."""
    try:
        client = aioredis.Redis(host=REDIS_HOST, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        return None


async def get_history(r, user_id: str) -> list:
    """Fetch last 5 conversations for a user from Redis"""
    if not r:
        return []
    raw = await r.get(f"history:{user_id}")
    return json.loads(raw) if raw else []


async def save_history(r, user_id: str, history: list):
    """Save updated conversation history to Redis"""
    if not r:
        return
    history = history[-HISTORY_LIMIT:]
    await r.set(f"history:{user_id}", json.dumps(history))


async def get_cache(r, query: str):
    """Check if query results are cached"""
    if not r:
        return None
    raw = await r.get(f"cache:{query}")
    return json.loads(raw) if raw else None


async def set_cache(r, query: str, results: list):
    """Cache Top 20 results for 30 minutes"""
    if not r:
        return
    await r.setex(f"cache:{query}", CACHE_TTL, json.dumps(results))

@app.get("/")
async def root():
    return {
        "service": "gateway-node",
        "status": "running",
        "scraper_url": SCRAPER_URL,
        "ranker_url": RANKER_URL,
        "redis_host": REDIS_HOST
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.websocket("/ws/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """
    Main chat WebSocket endpoint.
    - Requires JWT token as query param: ws://gateway/ws/chat/123?token=xxx
    - Fetches history from Redis
    - Checks cache before forwarding to Brain
    - Streams Brain response token by token back to client
    """

    # 1. Validate JWT token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        decode_token(token)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    r = await get_redis()

    try:
        while True:
            # 2. Receive query from client
            query = await websocket.receive_text()

            # 3. Fetch conversation history from Redis
            history = await get_history(r, user_id)

            # 4. Check cache
            cached = await get_cache(r, query)
            if cached:
                await websocket.send_json({
                    "type": "results",
                    "data": cached,
                    "from_cache": True
                })
                continue

            # 5. Forward query + history to Brain and stream response
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{BRAIN_URL}/query",
                        json={"query": query, "history": history}
                    ) as response:
                        results = []
                        async for chunk in response.aiter_text():
                            await websocket.send_json({
                                "type": "token",
                                "data": chunk
                            })
                            results.append(chunk)

                # 6. Cache the results
                await set_cache(r, query, results)

                # 7. Update and save history
                history.append({"role": "user", "content": query})
                history.append({"role": "assistant", "content": "".join(results)})
                await save_history(r, user_id, history)

                # 8. Signal end of stream to client
                await websocket.send_json({"type": "done"})

            except httpx.RequestError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Could not reach Brain: {str(e)}"
                })

    except WebSocketDisconnect:
        pass

@app.get("/services/health")
async def check_services_health():
    """Check health of all downstream services"""
    health_status = {
        "gateway": "healthy",
        "scraper": "unknown",
        "ranker": "unknown"
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check scraper
        try:
            response = await client.get(f"{SCRAPER_URL}/health")
            health_status["scraper"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["scraper"] = f"error: {str(e)}"
        
        # Check ranker
        try:
            response = await client.get(f"{RANKER_URL}/health")
            health_status["ranker"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health_status["ranker"] = f"error: {str(e)}"
    
    return health_status





@app.post("/scrape/launch")
async def launch_scraping(current_admin: TokenData = Depends(get_current_admin)):
    """Proxy scrape launch request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/launch")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/pause")
async def pause_scraping(admin: TokenData = Depends(get_current_admin)):
    """Proxy scrape pause request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/pause")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/resume")
async def resume_scraping(admin: TokenData = Depends(get_current_admin)):
    """Proxy scrape resume request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/resume")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/stop")
async def stop_scraping(admin: TokenData = Depends(get_current_admin)):
    """Proxy scrape stop request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SCRAPER_URL}/scrape/stop")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scrape/status")
async def proxy_scraping_status(admin: TokenData = Depends(get_current_admin)):
    """Proxy scrape status request to scraper node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SCRAPER_URL}/scrape/status")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Scraper service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/websocket_progress")
async def proxy_websocket_progress(websocket: WebSocket):
    """Proxy websocket connection to scraper node for progress updates"""
    await websocket.accept()
    scraper_ws_uri = f"{SCRAPER_WS_URL}/websocket_progress"
    
    try:
        async with websockets.connect(scraper_ws_uri) as scraper_ws:
            while True:
                # Receive message from scraper node and send to frontend client
                message = await scraper_ws.recv()
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

@app.post("/search")
async def search(query_data: SearchQuery):
    """Proxy search request to ranker node"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{RANKER_URL}/search",
                json={"query": query_data.query}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
        raise HTTPException(status_code=status_code, detail=f"Ranker service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/status/{task_id}")
async def status_websocket(websocket: WebSocket, task_id: str):
    """Proxy websocket connection to ranker node"""
    await websocket.accept()
    ranker_ws_uri = f"{RANKER_WS_URL}/ws/status/{task_id}"
    
    try:
        async with websockets.connect(ranker_ws_uri) as ranker_ws:
            while True:
                # Receive message from ranker node and send to frontend client
                message = await ranker_ws.recv()
                await websocket.send_text(message)
                
                # Check for completion states
                try:
                    data = json.loads(message)
                    if data.get("state") in ["SUCCESS", "FAILURE"]:
                        break
                except:
                    pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"state": "FAILURE", "status": "Gateway Error", "error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
