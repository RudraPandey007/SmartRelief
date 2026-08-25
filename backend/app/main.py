"""
FastAPI application entry point.

Covers:
  - CORS (explicit origins from .env)
  - Rate limiting (slowapi, per-IP)
  - API key authentication (global dependency)
  - /health endpoint for smoke-testing
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings, Settings
from app.security import limiter, require_api_key, rate_limit_exceeded_handler
from app.database import get_engine, load_all_seed_data

# Import routers
from app.routers import villages, risk, relocation, simulation, dashboard

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    
    # Startup: verify critical config
    if settings.APP_API_KEY == "REPLACE_WITH_INTERNAL_APP_API_KEY":
        logging.warning(
            "⚠️  APP_API_KEY is still the placeholder value. "
            "Set a real key in .env before production use."
        )
    
    # Startup: create tables and load seed data if empty
    engine = get_engine(settings.DATABASE_URL)
    summary = load_all_seed_data(engine)
    if any(v > 0 for v in summary.values()):
        logging.info(f"🌱 Seed data loaded: {summary}")
    else:
        logging.info("📦 Database already populated, skipping seed load.")
    
    # Store engine on app state for routers to access
    app.state.db_engine = engine
    
    yield
    # Shutdown: nothing to clean up for MVP


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Relocation & Evacuation Decision Support System",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Rate limiter (must be added before routes) ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# --- CORS (explicit origins from .env) ---
settings_for_cors = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_for_cors.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoint (no API key required — used for uptime checks)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
@limiter.limit("60/minute")
async def health(request: Request):
    return {"status": "ok", "service": "relocation-dss"}


# ---------------------------------------------------------------------------
# Protected demo route — proves the API key gate works
# ---------------------------------------------------------------------------
@app.get(
    "/protected-example",
    tags=["ops"],
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def protected_example(request: Request):
    return {
        "message": "✅ You are authenticated. The API key gate works.",
    }


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(villages.router)
app.include_router(risk.router)
app.include_router(relocation.router)
app.include_router(simulation.router)
app.include_router(dashboard.router)
