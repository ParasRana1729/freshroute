"""
FreshRoute API Schemas — Pydantic v2 (spec 3.2, 5.1-5.2)

Standardized JSON schemas for SurplusBatch and RecipientNode,
plus request/response envelopes for the four optimizer endpoints.
Units: kg and Celsius primary; frontend lbs supported via converter
in routes layer (mockData.js uses lbs, spec uses kg — schemas accept both
with validator).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class FoodCategory(str, Enum):
    Dairy = "Dairy"
    Prepared = "Prepared"
    Produce = "Produce"
    Bakery = "Bakery"
    Grains = "Grains"


class StorageCondition(str, Enum):
    Chilled_Reefer = "Chilled_Reefer"
    Insulated = "Insulated"
    Dry_Ambient = "Dry Ambient Safe"
    Ambient = "Dry Ambient"


class DietaryPolicy(str, Enum):
    Strict_Lacto_Vegetarian = "Strict_Lacto_Vegetarian"
    Lacto_Vegetarian = "Lacto_Vegetarian"
    Halal_Required = "Halal_Required"
    Vegetarian = "Vegetarian"
    Mixed = "Mixed"


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class DietaryFlags(BaseModel):
    is_pure_veg: bool = True
    contains_egg: bool = False
    contains_meat: bool = False
    is_halal: bool = False
    contains_onion_garlic: bool = False


# ---------------------------------------------------------------------------
# Spec 3.2: SurplusBatch Input Schema
# ---------------------------------------------------------------------------

class SurplusBatch(BaseModel):
    batch_id: str = Field(..., examples=["SURPLUS-PB-2026-0818"])
    donor_id: str = Field(..., examples=["donor-verka-ludhiana-01"])
    donor_name: Optional[str] = Field(None, examples=["Verka Dairy Cooperative Plant"])
    category: FoodCategory = Field(..., examples=["Dairy"])
    item_description: str = Field(..., examples=["Pasteurized Cow Milk Pouches (500ml)"])
    gross_weight_kg: Optional[float] = Field(None, ge=0, examples=[850.0])
    # Frontend sends lbs; we accept and convert.
    batchWeightLbs: Optional[float] = Field(None, ge=0, description="Alt lbs (mockData.js)")
    volume_liters: Optional[float] = Field(None, ge=0)
    base_shelf_life_hours: Optional[float] = Field(None, ge=0)
    storage_condition: Optional[StorageCondition] = None
    temp_requirement_c: Optional[List[float]] = Field(None, examples=[[2.0, 4.0]])
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None
    dietary_flags: DietaryFlags = Field(default_factory=DietaryFlags)
    origin_coordinates: List[float] = Field(..., min_length=2, max_length=2, examples=[[30.9325, 75.8350]])
    ambient_temp_c: Optional[float] = Field(None, examples=[36.0])
    humidity_pct: Optional[float] = Field(None, ge=0, le=100, examples=[72.0])
    elapsed_hours: float = Field(0.0, ge=0)

    # Compatibility: map lbs -> kg if kg missing
    @model_validator(mode="after")
    def _coerce_weight(self) -> "SurplusBatch":
        if self.gross_weight_kg is None and self.batchWeightLbs is not None:
            self.gross_weight_kg = round(self.batchWeightLbs / 2.20462, 2)
        if self.gross_weight_kg is None:
            self.gross_weight_kg = 0.0
        return self

    @field_validator("origin_coordinates")
    @classmethod
    def _validate_coords(cls, v: List[float]) -> List[float]:
        lat, lon = v
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("coordinates must be [lat,lon] in valid range")
        return v


# ---------------------------------------------------------------------------
# Spec 3.2: Recipient Pantry / Langar Node Schema
# ---------------------------------------------------------------------------

class RecipientNode(BaseModel):
    recipient_id: str = Field(..., examples=["recip-amritsar-langar-01"])
    name: str = Field(..., examples=["Sri Guru Ram Dass Ji Langar"])
    organization_type: Optional[str] = Field(None, examples=["Community_Langar_Kitchen"])
    address: Optional[str] = None
    coordinates: List[float] = Field(..., min_length=2, max_length=2, examples=[[31.6200, 74.8765]])
    daily_meal_demand: Optional[int] = Field(None, ge=0, examples=[45000])
    current_stock_hours: Optional[float] = Field(None, ge=0, examples=[3.5])
    has_cold_storage: Optional[bool] = None
    cold_storage_capacity_liters: Optional[float] = Field(None, ge=0)
    capacity_lbs: Optional[float] = Field(None, ge=0, description="Alt capacity lbs")
    dietary_policy: str = Field("Mixed", examples=["Strict_Lacto_Vegetarian"])
    urgency_score: float = Field(50.0, ge=0, le=100)
    hunger_vulnerability_index: Optional[float] = Field(None, ge=0, le=100)

    # Normalize legacy fields from mockData.js
    @field_validator("urgency_score", mode="before")
    @classmethod
    def _coerce_urgency(cls, v: Any) -> Any:
        if v is None:
            return 50.0
        return v

    @model_validator(mode="after")
    def _coerce_capacity(self) -> "RecipientNode":
        # Map hunger index -> urgency if urgency missing
        if self.hunger_vulnerability_index is not None and self.urgency_score == 50.0:
            # Heuristic: urgency ~ HVI if not explicitly set
            self.urgency_score = float(self.hunger_vulnerability_index)
        return self

    @field_validator("coordinates")
    @classmethod
    def _validate_recip_coords(cls, v: List[float]) -> List[float]:
        lat, lon = v
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("coordinates must be [lat,lon]")
        return v


# ---------------------------------------------------------------------------
# Endpoint Payloads (spec 5.1-5.2)
# ---------------------------------------------------------------------------

class ShelfLifeRequest(BaseModel):
    category: FoodCategory
    ambient_temp_c: float = Field(..., examples=[42.0])
    humidity_pct: float = Field(65.0, ge=0, le=100, examples=[78.0])
    elapsed_hours: float = Field(0.0, ge=0, examples=[2.0])


class ShelfLifeResponse(BaseModel):
    status: Literal["success"] = "success"
    category: FoodCategory
    ambient_temp_c: float
    humidity_pct: float
    decay_multiplier: float
    base_shelf_life_hours: float
    dynamic_safe_hours_remaining: float
    adjusted_shelf_life_hours: float
    risk_classification: str
    cold_chain_mandatory: bool
    recommendation: str
    critical_temp_c: float
    Ea_over_R: float


class MatchRequest(BaseModel):
    surplus_batch: Optional[SurplusBatch] = Field(None, description="Single surplus batch (legacy); if surplus_batches supplied, this may be omitted")
    ambient_weather: Optional[Dict[str, Any]] = Field(None, examples=[{"temp_c": 38.0, "humidity_pct": 72.0}])
    candidate_recipients: Optional[List[RecipientNode]] = None
    # P4 MILP options (spec 2.1 MILP vs greedy)
    use_milp: bool = Field(False, description="If true, use MILP optimal solver vs greedy heuristic")
    solver: Optional[str] = Field(None, examples=["pulp", "ortools"], description="MILP backend: pulp (CBC) or ortools (CP-SAT)")
    min_score: float = Field(40.0, ge=0, le=100, description="Feasibility threshold S_ij")
    time_limit_secs: float = Field(0.8, ge=0.1, le=5.0, description="MILP time budget")
    # Batch mode: optional list for MILP multi-batch optimization
    surplus_batches: Optional[List[SurplusBatch]] = Field(None, description="Batch MILP: list of surplus batches (alternative to single surplus_batch)")

    @model_validator(mode="after")
    def _require_batch(self) -> "MatchRequest":
        if self.surplus_batch is None and (self.surplus_batches is None or len(self.surplus_batches) == 0):
            raise ValueError("Either surplus_batch or surplus_batches must be provided")
        return self


class MatchResponse(BaseModel):
    status: Literal["success"] = "success"
    match_score: float
    assigned_recipient: Dict[str, Any]
    assigned_vehicle: Dict[str, Any]
    safe_transit_window_hours: float
    co2_abatement_kg: float
    execution_latency_ms: int
    risk_classification: str
    cold_chain_enforced: bool
    solver: Optional[str] = Field(None, examples=["greedy", "pulp-cbc:Optimal", "ortools-cp-sat"], description="Solver used")
    allocations: Optional[List[Dict[str, Any]]] = Field(None, description="Batch MILP: all allocations when surplus_batches supplied")


class ForecastRequest(BaseModel):
    state_code: str = Field("IN-PB", examples=["IN-PB"])
    district_id: Optional[str] = Field(None, examples=["ludhiana"])
    horizon_days: int = Field(7, ge=1, le=30)
    include_langar_pilgrim_surge: bool = True


class ForecastResponse(BaseModel):
    status: Literal["success"] = "success"
    district_id: str
    district_name: str
    horizon_days: int
    forecast_demand_lbs: List[float]
    forecast_demand_lower_lbs: Optional[List[float]] = Field(None, description="10th percentile lower demand bound")
    forecast_demand_upper_lbs: Optional[List[float]] = Field(None, description="90th percentile upper demand bound")
    weekly_total_lbs: float
    gap_lbs_estimate: float
    hunger_vulnerability_index: float


class RoutingRequest(BaseModel):
    fleet_available: Optional[List[str]] = None
    pickup_nodes: List[Dict[str, Any]]
    dropoff_nodes: List[Dict[str, Any]]
    traffic_matrix: Optional[str] = Field(None, examples=["live_nh44_telemetry"])
    # P5 VRPTW options
    use_or_tools: bool = Field(False, description="If true, use OR-Tools VRPTW solver")
    t_safe_hours: Optional[List[float]] = Field(None, description="Per-pickup t_safe hours for time windows (spec 2.3)")
    lambda_penalty: float = Field(2.0, ge=0, le=10, description="Perishability weight lambda in objective (spec 3.2:162)")
    time_limit_secs: float = Field(2.0, ge=0.5, le=10, description="OR-Tools time budget")
    traffic_congestion: bool = Field(False, description="NH44 congestion flag (Phagwara bypass)")


class RoutingResponse(BaseModel):
    status: Literal["success"] = "success"
    routes: List[Dict[str, Any]]
    total_distance_km: float
    total_eta_minutes: int
    fleet_used: List[str]
    solver: str
