import re

file_path = "gateway_node/ws_manager.py"
with open(file_path, "r") as f:
    content = f.read()

old_block = """            try:
                event_data = json.loads(event_str)
                await websocket.send_json(event_data)
            except Exception as e:
                print(f"[WS Manager] Failed to send offline event to {user_id}/{task_id}: {e}")"""

new_block = """            try:
                event_data = json.loads(event_str)
                await websocket.send_json(event_data)
            except Exception as e:
                print(f"[WS Manager] Failed to send offline event to {user_id}/{task_id}: {e}")
                # Push back to the front of the list to avoid losing it
                await redis_conn.lpush(offline_key, event_str)
                break"""

content = content.replace(old_block, new_block)

with open(file_path, "w") as f:
    f.write(content)
