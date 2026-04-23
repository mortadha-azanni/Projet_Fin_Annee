# PFA (Projet Fin d'Année) - Automated E-commerce Search & Ranking System

A distributed microservices system built with **FastAPI**, **Celery**, **Redis**, **pgvector**, and **React/Vite**. This application features an intelligent Semantic Search and NLP pipeline that scrapes e-commerce data and uses Large Language Models and Hybrid Search (BM25 + Cosine Distance) to return the best product recommendations ranked by relevance and price.

## 🏗️ Architecture

```text
┌─────────────┐
│   Client    │ (React / Vite)
└──────┬──────┘
       │ WebSocket & REST
       ▼
┌─────────────┐      ┌─────────────┐
│   Gateway   │◄────►│    Redis    │
│   :8000     │      │   :6379     │
└──────┬──────┘      └─────────────┘
       │                    ▲
       ├──────────────┬─────┴────────────┐
       ▼              ▼                  ▼
┌─────────────┐ ┌─────────────┐    ┌─────────────┐
│  Scraper    │ │   Ranker    │    │ Celery NLP  │ 
│   :8001     │ │   :8002     │    │ Worker      │
└─────────────┘ └─────────────┘    └─────────────┘
```

### Services Included
- **Frontend Client** - React/Vite Application (`my-react-app`) listening on port `5173`. Includes a Chat Interface and an ETL Admin Dashboard.
- **Gateway Node** (`:8000`) - API Gateway orchestrating REST & WebSocket traffic to downstream microservices.
- **Scraper Node** (`:8001`) - Web scraping routines using Celery to harvest e-commerce hardware data.
- **Ranker Node** (`:8002`) - Semantic and Keyword search using `SentenceTransformers`, `GLiNER` NER extraction, and `Google Gemini`.
- **Celery Worker(s)** - Handles asynchronous NLP & Scraping Tasks to prevent API timeouts.
- **Redis** (`:6380` locally, `:6379` internally) - Message broker for Celery and state caching layer.

---

## 🚀 Quick Start

### Prerequisites
- **Docker** & **Docker Compose**
- **Node.js** & **npm** (for the frontend)
- At least **4GB to 8GB of RAM allocated to Docker** (Crucial: Ranker loads PyTorch NLP models!).

### 1. Backend Setup

1. Copy the environment variables template and configure your API keys:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and add your **`GEMINI_API_KEY`**.
3. Spin up the backend microservices using Docker Compose:
   ```bash
   docker compose build
   docker compose up -d
   ```
4. Verify all containers are running smoothly without restarting:
   ```bash
   docker compose logs -f
   ```

### 2. Frontend Setup

1. Open a new terminal and navigate to the React app:
   ```bash
   cd my-react-app
   ```
2. Install the necessary Node modules:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 🖥️ Accessing the Application

Once everything is booted, you can access the different interfaces:

- **💬 Chat Interface (Main App):** [http://localhost:5173/chat](http://localhost:5173/chat)
- **⚙️ ETL Admin Dashboard:** [http://localhost:5173/admin](http://localhost:5173/admin)
- **🚪 Gateway API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔧 Managing and Developing

### Stopping the Services
To stop the backend microservices, run:
```bash
docker compose downproffisional
```
To wipe data (including the Redis cache), run:
```bash
docker compose down -v
```

### Important Notes on NLP Memory
The Ranker's `celery_worker` container dynamically loads models like **all-MiniLM-L6-v2** (SentenceTransformers) and **GLiNER**. 
If you see the `celery_worker` exiting with `Signal 9 (SIGKILL)`, it means Docker ran out of memory. 
Ensure Docker Desktop or your Docker Engine is configured with adequate RAM.

## 🤝 Contributing
1. Create a feature branch
2. Make your changes and test locally
3. Submit a pull request
