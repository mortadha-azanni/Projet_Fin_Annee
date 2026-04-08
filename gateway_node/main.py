from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
import websockets   #type: ignore
import httpx
import os
import json

app = FastAPI(
    title="Gateway Node",
    description="API Gateway for scraper and ranker microservices",
    version="0.1.0"
)

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


@app.get("/scrape-and-rank")
async def ETL(url: str):
    """
    Complete workflow: scrape URL and rank results
    
    Args:
        url: URL to scrape
    
    Returns:
        Ranked results from the scraped data
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Scrape the URL
            scrape_response = await client.get(
                f"{SCRAPER_URL}/scrape",
                params={"url": url}
            )
            scrape_response.raise_for_status()
            scrape_data = scrape_response.json()
            
            # Step 2: Rank the scraped data
            if scrape_data.get("data"):
                rank_response = await client.post(
                    f"{RANKER_URL}/rank",
                    json=scrape_data["data"]
                )
                rank_response.raise_for_status()
                rank_data = rank_response.json()
                
                return {
                    "success": True,
                    "url": url,
                    "scraped_items": len(scrape_data.get("data", [])),
                    "ranked_results": rank_data.get("ranked_items", []),
                    "final_response": rank_data.get("final_response", "")
                }
            else:
                return {
                    "success": True,
                    "url": url,
                    "scraped_items": 0,
                    "ranked_results": [],
                    "final_response": "",
                    "message": "No data scraped from URL"
                }
                
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Service error: {str(e)}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@app.post("/scrape/launch")
async def launch_scraping():
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
async def pause_scraping():
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
async def resume_scraping():
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
async def stop_scraping():
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
async def proxy_scraping_status():
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
