"""
Risk Router — risk assessment endpoint.

Endpoints:
  POST /risk/assess  — compute hazard + vulnerability for a village
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter

from app.config import get_settings
from app.database import get_engine, get_village_by_id
from app.security import require_api_key, limiter
from app.services.hazard_engine import compute_hazard_for_village
from app.services.vulnerability_engine import compute_vulnerability_for_village
from app.models.schemas import ErrorResponse

router = APIRouter(
    prefix="/risk",
    tags=["risk"],
    dependencies=[Depends(require_api_key)],
)


class RiskAssessRequest(BaseModel):
    village_id: str = Field(..., min_length=1, max_length=50)


class RiskAssessResponse(BaseModel):
    village_id: str
    village_name: str
    district: str
    state: str
    hazard_score: float
    risk_classification: str
    vulnerability_score: float
    vulnerability_classification: str
    combined_risk: float


@router.post("/assess", response_model=RiskAssessResponse)
@limiter.limit("30/minute")
async def assess_risk(
    request: Request,
    body: RiskAssessRequest,
):
    """Compute hazard and vulnerability scores for a village."""
    settings = get_settings()
    engine = get_engine(settings.DATABASE_URL)
    village = get_village_by_id(engine, body.village_id)

    if not village:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Village {body.village_id} not found"},
        )

    # Compute scores
    hazard = compute_hazard_for_village(village)
    vuln = compute_vulnerability_for_village(village)

    # Combined risk (weighted average)
    combined = round(
        0.6 * hazard["hazard_score"] + 0.4 * vuln["vulnerability_score"],
        4,
    )

    return RiskAssessResponse(
        village_id=village.id,
        village_name=village.name,
        district=village.district,
        state=village.state,
        hazard_score=hazard["hazard_score"],
        risk_classification=hazard["risk_classification"],
        vulnerability_score=vuln["vulnerability_score"],
        vulnerability_classification=vuln["vulnerability_classification"],
        combined_risk=combined,
    )
