# SEARCHILY — Backend Contract & Integration Spec

> **Source of truth**: derived from reading every frontend source file live.  
> The existing `.backend/FRONTEND_INTEGRATION_GUIDE.md` has partial info but is **incomplete and misaligned** with the actual frontend implementation — this document supersedes it.

---

## 0. Network Configuration

The frontend reads two environment variables from `.env`:

```env
VITE_API_URL=http://localhost:8000   # REST base URL
VITE_WS_URL=ws://localhost:8000      # WebSocket base URL
```

> **Note:** Both `services/api/client.ts` and `services/websocket/socket.ts` are **empty files** — they have not been implemented yet. All integration points below describe what the frontend hooks **currently expect** and **must be wired to**.

---

## 1. Authentication

### Token Storage (Frontend side — already implemented)
The frontend stores auth state in `localStorage`:
- Key `searchily_auth_token` → JWT or opaque token string
- Key `searchily_user_role` → `"admin"` | `"user"` (string)

The `AuthProvider` reads these on boot and passes them through context. The `ProtectedRoute` component uses:
- `isAuthenticated` (truthy token) to gate `/app/**`
- `role === 'admin'` to gate `/admin/**`

### Required Auth Endpoints

#### `POST /auth/login`
**Request body:**
```json
{
  "email": "user@example.com",
  "password": "••••••••"
}
```
**Success response `200`:**
```json
{
  "token": "<JWT or opaque string>",
  "role": "admin"
}
```
**Error response `401`:**
```json
{
  "error": "Invalid credentials"
}
```

> **Frontend behavior:** On success, calls `login(token, role)` which writes both to `localStorage` and then navigates to `/app`. On failure, the current `AuthPage.tsx` has no error handling — this is a gap to fix.

#### `POST /auth/logout`
Optional — the frontend currently only removes tokens from `localStorage` (pure client-side logout). No server invalidation call is made.

#### `POST /auth/register` *(not yet wired — stub only)*
The "Sign up" button in `AuthPage.tsx` currently shows a mock message. When implemented, expected shape mirrors login.

#### `GET /auth/me` *(needed but missing)*
The frontend has **no endpoint call to fetch the current user's profile data**. The `ProfilePage`, `Topbar`, and `Sidebar` all display hardcoded placeholder values (`"Mock User"`, `"admin@searchily.ai"`, `"AD"` initials). This endpoint needs to be called after login to populate real user data.

**Expected response:**
```json
{
  "id": "uuid",
  "name": "Mortadha Azanni",
  "email": "mortadha@example.com",
  "role": "admin",
  "plan": "free",
  "searches_this_month": 14,
  "searches_limit": 50
}
```

---

## 2. Chat / Search Flow

This is the **core feature**. The flow is currently **fully mocked** in `useChatSocket.ts` via `setTimeout` simulations. Here is what the real backend must implement.

### Step 1 — Submit Query (REST)

#### `POST /search`
**Headers:** `Authorization: Bearer <token>`  
**Request body:**
```json
{
  "query": "I need noise-cancelling headphones for travel under $300"
}
```
**Success response `200`:**
```json
{
  "task_id": "b5a9c9f2-1234-5678-abcd-ef1234567890",
  "status": "Processing..."
}
```

> The frontend currently **skips this REST step entirely** — it only calls `sendMessage(query)` which goes directly into a mock. The `task_id` returned here must be captured and passed into the WebSocket URL below.

---

### Step 2 — Real-Time Streaming (WebSocket)

**URL:** `ws://<VITE_WS_URL>/ws/status/{task_id}`

The frontend's `useChatSocket.ts` → `adaptSocketPayload()` function is the **strict validation layer**. Every message from the backend must be a JSON string that parses into one of these exact shapes:

#### Event: `start`
Signals that the AI has begun generating. The `message_id` here links all subsequent events together and becomes the ID of the assistant `Message` object.

```json
{
  "type": "start",
  "payload": {
    "message_id": "uuid-string"
  }
}
```

#### Event: `chunk`
One streaming text fragment to append to the AI message. Can be called many times.

```json
{
  "type": "chunk",
  "payload": {
    "message_id": "uuid-string",
    "content": " Here are some headphones"
  }
}
```
> **Alias:** The adapter also accepts `"text"` instead of `"content"`.

#### Event: `products`
Sends the ranked product list. Triggers the `ResultsPanel` on the right to populate.

```json
{
  "type": "products",
  "payload": {
    "message_id": "uuid-string",
    "items": [
      {
        "id": "p1",
        "title": "Sony WH-1000XM4",
        "description": "Industry leading ANC...",
        "price": "$248.00",
        "image": "https://example.com/image.jpg",
        "url": "https://amazon.com/...",
        "source": "amazon.com"
      }
    ]
  }
}
```
> **Alias:** The adapter also accepts `"data"` instead of `"items"`.  
> **Optional:** `message_id` may be omitted — the frontend falls back to the `activeMessageId`.

**Product object fields** (from `types/index.ts`):
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `string` | ✅ | Unique product ID |
| `title` | `string` | ✅ | Product name |
| `description` | `string` | ✅ | Used in `ProductCard` and `PreviewDrawer` (supports HTML, DOMPurify sanitized) |
| `price` | `string` | ✅ | Rendered as-is (e.g. `"$248.00"`) |
| `image` | `string` | ✅ | Direct image URL |
| `url` | `string` | ✅ | Retailer link — opens in new tab |
| `source` | `string` | ✅ | Retailer name badge (e.g. `"amazon.com"`) |

#### Event: `end`
Signals that streaming is complete. Sets the message status to `"done"`.

```json
{
  "type": "end",
  "payload": {
    "message_id": "uuid-string"
  }
}
```

#### Event: `error`
Signals a processing failure. Displays an error banner and sets message status to `"error"`.

```json
{
  "type": "error",
  "payload": {
    "message": "Something went wrong on the backend."
  }
}
```
> **Alias:** The adapter also accepts `"error"` field instead of `"message"`.

---

### Timeout Behavior (Frontend)
The frontend sets a **15-second timeout** on each WS response cycle. If no event arrives within 15s of the last event (or from initial send), a timeout error is shown. The backend must send events faster than this cadence.

---

### AI Message Format (Markdown)
The `chunk` events stream **Markdown text** which is rendered via `react-markdown`. The frontend supports:
- Headers, lists, blockquotes, bold/italic, links, code blocks
- **Citation syntax**: `[1]`, `[2]` etc. — rendered as interactive hover cards (currently mock sourced — backend can include numbered citations in its Markdown output)

---

## 3. Admin Panel

### 3A. ETL / Scraper Control

The `AdminETLPanel.tsx` page displays scraper status and a "Force Sync" button — all currently mocked. Real wiring needs:

#### `GET /scrape/status`
**Response:**
```json
{
  "state": "idle",
  "last_sync": "2026-04-13T10:45:00Z",
  "total_records": 14200000,
  "index_latency_ms": 42,
  "pipeline_health": "Healthy"
}
```
States: `"idle"` | `"running"` | `"paused"` | `"error"`

#### `POST /scrape/launch`
Starts the scraper. No request body needed.

#### `POST /scrape/pause`
#### `POST /scrape/resume`
#### `POST /scrape/stop`

### 3B. ETL Logs WebSocket (Admin)

**URL:** `ws://<VITE_WS_URL>/websocket_progress`

The `AdminETLPanel` console output panel currently shows static mock logs. When connected to the real WS, it should receive log lines:

```json
{
  "time": "12:06:12 AM",
  "level": "INFO",
  "message": "Successfully indexed 12,402 items."
}
```
`level` values: `"INFO"` | `"WARN"` | `"ERROR"` | `"WORK"`

---

### 3C. Admin Dashboard — Metrics

#### `GET /admin/metrics`
**Response:**
```json
{
  "total_searches": 124592,
  "active_users": 8234,
  "avg_response_time_ms": 1200,
  "error_rate_pct": 0.4,
  "search_volume_7d": [
    { "label": "Mon", "value": 45 }
  ],
  "recent_activity": [
    { "event": "ETL Sync Completed", "detail": "Processed 50K records", "time": "10:45 AM" }
  ]
}
```

---

### 3D. Admin Reports

#### `GET /admin/reports`
**Response:**
```json
{
  "items": [
    {
      "id": "REP-001",
      "name": "Weekly Search Engagement",
      "date": "2026-04-13",
      "status": "Generated"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 10
}
```
`status` values: `"Generated"` | `"Failed"`

#### `POST /admin/reports/generate`
Generates a new report.

#### `GET /admin/reports/{id}/download`
Returns a CSV file for download.

---

## 4. User Profile & Account

None of these are wired — they're placeholder pages.

#### `GET /user/me`
Returns current user info (see auth section above).

#### `PATCH /user/me`
Updates name, email, etc. Body: partial user object.

#### `GET /user/usage`
Returns `{ searches_this_month: 14, searches_limit: 50, plan: "free" }`

#### `DELETE /user/history`
Expected by the "Clear Chat History" button on `ProfilePage`. Currently only clears `localStorage`.

#### `GET /user/export`
Returns JSON blob of user data. Expected by the "Export JSON" button on `ProfilePage`.

---

## 5. Health & Gateway

#### `GET /health`
Basic health check.

#### `GET /services/health`
Returns status of internal services (scraper, ranker).

---

## 6. Summary: Mocked vs. Needs Wiring

| Feature | Status | Backend endpoint needed |
|---------|--------|------------------------|
| Login | Mock (any token works) | `POST /auth/login` |
| Logout | Client-only | `POST /auth/logout` (optional) |
| Register | Stub only | `POST /auth/register` |
| Current user info | Hardcoded | `GET /auth/me` |
| Chat / search query | Fully mocked via setTimeout | `POST /search` |
| Chat streaming (text chunks) | Mocked | WebSocket `ws/status/{task_id}` |
| Product results | Mocked static list | WebSocket `products` event |
| Admin ETL status | Mocked static | `GET /scrape/status` |
| Admin ETL control | Simulated 5s delay | `POST /scrape/{launch,pause,resume,stop}` |
| ETL logs stream | Static mock logs | WebSocket `/websocket_progress` |
| Admin metrics | Hardcoded data | `GET /admin/metrics` |
| Admin reports list | Hardcoded data | `GET /admin/reports` |
| Report generation | No-op button | `POST /admin/reports/generate` |
| Report download | No-op button | `GET /admin/reports/{id}/download` |
| Edit Profile | Empty placeholder page | `PATCH /user/me` |
| Billing | Empty placeholder page | Billing service TBD |
| Notifications | Empty placeholder page | Notification prefs TBD |
| Usage stats | Hardcoded 14/50 | `GET /user/usage` |
| Clear history | localStorage only | `DELETE /user/history` |
| Export data | No-op button | `GET /user/export` |

---

## 7. Auth Header Pattern

All protected endpoints should require:
```
Authorization: Bearer <token>
```
The frontend stores the token in `localStorage` under `searchily_auth_token`. **No request interceptor exists yet** — `services/api/client.ts` is empty. When implementing the API client, attach this header from localStorage automatically.
