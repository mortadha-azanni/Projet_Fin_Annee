# Searchily Analytics Module

## What We Built

A self-contained analytics dashboard integrated into the Searchily platform.
It connects directly to the project's PostgreSQL database via Cube.js and
presents product intelligence through a protected React dashboard.

### Features
- **Products by Source** — Bar chart showing total indexed products split by Mytek vs Tunisianet
- **Category Distribution** — Horizontal bar chart showing all 8 top-level categories with full subcategory rollup
- **Price Range Selector** — Interactive dropdown to select a category and view min/avg/max prices in DT
- **User Profile Search** — Search any user by email or ID and view their full profile card with avatar
- **Admin Protected** — Login page connected to `POST /auth/admin/login` on the gateway, JWT session stored for 8 hours

### Tech Stack
| Layer | Technology |
|-------|------------|
| Data API | Cube.js 0.35 (official Docker image) |
| Database | PostgreSQL (shared with main stack) |
| Frontend | React 18 + Vite + Recharts |
| Auth | Gateway JWT via `/auth/admin/login` |
| Serving | Node + serve (production build) |
| Orchestration | Docker Compose |

---

## Architecture
```
PostgreSQL
│
▼
Cube.js (port 4000)     ← reads DB, serves analytics API
│
▼
Dashboard (port 3001)   ← React app served via Node (serve)
│
▼
Admin Browser           ← protected by JWT login
```
### Folder Structure
```
analytics/
├── docker-compose.yml        ← analytics-only compose, joins pfa-network
├── .env                      ← local env (not committed)
├── .env.example              ← template for env variables
├── ANALYTICS_GUIDE.md        ← this file
├── cubejs/
│   ├── Dockerfile
│   ├── cube.js               ← Cube.js server config
│   └── model/
│       ├── cubes/            ← data models (Products, Categories, Users, rollups)
│       └── views/            ← query views exposed to frontend
└── dashboard/
├── Dockerfile            ← multi-stage build (Vite → serve)
├── package.json
├── vite.config.js
└── src/
├── auth/             ← login page + useAuth hook
├── components/       ← all chart components + layout
└── hooks/            ← useCubeQuery wrapper
```
---

## Docker Guide

### Prerequisites
- Docker Desktop must be running
- The main project stack must be started first (creates `pfa-network`)

### First Time Setup

**Step 1 — Start the main stack:**
```bash
cd Projet_Fin_Annee
docker compose up -d
Step 2 — Create the analytics env file:
bashcd analytics
copy .env.example .env
Open .env and fill in the same DB credentials as the root .env.
Also set CUBEJS_API_SECRET to any secure random string.
Step 3 — Start the analytics stack:
bashdocker compose up -d --build
Step 4 — Open the dashboard:
http://localhost:3001
Login with your admin credentials.

Daily Usage
Start everything:
bash# From Projet_Fin_Annee/
docker compose up -d

# From Projet_Fin_Annee/analytics/
docker compose up -d
Stop everything:
bash# From Projet_Fin_Annee/analytics/
docker compose down

# From Projet_Fin_Annee/
docker compose down
View logs:
bashdocker logs analytics_cubejs --tail=50
docker logs analytics_dashboard --tail=50
Rebuild after code changes:
bash# From Projet_Fin_Annee/analytics/
docker compose up -d --build

Startup Order (IMPORTANT)
Always start in this order:

Docker Desktop
Main stack (Projet_Fin_Annee/docker compose up -d)
Analytics stack (Projet_Fin_Annee/analytics/docker compose up -d)

Never start analytics alone — it needs pfa-network which is created by the main stack.

Environment Variables
VariableDescriptionDB_HOSTPostgreSQL host (same as root .env)DB_PORTPostgreSQL portDB_NAMEDatabase nameDB_USERDatabase userDB_PASSWORDDatabase passwordCUBEJS_API_SECRETSecret key for signing Cube.js JWT tokensVITE_CUBEJS_API_URLCube.js API base URL for the dashboard

Troubleshooting
network pfa-network not found
→ Start the main stack first: cd Projet_Fin_Annee && docker compose up -d
Dashboard shows blank page
→ Check Cube.js logs: docker logs analytics_cubejs --tail=50
Login fails with 401
→ Verify your admin account exists in the admins table in PostgreSQL
Charts show no data
→ Verify the database has products: SELECT COUNT(*) FROM products;
