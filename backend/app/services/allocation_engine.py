"""
Allocation Engine — priority-group-aware greedy allocation.

Allocates affected families to destinations using three priority tiers:

  Priority Group 1 (elderly + special assistance):
    Allocated FIRST to the feasible destination with the best healthcare_score.
    If that destination lacks capacity for the full group, split across the
    top-N healthcare destinations rather than spilling into low-healthcare ones.

  Priority Group 2 (children / families with young children):
    Allocated NEXT to the best remaining balance of healthcare + capacity.

  Priority Group 3 (remaining general population):
    Allocated LAST, filling remaining capacity by overall weighted_total rank
    (same as the original bin-packing behaviour).

ASSUMPTIONS (MVP):
  - Population breakdown per village is used to estimate proportional family
    counts per priority group via household-to-population ratios.  These are
    approximations: we assume each household's demographic profile mirrors the
    village average.  A more precise model would use actual household surveys.
  - "Families with elderly/special-needs" ≈ (elderly_above_65 + special_assistance)
    divided by (population / households), rounded to the nearest integer.
  - Children group ≈ children_under_5 scaled the same way.
"""

from typing import List, Tuple, Dict, Optional, Any
import math




def compute_priority_group_families(
    population: int,
    households: int,
    elderly_above_65: int,
    children_under_5: int,
    special_assistance: int,
) -> Dict[str, int]:
    """
    Estimate the number of families in each priority group using
    proportional household-to-population ratios.

    The groups are:
      priority_elderly_special_needs  — households with elderly or special-needs members
      priority_children              — households with children under 5
      general_population             — everything else

    ASSUMPTION: Each demographic characteristic is independently distributed
    across households, so we scale by (count / population) * households.
    This may double-count households that contain both elderly AND children;
    for MVP we accept this approximation — the total of all three groups is
    clamped to the total household count to prevent overflow.
    """
    if population <= 0 or households <= 0:
        return {
            "priority_elderly_special_needs": 0,
            "priority_children": 0,
            "general_population": households,
        }

    # Scale: (count / population) * households → estimated families
    elderly_special_families = round(
        ((elderly_above_65 + special_assistance) / population) * households
    )
    children_families = round(
        (children_under_5 / population) * households
    )

    # Clamp so the two priority groups never exceed total households
    total_priority = elderly_special_families + children_families
    if total_priority > households:
        # Proportionally reduce both groups
        scale = households / total_priority
        elderly_special_families = round(elderly_special_families * scale)
        children_families = households - elderly_special_families  # remainder goes to children

    general_families = max(0, households - elderly_special_families - children_families)

    return {
        "priority_elderly_special_needs": elderly_special_families,
        "priority_children": children_families,
        "general_population": general_families,
    }




def allocate_families(
    ranked_destinations: List[dict],
    affected_families: int,
    source_population: int = 0,
    source_households: int = 0,
    source_elderly_above_65: int = 0,
    source_children_under_5: int = 0,
    source_special_assistance: int = 0,
) -> Tuple[List[dict], int]:
    """
    Priority-group-aware allocation of affected families to ranked destinations.

    Args:
        ranked_destinations: list of destination dicts sorted by rank (best first).
            Each must have 'available_capacity', 'id', 'healthcare_score',
            and 'weighted_total' fields.
        affected_families: total families needing relocation.
        source_population: total population of the source village.
        source_households: total households in the source village.
        source_elderly_above_65: elderly count in source village.
        source_children_under_5: children count in source village.
        source_special_assistance: special-assistance count in source village.

    Returns:
        (allocated_destinations, unallocated_families)
        Each destination gets 'families_allocated', 'allocation_breakdown',
        and 'allocation_reasons' added.
    """


    groups = compute_priority_group_families(
        population=source_population or affected_families,  # fallback: treat 1 family = 1 person
        households=affected_families,
        elderly_above_65=source_elderly_above_65,
        children_under_5=source_children_under_5,
        special_assistance=source_special_assistance,
    )

    elderly_special_count = groups["priority_elderly_special_needs"]
    children_count = groups["priority_children"]
    general_count = groups["general_population"]

    # Mutable capacity tracking
    # We keep a copy of available_capacity per destination so we can deduct
    # during successive priority passes without mutating the originals until
    # the end.
    dest_caps = {d["id"]: d.get("available_capacity", 0) for d in ranked_destinations}

    # Track allocations per destination per group
    alloc: Dict[str, Dict[str, int]] = {
        d["id"]: {
            "priority_elderly_special_needs": 0,
            "priority_children": 0,
            "general_population": 0,
        }
        for d in ranked_destinations
    }

    # Track per-destination explanation reasons
    alloc_reasons: Dict[str, List[str]] = {d["id"]: [] for d in ranked_destinations}

    # Helper: find feasible destinations sorted by a custom key
    def _ranked_by_key(key_fn):
        """Return destination IDs sorted by key_fn(dest) descending, with capacity > 0."""
        return [
            d["id"] for d in ranked_destinations
            if dest_caps.get(d["id"], 0) > 0
        ]
        # We'll sort in-line for each pass

    # Priority Group 1: elderly + special assistance → best healthcare
    _allocate_priority_group(
        dests=ranked_destinations,
        dest_caps=dest_caps,
        alloc=alloc,
        alloc_reasons=alloc_reasons,
        group_name="priority_elderly_special_needs",
        group_label="elderly/special-needs",
        count=elderly_special_count,
        # Sort by healthcare_score descending (tie-break by weighted_total)
        sort_key=lambda d: (
            d.get("healthcare_score", 0),
            d.get("weighted_total", 0),
        ),
    )

    # Priority Group 2: children → best healthcare + capacity
    # NOTE: We use remaining capacity (dest_caps) rather than the pre-computed
    # capacity_score so that destinations whose capacity was consumed by Group 1
    # are appropriately deprioritised for children allocation.
    _allocate_priority_group(
        dests=ranked_destinations,
        dest_caps=dest_caps,
        alloc=alloc,
        alloc_reasons=alloc_reasons,
        group_name="priority_children",
        group_label="children/families with young children",
        count=children_count,
        sort_key=lambda d: (
            d.get("healthcare_score", 0) * 0.6
            + min(dest_caps.get(d["id"], 0) / max(d.get("total_capacity", 1), 1), 1.0) * 0.4
            + d.get("weighted_total", 0) * 0.1,  # small tie-break
        ),
    )

    # Priority Group 3: general population → by rank
    _allocate_priority_group(
        dests=ranked_destinations,
        dest_caps=dest_caps,
        alloc=alloc,
        alloc_reasons=alloc_reasons,
        group_name="general_population",
        group_label="general population",
        count=general_count,
        # Sort by weighted_total descending (same as original behaviour)
        sort_key=lambda d: (
            d.get("weighted_total", 0),
            d.get("rank", 999),  # lower rank = better
        ),
    )

    # Assemble results
    remaining = affected_families
    for d in ranked_destinations:
        did = d["id"]
        bd = alloc[did]
        total = (
            bd["priority_elderly_special_needs"]
            + bd["priority_children"]
            + bd["general_population"]
        )
        d["families_allocated"] = total
        d["allocation_breakdown"] = bd
        d["allocation_reasons"] = alloc_reasons[did]
        remaining -= total

    return ranked_destinations, max(0, remaining)




def _allocate_priority_group(
    dests: List[dict],
    dest_caps: Dict[str, int],
    alloc: Dict[str, Dict[str, int]],
    alloc_reasons: Dict[str, List[str]],
    group_name: str,
    group_label: str,
    count: int,
    sort_key,
) -> None:
    """
    Allocate `count` families from a priority group across destinations
    sorted by `sort_key` descending.

    For priority group 1 (elderly/special-needs), if the top healthcare
    destination can't fit the entire group, we split across the top-N
    healthcare destinations rather than spilling into a low-healthcare one.
    """
    if count <= 0:
        return

    remaining = count

    # Sort feasible destinations by the custom key (descending)
    feasible_ids = sorted(
        [d["id"] for d in dests],
        key=lambda did: sort_key(next(d for d in dests if d["id"] == did)),
        reverse=True,
    )

    for did in feasible_ids:
        if remaining <= 0:
            break
        available = dest_caps.get(did, 0)
        if available <= 0:
            continue

        alloc_here = min(remaining, available)
        alloc[did][group_name] += alloc_here
        dest_caps[did] -= alloc_here
        remaining -= alloc_here

        # Add explainability reason
        dest_obj = next(d for d in dests if d["id"] == did)
        hs = dest_obj.get("healthcare_score", 0)
        if group_name == "priority_elderly_special_needs":
            alloc_reasons[did].append(
                f"Prioritized for {group_label} allocation due to "
                f"healthcare_score of {hs:.2f}"
            )
        elif group_name == "priority_children":
            alloc_reasons[did].append(
                f"Prioritized for {group_label} allocation due to "
                f"healthcare_score of {hs:.2f} "
                f"(healthcare-weighted selection)"
            )
        else:
            alloc_reasons[did].append(
                f"General population allocated by overall weighted_total rank "
                f"(score: {dest_obj.get('weighted_total', 0):.2f})"
            )

    # If there is still remaining after all destinations are exhausted, those
    # families are unallocated — the caller will see them in the return value.
    # We intentionally do NOT spill into low-ranking destinations here to
    # preserve the priority-group semantics.




def compute_affected_families(
    households: int,
    max_affected: int = None,
) -> int:
    """
    Determine how many families are affected.

    For MVP: all households in source village are affected.
    Optional cap via max_affected parameter.
    """
    if max_affected is not None and max_affected > 0:
        return min(households, max_affected)
    return households




def get_allocation_summary(allocated_destinations: List[dict]) -> dict:
    """
    Summarize allocation results including per-group totals.
    """
    total_allocated = sum(d.get("families_allocated", 0) for d in allocated_destinations)
    destinations_used = sum(
        1 for d in allocated_destinations if d.get("families_allocated", 0) > 0
    )

    # Aggregate group totals across all destinations
    group_totals = {
        "priority_elderly_special_needs": 0,
        "priority_children": 0,
        "general_population": 0,
    }
    for d in allocated_destinations:
        bd = d.get("allocation_breakdown", {})
        for key in group_totals:
            group_totals[key] += bd.get(key, 0)

    return {
        "total_families_allocated": total_allocated,
        "destinations_used": destinations_used,
        "destinations_with_capacity_left": sum(
            1 for d in allocated_destinations
            if d.get("families_allocated", 0) == 0
            and d.get("available_capacity", 0) > 0
        ),
        "allocation_by_group": group_totals,
    }
