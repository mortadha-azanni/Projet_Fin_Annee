# NEXUS MARKETPLACE

Frontend Product Requirements Document

Chat UI · Admin Dashboard · Component System

v1.0 | April 2026 | ISIMM PFA Project

---

## Technology Stack

| Framework | Real-time | Styling |
|-----------|-----------|---------|
| **React + Vite** | **WebSocket** | **CSS Variables** |

---

## 1. Overview

This document defines the frontend requirements for the Nexus Marketplace platform. The frontend is a React single-page application that serves two distinct user surfaces: a Chat UI for end users and an Admin Dashboard for ETL operators. Both surfaces share a common component system and design language.

> **Scope of this document**
> 
> - Chat UI — the primary end-user interface for AI-powered product search
> - Admin Dashboard — ETL monitoring and control panel
> - Shared component system — design tokens, reusable components, style guide
> - WebSocket integration contract with the Gateway (FastAPI, Device 1)
> - Out of scope: backend services, database schema, LLM configuration

### 1.1 Goals

- Deliver a seamless conversational shopping experience — no page reloads, instant feedback
- Stream AI responses token-by-token to give users real-time feedback
- Display product cards inline within the conversation as AI messages resolve
- Give admins full visibility and control over the ETL pipeline state
- Maintain a clean, maintainable component architecture that teammates can extend independently

### 1.2 Target Users

| User Type | Surface | Primary Goal |
|-----------|---------|--------------|
| End User (shopper) | Chat UI | Find products using natural language queries |
| Admin / Developer | Admin Dashboard | Monitor and control the ETL scraping pipeline |

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Bundler | Vite | Fast HMR, native ESM, minimal config |
| UI Framework | React 18 | Hooks-first, team familiarity |
| Routing | React Router v6 | SPA routing for Chat / Admin surfaces |
| State | React hooks + custom hooks | No external state library needed at this scale |
| Real-time | Native WebSocket API | Direct WS connection to FastAPI Gateway |
| Styling | Plain CSS + CSS Custom Properties | No build-time dependency, easy theming |
| Typography | Google Fonts (Syne + DM Sans) | Syne for headings, DM Sans for body text |
| Icons | Inline SVG / Unicode | Zero dependency, no icon font flash |
| HTTP Client | Native fetch | REST calls to Gateway admin endpoints |
| Linting | ESLint + Vite plugin | Consistent code style across team |

---

## 3. Folder Structure

The `src/` directory is organized by surface, with shared primitives in a top-level `components/` and `hooks/` folder.

| Path | Contents |
|------|----------|
| `src/chat/` | Chat UI surface — all chat-related files |
| `src/chat/ChatPage.jsx` | Root layout component — owns sidebar state only |
| `src/chat/hooks/useChat.js` | All message state, streaming logic, WS connection |
| `src/chat/components/Sidebar.jsx` | Conversation history, new chat button, user info |
| `src/chat/components/Topbar.jsx` | Connection status dot, share/options actions |
| `src/chat/components/MessageList.jsx` | Scrollable area — renders all Message components |
| `src/chat/components/Message.jsx` | Single chat bubble + product grid for AI messages |
| `src/chat/components/ProductCard.jsx` | Product display card (image, name, price, CTA) |
| `src/chat/components/ChatInput.jsx` | Textarea + suggestion chips + send button |
| `src/chat/constants/mockData.js` | Mock products, chat history, suggestion chips, welcome message |
| `src/chat/utils/renderMarkdown.js` | Lightweight **bold** / *italic* → HTML converter |
| `src/chat/styles/chat.css` | All chat surface styles — no inline styles in JSX |
| `src/admin/` | Admin Dashboard surface (ETL control panel) |
| `src/admin/AdminPage.jsx` | Root admin layout |
| `src/admin/components/ETLControls.jsx` | Start / Pause / Resume / Force Stop buttons |
| `src/admin/components/ProgressFeed.jsx` | Live WebSocket progress log |
| `src/admin/components/StatusBadge.jsx` | ETL state indicator (Idle/Running/Paused/Error/Completed) |
| `src/admin/hooks/useETL.js` | ETL state machine + WS subscription for admin |
| `src/admin/styles/admin.css` | Admin surface styles |
| `src/shared/` | Components and tokens shared by both surfaces |
| `src/shared/tokens.css` | All CSS custom properties (colors, spacing, radius, fonts) |
| `src/App.jsx` | React Router root — /chat and /admin routes |

---

## 4. Design System

### 4.1 Color Tokens

All colors are defined as CSS custom properties in `src/shared/tokens.css`. Components reference variables only — never raw hex values.

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | #0d0f14 | Page / app background |
| `--bg2` | #13161d | Sidebar, panels |
| `--bg3` | #1a1e28 | Cards, input boxes, message bubbles (AI) |
| `--border` | #252a38 | All borders and dividers |
| `--accent` | #6C63FF | Primary CTA, user message bubble, links, active states |
| `--accent2` | #ff6b6b | Destructive / warning actions |
| `--gold` | #f5c842 | Ratings, italic highlights in AI text |
| `--text` | #e8eaf0 | Primary text |
| `--text2` | #8892a4 | Secondary / placeholder text |
| `--text3` | #5a6478 | Muted / hint text |
| `--radius` | 14px | Default border radius for cards and inputs |

### 4.2 Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Display / Logo | Syne | 800 | 18–72px depending on context |
| Headings | Syne | 600–700 | 15–36px |
| Body / UI labels | DM Sans | 400–500 | 11–14.5px |
| Code / CLI output | Courier New | 400 | 18px (in doc snippets) |
| Price labels | Syne | 700 | 14px — distinct from body for quick scanning |

### 4.3 Spacing & Radius

- Base unit: 8px — all spacing in multiples of 4px or 8px
- Card radius: `var(--radius)` = 14px
- Button radius: 8–10px (smaller than cards)
- Chip / badge radius: 20px (pill shape)
- Avatar radius: 50% (circle)

### 4.4 Animation Principles

| Animation | CSS | Trigger |
|-----------|-----|---------|
| Message appear | fadeUp 0.3s ease forwards | New message added to list |
| Product card appear | fadeUp 0.4s ease, stagger delay 0.12s per card | After stream ends |
| Status pulse | pulse 2s ease-in-out infinite (opacity 1→0.5) | Online indicator dot |
| Cursor blink | blink 0.8s step-end infinite | While assistant is streaming |
| Spinner | spin 0.7s linear infinite | Send button while streaming |
| Card hover lift | translateY(-3px) + border-color change, 0.2s | Product card hover |
| Button hover | opacity 0.88 + scale(1.05), 0.15s | Send button hover |

---

## 5. Chat UI — Detailed Requirements

### 5.1 Layout

The chat page is a full-viewport two-panel layout:

- Left panel: Sidebar (collapsible, 260px wide)
- Right panel: Main area (flex column — Topbar → MessageList → ChatInput)

The sidebar collapses to `width: 0` with an opacity transition. When collapsed, a hamburger button appears in the Topbar to restore it.

### 5.2 Sidebar

#### 5.2.1 Logo

- Hexagon icon (⬡) in accent color + 'Nexus' wordmark in Syne 800
- Close button (✕) on the right — collapses the sidebar

#### 5.2.2 New Chat Button

- Full-width, accent background, DM Sans 500
- On click: resets messages to the welcome message, clears active history item

#### 5.2.3 Conversation History

- Shows last N conversations fetched from the backend (currently mocked)
- Each item: chat bubble icon + truncated preview (single line, `text-overflow: ellipsis`) + relative timestamp
- Active item highlighted with `--bg3` background
- On click: loads the selected conversation's messages (future: fetch from Redis/DB)

#### 5.2.4 User Info Footer

- Gradient avatar circle with initials (e.g. 'BJ')
- Username + plan label ('Free Plan')
- Pinned to sidebar bottom with border-top separator

### 5.3 Topbar

- When sidebar is closed: shows hamburger (☰) button on the left
- Center: animated green status dot (pulsing) + 'AI Shopping Assistant' label
- Right: 'Share' button + options menu button (⋯) — both ghost-styled

### 5.4 Message List

#### 5.4.1 Message Bubble — User

- Right-aligned, `flex-direction: row-reverse`
- Bubble: accent background (#6C63FF), white text, `border-bottom-right-radius: 4px`
- Avatar: gradient circle (accent2 → gold) with user initials, top-right position

#### 5.4.2 Message Bubble — Assistant

- Left-aligned
- Bubble: `--bg3` background, `--text` color, 1px `--border`, `border-bottom-left-radius: 4px`
- Bold text rendered as #a78bfa (purple), italic text rendered as `--gold`
- Blinking cursor (▍) shown while streaming = true
- Avatar: gradient circle (accent → #a78bfa) with 'AI' label

#### 5.4.3 Product Grid (below AI messages)

- Appears only after streaming is complete and products are present
- 3-column CSS grid, gap 12px, max-width 680px
- Each card animates in with fadeUp, staggered by 120ms per card
- On hover: `border-color → --accent`, `translateY(-3px)`

### 5.5 Product Card

| Section | Content | Notes |
|---------|---------|-------|
| Image area | 120px tall, dark bg, centered product image (80x80) | |
| Category badge | Top-left absolute badge, pill-shaped, accent color at 20% opacity | e.g. 'RUNNING' |
| Product name | 12px, font-weight 500, 2-line max (`line-clamp: 2`) | |
| Rating | Star + numeric score in `--gold` color | e.g. ★ 4.8 |
| Price | Syne 700, 14px, `--accent` color | e.g. $129.99 |
| CTA button | 'View Product →' — ghost button, full-width | On hover: accent fill |

### 5.6 Chat Input

#### 5.6.1 Suggestion Chips

- Row of pill-shaped chips above the input box
- Chips defined in `constants/mockData.js` — easy to update without touching components
- On click: sets input value + focuses textarea
- Chips are hidden while streaming (future enhancement)

#### 5.6.2 Input Box

- Textarea (not input) — supports multi-line with Shift+Enter
- Enter key (without Shift): submits the query
- Auto-grows up to `max-height: 120px`, then scrolls
- Disabled state (opacity 0.5) while streaming
- Focus: `border-color` transitions to `--accent`

#### 5.6.3 Send Button

- 38x38px circle button, accent background
- While idle: shows ↑ arrow
- While streaming: shows CSS spinner (rotating border), button disabled
- Hint text below: 'Press Enter to send · Shift+Enter for new line'

### 5.7 Streaming UX Contract

The `useChat` hook manages the full streaming lifecycle. The sequence below defines the expected state transitions:

| Step | State Change | UI Effect |
|------|--------------|-----------|
| User sends query | Message appended (role: user) | User bubble appears instantly |
| 400ms delay | isStreaming = true | Send button → spinner |
| AI message created | Message appended (role: assistant, content: '', streaming: true) | AI bubble appears with cursor ▍ |
| Tokens arrive | content updated chunk by chunk | Text types out in real time |
| Stream ends | streaming = false | Cursor disappears |
| 300ms delay | products added to message | Product cards animate in |
| isStreaming = false | — | Send button restored |

### 5.8 WebSocket Integration

When replacing the mock simulation with the real backend, only `useChat.js` needs to change. The contract is:

> **WebSocket Contract (Gateway → Frontend)**
> 
> Connect to: `ws://<gateway-ip>:8000/ws/chat`
> 
> Send on query:
> ```json
> { "query": "...", "user_id": "..." }
> ```
> 
> Receive per token:
> ```json
> { "type": "token", "data": "..." }
> ```
> 
> Receive on products ready:
> ```json
> { "type": "products", "data": [ { id, name, price, ... } ] }
> ```
> 
> Receive on stream end:
> ```json
> { "type": "done" }
> ```

---

## 6. Admin Dashboard — Detailed Requirements

The Admin Dashboard gives ETL operators real-time visibility and control over the scraping pipeline running on Device 2. It is a separate route (`/admin`) within the same React app.

### 6.1 Layout

- Full-viewport layout: left Sidebar (same design system) + main content area
- Main area: Topbar + 2-column grid (controls left, progress feed right)

### 6.2 ETL Controls Panel

| Button | Action | Enabled When |
|--------|--------|--------------|
| Start | POST /admin/etl/start — sets `etl_status='running'` in Redis | Status is Idle or Completed or Error |
| Pause | POST /admin/etl/pause — sets `etl_status='pause'` | Status is Running |
| Resume | POST /admin/etl/resume — clears pause flag | Status is Paused |
| Force Stop | POST /admin/etl/stop — sets `etl_status='stop'` | Status is Running or Paused |
| Reset | POST /admin/etl/reset — clears all ETL Redis keys | Status is Error, Completed, or Stopping |

> **Force Stop vs Graceful Shutdown**
> 
> Force Stop sets `etl_status='stop'` in Redis. The ETL worker checks this key after each product.
> 
> It will finish the current product, flush the buffer, then exit — no data is lost.
> 
> It does NOT kill the process immediately. The status transitions to 'Stopping' then 'Idle'.

### 6.3 Status Badge

| State | Color | Description |
|-------|-------|-------------|
| Idle | Gray | ETL is not running. Awaiting admin trigger. |
| Running | Green | ETL is actively scraping, embedding, and upserting. |
| Paused | Amber | ETL is suspended. Buffer preserved. Can resume. |
| Stopping | Amber | Stop signal sent. Waiting for current product to finish. |
| Error | Red | Unexpected failure (network, hardware). Check logs. |
| Completed | Teal | All URLs processed successfully. |

### 6.4 Progress Feed

- Live WebSocket stream of ETL events from Device 2 via the Gateway
- Each event shows: timestamp + event type + message (e.g. 'Processed 247/1,432 products')
- Auto-scrolls to latest event
- Color-coded by event type: info (white), success (teal), warning (amber), error (red)
- 'Clear Feed' button resets the visible log without affecting the ETL process

### 6.5 Stats Cards (read-only)

- Products scraped this run
- Products upserted to Supabase
- Products skipped (Redis cache hit)
- Current run duration (live timer while Running)
- Estimated time remaining (based on current rate)

### 6.6 Admin WebSocket Contract

> **WebSocket Contract (ETL → Admin Dashboard)**
> 
> Connect to: `ws://<gateway-ip>:8000/ws/admin`
> 
> Auth header: `Authorization: Bearer <admin_token>`
> 
> Receive progress events:
> ```json
> { "type": "progress", "processed": 247, "total": 1432, "skipped": 18 }
> ```
> 
> Receive state change events:
> ```json
> { "type": "state_change", "state": "Running" | "Paused" | "Completed" | "Error" }
> ```
> 
> Receive error events:
> ```json
> { "type": "error", "message": "...", "url": "..." }
> ```

---

## 7. Routing

| Route | Component | Auth Required | Description |
|-------|-----------|---------------|-------------|
| `/` | Redirect → /chat | No | Root redirects to chat |
| `/chat` | ChatPage | No | End-user chat interface |
| `/admin` | AdminPage | Yes | ETL admin dashboard — requires admin token |
| `/*` | NotFound | No | 404 fallback |

---

## 8. Responsive Behavior

| Breakpoint | Sidebar | Product Grid | Chat Input |
|------------|---------|--------------|------------|
| ≥ 1024px (desktop) | Visible by default (260px) | 3 columns | Full width |
| 640–1023px (tablet) | Collapsed by default, toggle via ☰ | 2 columns | Full width |
| < 640px (mobile) | Collapsed, slides in as overlay | 1 column | Suggestion chips hidden |

---

## 9. Error States

| Scenario | UI Behavior |
|----------|-------------|
| WebSocket connection lost | Status dot turns red; toast notification 'Connection lost — retrying...' |
| Message send fails | User message bubble shows retry icon; toast 'Failed to send — click to retry' |
| Empty search results | AI message: 'No products found for your query. Try rephrasing or using broader terms.' |
| Stream timeout (> 30s) | AI bubble shows error state: 'Response timed out. Please try again.' |
| Product image load failure | Replaced by a placeholder image with product initial letter |
| Admin not authenticated | Redirect to /login before accessing /admin route |

---

## 10. Feature Status

| Feature / Screen | Status | Priority | Owner |
|------------------|--------|----------|-------|
| Chat UI — Sidebar (history, new chat, user info) | **Done** | P0 | Boj |
| Chat UI — Topbar with status indicator | **Done** | P0 | Boj |
| Chat UI — Message list + auto-scroll | **Done** | P0 | Boj |
| Chat UI — User message bubble | **Done** | P0 | Boj |
| Chat UI — AI streaming bubble + cursor | **Done** | P0 | Boj |
| Chat UI — Product card display (3-col grid) | **In Progress** | P0 | Boj |
| Chat UI — Suggestion chips | **Done** | P1 | Boj |
| Chat UI — WebSocket connection (real backend) | **Planned** | P0 | Boj |
| Chat UI — Conversation history (load from API) | **Planned** | P1 | Boj |
| Chat UI — Mobile responsive layout | **Planned** | P2 | Boj |
| Admin — ETL Controls (Start/Pause/Resume/Stop) | **In Progress** | P0 | Team |
| Admin — Status badge component | **In Progress** | P0 | Team |
| Admin — Live progress feed (WS) | **Planned** | P0 | Team |
| Admin — Stats cards | **Planned** | P1 | Team |
| Admin — Authentication guard | **Planned** | P1 | Team |
| Design tokens (CSS variables) | **Done** | P0 | Boj |
| Shared component — error toast | **Planned** | P1 | Team |
| Shared component — loading skeleton | **Planned** | P2 | Team |

---

*Nexus Marketplace — Frontend PRD v1.0 — Confidential*

*ISIMM PFA Project | April 2026*
