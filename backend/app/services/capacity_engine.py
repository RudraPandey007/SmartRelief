"""Capacity scoring for destination candidates."""
from typing import Optional


def compute_available_capacity(total_capacity: int, current_occupancy: int) -> int:
    return max(0, total_capacity - current_occupancy)


def compute_capacity_score(
    total_capacity: int,
    current_occupancy: int,
    reference_capacity: int = 2000,
) -> float:
    """Capacity score 0-1, proportional to available capacity vs reference (default 2000)."""
    available = compute_available_capacity(total_capacity, current_occupancy)

    if reference_capacity <= 0:
        return 0.0

    return round(min(available / reference_capacity, 1.0), 4)


def compute_capacity_for_destination(candidate: dict) -> dict:
    """Add available_capacity and capacity_score to a candidate dict."""
    total = candidate.get("total_capacity", 0)
    current = candidate.get("current_occupancy", 0)
    available = compute_available_capacity(total, current)
    score = compute_capacity_score(total, current)

    return {
        **candidate,
        "available_capacity": available,
        "capacity_score": score,
    }
