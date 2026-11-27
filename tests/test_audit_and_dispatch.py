"""Unit and integrity tests for calibration audit and constrained LP dispatch optimizer."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_model as am  # noqa: E402
from scripts import monitor_drift as md  # noqa: E402
from scripts import optimize_dispatch as od  # noqa: E402


def test_val_calibrators_and_ece_valid() -> None:
    rng = np.random.default_rng(42)
    y_val = rng.binomial(1, 0.1, size=500)
    p_val = np.clip(0.05 + 0.5 * y_val + rng.normal(0, 0.1, size=500), 0.01, 0.99)
    y_te = rng.binomial(1, 0.1, size=300)
    p_te = np.clip(0.05 + 0.5 * y_te + rng.normal(0, 0.1, size=300), 0.01, 0.99)

    cals = am.fit_val_calibrators(y_val, p_val)
    p_iso = am.apply_calibrator(cals["isotonic"], "isotonic", p_te)
    p_platt = am.apply_calibrator(cals["platt"], "platt", p_te)
    assert np.all((p_iso >= 0.0) & (p_iso <= 1.0))
    assert np.all((p_platt >= 0.0) & (p_platt <= 1.0))
    res = am.summarize_calibration(y_te, p_platt)
    assert 0.0 <= res["brier"] <= 1.0
    assert 0.0 <= res["ece"] <= 1.0


def test_haversine_known_mumbai_pune_distance() -> None:
    # Mumbai (19.0760, 72.8777) -> Pune (18.5204, 73.8567) ~ 118-125 km great-circle
    mat = od.haversine_matrix_km(
        np.array([19.0760]), np.array([72.8777]), np.array([18.5204]), np.array([73.8567])
    )
    assert mat.shape == (1, 1)
    assert 110.0 <= mat[0, 0] <= 130.0


def test_lp_optimizer_respects_supply_capacity_distance_and_beats_or_ties_greedy() -> None:
    cands = pd.DataFrame(
        [
            {
                "date": "2025-11-18",
                "target_date": "2025-11-19",
                "state_name": "MAHARASHTRA",
                "district_name": "PUNE",
                "market_center_name": "PUNE APMC",
                "commodity_name": "TOMATO",
                "pred_arrival_tonnes_next": 40.0,
                "p_glut_onset": 0.65,
                "latitude": 18.5204,
                "longitude": 73.8567,
            },
            {
                "date": "2025-11-18",
                "target_date": "2025-11-19",
                "state_name": "MAHARASHTRA",
                "district_name": "NASHIK",
                "market_center_name": "NASHIK APMC",
                "commodity_name": "ONION",
                "pred_arrival_tonnes_next": 50.0,
                "p_glut_onset": 0.60,
                "latitude": 19.9975,
                "longitude": 73.7898,
            },
            {
                "date": "2025-11-18",
                "target_date": "2025-11-19",
                "state_name": "ASSAM",
                "district_name": "GUWAHATI",
                "market_center_name": "FAR APMC",
                "commodity_name": "TOMATO",
                "pred_arrival_tonnes_next": 30.0,
                "p_glut_onset": 0.90,
                "latitude": 26.1445,
                "longitude": 91.7362,  # > 1500 km from MH hubs -> unreachable
            },
        ]
    )
    hubs = pd.DataFrame(
        [
            {
                "hub_id": "H1",
                "hub_name": "Pune Hub",
                "state_name": "MAHARASHTRA",
                "district_name": "PUNE",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "capacity_tonnes": 30.0,
                "demand_v_d": 0.60,
            },
            {
                "hub_id": "H2",
                "hub_name": "Mumbai Hub",
                "state_name": "MAHARASHTRA",
                "district_name": "MUMBAI",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "capacity_tonnes": 45.0,
                "demand_v_d": 0.95,
            },
        ]
    )

    plan_df, summary = od.optimize_mandi_to_hub_dispatch(cands, hubs, max_distance_km=250.0)
    assert summary["status"] == "optimal"
    assert not plan_df.empty
    # Far Assam mandi must never be dispatched
    assert "FAR APMC" not in set(plan_df["market_center_name"])
    # Distance cap respected
    assert (plan_df["distance_km"] <= 250.0).all()
    # Supply caps respected
    by_mandi = plan_df.groupby("market_center_name")["dispatched_tonnes"].sum()
    assert by_mandi.get("PUNE APMC", 0.0) <= 40.0 + 1e-4
    assert by_mandi.get("NASHIK APMC", 0.0) <= 50.0 + 1e-4
    # Hub capacity caps respected
    by_hub = plan_df.groupby("hub_id")["dispatched_tonnes"].sum()
    assert by_hub.get("H1", 0.0) <= 30.0 + 1e-4
    assert by_hub.get("H2", 0.0) <= 45.0 + 1e-4
    # LP utility >= greedy nearest utility
    assert summary["utility_lift_over_greedy"] >= -1e-4


def test_psi_and_feature_drift_detector() -> None:
    rng = np.random.default_rng(7)
    ref = pd.DataFrame({"f_stable": rng.normal(0.0, 1.0, 1000), "f_shifted": rng.normal(0.0, 1.0, 1000)})
    same = pd.DataFrame({"f_stable": rng.normal(0.0, 1.0, 1000), "f_shifted": rng.normal(3.0, 1.0, 1000)})

    psi_identical = md.compute_psi(ref["f_stable"].to_numpy(), ref["f_stable"].to_numpy())
    assert psi_identical == 0.0

    rows = md.compute_feature_drift(ref, same, ["f_stable", "f_shifted"])
    by_name = {r["feature"]: r for r in rows}
    assert by_name["f_stable"]["status"] == "stable"
    assert by_name["f_shifted"]["psi"] > 0.25
    assert by_name["f_shifted"]["status"] == "significant_shift"
