# Frontend Chat Development Map

Project: Nexus Marketplace Frontend
Scope: chat page only
Status: planning document for the next implementation pass

---

## 1) Non-negotiable scope rules

- Work only on the chat surface.
- Do not change the admin page.
- Do not add new pages.
- Keep the existing route structure in place for later use.
- Prefer clean architecture: small components, isolated hooks, explicit contracts.
- Keep shared styling/tokens consistent with the current design system.

### Locked for now

- `/admin`
- any login page
- any new 404 page
- any extra route outside the current chat flow

---

## 2) Current frontend reality check

### What already exists

- A routed React app with `/chat` and `/admin`.
- A working chat UI shell.
- A working admin UI shell.
- A theme token file and two surface-specific CSS files.
- Mock chat streaming logic in `useChat`.
- Mock ETL logic in `useETL`.

### What is still mock-only

- chat message streaming
- product retrieval
- conversation history loading
- sidebar conversation switching
- real backend transport

### What is broken or fragile right now

- chat streaming is simulated with timers, not a real transport
- async cleanup is incomplete in chat state
- sidebar default state does not match the PRD desktop behavior
- suggestion chips send immediately instead of filling the input
- no 404 route exists
- no auth guard exists for admin
- no markdown rendering utility exists for assistant responses

---

## 3) Backend map: what is exposed and what is ready

This section is the contract inventory for the frontend.

### 3.1 Gateway node

Source: `gateway_node/main.py`

#### Exposed endpoints

| Method | Path | Purpose | Ready for frontend? |
|---|---|---|---|
| GET | `/` | service metadata and configured upstream URLs | Yes, for diagnostics only |
| GET | `/health` | gateway health check | Yes |
| GET | `/services/health` | health of scraper and ranker upstreams | Yes |
| GET | `/scrape-and-rank?url=...` | scrape a URL, then rank scraped data | Yes, but only for URL-based workflow |

#### Important note

- The gateway is currently **not** a chat WebSocket gateway.
- It does **not** expose a `/chat` endpoint.
- It does **not** expose a `/ws/chat` endpoint.
- For chat, the frontend still needs a dedicated transport contract later.

### 3.2 Scraper node

Source: `scraper_node/main.py`

#### Visible endpoints in code

| Method | Path | Purpose | Ready for frontend? |
|---|---|---|---|
| GET | `/` | service metadata | No, not through gateway yet |
| GET | `/health` | scraper health check | No, not through gateway yet |
| POST | `/scrape/launch` | start scraping | No, admin-only concept |
| POST | `/scrape/pause` | pause scraping | No, admin-only concept |
| POST | `/scrape/resume` | resume scraping | No, admin-only concept |
| POST | `/scrape/stop` | stop scraping | No, admin-only concept |
| GET | `/scrape/status` | current scrape state | No, admin-only concept |

#### Important note

- A WebSocket progress helper exists in code, but it is **not exposed** as an actual route because it is missing an `@app.websocket(...)` decorator.
- That means the current scraper progress stream is not frontend-ready.

### 3.3 Ranker node

Source: `ranker_node/main.py`

#### Visible endpoints in code

| Method | Path | Purpose | Ready for frontend? |
|---|---|---|---|
| GET | `/` | service metadata | Not direct chat use |
| GET | `/health` | ranker health check | Useful for service health only |
| POST | `/search` | start async search task and return task id | Potentially useful later |
| WS | `/ws/status/{task_id}` | stream Celery task status | Potentially useful later |
| POST | `/rank` | format a ranked item list into markdown response | Useful as a formatting step, not the main chat transport |

#### Important note

- `POST /search` is the closest thing to a search lifecycle endpoint, but it is not yet wired through the gateway.
- `POST /rank` is a post-processing formatter, not a full chat API.

---

## 4) Frontend-facing backend readiness summary

### Ready now

- gateway health checks
- service health checks
- URL-based scrape-and-rank workflow

### Not ready for the chat page yet

- real token streaming over WebSocket
- message-level chat session transport
- chat history persistence
- product card hydration from a live response contract
- retry and timeout handling from a real stream

### Conclusion

The current backend can support **diagnostics** and **URL-based ETL** today.
It is **not yet a complete chat transport** for the chat page.

---

## 5) Chat-only development target

The chat page will be the only surface we improve first.

### Target files for the next phase

- `src/chat/ChatPage.jsx`
- `src/chat/hooks/useChat.js`
- `src/chat/components/Sidebar.jsx`
- `src/chat/components/Topbar.jsx`
- `src/chat/components/MessageList.jsx`
- `src/chat/components/Message.jsx`
- `src/chat/components/ProductCard.jsx`
- `src/chat/components/ChatInput.jsx`
- `src/chat/constants/mockData.js`
- `src/chat/styles/chat.css`

### Files to leave untouched for now

- `src/admin/*`
- route structure in `src/App.jsx`
- other future pages that may be added later

---

## 6) Code issues to fix first in the chat page

### Priority 1: state and async safety

- remove timer leaks in `useChat`
- track and clear all pending timeouts and intervals
- prevent stale async updates after reset/unmount
- ensure the chat state is deterministic

### Priority 2: sidebar behavior

- make the desktop default state match the design intent
- keep the mobile toggle behavior intact
- preserve a clean open/close state model

### Priority 3: input behavior

- make suggestion chips fill the textarea instead of sending immediately
- keep Enter-to-send and Shift+Enter behavior
- keep disabled state simple and predictable

### Priority 4: message rendering

- prepare for markdown-safe assistant rendering
- keep product cards isolated from message text rendering
- avoid mixing transport logic with presentation logic

### Priority 5: backend adapter boundary

- create a single chat transport abstraction inside `useChat`
- keep the component tree unaware of transport implementation details
- let the hook decide whether the source is mock, gateway fetch, or WebSocket later

---

## 7) Editing plan for the frontend

This is the order of work for the chat page.

### Phase 1 — stabilize the current chat shell

1. Clean up `useChat` state handling.
2. Add proper cleanup for timers and unmounts.
3. Make sidebar state predictable on desktop and mobile.
4. Fix suggestion chip behavior.

### Phase 2 — prepare the transport layer

1. Define a gateway-aware chat transport contract.
2. Keep the mock layer isolated so it can be swapped later.
3. Add a small adapter layer for future WebSocket integration.

### Phase 3 — improve rendering and UX

1. Add safe assistant text formatting.
2. Polish loading and streaming transitions.
3. Add empty/error/timeout states inside the chat surface.

### Phase 4 — verify quality

1. Run build checks.
2. Run lint checks.
3. Confirm the chat page still matches the current visual design.

---

## 8) Architecture rules to keep

- Keep page ownership strict: `ChatPage` owns layout state only.
- Keep async behavior inside hooks.
- Keep presentational components dumb.
- Keep backend contract details out of JSX where possible.
- Keep styles scoped to the chat surface.
- Avoid reworking the admin surface during chat work.

---

## 9) Known backend integration gap

The frontend still needs a real chat backend contract.

### Current gap

- gateway exposes URL scraping and health checks
- chat UI needs query-driven conversational transport

### Future direction

- a single gateway chat endpoint or WebSocket endpoint
- token streaming events
- product payload events
- completion events
- error events

Until that exists, the chat page should keep using a clean mock adapter with a clear swap point.

---

## 10) Working notes for the next edit pass

- Keep all changes local to the chat surface.
- Do not introduce unnecessary dependencies.
- Keep naming consistent with the existing codebase.
- Prefer incremental refactors over large rewrites.
- Preserve the current visual identity.
- Treat the markdown file as the source of truth for the editing sequence.

---

## 11) Next action after this map

1. Fix the chat hook state and cleanup logic.
2. Fix the chat input chip behavior.
3. Align the sidebar default/open behavior.
4. Add a clean transport boundary for future gateway integration.

---

End of map.