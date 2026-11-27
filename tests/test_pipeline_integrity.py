"""FreshRoute Plan v3.1: Automated Anti-Leakage & Collapse Integrity Suite (Phase 3).

Implements all 5 mandatory checks:
  1. test_1_target_date_non_overlap
  2. test_2_feature_allowlist_and_formula_guard
  3. test_3_zero_future_filtering_in_features
  4. test_4_shuffled_target_collapse
  5. test_5_mandatory_baseline_reporting

Run:
  python -m pytest -v tests/test_pipeline_integrity.py
"""
from __future__ import annotations

import ast
import inspect
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import (
    average_precision_score,
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

FORBIDDEN_TARGET_DAY_COLS: frozenset[str] = frozenset(
    {
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

FORBIDDEN_FORMULA_COLS: frozenset[str] = frozenset(
    {
        "price_z",
        "arrival_z",
        "surplus_S",
    }
)

FORBIDDEN_ALL_COLS: frozenset[str] = FORBIDDEN_TARGET_DAY_COLS | FORBIDDEN_FORMULA_COLS


@pytest.fixture(scope="module")
def pipeline_context() -> dict[str, Any]:
    """Load config, cleaned data, build features, and construct default 10d_7d_4d splits once."""
    config = bf.load_config()
    mode = config["split"]["mode"]
    train_end = config["split"]["presets"][mode]["train_end"]

    cleaned_df = bf.load_cleaned_data(config=config)
    feat_df = bf.build_features(cleaned_df, config=config, train_end_date=train_end)
    train, val, test, stats = bf.build_supervised_pairs(
        feat_df, config=config, split_mode=mode, return_stats=True
    )
    return {
        "config": config,
        "mode": mode,
        "train_end": train_end,
        "cleaned_df": cleaned_df,
        "feat_df": feat_df,
        "train": train,
        "val": val,
        "test": test,
        "stats": stats,
    }


def test_1_target_date_non_overlap(pipeline_context: dict[str, Any]) -> None:
    """Verify strict chronological target-date non-overlap and 7-weekday Val coverage."""
    assert pipeline_context["mode"] == "10d_7d_4d"
    train: pd.DataFrame = pipeline_context["train"]
    val: pd.DataFrame = pipeline_context["val"]
    test: pd.DataFrame = pipeline_context["test"]

    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["target_date"].max() < val["date"].min(), (
        f"Train target_date max ({train['target_date'].max()}) overlaps Val date min ({val['date'].min()})"
    )
    assert val["target_date"].max() < test["date"].min(), (
        f"Val target_date max ({val['target_date'].max()}) overlaps Test date min ({test['date'].min()})"
    )

    # Full 7-weekday coverage on Val for default 10d_7d_4d split
    assert val["date"].dt.dayofweek.nunique() == 7, (
        f"Expected 7 feature weekdays in Val, got {val['date'].dt.dayofweek.nunique()}"
    )
    assert val["target_date"].dt.dayofweek.nunique() == 7, (
        f"Expected 7 target weekdays in Val, got {val['target_date'].dt.dayofweek.nunique()}"
    )


def test_2_feature_allowlist_and_formula_guard() -> None:
    """Assert zero t+1 columns and zero old label-formula columns exist in feature lists or reports."""
    feature_cols = bf.get_feature_columns()
    assert len(feature_cols) > 0

    bad_bf_const = sorted(set(bf.FEATURE_COLS) & FORBIDDEN_ALL_COLS)
    bad_bf_fn = sorted(set(feature_cols) & FORBIDDEN_ALL_COLS)
    assert not bad_bf_const, f"Forbidden columns in build_features.FEATURE_COLS: {bad_bf_const}"
    assert not bad_bf_fn, f"Forbidden columns in get_feature_columns(): {bad_bf_fn}"

    # Verify the guard itself rejects forbidden columns
    for col in ("price_z", "arrival_z", "surplus_S", "target_date", "n_comm_day_next"):
        with pytest.raises(AssertionError):
            bf.assert_no_leakage_columns([col])

    config = bf.load_config()
    cleaning_report_path = ROOT / config["paths"]["cleaning_report"]
    assert cleaning_report_path.exists(), f"Missing {cleaning_report_path}"
    with cleaning_report_path.open("r", encoding="utf-8") as fh:
        cleaning_report = json.load(fh)

    for key in ("cleaned_columns", "X_columns"):
        assert key in cleaning_report, f"Missing '{key}' in cleaning_report.json"
        bad_clean = sorted(set(cleaning_report[key]) & FORBIDDEN_ALL_COLS)
        assert not bad_clean, f"Forbidden columns in cleaning_report.json[{key}]: {bad_clean}"

    metrics_path = ROOT / config["paths"]["model_metrics"]
    assert metrics_path.exists(), f"Missing {metrics_path}"
    with metrics_path.open("r", encoding="utf-8") as fh:
        model_metrics = json.load(fh)

    assert "X_columns" in model_metrics, "Missing 'X_columns' in model_metrics.json"
    bad_metrics = sorted(set(model_metrics["X_columns"]) & FORBIDDEN_ALL_COLS)
    assert not bad_metrics, f"Forbidden columns in model_metrics.json[X_columns]: {bad_metrics}"
    assert model_metrics["X_columns"] == feature_cols, (
        "model_metrics.json X_columns diverges from build_features.get_feature_columns()"
    )


def _strip_docstrings(tree: ast.AST) -> None:
    """Remove leading docstring expression nodes from function/class/module bodies in-place."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body = node.body[1:]


def test_3_zero_future_filtering_in_features(pipeline_context: dict[str, Any]) -> None:
    """Verify build_features() never accesses future columns and is invariant to t+1 perturbations."""
    config = pipeline_context["config"]
    cleaned_df: pd.DataFrame = pipeline_context["cleaned_df"]
    feature_cols = bf.get_feature_columns()
    entity_keys = list(config.get("entity_keys", bf.ENTITY_KEYS))

    # 1. Static AST & signature inspection of build_features and all feature helpers
    inspected_fns = [
        bf.fit_train_iqr_bounds,
        bf.apply_iqr_winsorization,
        bf.fit_shrinkage_priors,
        bf.apply_shrinkage_priors,
        bf._add_cross_sectional_features,
        bf._add_backward_lag_features,
        bf._add_spatial_spillover_features,
        bf._add_calendar_features,
        bf.build_features,
    ]
    forbidden_future_refs = FORBIDDEN_TARGET_DAY_COLS | {"arrival_tonnes_next", "price_per_kg_next", "log_price_next"}

    for fn in inspected_fns:
        sig = inspect.signature(fn)
        bad_params = sorted(set(sig.parameters.keys()) & forbidden_future_refs)
        assert not bad_params, f"{fn.__name__} signature references future params: {bad_params}"

        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
        _strip_docstrings(tree)

        found_refs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_future_refs:
                found_refs.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in forbidden_future_refs:
                found_refs.add(node.attr)
            elif isinstance(node, ast.arg) and node.arg in forbidden_future_refs:
                found_refs.add(node.arg)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in forbidden_future_refs:
                    found_refs.add(node.value)
        assert not found_refs, f"{fn.__name__} AST references future identifiers: {sorted(found_refs)}"

    # 2. Dynamic perturbation & drop invariance around Train/Val boundary (2025-11-05 | 2025-11-06)
    sample = cleaned_df[
        (cleaned_df["date"] >= pd.Timestamp("2025-11-01"))
        & (cleaned_df["date"] <= pd.Timestamp("2025-11-08"))
    ].copy()
    train_end = pd.Timestamp("2025-11-05")
    compare_cols = entity_keys + ["date"] + feature_cols

    feat_base = bf.build_features(sample, config=config, train_end_date=train_end)
    base_train_rows = (
        feat_base[feat_base["date"] <= train_end][compare_cols]
        .sort_values(entity_keys + ["date"], kind="mergesort")
        .reset_index(drop=True)
    )
    base_upto_nov07 = (
        feat_base[feat_base["date"] <= pd.Timestamp("2025-11-07")][compare_cols]
        .sort_values(entity_keys + ["date"], kind="mergesort")
        .reset_index(drop=True)
    )

    # Case A: Drop all t+1 / Val rows (date > 2025-11-05)
    sample_drop_future = sample[sample["date"] <= train_end].copy()
    feat_drop_future = bf.build_features(sample_drop_future, config=config, train_end_date=train_end)
    drop_train_rows = (
        feat_drop_future[compare_cols]
        .sort_values(entity_keys + ["date"], kind="mergesort")
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(base_train_rows, drop_train_rows, check_exact=True)

    # Case B: Perturb Val rows (price x500, arrival x1000) & drop half of 2025-11-06 rows
    sample_pert = sample.copy()
    future_mask = sample_pert["date"] > train_end
    sample_pert.loc[future_mask, "price_per_kg"] = (
        sample_pert.loc[future_mask, "price_per_kg"] * np.float32(500.0)
    )
    sample_pert.loc[future_mask, "arrival_tonnes"] = (
        sample_pert.loc[future_mask, "arrival_tonnes"] * np.float32(1000.0)
    )
    nov06_idx = sample_pert.index[sample_pert["date"] == pd.Timestamp("2025-11-06")]
    sample_pert = sample_pert.drop(index=nov06_idx[::2]).reset_index(drop=True)

    feat_pert = bf.build_features(sample_pert, config=config, train_end_date=train_end)
    pert_train_rows = (
        feat_pert[feat_pert["date"] <= train_end][compare_cols]
        .sort_values(entity_keys + ["date"], kind="mergesort")
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(base_train_rows, pert_train_rows, check_exact=True)

    # Case C: Drop t+1 rows within Val (date > 2025-11-07) while keeping train_end=2025-11-05
    sample_drop_nov08 = sample[sample["date"] <= pd.Timestamp("2025-11-07")].copy()
    feat_drop_nov08 = bf.build_features(sample_drop_nov08, config=config, train_end_date=train_end)
    drop_upto_nov07 = (
        feat_drop_nov08[compare_cols]
        .sort_values(entity_keys + ["date"], kind="mergesort")
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(base_upto_nov07, drop_upto_nov07, check_exact=True)


def test_4_shuffled_target_collapse(pipeline_context: dict[str, Any]) -> None:
    """Verify both Track 1A and Track 1B collapse to noise under permuted training targets."""
    config = pipeline_context["config"]
    train: pd.DataFrame = pipeline_context["train"]
    test: pd.DataFrame = pipeline_context["test"]
    feature_cols = bf.get_feature_columns()
    rng = np.random.default_rng(int(config["models"].get("random_seed", 42)))

    # Track 1A (Glut Onset 0 -> 1): permute y_onset_train
    tr_1a = train.loc[train["surplus_cs"] == 0]
    te_1a = test.loc[test["surplus_cs"] == 0]
    y_tr_1a_shuf = rng.permutation(tr_1a["y_onset"].to_numpy(dtype=np.int32))
    y_te_1a = te_1a["y_onset"].to_numpy(dtype=np.int32)

    xgb_1a_params = dict(config["models"]["track_1a"]["xgb_params"])
    clf = XGBClassifier(**xgb_1a_params)
    clf.fit(tr_1a[feature_cols], y_tr_1a_shuf, verbose=False)
    p_te_shuf = clf.predict_proba(te_1a[feature_cols])[:, 1]

    test_base_rate = float(np.mean(y_te_1a))
    shuf_pr_auc = float(average_precision_score(y_te_1a, p_te_shuf))
    shuf_roc_auc = float(roc_auc_score(y_te_1a, p_te_shuf))

    assert abs(shuf_pr_auc - test_base_rate) <= 0.01, (
        f"Track 1A shuffled PR-AUC ({shuf_pr_auc:.6f}) not within +-0.01 of base rate ({test_base_rate:.6f})"
    )
    assert 0.45 <= shuf_roc_auc <= 0.55, (
        f"Track 1A shuffled ROC-AUC ({shuf_roc_auc:.6f}) outside [0.45, 0.55]"
    )

    # Track 1B (Arrival Residuals delta_log_arr): permute delta_log_arr_train
    y_tr_1b_shuf = rng.permutation(train["delta_log_arr"].to_numpy(dtype=np.float32))
    y_te_1b = test["delta_log_arr"].to_numpy(dtype=np.float32)

    persistence_zero = np.zeros_like(y_te_1b)
    persistence_rmse = float(root_mean_squared_error(y_te_1b, persistence_zero))
    persistence_mae = float(mean_absolute_error(y_te_1b, persistence_zero))

    # Default L1 objective (reg:absoluteerror): loss-aligned MAE >= persistence_MAE & R^2 <= 0.01
    xgb_1b_l1_params = dict(config["models"]["track_1b"]["xgb_params"])
    xgb_1b_l1_params["objective"] = "reg:absoluteerror"
    reg_l1 = XGBRegressor(**xgb_1b_l1_params)
    reg_l1.fit(train[feature_cols], y_tr_1b_shuf, verbose=False)
    pred_te_l1 = reg_l1.predict(test[feature_cols])

    shuf_l1_r2 = float(r2_score(y_te_1b, pred_te_l1))
    shuf_l1_mae = float(mean_absolute_error(y_te_1b, pred_te_l1))
    assert shuf_l1_r2 <= 0.01, f"Track 1B (L1) shuffled R^2 ({shuf_l1_r2:.6f}) > 0.01"
    assert shuf_l1_mae >= persistence_mae, (
        f"Track 1B (L1) shuffled MAE ({shuf_l1_mae:.6f}) < persistence MAE ({persistence_mae:.6f})"
    )

    # L2 objective (reg:squarederror): RMSE >= persistence_RMSE & R^2 <= 0.01
    xgb_1b_l2_params = dict(config["models"]["track_1b"]["xgb_params"])
    xgb_1b_l2_params["objective"] = "reg:squarederror"
    reg_l2 = XGBRegressor(**xgb_1b_l2_params)
    reg_l2.fit(train[feature_cols], y_tr_1b_shuf, verbose=False)
    pred_te_l2 = reg_l2.predict(test[feature_cols])

    shuf_l2_r2 = float(r2_score(y_te_1b, pred_te_l2))
    shuf_l2_rmse = float(root_mean_squared_error(y_te_1b, pred_te_l2))
    assert shuf_l2_r2 <= 0.01, f"Track 1B (L2) shuffled R^2 ({shuf_l2_r2:.6f}) > 0.01"
    assert shuf_l2_rmse >= persistence_rmse, (
        f"Track 1B (L2) shuffled RMSE ({shuf_l2_rmse:.6f}) < persistence RMSE ({persistence_rmse:.6f})"
    )


def _assert_non_null_metrics(block: dict[str, Any], keys: tuple[str, ...], ctx: str) -> None:
    """Assert each expected metric key exists and is a finite non-null number."""
    for key in keys:
        assert key in block, f"Missing '{key}' in {ctx}"
        val = block[key]
        assert val is not None, f"Null value for '{key}' in {ctx}"
        assert isinstance(val, (int, float)) and np.isfinite(val), (
            f"Non-finite value for '{key}' in {ctx}: {val!r}"
        )


def test_5_mandatory_baseline_reporting() -> None:
    """Assert model_metrics.json exists and contains non-null Track 1A & 1B models and baselines."""
    config = bf.load_config()
    metrics_path = ROOT / config["paths"]["model_metrics"]
    assert metrics_path.exists(), f"Missing {metrics_path}"

    with metrics_path.open("r", encoding="utf-8") as fh:
        metrics = json.load(fh)

    assert "track_1a" in metrics and "models" in metrics["track_1a"]
    t1a_models = metrics["track_1a"]["models"]
    t1a_keys = (
        "base_rate",
        "pr_auc",
        "pr_auc_lift",
        "roc_auc",
        "f1_val_tuned",
        "val_threshold",
        "recall_at_20",
        "recall_at_50",
        "recall_at_100",
    )
    for model_name in ("Naive Persistence", "LogisticRegression", "XGBClassifier"):
        assert model_name in t1a_models, f"Missing Track 1A model '{model_name}'"
        for split_name in ("val", "test"):
            assert split_name in t1a_models[model_name], (
                f"Missing '{split_name}' metrics for Track 1A '{model_name}'"
            )
            _assert_non_null_metrics(
                t1a_models[model_name][split_name],
                t1a_keys,
                f"track_1a.{model_name}.{split_name}",
            )

    assert "track_1b" in metrics and "models" in metrics["track_1b"]
    t1b_models = metrics["track_1b"]["models"]
    t1b_reg_keys = ("rmse", "mae", "res_r2", "recon_r2")
    t1b_surge_keys = ("ndcg_at_5", "ndcg_at_10")

    assert "Naive Persistence" in t1b_models, "Missing Track 1B 'Naive Persistence'"
    for split_name in ("val", "test"):
        _assert_non_null_metrics(
            t1b_models["Naive Persistence"][split_name],
            t1b_reg_keys,
            f"track_1b.Naive Persistence.{split_name}",
        )

    for model_name in ("Mean-Reversion (-diff_prior_arr)", "XGBRegressor (reg:absoluteerror)"):
        assert model_name in t1b_models, f"Missing Track 1B model '{model_name}'"
        for split_name in ("val", "test"):
            assert split_name in t1b_models[model_name], (
                f"Missing '{split_name}' metrics for Track 1B '{model_name}'"
            )
            _assert_non_null_metrics(
                t1b_models[model_name][split_name],
                t1b_reg_keys + t1b_surge_keys,
                f"track_1b.{model_name}.{split_name}",
            )
