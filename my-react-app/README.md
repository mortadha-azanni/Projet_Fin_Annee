# Nexus Frontend (React + Vite)

Frontend app for:

- Chat interface at /chat
- Admin interface at /admin

## Tech Stack

- React 19
- React Router
- Vite
- ESLint

## Environment Variables

Create my-react-app/.env:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

These are used by src/chat/hooks/useChat.js:

- POST {VITE_API_URL}/search
- WS {VITE_WS_URL}/ws/status/{task_id}

## Install and Run

```bash
npm install
npm run dev
```

Default local URL: http://localhost:5173

## Build and Lint

```bash
npm run build
npm run lint
npm run preview
```

## Current Routes

- / -> redirects to /chat
- /chat -> ChatPage
- /admin -> AdminPage

## Frontend Structure

- src/chat/: chat UI, transport hook, message components.
- src/admin/: admin page and ETL controls UI.
- src/shared/tokens.css: shared design tokens.
