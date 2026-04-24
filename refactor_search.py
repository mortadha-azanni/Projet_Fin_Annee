import re
import json

file_path = "ranker_node/Search.py"
with open(file_path, "r") as f:
    content = f.read()

if "pubsub_redis" not in content:
    content = content.replace("from celery_app import celery_app", "from celery_app import celery_app, pubsub_redis\nimport json")

helper = """
def push_event(task, task_state, status_msg, user_id=None, extra_payload=None):
    if task:
        task.update_state(state=task_state, meta={"status": status_msg})
        
    if user_id and task:
        task_id = task.request.id
        channel = f"client-events:{user_id}"
        
        event_type = "status"
        if task_state == "FAILURE":
            event_type = "error"
            
        payload = {
            "type": event_type,
            "task_id": task_id,
            "payload": {
                "status": status_msg
            }
        }
        
        if task_state == "FAILURE":
            payload["payload"] = {"message": status_msg}
            
        if extra_payload:
            payload.update(extra_payload)
            
        try:
            pubsub_redis.publish(channel, json.dumps(payload))
        except Exception as e:
            print(f"[Redis Publish Error] {e}")

"""
if "def push_event" not in content:
    idx = content.find("def _normalize_query_text")
    content = content[:idx] + helper + content[idx:]

content = content.replace("def perform_search(self, user_query_str: str):", "def perform_search(self, user_query_str: str, user_id: str = None):")

content = re.sub(
    r"if self:\n\s*self\.update_state\(\n\s*state='PROGRESS',\n\s*meta=\{'status': (.*?)\}\n\s*\)",
    r"push_event(self, 'PROGRESS', \1, user_id)",
    content
)

content = re.sub(
    r"if self:\s*self\.update_state\(state='PROGRESS',\s*meta=\{'status': (.*?)\}\)",
    r"push_event(self, 'PROGRESS', \1, user_id)",
    content
)

content = re.sub(
    r"(return\s*\{\s*)(\"results\")",
    r"push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'products', 'payload': {'items': local_results} if 'local_results' in locals() else {} })\n    \1\2",
    content
)

with open(file_path, "w") as f:
    f.write(content)
print("done")
