"""FreshRoute Model Hardening: Feature & Prediction Drift Monitor (PSI & KS).

Computes Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov (KS)
statistics comparing Train vs. Val and Train vs. Test across all 34 FEATURE_COLS,
as well as target/label base-rate drift.

Standard PSI bands:
  - PSI < 0.10 : stable
  - 0.10 <= PSI < 0.25 : moderate_shift
  - PSI >= 0.25 : significant_shift

Run:
  python scripts/monitor_drift.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_features as bf  # noqa: E402


def compute_psi(
    expected: np.ndarray, actual: np.ndarray, n_bins: int = 10, eps: float = 1e-6
) -> float:
    """Compute Population Stability Index using quantile edges fit on `expected`."""
    exp = np.asarray(expected, dtype=np.float64)
    act = np.asarray(actual, dtype=np.float64)
    exp = exp[np.isfinite(exp)]
    act = act[np.isfinite(act)]
    if len(exp) == 0 or len(act) == 0:
        return 0.0

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(exp, quantiles))
    if len(edges) < 2:
        return 0.0

    edges[0] = -np.inf
    edges[-1] = np.inf
    exp_counts, _ = np.histogram(exp, bins=edges)
    act_counts, _ = np.histogram(act, bins=edges)

    exp_pct = np.clip(exp_counts / max(len(exp), 1), eps, None)
    act_pct = np.clip(act_counts / max(len(act), 1), eps, None)
    psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return round(max(psi, 0.0), 6)


def classify_psi(psi: float) -> str:
    if psi >= 0.25:
        return "significant_shift"
    if psi >= 0.10:
        return "moderate_shift"
    return "stable"


def compute_feature_drift(
    ref_df: pd.DataFrame,
    cur_df: pd.DataFrame,
    feature_cols: list[str],
) -> list[dict[str, Any]]:
    """Compute PSI, KS statistic, and p-value for every feature in `feature_cols`."""
    rows: list[dict[str, Any]] = []
    for col in feature_cols:
        r_vals = ref_df[col].to_numpy(dtype=np.float64)
        c_vals = cur_df[col].to_numpy(dtype=np.float64)
        r_nan = float(np.mean(~np.isfinite(r_vals)))
        c_nan = float(np.mean(~np.isfinite(c_vals)))
        r_clean = r_vals[np.isfinite(r_vals)]
        c_clean = c_vals[np.isfinite(c_vals)]

        psi = compute_psi(r_clean, c_clean)
        if len(r_clean) > 0 and len(c_clean) > 0:
            ks_res = ks_2samp(r_clean, c_clean)
            ks_stat = round(float(ks_res.statistic), 6)
            ks_p = float(ks_res.pvalue)
        else:
            ks_stat, ks_p = 0.0, 1.0

        rows.append(
            {
                "feature": col,
                "psi": psi,
                "status": classify_psi(psi),
                "ks_stat": ks_stat,
                "ks_pvalue": round(ks_p, 6),
                "ref_nan_rate": round(r_nan, 5),
                "cur_nan_rate": round(c_nan, 5),
            }
        )
    return sorted(rows, key=lambda r: r["psi"], reverse=True)


def run_drift_monitor(
    config_path: Path | str = bf.DEFAULT_CONFIG_PATH,
    output_json: Path | str | None = None,
) -> dict[str, Any]:
    config = bf.load_config(config_path)
    preset = config["split"]["presets"][config["split"]["mode"]]
    df_clean = bf.load_cleaned_data(ROOT / config["paths"]["cleaned_csv"], config=config)
    feat_df = bf.build_features(df_clean, config, train_end_date=preset["train_end"])
    train, val, test = bf.build_supervised_pairs(feat_df, config)
    feature_cols = bf.get_feature_columns()

    val_drift = compute_feature_drift(train, val, feature_cols)
    test_drift = compute_feature_drift(train, test, feature_cols)

    def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        counts = {"stable": 0, "moderate_shift": 0, "significant_shift": 0}
        for r in rows:
            counts[r["status"]] += 1
        return {
            "n_features": len(rows),
            "counts": counts,
            "max_psi": rows[0]["psi"] if rows else 0.0,
            "top_5_drifted": rows[:5],
        }

    tr_onset_rate = float(train.loc[train["surplus_cs"] == 0, "y_onset"].mean())
    va_onset_rate = float(val.loc[val["surplus_cs"] == 0, "y_onset"].mean())
    te_onset_rate = float(test.loc[test["surplus_cs"] == 0, "y_onset"].mean())

    report = {
        "split_mode": config["split"]["mode"],
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "n_test": int(len(test)),
        "target_drift": {
            "train_onset_base_rate": round(tr_onset_rate, 6),
            "val_onset_base_rate": round(va_onset_rate, 6),
            "test_onset_base_rate": round(te_onset_rate, 6),
            "train_delta_log_arr_mean": round(float(train["delta_log_arr"].mean()), 6),
            "val_delta_log_arr_mean": round(float(val["delta_log_arr"].mean()), 6),
            "test_delta_log_arr_mean": round(float(test["delta_log_arr"].mean()), 6),
        },
        "train_vs_val": _summarize(val_drift),
        "train_vs_test": _summarize(test_drift),
        "train_vs_test_all_features": test_drift,
    }

    if output_json is not None:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute feature & target drift monitor")
    parser.add_argument("--config", type=Path, default=bf.DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "data" / "processed" / "drift_report.json",
    )
    args = parser.parse_args()
    report = run_drift_monitor(config_path=args.config, output_json=args.output_json)
    print(
        json.dumps(
            {
                "split_mode": report["split_mode"],
                "target_drift": report["target_drift"],
                "train_vs_val_counts": report["train_vs_val"]["counts"],
                "train_vs_test_counts": report["train_vs_test"]["counts"],
                "train_vs_test_max_psi": report["train_vs_test"]["max_psi"],
                "output_json": str(args.output_json),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
