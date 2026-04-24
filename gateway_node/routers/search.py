from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from pydantic import BaseModel
import httpx
import json
import uuid
import asyncio
import re
import hashlib
from typing import Any
from core.config import settings
from auth.dependencies import get_current_user
from auth.models import TokenData
from ws_manager import manager  # Added WS Connection Manager
from services.session_manager import session_manager
from services.classifier import classify_intent
from core.redis_client import get_redis
from core.sanitization import SanitizedSearchQuery, SanitizedConstraints, SanitizedEntities, validate_and_sanitize_input

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


def _semantic_cache_key(query_text: str, constraints: dict) -> str:
    normalized_query = (query_text or "").strip().lower()
    normalized_constraints = json.dumps(constraints or {}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{normalized_query}|{normalized_constraints}".encode("utf-8")).hexdigest()
    return f"semantic_cache:{digest}"


async def send_cached_reply(user_id: str, task_id: str, cache_payload: dict) -> None:
    """Background task to publish a fast cached response over WS events."""
    redis_conn = get_redis()
    channel = f"client-events:{user_id}"

    items = (cache_payload.get("results") or [])[:5]
    final_response = cache_payload.get("final_response") or "Here are previously cached results for your request."

    msgs = [
        {"type": "status", "task_id": task_id, "payload": {"status": "Cache hit. Returning results..."}},
        {"type": "products", "task_id": task_id, "payload": {"items": items}},
        {"type": "chunk", "task_id": task_id, "payload": {"content": final_response}},
        {"type": "end", "task_id": task_id, "payload": {}},
    ]

    for msg in msgs:
        await redis_conn.publish(channel, json.dumps(msg))
        await asyncio.sleep(0.1)


async def send_direct_reply(user_id: str, task_id: str, reply_text: str) -> None:
    """Background task to send a rapid direct reply bypassing ranker."""
    redis_conn = get_redis()
    channel = f"client-events:{user_id}"

    await asyncio.sleep(0.5)

    msgs = [
        {"type": "status", "task_id": task_id, "payload": {"status": "Thinking..."}},
        {"type": "chunk", "task_id": task_id, "payload": {"content": reply_text}},
        {"type": "end", "task_id": task_id, "payload": {}},
    ]

    for msg in msgs:
        await redis_conn.publish(channel, json.dumps(msg))
        await asyncio.sleep(0.2)


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
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user),
):
    """
    POST /search — Contract §2, Step 1.
    Classify intent first. Forward to ranker OR reply directly via WS stream.
    """
    # Sanitize and validate input
    try:
        sanitized_query = SanitizedSearchQuery(query=query_data.query)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search query: {str(e)}"
        )

    user_id = str(current_user.id)
    query_text = sanitized_query.query

    # 1. Load recent history
    history = await session_manager.get_context(user_id)
    
    # 2. Log user message permanently into current session buffer
    await session_manager.add_turn(user_id, "user", query_text)
    
    # 3. Classify intent securely using Gemini (Stage 4)
    decision = await classify_intent(query_text, history)
    intent = decision.get("intent", "search")
    
    task_id = str(uuid.uuid4())
    
    # 4. Route Execution
    if intent in ("chitchat", "clarify", "ambiguous"):
        # Fire background task for immediate reply
        reply = decision.get("direct_reply") or decision.get("clarification_question") or "Can you clarify that?"
        background_tasks.add_task(send_direct_reply, user_id, task_id, reply)
        return {
            "task_id": task_id,
            "status": "Generating response...",
            "intent": intent
        }
    
    # Otherwise, it's a Search or Constrained -> Forward to Ranker
    constraints = decision.get("constraints", {})
    entities = decision.get("entities", {})

    # Sanitize constraints and entities
    try:
        sanitized_constraints = (
            SanitizedConstraints(**constraints)
            if constraints
            else SanitizedConstraints(max_price=None, location=None, filters=None)
        )
        sanitized_entities = (
            SanitizedEntities(**entities)
            if entities
            else SanitizedEntities(products=None, brands=None, categories=None, dates=None)
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search constraints: {str(e)}"
        )

    constraints_dict = sanitized_constraints.dict(exclude_unset=True) if sanitized_constraints else {}
    entities_dict = sanitized_entities.dict(exclude_unset=True) if sanitized_entities else {}

    semantic_cache_key = _semantic_cache_key(query_text, constraints_dict)

    redis_conn = get_redis()
    cached_payload = await redis_conn.get(semantic_cache_key)
    if cached_payload:
        try:
            parsed_cache = json.loads(cached_payload)
            if isinstance(parsed_cache, list):
                parsed_cache = {"results": parsed_cache, "final_response": "Here are cached results for your request."}
            background_tasks.add_task(send_cached_reply, user_id, task_id, parsed_cache)
            return {
                "task_id": task_id,
                "status": "Returning cached response...",
                "intent": intent,
                "cache_hit": True,
            }
        except Exception:
            # Cache payload malformed, continue with normal ranker path.
            pass
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.RANKER_URL}/search",
                json={
                    "query": query_text,
                    "user_id": user_id,
                    "intent": intent,
                    "constraints": constraints_dict,
                    "entities": entities_dict,
                    "semantic_cache_key": semantic_cache_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "task_id": data.get("task_id", task_id),
                "status": data.get("status", "Processing..."),
                "intent": intent
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
async def classify_intent_endpoint(query_data: IntentQuery):
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
        from core.security import decode_token
        token_data = decode_token(token)
        if token_data.role not in ("user", "admin"):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(str(token_data.id), task_id, websocket)

    message_id = str(uuid.uuid4())

    # Send 'start' event — signals the frontend to create the assistant message
    try:
        await websocket.send_json({
            "type": "start",
            "payload": {"message_id": message_id},
        })

        # Keep the connection open indefinitely.
        # The background Pub/Sub listener will push events automatically.
        while True:
            # We don't expect the client to send us text here, but we listen to detect disconnects.
            _ = await websocket.receive_text()
            
    except WebSocketDisconnect:
        # Client gracefully closed WS
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
        manager.disconnect(str(token_data.id), task_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
