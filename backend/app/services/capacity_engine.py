"""
Capacity Engine — calculate available capacity and capacity scores.

Capacity is critical for multi-destination evacuation:
  - Available capacity = total_capacity - current_occupancy
  - Capacity score = normalized available capacity (0-1)
"""
from typing import Optional


def compute_available_capacity(total_capacity: int, current_occupancy: int) -> int:
    """
    Calculate available capacity.

    Returns:
        int: max(0, total - current)
    """
    return max(0, total_capacity - current_occupancy)


def compute_capacity_score(
    total_capacity: int,
    current_occupancy: int,
    reference_capacity: int = 2000,
) -> float:
    """
    Compute capacity score 0-1.

    Score is proportional to available capacity relative to reference.
    A shelter with 2000 beds available scores 1.0.

    Args:
        total_capacity: maximum beds/places
        current_occupancy: currently occupied
        reference_capacity: normalization reference (default 2000)

    Returns:
        float 0-1
    """
    available = compute_available_capacity(total_capacity, current_occupancy)

    if reference_capacity <= 0:
        return 0.0

    return round(min(available / reference_capacity, 1.0), 4)


def compute_capacity_for_destination(candidate: dict) -> dict:
    """
    Add capacity fields to a candidate dict.

    Returns:
        dict with available_capacity and capacity_score added
    """
    total = candidate.get("total_capacity", 0)
    current = candidate.get("current_occupancy", 0)
    available = compute_available_capacity(total, current)
    score = compute_capacity_score(total, current)

    return {
        **candidate,
        "available_capacity": available,
        "capacity_score": score,
    }
