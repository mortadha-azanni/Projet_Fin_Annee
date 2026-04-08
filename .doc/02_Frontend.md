# Frontend Details

## Overview
The frontend is built with React and Vite. It serves an interface (`my-react-app`) that connects with the Gateway Node, interacting with search, chat capabilities, and web scraping administration.

## Directory Structure
- `my-react-app/src/`: Contains all essential source code.
  - `admin/`: Controls for the ETL (Extract, Transform, Load) pipelines, displaying `StatusBadge.jsx`, `ProgressFeed.jsx`, and a dashboard (`AdminPage.jsx`).
  - `chat/`: Handles conversational/search interactions. Holds components like `ChatInput.jsx`, `MessageList.jsx`, and `ProductCard.jsx`, driven by hooks like `useChat.js`.
  - `shared/`: Generic logic and styling like design tokens.

## Build Setup
The frontend dependencies and scripts are defined in `package.json`, utilizing standard Vite tooling (`vite.config.js`) for HMR and bundled builds. 
Websocket clients are tested directly via python scripts (e.g. `test_ws.py`).

## Responsibilities
- Provide a smooth UI for executing ranked search.
- Stream real-time events regarding scraper/ranker processes via WebSockets.
- Deliver mock or live rendering of extracted entities.