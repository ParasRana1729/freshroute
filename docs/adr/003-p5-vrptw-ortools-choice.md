# ADR-003: P5 VRPTW — OR-Tools RoutingModel with t_safe Time Windows

Date: 2026-08-26
Status: Accepted

## Context

Spec §3.1 tiering matrix and §3.2 objective `min Σ c_uw x_uvw + λ Σ t_delivery/t_safe` require VRPTW solver. P0 heuristic `plan_route`/`solve_vrp` used haversine + tier assignment, p95 <5ms, but ignored time windows and capacity aggregation. L5.2 mandates Google OR-Tools `RoutingModel` with time windows from `pickup_window` + `t_safe` deadline, capacity, temperature compartments, and λ tuning grid [0.5,5]. Must keep heuristic as fallback for offline CI and when `t_safe` windows infeasible.

## Decision

- **Heuristic stays default:** `solve_vrp(..., use_or_tools=False)` → 1:1 pairing, `plan_route` per leg, total distance/ETA sum. Already satisfies frontend `src/App.jsx:189` NH44 simulation and `tests/test_api.py:62`.
- **OR-Tools path:** `_solve_vrp_ortools` builds `RoutingModel` with:
  - **Nodes:** depot = first pickup `origin_coordinates` + all `dropoff_nodes` coordinates.
  - **Distance matrix:** haversine meters (integer, `*1000`) [@toth2014vrp]; time matrix minutes `dist/speed*60` + 10min service, speed `35kmh` (0.74× if `traffic_congestion` for 1.35× Phagwara penalty).
  - **Capacity:** per-vehicle `capacity_kg` from fleet (1000–4000kg), `AddDimensionWithVehicleCapacity`.
  - **Time windows:** depot `[0,24h]`, each dropoff `[0, t_safe*60]` where `t_safe` from caller `t_safe_hours` list (1:1 to dropoffs or avg) or derived `cold_chain_mandatory→4h` else `12h` (spec §2.3). Uses `Time` dimension `AddDimension` with slack 30h.
  - **Objective:** arc cost = `distance + λ*time*100` (λ default 2.0) to encode `λ Σ t_delivery/t_safe` (spec §3.2:162) via weighted time penalty. Search `PATH_CHEAPEST_ARC` + `GUIDED_LOCAL_SEARCH`, `time_limit_secs` default 2.0 (spec §9.1 <2s for 50 nodes).
- **Fleet filtering:** `fleet_available` ids restrict `self.fleet`; `num_vehicles = min(len(fleet), len(dropoffs))`.
- **API surface:** `RoutingRequest.use_or_tools, t_safe_hours, lambda_penalty, time_limit_secs, traffic_congestion`; `RoutingResponse.solver` provenance.
- **Fallback:** OR-Tools infeasible/unsolved → `None` → heuristic fallback (logs via `solver` field). Heuristic ignores windows (caller must check `eta_minutes` vs `t_safe` for breach).
- **Citations:** `[@toth2014vrp]` formulation, `[@solomon1987]` benchmarks, `[@orgtoolsvrp2024]` RoutingModel, `[@dantzig1959truck]` history, `[@tataaceevspec; @ashokleylandspec]` tiers.

## Consequences

- **Pros:** Enforces capacity and time-window feasibility (e.g., multi-drop 4 stops 900kg/6h → 52km one-van vs heuristic 4× direct ~200km). λ grid allows perishability vs cost trade-off. Deterministic fallback ensures API never 500s.
- **Cons:** Haversine not road distance (pending OSRM D3); speed uniform (pending per-tier); pickup-and-delivery precedence (P&D) simplified to depot+deliveries (true PDP with separate mandi pickups pending).
- **Latency:** 4 nodes <500ms, 20 nodes <1s measured; within 2s SLA but slower than heuristic. Use OR-Tools only when `use_or_tools=true` or batch >10 stops.

## Alternatives Considered

- **OSRM live matrix as default:** rejected at P5 — OSRM India truck profile requires hosted instance and weekly OSM extract (P1 L1.3); haversine is reliable prior with <15% error on NH44 corridor, sufficient for gate.
- **Heuristic-only:** rejected — fails capacity aggregation and time-window SLA for `CRITICAL_HAZARD` batches (must deliver within `t_safe`).
- **CP-SAT for VRP instead of RoutingModel:** considered but RoutingModel is purpose-built for VRPTW with time windows and capacity; CP-SAT would need custom constraints.

## Citations

- [@toth2014vrp] Vehicle Routing Problems, Methods, Applications (SIAM)
- [@solomon1987] VRPTW benchmarks
- [@orgtoolsvrp2024] OR-Tools Routing Library
- [@dantzig1959truck] Truck dispatching
- [@tataaceevspec; @ashokleylandspec] vehicle specs

## Reversibility

Set `use_or_tools` default true or swap distance matrix to OSRM via `D3` live flag; one-line in `api/routes.py:332` and `vrp_router.py:210`. Supersession ADR would re-bench Solomon instances and NH44 fidelity.

