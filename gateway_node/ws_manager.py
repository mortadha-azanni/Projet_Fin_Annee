import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

from core.redis_client import get_redis

class ConnectionManager:
    def __init__(self):
        # Maps user_id -> { task_id: set[WebSocket] }
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

    @staticmethod
    def _offline_key(user_id: str, task_id: str) -> str:
        return f"offline_events:{user_id}:{task_id}"

    async def connect(self, user_id: str, task_id: str, websocket: WebSocket):
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        if task_id not in self.active_connections[user_id]:
            self.active_connections[user_id][task_id] = set()
            
        self.active_connections[user_id][task_id].add(websocket)
        
        redis_conn = get_redis()
        await redis_conn.sadd(f"active_users", user_id)
        
        # Pull offline fallback events 
        offline_key = self._offline_key(user_id, task_id)
        while True:
            # LPOP removes and returns the first element of the list
            event_str = await redis_conn.lpop(offline_key)
            if not event_str:
                break
            
            try:
                event_data = json.loads(event_str)
                await websocket.send_json(event_data)
            except Exception as e:
                print(f"[WS Manager] Failed to send offline event to {user_id}/{task_id}: {e}")
                # Push back to the front of the list to avoid losing it
                await redis_conn.lpush(offline_key, event_str)
                break

    def disconnect(self, user_id: str, task_id: str, websocket: WebSocket):
        try:
            if user_id in self.active_connections:
                if task_id in self.active_connections[user_id]:
                    if websocket in self.active_connections[user_id][task_id]:
                        self.active_connections[user_id][task_id].remove(websocket)
                    
                    if not self.active_connections[user_id][task_id]:
                        del self.active_connections[user_id][task_id]
                
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    # Unregister from active_users
                    asyncio.create_task(get_redis().srem("active_users", user_id))
        except Exception as e:
            print(f"[WS Manager] Error upon disconnect for {user_id}/{task_id}: {e}")

    async def send_to_task(self, user_id: str, task_id: str, message: dict):
        """Send message to all sockets connected to a specific task for a user"""
        sent = False
        if user_id in self.active_connections and task_id in self.active_connections[user_id]:
            sockets = self.active_connections[user_id][task_id].copy()
            for websocket in sockets:
                try:
                    await websocket.send_json(message)
                    sent = True
                except Exception:
                    # Connection might be dead
                    self.disconnect(user_id, task_id, websocket)

        # Offline fallback: if no WebSocket received the message
        if not sent:
            try:
                redis_conn = get_redis()
                offline_key = self._offline_key(user_id, task_id)
                # Append stringified message and set TTL (e.g. 1 hour)
                await redis_conn.rpush(offline_key, json.dumps(message))
                await redis_conn.expire(offline_key, 3600)
            except Exception as e:
                print(f"[WS Manager] Failed to push offline event for {user_id}/{task_id}: {e}")

manager = ConnectionManager()
