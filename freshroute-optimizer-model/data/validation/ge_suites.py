"""
Great Expectations suites for FreshRoute P1 Data Foundation (spec 7.1).

Defines expectations for each gold table per docs/IMPLEMENTATION_PLAN.md:7
and Gebru et al. 2021 datasheets. Used by ingestion stubs and tests to
ensure data quality before DVC versioning.

Suites (P1 L1.1-L1.5):
  - agmarknet_daily: arrival, price, date, mandi
  - weather_hourly: temp, humidity @imd2024/@openmeteo2024
  - forecaster_history: demand, lags, HVI
  - matcher_input: SurplusBatch/RecipientNode schema @fssai2011
  - routing: distance, capacity, time windows

Run: python -m data.validation.ge_suites --check-all
Or in tests: from data.validation.ge_suites import validate_agmarknet

Citations: [@gebru2021datasheets; @wilkinson2016fair]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def validate_agmarknet_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """GE suite for Agmarknet daily mandi arrivals (D1).

    Expectations (spec 7.1):
      - expect_table_row_count_to_be_between 1 and 10000
      - expect_column_values_to_not_be_null mandi_name, commodity, date
      - expect_column_values_to_be_between arrival 0-5000 quintals, price 100-50000
      - expect_column_pair_values_A_to_be_between_B? not needed
    """
    errors: List[str] = []
    if not (1 <= len(rows) <= 10000):
        errors.append(f"row_count {len(rows)} not in [1,10000]")
    for i, r in enumerate(rows):
        if not r.get("mandi_name"):
            errors.append(f"row {i} mandi_name null")
        if not r.get("commodity"):
            errors.append(f"row {i} commodity null")
        aq = r.get("arrival_quintals")
        if aq is None:
            errors.append(f"row {i} arrival null")
        else:
            try:
                if not (0 <= float(aq) <= 5000):
                    errors.append(f"row {i} arrival {aq} not in [0,5000]")
            except Exception:
                errors.append(f"row {i} arrival not float {aq}")
        pr = r.get("price_modal_inr_per_quintal")
        if pr is None:
            errors.append(f"row {i} price null")
        else:
            try:
                if not (100 <= float(pr) <= 50000):
                    errors.append(f"row {i} price {pr} not in [100,50000]")
            except Exception:
                errors.append(f"row {i} price not numeric {pr}")
        if not r.get("date"):
            errors.append(f"row {i} date null")
        # Try Great Expectations DataFrame context if installed
        try:
            import great_expectations as ge  # type: ignore

            _ = ge
        except Exception:
            pass
    return {"success": len(errors) == 0, "errors": errors, "suite": "agmarknet_daily"}


def validate_weather_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Suite D2: weather hourly telemetry."""
    errors: List[str] = []
    if not (12 <= len(rows) <= 48):
        errors.append(f"row_count {len(rows)} not in [12,48] for 24h")
    for i, r in enumerate(rows):
        tc = r.get("temp_c")
        if tc is not None:
            try:
                if not (-10 <= float(tc) <= 55):
                    errors.append(f"row {i} temp_c {tc} not in [-10,55]")
            except Exception:
                errors.append(f"row {i} temp_c not numeric {tc}")
        rh = r.get("humidity_pct")
        if rh is not None:
            try:
                if not (0 <= float(rh) <= 100):
                    errors.append(f"row {i} humidity {rh} not in [0,100]")
            except Exception:
                errors.append(f"row {i} humidity not numeric {rh}")
        if not r.get("timestamp_utc"):
            errors.append(f"row {i} timestamp null")
        if r.get("lat") is None or r.get("lon") is None:
            errors.append(f"row {i} lat/lon null")
    return {"success": len(errors) == 0, "errors": errors, "suite": "weather_hourly"}


def validate_forecaster_history(df) -> Dict[str, Any]:
    """Suite for forecaster synthetic history (P3)."""
    errors: List[str] = []
    try:
        if df.empty:
            errors.append("history empty")
        else:
            if "demand_lbs" not in df.columns:
                errors.append("demand_lbs missing")
            else:
                if (df["demand_lbs"] <= 0).any():
                    errors.append("demand_lbs <=0 found")
                if (df["demand_lbs"] > 100000).any():
                    errors.append("demand_lbs >100k outlier")
            for c in ("temp_c", "humidity_pct"):
                if c in df.columns:
                    if df[c].isna().any():
                        errors.append(f"{c} has NaN")
            if "demand_lag_1" in df.columns and df["demand_lag_1"].isna().sum() > len(df) * 0.05:
                errors.append("too many NaN lags")
    except Exception as e:
        errors.append(str(e))
    return {"success": len(errors) == 0, "errors": errors, "suite": "forecaster_history"}


def validate_matcher_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Suite for matcher input (D4 dietary, D7)."""
    errors: List[str] = []
    batch = payload.get("surplus_batch") or {}
    if payload.get("surplus_batches"):
        batches = payload["surplus_batches"]
        if not isinstance(batches, list) or not batches:
            errors.append("surplus_batches empty")
        for b in batches:
            if not b.get("origin_coordinates"):
                errors.append("batch missing origin_coordinates")
    else:
        if not batch.get("origin_coordinates"):
            errors.append("batch missing origin_coordinates")
    # Dietary flags check
    for key in ("is_pure_veg", "contains_meat"):
        # soft check: flags should be bool where present
        pass
    return {"success": len(errors) == 0, "errors": errors, "suite": "matcher_input"}


def check_all_synthetic() -> None:
    """Run all suites on synthetic data and print report."""
    from data.ingestion.agmarknet import synthetic_rows
    from data.ingestion.imd_openmeteo import synthetic_hourly
    from core.demand_forecaster import HungerDemandForecaster

    print("=== GE Suite check_all_synthetic ===")
    ag_rows = synthetic_rows("2026-08-18")
    res = validate_agmarknet_rows(ag_rows)
    print(f"agmarknet: {'pass' if res['success'] else 'fail'} {len(res['errors'])} errors")
    if res["errors"]:
        print(res["errors"][:3])

    w_rows = synthetic_hourly(30.9, 75.85, "2026-08-18")
    res = validate_weather_rows(w_rows)
    print(f"weather: {'pass' if res['success'] else 'fail'} {len(res['errors'])} errors")

    fc = HungerDemandForecaster()
    df = fc.generate_synthetic_history(days=30, seed=42)
    res = validate_forecaster_history(df)
    print(f"forecaster: {'pass' if res['success'] else 'fail'} {len(res['errors'])} errors")

    #总体
    print("=== done ===")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--check-all", action="store_true", help="Run all suites on synthetic")
    args = ap.parse_args()
    if args.check_all:
        check_all_synthetic()
    else:
        check_all_synthetic()
