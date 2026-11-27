"""FreshRoute Phase 2: Weather-Augmented & Expanding Walk-Forward CV Trainer.

Plan v3.1 requirements:
  - Integrate strictly <= t district weather features (Open-Meteo, verified
    raw/Census-LGD centroids only; never state-median imputed coordinates) and
    causal 30d/90d/prior-year seasonal + festival/crop-season features.
  - Evaluate across 3-to-5 fold expanding walk-forward CV when multi-month APMC
    history (>= 7 months) is available, fitting Train-only IQR bounds and 4-level
    shrinkage priors strictly inside each fold.
  - On the 24-day local scoped window (< 7 months), run a clean 10d_7d_4d
    weather+calendar ablation against Naive Persistence and Baseline features.

Run:
  python scripts/train_phase2_walkforward.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_features as bf  # noqa: E402
from scripts import fetch_apmc_history as fah  # noqa: E402
from scripts import fetch_weather as fw  # noqa: E402
from scripts import train_model as tm  # noqa: E402

WEATHER_FEATURE_COLS: list[str] = [
    "precip_sum_3d",
    "precip_sum_7d",
    "temp_max_mean_3d",
    "humidity_mean_3d",
    "et0_sum_3d",
    "heat_spoilage_index",
]

SEASONAL_CALENDAR_COLS: list[str] = [
    "arr_mean_30d",
    "arr_mean_90d",
    "price_mean_30d",
    "price_mean_90d",
    "prior_year_month_log_arr",
    "prior_year_month_log_price",
    "days_to_major_festival",
    "is_kharif_harvest_peak",
    "is_rabi_harvest_peak",
    "is_zaid_harvest_peak",
]


def prepare_phase2_frame(
    apmc_df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    centroids_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Enrich scoped APMC rows with causal seasonal/calendar & verified weather features."""
    work = apmc_df.copy()
    work["date"] = pd.to_datetime(work["date"])
    for col in [*bf.ENTITY_KEYS, "district_name"]:
        if col in work.columns:
            work[col] = work[col].fillna("UNKNOWN").astype(str).str.strip().str.upper()

    # Deterministic row fields expected by build_features.py
    if "latitude" not in work.columns or "longitude" not in work.columns:
        if centroids_df is not None and not centroids_df.empty:
            c = centroids_df[["state_name", "district_name", "latitude", "longitude", "coord_source"]].copy()
            c = c[c["coord_source"].isin(["raw_mandi_median", "census_lgd_centroid"])]
            work = work.merge(c, on=["state_name", "district_name"], how="left")
            work["geo_missing"] = work["latitude"].isna().astype("int8")
            work["latitude"] = work["latitude"].fillna(0.0).astype("float32")
            work["longitude"] = work["longitude"].fillna(0.0).astype("float32")
        else:
            work["latitude"] = np.float32(0.0)
            work["longitude"] = np.float32(0.0)
            work["geo_missing"] = np.int8(1)
    elif "geo_missing" not in work.columns:
        work["geo_missing"] = (work["latitude"].isna() | work["longitude"].isna()).astype("int8")

    if "price_spread" not in work.columns:
        modal = work["modal_price"].replace(0, np.nan)
        work["price_spread"] = (
            ((work["max_per_kg"] - work["min_per_kg"]) * 100.0 / modal).fillna(0.0).clip(0.0, 5.0).astype("float32")
        )
    if "month_num" not in work.columns:
        work["month_num"] = work["date"].dt.month.astype("int8")
    if "day_num" not in work.columns:
        work["day_num"] = work["date"].dt.day.astype("int8")
    if "is_weekend" not in work.columns:
        work["is_weekend"] = (work["date"].dt.weekday >= 5).astype("int8")

    work = fah.build_seasonal_baselines(work)
    work = fah.add_calendar_season_features(work)

    if weather_df is not None and not weather_df.empty:
        w = fw.engineer_weather_features(weather_df)
        if "coord_source" in w.columns:
            imputed = w["coord_source"] == "state_median_imputed"
            if imputed.any():
                raise ValueError("Phase 2 weather join forbids state_median_imputed coordinates")
        keep_w = ["date", "state_name", "district_name"] + [
            c for c in WEATHER_FEATURE_COLS if c in w.columns
        ]
        w_dedup = w[keep_w].drop_duplicates(subset=["date", "state_name", "district_name"])
        work = work.merge(w_dedup, on=["date", "state_name", "district_name"], how="left")

    return work


def _get_available_phase2_cols(df: pd.DataFrame, include_weather: bool = True) -> list[str]:
    base = bf.get_feature_columns()
    extra = [c for c in SEASONAL_CALENDAR_COLS if c in df.columns]
    if include_weather:
        extra += [c for c in WEATHER_FEATURE_COLS if c in df.columns]
    cols = base + extra
    bf.assert_no_leakage_columns(cols)
    return cols


def _pair_all_active(feat_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create exact (t, t+1) supervised pairs filtered to n_comm_day >= min_n on both days."""
    entity_keys = list(config.get("entity_keys", bf.ENTITY_KEYS))
    min_n = int(config["cross_section"]["min_n_comm_day"])

    left = feat_df.copy()
    left["date"] = pd.to_datetime(left["date"])
    left["target_date"] = left["date"] + pd.Timedelta(days=1)

    right = left[
        entity_keys + ["date", "n_comm_day", "surplus_cs", "log_arrival"]
    ].rename(
        columns={
            "date": "target_date",
            "n_comm_day": "n_comm_day_next",
            "surplus_cs": "surplus_cs_next",
            "log_arrival": "log_arrival_next",
        }
    )
    pairs = left.merge(right, on=[*entity_keys, "target_date"], how="inner")
    pairs = pairs[(pairs["n_comm_day"] >= min_n) & (pairs["n_comm_day_next"] >= min_n)].copy()
    pairs["y_onset"] = pairs["surplus_cs_next"].astype("int8")
    pairs["delta_log_arr"] = (pairs["log_arrival_next"] - pairs["log_arrival"]).astype("float32")
    return pairs


def evaluate_walk_forward_cv(
    raw_phase2_df: pd.DataFrame,
    config: dict[str, Any],
    min_train_months: int = 6,
    test_window_months: int = 1,
    n_folds: int = 5,
    include_weather: bool = True,
) -> dict[str, Any]:
    """Run expanding walk-forward CV with strict per-fold Train-only IQR & shrinkage."""
    work = raw_phase2_df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["ym"] = work["date"].dt.to_period("M")
    all_months = sorted(work["ym"].unique())

    fold_reports: list[dict[str, Any]] = []
    for idx in range(min_train_months, len(all_months) - test_window_months + 1):
        if len(fold_reports) >= n_folds:
            break
        train_months = all_months[:idx]
        test_months = all_months[idx : idx + test_window_months]

        # Carve an internal chronological Val month (last month of train_months) for early stopping / threshold tuning
        fit_months = set(train_months[:-1]) if len(train_months) >= 2 else set(train_months)
        val_months = {train_months[-1]} if len(train_months) >= 2 else set(train_months)

        fit_end_date = work.loc[work["ym"].isin(fit_months), "date"].max()
        val_end_date = work.loc[work["ym"].isin(val_months), "date"].max()
        test_start_date = work.loc[work["ym"].isin(test_months), "date"].min()
        test_end_date = work.loc[work["ym"].isin(test_months), "date"].max()

        # Fit IQR & shrinkage strictly on fold's fit rows (<= fit_end_date)
        feat_df = bf.build_features(work.drop(columns=["ym"]), config, train_end_date=fit_end_date)
        pairs = _pair_all_active(feat_df, config)
        if pairs.empty:
            continue

        tr = pairs[pairs["target_date"] <= fit_end_date].copy()
        va = pairs[(pairs["date"] > fit_end_date) & (pairs["target_date"] <= val_end_date)].copy()
        te = pairs[(pairs["date"] >= test_start_date) & (pairs["date"] <= test_end_date)].copy()
        if tr.empty or va.empty or te.empty:
            continue

        assert tr["target_date"].max() < va["date"].min()
        assert va["target_date"].max() < te["date"].min()

        feat_cols = _get_available_phase2_cols(pairs, include_weather=include_weather)
        t1a_res, _ = tm.train_and_evaluate_track_1a(tr, va, te, feat_cols, config)
        t1b_res, _ = tm.train_and_evaluate_track_1b(tr, va, te, feat_cols, config)

        fold_reports.append(
            {
                "fold": len(fold_reports) + 1,
                "fit_months": [str(m) for m in sorted(fit_months)],
                "val_months": [str(m) for m in sorted(val_months)],
                "test_months": [str(m) for m in sorted(test_months)],
                "n_train": int(len(tr)),
                "n_val": int(len(va)),
                "n_test": int(len(te)),
                "track_1a_test": {
                    name: m["test"] for name, m in t1a_res["models"].items()
                },
                "track_1b_test": {
                    name: m["test"] for name, m in t1b_res["models"].items()
                },
            }
        )

    if not fold_reports:
        return {"mode": "walk_forward_cv", "n_folds": 0, "folds": []}

    # Aggregate mean +/- std lift over Naive Persistence across folds
    t1a_pr_lifts = [
        f["track_1a_test"]["XGBClassifier"]["pr_auc_lift"] for f in fold_reports
    ]
    t1a_rocs = [
        f["track_1a_test"]["XGBClassifier"]["roc_auc"] for f in fold_reports
    ]
    t1b_rmse_deltas = [
        f["track_1b_test"]["Naive Persistence"]["rmse"]
        - f["track_1b_test"]["XGBRegressor (reg:absoluteerror)"]["rmse"]
        for f in fold_reports
    ]
    t1b_mae_deltas = [
        f["track_1b_test"]["Naive Persistence"]["mae"]
        - f["track_1b_test"]["XGBRegressor (reg:absoluteerror)"]["mae"]
        for f in fold_reports
    ]
    t1b_ndcg10_lifts = [
        f["track_1b_test"]["XGBRegressor (reg:absoluteerror)"]["ndcg_at_10"]
        - f["track_1b_test"]["Mean-Reversion (-diff_prior_arr)"]["ndcg_at_10"]
        for f in fold_reports
    ]

    return {
        "mode": "walk_forward_cv",
        "n_folds": len(fold_reports),
        "summary": {
            "track_1a_xgb_pr_auc_lift_mean": round(float(np.mean(t1a_pr_lifts)), 4),
            "track_1a_xgb_pr_auc_lift_std": round(float(np.std(t1a_pr_lifts)), 4),
            "track_1a_xgb_roc_auc_mean": round(float(np.mean(t1a_rocs)), 4),
            "track_1b_rmse_reduction_mean": round(float(np.mean(t1b_rmse_deltas)), 4),
            "track_1b_rmse_reduction_std": round(float(np.std(t1b_rmse_deltas)), 4),
            "track_1b_mae_reduction_mean": round(float(np.mean(t1b_mae_deltas)), 4),
            "track_1b_mae_reduction_std": round(float(np.std(t1b_mae_deltas)), 4),
            "track_1b_surge_ndcg10_lift_mean": round(float(np.mean(t1b_ndcg10_lifts)), 4),
            "track_1b_surge_ndcg10_lift_std": round(float(np.std(t1b_ndcg10_lifts)), 4),
        },
        "folds": fold_reports,
    }


def evaluate_scoped_weather_ablation(
    raw_phase2_df: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate 10d_7d_4d scoped subset with vs. without weather + calendar features."""
    preset = config["split"]["presets"][config["split"]["mode"]]
    feat_df = bf.build_features(raw_phase2_df, config, train_end_date=preset["train_end"])
    tr, va, te, split_stats = bf.build_supervised_pairs(feat_df, config, return_stats=True)

    base_cols = bf.get_feature_columns()
    plus_cols = _get_available_phase2_cols(tr, include_weather=True)

    t1a_base, _ = tm.train_and_evaluate_track_1a(tr, va, te, base_cols, config)
    t1b_base, _ = tm.train_and_evaluate_track_1b(tr, va, te, base_cols, config)
    t1a_plus, _ = tm.train_and_evaluate_track_1a(tr, va, te, plus_cols, config)
    t1b_plus, _ = tm.train_and_evaluate_track_1b(tr, va, te, plus_cols, config)

    return {
        "mode": "scoped_24d_weather_ablation",
        "split_stats": split_stats,
        "base_feature_count": len(base_cols),
        "phase2_feature_count": len(plus_cols),
        "added_features": [c for c in plus_cols if c not in base_cols],
        "baseline_features": {
            "track_1a": t1a_base,
            "track_1b": t1b_base,
        },
        "with_weather_and_calendar": {
            "track_1a": t1a_plus,
            "track_1b": t1b_plus,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute Phase 2 weather + walk-forward CV trainer")
    parser.add_argument("--config", type=Path, default=bf.DEFAULT_CONFIG_PATH)
    parser.add_argument("--apmc-csv", type=Path, default=None)
    parser.add_argument("--weather-csv", type=Path, default=None)
    parser.add_argument("--centroids-csv", type=Path, default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "data" / "processed" / "phase2_walkforward_metrics.json",
    )
    args = parser.parse_args()

    config = bf.load_config(args.config)
    p2 = config["phase_2"]
    apmc_path = args.apmc_csv or (ROOT / p2["apmc_history"]["output_csv"])
    weather_path = args.weather_csv or (ROOT / p2["weather"]["output_csv"])
    centroids_path = args.centroids_csv or (ROOT / p2["weather"]["centroids_csv"])

    if not apmc_path.exists():
        raise FileNotFoundError(
            f"Scoped APMC CSV not found at {apmc_path}. Run scripts/fetch_apmc_history.py first."
        )

    apmc_df = pd.read_csv(apmc_path, low_memory=False)
    weather_df = pd.read_csv(weather_path, low_memory=False) if weather_path.exists() else None
    centroids_df = pd.read_csv(centroids_path, low_memory=False) if centroids_path.exists() else None

    enriched = prepare_phase2_frame(apmc_df, weather_df=weather_df, centroids_df=centroids_df)
    n_months = int(pd.to_datetime(enriched["date"]).dt.to_period("M").nunique())
    wf_cfg = p2["apmc_history"]["walk_forward_cv"]

    if n_months >= int(wf_cfg["min_train_months"]) + int(wf_cfg["test_window_months"]):
        report = evaluate_walk_forward_cv(
            enriched,
            config,
            min_train_months=int(wf_cfg["min_train_months"]),
            test_window_months=int(wf_cfg["test_window_months"]),
            n_folds=int(wf_cfg["n_folds"]),
            include_weather=weather_df is not None,
        )
    else:
        report = evaluate_scoped_weather_ablation(enriched, config)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "output_json": str(args.output_json)}, indent=2))


if __name__ == "__main__":
    main()
