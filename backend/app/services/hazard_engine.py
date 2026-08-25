"""
Hazard Risk Engine — transparent weighted formula for flood + landslide risk.

Score 0.0 (safe) → 1.0 (extreme risk).

Factors (MVP weights, configurable):
  - River flood risk:        40%  (from seed data)
  - Rainfall intensity:      25%  (weather API or seed avg_rainfall_mm)
  - River proximity:         15%  (inverse of distance)
  - Historical frequency:    10%  (normalized count)
  - Landslide risk:          10%  (from seed data)
"""
from typing import Optional


# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "river_flood_risk": 0.40,
    "rainfall": 0.25,
    "river_proximity": 0.15,
    "historical_frequency": 0.10,
    "landslide_risk": 0.10,
}

# Classification thresholds
RISK_THRESHOLDS = {
    "extreme": 0.75,
    "high": 0.55,
    "medium": 0.35,
    "low": 0.0,
}


def _normalize_rainfall(rainfall_mm: float, max_rainfall: float = 250.0) -> float:
    """Normalize rainfall to 0-1 scale. 250mm is extreme monsoon rainfall."""
    return min(rainfall_mm / max_rainfall, 1.0)


def _normalize_river_proximity(distance_km: float, max_distance: float = 15.0) -> float:
    """
    Inverse proximity — closer to river = higher risk.
    0km → 1.0, 15km+ → ~0.0
    """
    return max(0.0, 1.0 - (distance_km / max_distance))


def _normalize_historical_frequency(count: int, max_count: int = 10) -> float:
    """Normalize historical flood count to 0-1 scale."""
    return min(count / max_count, 1.0)


def compute_hazard_score(
    river_flood_risk: float,
    avg_rainfall_mm: float,
    river_distance_km: float,
    historical_flood_frequency: int,
    landslide_risk: float,
    live_rainfall_mm: Optional[float] = None,
    weights: Optional[dict] = None,
) -> float:
    """
    Compute composite hazard score for a village.

    Args:
        river_flood_risk: 0-1 flood risk from seed data
        avg_rainfall_mm: average rainfall in mm
        river_distance_km: distance to nearest river in km
        historical_flood_frequency: count of past floods
        landslide_risk: 0-1 landslide risk from seed data
        live_rainfall_mm: optional live rainfall from weather API (overrides seed)
        weights: optional custom weights dict

    Returns:
        float 0.0 (safe) to 1.0 (extreme risk)
    """
    w = weights or DEFAULT_WEIGHTS

    # Use live rainfall if available, else seed average
    rainfall_value = live_rainfall_mm if live_rainfall_mm is not None else avg_rainfall_mm

    # Normalize each factor to 0-1
    f_river = max(0.0, min(river_flood_risk, 1.0))
    f_rainfall = _normalize_rainfall(rainfall_value)
    f_proximity = _normalize_river_proximity(river_distance_km)
    f_historical = _normalize_historical_frequency(historical_flood_frequency)
    f_landslide = max(0.0, min(landslide_risk, 1.0))

    # Weighted sum
    score = (
        w["river_flood_risk"] * f_river
        + w["rainfall"] * f_rainfall
        + w["river_proximity"] * f_proximity
        + w["historical_frequency"] * f_historical
        + w["landslide_risk"] * f_landslide
    )

    return round(min(max(score, 0.0), 1.0), 4)


def classify_risk(score: float) -> str:
    """Classify a hazard score into extreme/high/medium/low."""
    for level in ["extreme", "high", "medium"]:
        if score >= RISK_THRESHOLDS[level]:
            return level
    return "low"


def compute_hazard_for_village(village, live_rainfall_mm: Optional[float] = None) -> dict:
    """
    Convenience wrapper: compute hazard score for a Village DB model.

    Returns dict with score and classification.
    """
    score = compute_hazard_score(
        river_flood_risk=village.river_flood_risk,
        avg_rainfall_mm=village.avg_rainfall_mm,
        river_distance_km=village.river_distance_km,
        historical_flood_frequency=village.historical_flood_frequency,
        landslide_risk=village.landslide_risk,
        live_rainfall_mm=live_rainfall_mm,
    )
    return {
        "hazard_score": score,
        "risk_classification": classify_risk(score),
    }
