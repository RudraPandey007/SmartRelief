"""
Allocation Engine — greedy bin-packing across ranked destinations.

Allocates affected families to destinations in rank order:
  1. Start with best-ranked destination
  2. Fill it to capacity
  3. Move to next destination
  4. Continue until all families allocated or no capacity left
"""
from typing import List, Tuple


def allocate_families(
    ranked_destinations: List[dict],
    affected_families: int,
) -> Tuple[List[dict], int]:
    """
    Greedy allocation: fill destinations in rank order.

    Args:
        ranked_destinations: list of destination dicts, sorted by rank (best first)
            Each must have 'available_capacity' and 'id' fields.
        affected_families: total families needing relocation

    Returns:
        (allocated_destinations, unallocated_families)
        Each destination in the list gets 'families_allocated' added.
    """
    remaining = affected_families
    allocated = []

    for dest in ranked_destinations:
        if remaining <= 0:
            # No more families to allocate
            dest["families_allocated"] = 0
            allocated.append(dest)
            continue

        available = dest.get("available_capacity", 0)
        families_for_this = min(remaining, available)

        dest["families_allocated"] = families_for_this
        remaining -= families_for_this
        allocated.append(dest)

    return allocated, remaining


def compute_affected_families(
    households: int,
    max_affected: int = None,
) -> int:
    """
    Determine how many families are affected.

    For MVP: all households in source village are affected.
    Optional cap via max_affected parameter.

    Args:
        households: total households in source village
        max_affected: optional cap on affected families

    Returns:
        int: number of families to allocate
    """
    if max_affected is not None and max_affected > 0:
        return min(households, max_affected)
    return households


def get_allocation_summary(allocated_destinations: List[dict]) -> dict:
    """
    Summarize allocation results.

    Returns dict with totals and per-destination breakdown.
    """
    total_allocated = sum(d.get("families_allocated", 0) for d in allocated_destinations)
    destinations_used = sum(1 for d in allocated_destinations if d.get("families_allocated", 0) > 0)

    return {
        "total_families_allocated": total_allocated,
        "destinations_used": destinations_used,
        "destinations_with_capacity_left": sum(
            1 for d in allocated_destinations
            if d.get("families_allocated", 0) == 0
            and d.get("available_capacity", 0) > 0
        ),
    }
