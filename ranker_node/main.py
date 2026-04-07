from fastapi import FastAPI
from typing import List

app = FastAPI(title="Ranker Node")


@app.get("/")
async def root():
    return {
        "service": "ranker-node",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/rank")
async def rank(items: List[dict]):
    """Rank a list of items"""
    return {
        "message": "Ranking functionality to be implemented",
        "ranked_items": items
    }
