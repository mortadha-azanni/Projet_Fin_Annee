from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from importlib import import_module

AsyncResult = import_module("celery.result").AsyncResult

from LLM.FLLM import MarkdownDescription
from celery_app import celery_app
from core.sanitization import SanitizedSearchQuery, SanitizedConstraints, SanitizedEntities, validate_and_sanitize_input

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
    user_id: Optional[str] = None
    intent: Optional[str] = None
    constraints: Optional[dict] = None
    entities: Optional[dict] = None
    semantic_cache_key: Optional[str] = None

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
    # Validate and sanitize input
    try:
        sanitized_query = SanitizedSearchQuery(query=query_data.query)
        sanitized_constraints = (
            SanitizedConstraints(**query_data.constraints)
            if query_data.constraints
            else SanitizedConstraints(max_price=None, location=None, filters=None)
        )
        sanitized_entities = (
            SanitizedEntities(**query_data.entities)
            if query_data.entities
            else SanitizedEntities(products=None, brands=None, categories=None, dates=None)
        )
    except Exception as e:
        return {
            "error": f"Input validation failed: {str(e)}",
            "task_id": None,
            "status": "Validation Error"
        }

    # Sanitize user_id if provided
    user_id = validate_and_sanitize_input(query_data.user_id) if query_data.user_id else None
    intent = validate_and_sanitize_input(query_data.intent) if query_data.intent else "search"
    semantic_cache_key = validate_and_sanitize_input(query_data.semantic_cache_key) if query_data.semantic_cache_key else None

    kwargs = {
        "user_query_str": sanitized_query.query,
        "user_id": user_id,
        "intent": intent,
        "constraints": sanitized_constraints.dict(exclude_unset=True) if sanitized_constraints else {},
        "entities": sanitized_entities.dict(exclude_unset=True) if sanitized_entities else {},
        "semantic_cache_key": semantic_cache_key,
    }
    task = celery_app.send_task("Search.perform_search", kwargs=kwargs)
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
                final_response = task.result.get('final_response') or task.result.get('message') or ''
                response = {
                    "state": state,
                    "status": "Search Complete",
                    "results": task.result.get('results', []),
                    "final_response": final_response,
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
