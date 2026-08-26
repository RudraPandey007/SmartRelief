"""
Relocation Router — the main "generate plan" endpoint.

Endpoints:
  POST /relocation/generate-plan  — full pipeline execution
"""
import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from slowapi import Limiter

from app.config import get_settings
from app.database import get_engine, get_village_by_id, get_all_shelters, get_all_routes, get_route_between
from app.security import require_api_key, limiter
from app.models.schemas import (
    GeneratePlanRequest,
    GeneratePlanResponse,
    OptimizationWeights,
    DestinationScore,
    RejectedDestination,
    ErrorResponse,
)

router = APIRouter(
    prefix="/relocation",
    tags=["relocation"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/generate-plan", response_model=GeneratePlanResponse)
@limiter.limit("10/minute")
async def generate_plan(
    request: Request,
    body: GeneratePlanRequest,
):
    """
    Generate an evacuation plan for a village.

    Runs the full pipeline:
      1. Hazard Risk Engine
      2. Vulnerability Engine
      3. Candidate Destination Engine
      4. Hard Constraint Filtering
      5. Capacity Engine
      6. Route Safety Engine
      7. Multi-Criteria Optimization
      8. Population Allocation
      9. Explainability Engine
    """
    settings = get_settings()
    engine = get_engine(settings.DATABASE_URL)

    # --- Step 0: Validate source village ---
    village = get_village_by_id(engine, body.village_id)
    if not village:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Village {body.village_id} not found"},
        )

    # --- Step 1: Hazard Risk Engine ---
    from app.services.hazard_engine import compute_hazard_for_village
    hazard_result = compute_hazard_for_village(village)

    # --- Step 2: Vulnerability Engine ---
    from app.services.vulnerability_engine import compute_vulnerability_for_village
    vuln_result = compute_vulnerability_for_village(village)

    # Combined risk
    combined_risk = round(
        0.6 * hazard_result["hazard_score"] + 0.4 * vuln_result["vulnerability_score"],
        4,
    )

    # --- Step 3: Candidate Destination Engine ---
    from app.services.candidate_engine import find_all_candidates

    all_villages = _get_all_villages(engine)
    all_shelters = get_all_shelters(engine)

    candidates = find_all_candidates(
        source_lat=village.latitude,
        source_lon=village.longitude,
        villages=all_villages,
        shelters=all_shelters,
        radius_km=body.search_radius_km,
        exclude_source_id=village.id,
    )

    # --- Step 4: Hard Constraint Filtering ---
    from app.services.filtering_engine import filter_candidates

    # Compute hazard scores for each candidate
    hazard_scores = {}
    hazard_classifications = {}
    for c in candidates:
        # For village candidates, compute their own hazard
        if c["type"] == "village":
            # Find the village object
            for v in all_villages:
                if v.id == c["id"]:
                    h = compute_hazard_for_village(v)
                    hazard_scores[c["id"]] = h["hazard_score"]
                    hazard_classifications[c["id"]] = h["risk_classification"]
                    break
        else:
            # Shelters assumed low risk
            hazard_scores[c["id"]] = 0.1
            hazard_classifications[c["id"]] = "low"

    # Get route statuses
    # Use "no_data" sentinel when no route record exists — this is a DATA GAP,
    # not the same as an explicitly blocked route.
    route_statuses = {}
    for c in candidates:
        route = get_route_between(engine, village.id, c["id"])
        if route:
            route_statuses[c["id"]] = route.route_status
        else:
            route_statuses[c["id"]] = "no_data"

    accepted, rejected_raw = filter_candidates(
        candidates, hazard_scores, route_statuses,
        hazard_classifications=hazard_classifications,
        hazard_threshold=0.75,
    )

    # --- Step 5: Capacity Engine ---
    from app.services.capacity_engine import compute_capacity_for_destination
    accepted = [compute_capacity_for_destination(c) for c in accepted]

    # --- Step 6: Route Safety Engine ---
    from app.services.route_engine import compute_route_for_destination
    for i, c in enumerate(accepted):
        route = get_route_between(engine, village.id, c["id"])
        accepted[i] = compute_route_for_destination(c, route)

    # --- Step 7: Multi-Criteria Optimization ---
    from app.services.optimization_engine import score_destination, rank_destinations

    weights_dict = None
    if body.weights:
        weights_dict = {
            "safety": body.weights.safety,
            "capacity": body.weights.capacity,
            "route": body.weights.route,
            "healthcare": body.weights.healthcare,
            "water": body.weights.water,
            "vulnerability_fit": body.weights.vulnerability_fit,
            "distance": body.weights.distance,
        }

    scored = [
        score_destination(c, vuln_result["vulnerability_score"], weights_dict)
        for c in accepted
    ]
    ranked = rank_destinations(scored)

    # --- Step 8: Population Allocation (priority-group-aware) ---
    from app.services.allocation_engine import allocate_families, compute_affected_families

    affected_families = compute_affected_families(
        village.households,
        body.max_affected_families,
    )
    allocated, unallocated = allocate_families(
        ranked,
        affected_families,
        source_population=village.population,
        source_households=village.households,
        source_elderly_above_65=village.elderly_above_65,
        source_children_under_5=village.children_under_5,
        source_special_assistance=village.special_assistance,
    )

    # --- Step 9: Explainability Engine ---
    from app.services.explainability_engine import (
        build_selected_destination_explanations,
        build_rejected_destination_explanations,
        generate_rule_based_summary,
    )

    # Try Gemini for AI summary, fall back to rule-based
    ai_summary = ""
    if body.include_ai_summary:
        try:
            from app.services.gemini_client import generate_plan_summary_sync
            plan_data = {
                "village_name": village.name,
                "district": village.district,
                "risk_classification": hazard_result["risk_classification"],
                "hazard_score": hazard_result["hazard_score"],
                "vulnerability_score": vuln_result["vulnerability_score"],
                "affected_families": affected_families,
                "total_families_allocated": affected_families - unallocated,
                "unallocated_families": unallocated,
                "ranked_destinations": [
                    {"name": d["name"], "type": d["type"], "rank": d["rank"],
                     "weighted_total": d["weighted_total"], "families_allocated": d["families_allocated"]}
                    for d in allocated if d.get("families_allocated", 0) > 0
                ],
            }
            ai_summary = generate_plan_summary_sync(plan_data) or ""
        except Exception:
            pass  # Graceful degradation

    # Rule-based summary (always generate)
    rule_summary = generate_rule_based_summary(
        source_village={"name": village.name, "district": village.district},
        hazard_score=hazard_result["hazard_score"],
        vulnerability_score=vuln_result["vulnerability_score"],
        risk_classification=hazard_result["risk_classification"],
        allocated_count=sum(1 for d in allocated if d.get("families_allocated", 0) > 0),
        rejected_count=len(rejected_raw),
        total_allocated=affected_families - unallocated,
        unallocated=unallocated,
        affected_families=affected_families,
    )

    # --- Build response ---
    weights_used = OptimizationWeights(**weights_dict) if weights_dict else OptimizationWeights()

    return GeneratePlanResponse(
        village_id=village.id,
        village_name=village.name,
        district=village.district,
        state=village.state,
        latitude=village.latitude,
        longitude=village.longitude,
        population=village.population,
        households=village.households,
        hazard_score=hazard_result["hazard_score"],
        vulnerability_score=vuln_result["vulnerability_score"],
        combined_risk=combined_risk,
        risk_classification=hazard_result["risk_classification"],
        affected_families=affected_families,
        search_radius_km=body.search_radius_km,
        ranked_destinations=[
            DestinationScore(
                destination_id=d["id"],
                destination_name=d["name"],
                destination_type=d["type"],
                district=d.get("district", ""),
                state=d.get("state", ""),
                latitude=d["latitude"],
                longitude=d["longitude"],
                safety_score=d.get("safety_score", 0),
                capacity_score=d.get("capacity_score", 0),
                route_safety_score=d.get("route_safety_score", 0),
                healthcare_score=d.get("healthcare_score", 0),
                water_score=d.get("water_score", 0),
                vulnerability_fit_score=d.get("vulnerability_fit_score", 0),
                distance_score=d.get("distance_score", 0),
                weighted_total=d.get("weighted_total", 0),
                rank=d.get("rank", 0),
                total_capacity=d.get("total_capacity", 0),
                available_capacity=d.get("available_capacity", 0),
                families_allocated=d.get("families_allocated", 0),
                allocation_breakdown=d.get("allocation_breakdown"),
                allocation_reasons=d.get("allocation_reasons"),
                route_id=d.get("route_id"),
                route_distance_km=d.get("route_distance_km", 0),
                route_time_min=d.get("route_time_min", 0),
                route_status=d.get("route_status", "unknown"),
                is_flooded=d.get("is_flooded", False),
                is_landslide_affected=d.get("is_landslide_affected", False),
            )
            for d in allocated
        ],
        rejected_destinations=[
            RejectedDestination(
                destination_id=r["id"],
                destination_name=r["name"],
                latitude=r.get("latitude", 0.0),
                longitude=r.get("longitude", 0.0),
                rejection_reasons=r["rejection_reasons"],
            )
            for r in rejected_raw
        ],
        total_families_allocated=affected_families - unallocated,
        unallocated_families=unallocated,
        summary_text=rule_summary,
        ai_summary=ai_summary,
        weights_used=weights_used,
        created_at=datetime.datetime.utcnow().isoformat(),
    )


def _get_all_villages(engine):
    """Get all villages as list."""
    from app.database import get_all_villages
    return get_all_villages(engine)
