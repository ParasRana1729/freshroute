"""FreshRoute Post-v3.1: Probability Calibration & Per-State Fairness/Error Audit.

Evaluates Track 1A (Glut Onset) probability calibration (Brier, LogLoss, ECE,
and strictly Val-fit Isotonic & Platt calibration) plus per-state breakdowns
for both Track 1A and Track 1B on the 10d_7d_4d chronological Test split.

Run:
  python scripts/audit_model.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
    root_mean_squared_error,
)
from xgboost import XGBClassifier, XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_features as bf  # noqa: E402
from scripts import train_model as tm  # noqa: E402


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> tuple[float, list[dict[str, Any]]]:
    """Compute Expected Calibration Error (ECE) and reliability curve bins."""
    y_t = np.asarray(y_true, dtype=np.float64)
    p = np.clip(np.asarray(y_prob, dtype=np.float64), 0.0, 1.0)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bins: list[dict[str, Any]] = []
    n = len(y_t)
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        if b == n_bins - 1:
            mask = (p >= lo) & (p <= hi)
        else:
            mask = (p >= lo) & (p < hi)
        cnt = int(mask.sum())
        if cnt == 0:
            continue
        conf = float(p[mask].mean())
        acc = float(y_t[mask].mean())
        ece += (cnt / max(n, 1)) * abs(acc - conf)
        bins.append(
            {
                "bin": f"[{lo:.1f},{hi:.1f}]",
                "count": cnt,
                "mean_pred": round(conf, 5),
                "empirical_rate": round(acc, 5),
            }
        )
    return round(float(ece), 6), bins


def fit_val_calibrators(
    y_val: np.ndarray, p_val: np.ndarray
) -> dict[str, Any]:
    """Fit Isotonic and Platt (logit-logistic) calibrators strictly on Val."""
    p_clip = np.clip(np.asarray(p_val, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    logits_val = np.log(p_clip / (1.0 - p_clip)).reshape(-1, 1)

    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(p_clip, y_val)

    platt = LogisticRegression(C=1.0, max_iter=1000)
    platt.fit(logits_val, y_val)
    return {"isotonic": iso, "platt": platt}


def apply_calibrator(calibrator: Any, kind: str, p_raw: np.ndarray) -> np.ndarray:
    p_clip = np.clip(np.asarray(p_raw, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    if kind == "isotonic":
        return np.clip(calibrator.predict(p_clip), 0.0, 1.0)
    if kind == "platt":
        logits = np.log(p_clip / (1.0 - p_clip)).reshape(-1, 1)
        return np.clip(calibrator.predict_proba(logits)[:, 1], 0.0, 1.0)
    raise ValueError(f"Unknown calibrator kind: {kind}")


def summarize_calibration(y_true: np.ndarray, p_prob: np.ndarray) -> dict[str, Any]:
    p_clip = np.clip(np.asarray(p_prob, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    ece, bins = compute_ece(y_true, p_clip, n_bins=10)
    return {
        "brier": round(float(brier_score_loss(y_true, p_clip)), 6),
        "log_loss": round(float(log_loss(y_true, p_clip)), 6),
        "ece": ece,
        "pr_auc": round(float(average_precision_score(y_true, p_clip)), 6),
        "roc_auc": round(float(roc_auc_score(y_true, p_clip)), 6),
        "bins": bins,
    }


def audit_per_state_track_1a(
    te_o: pd.DataFrame, p_test: np.ndarray, threshold: float, min_rows: int = 200, min_pos: int = 5
) -> list[dict[str, Any]]:
    work = te_o[["state_name", "y_onset"]].copy()
    work["state_str"] = work["state_name"].astype(str)
    work["p"] = p_test
    rows: list[dict[str, Any]] = []
    for state, grp in work.groupby("state_str"):
        n = len(grp)
        pos = int(grp["y_onset"].sum())
        if n < min_rows or pos < min_pos or pos == n:
            continue
        base = float(pos / n)
        pr = float(average_precision_score(grp["y_onset"], grp["p"]))
        roc = float(roc_auc_score(grp["y_onset"], grp["p"]))
        f1 = float(f1_score(grp["y_onset"], (grp["p"] >= threshold).astype(int), zero_division=0))
        rows.append(
            {
                "state_name": state,
                "n": int(n),
                "positives": pos,
                "base_rate": round(base, 5),
                "pr_auc": round(pr, 5),
                "pr_auc_lift": round(pr / max(base, 1e-9), 2),
                "roc_auc": round(roc, 5),
                "f1": round(f1, 5),
            }
        )
    return sorted(rows, key=lambda r: r["n"], reverse=True)


def audit_per_state_track_1b(
    test_df: pd.DataFrame, pred_delta: np.ndarray, min_rows: int = 200
) -> list[dict[str, Any]]:
    work = test_df[["state_name", "delta_log_arr"]].copy()
    work["state_str"] = work["state_name"].astype(str)
    work["pred"] = pred_delta
    rows: list[dict[str, Any]] = []
    for state, grp in work.groupby("state_str"):
        n = len(grp)
        if n < min_rows:
            continue
        y_true = grp["delta_log_arr"].to_numpy(dtype=np.float64)
        y_pred = grp["pred"].to_numpy(dtype=np.float64)
        zeros = np.zeros_like(y_true)
        rmse = float(root_mean_squared_error(y_true, y_pred))
        mae = float(mean_absolute_error(y_true, y_pred))
        p_rmse = float(root_mean_squared_error(y_true, zeros))
        p_mae = float(mean_absolute_error(y_true, zeros))
        rows.append(
            {
                "state_name": state,
                "n": int(n),
                "rmse": round(rmse, 5),
                "persistence_rmse": round(p_rmse, 5),
                "rmse_improvement": round(p_rmse - rmse, 5),
                "mae": round(mae, 5),
                "persistence_mae": round(p_mae, 5),
                "mae_improvement": round(p_mae - mae, 5),
                "res_r2": round(float(r2_score(y_true, y_pred)), 5),
            }
        )
    return sorted(rows, key=lambda r: r["n"], reverse=True)


def run_audit(config_path: Path | str = bf.DEFAULT_CONFIG_PATH, output_json: Path | str | None = None) -> dict[str, Any]:
    config = bf.load_config(config_path)
    metrics_path = ROOT / config["paths"]["model_metrics"]
    saved_metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}

    preset = config["split"]["presets"][config["split"]["mode"]]
    df_clean = bf.load_cleaned_data(ROOT / config["paths"]["cleaned_csv"], config=config)
    feat_df = bf.build_features(df_clean, config, train_end_date=preset["train_end"])
    train, val, test = bf.build_supervised_pairs(feat_df, config)
    feature_cols = bf.get_feature_columns()

    # Refit Track 1A winner using saved best_params (or config default)
    tr_o = train.loc[train["surplus_cs"] == 0]
    va_o = val.loc[val["surplus_cs"] == 0]
    te_o = test.loc[test["surplus_cs"] == 0]
    y_tr_1a = tr_o["y_onset"].to_numpy(dtype=np.int32)
    y_va_1a = va_o["y_onset"].to_numpy(dtype=np.int32)
    y_te_1a = te_o["y_onset"].to_numpy(dtype=np.int32)

    t1a_saved = saved_metrics.get("track_1a", {}).get("models", {}).get("XGBClassifier", {})
    xgb_1a_params = dict(t1a_saved.get("best_params") or config["models"]["track_1a"]["xgb_params"])
    clf = XGBClassifier(**xgb_1a_params, early_stopping_rounds=40)
    clf.fit(tr_o[feature_cols], y_tr_1a, eval_set=[(va_o[feature_cols], y_va_1a)], verbose=False)
    p_va_raw = clf.predict_proba(va_o[feature_cols])[:, 1]
    p_te_raw = clf.predict_proba(te_o[feature_cols])[:, 1]
    thr, _ = tm.tune_f1_threshold(y_va_1a, p_va_raw)

    calibrators = fit_val_calibrators(y_va_1a, p_va_raw)
    p_te_iso = apply_calibrator(calibrators["isotonic"], "isotonic", p_te_raw)
    p_te_platt = apply_calibrator(calibrators["platt"], "platt", p_te_raw)

    # Refit Track 1B default (reg:absoluteerror)
    t1b_params = dict(config["models"]["track_1b"]["xgb_params"])
    t1b_params["objective"] = str(config["models"]["track_1b"]["default_objective"])
    reg = XGBRegressor(**t1b_params, early_stopping_rounds=40)
    reg.fit(
        train[feature_cols],
        train["delta_log_arr"].to_numpy(dtype=np.float32),
        eval_set=[(val[feature_cols], val["delta_log_arr"].to_numpy(dtype=np.float32))],
        verbose=False,
    )
    pred_1b_te = reg.predict(test[feature_cols])

    report = {
        "split_mode": config["split"]["mode"],
        "track_1a_calibration_test": {
            "uncalibrated": summarize_calibration(y_te_1a, p_te_raw),
            "val_isotonic": summarize_calibration(y_te_1a, p_te_iso),
            "val_platt": summarize_calibration(y_te_1a, p_te_platt),
        },
        "track_1a_per_state_test": audit_per_state_track_1a(te_o, p_te_raw, threshold=thr),
        "track_1b_per_state_test": audit_per_state_track_1b(test, pred_1b_te),
    }

    # Highlight Tamil Nadu vs rest-of-India geographic parity check
    tn_1a = [r for r in report["track_1a_per_state_test"] if r["state_name"] == "TAMIL NADU"]
    tn_1b = [r for r in report["track_1b_per_state_test"] if r["state_name"] == "TAMIL NADU"]
    report["tamil_nadu_bias_check"] = {
        "track_1a": tn_1a[0] if tn_1a else None,
        "track_1b": tn_1b[0] if tn_1b else None,
        "states_beating_persistence_rmse": sum(
            1 for r in report["track_1b_per_state_test"] if r["rmse_improvement"] > 0
        ),
        "states_beating_persistence_mae": sum(
            1 for r in report["track_1b_per_state_test"] if r["mae_improvement"] > 0
        ),
        "total_audited_states_1b": len(report["track_1b_per_state_test"]),
    }

    if output_json is not None:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute calibration & per-state audit")
    parser.add_argument("--config", type=Path, default=bf.DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "data" / "processed" / "model_audit_report.json",
    )
    args = parser.parse_args()
    report = run_audit(config_path=args.config, output_json=args.output_json)
    print(
        json.dumps(
            {
                "calibration_brier": {
                    k: v["brier"] for k, v in report["track_1a_calibration_test"].items()
                },
                "calibration_ece": {
                    k: v["ece"] for k, v in report["track_1a_calibration_test"].items()
                },
                "tamil_nadu_bias_check": report["tamil_nadu_bias_check"],
                "output_json": str(args.output_json),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
