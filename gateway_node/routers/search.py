from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import httpx
import websockets
import json
import uuid
import asyncio
import re
from typing import Optional, Any
from core.config import settings
from auth.dependencies import get_current_user, get_ws_user
from auth.models import TokenData

router = APIRouter()


class SearchQuery(BaseModel):
    query: str


class ChatQuery(BaseModel):
    message: str


class IntentQuery(BaseModel):
    message: str


PRODUCT_INTENT_PATTERN = re.compile(
    r"(buy|purchase|recommend|suggest|looking for|need a|need an|find me|search|best|budget|price|laptop|pc|computer|phone|smartphone|tablet|headset|headphone|earbuds|keyboard|mouse|monitor|printer|camera|ssd|ram|gpu|iphone|samsung|xiaomi|macbook|lenovo|hp|asus|dell|portable|ordinateur|pc portable|t[ée]l[ée]phone|prix|produit|article)",
    re.IGNORECASE,
)


def heuristic_classify_intent(message: str) -> dict[str, Any]:
    if PRODUCT_INTENT_PATTERN.search(message):
        return {
            "intent": "product_search",
            "confidence": 0.72,
            "source": "heuristic",
            "reason": "Matched shopping/product keywords",
        }

    return {
        "intent": "normal_chat",
        "confidence": 0.68,
        "source": "heuristic",
        "reason": "No strong shopping keyword signal",
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None

    return None


async def llm_classify_intent(message: str) -> dict[str, Any] | None:
    if not settings.GEMINI_API_KEY:
        return None

    classifier_prompt = (
        "Classify the user message into one of two intents:\n"
        "- product_search: user wants product recommendations, comparisons, prices, specs, or shopping help\n"
        "- normal_chat: greetings, general conversation, non-shopping Q&A\n\n"
        "Return strict JSON only with this schema:\n"
        '{"intent":"product_search|normal_chat","confidence":0.0,"reason":"short reason"}\n\n'
        f"User message: {message}"
    )
    request_payload = {
        "contents": [{"parts": [{"text": classifier_prompt}]}],
        "generationConfig": {"temperature": 0.0, "topP": 0.1, "maxOutputTokens": 120},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=request_payload)
            if response.status_code == 429:
                return None
            response.raise_for_status()
            data = response.json()

        raw = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        parsed = extract_json_object(raw)
        if not parsed:
            return None

        intent = str(parsed.get("intent", "")).strip().lower()
        if intent not in {"product_search", "normal_chat"}:
            return None

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        return {
            "intent": intent,
            "confidence": max(0.0, min(1.0, confidence)),
            "source": "llm",
            "reason": str(parsed.get("reason", "LLM classification"))[:140],
        }
    except Exception:
        return None


async def llm_chat_reply(message: str) -> str | None:
    if not settings.GEMINI_API_KEY:
        return None

    prompt = (
        "You are a helpful and concise assistant for a tech e-commerce platform. "
        "If the user asks general questions, answer naturally. "
        "If the user asks for products, suggest they use product search."
        f"\nUser message: {message}"
    )
    request_payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "topP": 0.9, "maxOutputTokens": 280},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent"

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=request_payload)
            if response.status_code == 429:
                return None
            response.raise_for_status()
            data = response.json()
        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
            or None
        )
    except Exception:
        return None


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


@router.post("/intent/classify")
async def classify_intent(query_data: IntentQuery):
    user_message = query_data.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    llm_result = await llm_classify_intent(user_message)
    if llm_result:
        return llm_result

    return heuristic_classify_intent(user_message)


@router.post("/chat")
async def chat(query_data: ChatQuery):
    user_message = query_data.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    llm_reply = await llm_chat_reply(user_message)
    if llm_reply:
        return {"response": llm_reply, "source": "llm"}

    return {
        "response": "I can help with general questions. For product recommendations, ask me what you're looking for and your budget.",
        "source": "fallback",
    }


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
                elif state in ("PROGRESS", "PENDING") or event_type == "status":
                    status_text = data.get("status") or data.get("message") or "Processing..."
                    await websocket.send_json({
                        "type": "status",
                        "payload": {
                            "message_id": message_id,
                            "status": status_text,
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

                elif state == "SUCCESS":
                    if data.get("results"):
                        await websocket.send_json({
                            "type": "products",
                            "payload": {
                                "message_id": message_id,
                                "items": data.get("results"),
                            },
                        })
                    if data.get("final_response"):
                        await websocket.send_json({
                            "type": "chunk",
                            "payload": {
                                "message_id": message_id,
                                "content": data.get("final_response"),
                            },
                        })
                    await websocket.send_json({
                        "type": "end",
                        "payload": {"message_id": message_id},
                    })
                    break

                elif event_type == "end":
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
