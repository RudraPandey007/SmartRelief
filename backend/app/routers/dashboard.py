"""Dashboard router — aggregate overview for the frontend."""
from fastapi import APIRouter, Depends, Request
from slowapi import Limiter

from app.config import get_settings
from app.database import get_engine, get_all_villages, get_all_shelters, get_all_routes
from app.security import require_api_key, limiter
from app.models.schemas import DashboardOverview

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/overview", response_model=DashboardOverview)
@limiter.limit("30/minute")
async def dashboard_overview(
    request: Request,
):
    """Get aggregate counts for the dashboard."""
    settings = get_settings()
    engine = get_engine(settings.DATABASE_URL)

    villages = get_all_villages(engine)
    shelters = get_all_shelters(engine)
    routes = get_all_routes(engine)

    # Risk classification counts
    from app.services.hazard_engine import compute_hazard_for_village
    risk_counts = {"extreme": 0, "high": 0, "medium": 0, "low": 0}
    total_affected = 0

    for v in villages:
        info = compute_hazard_for_village(v)
        risk_counts[info["risk_classification"]] += 1
        if info["risk_classification"] in ("extreme", "high"):
            total_affected += v.households

    # Shelter capacity
    total_shelter_capacity = sum(s.total_capacity for s in shelters)
    available_shelter_capacity = sum(s.total_capacity - s.current_occupancy for s in shelters)

    # Route stats
    blocked_routes = sum(1 for r in routes if r.route_status == "blocked")
    degraded_routes = sum(1 for r in routes if r.route_status == "degraded")

    return DashboardOverview(
        total_villages=len(villages),
        villages_by_risk=risk_counts,
        total_population=sum(v.population for v in villages),
        total_households=sum(v.households for v in villages),
        total_shelters=len(shelters),
        total_shelter_capacity=total_shelter_capacity,
        available_shelter_capacity=available_shelter_capacity,
        total_routes=len(routes),
        blocked_routes=blocked_routes,
        degraded_routes=degraded_routes,
        active_plans=0,  # Will be populated when plans are stored
        total_affected_population=total_affected,
    )
