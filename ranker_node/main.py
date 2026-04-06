from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import redis
import json
import os
import hashlib


app = FastAPI(
    title="Ranker Node",
    description="Ranking service - scores and sorts scraped content items",
    version="0.1.0"
)

# --- Config from environment variables ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Cache ranking results for 5 minutes (300 seconds)
CACHE_TTL = 300


def get_redis():
    """Return a Redis client. Returns None if Redis is unavailable."""
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


# --- Request / Response Models ---

class Item(BaseModel):
    type: str
    text: str
    url: str = ""


class RankResponse(BaseModel):
    total: int
    ranked_items: List[Item]
    from_cache: bool = False


# --- Helpers ---

def score_item(item: Item) -> int:
    """
    Simple scoring rule (beginner-friendly):
    - Headings are more important than paragraphs, which beat links.
    - Within the same type, longer text gets a higher score.
    """
    type_bonus = {"heading": 100, "paragraph": 50, "link": 10}
    base = type_bonus.get(item.type, 0)
    return base + len(item.text)


# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "service": "ranker-node",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {"status": "healthy", "redis": "unknown"}
    r = get_redis()
    health_status["redis"] = "healthy" if r else "unavailable"
    return health_status


@app.post("/rank", response_model=RankResponse)
async def rank(items: List[Item]):
    """
    Rank a list of content items by importance.

    Results are cached in Redis for 5 minutes to avoid repeating
    the same ranking for identical input lists.

    Scoring:
    - Headings score highest (100 + text length)
    - Paragraphs score medium (50 + text length)
    - Links score lowest (10 + text length)

    Returns items sorted from highest to lowest score.
    """
    # Create a consistent cache key from the input items
    sorted_items = sorted(items, key=lambda x: (x.type, x.text, x.url))
    input_hash = hashlib.md5(json.dumps([item.dict() for item in sorted_items]).encode()).hexdigest()
    cache_key = f"rank:{input_hash}"

    r = get_redis()
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return RankResponse(**result)

    ranked = sorted(items, key=score_item, reverse=True)
    result = RankResponse(total=len(ranked), ranked_items=ranked, from_cache=False)

    # Store in cache
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(result.dict()))

    return result
