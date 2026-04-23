# Backend Communication Issue Report & Frontend Expectations

This document outlines the exact requirements the frontend expects from the backend, and details the current bugs occurring in the backend's WebSocket/Celery streaming logic.

## 🚨 What is Currently Failing (The Issue)

The frontend's UI chat window is currently rendering blank "empty" bubbles for the AI responses. 
After extensive debugging, we've determined that **the frontend connection is working perfectly, but the backend worker is failing to send the actual response chunks.**

### The Exact Sequence Happening Right Now:
1. The frontend successfully authenticates and receives a `task_id` from `POST /search`.
2. The frontend successfully connects to the WebSocket at `ws://localhost:8000/ws/status/{task_id}?token={jwt}`.
3. The backend immediately fires:
   ```json
   { "type": "start", "payload": { "message_id": "xxx" } }
   ```
4. **[MISSING DATA]** The backend completely skips sending any `"type": "chunk"` or `"type": "products"` payloads.
5. The backend immediately fires:
   ```json
   { "type": "end", "payload": { "message_id": "xxx" } }
   ```
6. The backend closes the socket cleanly with code `1000`.

**Conclusion:** The Python backend (specifically the Celery worker handling the AI generation) is silently aborting or returning empty results before it can broadcast the chunked output. 

---

## 📋 What the Frontend Expects (The Contract)

To make the UI work correctly, the backend **must** strictly adhere to the following data contracts:

### 1. Authentication
* **Endpoint:** `POST /auth/login`
* **Expected Response:** Must contain a valid JWT in the `token` field.
  ```json
  { "token": "ey..." }
  ```

### 2. Search Handshake
* **Endpoint:** `POST /search` (Requires `Authorization: Bearer <token>`)
* **Expected Response:** Must return the asynchronous task identifier.
  ```json
  { "task_id": "some-uuid-string" }
  ```

### 3. WebSocket Connection
* **URL:** `ws://<domain>/ws/status/<task_id>?token=<token>`
* **Authentication:** The frontend cannot pass headers to a native Browser WebSocket. It will append `?token=<jwt>` to the URL.

### 4. WebSocket Payload Format
The frontend's parser (`useChatSocket.ts`) strictly expects JSON objects wrapped with a `type` and an inner `payload` mapping to a `message_id`.

**A complete, successful execution must stream in this order:**

1. **Start the message bubble:**
   ```json
   {
     "type": "start",
     "payload": {
       "message_id": "msg-123"
     }
   }
   ```

2. **Stream Text Chunks (Multiple times):**
   ```json
   {
     "type": "chunk",
     "payload": {
       "message_id": "msg-123",
       "content": "Here is a "
     }
   }
   ```

3. **Provide Product Results (Optional, can be sent during or after chunks):**
   ```json
   {
     "type": "products",
     "payload": {
       "message_id": "msg-123",
       "items": [
         { "id": "1", "name": "Laptop", "price": 999 }
       ]
     }
   }
   ```

4. **End the message bubble:**
   ```json
   {
     "type": "end",
     "payload": {
       "message_id": "msg-123"
     }
   }
   ```

**Error Handling:**
If the Celery worker fails, the backend should emit an error *instead* of an empty `end` event:
```json
{
  "type": "error",
  "payload": {
    "message": "Failed to connect to LLM provider."
  }
}
```

---

## 🛠️ Next Steps for Backend Debugging

1. **Check Celery Worker Logs:** Look directly at the terminal or docker logs where the Celery worker is running. There is highly likely a Python exception being swallowed (e.g., Missing OpenAI/Groq API keys, DB connection failure).
2. **Verify Stream Yielding:** Ensure the `yield` or `publish` statements in the backend AI generation loop are actually executing and emitting `{"type": "chunk"}` objects.
