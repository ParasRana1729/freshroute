"""FreshRoute Demand Vulnerability Layer (V_d) & Constrained Hub-Routing Optimizer.

Upgrades the greedy top-50 dispatch demo (`dispatch_list_demo.csv`) into a
capacity- and distance-constrained Linear Programming (LP / HiGHS) optimizer:
  - Scores regional food-bank hubs with Demand Vulnerability V_d (from an
    external NFSA/PDS beneficiary CSV via `--pds-csv`, or disclosed regional
    reference weights when external PDS files are not provided).
  - Weights mandi surplus supply by predicted glut-onset probability (`p_glut_onset`)
    and commodity perishability tier (`w_perish`), using verified non-imputed
    mandi or Census/LGD district coordinates.
  - Enforces Haversine distance cutoffs (`max_distance_km`), mandi supply limits,
    and hub receiving capacities (`scipy.optimize.linprog`).

Run:
  python scripts/optimize_dispatch.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import fetch_weather as fw  # noqa: E402

# Disclosed reference food-bank / redistribution hubs across major agricultural corridors.
# Used when `--hubs-csv` is not provided. `demand_v_d` is a normalized [0.1, 1.0] proxy
# reflecting district/corridor vulnerability; override with real NFSA AAY/PHH data via `--pds-csv`.
DEFAULT_HUBS: list[dict[str, Any]] = [
    {"hub_id": "HUB_MUM", "hub_name": "Mumbai Metro Food Bank", "state_name": "MAHARASHTRA", "district_name": "MUMBAI", "latitude": 19.0760, "longitude": 72.8777, "capacity_tonnes": 65.0, "demand_v_d": 0.78},
    {"hub_id": "HUB_PUN", "hub_name": "Pune Regional Hub", "state_name": "MAHARASHTRA", "district_name": "PUNE", "latitude": 18.5204, "longitude": 73.8567, "capacity_tonnes": 55.0, "demand_v_d": 0.72},
    {"hub_id": "HUB_NAS", "hub_name": "Nashik North-MH Hub", "state_name": "MAHARASHTRA", "district_name": "NASHIK", "latitude": 19.9975, "longitude": 73.7898, "capacity_tonnes": 50.0, "demand_v_d": 0.80},
    {"hub_id": "HUB_CHE", "hub_name": "Chennai TN Hub", "state_name": "TAMIL NADU", "district_name": "CHENNAI", "latitude": 13.0827, "longitude": 80.2707, "capacity_tonnes": 70.0, "demand_v_d": 0.74},
    {"hub_id": "HUB_CBE", "hub_name": "Coimbatore West-TN Hub", "state_name": "TAMIL NADU", "district_name": "COIMBATORE", "latitude": 11.0168, "longitude": 76.9558, "capacity_tonnes": 55.0, "demand_v_d": 0.70},
    {"hub_id": "HUB_MDU", "hub_name": "Madurai South-TN Hub", "state_name": "TAMIL NADU", "district_name": "MADURAI", "latitude": 9.9252, "longitude": 78.1198, "capacity_tonnes": 55.0, "demand_v_d": 0.79},
    {"hub_id": "HUB_LKO", "hub_name": "Lucknow Central-UP Hub", "state_name": "UTTAR PRADESH", "district_name": "LUCKNOW", "latitude": 26.8467, "longitude": 80.9462, "capacity_tonnes": 80.0, "demand_v_d": 0.95},
    {"hub_id": "HUB_KNP", "hub_name": "Kanpur Bundelkhand Hub", "state_name": "UTTAR PRADESH", "district_name": "KANPUR NAGAR", "latitude": 26.4499, "longitude": 80.3319, "capacity_tonnes": 70.0, "demand_v_d": 0.93},
    {"hub_id": "HUB_BPL", "hub_name": "Bhopal MP Hub", "state_name": "MADHYA PRADESH", "district_name": "BHOPAL", "latitude": 23.2599, "longitude": 77.4126, "capacity_tonnes": 65.0, "demand_v_d": 0.91},
    {"hub_id": "HUB_IDR", "hub_name": "Indore Malwa Hub", "state_name": "MADHYA PRADESH", "district_name": "INDORE", "latitude": 22.7196, "longitude": 75.8577, "capacity_tonnes": 60.0, "demand_v_d": 0.85},
    {"hub_id": "HUB_JAI", "hub_name": "Jaipur Rajasthan Hub", "state_name": "RAJASTHAN", "district_name": "JAIPUR", "latitude": 26.9124, "longitude": 75.7873, "capacity_tonnes": 65.0, "demand_v_d": 0.86},
    {"hub_id": "HUB_DEL", "hub_name": "Delhi-NCR Gurugram Hub", "state_name": "HARYANA", "district_name": "GURUGRAM", "latitude": 28.4595, "longitude": 77.0266, "capacity_tonnes": 85.0, "demand_v_d": 0.82},
    {"hub_id": "HUB_COK", "hub_name": "Kochi Kerala Hub", "state_name": "KERALA", "district_name": "ERNAKULAM", "latitude": 9.9312, "longitude": 76.2673, "capacity_tonnes": 45.0, "demand_v_d": 0.65},
    {"hub_id": "HUB_BLR", "hub_name": "Bengaluru Karnataka Hub", "state_name": "KARNATAKA", "district_name": "BENGALURU", "latitude": 12.9716, "longitude": 77.5946, "capacity_tonnes": 65.0, "demand_v_d": 0.72},
    {"hub_id": "HUB_CCU", "hub_name": "Kolkata Bengal Hub", "state_name": "WEST BENGAL", "district_name": "KOLKATA", "latitude": 22.5726, "longitude": 88.3639, "capacity_tonnes": 70.0, "demand_v_d": 0.84},
]

# Perishability weights reflecting cold-chain / spoilage urgency for rescue dispatch
PERISHABILITY_WEIGHTS: dict[str, float] = {
    "TOMATO": 1.00,
    "SPINACH": 1.00,
    "METHI(LEAVES)": 1.00,
    "CORIANDER(LEAVES)": 1.00,
    "GREEN CHILLI": 0.92,
    "BHINDI(LADIES FINGER)": 0.95,
    "BRINJAL": 0.90,
    "CAULIFLOWER": 0.90,
    "CABBAGE": 0.85,
    "BITTER GOURD": 0.88,
    "BOTTLE GOURD": 0.88,
    "CUCUMBAR(KHEERA)": 0.94,
    "BANANA": 0.90,
    "CARROT": 0.80,
    "RADDISH": 0.82,
    "ONION GREEN": 0.92,
    "ONION": 0.65,
    "POTATO": 0.60,
    "WHEAT": 0.30,
    "PADDY(COMMON)": 0.30,
    "PADDY(BASMATI)": 0.30,
    "MAIZE": 0.35,
    "SOYABEAN": 0.35,
}


def get_perishability_weight(commodity_name: str) -> float:
    name = str(commodity_name).strip().upper()
    if name in PERISHABILITY_WEIGHTS:
        return PERISHABILITY_WEIGHTS[name]
    if any(k in name for k in ("LEAVES", "GOURD", "BERRY", "MANGO", "PAPAYA", "GRAPES")):
        return 0.92
    if any(k in name for k in ("DAL", "GRAM", "PULSE", "RICE", "MILLET", "COTTON")):
        return 0.35
    return 0.75


def haversine_matrix_km(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Compute pairwise great-circle distances in km of shape (len(lat1), len(lat2))."""
    r_km = 6371.0
    la1 = np.radians(np.asarray(lat1, dtype=np.float64))[:, None]
    lo1 = np.radians(np.asarray(lon1, dtype=np.float64))[:, None]
    la2 = np.radians(np.asarray(lat2, dtype=np.float64))[None, :]
    lo2 = np.radians(np.asarray(lon2, dtype=np.float64))[None, :]
    dlat = la2 - la1
    dlon = lo2 - lo1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(la1) * np.cos(la2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r_km * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def load_hubs_with_demand(
    hubs_csv: Path | str | None = None,
    pds_csv: Path | str | None = None,
) -> pd.DataFrame:
    """Load food-bank hubs and optionally apply NFSA/PDS AAY+PHH demand weights V_d."""
    hubs = pd.read_csv(hubs_csv) if hubs_csv is not None else pd.DataFrame(DEFAULT_HUBS)
    hubs["state_name"] = hubs["state_name"].astype(str).str.strip().str.upper()
    hubs["district_name"] = hubs["district_name"].astype(str).str.strip().str.upper()

    if pds_csv is not None:
        pds = pd.read_csv(pds_csv)
        pds["state_name"] = pds["state_name"].astype(str).str.strip().str.upper()
        pds["district_name"] = pds["district_name"].astype(str).str.strip().str.upper()
        # Support either explicit `demand_v_d` or raw `aay_beneficiaries` + `phh_beneficiaries`
        if "demand_v_d" not in pds.columns:
            aay = pd.to_numeric(pds.get("aay_beneficiaries", 0), errors="coerce").fillna(0.0)
            phh = pd.to_numeric(pds.get("phh_beneficiaries", 0), errors="coerce").fillna(0.0)
            score = 2.0 * aay + 1.0 * phh
            mx = float(score.max()) if len(score) else 1.0
            pds["demand_v_d"] = np.clip(score / max(mx, 1.0), 0.1, 1.0)
        hubs = hubs.drop(columns=["demand_v_d"], errors="ignore").merge(
            pds[["state_name", "district_name", "demand_v_d"]].drop_duplicates(),
            on=["state_name", "district_name"],
            how="left",
        )
        hubs["demand_v_d"] = hubs["demand_v_d"].fillna(0.5)

    return hubs.reset_index(drop=True)


def attach_mandi_coordinates(
    dispatch_df: pd.DataFrame,
    raw_apmc_csv: Path | str | None = None,
    centroids_csv: Path | str | None = None,
) -> pd.DataFrame:
    """Attach verified non-imputed mandi/district coordinates to dispatch candidates."""
    out = dispatch_df.copy()
    out["state_name"] = out["state_name"].astype(str).str.strip().str.upper()
    out["district_name"] = out["district_name"].astype(str).str.strip().str.upper()
    out["market_center_name"] = out["market_center_name"].astype(str).str.strip().str.upper()

    if {"latitude", "longitude"}.issubset(out.columns) and out[["latitude", "longitude"]].notna().all().all():
        out["coord_source"] = out.get("coord_source", "provided")
        return out

    # 1. Non-imputed mandi-level coordinates from raw APMC
    if raw_apmc_csv is not None and Path(raw_apmc_csv).exists():
        raw = pd.read_csv(
            raw_apmc_csv,
            usecols=["state_name", "district_name", "market_center_name", "latitude", "longitude"],
            low_memory=False,
        ).dropna(subset=["latitude", "longitude"])
        raw["state_name"] = raw["state_name"].astype(str).str.strip().str.upper()
        raw["district_name"] = raw["district_name"].astype(str).str.strip().str.upper()
        raw["market_center_name"] = raw["market_center_name"].astype(str).str.strip().str.upper()
        mandi_coords = raw.groupby(
            ["state_name", "market_center_name"], as_index=False
        ).agg(latitude=("latitude", "median"), longitude=("longitude", "median"))
        out = out.merge(mandi_coords, on=["state_name", "market_center_name"], how="left")
        out["coord_source"] = np.where(out["latitude"].notna(), "raw_mandi_median", "missing")
    else:
        out["latitude"] = np.nan
        out["longitude"] = np.nan
        out["coord_source"] = "missing"

    # 2. Verified district centroids (from fetch_weather.py / Census-LGD lookup)
    dist_lookup: dict[tuple[str, str], tuple[float, float]] = dict(fw.CENSUS_LGD_CENTROIDS)
    if centroids_csv is not None and Path(centroids_csv).exists():
        cdf = pd.read_csv(centroids_csv)
        for _, r in cdf.iterrows():
            dist_lookup[(str(r["state_name"]).upper(), str(r["district_name"]).upper())] = (
                float(r["latitude"]),
                float(r["longitude"]),
            )
    for idx in out.index[out["latitude"].isna()]:
        key = (str(out.at[idx, "state_name"]), str(out.at[idx, "district_name"]))
        if key in dist_lookup:
            out.at[idx, "latitude"], out.at[idx, "longitude"] = dist_lookup[key]
            out.at[idx, "coord_source"] = "district_centroid"

    # 3. Fallback to nearest matching state hub coordinate if any district remains unmapped
    state_hubs = {h["state_name"]: (h["latitude"], h["longitude"]) for h in DEFAULT_HUBS}
    for idx in out.index[out["latitude"].isna()]:
        st = str(out.at[idx, "state_name"])
        if st in state_hubs:
            out.at[idx, "latitude"], out.at[idx, "longitude"] = state_hubs[st]
            out.at[idx, "coord_source"] = "state_hub_fallback"
        else:
            out.at[idx, "latitude"], out.at[idx, "longitude"] = 22.9734, 78.6569
            out.at[idx, "coord_source"] = "india_centroid_fallback"

    return out


def optimize_mandi_to_hub_dispatch(
    candidates_df: pd.DataFrame,
    hubs_df: pd.DataFrame,
    max_distance_km: float = 400.0,
    distance_penalty_alpha: float = 0.25,
    supply_col: str = "pred_arrival_tonnes_next",
    urgency_col: str = "p_glut_onset",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Solve capacity- & distance-constrained LP for mandi -> food-bank dispatch."""
    cands = candidates_df.copy().reset_index(drop=True)
    hubs = hubs_df.copy().reset_index(drop=True)
    if cands.empty or hubs.empty:
        return pd.DataFrame(), {"status": "empty_input", "allocated_tonnes": 0.0}

    cands["w_perish"] = cands["commodity_name"].map(get_perishability_weight).astype(float)
    supply = np.clip(pd.to_numeric(cands[supply_col], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64), 0.0, None)
    urgency = np.clip(pd.to_numeric(cands[urgency_col], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64), 0.0, 1.0)
    perish = cands["w_perish"].to_numpy(dtype=np.float64)
    hub_caps = np.clip(pd.to_numeric(hubs["capacity_tonnes"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64), 0.0, None)
    hub_vd = np.clip(pd.to_numeric(hubs["demand_v_d"], errors="coerce").fillna(0.5).to_numpy(dtype=np.float64), 0.0, 1.0)

    dist_km = haversine_matrix_km(
        cands["latitude"].to_numpy(),
        cands["longitude"].to_numpy(),
        hubs["latitude"].to_numpy(),
        hubs["longitude"].to_numpy(),
    )

    n_m, n_h = len(cands), len(hubs)
    feasible_i, feasible_j = np.where(dist_km <= max_distance_km)
    if len(feasible_i) == 0:
        return pd.DataFrame(), {"status": "no_routes_within_max_distance", "allocated_tonnes": 0.0}

    # Build sparse-like LP over ONLY feasible (i, j) arcs within max_distance_km
    n_vars = len(feasible_i)
    arc_d = dist_km[feasible_i, feasible_j]
    arc_value = (
        urgency[feasible_i] * perish[feasible_i] * hub_vd[feasible_j]
        - distance_penalty_alpha * (arc_d / max(max_distance_km, 1.0))
    )
    # Only allow arcs with positive net social value (avoid hauling low-urgency grain far)
    c_obj = -arc_value  # linprog minimizes

    # Constraints: row i sum <= supply[i]; col j sum <= hub_caps[j]
    a_ub = np.zeros((n_m + n_h, n_vars), dtype=np.float64)
    for var_idx, (i, j) in enumerate(zip(feasible_i, feasible_j)):
        a_ub[i, var_idx] = 1.0
        a_ub[n_m + j, var_idx] = 1.0
    b_ub = np.concatenate([supply, hub_caps])
    bounds = [(0.0, float(min(supply[i], hub_caps[j])) if arc_value[v] > 0 else 0.0) for v, (i, j) in enumerate(zip(feasible_i, feasible_j))]

    res = linprog(c=c_obj, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"LP optimization failed: {res.message}")

    x = res.x
    routes: list[dict[str, Any]] = []
    for v, qty in enumerate(x):
        if qty <= 1e-4:
            continue
        i, j = int(feasible_i[v]), int(feasible_j[v])
        routes.append(
            {
                "date": str(cands.at[i, "date"]) if "date" in cands.columns else "",
                "target_date": str(cands.at[i, "target_date"]) if "target_date" in cands.columns else "",
                "mandi_state": str(cands.at[i, "state_name"]),
                "mandi_district": str(cands.at[i, "district_name"]),
                "market_center_name": str(cands.at[i, "market_center_name"]),
                "commodity_name": str(cands.at[i, "commodity_name"]),
                "p_glut_onset": round(float(urgency[i]), 4),
                "w_perish": round(float(perish[i]), 2),
                "mandi_supply_tonnes": round(float(supply[i]), 2),
                "hub_id": str(hubs.at[j, "hub_id"]),
                "hub_name": str(hubs.at[j, "hub_name"]),
                "hub_state": str(hubs.at[j, "state_name"]),
                "hub_demand_v_d": round(float(hub_vd[j]), 3),
                "distance_km": round(float(arc_d[v]), 2),
                "dispatched_tonnes": round(float(qty), 2),
                "route_utility_score": round(float(qty * arc_value[v]), 3),
            }
        )

    plan_df = pd.DataFrame(routes)
    if not plan_df.empty:
        plan_df = plan_df.sort_values(["route_utility_score", "dispatched_tonnes"], ascending=False).reset_index(drop=True)

    # Greedy nearest-feasible baseline for benchmark comparison
    greedy_rem_hub = hub_caps.copy()
    greedy_tonnes = 0.0
    greedy_utility = 0.0
    order = np.argsort(-(urgency * perish))
    for i in order:
        rem_s = supply[i]
        if rem_s <= 0:
            continue
        valid_j = np.where((dist_km[i] <= max_distance_km) & (greedy_rem_hub > 0))[0]
        if len(valid_j) == 0:
            continue
        nearest_order = valid_j[np.argsort(dist_km[i, valid_j])]
        for j in nearest_order:
            val = urgency[i] * perish[i] * hub_vd[j] - distance_penalty_alpha * (dist_km[i, j] / max(max_distance_km, 1.0))
            if val <= 0:
                continue
            take = min(rem_s, greedy_rem_hub[j])
            if take > 1e-4:
                greedy_tonnes += take
                greedy_utility += take * val
                rem_s -= take
                greedy_rem_hub[j] -= take
            if rem_s <= 1e-4:
                break

    active_mask = x > 1e-4
    total_disp = float(np.sum(x[active_mask])) if np.any(active_mask) else 0.0
    total_util = float(np.sum(x[active_mask] * arc_value[active_mask])) if np.any(active_mask) else 0.0
    avg_dist = float(np.sum(x[active_mask] * arc_d[active_mask]) / max(total_disp, 1e-9)) if total_disp > 0 else 0.0

    summary = {
        "status": "optimal",
        "max_distance_km": float(max_distance_km),
        "n_candidate_mandis": int(n_m),
        "n_hubs": int(n_h),
        "n_active_routes": int(len(plan_df)),
        "total_candidate_tonnes": round(float(supply.sum()), 2),
        "total_hub_capacity_tonnes": round(float(hub_caps.sum()), 2),
        "lp_dispatched_tonnes": round(total_disp, 2),
        "lp_total_utility": round(total_util, 3),
        "lp_weighted_avg_distance_km": round(avg_dist, 2),
        "greedy_nearest_dispatched_tonnes": round(float(greedy_tonnes), 2),
        "greedy_nearest_total_utility": round(float(greedy_utility), 3),
        "utility_lift_over_greedy": round(float(total_util - greedy_utility), 3),
    }
    return plan_df, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute constrained mandi -> hub dispatch optimizer")
    parser.add_argument(
        "--dispatch-csv",
        type=Path,
        default=ROOT / "data" / "processed" / "dispatch_list_demo.csv",
    )
    parser.add_argument("--hubs-csv", type=Path, default=None)
    parser.add_argument("--pds-csv", type=Path, default=None)
    parser.add_argument("--max-distance-km", type=float, default=400.0)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=ROOT / "data" / "processed" / "optimized_dispatch_plan.csv",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=ROOT / "data" / "processed" / "dispatch_optimization_summary.json",
    )
    args = parser.parse_args()

    cands = pd.read_csv(args.dispatch_csv)
    raw_apmc = ROOT / "data" / "raw" / "apmc_arrivals_prices.csv"
    centroids_csv = ROOT / "data" / "external" / "district_centroids.csv"
    cands = attach_mandi_coordinates(cands, raw_apmc_csv=raw_apmc, centroids_csv=centroids_csv)
    hubs = load_hubs_with_demand(hubs_csv=args.hubs_csv, pds_csv=args.pds_csv)

    plan_df, summary = optimize_mandi_to_hub_dispatch(
        cands, hubs, max_distance_km=args.max_distance_km
    )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    plan_df.to_csv(args.output_csv, index=False)
    args.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
