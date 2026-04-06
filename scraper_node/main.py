from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import redis
import json
import os


app = FastAPI(
    title="Scraper Node",
    description="Web scraping service - extracts content from URLs",
    version="0.1.0"
)

# --- Config from environment variables ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Cache scraped data for 10 minutes (600 seconds)
CACHE_TTL = 600


def get_redis():
    """Return a Redis client. Returns None if Redis is unavailable."""
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


# --- Response Models ---

class ScrapedItem(BaseModel):
    type: str   # e.g. "heading", "paragraph", "link"
    text: str
    url: str = ""  # only for links


class ScrapeResponse(BaseModel):
    url: str
    title: str
    data: List[ScrapedItem]
    from_cache: bool = False


# --- Helpers ---

def validate_url(url: str) -> None:
    """
    Basic SSRF protection: only allow http/https URLs pointing at
    public hostnames (not localhost or private IP ranges).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")

    hostname = parsed.hostname or ""
    # Block requests to localhost and common private/internal addresses
    blocked = ("localhost", "127.0.0.1", "::1", "0.0.0.0")
    if hostname.lower() in blocked or hostname.startswith("192.168.") \
            or hostname.startswith("10.") or hostname.startswith("172."):
        raise HTTPException(status_code=400, detail="Requests to internal addresses are not allowed")


# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "service": "scraper-node",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {"status": "healthy", "redis": "unknown"}
    r = get_redis()
    health_status["redis"] = "healthy" if r else "unavailable"
    return health_status


@app.get("/scrape", response_model=ScrapeResponse)
async def scrape(url: str):
    """
    Scrape a web page and return its title, headings, paragraphs and links.

    Results are cached in Redis for 10 minutes to avoid repeating
    the same scrape for the same URL.

    Args:
        url: The full URL to scrape (e.g. https://example.com)

    Returns:
        Page title and a list of extracted content items.
    """
    validate_url(url)

    cache_key = f"scrape:{url}"
    r = get_redis()
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return ScrapeResponse(**result)

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach URL: {exc}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code,
                            detail=f"URL returned an error: {exc}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Page title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "No title"

    items: List[ScrapedItem] = []

    # Headings (h1 -> h3)
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            items.append(ScrapedItem(type="heading", text=text))

    # First 5 paragraphs
    for tag in soup.find_all("p")[:5]:
        text = tag.get_text(strip=True)
        if text:
            items.append(ScrapedItem(type="paragraph", text=text))

    # First 10 links
    for tag in soup.find_all("a", href=True)[:10]:
        text = tag.get_text(strip=True)
        if text:
            items.append(ScrapedItem(type="link", text=text, url=tag["href"]))

    result = ScrapeResponse(url=url, title=title, data=items, from_cache=False)

    # Store in cache
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(result.dict()))

    return result
