from fastapi import FastAPI

app = FastAPI(title="Scraper Node")


@app.get("/")
async def root():
    return {
        "service": "scraper-node",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/scrape")
async def scrape(url: str):
    """Scrape data from a given URL"""
    return {
        "url": url,
        "message": "Scraping functionality to be implemented",
        "data": []
    }
