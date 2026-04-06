from fastapi import FastAPI, HTTPException
from typing import Any
import httpx
import redis
import json
import os


app = FastAPI(
    title="Gateway Node",
    description="API Gateway that orchestrates the scraper and ranker services",
    version="0.1.0"
)

# --- Config from environment variables ---
SCRAPER_URL = os.getenv("SCRAPER_URL", "http://localhost:8001")
RANKER_URL = os.getenv("RANKER_URL", "http://localhost:8002")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Cache results for 5 minutes (300 seconds)
CACHE_TTL = 300


def get_redis():
    """Return a Redis client. Returns None if Redis is unavailable."""
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


# --- Endpoints ---

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
        "ranker": "unknown",
        "redis": "unknown"
    }

    # Check Redis
    r = get_redis()
    health_status["redis"] = "healthy" if r else "unavailable"

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
async def scrape_and_rank(url: str) -> Any:
    """
    Complete workflow: scrape a URL and return ranked results.

    Results are cached in Redis for 5 minutes to avoid repeating
    the same scrape for the same URL.

    Args:
        url: URL to scrape

    Returns:
        Ranked content items extracted from the page.
    """
    cache_key = f"scrape-and-rank:{url}"

    # --- Try cache first ---
    r = get_redis()
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return result

    # --- Call scraper ---
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            scrape_response = await client.get(
                f"{SCRAPER_URL}/scrape",
                params={"url": url}
            )
            scrape_response.raise_for_status()
            scrape_data = scrape_response.json()

            # --- Call ranker if there is data ---
            ranked_items = []
            if scrape_data.get("data"):
                rank_response = await client.post(
                    f"{RANKER_URL}/rank",
                    json=scrape_data["data"]
                )
                rank_response.raise_for_status()
                rank_data = rank_response.json()
                ranked_items = rank_data.get("ranked_items", [])

            result = {
                "success": True,
                "url": url,
                "title": scrape_data.get("title", ""),
                "scraped_items": len(scrape_data.get("data", [])),
                "ranked_results": ranked_items,
                "from_cache": False
            }

            # --- Store in cache ---
            if r:
                r.setex(cache_key, CACHE_TTL, json.dumps(result))

            return result

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
