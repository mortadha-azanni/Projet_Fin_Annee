from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
import asyncio
from core.database import create_pool, close_pool
from core.redis_client import create_redis, close_redis
from auth.router import router as auth_router
from routers.users import router as users_router
from routers.etl import router as etl_router
from routers.search import router as search_router
from routers.admin import router as admin_router
from pubsub import start_pubsub_listener
from core.security_middleware import SecurityMiddleware
import httpx

app = FastAPI(redirect_slashes=False)
# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────


async def init_db_pool_with_retry(retries: int = 30, delay_seconds: float = 5.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            await create_pool()
            print("[gateway] database pool connected")
            return
        except Exception as exc:
            print(f"[gateway] database pool init failed (attempt {attempt}/{retries}): {exc}")
            if attempt < retries:
                await asyncio.sleep(delay_seconds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB and Redis pools
    db_init_task = asyncio.create_task(init_db_pool_with_retry())
    await create_redis()
    
    # Start Pub/Sub listener
    pubsub_task = asyncio.create_task(start_pubsub_listener())
    
    yield
    
    # Graceful shutdown
    db_init_task.cancel()
    try:
        await db_init_task
    except asyncio.CancelledError:
        pass

    pubsub_task.cancel()
    try:
        await pubsub_task
    except asyncio.CancelledError:
        pass
        
    await close_redis()
    await close_pool()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API Gateway for scraper and ranker microservices",
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origins must be an explicit list when allow_credentials=True.
# Set CORS_ORIGINS env var to a comma-separated list for production.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security Middleware ────────────────────────────────────────────────────────
app.add_middleware(SecurityMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router,  prefix="/auth",   tags=["Auth"])
app.include_router(users_router, prefix="/user",   tags=["User"])
app.include_router(etl_router,   prefix="/scrape", tags=["ETL"])
app.include_router(search_router,                  tags=["Search"])
app.include_router(admin_router, prefix="/admin",  tags=["Admin"])


# ── Basic endpoints ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "gateway-node",
        "status": "running",
        "version": settings.VERSION,
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/services/health")
async def check_services_health():
    status_map = {"gateway": "healthy", "scraper": "unknown", "ranker": "unknown"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for key, url in [("scraper", settings.SCRAPER_URL), ("ranker", settings.RANKER_URL)]:
            try:
                r = await client.get(f"{url}/health")
                status_map[key] = "healthy" if r.status_code == 200 else "unhealthy"
            except Exception as exc:
                status_map[key] = f"error: {exc}"
    return status_map


# ── Legacy WebSocket aliases (kept for backwards compatibility) ────────────────

@app.websocket("/websocket_progress")
async def legacy_proxy_websocket_progress(websocket: WebSocket):
    from routers.etl import proxy_websocket_progress
    await proxy_websocket_progress(websocket)
