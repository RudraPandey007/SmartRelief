"""
Security module: API key authentication dependency and rate limiter setup.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Rate limiter (global singleton, wired into main.py later)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


def _parse_rate(rate_str: str) -> int:
    """Parse e.g. '30/minute' -> 30."""
    try:
        return int(rate_str.split("/")[0])
    except (ValueError, IndexError):
        return 30


# ---------------------------------------------------------------------------
# API Key dependency
# ---------------------------------------------------------------------------
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    request: Request,
    api_key: Optional[str] = Depends(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI dependency that enforces X-API-Key on every protected route."""
    if not api_key or api_key != settings.APP_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "Missing or invalid X-API-Key header.",
            },
        )
    return api_key


# ---------------------------------------------------------------------------
# Custom rate-limit exceeded handler (returns 429 + Retry-After)
# ---------------------------------------------------------------------------
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", None) or 60
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
        },
        headers={"Retry-After": str(retry_after)},
    )
