# Frontend Chat Development Map

Project: Nexus Marketplace Frontend  
Scope: chat surface first, without breaking current admin route.

## 1) Current State Snapshot

- Routes exist for /chat and /admin.
- Chat already uses real backend transport (POST /search + WS /ws/status/{task_id}).
- Admin UI exists but backend integration and auth hardening are still incomplete.
- Shared design tokens and per-surface CSS files are in place.

## 2) Backend Contract Inventory

### Gateway (gateway_node/main.py)

| Method | Path | Purpose | Chat usage |
|---|---|---|---|
| GET | /health | Liveness | Diagnostics |
| GET | /services/health | Scraper/ranker status | Diagnostics |
| POST | /search | Proxy to ranker async search | Active |
| WS | /ws/status/{task_id} | Proxy task status stream | Active |
| WS | /ws/chat/{user_id}?token=... | Token streaming chat via Brain service | Available, not used by current useChat |

### Ranker (ranker_node/main.py)

| Method | Path | Purpose |
|---|---|---|
| POST | /search | Start Celery search task |
| WS | /ws/status/{task_id} | Stream task progress/results |
| POST | /rank | Format ranked items to markdown |

### Scraper (scraper_node/main.py)

| Method | Path | Purpose |
|---|---|---|
| POST | /scrape/launch | Start ETL task |
| POST | /scrape/pause | Pause ETL |
| POST | /scrape/resume | Resume ETL |
| POST | /scrape/stop | Stop ETL |
| GET | /scrape/status | Current ETL state |
| WS | /websocket_progress | Live ETL progress |

## 3) Chat Transport in Code Today

Implemented in src/chat/hooks/useChat.js:

1. Send user query to VITE_API_URL/search.
2. Receive task_id.
3. Open websocket to VITE_WS_URL/ws/status/{task_id}.
4. Update assistant message as status events arrive.
5. On SUCCESS, render final_response and mapped products.

## 4) Gaps to Resolve Next

- Add auth-aware admin route protection.
- Standardize websocket error/reconnect behavior in useChat.
- Consider moving from task-status UX to token-stream UX using /ws/chat/{user_id} for richer chat feel.
- Add explicit loading, timeout, and retry UI states.
- Add route-level fallback for unknown paths.

## 5) File Ownership for Chat Work

Primary files:

- src/chat/ChatPage.jsx
- src/chat/hooks/useChat.js
- src/chat/components/*
- src/chat/constants/mockData.js
- src/chat/styles/chat.css

Do not modify during chat-only passes:

- src/admin/*
- src/App.jsx route structure (unless routing change is the task)

## 6) Development Checklist

1. Keep async side effects isolated in hooks.
2. Avoid transport logic inside presentational components.
3. Keep API and WS base URLs environment-driven.
4. Run npm run lint and npm run build after chat-surface changes.