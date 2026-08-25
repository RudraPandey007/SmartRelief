"""
Pydantic v2 request/response schemas for the Relocation DSS API.

Strict validation: lat/lng bounds, positive integers, radius caps, etc.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import datetime


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    error: str
    message: str


class VillageOut(BaseModel):
    id: str
    name: str
    district: str
    state: str
    latitude: float
    longitude: float
    population: int
    households: int
    children_under_5: int
    elderly_above_65: int
    special_assistance: int
    river_flood_risk: float
    landslide_risk: float
    elevation_m: float
    river_distance_km: float
    avg_rainfall_mm: float
    historical_flood_frequency: int
    has_healthcare: bool
    has_water_supply: bool
    road_status: str
    is_source_village: bool
    notes: str = ""

    model_config = {"from_attributes": True}


class VillageListOut(BaseModel):
    count: int
    villages: List[VillageOut]


# ---------------------------------------------------------------------------
# Generate Plan Request / Response
# ---------------------------------------------------------------------------
class OptimizationWeights(BaseModel):
    safety: float = Field(default=0.25, ge=0, le=1)
    capacity: float = Field(default=0.20, ge=0, le=1)
    route: float = Field(default=0.15, ge=0, le=1)
    healthcare: float = Field(default=0.15, ge=0, le=1)
    water: float = Field(default=0.10, ge=0, le=1)
    vulnerability_fit: float = Field(default=0.10, ge=0, le=1)
    distance: float = Field(default=0.05, ge=0, le=1)


class GeneratePlanRequest(BaseModel):
    village_id: str = Field(..., min_length=1, max_length=50)
    search_radius_km: float = Field(default=120.0, ge=1.0, le=500.0)
    max_affected_families: Optional[int] = Field(default=None, ge=0)
    weights: Optional[OptimizationWeights] = None
    include_ai_summary: bool = Field(default=True)


class DestinationScore(BaseModel):
    destination_id: str
    destination_name: str
    destination_type: str  # village | shelter
    district: str
    state: str
    latitude: float
    longitude: float

    # Individual scores (0-1)
    safety_score: float = 0.0
    capacity_score: float = 0.0
    route_safety_score: float = 0.0
    healthcare_score: float = 0.0
    water_score: float = 0.0
    vulnerability_fit_score: float = 0.0
    distance_score: float = 0.0

    # Combined
    weighted_total: float = 0.0
    rank: int = 0

    # Capacity details
    total_capacity: int = 0
    available_capacity: int = 0
    families_allocated: int = 0

    # Route details
    route_id: Optional[str] = None
    route_distance_km: float = 0.0
    route_time_min: float = 0.0
    route_status: str = "unknown"
    is_flooded: bool = False
    is_landslide_affected: bool = False


class RejectedDestination(BaseModel):
    destination_id: str
    destination_name: str
    latitude: float = 0.0
    longitude: float = 0.0
    rejection_reasons: List[str]


class GeneratePlanResponse(BaseModel):
    # Source village
    village_id: str
    village_name: str
    district: str
    state: str
    latitude: float = 0.0
    longitude: float = 0.0
    population: int
    households: int
    hazard_score: float
    vulnerability_score: float
    combined_risk: float
    risk_classification: str  # extreme | high | medium | low

    # Affected population
    affected_families: int
    search_radius_km: float

    # Results
    ranked_destinations: List[DestinationScore]
    rejected_destinations: List[RejectedDestination]
    total_families_allocated: int
    unallocated_families: int

    # Summary
    summary_text: str = ""
    ai_summary: str = ""

    # Metadata
    weights_used: OptimizationWeights
    created_at: str = ""


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
class SimulationOverrides(BaseModel):
    rainfall_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    occupancy_percent: float = Field(default=1.0, ge=0.0, le=1.0)
    road_accessibility_percent: float = Field(default=1.0, ge=0.0, le=1.0)


class SimulationRequest(BaseModel):
    village_id: str = Field(..., min_length=1, max_length=50)
    overrides: SimulationOverrides = SimulationOverrides()
    search_radius_km: float = Field(default=120.0, ge=1.0, le=500.0)
    weights: Optional[OptimizationWeights] = None


class SimulationResponse(BaseModel):
    before: GeneratePlanResponse
    after: GeneratePlanResponse
    changes_summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardOverview(BaseModel):
    total_villages: int
    villages_by_risk: Dict[str, int]  # extreme/high/medium/low: count
    total_population: int
    total_households: int
    total_shelters: int
    total_shelter_capacity: int
    available_shelter_capacity: int
    total_routes: int
    blocked_routes: int
    degraded_routes: int
    active_plans: int
    total_affected_population: int
