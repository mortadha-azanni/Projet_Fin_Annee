from fastapi import FastAPI
import os

app = FastAPI(title="Gateway Node")

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
    return {"status": "healthy"}
