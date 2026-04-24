import asyncio
import json
import logging
from core.redis_client import get_redis
from ws_manager import manager

logger = logging.getLogger(__name__)


def _chunk_buffer_key(user_id: str, task_id: str) -> str:
    return f"stream_buffer:{user_id}:{task_id}"

async def start_pubsub_listener():
    """Background task to listen to Redis Pub/Sub events for clients."""
    redis_conn = get_redis()
    pubsub = redis_conn.pubsub()
    
    channel_pattern = "client-events:*"
    await pubsub.psubscribe(channel_pattern)
    
    logger.info(f"Started Redis Pub/Sub listener on {channel_pattern}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]
                
                try:
                    parts = channel.split(":")
                    if len(parts) >= 2:
                        user_id = parts[1]
                        payload = json.loads(data)
                        
                        task_id = payload.get("task_id")
                        if not task_id:
                            logger.warning(f"Discarding PubSub message missing task_id: {data}")
                            continue

                        event_type = payload.get("type")
                        if event_type == "chunk":
                            # Buffer stream chunks and persist a single assistant turn on "end".
                            content = payload.get("payload", {}).get("content")
                            if content:
                                await redis_conn.rpush(_chunk_buffer_key(user_id, task_id), content)
                                await redis_conn.expire(_chunk_buffer_key(user_id, task_id), 3600)
                        elif event_type == "end":
                            buffered_chunks = await redis_conn.lrange(_chunk_buffer_key(user_id, task_id), 0, -1)
                            if buffered_chunks:
                                full_text = "".join(buffered_chunks).strip()
                                if full_text:
                                    from services.session_manager import session_manager
                                    asyncio.create_task(session_manager.add_turn(user_id, "assistant", full_text))
                            await redis_conn.delete(_chunk_buffer_key(user_id, task_id))
                        elif event_type == "error":
                            # Best-effort cleanup for abandoned streams.
                            await redis_conn.delete(_chunk_buffer_key(user_id, task_id))
                            
                        # Send to the user's task sockets
                        await manager.send_to_task(user_id, task_id, payload)
                        
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode PubSub payload on {channel}: {data}")
                except Exception as e:
                    logger.error(f"Error handling PubSub message: {e}")
                    
    except asyncio.CancelledError:
        logger.info("Pub/Sub listener cancelled. Shutting down.")
    finally:
        await pubsub.punsubscribe(channel_pattern)
        await pubsub.close()
