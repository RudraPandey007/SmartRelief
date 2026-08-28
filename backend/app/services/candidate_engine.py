"""Candidate engine — find nearby villages and shelters using haversine."""
from typing import List, Tuple
from math import radians, sin, cos, sqrt, atan2


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0  # Earth's radius in km

    lat1_r, lon1_r = radians(lat1), radians(lon1)
    lat2_r, lon2_r = radians(lat2), radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(R * c, 2)


def find_nearby_villages(
    source_lat: float,
    source_lon: float,
    villages: list,
    radius_km: float = 120.0,
    exclude_source_id: str = None,
) -> List[Tuple[dict, float]]:
    """Villages within radius_km, sorted by distance."""
    candidates = []

    for v in villages:
        if exclude_source_id and v.id == exclude_source_id:
            continue

        dist = haversine_km(source_lat, source_lon, v.latitude, v.longitude)

        if dist <= radius_km:
            candidates.append((v, dist))

    # Sort by distance ascending
    candidates.sort(key=lambda x: x[1])
    return candidates


def find_nearby_shelters(
    source_lat: float,
    source_lon: float,
    shelters: list,
    radius_km: float = 120.0,
) -> List[Tuple[dict, float]]:
    """Shelters within radius_km, sorted by distance."""
    candidates = []

    for s in shelters:
        dist = haversine_km(source_lat, source_lon, s.latitude, s.longitude)

        if dist <= radius_km:
            candidates.append((s, dist))

    # Sort by distance ascending
    candidates.sort(key=lambda x: x[1])
    return candidates


def find_all_candidates(
    source_lat: float,
    source_lon: float,
    villages: list,
    shelters: list,
    radius_km: float = 120.0,
    exclude_source_id: str = None,
) -> List[dict]:
    """Combined search for nearby villages + shelters, sorted by distance."""
    candidates = []

    # Villages
    for v, dist in find_nearby_villages(
        source_lat, source_lon, villages, radius_km, exclude_source_id
    ):
        candidates.append({
            "id": v.id,
            "name": v.name,
            "type": "village",
            "district": v.district,
            "state": v.state,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "distance_km": dist,
            # Village-specific fields for scoring
            "river_flood_risk": v.river_flood_risk,
            "landslide_risk": v.landslide_risk,
            "elevation_m": v.elevation_m,
            "has_healthcare": v.has_healthcare,
            "has_water_supply": v.has_water_supply,
            "road_status": v.road_status,
            "population": v.population,
            "households": v.households,
            # For capacity scoring, use population as proxy (shelters have explicit capacity)
            "total_capacity": v.population // 2,  # rough: can host ~50% of existing pop
            "current_occupancy": 0,
        })

    # Shelters
    for s, dist in find_nearby_shelters(
        source_lat, source_lon, shelters, radius_km
    ):
        candidates.append({
            "id": s.id,
            "name": s.name,
            "type": "shelter",
            "district": s.district,
            "state": "",
            "latitude": s.latitude,
            "longitude": s.longitude,
            "distance_km": dist,
            # Shelter-specific fields
            "river_flood_risk": 0.0,  # shelters assumed safe
            "landslide_risk": 0.0,
            "elevation_m": 0.0,
            "has_healthcare": "medical_team" in (s.facility_list if hasattr(s, 'facility_list') else []),
            "has_water_supply": "water" in (s.facility_list if hasattr(s, 'facility_list') else []),
            "road_status": "available",
            "population": 0,
            "households": 0,
            "total_capacity": s.total_capacity,
            "current_occupancy": s.current_occupancy,
        })

    candidates.sort(key=lambda x: x["distance_km"])
    return candidates
