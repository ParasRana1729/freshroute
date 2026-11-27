"""FreshRoute Plan v3.1: Signal-Aligned Modeling & Surge Ranking (Phase 1).

Implements:
  - Track 1A (Glut-Onset 0 -> 1 Transition Detection):
      Naive Persistence, LogisticRegression (OHE + StandardScaler),
      and regularized XGBClassifier tuned strictly on Val.
  - Track 1B (Arrival Residual Forecasting `delta_log_arr` & Surge Ranking):
      Naive Persistence (delta = 0), Mean-Reversion (-diff_prior_arr),
      XGBRegressor(objective="reg:absoluteerror") [default],
      and secondary reg:squarederror / reg:pseudohubererror models.
  - Outputs:
      data/processed/model_metrics.json
      data/processed/dispatch_list_demo.csv

Run:
  python scripts/train_model.py
  python scripts/train_model.py --split-mode 11d_6d_4d
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    ndcg_score,
    precision_recall_curve,
    r2_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_features import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    assert_no_leakage_columns,
    build_features,
    build_supervised_pairs,
    get_feature_columns,
    load_cleaned_data,
    load_config,
)


def compute_top_k_recall(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Compute recall among the top-K highest-scoring rows."""
    n = len(y_true)
    pos = int(np.sum(y_true))
    if n == 0 or pos == 0:
        return 0.0
    k_eff = min(int(k), n)
    order = np.argsort(-np.asarray(y_score, dtype=np.float64), kind="mergesort")
    hits = int(np.sum(y_true[order[:k_eff]]))
    return float(hits / pos)


def tune_f1_threshold(y_val: np.ndarray, p_val: np.ndarray) -> tuple[float, float]:
    """Select the probability threshold strictly on Val that maximizes Val F1."""
    prec, rec, thrs = precision_recall_curve(y_val, p_val)
    if len(thrs) == 0:
        return 0.5, float(f1_score(y_val, (p_val >= 0.5).astype(int), zero_division=0))
    denom = np.maximum(prec[:-1] + rec[:-1], 1e-12)
    f1s = (2.0 * prec[:-1] * rec[:-1]) / denom
    best_idx = int(np.argmax(f1s))
    best_thr = float(thrs[best_idx])
    best_f1 = float(f1_score(y_val, (p_val >= best_thr).astype(int), zero_division=0))
    return best_thr, best_f1


def evaluate_track_1a_predictions(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
    topk_values: list[int],
    is_constant_zero: bool = False,
) -> dict[str, Any]:
    """Compute Track 1A classification and top-K recall metrics."""
    y_arr = np.asarray(y_true, dtype=np.int32)
    base_rate = float(np.mean(y_arr))
    if is_constant_zero:
        metrics: dict[str, Any] = {
            "base_rate": round(base_rate, 6),
            "pr_auc": round(base_rate, 6),
            "pr_auc_lift": 1.0,
            "roc_auc": 0.5,
            "f1_val_tuned": 0.0,
            "val_threshold": float(threshold),
        }
        for k in topk_values:
            metrics[f"recall_at_{k}"] = 0.0
        return metrics

    scores = np.asarray(y_score, dtype=np.float64)
    pr_auc = float(average_precision_score(y_arr, scores))
    roc_auc = float(roc_auc_score(y_arr, scores))
    f1_val = float(f1_score(y_arr, (scores >= threshold).astype(int), zero_division=0))
    metrics = {
        "base_rate": round(base_rate, 6),
        "pr_auc": round(pr_auc, 6),
        "pr_auc_lift": round(pr_auc / base_rate if base_rate > 0 else 0.0, 4),
        "roc_auc": round(roc_auc, 6),
        "f1_val_tuned": round(f1_val, 6),
        "val_threshold": round(float(threshold), 6),
    }
    for k in topk_values:
        metrics[f"recall_at_{k}"] = round(compute_top_k_recall(y_arr, scores, k), 6)
    return metrics


def _track_1a_candidate_grid(base_params: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a small regularized XGBClassifier grid tuned strictly on Val."""
    common = {
        "tree_method": base_params.get("tree_method", "hist"),
        "scale_pos_weight": float(base_params.get("scale_pos_weight", 1.0)),
        "eval_metric": base_params.get("eval_metric", "aucpr"),
        "random_state": int(base_params.get("random_state", 42)),
        "n_jobs": int(base_params.get("n_jobs", -1)),
    }
    candidates = [
        {
            **common,
            "n_estimators": int(base_params.get("n_estimators", 300)),
            "learning_rate": float(base_params.get("learning_rate", 0.05)),
            "max_depth": int(base_params.get("max_depth", 5)),
            "min_child_weight": int(base_params.get("min_child_weight", 10)),
            "subsample": float(base_params.get("subsample", 0.8)),
            "colsample_bytree": float(base_params.get("colsample_bytree", 0.8)),
            "reg_lambda": float(base_params.get("reg_lambda", 5.0)),
            "reg_alpha": float(base_params.get("reg_alpha", 0.0)),
        },
        {
            **common,
            "n_estimators": 600,
            "learning_rate": 0.03,
            "max_depth": 4,
            "min_child_weight": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_lambda": 10.0,
            "reg_alpha": 2.0,
        },
        {
            **common,
            "n_estimators": 600,
            "learning_rate": 0.03,
            "max_depth": 5,
            "min_child_weight": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.6,
            "reg_lambda": 10.0,
            "reg_alpha": 2.0,
        },
        {
            **common,
            "n_estimators": 600,
            "learning_rate": 0.03,
            "max_depth": 5,
            "min_child_weight": 15,
            "subsample": 0.8,
            "colsample_bytree": 0.5,
            "reg_lambda": 10.0,
            "reg_alpha": 1.0,
        },
        {
            **common,
            "n_estimators": 600,
            "learning_rate": 0.03,
            "max_depth": 6,
            "min_child_weight": 30,
            "subsample": 0.8,
            "colsample_bytree": 0.5,
            "reg_lambda": 15.0,
            "reg_alpha": 2.0,
        },
    ]
    return candidates


def train_and_evaluate_track_1a(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    config: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    """Train and evaluate Track 1A (0 -> 1 glut-onset) models and baselines."""
    assert_no_leakage_columns(feature_cols)
    t1a_cfg = config["models"]["track_1a"]
    topk_values = [int(k) for k in t1a_cfg["topk_values"]]
    seed = int(config["models"].get("random_seed", 42))

    tr_o = train.loc[train["surplus_cs"] == 0].copy()
    va_o = val.loc[val["surplus_cs"] == 0].copy()
    te_o = test.loc[test["surplus_cs"] == 0].copy()

    y_tr = tr_o["y_onset"].to_numpy(dtype=np.int32)
    y_va = va_o["y_onset"].to_numpy(dtype=np.int32)
    y_te = te_o["y_onset"].to_numpy(dtype=np.int32)

    results: dict[str, Any] = {
        "task": "glut_onset_0_to_1",
        "subset_filter": "surplus_cs == 0 & n_comm_day(t) >= 10 & n_comm_day(t+1) >= 10",
        "train_n": int(len(tr_o)),
        "train_pos": int(np.sum(y_tr)),
        "train_base_rate": round(float(np.mean(y_tr)), 6),
        "val_n": int(len(va_o)),
        "val_pos": int(np.sum(y_va)),
        "val_base_rate": round(float(np.mean(y_va)), 6),
        "test_n": int(len(te_o)),
        "test_pos": int(np.sum(y_te)),
        "test_base_rate": round(float(np.mean(y_te)), 6),
        "models": {},
    }

    # 1. Naive Persistence (predicts 0 for all normal markets)
    results["models"]["Naive Persistence"] = {
        "val": evaluate_track_1a_predictions(
            y_va, np.zeros_like(y_va, dtype=np.float64), 0.5, topk_values, is_constant_zero=True
        ),
        "test": evaluate_track_1a_predictions(
            y_te, np.zeros_like(y_te, dtype=np.float64), 0.5, topk_values, is_constant_zero=True
        ),
    }

    # 2. LogisticRegression (OHE on state_name & Train top-20 commodities + imputed StandardScaler)
    t0 = time.perf_counter()
    top_comms = tr_o["commodity_name"].astype(str).value_counts().nlargest(20).index
    for frame in (tr_o, va_o, te_o):
        frame["state_str"] = frame["state_name"].astype(str)
        comm_str = frame["commodity_name"].astype(str)
        frame["commodity_top"] = comm_str.where(comm_str.isin(top_comms), "OTHER")

    lr_cols = feature_cols + ["state_str", "commodity_top"]
    preproc = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                feature_cols,
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                ["state_str", "commodity_top"],
            ),
        ]
    )
    lr_pipe = Pipeline(
        [
            ("preproc", preproc),
            ("clf", LogisticRegression(max_iter=1000, random_state=seed)),
        ]
    )
    lr_pipe.fit(tr_o[lr_cols], y_tr)
    lr_fit_sec = time.perf_counter() - t0

    p_lr_va = lr_pipe.predict_proba(va_o[lr_cols])[:, 1]
    p_lr_te = lr_pipe.predict_proba(te_o[lr_cols])[:, 1]
    lr_thr, _ = tune_f1_threshold(y_va, p_lr_va)
    results["models"]["LogisticRegression"] = {
        "fit_seconds": round(lr_fit_sec, 3),
        "top_commodities_count": int(len(top_comms)),
        "val": evaluate_track_1a_predictions(y_va, p_lr_va, lr_thr, topk_values),
        "test": evaluate_track_1a_predictions(y_te, p_lr_te, lr_thr, topk_values),
    }

    # 3. Regularized XGBClassifier tuned strictly on Val (numeric FEATURE_COLS only)
    X_tr = tr_o[feature_cols]
    X_va = va_o[feature_cols]
    X_te = te_o[feature_cols]

    best_clf: XGBClassifier | None = None
    best_params: dict[str, Any] = {}
    best_val_pr = -1.0
    best_p_va = np.zeros(len(y_va), dtype=np.float64)
    best_fit_sec = 0.0

    for params in _track_1a_candidate_grid(dict(t1a_cfg["xgb_params"])):
        t1 = time.perf_counter()
        clf = XGBClassifier(**params, early_stopping_rounds=60)
        clf.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        fit_sec = time.perf_counter() - t1
        p_va = clf.predict_proba(X_va)[:, 1]
        val_pr = float(average_precision_score(y_va, p_va))
        if val_pr > best_val_pr:
            best_val_pr = val_pr
            best_clf = clf
            best_params = params
            best_p_va = p_va
            best_fit_sec = fit_sec

    assert best_clf is not None
    p_xgb_te = best_clf.predict_proba(X_te)[:, 1]
    xgb_thr, _ = tune_f1_threshold(y_va, best_p_va)

    importances = pd.Series(best_clf.feature_importances_, index=feature_cols).sort_values(
        ascending=False
    )
    top_features = {k: round(float(v), 6) for k, v in importances.head(10).items()}

    results["models"]["XGBClassifier"] = {
        "fit_seconds": round(best_fit_sec, 3),
        "best_iteration": int(best_clf.best_iteration),
        "best_params": best_params,
        "top_features": top_features,
        "val": evaluate_track_1a_predictions(y_va, best_p_va, xgb_thr, topk_values),
        "test": evaluate_track_1a_predictions(y_te, p_xgb_te, xgb_thr, topk_values),
    }

    # Score all Test rows (including surplus_cs == 1 for reference in dispatch output)
    p_xgb_all_test = best_clf.predict_proba(test[feature_cols])[:, 1]
    return results, p_xgb_all_test


def compute_surge_ndcg(
    df_split: pd.DataFrame,
    y_pred: np.ndarray,
    k_values: list[int],
) -> dict[str, Any]:
    """Compute Arrival-Surge NDCG@K within active (commodity_name, target_date) slices."""
    tmp = pd.DataFrame(
        {
            "comm": df_split["commodity_name"].astype(str).to_numpy(),
            "td": df_split["target_date"].to_numpy(),
            "rel": np.maximum(df_split["delta_log_arr"].to_numpy(dtype=np.float64), 0.0),
            "pred": np.asarray(y_pred, dtype=np.float64),
        }
    )
    scores: dict[int, list[float]] = {int(k): [] for k in k_values}
    for _, grp in tmp.groupby(["comm", "td"], sort=False):
        if len(grp) < 2 or float(grp["rel"].sum()) <= 0.0:
            continue
        rel_arr = grp["rel"].to_numpy()[None, :]
        pred_arr = grp["pred"].to_numpy()[None, :]
        for k in k_values:
            scores[int(k)].append(float(ndcg_score(rel_arr, pred_arr, k=int(k))))

    out: dict[str, Any] = {
        "n_evaluated_slices": int(len(scores[int(k_values[0])])) if k_values else 0,
    }
    for k in k_values:
        vals = scores[int(k)]
        out[f"ndcg_at_{k}"] = round(float(np.mean(vals)), 6) if vals else 0.0
    return out


def evaluate_track_1b_predictions(
    df_split: pd.DataFrame,
    y_pred: np.ndarray,
    k_values: list[int],
    include_surge_ndcg: bool = True,
) -> dict[str, Any]:
    """Compute Track 1B continuous residual, reconstructed arrival, and Surge NDCG@K metrics."""
    y_true = df_split["delta_log_arr"].to_numpy(dtype=np.float64)
    log_arr_t = df_split["log_arrival"].to_numpy(dtype=np.float64)
    log_arr_next = df_split["log_arrival_next"].to_numpy(dtype=np.float64)
    pred = np.asarray(y_pred, dtype=np.float64)

    metrics: dict[str, Any] = {
        "rmse": round(float(root_mean_squared_error(y_true, pred)), 6),
        "mae": round(float(mean_absolute_error(y_true, pred)), 6),
        "res_r2": round(float(r2_score(y_true, pred)), 6),
        "recon_r2": round(float(r2_score(log_arr_next, log_arr_t + pred)), 6),
    }
    if include_surge_ndcg:
        metrics.update(compute_surge_ndcg(df_split, pred, k_values))
    return metrics


def train_and_evaluate_track_1b(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    config: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    """Train and evaluate Track 1B (delta_log_arr) models, Persistence, and Mean-Reversion."""
    assert_no_leakage_columns(feature_cols)
    t1b_cfg = config["models"]["track_1b"]
    default_obj = str(t1b_cfg["default_objective"])
    secondary_objs = [str(o) for o in t1b_cfg.get("secondary_objectives", [])]
    k_values = [int(k) for k in t1b_cfg["surge_ndcg_k"]]
    base_xgb_params = dict(t1b_cfg["xgb_params"])

    y_tr = train["delta_log_arr"].to_numpy(dtype=np.float32)
    y_va = val["delta_log_arr"].to_numpy(dtype=np.float32)
    y_te = test["delta_log_arr"].to_numpy(dtype=np.float32)

    results: dict[str, Any] = {
        "task": "arrival_residual_delta_log_arr",
        "default_objective": default_obj,
        "train_n": int(len(train)),
        "val_n": int(len(val)),
        "test_n": int(len(test)),
        "val_zero_delta_frac": round(float(np.mean(y_va == 0.0)), 6),
        "test_zero_delta_frac": round(float(np.mean(y_te == 0.0)), 6),
        "models": {},
    }

    # 1. Naive Persistence (delta_hat = 0.0)
    results["models"]["Naive Persistence"] = {
        "role": "baseline",
        "val": evaluate_track_1b_predictions(
            val, np.zeros(len(val), dtype=np.float64), k_values, include_surge_ndcg=False
        ),
        "test": evaluate_track_1b_predictions(
            test, np.zeros(len(test), dtype=np.float64), k_values, include_surge_ndcg=False
        ),
    }

    # 2. Mean-Reversion (-diff_prior_arr) for Arrival-Surge NDCG@K baseline
    mr_va = (-val["diff_prior_arr"].fillna(0.0)).to_numpy(dtype=np.float64)
    mr_te = (-test["diff_prior_arr"].fillna(0.0)).to_numpy(dtype=np.float64)
    results["models"]["Mean-Reversion (-diff_prior_arr)"] = {
        "role": "ranking_baseline",
        "val": evaluate_track_1b_predictions(val, mr_va, k_values, include_surge_ndcg=True),
        "test": evaluate_track_1b_predictions(test, mr_te, k_values, include_surge_ndcg=True),
    }

    # 3. XGBRegressor models (default reg:absoluteerror + secondary objectives)
    X_tr = train[feature_cols]
    X_va = val[feature_cols]
    X_te = test[feature_cols]

    default_pred_test = np.zeros(len(test), dtype=np.float64)
    objectives = [default_obj] + [o for o in secondary_objs if o != default_obj]
    for obj in objectives:
        params = dict(base_xgb_params)
        params["objective"] = obj
        t0 = time.perf_counter()
        reg = XGBRegressor(**params, early_stopping_rounds=40)
        reg.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        fit_sec = time.perf_counter() - t0

        pred_va = reg.predict(X_va)
        pred_te = reg.predict(X_te)
        if obj == default_obj:
            default_pred_test = pred_te

        label = f"XGBRegressor ({obj})"
        results["models"][label] = {
            "role": "default" if obj == default_obj else "secondary",
            "objective": obj,
            "fit_seconds": round(fit_sec, 3),
            "best_iteration": int(reg.best_iteration),
            "params": params,
            "val": evaluate_track_1b_predictions(val, pred_va, k_values, include_surge_ndcg=True),
            "test": evaluate_track_1b_predictions(test, pred_te, k_values, include_surge_ndcg=True),
        }

    # Verify Plan v3.1 Track 1B success criteria on Test
    persist_te = results["models"]["Naive Persistence"]["test"]
    mr_te_metrics = results["models"]["Mean-Reversion (-diff_prior_arr)"]["test"]
    def_te = results["models"][f"XGBRegressor ({default_obj})"]["test"]
    results["success_checks"] = {
        "beats_persistence_rmse": bool(def_te["rmse"] < persist_te["rmse"]),
        "beats_persistence_mae": bool(def_te["mae"] < persist_te["mae"]),
        "beats_mean_reversion_surge_ndcg10": bool(
            def_te["ndcg_at_10"] > mr_te_metrics["ndcg_at_10"]
        ),
    }

    return results, default_pred_test


def build_dispatch_demo(
    test: pd.DataFrame,
    p_onset_test: np.ndarray,
    pred_delta_test: np.ndarray,
    val_threshold: float,
    top_n: int = 50,
) -> pd.DataFrame:
    """Create top-N predicted glut-onset & arrival-surge dispatch demo table on Test."""
    out = test[
        [
            "date",
            "target_date",
            "state_name",
            "district_name",
            "market_center_name",
            "commodity_name",
            "variety",
            "grade",
            "arrival_tonnes",
            "price_per_kg",
            "log_arrival",
            "surplus_cs",
            "y_onset",
            "delta_log_arr",
        ]
    ].copy()
    out["p_glut_onset"] = np.round(p_onset_test, 4)
    out["pred_onset"] = ((out["surplus_cs"] == 0) & (out["p_glut_onset"] >= val_threshold)).astype(
        int
    )
    out["pred_delta_log_arr"] = np.round(pred_delta_test, 4)
    out["pred_arrival_tonnes_next"] = np.round(
        np.expm1(np.clip(out["log_arrival"].to_numpy() + pred_delta_test, 0.0, None)), 2
    )
    out["pred_price_per_kg_next_persistence"] = out["price_per_kg"]

    normal_only = out.loc[out["surplus_cs"] == 0].sort_values(
        ["p_glut_onset", "pred_delta_log_arr", "arrival_tonnes"],
        ascending=[False, False, False],
    )
    return normal_only.head(top_n).reset_index(drop=True)


def compute_price_persistence_policy(test: pd.DataFrame) -> dict[str, Any]:
    """Document and benchmark 1-day Naive Persistence price policy on Test."""
    y_true = test["log_price_next"].to_numpy(dtype=np.float64)
    y_pred = test["log_price"].to_numpy(dtype=np.float64)
    return {
        "strategy": "Naive Persistence",
        "formula": "price_hat_{t+1} = price_t",
        "rationale": "Zero 1-day price residual R^2 lift on the 24-day window; persistence retained per Plan v3.1.",
        "test_log_price_rmse": round(float(root_mean_squared_error(y_true, y_pred)), 6),
        "test_log_price_mae": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "test_log_price_r2": round(float(r2_score(y_true, y_pred)), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FreshRoute v3.1 Track 1A & 1B models.")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--split-mode", type=str, default=None, help="Override config split.mode")
    args = parser.parse_args()

    t_start = time.perf_counter()
    config = load_config(args.config)
    mode = args.split_mode or config["split"]["mode"]
    preset = config["split"]["presets"][mode]
    train_end_date = preset["train_end"]

    df_raw = load_cleaned_data(config=config)
    feat_df = build_features(df_raw, config=config, train_end_date=train_end_date)
    train, val, test, pair_stats = build_supervised_pairs(
        feat_df, config=config, split_mode=mode, return_stats=True
    )

    feature_cols = get_feature_columns()
    assert_no_leakage_columns(feature_cols)

    track_1a_res, p_onset_test = train_and_evaluate_track_1a(
        train, val, test, feature_cols, config
    )
    track_1b_res, pred_delta_test = train_and_evaluate_track_1b(
        train, val, test, feature_cols, config
    )

    val_threshold = float(track_1a_res["models"]["XGBClassifier"]["val"]["val_threshold"])
    dispatch_df = build_dispatch_demo(
        test, p_onset_test, pred_delta_test, val_threshold=val_threshold, top_n=50
    )

    dispatch_path = ROOT / config["paths"]["dispatch_list_demo"]
    metrics_path = ROOT / config["paths"]["model_metrics"]
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_df.to_csv(dispatch_path, index=False)

    split_details = {
        **pair_stats,
        "train_dates": [str(train["date"].min().date()), str(train["date"].max().date())],
        "train_target_dates": [
            str(train["target_date"].min().date()),
            str(train["target_date"].max().date()),
        ],
        "val_dates": [str(val["date"].min().date()), str(val["date"].max().date())],
        "val_target_dates": [
            str(val["target_date"].min().date()),
            str(val["target_date"].max().date()),
        ],
        "val_weekdays": sorted(val["date"].dt.day_name().unique().tolist()),
        "test_dates": [str(test["date"].min().date()), str(test["date"].max().date())],
        "test_target_dates": [
            str(test["target_date"].min().date()),
            str(test["target_date"].max().date()),
        ],
    }

    metrics_payload: dict[str, Any] = {
        "plan_version": "v3.1",
        "split_mode": mode,
        "split_stats": split_details,
        "feature_count": int(len(feature_cols)),
        "X_columns": feature_cols,
        "price_policy": compute_price_persistence_policy(test),
        "track_1a": track_1a_res,
        "track_1b": track_1b_res,
        "dispatch_demo": {
            "path": str(config["paths"]["dispatch_list_demo"]),
            "rows": int(len(dispatch_df)),
        },
        "total_runtime_seconds": round(time.perf_counter() - t_start, 3),
    }

    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print("=== FreshRoute v3.1 Model Training Summary ===")
    print(f"Split mode: {mode} | Features: {len(feature_cols)} | Runtime: {metrics_payload['total_runtime_seconds']:.2f}s")
    print("\n--- Track 1A: Glut-Onset (0 -> 1) on Test ---")
    for m_name, m_data in track_1a_res["models"].items():
        te = m_data["test"]
        print(
            f"  {m_name:22s} | PR-AUC={te['pr_auc']:.4f} ({te['pr_auc_lift']:.2f}x) "
            f"| ROC-AUC={te['roc_auc']:.4f} | F1={te['f1_val_tuned']:.4f} "
            f"| R@20={te['recall_at_20']:.4f} R@50={te['recall_at_50']:.4f} R@100={te['recall_at_100']:.4f}"
        )
    print("\n--- Track 1B: delta_log_arr & Surge Ranking on Test ---")
    for m_name, m_data in track_1b_res["models"].items():
        te = m_data["test"]
        ndcg5 = f"{te['ndcg_at_5']:.4f}" if "ndcg_at_5" in te else "N/A"
        ndcg10 = f"{te['ndcg_at_10']:.4f}" if "ndcg_at_10" in te else "N/A"
        print(
            f"  {m_name:34s} | RMSE={te['rmse']:.4f} | MAE={te['mae']:.4f} "
            f"| resR2={te['res_r2']:.4f} | reconR2={te['recon_r2']:.4f} "
            f"| NDCG@5={ndcg5} NDCG@10={ndcg10}"
        )
    print(f"\nTrack 1B checks: {track_1b_res['success_checks']}")
    print(f"Wrote {metrics_path} and {dispatch_path} ({len(dispatch_df)} rows).")


if __name__ == "__main__":
    main()
