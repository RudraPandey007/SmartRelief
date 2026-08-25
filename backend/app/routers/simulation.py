"""
Simulation Router — what-if simulation endpoint.

Endpoints:
  POST /simulation/run  — re-runs pipeline with modified parameters
"""
import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from slowapi import Limiter

from app.config import get_settings
from app.database import get_engine, get_village_by_id, get_all_shelters, get_all_routes, get_route_between
from app.security import require_api_key, limiter
from app.models.schemas import (
    SimulationRequest,
    SimulationResponse,
    GeneratePlanResponse,
    OptimizationWeights,
    DestinationScore,
    RejectedDestination,
    ErrorResponse,
)

router = APIRouter(
    prefix="/simulation",
    tags=["simulation"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/run", response_model=SimulationResponse)
@limiter.limit("10/minute")
async def run_simulation(
    request: Request,
    body: SimulationRequest,
):
    """
    Run a what-if simulation by applying overrides to seed data.

    Overrides:
      - rainfall_multiplier: scales rainfall for all villages
      - occupancy_percent: scales shelter occupancy
      - road_accessibility_percent: scales road safety scores
    """
    settings = get_settings()
    engine = get_engine(settings.DATABASE_URL)

    # Validate source village
    village = get_village_by_id(engine, body.village_id)
    if not village:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Village {body.village_id} not found"},
        )

    # --- Generate BEFORE plan (no overrides) ---
    before = await _generate_plan_internal(engine, village, body, overrides_applied=False)

    # --- Generate AFTER plan (with overrides) ---
    after = await _generate_plan_internal(engine, village, body, overrides_applied=True, overrides=body.overrides)

    # --- Compute changes summary ---
    changes = {
        "rainfall_change": f"{body.overrides.rainfall_multiplier}x",
        "occupancy_change": f"{body.overrides.occupancy_percent * 100:.0f}%",
        "road_accessibility_change": f"{body.overrides.road_accessibility_percent * 100:.0f}%",
        "risk_change": round(after.combined_risk - before.combined_risk, 4),
        "allocation_change": after.total_families_allocated - before.total_families_allocated,
        "destinations_changed": len(after.ranked_destinations) != len(before.ranked_destinations),
    }

    return SimulationResponse(
        before=before,
        after=after,
        changes_summary=changes,
    )


async def _generate_plan_internal(
    engine,
    village,
    body,
    overrides_applied: bool = False,
    overrides=None,
):
    """Internal plan generation with optional overrides."""
    # --- Step 1: Hazard Risk Engine ---
    from app.services.hazard_engine import compute_hazard_for_village, compute_hazard_score

    hazard_result = compute_hazard_for_village(village)

    # Apply rainfall override if enabled
    live_rainfall = None
    if overrides_applied and overrides:
        live_rainfall = village.avg_rainfall_mm * overrides.rainfall_multiplier
        # Recompute hazard with modified rainfall
        from app.services.hazard_engine import classify_risk
        new_score = compute_hazard_score(
            river_flood_risk=village.river_flood_risk,
            avg_rainfall_mm=village.avg_rainfall_mm,
            river_distance_km=village.river_distance_km,
            historical_flood_frequency=village.historical_flood_frequency,
            landslide_risk=village.landslide_risk,
            live_rainfall_mm=live_rainfall,
        )
        hazard_result = {
            "hazard_score": new_score,
            "risk_classification": classify_risk(new_score),
        }

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

    all_villages = get_all_villages_list(engine)
    all_shelters = get_all_shelters_list(engine)

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

    hazard_scores = {}
    for c in candidates:
        if c["type"] == "village":
            for v in all_villages:
                if v.id == c["id"]:
                    h = compute_hazard_for_village(v)
                    hazard_scores[c["id"]] = h["hazard_score"]
                    break
        else:
            hazard_scores[c["id"]] = 0.1

    route_statuses = {}
    for c in candidates:
        route = get_route_between(engine, village.id, c["id"])
        if route:
            route_statuses[c["id"]] = route.route_status
        else:
            route_statuses[c["id"]] = "blocked"

    accepted, rejected_raw = filter_candidates(candidates, hazard_scores, route_statuses)

    # --- Step 5: Capacity Engine ---
    from app.services.capacity_engine import compute_capacity_for_destination
    accepted = [compute_capacity_for_destination(c) for c in accepted]

    # Apply occupancy override if enabled
    if overrides_applied and overrides:
        for c in accepted:
            c["current_occupancy"] = int(c["total_capacity"] * overrides.occupancy_percent)
            c["available_capacity"] = c["total_capacity"] - c["current_occupancy"]
            c["capacity_score"] = min(c["available_capacity"] / 2000, 1.0)

    # --- Step 6: Route Safety Engine ---
    from app.services.route_engine import compute_route_for_destination, compute_route_score

    for i, c in enumerate(accepted):
        route = get_route_between(engine, village.id, c["id"])
        if route and overrides_applied and overrides:
            # Apply road accessibility override
            adjusted_safety = route.safety_score * overrides.road_accessibility_percent
            c["route_safety_score"] = compute_route_score(
                safety_score=adjusted_safety,
                is_flooded=route.is_flooded,
                is_landslide_affected=route.is_landslide_affected,
                road_type=route.road_type,
            )
            c["route_id"] = route.id
            c["route_distance_km"] = route.distance_km
            c["route_time_min"] = route.estimated_time_min
            c["route_status"] = route.route_status
            c["is_flooded"] = route.is_flooded
            c["is_landslide_affected"] = route.is_landslide_affected
        else:
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

    # --- Step 8: Population Allocation ---
    from app.services.allocation_engine import allocate_families, compute_affected_families

    affected_families = compute_affected_families(village.households)
    allocated, unallocated = allocate_families(ranked, affected_families)

    # --- Step 9: Explainability ---
    from app.services.explainability_engine import generate_rule_based_summary

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
                rejection_reasons=r["rejection_reasons"],
            )
            for r in rejected_raw
        ],
        total_families_allocated=affected_families - unallocated,
        unallocated_families=unallocated,
        summary_text=rule_summary,
        ai_summary="",
        weights_used=weights_used,
        created_at=datetime.datetime.utcnow().isoformat(),
    )


def get_all_villages_list(engine):
    """Get all villages as list."""
    from app.database import get_all_villages
    return get_all_villages(engine)


def get_all_shelters_list(engine):
    """Get all shelters as list."""
    from app.database import get_all_shelters
    return get_all_shelters(engine)
