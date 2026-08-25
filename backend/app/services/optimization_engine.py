"""
Optimization Engine — weighted multi-criteria scoring and ranking.

Default weights (from spec doc):
  - Safety:            25%
  - Capacity:          20%
  - Route Safety:      15%
  - Healthcare:        15%
  - Water Supply:      10%
  - Vulnerability Fit: 10%
  - Distance:           5%
"""
from typing import List, Optional, Dict, Any


# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "safety": 0.25,
    "capacity": 0.20,
    "route": 0.15,
    "healthcare": 0.15,
    "water": 0.10,
    "vulnerability_fit": 0.10,
    "distance": 0.05,
}


def compute_healthcare_score(has_healthcare: bool) -> float:
    """Binary: 1.0 if healthcare available, 0.3 if not (penalized but not zero)."""
    return 1.0 if has_healthcare else 0.3


def compute_water_score(has_water_supply: bool) -> float:
    """Binary: 1.0 if water supply available, 0.2 if not."""
    return 1.0 if has_water_supply else 0.2


def compute_vulnerability_fit_score(
    dest_healthcare: bool,
    dest_water: bool,
    source_vulnerability_score: float,
) -> float:
    """
    How well does this destination match the source's vulnerability needs?

    High vulnerability source → destination with healthcare/water scores higher.
    """
    base = 0.5  # default fit

    # Boost if destination has facilities vulnerable population needs
    if dest_healthcare:
        base += 0.25
    if dest_water:
        base += 0.25

    # Scale by source vulnerability (more vulnerable = need better facilities)
    fit = base * (0.5 + source_vulnerability_score * 0.5)

    return round(min(max(fit, 0.0), 1.0), 4)


def compute_distance_score(distance_km: float, max_distance_km: float = 120.0) -> float:
    """
    Closer = better. 0km → 1.0, max_distance → ~0.1 (not zero, to keep in running).
    """
    if max_distance_km <= 0:
        return 0.0
    score = 1.0 - (distance_km / max_distance_km)
    return round(min(max(score, 0.0), 1.0), 4)


def score_destination(
    candidate: dict,
    source_vulnerability_score: float = 0.5,
    weights: Optional[Dict[str, float]] = None,
) -> dict:
    """
    Compute weighted multi-criteria score for a single candidate.

    Expects candidate dict with fields from previous engines:
      - river_flood_risk, has_healthcare, has_water_supply, distance_km
      - route_safety_score, available_capacity, total_capacity

    Returns:
        dict with individual scores + weighted_total
    """
    w = weights or DEFAULT_WEIGHTS

    # Individual scores
    safety_score = 1.0 - candidate.get("river_flood_risk", 0.5)  # invert: low risk = high safety
    capacity_score = candidate.get("capacity_score", 0.5)
    route_score = candidate.get("route_safety_score", 0.5)
    healthcare_score = compute_healthcare_score(candidate.get("has_healthcare", False))
    water_score = compute_water_score(candidate.get("has_water_supply", False))
    vuln_fit_score = compute_vulnerability_fit_score(
        candidate.get("has_healthcare", False),
        candidate.get("has_water_supply", False),
        source_vulnerability_score,
    )
    dist_score = compute_distance_score(candidate.get("distance_km", 100.0))

    # Weighted total
    weighted_total = (
        w["safety"] * safety_score
        + w["capacity"] * capacity_score
        + w["route"] * route_score
        + w["healthcare"] * healthcare_score
        + w["water"] * water_score
        + w["vulnerability_fit"] * vuln_fit_score
        + w["distance"] * dist_score
    )

    return {
        **candidate,
        "safety_score": round(safety_score, 4),
        "capacity_score": round(capacity_score, 4),
        "route_safety_score": round(route_score, 4),
        "healthcare_score": round(healthcare_score, 4),
        "water_score": round(water_score, 4),
        "vulnerability_fit_score": round(vuln_fit_score, 4),
        "distance_score": round(dist_score, 4),
        "weighted_total": round(weighted_total, 4),
    }


def rank_destinations(
    scored_candidates: List[dict],
) -> List[dict]:
    """
    Sort candidates by weighted_total descending and assign ranks.

    Returns:
        List of candidates with 'rank' field added, sorted best → worst.
    """
    # Sort by weighted_total descending
    ranked = sorted(scored_candidates, key=lambda x: x.get("weighted_total", 0), reverse=True)

    # Assign ranks
    for i, c in enumerate(ranked, start=1):
        c["rank"] = i

    return ranked
