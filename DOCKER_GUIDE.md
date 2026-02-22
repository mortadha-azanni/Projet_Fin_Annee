# Docker Guide for Team - PFA Project

**A beginner-friendly guide to working with Docker in this project**

---

## 📚 Table of Contents

1. [What is Docker?](#what-is-docker)
2. [Installation](#installation)
3. [Basic Concepts](#basic-concepts)
4. [Project Setup](#project-setup)
5. [Development Workflow](#development-workflow)
6. [Testing the Services](#testing-the-services)
7. [Common Commands](#common-commands)
8. [Troubleshooting](#troubleshooting)

---

## 🐋 What is Docker?

**Docker** packages your application and all its dependencies into **containers** - lightweight, portable boxes that run the same way on any computer.

### Why We Use Docker?

- ✅ **No "works on my machine" problems** - Same environment for everyone
- ✅ **Easy setup** - No manual installation of Python, Redis, or other dependencies
- ✅ **Isolation** - Each service runs in its own container without conflicts
- ✅ **Team consistency** - Everyone uses identical environments

### Key Terms

| Term | Explanation |
|------|-------------|
| **Image** | A blueprint/template for creating containers (like a recipe) |
| **Container** | A running instance of an image (like a cooked meal) |
| **Docker Compose** | A tool to run multiple containers together as a system |
| **Volume** | A way to share files between your computer and containers |
| **Port** | A door that lets you access services (e.g., `:8000` for gateway) |

---

## 💻 Installation

### Ubuntu/Linux
```bash
# Install Docker
sudo apt update
sudo apt install docker.io docker-compose

# Add yourself to docker group (avoid using sudo)
sudo usermod -aG docker $USER

# Log out and log back in, then test
docker --version
docker-compose --version
```

### macOS
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Or use Homebrew:
brew install --cask docker

# Start Docker Desktop, then verify:
docker --version
docker-compose --version
```

### Windows
1. Download **Docker Desktop** from: https://www.docker.com/products/docker-desktop
2. Run the installer
3. Restart your computer
4. Open PowerShell or Command Prompt and verify:
```bash
docker --version
docker-compose --version
```

---

## 🏗️ Basic Concepts

### Our Project Architecture

```
┌─────────────┐
│   Client    │  (Your browser/curl)
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│   Gateway   │◄────►│    Redis    │
│  Container  │      │  Container  │
│   :8000     │      │   :6380     │
└──────┬──────┘      └─────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐
│  Scraper    │ │   Ranker    │
│  Container  │ │  Container  │
│   :8001     │ │   :8002     │
└─────────────┘ └─────────────┘
```

### What Happens When You Run Docker Compose?

1. **Reads** `docker-compose.yml` (our configuration file)
2. **Builds** images from `Dockerfile` in each service folder
3. **Creates** containers from those images
4. **Connects** containers via an internal network
5. **Exposes** ports so you can access services from your browser/terminal

---

## 🚀 Project Setup

### First Time Setup

1. **Clone the repository** (if you haven't already)
```bash
git clone <repository-url>
cd PFA
```

2. **Check the project structure**
```bash
ls -la
# You should see:
# - docker-compose.yml
# - .env.example
# - gateway_node/
# - scraper_node/
# - ranker_node/
```

3. **Set up environment variables**
```bash
# Copy the example file
cp .env.example .env

# Edit the .env file and add your API keys
nano .env  # or use your preferred editor
# Important: Add your GEMINI_API_KEY at minimum!
```

4. **Build and start all services**
```bash
docker-compose up --build
```

**What's happening?**
- `docker-compose` - The tool to manage multiple containers
- `up` - Start all services
- `--build` - Build the images first (use this the first time or when code changes)

4. **Wait for services to start** (this may take 1-2 minutes the first time)

You'll see logs from all services. When you see:
```
gateway_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
scraper_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
ranker_1   | INFO:     Uvicorn running on http://0.0.0.0:8000
```
Everything is ready! ✅

---

## 💼 Development Workflow

### Starting Services

**Option 1: Foreground (see logs in terminal)**
```bash
docker-compose up
```
- Logs appear in your terminal
- Press `Ctrl+C` to stop all services

**Option 2: Background (detached mode)**
```bash
docker-compose up -d
```
- Services run in background
- Terminal is free for other commands
- Use `docker-compose logs -f` to see logs

### Stopping Services

**If running in foreground:**
```bash
Press Ctrl+C
```

**If running in background:**
```bash
docker-compose down
```

### Making Code Changes

**Good news!** 🎉 You don't need to restart Docker when you edit code!

1. Edit your code in `gateway_node/main.py` (or any service)
2. Save the file
3. The service **automatically reloads** (hot reload is enabled)
4. Test your changes immediately

**When DO you need to rebuild?**
- When you change `pyproject.toml` (add new dependencies)
- When you change `Dockerfile`
- When you change `docker-compose.yml`

```bash
# Rebuild and restart
docker-compose up --build
```

### Viewing Logs

**See logs from all services:**
```bash
docker-compose logs -f
```

**See logs from one service:**
```bash
docker-compose logs -f gateway
docker-compose logs -f scraper
docker-compose logs -f ranker
```

**See last 50 lines:**
```bash
docker-compose logs --tail=50 gateway
```

---

## 🧪 Testing the Services

### 1. Check All Services Are Running

```bash
docker-compose ps
```

You should see 4 services with "State: Up":
- pfa_gateway_1
- pfa_scraper_1
- pfa_ranker_1
- pfa_redis_1

### 2. Test Individual Services

**Gateway (port 8000):**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**Scraper (port 8001):**
```bash
curl http://localhost:8001/health
# Expected: {"status":"healthy"}
```

**Ranker (port 8002):**
```bash
curl http://localhost:8002/health
# Expected: {"status":"healthy"}
```

### 3. Test Inter-Service Communication

**Check if gateway can talk to other services:**
```bash
curl http://localhost:8000/services/health
```

Expected response:
```json
{
    "gateway": "healthy",
    "scraper": "healthy",
    "ranker": "healthy"
}
```

### 4. Test Complete Workflow

**Full scrape-and-rank workflow:**
```bash
curl "http://localhost:8000/scrape-and-rank?url=https://example.com"
```

### 5. View API Documentation

Open in your browser:
- Gateway API: http://localhost:8000/docs
- Scraper API: http://localhost:8001/docs
- Ranker API: http://localhost:8002/docs

You'll see **Swagger UI** - an interactive API documentation where you can test endpoints!

---

## 📋 Common Commands

### Essential Commands

| Command | What It Does |
|---------|--------------|
| `docker-compose up` | Start all services (see logs) |
| `docker-compose up -d` | Start all services (background) |
| `docker-compose down` | Stop and remove all containers |
| `docker-compose ps` | List running containers |
| `docker-compose logs -f` | View real-time logs |
| `docker-compose restart gateway` | Restart one service |
| `docker-compose up --build` | Rebuild and start (after changing code/deps) |

### Advanced Commands

**Restart a single service:**
```bash
docker-compose restart gateway
```

**Rebuild a single service:**
```bash
docker-compose build gateway
docker-compose up -d gateway
```

**Execute command inside a container:**
```bash
docker-compose exec gateway ls -la
docker-compose exec gateway python --version
```

**Clean up everything (including volumes):**
```bash
docker-compose down -v
```
⚠️ This deletes all data in Redis!

**View resource usage:**
```bash
docker stats
```

**Remove unused images/containers:**
```bash
docker system prune -a
```

---

## 🔧 Troubleshooting

### Problem: "Port already in use"

**Error:**
```
Cannot start service gateway: ports are not available: bind: address already in use
```

**Solution:**
```bash
# Find what's using the port (e.g., 8000)
sudo lsof -i :8000
# or
netstat -tuln | grep 8000

# Stop that process, or change the port in docker-compose.yml
```

### Problem: "Network needs to be recreated"

**Error:**
```
ERROR: Network "pfa_default" needs to be recreated
```

**Solution:**
```bash
docker-compose down
docker-compose up -d
```

### Problem: Service keeps restarting

**Check logs:**
```bash
docker-compose logs gateway
```

**Common causes:**
- Syntax error in Python code
- Missing dependency in pyproject.toml
- Port conflict

**Solution:**
1. Fix the error in your code
2. Rebuild: `docker-compose up --build`

### Problem: Changes not appearing

**If your code changes aren't reflected:**

1. **Check if hot-reload is working:**
   - Look for "Reloading..." in logs when you save
   
2. **If not, restart the service:**
   ```bash
   docker-compose restart gateway
   ```

3. **If still not working, rebuild:**
   ```bash
   docker-compose up --build
   ```

### Problem: Can't connect to services

**Check if services are running:**
```bash
docker-compose ps
```

**If "State" shows "Exit":**
```bash
docker-compose logs <service-name>
# Read the error message and fix it
```

**Restart everything:**
```bash
docker-compose down
docker-compose up --build
```

### Problem: "Permission denied" errors (Linux)

**Add yourself to docker group:**
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Problem: Containers are slow

**Check resource usage:**
```bash
docker stats
```

**Clean up unused resources:**
```bash
docker system prune -a
docker volume prune
```

---

## 🎯 Quick Reference Card

**Print this and keep it handy! 📌**

```
╔════════════════════════════════════════════════════════════╗
║                    QUICK REFERENCE                         ║
╠════════════════════════════════════════════════════════════╣
║ START ALL SERVICES                                         ║
║   docker-compose up -d                                     ║
║                                                            ║
║ STOP ALL SERVICES                                          ║
║   docker-compose down                                      ║
║                                                            ║
║ VIEW LOGS (LIVE)                                           ║
║   docker-compose logs -f                                   ║
║                                                            ║
║ CHECK STATUS                                               ║
║   docker-compose ps                                        ║
║                                                            ║
║ REBUILD AFTER CHANGES                                      ║
║   docker-compose up --build                                ║
║                                                            ║
║ TEST SERVICES                                              ║
║   curl http://localhost:8000/health                        ║
║   curl http://localhost:8000/services/health               ║
║                                                            ║
║ API DOCS                                                   ║
║   http://localhost:8000/docs                               ║
║   http://localhost:8001/docs                               ║
║   http://localhost:8002/docs                               ║
╚════════════════════════════════════════════════════════════╝
```

---

## 📚 Learning Resources

**Want to learn more about Docker?**

- [Docker Official Tutorial](https://www.docker.com/101-tutorial)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Play with Docker](https://labs.play-with-docker.com/) - Practice online

---

## 🤝 Getting Help

1. **Check this guide first** - Most answers are here
2. **Read the error message** - It usually tells you what's wrong
3. **Check logs** - `docker-compose logs -f`
4. **Ask the team** - Share your error messages on Slack/Teams
5. **Google it** - "Docker [your error]" usually finds solutions

---

## ✅ Checklist for New Team Members

- [ ] Install Docker and Docker Compose
- [ ] Verify installation: `docker --version`
- [ ] Clone the project repository
- [ ] Copy environment file: `cp .env.example .env`
- [ ] Edit `.env` and add your GEMINI_API_KEY
- [ ] Run `docker-compose up --build`
- [ ] Wait for services to start (~2 minutes)
- [ ] Test: `curl http://localhost:8000/health`
- [ ] Open API docs: http://localhost:8000/docs
- [ ] Make a small code change and see hot reload work
- [ ] Stop services: `Ctrl+C` or `docker-compose down`
- [ ] Celebrate! 🎉 You're ready to develop!

---

**Questions?** Ask in the team chat! We're here to help. 🚀

**Happy coding!** 👨‍💻👩‍💻
