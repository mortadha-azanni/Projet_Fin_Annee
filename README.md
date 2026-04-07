# PFA - Microservices Architecture
**Projet Fin d'Année**

A distributed microservices system built with FastAPI and Docker Compose, featuring web scraping, data ranking, and an API gateway.

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│   Gateway   │◄────►│    Redis    │
│   :8000     │      │   :6380     │
└──────┬──────┘      └─────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Scraper    │ │   Ranker    │ │   ...       │
│   :8001     │ │   :8002     │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Services

- **Gateway Node** (`:8000`) - API Gateway that orchestrates requests between services
- **Scraper Node** (`:8001`) - Web scraping service for data extraction
- **Ranker Node** (`:8002`) - Ranking and scoring service for scraped data
- **Redis** (`:6380`) - Caching layer for improved performance

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)

> **📘 New to Docker?** Check out our [Docker Guide for Beginners](DOCKER_GUIDE.md) - a complete step-by-step guide for team members!

### Running the Project

```bash
# Copy environment variables template
cp .env.example .env

# Edit .env and add your API keys (especially GEMINI_API_KEY)
nano .env  # or use your preferred editor

# Start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Accessing Services

- Gateway API: http://localhost:8000
- Gateway Docs: http://localhost:8000/docs
- Scraper API: http://localhost:8001
- Scraper Docs: http://localhost:8001/docs
- Ranker API: http://localhost:8002
- Ranker Docs: http://localhost:8002/docs
- Redis: localhost:6380

## 📡 API Endpoints

### Gateway (`/`)

- `GET /` - Service information
- `GET /health` - Health check
- `GET /services/health` - Check all services health
- `GET /scrape-and-rank?url={url}` - Complete workflow: scrape and rank

### Scraper (`/`)

- `GET /` - Service information
- `GET /health` - Health check
- `GET /scrape?url={url}` - Scrape data from URL

### Ranker (`/`)

- `GET /` - Service information
- `GET /health` - Health check
- `POST /rank` - Rank list of items

## 🛠️ Development

### Project Structure

```
PFA/
├── docker-compose.yml          # Docker orchestration
├── README.md                   # This file
├── .gitignore                  # Git ignore patterns
├── gateway_node/
│   ├── Dockerfile
│   ├── main.py                 # Gateway service
│   ├── pyproject.toml          # Dependencies
│   └── uv.lock
├── scraper_node/
│   ├── Dockerfile
│   ├── main.py                 # Scraper service
│   ├── pyproject.toml
│   └── uv.lock
└── ranker_node/
    ├── Dockerfile
    ├── main.py                 # Ranker service
    ├── pyproject.toml
    └── uv.lock
```

### Local Development

Each service can be run independently:

```bash
cd gateway_node
uv sync
uv run uvicorn main:app --reload --port 8000
```

### Adding Dependencies

```bash
cd <service_folder>
# Edit pyproject.toml, then:
uv lock
```

## 🧪 Testing

```bash
# Test gateway health
curl http://localhost:8000/health

# Test all services
curl http://localhost:8000/services/health

# Test scrape and rank workflow
curl "http://localhost:8000/scrape-and-rank?url=https://example.com"
```

## 🔧 Environment Variables

All environment variables are documented in [.env.example](.env.example). Copy it to `.env` and configure:

```bash
cp .env.example .env
```

### Key Variables:

**Gateway Node:**
- `SCRAPER_URL` - Scraper service URL (default: `http://scraper:8000`)
- `RANKER_URL` - Ranker service URL (default: `http://ranker:8000`)
- `REDIS_HOST` - Redis host (default: `redis`)

**API Keys:**
- `GEMINI_API_KEY` - Google Gemini API key (required for AI features)
  - Get your key: https://makersuite.google.com/app/apikey
- `OPENAI_API_KEY` - OpenAI API key (optional, alternative)

**See [.env.example](.env.example) for complete configuration options.**

## 📝 TODO

- [ ] Implement actual scraping logic (BeautifulSoup/Playwright)
- [ ] Implement ranking algorithms
- [ ] Add Redis caching to gateway
- [ ] Add authentication/authorization
- [ ] Add rate limiting
- [ ] Add comprehensive logging
- [ ] Add unit and integration tests
- [ ] Add CI/CD pipeline
- [ ] Add monitoring and observability
- [ ] Add API rate limiting per service
- [ ] Document API schemas with Pydantic models

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📄 License

[Add your license here]

## 👥 Authors

[Add your name and teammates]

