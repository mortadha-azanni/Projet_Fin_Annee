from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import httpx
import websockets
import json
import uuid
import asyncio
from typing import List, Optional
from core.config import settings
from auth.dependencies import get_current_user
from auth.models import TokenData

router = APIRouter()

class SearchQuery(BaseModel):
    query: str

@router.post("")
async def search(query_data: SearchQuery, current_user: TokenData = Depends(get_current_user)):
    """
    Initial search request. Returns a task_id for WebSocket tracking.
    Matches Step 1 of the contract.
    """
    task_id = str(uuid.uuid4())
    # In a real system, we might trigger a background task or store the query state.
    # For now, we return the task_id which the frontend will use to connect to WS.
    return {
        "task_id": task_id,
        "status": "Processing..."
    }

@router.websocket("/status/{task_id}")
async def status_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket for real-time streaming of search results.
    Matches Step 2 of the contract.
    """
    await websocket.accept()
    
    # Generate a message_id for this session
    message_id = str(uuid.uuid4())
    
    # Send 'start' event
    await websocket.send_json({
        "type": "start",
        "payload": {"message_id": message_id}
    })

    ranker_ws_uri = f"{settings.ranker_ws_url}/ws/status/{task_id}"
    
    try:
        # Connect to downstream ranker/brain
        async with websockets.connect(ranker_ws_uri) as ranker_ws:
            while True:
                message = await ranker_ws.recv()
                try:
                    data = json.loads(message)
                    
                    # Transform downstream events to match our contract
                    if data.get("type") == "chunk":
                        await websocket.send_json({
                            "type": "chunk",
                            "payload": {
                                "message_id": message_id,
                                "content": data.get("content") or data.get("text")
                            }
                        })
                    elif data.get("type") == "products":
                        await websocket.send_json({
                            "type": "products",
                            "payload": {
                                "message_id": message_id,
                                "items": data.get("items") or data.get("data")
                            }
                        })
                    elif data.get("state") in ["SUCCESS", "FAILURE"]:
                        if data.get("state") == "SUCCESS":
                            await websocket.send_json({
                                "type": "end",
                                "payload": {"message_id": message_id}
                            })
                        break
                except json.JSONDecodeError:
                    # Fallback for non-json messages if any
                    await websocket.send_json({
                        "type": "chunk",
                        "payload": {"message_id": message_id, "content": message}
                    })
                    
    except websockets.exceptions.ConnectionClosed:
        await websocket.send_json({
            "type": "end",
            "payload": {"message_id": message_id}
        })
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Search Error: {str(e)}"}
        })
    finally:
        try:
            await websocket.close()
        except:
            pass
