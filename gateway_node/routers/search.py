from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import httpx
import websockets
import json
import uuid
import asyncio
from typing import Optional
from core.config import settings
from auth.dependencies import get_current_user, get_ws_user
from auth.models import TokenData

router = APIRouter()


class SearchQuery(BaseModel):
    query: str


@router.post("/search")
async def search(
    query_data: SearchQuery,
    current_user: TokenData = Depends(get_current_user),
):
    """
    POST /search — Contract §2, Step 1.
    Forwards the query to the ranker service and returns the real task_id
    that the frontend will use to connect to the WebSocket stream.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.RANKER_URL}/search",
                json={
                    "query": query_data.query,
                    "user_id": current_user.id,
                },
            )
            response.raise_for_status()
            data = response.json()
            # Ranker must return {"task_id": "...", "status": "..."}
            return {
                "task_id": data.get("task_id", str(uuid.uuid4())),
                "status": data.get("status", "Processing..."),
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ranker service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ranker service unreachable: {str(e)}",
        )


@router.websocket("/ws/status/{task_id}")
async def status_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(..., description="JWT token for authentication"),
):
    """
    WS /ws/status/{task_id} — Contract §2, Step 2.
    Authenticates the connection via ?token=<jwt>, then proxies the ranker's
    streaming events to the client, normalising them to the contract format.
    """
    # Validate token before accepting the WS upgrade
    try:
        get_ws_user.__wrapped__ if hasattr(get_ws_user, "__wrapped__") else None
        from core.security import decode_token
        token_data = decode_token(token)
        if token_data.role not in ("user", "admin"):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    message_id = str(uuid.uuid4())

    # Send 'start' event — signals the frontend to create the assistant message
    await websocket.send_json({
        "type": "start",
        "payload": {"message_id": message_id},
    })

    ranker_ws_uri = f"{settings.ranker_ws_url}/ws/status/{task_id}"

    try:
        async with websockets.connect(ranker_ws_uri) as ranker_ws:
            while True:
                message = await ranker_ws.recv()
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    # Non-JSON from ranker — treat as a plain text chunk
                    await websocket.send_json({
                        "type": "chunk",
                        "payload": {"message_id": message_id, "content": message},
                    })
                    continue

                event_type = data.get("type")
                state = data.get("state")

                if event_type == "chunk":
                    await websocket.send_json({
                        "type": "chunk",
                        "payload": {
                            "message_id": message_id,
                            "content": data.get("content") or data.get("text", ""),
                        },
                    })

                elif event_type == "products":
                    await websocket.send_json({
                        "type": "products",
                        "payload": {
                            "message_id": message_id,
                            "items": data.get("items") or data.get("data", []),
                        },
                    })

                elif event_type == "end" or state == "SUCCESS":
                    await websocket.send_json({
                        "type": "end",
                        "payload": {"message_id": message_id},
                    })
                    break

                elif event_type == "error" or state == "FAILURE":
                    await websocket.send_json({
                        "type": "error",
                        "payload": {
                            "message": data.get("message") or data.get("error", "Search failed"),
                        },
                    })
                    break

    except websockets.exceptions.ConnectionClosed:
        # Ranker closed the connection — signal end to client
        try:
            await websocket.send_json({
                "type": "end",
                "payload": {"message_id": message_id},
            })
        except Exception:
            pass

    except Exception as exc:
        try:
            await websocket.send_json({
                "type": "error",
                "payload": {"message": f"Gateway error: {str(exc)}"},
            })
        except Exception:
            pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
