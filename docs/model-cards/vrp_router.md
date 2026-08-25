# Model Card: VRPRouter (Stage 4) — VRPTW

> Stage 4 `core/vrp_router.py:63` — see `docs/model-cards/TEMPLATE.md` and spec §3.1–3.2.

**Version:** v1.1.0-P5  **Date:** 2026-08-26  **MLflow Run:** ` TBD after P5 benchmark`
**Owners:** FreshRoute AI Core  **Reviewers:** pending outer gate
**DOI:** `10.5281/zenodo.XXXXXXX` (to be minted P5)
**BibTeX keys:** `[@toth2014vrp; @solomon1987; @orgtoolsvrp2024; @dantzig1959truck; @tataaceevspec; @ashokleylandspec]`

---

## 1. Model Details

- **Vehicle tiering (spec §3.1):** 4 tiers — Cargo E-Rickshaw 500kg/8km/18kmh (non-reefer), Tata Ace EV 1000kg/30km/30kmh (reefer) [@tataaceevspec], Reefer Sprinter 1500kg/80km/45kmh [@ashokleylandspec], Heavy Reefer 4000kg/250km/55kmh. Selection `select_vehicle:82` picks smallest feasible tier fulfilling weight, distance, and `cold_chain_mandatory` (from Stage 1).
- **Fleet mock:** 4 vans mirroring `src/data/mockData.js` INITIAL_FLEET (Tata Ace EV PB-10-CZ-8821, Ashok Leyland PB-02-AK-4412, Mahindra PB-11-BT-9034, Eicher PB-65-AX-1288).
- **Objective (spec §3.2:162):** `min Σ c_uw x_uvw + λ Σ t_delivery(i)/t_safe(i)` with `λ ∈ [0.5,5]` (default 2.0) — distance cost + perishability penalty (weighted time). `λ` grid tuning via benchmark.
- **Solver paths:**
  - **Heuristic** `plan_route:134` / `solve_vrp:182` (default) — haversine distance, speed-based ETA (+1.35× for NH44 Phagwara congestion, `src/App.jsx:189`), tier assignment. p95 <5ms.
  - **OR-Tools VRPTW** `_solve_vrp_ortools:269` — `RoutingModel` with distance matrix (haversine, meters) + time matrix (minutes, service 10min), capacity dimension (kg), time windows `[0, t_safe*60]` (derived from `t_safe_hours` or `cold_chain_mandatory` → 4h/12h), objective `distance + λ*time*100`. Uses `PATH_CHEAPEST_ARC` + `GUIDED_LOCAL_SEARCH`, `time_limit_secs` default 2.0 (spec §9.1 <2s for 50 nodes). Fallback to heuristic on failure/infeasibility.
- **Distance prior:** haversine [@toth2014vrp]; live OSRM via D3 `osm2024`/`osrm2024` reserved for P1 L1.3 (precomputed Punjab donor↔recipient matrix).
- **Inputs:** `pickup_nodes` (with `origin_coordinates`, `gross_weight_kg`, `cold_chain_mandatory`), `dropoff_nodes` (with `coordinates`), `fleet_available`, `t_safe_hours` list, `lambda_penalty`, `time_limit_secs`, `traffic_congestion`.
- **Outputs:** `routes` (per-vehicle `distance_km, eta_minutes, vehicle_id, tier, reefer, target_temp_c, waypoints, dropoff_ids, weight_kg`), `total_distance_km`, `total_eta_minutes`, `fleet_used`, `solver`.

## 2. Intended Use

- Primary: `POST /api/v1/optimize/routing` — multi-stop cold-chain dispatch after Stage 3 matching. Supports single pickup→drop and multi-pickup/multi-drop GT corridor (Ludhiana→Amritsar ~118km haversine, 130km road).
- Users: Driver app, dispatcher console.
- Out-of-scope: Not for frozen retail (<0°C) or when `t_safe` < transit+buffer — then `CRITICAL_HAZARD` without reefer returns 422 at matcher; router not invoked. Not validated for hill terrain (Pathankot) beyond flat Punjab.

## 3. Factors

- Cold-chain mandatory (from `ThermalDecayEngine`): forces reefer tier, tight time window 4h (CRITICAL_HAZARD) vs 12h (ELEVATED_RISK) vs 24h (SAFE).
- Weight & distance: tier matrix thresholds; capacity dimension enforces `Σ demand ≤ vehicle_capacity`.
- Traffic: NH44 congestion flag (Phagwara bypass) multiplies time by 1.35 (spec simulation).
- Weather: `Phi_env` not directly in router but `t_safe` already encodes temp/humidity; future `t_delivery/t_safe` weighting via `λ`.

## 4. Metrics

| Metric | Heuristic | OR-Tools VRPTW | Target | Dataset |
| :--- | :--- | :--- | :--- | :--- |
| Single-route Ludhiana→Amritsar distance | 118.92km | 118.92km | — | mockData corridor |
| Multi-drop 4 stops total distance | — | 52.27km (one van, 900kg, 6h windows) | — | synthetic 4 dropoffs near Ludhiana |
| 3×3 (3 pickups 400kg → 3 drops) | — | 68.26km (one van, 1200kg) | — | synthetic |
| Capacity violation rate | 0 (per-leg) | 0 (dimension-enforced) | 0 | N=20–50 |
| Time-window feasibility | not enforced | enforced (0–4/12/24h) | 100% feasible routes within `t_safe` | tight-window test (1h far Delhi → fallback) |
| Latency p95 | <5ms | <500ms for 4 nodes, <1s for 20 nodes | <2s for 50 nodes (spec §9.1) | `time_limit_secs=2.0` |
| Cost vs nearest-neighbor | — | ≥15% improvement expected after λ tuning (Toth & Vigo) | — | Solomon benchmark pending P5 L5.2 |

- **Cold-chain compliance Tier 1:** 100% when `cold_chain_mandatory` → reefer (target 2.7°C spec example).
- **CO₂:** not in router but `pareto_matcher` `co2_saved_kg = weight*2.5` aggregated per route.

## 5. Evaluation Data

- **Datasheets:** `punjab_districts.json` (23 districts, HVI), `indian_commodities.json` (tier `critical_temp_c`), OSM Punjab extract (future, ODbL), OSRM truck profile.
- **Benchmarks:** Solomon VRPTW instances [@solomon1987] (time-window feasibility), NH44 corridor manual distances (haversine vs road +7–10%).
- **Split:** Simulation replay of L1.3 distance matrix; no leakage.

## 6. Training Data

- No ML training; deterministic OR heuristics + OR-Tools search. `λ` tuning grid `[0.5,5]` via manual benchmark (future MLflow).
- Fleet specs from OEM datasheets (Tata, Ashok Leyland) cited.

## 7. Quantitative Analyses (Ablations)

- Without time windows vs with `t_safe` 4h/12h: on-time delivery within `t_safe` improves but distance may increase (trade-off via `λ`).
- `λ=0` (pure distance) vs `λ=2` (spec default) vs `λ=5` (aggressive perishability): higher `λ` prioritizes urgent `t_safe` small deliveries, may increase total km.
- Heuristic 1:1 pairing vs OR-Tools multi-stop: multi-stop reduces total km when total weight fits single vehicle (e.g., 900kg across 4 drops: heuristic would be 4× direct ~200km, OR-Tools 52km).
- Reefer vs non-reefer tier selection: cold_chain_mandatory forces reefer even for 100kg short hop (e.g., E-Rickshaw not allowed).

## 8. Ethical Considerations

- **Equity:** Router does not reorder by HVI — that is Stage 3 matcher’s job; router only optimizes feasible routes, avoiding “nearest-rich” bias carryover.
- **Safety:** `CRITICAL_HAZARD` without reefer is hard-blocked at matcher, so router never plans unrefrigerated dairy in Loo.
- **Driver autonomy:** ETA includes traffic flag; driver can override via manual `traffic_congestion` hint.

## 9. Caveats & Recommendations

- **Haversine vs road:** current distance is great-circle; road distance ~1.1–1.3× haversine in rural Malwa; OSRM live matrix (P1 L1.3) will improve.
- **Speed uniform:** time matrix uses avg 35kmh; per-vehicle speed not yet per-leg; future: per-tier speed in time callback.
- **PDP not yet:** pickup-and-delivery precedence (each batch’s pickup before its delivery) simplified to depot+deliveries; true PDP with multiple distinct pickup markets (mandis) pending P5 L5.2.
- **Infeasibility fallback:** OR-Tools returns `None` when no feasible time-window tour (e.g., far Delhi 290km with 1h window) → heuristic fallback ignores window; caller should check `t_safe` vs `eta_minutes` and flag `cold_chain_enforced` breach.
- **Citation debt:** all numeric tiers, speeds, `λ` range, thresholds cite `BIBLIOGRAPHY.bib` or `docs/calibration/`.
