import json
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from core.redis_client import get_redis
from core.config import settings

async def summarize_history(history_text: str) -> Optional[str]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    system_prompt = "You are a conversational context summarizer. Distill the following conversation into a concise set of facts, extracted constraints, and preferences for search context. Omit filler words."
    
    payload = {
        "contents": [
            {
                "parts": [{"text": system_prompt + "\n\nConversation:\n" + history_text}]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 250
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[Summarization Error] {e}")
        return None

class SessionManager:
    """Manages short-term conversational context in Redis"""
    def __init__(self, key_prefix="session"):
        self.key_prefix = key_prefix
        self.max_history_turns = 6 # Last 6 interactions before summarization
        self.ttl = 86400 # 24 hours

    def _key(self, user_id: str) -> str:
        return f"{self.key_prefix}:{user_id}"

    def _compact_lock_key(self, user_id: str) -> str:
        return f"{self.key_prefix}:compact_lock:{user_id}"

    async def _compact_history(self, user_id: str):
        """Compact oversized history in the background to avoid request-path latency."""
        redis_conn = get_redis()
        key = self._key(user_id)
        lock_key = self._compact_lock_key(user_id)

        acquired = await redis_conn.set(lock_key, "1", ex=30, nx=True)
        if not acquired:
            return

        try:
            items = await redis_conn.lrange(key, 0, -1)
            if len(items) <= (self.max_history_turns * 2):
                return

            history_text = "\n".join(
                [f"{json.loads(item).get('role', 'unknown')}: {json.loads(item).get('content', '')}" for item in items]
            )
            summary = await summarize_history(history_text)

            if summary:
                await redis_conn.delete(key)
                summary_msg = {
                    "role": "system",
                    "content": f"Previous Context Summary: {summary}",
                }
                await redis_conn.rpush(key, json.dumps(summary_msg))
            else:
                await redis_conn.ltrim(key, -(self.max_history_turns * 2), -1)

            await redis_conn.expire(key, self.ttl)
        finally:
            await redis_conn.delete(lock_key)

    async def add_turn(self, user_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Append a message to the user's conversation history."""
        redis_conn = get_redis()
        key = self._key(user_id)
        
        message: Dict[str, Any] = {
            "role": role,
            "content": content
        }
        if metadata:
            message["metadata"] = metadata

        await redis_conn.rpush(key, json.dumps(message))
        
        # Determine if we need to summarize
        current_len = await redis_conn.llen(key)
        if current_len > (self.max_history_turns * 2):
            asyncio.create_task(self._compact_history(user_id))

        await redis_conn.expire(key, self.ttl)

    async def get_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch the current conversation history for the user."""
        redis_conn = get_redis()
        key = self._key(user_id)
        
        items = await redis_conn.lrange(key, 0, -1)
        if not items:
            return []
            
        return [json.loads(item) for item in items]

    async def clear_context(self, user_id: str):
        """Delete the user's conversational session"""
        redis_conn = get_redis()
        key = self._key(user_id)
        await redis_conn.delete(key)

# Global instance
session_manager = SessionManager()
