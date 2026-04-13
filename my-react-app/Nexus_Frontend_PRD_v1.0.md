# NEXUS MARKETPLACE

Frontend Product Requirements Document (Implementation-Aligned)

v1.1 | April 2026 | ISIMM PFA Project

## 1. Product Scope

The frontend is a React single-page app with two active routes:

- /chat: conversational product discovery UI
- /admin: ETL control and monitoring surface

Out of scope for this version:

- backend internals
- database schema
- LLM prompt design

## 2. Technology Baseline

| Layer | Current Choice |
|---|---|
| Framework | React 19 + Vite |
| Routing | react-router-dom |
| Data fetch | native fetch |
| Realtime | native WebSocket |
| Styling | plain CSS + tokens |

## 3. Routing Contract

| Route | Behavior |
|---|---|
| / | Redirects to /chat |
| /chat | Loads ChatPage |
| /admin | Loads AdminPage |

No wildcard 404 route is currently implemented.

## 4. Chat Functional Requirements

### 4.1 Query Lifecycle (Current)

1. User submits query.
2. Frontend calls POST {VITE_API_URL}/search.
3. Frontend receives task_id.
4. Frontend opens WS {VITE_WS_URL}/ws/status/{task_id}.
5. UI updates assistant message while task state changes.
6. On SUCCESS, render final_response and product cards.

### 4.2 Chat UI Requirements

- Preserve two-panel chat layout with collapsible sidebar.
- Keep send action disabled while a request is in flight.
- Render assistant output safely as plain text/markdown-compatible content.
- Render product cards from ranker results mapping.
- Support reset chat action.

### 4.3 Environment Requirements

Required variables in my-react-app/.env:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 5. Admin Functional Requirements

### 5.1 Intended Backend Contract

Gateway exposes admin-oriented scraper controls:

- POST /scrape/launch
- POST /scrape/pause
- POST /scrape/resume
- POST /scrape/stop
- GET /scrape/status
- WS /websocket_progress

These endpoints require admin authentication for the REST controls through gateway dependencies.

### 5.2 Admin UI Expectations

- Show current ETL state and progress feed.
- Provide start/pause/resume/stop controls.
- Handle unauthorized and backend error responses explicitly.

## 6. Non-Functional Requirements

- Maintain responsive layout for desktop and mobile.
- Keep transport logic inside hooks, not presentation components.
- Keep styling token-driven and scoped by surface.
- Run lint/build checks before merge.

## 7. Known Gaps

- Admin route currently lacks explicit frontend route guard.
- Chat currently uses task-status streaming, not token-level conversational websocket.
- No route-level 404 fallback in App router.

## 8. Success Criteria

- Chat can complete end-to-end search flow with visible progress and results.
- Admin can control scraper flow through gateway endpoints.
- Frontend builds and lints cleanly.
