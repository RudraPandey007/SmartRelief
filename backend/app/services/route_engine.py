"""
Route Safety Engine — compute route safety scores from seeded data.

For MVP, routes have pre-computed safety scores in seed data.
This engine looks up routes and computes composite route quality.
"""
from typing import Optional


# Weight factors for composite route quality
DEFAULT_WEIGHTS = {
    "safety_score": 0.50,
    "flood_penalty": 0.25,
    "landslide_penalty": 0.15,
    "road_type_bonus": 0.10,
}

# Road type quality bonuses
ROAD_TYPE_BONUS = {
    "national_highway": 0.10,
    "state_highway": 0.08,
    "district_road": 0.05,
    "ferry_road": 0.02,
}


def compute_route_score(
    safety_score: float,
    is_flooded: bool,
    is_landslide_affected: bool,
    road_type: str = "district_road",
    weights: Optional[dict] = None,
) -> float:
    """
    Compute composite route quality score 0-1.

    Args:
        safety_score: base safety score from seed data (0-1)
        is_flooded: whether route is currently flooded
        is_landslide_affected: whether route has landslide
        road_type: type of road (national_highway, state_highway, etc.)
        weights: optional custom weights

    Returns:
        float 0-1 (higher = better route)
    """
    w = weights or DEFAULT_WEIGHTS

    # Base safety (already 0-1)
    f_safety = max(0.0, min(safety_score, 1.0))

    # Flood penalty: flooded = 0.3, not flooded = 1.0
    f_flood = 0.3 if is_flooded else 1.0

    # Landslide penalty: affected = 0.4, not affected = 1.0
    f_landslide = 0.4 if is_landslide_affected else 1.0

    # Road type bonus
    f_road = ROAD_TYPE_BONUS.get(road_type, 0.05)

    # Weighted composite
    score = (
        w["safety_score"] * f_safety
        + w["flood_penalty"] * f_flood
        + w["landslide_penalty"] * f_landslide
        + w["road_type_bonus"] * f_road
    )

    return round(min(max(score, 0.0), 1.0), 4)


def compute_route_for_destination(candidate: dict, route) -> dict:
    """
    Look up route for a candidate and compute route score.

    Args:
        candidate: candidate destination dict
        route: Route DB model (or None if no route)

    Returns:
        dict with route fields added
    """
    if route is None:
        return {
            **candidate,
            "route_id": None,
            "route_distance_km": 0.0,
            "route_time_min": 0.0,
            "route_status": "unknown",
            "is_flooded": False,
            "is_landslide_affected": False,
            "route_safety_score": 0.0,
        }

    score = compute_route_score(
        safety_score=route.safety_score,
        is_flooded=route.is_flooded,
        is_landslide_affected=route.is_landslide_affected,
        road_type=route.road_type,
    )

    return {
        **candidate,
        "route_id": route.id,
        "route_distance_km": route.distance_km,
        "route_time_min": route.estimated_time_min,
        "route_status": route.route_status,
        "is_flooded": route.is_flooded,
        "is_landslide_affected": route.is_landslide_affected,
        "route_safety_score": score,
    }
