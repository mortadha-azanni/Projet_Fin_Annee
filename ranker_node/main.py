from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
import asyncio
from importlib import import_module

AsyncResult = import_module("celery.result").AsyncResult

from LLM.FLLM import MarkdownDescription
from celery_app import celery_app

app = FastAPI(title="Ranker Node")

# Allow all CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str

@app.get("/")
async def root():
    return {
        "service": "ranker-node",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/search")
async def search(query_data: SearchQuery):
    """Trigger an async search task and return its task ID"""
    task = celery_app.send_task("Search.perform_search", args=[query_data.query])
    return {"task_id": task.id, "message": "Search task started"}

@app.websocket("/ws/status/{task_id}")
async def status_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    task = AsyncResult(task_id)
    try:
        while True:
            # Current state of the celery task
            state = task.state

            # Gather whatever data is presently available
            if state == 'PENDING':
                response = {"state": state, "status": "Task is pending execution..."}
            elif state == 'PROGRESS':
                response = {
                    "state": state,
                    "status": task.info.get('status', 'Processing...') if task.info else 'Processing...'
                }
            elif state == 'SUCCESS':
                response = {
                    "state": state,
                    "status": "Search Complete",
                    "results": task.result.get('results', []),
                    "final_response": task.result.get('final_response', ''),
                    "cache_key": task.result.get('cache_key'),
                }
                await websocket.send_json(response)
                break
            elif state == 'FAILURE':
                response = {"state": state, "status": "Task Failed", "error": str(task.info)}
                await websocket.send_json(response)
                break
            else:
                response = {"state": state, "status": "Unknown state"}

            await websocket.send_json(response)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print(f"Client disconnected from task: {task_id}")

@app.post("/rank")
async def rank(items: List[dict]):
    """Generate the final markdown response for a list of ranked items."""
    final_response = MarkdownDescription(items).generate() if items else ""
    return {
        "message": "Ranking completed",
        "ranked_items": items,
        "final_response": final_response,
    }
