from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
import httpx
import os

app = FastAPI(
    title="Gateway Node",
    description="API Gateway for scraper and ranker microservices",
    version="0.1.0"
)

SCRAPER_URL = os.getenv("SCRAPER_URL", "http://localhost:8001")
RANKER_URL = os.getenv("RANKER_URL", "http://localhost:8002")
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

