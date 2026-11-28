"""Combine chronological forecasts of the two conditions for a glut onset."""

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score

from scripts import prepare_onset_archive as prep
from scripts.train_model import tune_f1_threshold

RANK_TARGETS = ["y_arr_rank", "y_price_rank"]
CATEGORIES = [*prep.INT_KEYS, "district", "weekday", "rule_state"]
CALIBRATION_COLUMNS = [
    "p_arr",
    "p_price",
    "rule_state",
    "weekday",
    "n_comm",
    "reports",
    "known_onset_recent",
    "state_comm_onset_rate_recent",
    "mkt_comm_onset_rate_recent",
    "entity_onset_rate_recent",
    "log_arrival_step",
    "log_price_step",
    "log_arrival_std_7",
    "log_price_std_7",
]


def default_params(threads: int) -> dict:
    return dict(
        n_jobs=min(threads, 3),
        learning_rate=0.075,
        n_estimators=100,
        num_leaves=48,
        min_child_samples=120,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
        random_state=124,
        feature_fraction=0.9,
        bagging_fraction=0.85,
        bagging_freq=1,
        reg_lambda=6,
        max_bin=95,
    )


def fit_heads(
    source: pl.LazyFrame, columns: list[str], end: date, threads: int
) -> dict[str, LGBMClassifier]:
    """Use one in three training dates to bound memory and cover every weekday."""
    train = (
        source.filter(pl.col("date") < end, pl.col("date").cast(pl.Int32) % 3 == 0)
        .select(*columns, "y", *RANK_TARGETS)
        .collect()
        .to_pandas()
    )
    joint = train.pop("y").to_numpy()
    cutoff = prep.bf.load_config()["surplus_cs"]
    arrival = train.pop("y_arr_rank").to_numpy() >= cutoff["arrival_pct_min"]
    price = train.pop("y_price_rank").to_numpy() <= cutoff["price_pct_max"]
    normal = train["rule_state"].to_numpy() != 3

    return {
        name: LGBMClassifier(**default_params(threads)).fit(
            dataset, labels, categorical_feature=CATEGORIES
        )
        for name, dataset, labels in (
            ("joint_score", train.loc[normal], joint[normal]),
            ("high_arrival_score", train, arrival),
            ("low_price_score", train, price),
        )
    }


def forecast(
    source: pl.LazyFrame,
    columns: list[str],
    heads: dict[str, LGBMClassifier],
    first: date,
    last: date,
) -> pd.DataFrame:
    window = source.filter(
        pl.col("date") > first, pl.col("date") < last, pl.col("surplus") == 0
    )
    inputs = window.select(*columns, "date", "y").collect().to_pandas()
    outputs = inputs[["date", "y", *CALIBRATION_COLUMNS]].copy()
    for name, model in heads.items():
        outputs[name] = model.predict_proba(inputs[columns])[:, 1].astype(np.float32)
    outputs["product"] = outputs["high_arrival_score"] * outputs["low_price_score"]
    return outputs


def validation_search(source, columns, train_end, val_end, threads):
    """Fit the stack on forward predictions and choose its alert threshold on validation."""
    columns = [
        column
        for column in columns
        if not column.startswith(("commodity_", "district_comm_"))
    ]
    calibration_start = train_end.replace(day=1) - timedelta(days=1)
    earlier_heads = fit_heads(source, columns, calibration_start, threads)
    calibration = forecast(source, columns, earlier_heads, calibration_start, train_end)
    heads = fit_heads(source, columns, train_end, threads)
    validation = forecast(source, columns, heads, train_end, val_end)
    calibration_columns = [
        column for column in calibration.columns if column not in ("date", "y")
    ]
    y_val = validation["y"].to_numpy()
    trials = []
    models: dict[int, LGBMClassifier] = {}
    for name in ("joint_score", "product"):
        scores = validation[name].to_numpy()
        threshold, f1 = tune_f1_threshold(y_val, scores)
        trials.append(
            {
                "model": name,
                "threshold": threshold,
                "f1": f1,
                "pr_auc": float(average_precision_score(y_val, scores)),
            }
        )
    for leaves in (8, 16, 32):
        params = {
            **default_params(threads),
            "num_leaves": leaves,
            "n_estimators": 180,
            "min_child_samples": 250,
        }
        model = LGBMClassifier(**params).fit(
            calibration[calibration_columns],
            calibration["y"],
            categorical_feature=["rule_state", "weekday"],
        )
        models[leaves] = model
        for trees in (40, 80, 120, 180):
            scores = model.predict_proba(
                validation[calibration_columns], num_iteration=trees
            )[:, 1]
            threshold, f1 = tune_f1_threshold(y_val, scores)
            trials.append(
                {
                    "model": "stack",
                    "num_leaves": leaves,
                    "trees": trees,
                    "threshold": threshold,
                    "f1": f1,
                    "pr_auc": float(average_precision_score(y_val, scores)),
                }
            )
    selected = max(trials, key=lambda trial: (trial["f1"], trial["pr_auc"]))
    fitted = heads, columns, calibration_columns, models
    counts = (
        len(calibration),
        int(calibration["y"].sum()),
        len(validation),
        int(y_val.sum()),
    )
    return selected, trials, fitted, counts


def score_test(source, selected: dict[str, Any], fitted, val_end, test_end):
    heads, columns, calibration_columns, models = fitted
    test = forecast(source, columns, heads, val_end, test_end)
    if selected["model"] != "stack":
        scores = test[selected["model"]].to_numpy()
    else:
        model = models[selected["num_leaves"]]
        scores = model.predict_proba(
            test[calibration_columns], num_iteration=selected["trees"]
        )[:, 1]
    return test["date"], test["y"].to_numpy(), scores
