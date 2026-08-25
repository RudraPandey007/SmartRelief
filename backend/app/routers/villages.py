"""
Villages Router — basic CRUD-read for the frontend map.

Endpoints:
  GET /villages          — list all villages
  GET /villages/{id}     — get a single village by ID
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import get_all_villages, get_village_by_id
from app.models.schemas import VillageOut, VillageListOut, ErrorResponse
from app.security import require_api_key, limiter

router = APIRouter(
    prefix="/villages",
    tags=["villages"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=VillageListOut)
@limiter.limit("30/minute")
async def list_villages(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state"),
    risk_level: Optional[str] = Query(None, description="Filter by risk: extreme/high/medium/low"),
):
    """List all villages with optional state/risk filters."""
    from app.services.hazard_engine import classify_risk, compute_hazard_for_village

    settings = get_settings()
    engine = _get_engine(settings)
    villages = get_all_villages(engine)

    # Apply filters
    if state:
        villages = [v for v in villages if v.state.lower() == state.lower()]

    if risk_level:
        filtered = []
        for v in villages:
            info = compute_hazard_for_village(v)
            if info["risk_classification"] == risk_level.lower():
                filtered.append(v)
        villages = filtered

    return VillageListOut(
        count=len(villages),
        villages=[VillageOut.model_validate(v) for v in villages],
    )


@router.get("/{village_id}", response_model=VillageOut)
@limiter.limit("30/minute")
async def get_village(
    request: Request,
    village_id: str,
):
    """Get a single village by ID."""
    from app.services.hazard_engine import compute_hazard_for_village

    settings = get_settings()
    engine = _get_engine(settings)
    village = get_village_by_id(engine, village_id)

    if not village:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Village {village_id} not found"},
        )

    return VillageOut.model_validate(village)


def _get_engine(settings):
    """Get database engine from settings."""
    from app.database import get_engine
    return get_engine(settings.DATABASE_URL)
