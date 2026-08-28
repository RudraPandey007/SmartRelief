"""
Filtering engine — hard constraint rejection.

Rejects candidates with hazard above threshold, blocked routes, or zero capacity.
Missing route data (no record) is treated as a data gap, not a blockage.
"""
from typing import List, Tuple


# Default thresholds
DEFAULT_HAZARD_THRESHOLD = 0.75  # Reject if hazard > 0.75


def check_hazard_constraint(
    candidate: dict,
    hazard_score: float,
    threshold: float = DEFAULT_HAZARD_THRESHOLD,
    risk_classification: str = "unknown",
) -> Tuple[bool, str]:
    """
    Reject candidate if hazard score exceeds threshold.

    Args:
        candidate: candidate dict (used for name/id context)
        hazard_score: computed hazard score 0-1
        threshold: max allowed hazard score
        risk_classification: pre-computed classification string (e.g. "extreme")

    Returns:
        (is_rejected, reason_string)
    """
    if hazard_score > threshold:
        return True, (
            f"Hazard score {hazard_score:.2f} exceeds threshold {threshold:.2f} "
            f"(classified as {risk_classification})"
        )
    return False, ""


def check_route_constraint(
    route_status: str,
) -> Tuple[bool, str]:
    """
    Reject candidate if route is explicitly blocked or has no route data.

    Distinguishes two cases:
      - "blocked"  → route record EXISTS and is explicitly marked blocked
      - "no_data"  → no route record at all (data gap, not a hazard)

    Returns:
        (is_rejected, reason_string)
    """
    if route_status == "blocked":
        return True, "Route is blocked — evacuation not possible"
    if route_status == "no_data":
        return True, "No route data available for this destination"
    return False, ""


def check_capacity_constraint(
    available_capacity: int,
) -> Tuple[bool, str]:
    """
    Reject candidate if no capacity available.

    Returns:
        (is_rejected, reason_string)
    """
    if available_capacity <= 0:
        return True, f"No available capacity ({available_capacity} beds)"
    return False, ""


def filter_candidates(
    candidates: list,
    hazard_scores: dict,
    routes: dict,
    hazard_threshold: float = DEFAULT_HAZARD_THRESHOLD,
    hazard_classifications: dict = None,
) -> Tuple[list, list]:
    """
    Apply all hard constraints to filter candidates.

    Args:
        candidates: list of candidate dicts from candidate_engine
        hazard_scores: dict mapping candidate_id -> hazard_score float
        routes: dict mapping candidate_id -> route_status string
                  ("available", "degraded", "blocked", or "no_data")
        hazard_threshold: max allowed hazard score
        hazard_classifications: optional dict mapping candidate_id -> classification string
                                (e.g. "extreme", "high"). Falls back to "unknown" if absent.

    Returns:
        (accepted_candidates, rejected_candidates)
        rejected_candidates has additional 'rejection_reasons' field
    """
    if hazard_classifications is None:
        hazard_classifications = {}

    accepted = []
    rejected = []

    for c in candidates:
        c_id = c["id"]
        reasons = []

        # Hazard constraint
        h_score = hazard_scores.get(c_id, 0.0)
        classification = hazard_classifications.get(c_id, "unknown")
        is_rejected, reason = check_hazard_constraint(
            c, h_score, hazard_threshold, risk_classification=classification
        )
        if is_rejected:
            reasons.append(reason)

        # Route constraint
        route_status = routes.get(c_id, "available")
        is_rejected, reason = check_route_constraint(route_status)
        if is_rejected:
            reasons.append(reason)

        # Capacity constraint
        avail_cap = c.get("total_capacity", 0) - c.get("current_occupancy", 0)
        is_rejected, reason = check_capacity_constraint(avail_cap)
        if is_rejected:
            reasons.append(reason)

        if reasons:
            rejected.append({
                "id": c_id,
                "name": c["name"],
                "type": c["type"],
                "latitude": c.get("latitude", 0.0),
                "longitude": c.get("longitude", 0.0),
                "rejection_reasons": reasons,
            })
        else:
            accepted.append(c)

    return accepted, rejected
