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

# Simple literal replaces for update_state
replacements = [
    ("self.update_state(\n                state='PROGRESS',\n                meta={'status': 'I can help with product searches. Tell me what item, brand, or budget you want.'}\n            )", "push_event(self, 'PROGRESS', 'I can help with product searches. Tell me what item, brand, or budget you want.', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Normalizing query and extracting entities...'})", "push_event(self, 'PROGRESS', 'Normalizing query and extracting entities...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Fetching and ranking categories...'})", "push_event(self, 'PROGRESS', 'Fetching and ranking categories...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Consulting LLM for category and price selection...'})", "push_event(self, 'PROGRESS', 'Consulting LLM for category and price selection...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': f'Fetching top products efficiently for category {selected_category_id}...'})", "push_event(self, 'PROGRESS', f'Fetching top products efficiently for category {selected_category_id}...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Executing hybrid search locally across chunks...'})", "push_event(self, 'PROGRESS', 'Executing hybrid search locally across chunks...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Applying Reciprocal Rank Fusion (RRF) for final ranking...'})", "push_event(self, 'PROGRESS', 'Applying Reciprocal Rank Fusion (RRF) for final ranking...', user_id)"),
    ("self.update_state(state='PROGRESS', meta={'status': 'Caching top 20 results and finalizing...'})", "push_event(self, 'PROGRESS', 'Caching top 20 results and finalizing...', user_id)")
]

for old, new in replacements:
    content = content.replace(old, new)


# Update the early return
early_return_old = """        return {
            "results": [],
            "final_response": "I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.",
            "message": "No product search detected.",
            "cache_key": None,
        }"""
early_return_new = """        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'chunk', 'payload': {'content': 'I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.'}})
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'end'})
        return {
            "results": [],
            "final_response": "I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.",
            "message": "No product search detected.",
            "cache_key": None,
        }"""
content = content.replace(early_return_old, early_return_new)


# Update the final return
final_return_old = """    return {
        "results": top_5,
        "final_response": final_response,
        "cache_key": f"search_results:{task_id}" if 'task_id' in locals() else None,
    }"""
final_return_new = """    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'products', 'payload': {'items': top_5}})
    if final_response:
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'chunk', 'payload': {'content': final_response}})
    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'end'})
    
    return {
        "results": top_5,
        "final_response": final_response,
        "cache_key": f"search_results:{task_id}" if 'task_id' in locals() else None,
    }"""
content = content.replace(final_return_old, final_return_new)

with open(file_path, "w") as f:
    f.write(content)
print("Safe refactor complete")
