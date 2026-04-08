import requests
import json
import websocket
import time

query = "ordinateur portable thinkpad under 2500"
print(f"Sending query: {query}")

# 1. Start search
res = requests.post("http://localhost:8002/search", json={"query": query})
data = res.json()
print(f"Post response: {data}")
task_id = data.get("task_id")

if task_id:
    print(f"Task ID: {task_id}")
    # 2. Listen to websocket
    ws = websocket.create_connection(f"ws://localhost:8002/ws/status/{task_id}")
    while True:
        try:
            msg = ws.recv()
            msg_data = json.loads(msg)
            state = msg_data.get("state")
            print(f"State: {state} - Status: {msg_data.get('status')}")
            
            if state == "SUCCESS":
                print("\n--- RESULTS ---")
                print(json.dumps(msg_data.get("results"), indent=2))
                break
            elif state == "FAILURE":
                print("Failed")
                break
        except Exception as e:
            print(f"Error: {e}")
            break
    ws.close()
