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

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _get_osrm_distance_matrix(
    coords: List[List[float]], timeout: float = 3.0
) -> Optional[Tuple[List[List[int]], List[List[int]]]]:
    """Try OSRM table for haversine fallback (D3) [@osm2024; @osrm2024].

    Expects coords as [lat,lon] per spec; OSRM needs lon,lat.
    Returns (dist_matrix_m, time_matrix_s) or None on failure/timeout.
    Uses public demo server https://router.project-osrm.org; falls back to
    None so caller uses haversine (spec prior). No API key required.
    """
    try:
        # OSRM table expects lon,lat;lon,lat;...
        coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
        # Use table service: https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance,duration
        url = f"https://router.project-osrm.org/table/v1/driving/{coord_str}?annotations=distance,duration"
        req = urllib.request.Request(url, headers={"User-Agent": "FreshRoute-P5-OSRM/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
            if data.get("code") != "Ok":
                return None
            dists = data.get("distances")
            durs = data.get("durations")
            if not dists or not durs:
                return None
            # Convert to int meters / seconds, round
            dist_m = [[int(round(v)) if v is not None else 0 for v in row] for row in dists]
            time_s = [[int(round(v)) if v is not None else 0 for v in row] for row in durs]
            # Basic sanity: must be n x n
            n = len(coords)
            if len(dist_m) != n or any(len(row) != n for row in dist_m):
                return None
            return dist_m, time_s
    except Exception:
        return None


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
    if solver not installed. Objective (spec 3.2:162) min sum c_uw x_uvw
    + lambda sum t_delivery/t_safe is encoded via weighted time cost
    [@toth2014vrp; @solomon1987; @orgtoolsvrp2024].
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
        *,
        t_safe_hours: Optional[List[float]] = None,
        lambda_penalty: float = 2.0,
        time_limit_secs: float = 2.0,
        traffic_congestion: bool = False,
    ) -> Dict[str, Any]:
        """Multi-node VRP with OR-Tools VRPTW [@toth2014vrp; @solomon1987].

        Heuristic fallback pairs pickups-dropoffs 1:1. OR-Tools path builds
        RoutingModel with time windows derived from t_safe, capacity
        constraints from vehicle tiering (spec 3.1), and objective
        min sum c_uw x_uvw + lambda sum t_delivery/t_safe (spec 3.2:162).

        Parameters
        ----------
        pickup_nodes, dropoff_nodes : as in tests/test_api.py:62-67
        fleet_available : optional list of vehicle ids to restrict fleet
        use_or_tools : if True, attempt OR-Tools solve with fallback
        t_safe_hours : optional list of t_safe per pickup (for time windows)
        lambda_penalty : weight for perishability term (grid [0.5,5], default 2.0)
        time_limit_secs : solver time budget (spec 9.1 <2s for 50 nodes)
        """
        if use_or_tools:
            ort_res = self._solve_vrp_ortools(
                pickup_nodes, dropoff_nodes, fleet_available,
                t_safe_hours=t_safe_hours,
                lambda_penalty=lambda_penalty,
                time_limit_secs=time_limit_secs,
                traffic_congestion=traffic_congestion,
            )
            if ort_res is not None:
                return ort_res

        # Heuristic: pair pickups-dropoffs 1:1 in order
        routes: List[Dict[str, Any]] = []
        pairs = min(len(pickup_nodes), len(dropoff_nodes))
        # Handle single pickup multi-dropoff: if one pickup but many dropoffs, repeat same pickup
        if len(pickup_nodes) == 1 and len(dropoff_nodes) > 1:
            pairs = len(dropoff_nodes)
            pickup_nodes = pickup_nodes * len(dropoff_nodes)
        for i in range(pairs):
            p = pickup_nodes[i] if i < len(pickup_nodes) else pickup_nodes[-1]
            d = dropoff_nodes[i] if i < len(dropoff_nodes) else dropoff_nodes[-1]
            # Extract coords with tolerant key lookups
            o = p.get("origin_coordinates") or p.get("coordinates") or p.get("origin") or [30.9, 75.85]
            dest = d.get("coordinates") or d.get("destination") or [31.6, 74.85]
            w = float(p.get("gross_weight_kg", p.get("batchWeightLbs", p.get("weight_kg", 500))) or 500)
            route = self.plan_route(
                origin_coords=o,
                dest_coords=dest,
                weight_kg=w if w < 2000 else w / 2.20462,
                cold_chain_mandatory=bool(p.get("cold_chain_mandatory", p.get("coldChainRequired", False))),
                traffic_congestion=traffic_congestion,
            )
            route["pickup_id"] = p.get("batch_id", p.get("id", f"pickup-{i}"))
            route["dropoff_id"] = d.get("recipient_id", d.get("id", f"drop-{i}"))
            routes.append(route)

        if not routes and pickup_nodes and dropoff_nodes:
            # Edge: no pairs due to empty but nodes exist — create at least one
            routes = [self.plan_route(
                origin_coords=pickup_nodes[0].get("origin_coordinates", [30.9, 75.85]),
                dest_coords=dropoff_nodes[0].get("coordinates", [31.6, 74.85]),
                weight_kg=float(pickup_nodes[0].get("gross_weight_kg", 500)),
                cold_chain_mandatory=bool(pickup_nodes[0].get("cold_chain_mandatory", False)),
            )]

        total_km = round(sum(r["distance_km"] for r in routes), 2)
        total_eta = sum(r["eta_minutes"] for r in routes)
        return {
            "routes": routes,
            "total_distance_km": total_km,
            "total_eta_minutes": total_eta,
            "fleet_used": list({r["vehicle_id"] for r in routes}),
            "solver": "heuristic-v1",
        }

    # ------------------------------------------------------------------
    # OR-Tools VRPTW implementation (P5)
    # ------------------------------------------------------------------

    def _solve_vrp_ortools(
        self,
        pickup_nodes: List[Dict[str, Any]],
        dropoff_nodes: List[Dict[str, Any]],
        fleet_available: Optional[List[str]],
        *,
        t_safe_hours: Optional[List[float]],
        lambda_penalty: float,
        time_limit_secs: float,
        traffic_congestion: bool,
    ) -> Optional[Dict[str, Any]]:
        """Build and solve VRPTW via OR-Tools RoutingModel [@orgtoolsvrp2024]."""
        try:
            from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore
        except ImportError:
            return None

        if not pickup_nodes or not dropoff_nodes:
            return None

        # Fleet filtering
        fleet = self.fleet
        if fleet_available:
            avail_set = set(fleet_available)
            filtered = [v for v in fleet if v.get("id") in avail_set]
            if filtered:
                fleet = filtered

        # Build node list: depot + dropoffs (and pickups if multi-pickup case)
        # For PDP case where pickups != dropoffs counts, we treat all dropoffs as delivery nodes
        # Depot is centroid of pickup origins or first pickup
        try:
            # Depot = first pickup origin
            depot_coords = pickup_nodes[0].get("origin_coordinates") or pickup_nodes[0].get("coordinates") or [30.9325, 75.8350]
        except Exception:
            depot_coords = [30.9325, 75.8350]

        # Nodes: 0=depot, 1..N = dropoffs
        # If multiple pickups with distinct origins, we treat each pickup as separate depot-visit? Simplify to depot+all unique coords
        dropoff_coords: List[List[float]] = []
        dropoff_demands: List[float] = []
        dropoff_ids: List[str] = []
        # Distribute total pickup weight across dropoffs proportionally if needed
        total_pickup_weight = sum(float(p.get("gross_weight_kg") or p.get("batchWeightLbs") or p.get("weight_kg") or 0) for p in pickup_nodes)
        if total_pickup_weight == 0:
            total_pickup_weight = len(dropoff_nodes) * 500.0

        for idx, d in enumerate(dropoff_nodes):
            coords = d.get("coordinates") or d.get("destination") or [31.6, 74.85]
            # Ensure [lat,lon]
            if not isinstance(coords, (list, tuple)) or len(coords) != 2:
                coords = [31.6, 74.85]
            dropoff_coords.append(list(coords))
            dropoff_ids.append(str(d.get("recipient_id", d.get("id", f"drop-{idx}"))))
            # Demand: if pickup_nodes 1:1, use that pickup's weight for this dropoff
            if len(pickup_nodes) == len(dropoff_nodes):
                w = float(pickup_nodes[idx].get("gross_weight_kg", pickup_nodes[idx].get("batchWeightLbs", 500)) or 500)
            else:
                # Split total weight evenly (or use dropoff's demand if hints)
                w = float(d.get("demand_kg", total_pickup_weight / max(1, len(dropoff_nodes))))
            if w > 3000:  # lbs confusion
                w = w / 2.20462
            dropoff_demands.append(max(0.0, w))

        # If single pickup with large weight and multiple dropoffs, demands already split; keep as is

        all_coords = [list(depot_coords)] + dropoff_coords
        n_nodes = len(all_coords)

        # Build distance matrix: try OSRM live first (D3), fallback to haversine [@toth2014vrp]
        dist_matrix: Optional[List[List[int]]] = None
        time_matrix: Optional[List[List[int]]] = None
        # OSRM attempt (public demo, 3s timeout) — uses lon,lat order
        osrm_res = _get_osrm_distance_matrix(all_coords, timeout=3.0)
        if osrm_res is not None:
            dist_m, time_s = osrm_res
            # OSRM gives meters and seconds; convert time to minutes + service
            dist_matrix = dist_m
            time_matrix = [[0]*n_nodes for _ in range(n_nodes)]
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i == j:
                        continue
                    # time_s is seconds, convert to minutes, add service
                    base_min = int(round(time_s[i][j] / 60))
                    if j != 0:
                        base_min += 10
                    # Traffic congestion penalty (1.35× if flagged, as in heuristic)
                    if traffic_congestion:
                        base_min = int(round(base_min * 1.35))
                    time_matrix[i][j] = max(1, base_min)
        if dist_matrix is None or time_matrix is None:
            # Haversine fallback
            dist_matrix = [[0]*n_nodes for _ in range(n_nodes)]
            time_matrix = [[0]*n_nodes for _ in range(n_nodes)]
            speed_kmh = 35.0 * (0.74 if traffic_congestion else 1.0)
            for i in range(n_nodes):
                for j in range(n_nodes):
                    if i == j:
                        continue
                    d_km = haversine_km(all_coords[i][0], all_coords[i][1], all_coords[j][0], all_coords[j][1])
                    dist_matrix[i][j] = int(round(d_km * 1000))
                    time_min = int(round((d_km / max(5.0, speed_kmh)) * 60))
                    if j != 0:
                        time_min += 10
                    time_matrix[i][j] = max(1, time_min)

        num_vehicles = min(len(fleet), max(1, len(dropoff_nodes)))
        # If fleet is larger than needed, cap; if smaller, use all fleet and allow multiple trips per vehicle via capacity splits
        # For VRPTW single-tour model, each vehicle does one tour from depot

        # Capacities per vehicle (kg)
        vehicle_capacities: List[int] = []
        vehicle_speeds: List[float] = []
        for idx in range(num_vehicles):
            van = fleet[idx % len(fleet)]
            cap = float(van.get("capacity_kg", van.get("capacityLbs", 1000) / 2.20462 if van.get("capacityLbs") else 1000))
            vehicle_capacities.append(int(round(cap)))
            vehicle_speeds.append(float(van.get("speed_kmh", 35.0)))

        # Time windows: depot [0, 24h], dropoffs [0, t_safe_hours*60]
        # t_safe_hours may be per-pickup; map to dropoff via pairing or use max
        time_windows: List[Tuple[int, int]] = [(0, 24*60)]  # depot
        horizon_hours = 24.0
        if t_safe_hours:
            # Map t_safe to dropoffs: if 1:1 length matches dropoffs, use directly
            if len(t_safe_hours) == len(dropoff_nodes):
                for h in t_safe_hours:
                    # At least 30 min, at most 24h
                    win_end = int(round(max(30, min(24*60, float(h) * 60))))
                    time_windows.append((0, win_end))
            else:
                # Use first t_safe for all, or avg
                avg_safe = float(sum(t_safe_hours) / len(t_safe_hours)) if t_safe_hours else 12.0
                win_end = int(round(max(30, min(24*60, avg_safe * 60))))
                time_windows.extend([(0, win_end)] * len(dropoff_nodes))
        else:
            # Derive from cold_chain flags: if any pickup cold_chain_mandatory, tight window 4h for corresponding dropoffs
            for idx, d in enumerate(dropoff_nodes):
                # Check matching pickup
                if idx < len(pickup_nodes) and pickup_nodes[idx].get("cold_chain_mandatory"):
                    time_windows.append((0, 4*60))  # 4h CRITICAL_HAZARD
                else:
                    time_windows.append((0, 12*60))  # 12h ELEVATED_RISK default

        # If we have fewer time_windows than nodes (edge), pad
        while len(time_windows) < n_nodes:
            time_windows.append((0, 24*60))

        # Manager & Model
        try:
            manager = pywrapcp.RoutingIndexManager(n_nodes, num_vehicles, 0)
            routing = pywrapcp.RoutingModel(manager)
        except Exception:
            return None

        # Distance callback (cost = distance + lambda * time_perishability)
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            # Base distance
            base = dist_matrix[from_node][to_node]
            # Perishability penalty: lambda * time_matrix weighted into distance space
            # Scale: lambda=2 means 1 min ~= 2* (distance meter equivalent ~ 100m)? Keep moderate: lambda* time_min* 100
            penalty = int(round(lambda_penalty * time_matrix[from_node][to_node] * 100))
            return base + penalty

        transit_cb_idx = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)

        # Capacity dimension
        def demand_callback(from_index):
            node = manager.IndexToNode(from_index)
            if node == 0:
                return 0
            # dropoff index 1-based -> demands list 0-based
            return int(round(dropoff_demands[node - 1]))

        demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_cb_idx,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Time dimension with windows
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        time_cb_idx = routing.RegisterTransitCallback(time_callback)
        # Allow waiting time, max time 24h per vehicle
        routing.AddDimension(
            time_cb_idx,
            30 * 60,  # allow waiting slack
            24 * 60,  # maximum time per vehicle
            False,
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")
        # Set time windows
        for node_idx in range(n_nodes):
            if node_idx == 0:
                for v in range(num_vehicles):
                    time_dimension.CumulVar(routing.Start(v)).SetRange(time_windows[node_idx][0], time_windows[node_idx][1])
            else:
                index = manager.NodeToIndex(node_idx)
                time_dimension.CumulVar(index).SetRange(time_windows[node_idx][0], time_windows[node_idx][1])

        # For depot, set start windows
        for v in range(num_vehicles):
            start_index = routing.Start(v)
            time_dimension.CumulVar(start_index).SetRange(time_windows[0][0], time_windows[0][1])
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(v)))

        # Search params
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.FromSeconds(int(max(1, time_limit_secs)))
        # Log disabled
        search_params.log_search = False

        try:
            solution = routing.SolveWithParameters(search_params)
        except Exception:
            return None

        if solution is None:
            return None

        # Extract routes
        routes: List[Dict[str, Any]] = []
        total_km = 0.0
        total_eta = 0
        fleet_used: List[str] = []

        for v in range(num_vehicles):
            index = routing.Start(v)
            route_nodes: List[int] = []
            route_distance_m = 0
            route_time_min = 0
            prev_index = index
            # Follow path
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_nodes.append(node)
                next_index = solution.Value(routing.NextVar(index))
                if not routing.IsEnd(next_index):
                    from_n = manager.IndexToNode(index)
                    to_n = manager.IndexToNode(next_index)
                    route_distance_m += dist_matrix[from_n][to_n]
                    route_time_min += time_matrix[from_n][to_n]
                index = next_index
                if len(route_nodes) > n_nodes + 5:  # guard infinite loop
                    break

            if len(route_nodes) <= 1:  # only depot, no deliveries
                continue

            # Build waypoints for this vehicle
            waypoints: List[List[float]] = [all_coords[n] for n in route_nodes]
            # For display, add depot return? Not needed; keep as path
            # Distance in km
            d_km = round(route_distance_m / 1000.0, 2)
            # ETA: route_time includes service; use time_dimension cumul at end
            # Use route_time_min as eta (includes service)
            van = fleet[v % len(fleet)]
            # Map vehicle tier via capacity -> select_vehicle logic for consistent naming
            # Use first dropoff distance to estimate tier? Use max distance in route
            max_leg_km = 0.0
            for a, b in zip(route_nodes, route_nodes[1:]):
                leg = haversine_km(all_coords[a][0], all_coords[a][1], all_coords[b][0], all_coords[b][1])
                max_leg_km = max(max_leg_km, leg)
            # Weight for vehicle selection: sum demands on this route
            route_weight = sum(dropoff_demands[n-1] for n in route_nodes if n != 0)
            # Check if any pickup cold_chain_mandatory
            cold_mandatory = any(p.get("cold_chain_mandatory") for p in pickup_nodes)
            sel = self.select_vehicle(route_weight, max_leg_km if max_leg_km else d_km, cold_mandatory)

            fleet_used.append(van.get("id", f"veh-{v}"))
            total_km += d_km
            total_eta += route_time_min

            routes.append({
                "vehicle_id": van.get("id", f"veh-{v}"),
                "vehicle_name": van.get("name", sel["vehicle_name"]),
                "tier": sel["tier"],
                "reefer": sel["reefer"],
                "target_temp_c": 2.7 if cold_mandatory else (4.0 if sel["reefer"] else 12.0),
                "distance_km": d_km,
                "eta_minutes": route_time_min,
                "waypoints": waypoints,
                "nodes": route_nodes,
                "dropoff_ids": [dropoff_ids[n-1] for n in route_nodes if n != 0],
                "weight_kg": round(route_weight, 1),
                "origin": depot_coords,
                "destination": waypoints[-1] if len(waypoints) > 1 else depot_coords,
            })

        if not routes:
            return None

        return {
            "routes": routes,
            "total_distance_km": round(total_km, 2),
            "total_eta_minutes": total_eta,
            "fleet_used": fleet_used,
            "solver": f"ortools-routing-vrpTW-lambda{lambda_penalty}",
            "num_vehicles": num_vehicles,
            "objective_with_lambda": True,
        }
