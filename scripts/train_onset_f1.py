"""Benchmark F1-first Track 1A models on the original chronological split."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_features as bf  # noqa: E402
from scripts import train_model as tm  # noqa: E402

F1_TARGET = 0.80
TREE_COUNTS = (50, 80, 120, 180, 260, 340)


def add_causal_history(
    frame: pd.DataFrame, entity_keys: list[str]
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Build rolling entity and cumulative peer features from observations through day t."""
    frame = frame.sort_values([*entity_keys, "date"], kind="stable").reset_index(drop=True)
    entity = frame.groupby(entity_keys, observed=True, sort=False)
    date = frame["date"]
    yesterday = (date - entity["date"].shift()).eq(pd.Timedelta(days=1))
    previous_surplus = entity["surplus_cs"].shift()
    known_onset = frame["surplus_cs"].where(yesterday & previous_surplus.eq(0))
    measures = ["log_arrival", "log_price", "p_arr_t", "p_price_t", "surplus_cs"]

    # Aggregate by day before accumulating so every row in a peer group sees
    # the same data available at the close of that day.
    observations = frame.assign(observed_onset=known_onset)
    averages = {}
    for name, keys in (
        ("commodity", ["commodity_name"]),
        ("state_commodity", ["state_name", "commodity_name"]),
        ("market_commodity", ["state_name", "market_center_name", "commodity_name"]),
        ("entity", entity_keys),
    ):
        daily = observations.groupby([*keys, "date"], observed=True, sort=True)[
            [*measures, "observed_onset"]
        ].agg(["sum", "count"])
        accumulated = daily.groupby(level=keys, observed=True, sort=False).cumsum()
        means = accumulated.xs("sum", level=1, axis=1) / accumulated.xs("count", level=1, axis=1)
        means = means.add_prefix(f"history_{name}_")
        values = frame[[*keys, "date"]].join(means, on=[*keys, "date"])
        averages.update({column: values[column] for column in means})

    history = {}
    levels = list(range(len(entity_keys)))
    for measure in measures:
        last_five = entity[measure].rolling(5, min_periods=1).mean().droplevel(levels)
        history[f"last_5_mean_{measure}"] = last_five
        if measure != "surplus_cs":
            history[f"last_5_std_{measure}"] = (
                entity[measure].rolling(5, min_periods=2).std().droplevel(levels)
            )
            history[f"change_from_last_5_mean_{measure}"] = frame[measure] - last_five
        if measure in ("p_arr_t", "p_price_t", "surplus_cs"):
            for lag in (1, 2, 3):
                history[f"previous_{lag}_{measure}"] = entity[measure].shift(lag)

    last_surplus = date.where(frame["surplus_cs"].eq(1)).groupby(
        [frame[key] for key in entity_keys], observed=True, sort=False
    ).ffill()
    history["days_since_observed_surplus"] = (date - last_surplus).dt.days

    # At day t, date t-6 matches the weekday of the t+1 forecast.
    observed = frame.set_index([*entity_keys, "date"])[measures]
    for days in (6, 7, 13):
        earlier = pd.MultiIndex.from_frame(
            frame[entity_keys].assign(date=date - pd.Timedelta(days=days))
        )
        values = observed.reindex(earlier).set_axis(frame.index)
        history.update({f"day_minus_{days}_{column}": values[column] for column in measures})

    extra = pd.DataFrame({**averages, **history}, dtype=np.float32)
    return pd.concat([frame, extra], axis=1), list(averages), list(history)


def add_peer_cutoffs(
    frame: pd.DataFrame, surplus_config: dict[str, Any]
) -> tuple[pd.DataFrame, list[str]]:
    """Compare day-t observations with recent commodity-wide cutoff levels."""
    keys = ["commodity_name", "date"]
    commodity_day = frame.groupby(keys, observed=True, sort=False)
    cutoffs = pd.DataFrame({
        "log_arrival": commodity_day["log_arrival"].quantile(surplus_config["arrival_pct_min"]),
        "log_price": commodity_day["log_price"].quantile(surplus_config["price_pct_max"]),
        "daily_count": commodity_day.size(),
    })
    extra = {}
    for days in (0, 1, 2, 6, 7, 13):
        date = frame["date"] - pd.Timedelta(days=days)
        lookup = pd.MultiIndex.from_frame(frame[["commodity_name"]].assign(date=date))
        past = cutoffs.reindex(lookup).set_axis(frame.index)
        extra[f"arrival_margin_day_minus_{days}"] = frame["log_arrival"] - past["log_arrival"]
        extra[f"price_margin_day_minus_{days}"] = past["log_price"] - frame["log_price"]
        if days:
            extra[f"commodity_count_day_minus_{days}"] = past["daily_count"]

    for measure, previous in (("log_arrival", "lag_1_log_arr"), ("log_price", "lag_1_log_price")):
        level = frame[measure]
        proxies = {
            "recent": (level + frame[f"last_5_mean_{measure}"]) / 2,
            "weekday": (level + frame[f"day_minus_6_{measure}"].fillna(
                frame[f"last_5_mean_{measure}"]
            )) / 2,
            "trend": level + 0.5 * (level - frame[previous]).fillna(0),
        }
        for name, estimate in proxies.items():
            extra[f"{name}_{measure}_peer_rank"] = estimate.groupby(
                [frame[key] for key in keys], observed=True, sort=False
            ).rank(pct=True)
    return pd.concat([frame, pd.DataFrame(extra, dtype=np.float32)], axis=1), list(extra)


def f1_metrics(
    y_true: np.ndarray, scores: np.ndarray, threshold: float | np.ndarray
) -> dict[str, Any]:
    decisions = scores >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, decisions, average="binary", zero_division=0
    )
    return {
        "rows": len(y_true),
        "positives": int(y_true.sum()),
        "predicted_positives": int(decisions.sum()),
        "true_positives": int((decisions & (y_true == 1)).sum()),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def benchmark(cleaned: pd.DataFrame, config: dict[str, Any], split_mode: str) -> dict[str, Any]:
    preset = config["split"]["presets"][split_mode]
    features = bf.build_features(cleaned, config, preset["train_end"])
    features, peer_cols, history_cols = add_causal_history(
        features, config.get("entity_keys", bf.ENTITY_KEYS)
    )
    features, cutoff_cols = add_peer_cutoffs(features, config["surplus_cs"])
    train, val, test = bf.build_supervised_pairs(features, config, split_mode)
    del features

    tr = train.loc[train["surplus_cs"].eq(0)]
    va = val.loc[val["surplus_cs"].eq(0)]
    te = test.loc[test["surplus_cs"].eq(0)]
    y_train = tr["y_onset"].to_numpy()
    y_val = va["y_onset"].to_numpy()
    if np.unique(y_train).size != 2 or np.unique(y_val).size != 2:
        raise ValueError("Track 1A training and validation each need both onset classes")

    base_cols = bf.get_feature_columns()
    causal_base = [column for column in base_cols if not column.startswith("prior_")]
    feature_sets = {
        "without_static_priors": causal_base,
        "causal_peer_averages": [*causal_base, *peer_cols],
        "causal_peer_and_entity_history": [*causal_base, *peer_cols, *history_cols],
        "causal_peer_history_and_cutoffs": [*causal_base, *peer_cols, *history_cols, *cutoff_cols],
    }
    base_params = config["models"]["track_1a"]["xgb_params"]
    trials = []
    winner = None
    for feature_set, columns in feature_sets.items():
        bf.assert_no_leakage_columns(columns)
        for depth, positive_weight in ((4, 1.0), (6, 1.0), (7, 4.0)):
            params = {
                **base_params,
                "n_estimators": max(TREE_COUNTS),
                "max_depth": depth,
                "min_child_weight": 8,
                "scale_pos_weight": positive_weight,
            }
            model = XGBClassifier(**params)
            model.fit(tr[columns], y_train)
            best_score = (-1.0, -1.0)
            best_trial = {}
            for tree_count in TREE_COUNTS:
                scores = model.predict_proba(va[columns], iteration_range=(0, tree_count))[:, 1]
                threshold, f1 = tm.tune_f1_threshold(y_val, scores)
                pr_auc = float(average_precision_score(y_val, scores))
                trial = {
                    "feature_set": feature_set,
                    "max_depth": depth,
                    "scale_pos_weight": positive_weight,
                    "trees": tree_count,
                    "threshold": threshold,
                    "validation_f1": f1,
                    "validation_pr_auc": pr_auc,
                }
                if (f1, pr_auc) > best_score:
                    best_score = (f1, pr_auc)
                    best_trial = trial
            trials.append(best_trial)
            if winner is None or best_score > winner[0]:
                winner = best_score, model, columns, best_trial, params

    assert winner is not None
    _, model, columns, selected, params = winner
    trees = selected["trees"]
    threshold = selected["threshold"]
    test_scores = model.predict_proba(te[columns], iteration_range=(0, trees))[:, 1]
    y_test = te["y_onset"].to_numpy()
    test_metrics = f1_metrics(y_test, test_scores, threshold)
    test_metrics["pr_auc"] = float(average_precision_score(y_test, test_scores))
    test_daily = {}
    for date, positions in te.groupby("target_date").indices.items():
        test_daily[str(date.date())] = f1_metrics(y_test[positions], test_scores[positions], threshold)

    baseline, _ = tm.train_and_evaluate_track_1a(train, val, test, base_cols, config)
    baseline_xgb = baseline["models"]["XGBClassifier"]
    return {
        "task": baseline["task"],
        "split_mode": split_mode,
        "subset_filter": baseline["subset_filter"],
        "f1_target": F1_TARGET,
        "test_target_met": test_metrics["f1"] >= F1_TARGET,
        "test_f1_difference_from_baseline": test_metrics["f1"] - baseline_xgb["test"]["f1_val_tuned"],
        "baseline": {split: baseline_xgb[split] for split in ("val", "test")},
        "selected": {**selected, "params": {**params, "n_estimators": trees}},
        "feature_columns": columns,
        "validation_trials": trials,
        "test": test_metrics,
        "test_by_target_date": test_daily,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=bf.DEFAULT_CONFIG_PATH)
    parser.add_argument("--split-mode")
    parser.add_argument("--cleaned-csv", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/onset_f1_metrics.json")
    args = parser.parse_args()
    config = bf.load_config(args.config)
    path = args.cleaned_csv or ROOT / config["paths"]["cleaned_csv"]
    if not path.is_file():
        parser.error(f"Missing {path}. Fetch the benchmark and run scripts/clean_dataset.py first.")
    cleaned = bf.load_cleaned_data(path)
    report = benchmark(cleaned, config, args.split_mode or config["split"]["mode"])
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    report["input"] = {"cleaned_rows": len(cleaned), "cleaned_csv_sha256": checksum.hexdigest()}
    report["versions"] = {"xgboost": xgboost.__version__, "pandas": pd.__version__}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Track 1A test F1: {report['test']['f1']:.2%} (target: {F1_TARGET:.0%})")
    print(f"Baseline test F1 on the same rows: {report['baseline']['test']['f1_val_tuned']:.2%}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
