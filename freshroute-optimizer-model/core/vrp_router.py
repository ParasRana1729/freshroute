"""
FreshRoute AI: Cold-Chain Vehicle Assignment & VRPTW Router (Stage 4)

Assigns vehicle class and solves Vehicle Routing Problem with Time Windows
using Google OR-Tools (spec 3.1-3.2).

Vehicle tiering matrix (spec 3.1):
  Cargo E-Rickshaw  300-500 kg   <8 km    hyper-local alleys
  Tata Ace EV       1000 kg      10-30 km intra-city mandi→kitchen
  Reefer Sprinter   1500 kg      20-80 km chilled milk & paneer
  Heavy Reefer      4000+ kg     50-250 km inter-city GT corridor

Objective (spec 3.2:162):
  min sum_{v in V} sum_{(u,w)} c_uw x_uvw + lambda sum_i t_delivery(i)/t_safe(i)

Status (P0): Deterministic heuristic using haversine + tiering; OR-Tools
solver path wired behind `use_or_tools` flag for P5. Heuristic already
satisfies spec unit expectations and frontend simulation (see src/App.jsx:189).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class VehicleSpec:
    vehicle_type: str
    max_capacity_kg: float
    range_radius_km: float
    best_use_case: str
    reefer: bool
    nominal_speed_kmh: float = 35.0


# Tiering matrix exactly as spec 3.1, units kg (spec says kg; frontend lbs).
VEHICLE_TIERS: List[VehicleSpec] = [
    VehicleSpec("Cargo E-Rickshaw", 500, 8, "Hyper-local congested alleys", reefer=False, nominal_speed_kmh=18),
    VehicleSpec("Tata Ace EV", 1000, 30, "Intra-city mandi-to-kitchen", reefer=True, nominal_speed_kmh=30),
    VehicleSpec("Reefer Sprinter", 1500, 80, "Chilled milk & paneer routes", reefer=True, nominal_speed_kmh=45),
    VehicleSpec("Heavy Reefer", 4000, 250, "Inter-city GT Road corridors", reefer=True, nominal_speed_kmh=55),
]

# Mock fleet mirroring src/data/mockData.js INITIAL_FLEET for demo continuity
FLEET_MOCK: List[Dict[str, Any]] = [
    {"id": "van-01", "name": "Tata Ace EV Reefer (PB-10-CZ-8821)", "type": "Electric Cold-Chain Van", "capacityLbs": 2200, "capacity_kg": 1000, "reefer": True, "speed_kmh": 30},
    {"id": "van-02", "name": "Ashok Leyland Cold Carrier (PB-02-AK-4412)", "type": "Refrigerated Medium Truck", "capacityLbs": 4500, "capacity_kg": 1500, "reefer": True, "speed_kmh": 45},
    {"id": "van-03", "name": "Mahindra Bolero Maxi Reefer (PB-11-BT-9034)", "type": "Refrigerated Utility Vehicle", "capacityLbs": 2800, "capacity_kg": 1200, "reefer": True, "speed_kmh": 40},
    {"id": "van-04", "name": "Eicher Pro 2049 Heavy Reefer (PB-65-AX-1288)", "type": "Heavy Cold-Chain Carrier", "capacityLbs": 8000, "capacity_kg": 4000, "reefer": True, "speed_kmh": 55},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)), 2)


class VRPRouter:
    """Vehicle assignment + route optimizer.

    Heuristic path (default): pick smallest feasible tier/vehicle fulfilling
    weight, distance, and cold_chain_mandatory; compute ETA via haversine/speed
    (+toll for NH44 congestion if flagged).

    OR-Tools path (P5): `solve_vrp(..., use_or_tools=True)` builds RoutingModel
    with time windows = [pickup_window, t_safe deadline]; fallback to heuristic
    if solver not installed.
    """

    def __init__(self, fleet: Optional[List[Dict[str, Any]]] = None) -> None:
        self.fleet = fleet or FLEET_MOCK

    # ------------------------------------------------------------------
    # Vehicle selection
    # ------------------------------------------------------------------

    def select_vehicle(
        self,
        weight_kg: float,
        distance_km: float,
        cold_chain_mandatory: bool,
    ) -> Dict[str, Any]:
        """Select optimal vehicle spec + concrete van.

        Preference: smallest capacity that covers weight and radius; reefer if mandatory.
        """
        # Filter tiers by capacity and reefer
        candidates = [t for t in VEHICLE_TIERS if t.max_capacity_kg >= weight_kg]
        if not candidates:
            candidates = [VEHICLE_TIERS[-1]]  # heavy
        # Cold-chain filter
        if cold_chain_mandatory:
            reefer_candidates = [t for t in candidates if t.reefer]
            if reefer_candidates:
                candidates = reefer_candidates
        # Radius filter (allow exceed if heavy)
        radius_ok = [t for t in candidates if t.range_radius_km >= distance_km]
        tier = (radius_ok or candidates)[0]

        # Pick concrete fleet van matching tier approx capacity
        # Try to match capacity bucket
        fleet_sorted = sorted(self.fleet, key=lambda v: v.get("capacity_kg", v.get("capacityLbs", 0) / 2.20462))
        chosen = None
        for van in fleet_sorted:
            cap = float(van.get("capacity_kg", van.get("capacityLbs", 0) / 2.20462))
            if cap >= weight_kg and (not cold_chain_mandatory or van.get("reefer", True)):
                # Also check radius via tier
                if tier.range_radius_km >= distance_km or cap >= 3000:
                    chosen = van
                    break
        if chosen is None:
            chosen = fleet_sorted[-1]

        return {
            "tier": tier.vehicle_type,
            "tier_spec": tier,
            "vehicle": chosen,
            "vehicle_id": chosen.get("id"),
            "vehicle_name": chosen.get("name"),
            "reefer": tier.reefer or chosen.get("reefer", False),
        }

    # ------------------------------------------------------------------
    # Route solving
    # ------------------------------------------------------------------

    def plan_route(
        self,
        origin_coords: List[float],
        dest_coords: List[float],
        *,
        weight_kg: float = 500,
        cold_chain_mandatory: bool = False,
        traffic_congestion: bool = False,
        target_temp_c: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Plan single pickup->drop route.

        Returns distance_km, eta_minutes, vehicle assignment, temp target.
        """
        d_km = haversine_km(origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1])
        sel = self.select_vehicle(weight_kg, d_km, cold_chain_mandatory)
        tier: VehicleSpec = sel["tier_spec"]
        van = sel["vehicle"]

        # ETA
        speed = float(van.get("speed_kmh", tier.nominal_speed_kmh))
        eta_h = d_km / max(5.0, speed)
        # Congestion penalty (NH44 Phagwara bypass case src/App.jsx:189-203)
        if traffic_congestion:
            eta_h *= 1.35
        eta_min = int(round(eta_h * 60))
        # Cold chain target
        if target_temp_c is None:
            if cold_chain_mandatory:
                target_temp_c = 2.7  # spec example Ashok Leyland @2.7C
            else:
                target_temp_c = 4.0 if tier.reefer else 12.0

        # Simple waypoint: direct; P5 OR-Tools will expand to multi-stop
        return {
            "distance_km": d_km,
            "eta_minutes": eta_min,
            "vehicle_id": sel["vehicle_id"],
            "vehicle_name": sel["vehicle_name"],
            "tier": sel["tier"],
            "reefer": sel["reefer"],
            "target_temp_c": round(target_temp_c, 1),
            "origin": origin_coords,
            "destination": dest_coords,
            "waypoints": [origin_coords, dest_coords],
            "traffic_congestion": traffic_congestion,
        }

    def solve_vrp(
        self,
        pickup_nodes: List[Dict[str, Any]],
        dropoff_nodes: List[Dict[str, Any]],
        fleet_available: Optional[List[str]] = None,
        use_or_tools: bool = False,
    ) -> Dict[str, Any]:
        """Multi-node VRP stub.

        When use_or_tools=True and ortools installed, delegates to OR-Tools
        RoutingModel (P5). Otherwise returns sequential heuristic routes.
        """
        if use_or_tools:
            try:
                # Lazy import to keep dependency optional at P0
                from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore

                # TODO(P5): build distance matrix via haversine or OSRM, set
                # time windows from t_safe, capacities, and solve.
                # For now fall through to heuristic note.
                _ = (pywrapcp, routing_enums_pb2)
            except ImportError:
                pass

        # Heuristic: pair pickups-dropoffs 1:1 in order
        routes: List[Dict[str, Any]] = []
        pairs = min(len(pickup_nodes), len(dropoff_nodes))
        for i in range(pairs):
            p = pickup_nodes[i]
            d = dropoff_nodes[i]
            # Extract coords with tolerant key lookups
            o = p.get("origin_coordinates") or p.get("coordinates") or p.get("origin") or [30.9, 75.85]
            dest = d.get("coordinates") or d.get("destination") or [31.6, 74.85]
            w = float(p.get("gross_weight_kg", p.get("batchWeightLbs", 500)))
            if w > 1000 and w < 5000:  # heuristic: lbs vs kg confusion -> /2.2 if looks like lbs grain
                # Keep as-is for mock; real schema uses kg (Pydantic will normalize)
                pass
            route = self.plan_route(
                origin_coords=o,
                dest_coords=dest,
                weight_kg=w if w < 2000 else w / 2.20462,
                cold_chain_mandatory=bool(p.get("cold_chain_mandatory", p.get("coldChainRequired", False))),
            )
            route["pickup_id"] = p.get("batch_id", p.get("id", f"pickup-{i}"))
            route["dropoff_id"] = d.get("recipient_id", d.get("id", f"drop-{i}"))
            routes.append(route)

        total_km = round(sum(r["distance_km"] for r in routes), 2)
        total_eta = sum(r["eta_minutes"] for r in routes)
        return {
            "routes": routes,
            "total_distance_km": total_km,
            "total_eta_minutes": total_eta,
            "fleet_used": list({r["vehicle_id"] for r in routes}),
            "solver": "heuristic-v1 (OR-Tools reserved for P5)",
        }
