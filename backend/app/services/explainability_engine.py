"""Explainability engine — structured reason lists and plan summaries."""
from typing import List, Dict, Any, Optional


def _build_destination_reasons(dest: dict) -> List[str]:
    """Build human-readable reasons for why a destination scored as it did."""
    reasons = []

    # Safety
    safety = dest.get("safety_score", 0.5)
    if safety >= 0.7:
        reasons.append(f"✅ Good safety (score: {safety:.2f}) — low hazard destination")
    elif safety >= 0.4:
        reasons.append(f"⚠️ Moderate safety (score: {safety:.2f}) — some risk present")
    else:
        reasons.append(f"❌ Poor safety (score: {safety:.2f}) — significant hazard risk")

    # Capacity
    cap = dest.get("available_capacity", 0)
    total = dest.get("total_capacity", 0)
    cap_score = dest.get("capacity_score", 0.5)
    if cap_score >= 0.6:
        reasons.append(f"✅ High capacity ({cap}/{total} beds available)")
    elif cap_score >= 0.3:
        reasons.append(f"⚠️ Moderate capacity ({cap}/{total} beds available)")
    else:
        reasons.append(f"❌ Low capacity ({cap}/{total} beds available)")

    # Route
    route_score = dest.get("route_safety_score", 0.5)
    route_status = dest.get("route_status", "unknown")
    if route_status == "blocked":
        reasons.append(f"❌ Route blocked")
    elif route_status == "degraded":
        reasons.append(f"⚠️ Route degraded (safety: {route_score:.2f})")
    elif route_score >= 0.7:
        reasons.append(f"✅ Good route (safety: {route_score:.2f}, {dest.get('route_distance_km', 0):.0f}km)")
    else:
        reasons.append(f"⚠️ Moderate route (safety: {route_score:.2f})")

    # Healthcare
    if dest.get("has_healthcare", False):
        reasons.append("✅ Healthcare available at destination")
    else:
        reasons.append("⚠️ No healthcare at destination — may need mobile medical unit")

    # Water
    if dest.get("has_water_supply", False):
        reasons.append("✅ Water supply available")
    else:
        reasons.append("⚠️ No water supply — temporary arrangements needed")

    # Distance
    dist = dest.get("distance_km", 0)
    if dist <= 20:
        reasons.append(f"✅ Very close ({dist:.1f}km) — quick evacuation")
    elif dist <= 60:
        reasons.append(f"✅ Reasonable distance ({dist:.1f}km)")
    elif dist <= 100:
        reasons.append(f"⚠️ Far ({dist:.1f}km) — longer evacuation time")
    else:
        reasons.append(f"❌ Very far ({dist:.1f}km) — transport challenges")

    # Vulnerability fit
    vuln_fit = dest.get("vulnerability_fit_score", 0.5)
    if vuln_fit >= 0.7:
        reasons.append(f"✅ Good fit for vulnerable population (score: {vuln_fit:.2f})")
    elif vuln_fit >= 0.4:
        reasons.append(f"⚠️ Moderate fit for vulnerable population (score: {vuln_fit:.2f})")
    else:
        reasons.append(f"❌ Poor fit for vulnerable population (score: {vuln_fit:.2f})")

    return reasons


def build_selected_destination_explanations(
    allocated_destinations: List[dict],
) -> List[Dict[str, Any]]:
    """Build explanation dicts for allocated (selected) destinations."""
    explanations = []

    for dest in allocated_destinations:
        families = dest.get("families_allocated", 0)
        if families == 0:
            continue  # Skip unallocated destinations

        reasons = _build_destination_reasons(dest)
        reasons.insert(0, f"📍 Allocated {families} families (weighted score: {dest.get('weighted_total', 0):.2f})")

        # Append priority-group allocation reasons from the allocator
        alloc_reasons = dest.get("allocation_reasons", [])
        for ar in alloc_reasons:
            reasons.append(f"🎯 {ar}")

        explanations.append({
            "destination_id": dest.get("id", ""),
            "destination_name": dest.get("name", ""),
            "destination_type": dest.get("type", "village"),
            "rank": dest.get("rank", 0),
            "families_allocated": families,
            "allocation_breakdown": dest.get("allocation_breakdown"),
            "weighted_total": dest.get("weighted_total", 0),
            "reasons": reasons,
        })

    return explanations


def build_rejected_destination_explanations(
    rejected_destinations: List[dict],
) -> List[Dict[str, Any]]:
    """Build explanation dicts for rejected destinations."""
    explanations = []

    for dest in rejected_destinations:
        reasons = []
        for reason in dest.get("rejection_reasons", []):
            reasons.append(f"❌ {reason}")

        explanations.append({
            "destination_id": dest.get("id", ""),
            "destination_name": dest.get("name", ""),
            "destination_type": dest.get("type", "village"),
            "rejection_reasons": reasons,
        })

    return explanations


def generate_rule_based_summary(
    source_village: dict,
    hazard_score: float,
    vulnerability_score: float,
    risk_classification: str,
    allocated_count: int,
    rejected_count: int,
    total_allocated: int,
    unallocated: int,
    affected_families: int,
) -> str:
    """
    Generate a rule-based text summary of the evacuation plan.

    This is the fallback when Gemini is unavailable.
    """
    village_name = source_village.get("name", "the village")
    district = source_village.get("district", "unknown district")

    summary_parts = [
        f"EVACUATION PLAN SUMMARY",
        f"",
        f"Source: {village_name}, {district}",
        f"Risk Level: {risk_classification.upper()} (hazard: {hazard_score:.2f}, vulnerability: {vulnerability_score:.2f})",
        f"",
        f"Affected Population: {affected_families} families",
        f"",
        f"Results:",
        f"  • {allocated_count} destination(s) selected",
        f"  • {rejected_count} destination(s) rejected (unsafe or inaccessible)",
        f"  • {total_allocated} families allocated successfully",
    ]

    if unallocated > 0:
        summary_parts.append(f"  • ⚠️ {unallocated} families UNALLOCATED — additional destinations needed")
    else:
        summary_parts.append(f"  • ✅ All families allocated")

    return "\n".join(summary_parts)
