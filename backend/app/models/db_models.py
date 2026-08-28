"""SQLModel table definitions for the Relocation DSS."""
from typing import Optional
from sqlmodel import SQLModel, Field, Column
import datetime
import json



class Village(SQLModel, table=True):
    __tablename__ = "villages"

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    district: str
    state: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    # Population
    population: int = Field(ge=0)
    households: int = Field(ge=0)
    children_under_5: int = Field(ge=0)
    elderly_above_65: int = Field(ge=0)
    special_assistance: int = Field(ge=0)

    # Hazard indicators
    avg_rainfall_mm: float = Field(ge=0)
    elevation_m: float
    river_distance_km: float = Field(ge=0)
    historical_flood_frequency: int = Field(ge=0)
    river_flood_risk: float = Field(ge=0, le=1)
    landslide_risk: float = Field(ge=0, le=1)

    # Infrastructure
    has_healthcare: bool = True
    has_water_supply: bool = True
    road_status: str = "available"  # available | degraded | blocked
    is_source_village: bool = False

    # Metadata
    notes: str = ""



class Shelter(SQLModel, table=True):
    __tablename__ = "shelters"

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    village_id: str = Field(foreign_key="villages.id")
    district: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    total_capacity: int = Field(ge=0)
    current_occupancy: int = Field(ge=0)
    facilities: str = "[]"  # JSON string of facility list
    is_temporary: bool = False

    notes: str = ""

    @property
    def available_capacity(self) -> int:
        return self.total_capacity - self.current_occupancy

    @property
    def facility_list(self) -> list:
        return json.loads(self.facilities) if self.facilities else []



class Route(SQLModel, table=True):
    __tablename__ = "routes"

    id: str = Field(primary_key=True)
    from_village_id: str = Field(foreign_key="villages.id", index=True)
    # to_village_id holds a village ID *or* a shelter ID — no FK so both work
    to_village_id: str = Field(index=True)
    # Optional explicit shelter target (mirrors to_village_id when destination is a shelter)
    to_shelter_id: Optional[str] = Field(default=None)
    distance_km: float = Field(ge=0)
    estimated_time_min: float = Field(ge=0)

    route_status: str = "available"  # available | degraded | blocked
    safety_score: float = Field(ge=0, le=1)
    is_flooded: bool = False
    is_landslide_affected: bool = False
    road_type: str = "district_road"

    notes: str = ""


# Relocation Plan (stored for history)
class RelocationPlan(SQLModel, table=True):
    __tablename__ = "relocation_plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    village_id: str = Field(foreign_key="villages.id", index=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # Source village risk scores
    hazard_score: float = 0.0
    vulnerability_score: float = 0.0
    combined_risk: float = 0.0

    # Plan output (JSON-serialized)
    allocations: str = "[]"  # JSON: [{dest_id, dest_name, families_allocated, route_id, ...}]
    rejected_destinations: str = "[]"  # JSON: [{dest_id, reason, ...}]
    summary_text: str = ""  # Gemini-generated or rule-based summary

    # Metadata
    is_simulation: bool = False
    simulation_overrides: str = "{}"  # JSON: override params if simulation
