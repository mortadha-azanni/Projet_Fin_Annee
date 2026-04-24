import re

file_path = "ranker_node/Search.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix early return
early_return = """    if not _is_product_search_query(cleaned_query):
        push_event(self, 'PROGRESS', 'I can help with product searches. Tell me what item, brand, or budget you want.', user_id)
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'chunk', 'payload': {'content': 'I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.'} })
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'end' })
        return {
            "results": [],
            "final_response": "I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.",
            "message": "No product search detected.",
            "cache_key": None,
        }"""

# Replaces the broken early return
content = re.sub(r"\s*if not _is_product_search_query\(cleaned_query\):.*?return \{\s*\"results\": \[\],\s*\"final_response\": \"I can help[^\}]*\}", early_return, content, flags=re.DOTALL)

# Fix bottom main return
bottom_return = """    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'products', 'payload': {'items': top_5} })
    if final_response:
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'chunk', 'payload': {'content': final_response} })
    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={ 'type': 'end' })
    
    return {
        "results": top_5,
        "final_response": final_response,
        "cache_key": f"search_results:{task_id}" if 'task_id' in locals() else None,
    }"""

content = re.sub(r"    push_event\(self, 'SUCCESS'.*?return \{\s*\"results\": top_5,.*?cache_key.*?[^\}]*\}", bottom_return, content, flags=re.DOTALL)


with open(file_path, "w") as f:
    f.write(content)
