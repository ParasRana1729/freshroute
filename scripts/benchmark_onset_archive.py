"""Run the extended Track 1A benchmark with chronological train, validation and test windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import lightgbm
import numpy as np
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import prepare_onset_archive as prep  # noqa: E402
from scripts import onset_archive_stack as stack  # noqa: E402
from scripts.train_model import tune_f1_threshold  # noqa: E402
from scripts.train_onset_f1 import F1_TARGET, f1_metrics  # noqa: E402

NOT_FEATURES = {
    "d",
    "date",
    "entity",
    "mkt_comm",
    "district_comm",
    "state_comm",
    "known_onset",
    "surplus",
    "previous_state",
    "previous_surplus",
}
CATEGORIES = [*prep.INT_KEYS, "district", "weekday", "rule_state"]
CHECKPOINTS = (50, 100, 175, 250, 350, 500)
CANDIDATES = (
    dict(num_leaves=31, min_child_samples=150, feature_fraction=0.90),
    dict(num_leaves=63, min_child_samples=100, feature_fraction=0.80),
    dict(num_leaves=127, min_child_samples=80, feature_fraction=0.85),
)


def model_params(candidate: dict, threads: int, trees: int) -> dict:
    return {
        "n_jobs": threads,
        "learning_rate": 0.05,
        "n_estimators": trees,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
        "random_state": 143,
        "reg_lambda": 4,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "max_bin": 127,
        **candidate,
    }


def read_window(source, columns: list[str], start: date | None, end: date):
    """Exclude pairs across boundaries and return eligible normal-market rows."""
    frame = source.filter(pl.col("surplus") == 0, pl.col("date") < end)
    if start is not None:
        frame = frame.filter(pl.col("date") >= start)
    return frame.select(*columns, "date", "y").collect().to_pandas()


def pop_labels(data):
    return data.pop("date"), data.pop("y").to_numpy()


def validation_search(source, columns, train_end, val_end, threads):
    train = read_window(source, columns, None, train_end)
    val = read_window(source, columns, train_end + timedelta(days=1), val_end)
    _, y_train = pop_labels(train)
    _, y_val = pop_labels(val)
    trials = []
    for candidate in CANDIDATES:
        params = model_params(candidate, threads, max(CHECKPOINTS))
        model = LGBMClassifier(**params).fit(
            train, y_train, categorical_feature=CATEGORIES
        )
        for trees in CHECKPOINTS:
            scores = model.predict_proba(val, num_iteration=trees)[:, 1]
            threshold, f1 = tune_f1_threshold(y_val, scores)
            trials.append(
                {
                    "params": {**params, "n_estimators": trees},
                    "threshold": threshold,
                    "f1": f1,
                    "pr_auc": float(average_precision_score(y_val, scores)),
                }
            )
    selected = max(trials, key=lambda trial: (trial["f1"], trial["pr_auc"]))
    return (
        selected,
        trials,
        (len(y_train), int(y_train.sum())),
        (len(y_val), int(y_val.sum())),
    )


def predict_test(source, columns, selected, train_end, val_end, test_end):
    train = read_window(source, columns, None, train_end)
    _, y_train = pop_labels(train)
    model = LGBMClassifier(**selected["params"]).fit(
        train, y_train, categorical_feature=CATEGORIES
    )
    del train, y_train

    test = read_window(source, columns, val_end + timedelta(days=1), test_end)
    dates, y_test = pop_labels(test)
    scores = model.predict_proba(test)[:, 1]
    return dates, y_test, scores


def summarize_test(dates, y_test, scores, threshold):
    metrics = f1_metrics(y_test, scores, threshold)
    metrics["pr_auc"] = float(average_precision_score(y_test, scores))
    row_thresholds = np.broadcast_to(threshold, scores.shape)
    by_target_date = {
        str((day + timedelta(days=1)).date()): f1_metrics(
            y_test[rows], scores[rows], row_thresholds[rows]
        )
        for day, rows in dates.groupby(dates).indices.items()
    }
    return metrics, by_target_date


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--train-through", type=date.fromisoformat, default=prep.TRAIN_END
    )
    parser.add_argument(
        "--validate-through", type=date.fromisoformat, default=prep.VAL_END
    )
    parser.add_argument(
        "--test-through", type=date.fromisoformat, default=prep.TEST_END
    )
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--model", choices=["stack", "direct"], default="stack")
    args = parser.parse_args()
    if not args.train_through < args.validate_through < args.test_through:
        parser.error("Provide increasing train, validation and test end dates.")

    args.work_dir.mkdir(parents=True, exist_ok=True)
    cleaned = args.work_dir / "cleaned.parquet"
    paired = args.work_dir / "pairs.parquet"
    prep.clean_archive(args.archive, cleaned, args.test_through)
    prep.build_pairs(cleaned, args.train_through).write_parquet(
        paired, compression="zstd"
    )
    source = pl.scan_parquet(paired)
    columns = [
        column
        for column in source.collect_schema().names()
        if column not in NOT_FEATURES and column != "y" and not column.startswith("y_")
    ]
    if args.model == "stack":
        selected, trials, fitted, counts = stack.validation_search(
            source, columns, args.train_through, args.validate_through, args.threads
        )
        dates, y_test, scores = stack.score_test(
            source, selected, fitted, args.validate_through, args.test_through
        )
        train_data = {"calibration_rows": counts[0], "calibration_positives": counts[1]}
        val_n = counts[2:]
    else:
        selected, trials, train_n, val_n = validation_search(
            source, columns, args.train_through, args.validate_through, args.threads
        )
        dates, y_test, scores = predict_test(
            source,
            columns,
            selected,
            args.train_through,
            args.validate_through,
            args.test_through,
        )
        train_data = {"rows": train_n[0], "positives": train_n[1]}
    test, by_date = summarize_test(dates, y_test, scores, selected["threshold"])
    with args.archive.open("rb") as archive:
        checksum = hashlib.file_digest(archive, "sha256").hexdigest()
    report = {
        "task": "glut_onset_0_to_1",
        "target": F1_TARGET,
        "target_met": test["f1"] >= F1_TARGET,
        "archive_sha256": checksum,
        "model_family": args.model,
        "versions": {"polars": pl.__version__, "lightgbm": lightgbm.__version__},
        "train": {
            "through": str(args.train_through),
            **train_data,
        },
        "validation": {
            "through": str(args.validate_through),
            "rows": val_n[0],
            "positives": val_n[1],
        },
        "selected": selected,
        "validation_trials": trials,
        "test": {"through": str(args.test_through), **test},
        "test_by_target_date": by_date,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Extended holdout F1: {test['f1']:.2%} (target {F1_TARGET:.0%})")


if __name__ == "__main__":
    main()
