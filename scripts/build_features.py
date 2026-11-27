"""FreshRoute Plan v3.1: Leak-Free Feature Engineering & Target Pairing (Phase 0-1).

Exposes decoupled, anti-leakage feature construction:
  1. load_config / load_cleaned_data (float32 numerics + category string IDs)
  2. Train-only per-commodity IQR winsorization (fit_train_iqr_bounds / apply_iqr_winsorization)
  3. 4-level state-qualified hierarchical shrinkage priors (fit_shrinkage_priors / apply_shrinkage_priors)
  4. Strictly <= t feature builder (build_features) retaining 100% of rows
  5. Exact (ENTITY_KEYS, date + 1 day) supervised target pairing & split (build_supervised_pairs)

Run standalone:
  python scripts/build_features.py
  python scripts/build_features.py --split-mode 11d_6d_4d
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "experiment_config.yaml"

ENTITY_KEYS: list[str] = [
    "state_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
]

FORBIDDEN_LEAKAGE_COLS: frozenset[str] = frozenset(
    {
        "price_z",
        "arrival_z",
        "surplus_S",
        "target_date",
        "next_date",
        "next_gap_days",
        "n_comm_day_next",
        "y_onset",
        "delta_log_arr",
        "log_arrival_next",
        "surplus_cs_next",
    }
)

FEATURE_COLS: list[str] = [
    # Geo
    "latitude",
    "longitude",
    "geo_missing",
    # Day-t winsorized levels & spread
    "arrival_tonnes",
    "price_per_kg",
    "log_arrival",
    "log_price",
    "price_spread",
    # Day-t cross-section (n_comm_day >= 10)
    "n_comm_day",
    "p_arr_t",
    "p_price_t",
    "surplus_cs",
    "dist_arr_070",
    "dist_price_030",
    # Strictly backward lags & entity dynamics (<= t)
    "lag_1_log_arr",
    "lag_2_log_arr",
    "lag_3_log_arr",
    "lag_1_log_price",
    "lag_2_log_price",
    "lag_3_log_price",
    "diff_prior_arr",
    "diff_prior_price",
    "arr_growth_3d",
    "days_since_prev_report",
    "past_report_count",
    # Same-day spatial spillover (strictly day t)
    "market_price_ratio_state_comm_t",
    "market_arr_ratio_state_comm_t",
    "neighbor_surplus_frac_t",
    # Calendar
    "dow_sin",
    "dow_cos",
    "is_weekend",
    # Train-fitted 4-level hierarchical shrinkage priors
    "prior_surplus_cs",
    "prior_log_arrival",
    "prior_log_price",
]

_CATEGORICAL_COLS: tuple[str, ...] = (
    "state_name",
    "district_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
)

_FLOAT32_COLS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "arrival_tonnes",
    "modal_price",
    "price_per_kg",
    "min_per_kg",
    "max_per_kg",
    "log_arrival",
    "price_spread",
)

_INT8_COLS: tuple[str, ...] = (
    "geo_missing",
    "month_num",
    "day_num",
    "is_weekend",
)


def assert_no_leakage_columns(cols: list[str] | tuple[str, ...]) -> None:
    """Assert that no forbidden or future-day columns appear in a feature list."""
    bad = sorted(set(cols) & FORBIDDEN_LEAKAGE_COLS)
    if bad:
        raise AssertionError(f"Forbidden leakage columns detected in features: {bad}")


def get_feature_columns() -> list[str]:
    """Return the validated numeric feature column list (strictly <= t)."""
    assert_no_leakage_columns(FEATURE_COLS)
    return list(FEATURE_COLS)


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load experiment YAML configuration."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_cleaned_data(
    csv_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Load deterministic cleaned APMC dataset with float32 numerics and category string IDs."""
    if csv_path is None:
        if config is not None and "paths" in config and "cleaned_csv" in config["paths"]:
            path = ROOT / config["paths"]["cleaned_csv"]
        else:
            path = ROOT / "data" / "processed" / "freshroute_foodbank_cleaned.csv"
    else:
        path = Path(csv_path)

    dtype_map: dict[str, str] = {}
    for col in _CATEGORICAL_COLS:
        dtype_map[col] = "category"
    for col in _FLOAT32_COLS:
        dtype_map[col] = "float32"
    for col in _INT8_COLS:
        dtype_map[col] = "int8"

    df = pd.read_csv(path, dtype=dtype_map, parse_dates=["date"], low_memory=False)
    return df


def _compute_series_iqr_bounds(s: pd.Series, k: float) -> dict[str, float]:
    """Compute (q1, q3, lower, upper) IQR bounds for a numeric series."""
    clean = pd.to_numeric(s, errors="coerce").dropna()
    if clean.empty:
        return {"q1": 0.0, "q3": 0.0, "lower": float("-inf"), "upper": float("inf")}
    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1
    if np.isnan(iqr) or iqr <= 0.0:
        return {"q1": q1, "q3": q3, "lower": float("-inf"), "upper": float("inf")}
    return {
        "q1": q1,
        "q3": q3,
        "lower": float(q1 - k * iqr),
        "upper": float(q3 + k * iqr),
    }


def fit_train_iqr_bounds(
    df_train: pd.DataFrame,
    price_k: float = 3.0,
    arrival_k: float = 5.0,
) -> dict[str, Any]:
    """Fit per-commodity and global fallback IQR clipping bounds strictly on Train rows."""
    bounds: dict[str, Any] = {
        "price_k": float(price_k),
        "arrival_k": float(arrival_k),
        "price": {"per_commodity": {}, "global": {}},
        "arrival": {"per_commodity": {}, "global": {}},
    }

    bounds["price"]["global"] = _compute_series_iqr_bounds(df_train["price_per_kg"], price_k)
    bounds["arrival"]["global"] = _compute_series_iqr_bounds(df_train["arrival_tonnes"], arrival_k)

    comm_str = df_train["commodity_name"].astype(str)
    for comm, grp in df_train.groupby(comm_str, observed=True, sort=False):
        bounds["price"]["per_commodity"][str(comm)] = _compute_series_iqr_bounds(
            grp["price_per_kg"], price_k
        )
        bounds["arrival"]["per_commodity"][str(comm)] = _compute_series_iqr_bounds(
            grp["arrival_tonnes"], arrival_k
        )

    return bounds


def apply_iqr_winsorization(df: pd.DataFrame, bounds: dict[str, Any]) -> pd.DataFrame:
    """Clip price_per_kg and arrival_tonnes using Train-fitted IQR bounds and recompute logs."""
    out = df.copy()
    comm_str = out["commodity_name"].astype(str)

    for col, key in (("price_per_kg", "price"), ("arrival_tonnes", "arrival")):
        per_comm = bounds[key]["per_commodity"]
        glob = bounds[key]["global"]
        lower_map = {k: v["lower"] for k, v in per_comm.items()}
        upper_map = {k: v["upper"] for k, v in per_comm.items()}

        lo = comm_str.map(lower_map).fillna(glob["lower"]).to_numpy(dtype=np.float64)
        hi = comm_str.map(upper_map).fillna(glob["upper"]).to_numpy(dtype=np.float64)
        vals = pd.to_numeric(out[col], errors="coerce").to_numpy(dtype=np.float64)
        out[col] = np.clip(vals, lo, hi).astype(np.float32)

    out["log_arrival"] = np.log1p(
        np.clip(out["arrival_tonnes"].to_numpy(dtype=np.float32), 0.0, None)
    ).astype(np.float32)
    out["log_price"] = np.log1p(
        np.clip(out["price_per_kg"].to_numpy(dtype=np.float32), 0.0, None)
    ).astype(np.float32)
    return out


def _fit_one_hierarchical_prior(
    df_valid: pd.DataFrame,
    target_col: str,
    smoothing_m: float,
) -> dict[str, Any]:
    """Fit 4-level state-qualified empirical-Bayes shrinkage lookup tables for one target."""
    global_mean = float(df_valid[target_col].mean()) if len(df_valid) > 0 else 0.0

    l4_cols = ["commodity_name"]
    l3_cols = ["state_name", "commodity_name"]
    l2_cols = ["state_name", "market_center_name", "commodity_name"]
    l1_cols = ["state_name", "market_center_name", "commodity_name", "variety", "grade"]

    work = df_valid[l1_cols + [target_col]].copy()
    for c in l1_cols:
        work[c] = work[c].astype(str)

    def _agg_level(cols: list[str]) -> pd.DataFrame:
        return (
            work.groupby(cols, observed=True, sort=False)[target_col]
            .agg(count="count", mean="mean")
            .reset_index()
        )

    l4 = _agg_level(l4_cols)
    l4["prior"] = (l4["count"] * l4["mean"] + smoothing_m * global_mean) / (
        l4["count"] + smoothing_m
    )

    l3 = _agg_level(l3_cols).merge(
        l4[l4_cols + ["prior"]].rename(columns={"prior": "parent"}),
        on=l4_cols,
        how="left",
    )
    l3["parent"] = l3["parent"].fillna(global_mean)
    l3["prior"] = (l3["count"] * l3["mean"] + smoothing_m * l3["parent"]) / (
        l3["count"] + smoothing_m
    )

    l2 = _agg_level(l2_cols).merge(
        l3[l3_cols + ["prior"]].rename(columns={"prior": "parent"}),
        on=l3_cols,
        how="left",
    )
    l2["parent"] = l2["parent"].fillna(global_mean)
    l2["prior"] = (l2["count"] * l2["mean"] + smoothing_m * l2["parent"]) / (
        l2["count"] + smoothing_m
    )

    l1 = _agg_level(l1_cols).merge(
        l2[l2_cols + ["prior"]].rename(columns={"prior": "parent"}),
        on=l2_cols,
        how="left",
    )
    l1["parent"] = l1["parent"].fillna(global_mean)
    l1["prior"] = (l1["count"] * l1["mean"] + smoothing_m * l1["parent"]) / (
        l1["count"] + smoothing_m
    )

    def _to_lookup(frame: pd.DataFrame, cols: list[str]) -> dict[Any, float]:
        if len(cols) == 1:
            return dict(zip(frame[cols[0]], frame["prior"].astype(np.float32)))
        keys = zip(*(frame[c].tolist() for c in cols))
        return dict(zip(keys, frame["prior"].astype(np.float32)))

    return {
        "global_mean": global_mean,
        "L1": _to_lookup(l1, l1_cols),
        "L2": _to_lookup(l2, l2_cols),
        "L3": _to_lookup(l3, l3_cols),
        "L4": _to_lookup(l4, l4_cols),
    }


def fit_shrinkage_priors(
    train_df: pd.DataFrame,
    smoothing_m: float = 10.0,
) -> dict[str, Any]:
    """Fit 4-level state-qualified shrinkage priors strictly on Train rows."""
    priors: dict[str, Any] = {
        "smoothing_m": float(smoothing_m),
        "targets": {},
    }

    active_surplus = train_df[train_df["surplus_cs"].notna()]
    priors["targets"]["surplus_cs"] = _fit_one_hierarchical_prior(
        active_surplus, "surplus_cs", float(smoothing_m)
    )
    for col in ("log_arrival", "log_price"):
        valid = train_df[train_df[col].notna()]
        priors["targets"][col] = _fit_one_hierarchical_prior(valid, col, float(smoothing_m))

    return priors


def _lookup_level(
    key_cols: list[pd.Series],
    lookup_dict: dict[Any, float],
) -> pd.Series:
    """Vectorized tuple-key lookup returning float32 Series with NaNs on misses."""
    if len(key_cols) == 1:
        return key_cols[0].map(lookup_dict).astype(np.float32)
    keys = list(zip(*(s.tolist() for s in key_cols)))
    vals = [lookup_dict.get(k, np.nan) for k in keys]
    return pd.Series(vals, index=key_cols[0].index, dtype=np.float32)


def apply_shrinkage_priors(
    df: pd.DataFrame,
    priors: dict[str, Any],
    return_coverage: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    """Apply Train-fitted 4-level hierarchical shrinkage priors to df."""
    out = df.copy()
    state_s = out["state_name"].astype(str)
    mkt_s = out["market_center_name"].astype(str)
    comm_s = out["commodity_name"].astype(str)
    var_s = out["variety"].astype(str)
    grade_s = out["grade"].astype(str)

    coverage_stats: dict[str, dict[str, float]] = {}

    for target_col, out_col in (
        ("surplus_cs", "prior_surplus_cs"),
        ("log_arrival", "prior_log_arrival"),
        ("log_price", "prior_log_price"),
    ):
        spec = priors["targets"][target_col]
        v1 = _lookup_level([state_s, mkt_s, comm_s, var_s, grade_s], spec["L1"])
        v2 = _lookup_level([state_s, mkt_s, comm_s], spec["L2"])
        v3 = _lookup_level([state_s, comm_s], spec["L3"])
        v4 = _lookup_level([comm_s], spec["L4"])
        gmean = np.float32(spec["global_mean"])

        out[out_col] = v1.fillna(v2).fillna(v3).fillna(v4).fillna(gmean).astype(np.float32)

        if return_coverage:
            m1 = v1.notna()
            m2 = (~m1) & v2.notna()
            m3 = (~m1) & (~m2) & v3.notna()
            m4 = (~m1) & (~m2) & (~m3) & v4.notna()
            entity_covered = (m1 | m2 | m3 | m4).mean()
            coverage_stats[out_col] = {
                "entity_coverage": float(entity_covered),
                "L1": float(m1.mean()),
                "L2": float(m2.mean()),
                "L3": float(m3.mean()),
                "L4": float(m4.mean()),
                "global_fallback": float(1.0 - entity_covered),
            }

    if return_coverage:
        return out, coverage_stats
    return out


def _add_cross_sectional_features(
    df: pd.DataFrame,
    min_n_comm_day: int = 10,
    arr_pct_min: float = 0.70,
    price_pct_max: float = 0.30,
) -> pd.DataFrame:
    """Compute strictly day-t cross-sectional counts, percentiles, and surplus_cs."""
    out = df.copy()
    g_cd = out.groupby(["commodity_name", "date"], observed=True, sort=False)
    n_comm_day = g_cd["arrival_tonnes"].transform("count").astype(np.int32)
    out["n_comm_day"] = n_comm_day

    active = n_comm_day >= int(min_n_comm_day)

    p_arr = pd.Series(np.nan, index=out.index, dtype=np.float32)
    p_price = pd.Series(np.nan, index=out.index, dtype=np.float32)

    if active.any():
        active_df = out.loc[active]
        g_act = active_df.groupby(["commodity_name", "date"], observed=True, sort=False)
        p_arr.loc[active] = g_act["arrival_tonnes"].rank(pct=True, method="average").astype(np.float32)
        p_price.loc[active] = g_act["price_per_kg"].rank(pct=True, method="average").astype(np.float32)

    out["p_arr_t"] = p_arr
    out["p_price_t"] = p_price

    surplus = pd.Series(np.nan, index=out.index, dtype=np.float32)
    if active.any():
        is_glut = (p_arr.loc[active] >= arr_pct_min) & (p_price.loc[active] <= price_pct_max)
        surplus.loc[active] = is_glut.astype(np.float32)

    out["surplus_cs"] = surplus
    out["dist_arr_070"] = (np.float32(arr_pct_min) - out["p_arr_t"]).astype(np.float32)
    out["dist_price_030"] = (out["p_price_t"] - np.float32(price_pct_max)).astype(np.float32)
    return out


def _add_backward_lag_features(
    df: pd.DataFrame,
    entity_keys: list[str],
) -> pd.DataFrame:
    """Compute strictly backward (<= t) entity lag and reporting-cadence features."""
    out = df.sort_values(entity_keys + ["date"], kind="mergesort").reset_index(drop=True)
    g = out.groupby(entity_keys, observed=True, sort=False)

    for k in (1, 2, 3):
        out[f"lag_{k}_log_arr"] = g["log_arrival"].shift(k).astype(np.float32)
        out[f"lag_{k}_log_price"] = g["log_price"].shift(k).astype(np.float32)

    out["diff_prior_arr"] = (out["log_arrival"] - out["lag_1_log_arr"]).astype(np.float32)
    out["diff_prior_price"] = (out["log_price"] - out["lag_1_log_price"]).astype(np.float32)
    out["arr_growth_3d"] = (out["log_arrival"] - out["lag_3_log_arr"]).astype(np.float32)

    prev_date = g["date"].shift(1)
    out["days_since_prev_report"] = (out["date"] - prev_date).dt.days.astype(np.float32)
    out["past_report_count"] = (g.cumcount() + 1).astype(np.int32)
    return out


def _add_spatial_spillover_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute strictly day-t same-(state, commodity, date) spatial spillover features."""
    out = df
    g_scd = out.groupby(["state_name", "commodity_name", "date"], observed=True, sort=False)

    med_price = g_scd["price_per_kg"].transform("median").to_numpy(dtype=np.float32)
    mean_arr = g_scd["arrival_tonnes"].transform("mean").to_numpy(dtype=np.float32)
    price_vals = out["price_per_kg"].to_numpy(dtype=np.float32)
    arr_vals = out["arrival_tonnes"].to_numpy(dtype=np.float32)

    out["market_price_ratio_state_comm_t"] = np.divide(
        price_vals,
        med_price,
        out=np.ones_like(price_vals, dtype=np.float32),
        where=med_price > 0.0,
    ).astype(np.float32)
    out["market_arr_ratio_state_comm_t"] = np.divide(
        arr_vals,
        mean_arr,
        out=np.ones_like(arr_vals, dtype=np.float32),
        where=mean_arr > 0.0,
    ).astype(np.float32)

    active_mask = out["surplus_cs"].notna()
    is_surplus = (out["surplus_cs"] == 1.0).astype(np.float32)
    out["_tmp_is_surplus"] = is_surplus
    g_scd_tmp = out.groupby(["state_name", "commodity_name", "date"], observed=True, sort=False)
    total_surplus = g_scd_tmp["_tmp_is_surplus"].transform("sum").to_numpy(dtype=np.float32)
    total_count = g_scd_tmp["_tmp_is_surplus"].transform("count").to_numpy(dtype=np.float32)
    out = out.drop(columns=["_tmp_is_surplus"])

    other_count = total_count - 1.0
    other_surplus = total_surplus - is_surplus.to_numpy(dtype=np.float32)

    valid_neighbor = active_mask.to_numpy() & (other_count > 0.0)
    neighbor_frac = np.full(len(out), np.nan, dtype=np.float32)
    neighbor_frac[valid_neighbor] = (
        other_surplus[valid_neighbor] / other_count[valid_neighbor]
    ).astype(np.float32)
    out["neighbor_surplus_frac_t"] = neighbor_frac
    return out


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical day-of-week and weekend features strictly from day-t date."""
    out = df
    dow = out["date"].dt.weekday.to_numpy(dtype=np.float32)
    angle = np.float32(2.0 * np.pi / 7.0) * dow
    out["dow_sin"] = np.sin(angle).astype(np.float32)
    out["dow_cos"] = np.cos(angle).astype(np.float32)
    out["is_weekend"] = (dow >= 5.0).astype(np.int8)
    return out


def build_features(
    df: pd.DataFrame,
    config: dict[str, Any],
    train_end_date: str | pd.Timestamp,
    iqr_bounds: dict[str, Any] | None = None,
    shrinkage_priors: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Construct strictly <= t features on 100% of deduplicated rows.

    Never reads, computes, or filters on any next-day column.
    """
    entity_keys = list(config.get("entity_keys", ENTITY_KEYS))
    min_n_comm_day = int(config["cross_section"]["min_n_comm_day"])
    price_k = float(config["winsorization"]["price_iqr_k"])
    arrival_k = float(config["winsorization"]["arrival_iqr_k"])
    arr_pct_min = float(config["surplus_cs"]["arrival_pct_min"])
    price_pct_max = float(config["surplus_cs"]["price_pct_max"])
    smoothing_m = float(config["shrinkage"]["smoothing_m"])

    work = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(work["date"]):
        work["date"] = pd.to_datetime(work["date"])

    train_end_ts = pd.Timestamp(train_end_date)

    if iqr_bounds is None:
        df_train_raw = work[work["date"] <= train_end_ts]
        iqr_bounds = fit_train_iqr_bounds(df_train_raw, price_k=price_k, arrival_k=arrival_k)

    work = apply_iqr_winsorization(work, iqr_bounds)
    work = _add_cross_sectional_features(
        work,
        min_n_comm_day=min_n_comm_day,
        arr_pct_min=arr_pct_min,
        price_pct_max=price_pct_max,
    )

    if shrinkage_priors is None:
        df_train_cs = work[work["date"] <= train_end_ts]
        shrinkage_priors = fit_shrinkage_priors(df_train_cs, smoothing_m=smoothing_m)

    work = apply_shrinkage_priors(work, shrinkage_priors)
    work = _add_backward_lag_features(work, entity_keys=entity_keys)
    work = _add_spatial_spillover_features(work)
    work = _add_calendar_features(work)

    assert len(work) == len(df), f"Row count mismatch: expected {len(df)}, got {len(work)}"
    assert_no_leakage_columns(get_feature_columns())
    return work


def build_supervised_pairs(
    feat_df: pd.DataFrame,
    config: dict[str, Any],
    split_mode: str | None = None,
    return_stats: bool = False,
) -> (
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    | tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]
):
    """Pair day t features with exact (ENTITY_KEYS, date + 1 day) targets and split chronologically."""
    entity_keys = list(config.get("entity_keys", ENTITY_KEYS))
    min_n = int(config["cross_section"]["min_n_comm_day"])
    mode = split_mode or config["split"]["mode"]
    preset = config["split"]["presets"][mode]

    left = feat_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(left["date"]):
        left["date"] = pd.to_datetime(left["date"])
    left["target_date"] = left["date"] + pd.Timedelta(days=1)

    right_cols = entity_keys + [
        "date",
        "n_comm_day",
        "surplus_cs",
        "log_arrival",
        "log_price",
        "arrival_tonnes",
        "price_per_kg",
    ]
    right = left[right_cols].rename(
        columns={
            "date": "target_date",
            "n_comm_day": "n_comm_day_next",
            "surplus_cs": "surplus_cs_next",
            "log_arrival": "log_arrival_next",
            "log_price": "log_price_next",
            "arrival_tonnes": "arrival_tonnes_next",
            "price_per_kg": "price_per_kg_next",
        }
    )

    # Convert entity keys temporarily to str if categories differ; here left & right share feat_df dtypes
    pairs_all = pd.merge(left, right, on=entity_keys + ["target_date"], how="inner")

    t_active = pairs_all["n_comm_day"] >= min_n
    next_active = pairs_all["n_comm_day_next"] >= min_n
    both_active = t_active & next_active

    dropped_t_only_inactive = int((~t_active & next_active).sum())
    dropped_next_only_inactive = int((t_active & ~next_active).sum())
    dropped_both_inactive = int((~t_active & ~next_active).sum())

    pairs = pairs_all.loc[both_active].copy()
    pairs["y_onset"] = pairs["surplus_cs_next"].astype(np.int8)
    pairs["delta_log_arr"] = (pairs["log_arrival_next"] - pairs["log_arrival"]).astype(np.float32)

    train_mask = (
        (pairs["date"] >= pd.Timestamp(preset["train_start"]))
        & (pairs["date"] <= pd.Timestamp(preset["train_end"]))
        & (pairs["target_date"] <= pd.Timestamp(preset["train_target_max"]))
    )
    val_mask = (
        (pairs["date"] >= pd.Timestamp(preset["val_start"]))
        & (pairs["date"] <= pd.Timestamp(preset["val_end"]))
        & (pairs["target_date"] <= pd.Timestamp(preset["val_target_max"]))
    )
    test_mask = (
        (pairs["date"] >= pd.Timestamp(preset["test_start"]))
        & (pairs["date"] <= pd.Timestamp(preset["test_end"]))
        & (pairs["target_date"] <= pd.Timestamp(preset["test_target_max"]))
    )

    train = pairs.loc[train_mask].reset_index(drop=True)
    val = pairs.loc[val_mask].reset_index(drop=True)
    test = pairs.loc[test_mask].reset_index(drop=True)

    assert train["target_date"].max() < val["date"].min(), (
        f"Train target overlap with Val: {train['target_date'].max()} >= {val['date'].min()}"
    )
    assert val["target_date"].max() < test["date"].min(), (
        f"Val target overlap with Test: {val['target_date'].max()} >= {test['date'].min()}"
    )

    if return_stats:
        stats = {
            "split_mode": mode,
            "total_exact_pairs": int(len(pairs_all)),
            "active_pairs_both": int(len(pairs)),
            "dropped_t_ge_10_next_lt_10": dropped_next_only_inactive,
            "dropped_t_lt_10_next_ge_10": dropped_t_only_inactive,
            "dropped_both_lt_10": dropped_both_inactive,
            "train_pairs": int(len(train)),
            "val_pairs": int(len(val)),
            "test_pairs": int(len(test)),
            "boundary_purged_pairs": int(
                len(pairs) - (len(train) + len(val) + len(test))
            ),
        }
        return train, val, test, stats

    return train, val, test


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leak-free FreshRoute v3.1 features & splits.")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--split-mode", type=str, default=None, help="Override config split.mode")
    args = parser.parse_args()

    config = load_config(args.config)
    mode = args.split_mode or config["split"]["mode"]
    preset = config["split"]["presets"][mode]
    train_end_date = preset["train_end"]

    df_raw = load_cleaned_data(config=config)
    raw_ram_mb = df_raw.memory_usage(deep=True).sum() / (1024 ** 2)

    df_train_raw = df_raw[df_raw["date"] <= pd.Timestamp(train_end_date)]
    iqr_bounds = fit_train_iqr_bounds(
        df_train_raw,
        price_k=float(config["winsorization"]["price_iqr_k"]),
        arrival_k=float(config["winsorization"]["arrival_iqr_k"]),
    )

    df_wins = apply_iqr_winsorization(df_raw, iqr_bounds)
    df_cs = _add_cross_sectional_features(
        df_wins,
        min_n_comm_day=int(config["cross_section"]["min_n_comm_day"]),
        arr_pct_min=float(config["surplus_cs"]["arrival_pct_min"]),
        price_pct_max=float(config["surplus_cs"]["price_pct_max"]),
    )
    shrinkage_priors = fit_shrinkage_priors(
        df_cs[df_cs["date"] <= pd.Timestamp(train_end_date)],
        smoothing_m=float(config["shrinkage"]["smoothing_m"]),
    )

    feat_df = build_features(
        df_raw,
        config=config,
        train_end_date=train_end_date,
        iqr_bounds=iqr_bounds,
        shrinkage_priors=shrinkage_priors,
    )
    feat_ram_mb = feat_df.memory_usage(deep=True).sum() / (1024 ** 2)

    # Check shrinkage entity coverage on Val & Test feature rows
    val_feat = feat_df[
        (feat_df["date"] >= pd.Timestamp(preset["val_start"]))
        & (feat_df["date"] <= pd.Timestamp(preset["val_end"]))
    ]
    test_feat = feat_df[
        (feat_df["date"] >= pd.Timestamp(preset["test_start"]))
        & (feat_df["date"] <= pd.Timestamp(preset["test_end"]))
    ]
    _, val_cov = apply_shrinkage_priors(val_feat, shrinkage_priors, return_coverage=True)
    _, test_cov = apply_shrinkage_priors(test_feat, shrinkage_priors, return_coverage=True)
    min_n = int(config["cross_section"]["min_n_comm_day"])
    _, val_act_cov = apply_shrinkage_priors(
        val_feat[val_feat["n_comm_day"] >= min_n], shrinkage_priors, return_coverage=True
    )
    _, test_act_cov = apply_shrinkage_priors(
        test_feat[test_feat["n_comm_day"] >= min_n], shrinkage_priors, return_coverage=True
    )

    train, val, test, pair_stats = build_supervised_pairs(
        feat_df, config=config, split_mode=mode, return_stats=True
    )

    val_weekdays = sorted(val["date"].dt.day_name().unique().tolist())
    val_target_weekdays = sorted(val["target_date"].dt.day_name().unique().tolist())

    print("=== FreshRoute v3.1 Feature Pipeline Summary ===")
    print(f"Split mode: {mode} | train_end={train_end_date}")
    print(f"Cleaned rows loaded: {len(df_raw):,} | RAM: {raw_ram_mb:.2f} MB")
    print(f"Feature df rows:     {len(feat_df):,} | RAM: {feat_ram_mb:.2f} MB")
    print(f"FEATURE_COLS count:  {len(get_feature_columns())}")
    print(
        f"Exact (t, t+1) pairs: {pair_stats['total_exact_pairs']:,} | "
        f"Both active (>=10): {pair_stats['active_pairs_both']:,}"
    )
    print(
        f"Dropped boundary pairs: "
        f"(n(t)>=10, n(t+1)<10)={pair_stats['dropped_t_ge_10_next_lt_10']}, "
        f"(n(t)<10, n(t+1)>=10)={pair_stats['dropped_t_lt_10_next_ge_10']}, "
        f"both<10={pair_stats['dropped_both_lt_10']}"
    )
    print(
        f"Splits: Train={pair_stats['train_pairs']:,} "
        f"[{train['date'].min().date()}..{train['date'].max().date()} -> "
        f"target {train['target_date'].min().date()}..{train['target_date'].max().date()}], "
        f"Val={pair_stats['val_pairs']:,} "
        f"[{val['date'].min().date()}..{val['date'].max().date()} -> "
        f"target {val['target_date'].min().date()}..{val['target_date'].max().date()}], "
        f"Test={pair_stats['test_pairs']:,} "
        f"[{test['date'].min().date()}..{test['date'].max().date()} -> "
        f"target {test['target_date'].min().date()}..{test['target_date'].max().date()}]"
    )
    print(f"Boundary purged pairs: {pair_stats['boundary_purged_pairs']:,}")
    print(f"Val feature weekdays ({len(val_weekdays)}/7): {val_weekdays}")
    print(f"Val target weekdays  ({len(val_target_weekdays)}/7): {val_target_weekdays}")
    print(
        "Shrinkage entity coverage (Val all):     "
        + ", ".join(f"{k}={v['entity_coverage']:.4%}" for k, v in val_cov.items())
    )
    print(
        "Shrinkage entity coverage (Val active):  "
        + ", ".join(f"{k}={v['entity_coverage']:.4%}" for k, v in val_act_cov.items())
    )
    print(
        "Shrinkage entity coverage (Test all):    "
        + ", ".join(f"{k}={v['entity_coverage']:.4%}" for k, v in test_cov.items())
    )
    print(
        "Shrinkage entity coverage (Test active): "
        + ", ".join(f"{k}={v['entity_coverage']:.4%}" for k, v in test_act_cov.items())
    )


if __name__ == "__main__":
    main()
