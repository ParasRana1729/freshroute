"""Compare projected reporting cohorts on a fresh monthly glut-onset holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import lightgbm
import numpy as np
import polars as pl
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import onset_archive_stack as stack  # noqa: E402
from scripts import prepare_onset_archive as prep  # noqa: E402
from scripts.benchmark_onset_archive import NOT_FEATURES, summarize_test  # noqa: E402
from scripts.forecast_reporting_cohort import expected_peer_ranks  # noqa: E402
from scripts.onset_gate_thresholds import (
    alert_thresholds,
    choose_gate_thresholds,
)  # noqa: E402
from scripts.train_model import tune_f1_threshold  # noqa: E402
from scripts.train_onset_f1 import F1_TARGET  # noqa: E402

MARCH_START = date(2026, 2, 28)
APRIL_START = date(2026, 3, 31)
MAY_START = date(2026, 4, 30)
TEST_END = date(2026, 5, 31)
IDENTITY = ["entity", "d"]
COHORT_KEYS = [*IDENTITY, "commodity"]
PROJECTIONS = [
    "weekly_weight",
    "expected_report_weight",
    "projected_n_current",
    "forecast_rank_log_arrival",
    "forecast_rank_log_price",
    "weekly_mean_log_arrival",
    "weekly_mean_log_price",
    "forecast_log_arrival",
    "forecast_log_price",
    "deviation_weekday_log_arrival",
    "deviation_weekday_log_price",
    "forecast_rank_arrival_change",
    "forecast_rank_price_change",
]


def prepare_sources(archive: Path, directory: Path, *, write_market_keys=False):
    """Build both feature sets from the same rows and fixed Train-only clipping bounds."""
    directory.mkdir(parents=True, exist_ok=True)
    cleaned = directory / "cleaned.parquet"
    prep.clean_archive(archive, cleaned, TEST_END)
    config = prep.bf.load_config()
    reports = pl.scan_parquet(cleaned)
    names = ["state_name", "market_center_name", "commodity_name"]
    aliases = [f"source_{name}" for name in names]
    if write_market_keys:
        reports = reports.with_columns(
            pl.col(name).alias(key) for name, key in zip(names, aliases)
        )
    ranked = prep.cross_section(reports, MARCH_START, config).collect()
    if write_market_keys:
        ranked.select(*IDENTITY, *aliases).rename(
            dict(zip(aliases, names))
        ).write_parquet(directory / "market_keys.parquet", compression="zstd")
        ranked = ranked.drop(aliases)
    history = prep.history(ranked)
    del ranked
    # Freeze clipping before the first calibration forecast in March.
    # Save the full day-t peer snapshot before matching next-day rows.
    peer_history = directory / "peer_history.parquet"
    history.select(
        *COHORT_KEYS,
        "log_arrival",
        "log_price",
        "log_arrival_mean_7",
        "log_price_mean_7",
        "state",
        "district",
        "market",
        "p_arr",
        "p_price",
        "surplus",
    ).write_parquet(peer_history, compression="zstd")
    # Every peer group and matched entity belongs to one commodity. Materialize
    # its bucket separately to bound the peak memory of the peer joins.
    parts = []
    for bucket in range(16):
        subset = history.filter(pl.col("commodity") % 16 == bucket)
        if subset.is_empty():
            continue
        part = directory / f"pairs-{bucket:02d}.parquet"
        prep.pair(prep.peers(subset, config["surplus_cs"])).write_parquet(
            part, compression="zstd"
        )
        parts.append(part)
    del history
    pl.scan_parquet(parts).sink_parquet(directory / "pairs.parquet", compression="zstd")
    for part in parts:
        part.unlink()
    projection_path = directory / "report_projection.parquet"
    expected_peer_ranks(pl.scan_parquet(peer_history)).write_parquet(
        projection_path, compression="zstd"
    )
    return open_sources(directory)


def open_sources(directory: Path):
    base = pl.scan_parquet(directory / "pairs.parquet")
    cohort = base.join(
        pl.scan_parquet(directory / "report_projection.parquet"),
        on=COHORT_KEYS,
        how="left",
        maintain_order="left",
    ).with_columns(
        (pl.col("forecast_rank_log_arrival") - pl.col("p_arr")).alias(
            "forecast_rank_arrival_change"
        ),
        (pl.col("forecast_rank_log_price") - pl.col("p_price")).alias(
            "forecast_rank_price_change"
        ),
    )
    return base, cohort


def feature_columns(source: pl.LazyFrame) -> list[str]:
    return [
        column
        for column in source.collect_schema().names()
        if column not in NOT_FEATURES
        and column != "y"
        and not column.startswith(("y_", "commodity_", "district_comm_"))
    ]


def read_frame(source, features, end, start=None):
    if start is None:
        target_columns = ["y", *stack.RANK_TARGETS, "y_arr_level", "y_price_level"]
        window = source.filter(pl.col("date") < end, pl.col("d") % 3 == 0)
    else:
        target_columns = ["y"]
        window = source.filter(
            pl.col("date") > start, pl.col("date") < end, pl.col("surplus") == 0
        )
    return (
        window.select("date", *IDENTITY, *features, *target_columns)
        .sort("d", *prep.INT_KEYS)
        .collect()
    )


def score_window(
    source,
    first,
    last,
    *,
    projected: bool,
    threads: int,
    additional_metadata=(),
):
    """Forecast the joint event, both gates, and optional gate-specific outcomes."""
    features = feature_columns(source)
    train = read_frame(source, features, min(first, APRIL_START)).to_pandas()
    forecast = read_frame(source, features, last, start=first)
    inputs = forecast.select(features).to_pandas()
    y = train.pop("y").to_numpy()
    cutoff = prep.bf.load_config()["surplus_cs"]
    y_arrival = train.pop("y_arr_rank").to_numpy() >= cutoff["arrival_pct_min"]
    y_price = train.pop("y_price_rank").to_numpy() <= cutoff["price_pct_max"]
    y_arrival_level = train.pop("y_arr_level").to_numpy()
    y_price_level = train.pop("y_price_level").to_numpy()
    train.drop(columns=["date", *IDENTITY], inplace=True)

    options = stack.default_params(threads)
    rules = train["rule_state"].to_numpy()
    normal = rules != 3
    outputs = {}
    for name, matrix, labels in (
        ("joint", train.loc[normal], y[normal]),
        ("arrival", train, y_arrival),
        ("price", train, y_price),
    ):
        model = LGBMClassifier(**options).fit(
            matrix, labels, categorical_feature=stack.CATEGORIES
        )
        outputs[name] = model.predict_proba(inputs)[:, 1].astype(np.float32)
    outputs["product"] = outputs["arrival"] * outputs["price"]

    if projected:
        specialist = np.zeros(len(inputs), dtype=np.float32)
        test_rules = inputs["rule_state"].to_numpy()
        for rule in (0, 1, 2):
            rows = rules == rule
            output_rows = test_rules == rule
            if not output_rows.any():
                continue
            model = LGBMClassifier(
                **{**options, "num_leaves": 31, "min_child_samples": 95}
            ).fit(train.loc[rows], y[rows], categorical_feature=stack.CATEGORIES)
            specialist[output_rows] = model.predict_proba(inputs.loc[output_rows])[:, 1]
        outputs["specialist"] = specialist
        for level, observed in (
            ("log_arrival", y_arrival_level),
            ("log_price", y_price_level),
        ):
            model = LGBMRegressor(
                **{
                    **options,
                    "learning_rate": 0.06,
                    "num_leaves": 45,
                    "min_child_samples": 140,
                }
            ).fit(
                train,
                observed - train[level].to_numpy(),
                categorical_feature=stack.CATEGORIES,
            )
            levels = (inputs[level].to_numpy() + model.predict(inputs)).astype(
                np.float32
            )
            outputs[f"expected_{level}"] = levels
            outputs[f"expected_{level}_gap"] = (
                levels - inputs[f"forecast_{level}"].to_numpy()
            )
    extra = PROJECTIONS if projected else []
    metadata = [
        "date",
        *IDENTITY,
        "y",
        *stack.CALIBRATION_COLUMNS,
        "days_since_previous",
        *extra,
        *additional_metadata,
    ]
    return forecast.select(metadata).with_columns(
        *[pl.Series(name, scores) for name, scores in outputs.items()]
    )


def fit_catboost(source, end, threads):
    """Fit a second tree learner on a disjoint sample of historical dates."""
    from catboost import CatBoostClassifier

    features = feature_columns(source)
    train = (
        source.filter(
            pl.col("date") < end, pl.col("d") % 3 == 1, pl.col("surplus") == 0
        )
        .select("d", *features, "y")
        .sort("d", *prep.INT_KEYS)
        .drop("d")
        .collect()
        .to_pandas()
    )
    labels = train.pop("y").to_numpy()
    model = CatBoostClassifier(
        iterations=320,
        depth=6,
        learning_rate=0.075,
        eval_metric="PRAUC",
        l2_leaf_reg=8,
        random_seed=43,
        thread_count=min(threads, 3),
        cat_features=stack.CATEGORIES,
        has_time=True,
        allow_writing_files=False,
        verbose=False,
    ).fit(train, labels)
    return model, features


def forecast_catboost(source, fitted, start, end):
    model, features = fitted
    frame = read_frame(source, features, end, start=start)
    inputs = frame.select(features).to_pandas()
    return frame.select(*IDENTITY).with_columns(
        *[
            pl.Series(
                f"cat_{trees}",
                model.predict_proba(inputs, ntree_end=trees)[:, 1].astype(np.float32),
            )
            for trees in (200, 320)
        ]
    )


def design(label, base, cohort, cat=None):
    """Combine forecast variants keyed by reporting entity and feature date."""
    parts = label.split("+")
    frame = base if parts[0] == "base" else cohort
    if "ensemble" in parts:
        extra = base.select(
            *IDENTITY,
            *[
                pl.col(key).alias(f"base_{key}")
                for key in ("joint", "arrival", "price", "product")
            ],
        )
        frame = frame.join(
            extra, on=IDENTITY, how="left", validate="1:1", maintain_order="left"
        )
    if "catboost" in parts:
        frame = frame.join(
            cat, on=IDENTITY, how="left", validate="1:1", maintain_order="left"
        )
    return frame


def select_model(label, train, validation, threads):
    features = [col for col in train.columns if col not in ("date", *IDENTITY, "y")]
    train_x = train.select(features).to_pandas()
    val_x = validation.select(features).to_pandas()
    labels = validation["y"].to_numpy()
    gates = validation["rule_state"].to_numpy()
    best = None
    for leaves in (8, 16, 32, 64):
        params = {
            **stack.default_params(threads),
            "num_leaves": leaves,
            "n_estimators": 180,
            "min_child_samples": 250,
        }
        model = LGBMClassifier(**params).fit(
            train_x,
            train["y"].to_numpy(),
            categorical_feature=["rule_state", "weekday"],
        )
        for trees in (40, 80, 120, 180):
            scores = model.predict_proba(val_x, num_iteration=trees)[:, 1]
            threshold, global_f1 = tune_f1_threshold(labels, scores)
            cutoffs, gate_f1 = choose_gate_thresholds(labels, scores, gates)
            use_gates = gate_f1 > global_f1 + 0.0005
            trial = {
                "case": label,
                "num_leaves": leaves,
                "trees": trees,
                "f1": gate_f1 if use_gates else global_f1,
                "global_f1": global_f1,
                "gate_f1": gate_f1,
                "pr_auc": float(average_precision_score(labels, scores)),
                "mode": "gate" if use_gates else "global",
                "global_threshold": threshold,
                "gate_thresholds": cutoffs,
            }
            if best is None or validation_order(trial) > validation_order(best[0]):
                best = trial, model, features
    return best


def validation_order(trial):
    return trial["f1"], trial["pr_auc"]


def test_report(frame, fitted):
    selected, model, features = fitted
    threshold = selected["global_threshold"]
    if selected["mode"] == "gate":
        threshold = alert_thresholds(
            frame["rule_state"].to_numpy(), selected["gate_thresholds"]
        )
    score = model.predict_proba(
        frame.select(features).to_pandas(), num_iteration=selected["trees"]
    )[:, 1]
    result, by_date = summarize_test(
        frame["date"].to_pandas(), frame["y"].to_numpy(), score, threshold
    )
    return {"selected": selected, **result, "by_target_date": by_date}


def run_benchmark(base, cohort, archive, output, threads, with_catboost=False):
    labels = ["base", "cohort", "cohort+ensemble"]
    if with_catboost:
        labels.append("cohort+ensemble+catboost")

    base_fit, cohort_fit = [
        score_window(
            frame, MARCH_START, APRIL_START, projected=projected, threads=threads
        )
        for frame, projected in ((base, False), (cohort, True))
    ]
    base_val, cohort_val = [
        score_window(
            frame, APRIL_START, MAY_START, projected=projected, threads=threads
        )
        for frame, projected in ((base, False), (cohort, True))
    ]
    cat_fit = cat_val = cat_model = None
    if with_catboost:
        import catboost

        print("Training CatBoost through February", flush=True)
        earlier = fit_catboost(cohort, MARCH_START, threads)
        cat_fit = forecast_catboost(cohort, earlier, MARCH_START, APRIL_START)
        print("Training CatBoost through March", flush=True)
        cat_model = fit_catboost(cohort, APRIL_START, threads)
        cat_val = forecast_catboost(cohort, cat_model, APRIL_START, MAY_START)
    models = {}
    for label in labels:
        models[label] = select_model(
            label,
            design(label, base_fit, cohort_fit, cat_fit),
            design(label, base_val, cohort_val, cat_val),
            threads,
        )
        print("April validation", label, models[label][0]["f1"], flush=True)

    chosen = max(models, key=lambda label: validation_order(models[label][0]))
    base_test = score_window(
        base, MAY_START, TEST_END, projected=False, threads=threads
    )
    cohort_test = None
    if chosen.startswith("cohort"):
        cohort_test = score_window(
            cohort, MAY_START, TEST_END, projected=True, threads=threads
        )
    cat_test = (
        forecast_catboost(cohort, cat_model, MAY_START, TEST_END)
        if "catboost" in chosen
        else None
    )
    baseline = test_report(base_test, models["base"])
    selected = test_report(
        design(chosen, base_test, cohort_test, cat_test), models[chosen]
    )
    with archive.open("rb") as archive:
        checksum = hashlib.file_digest(archive, "sha256").hexdigest()
    results = {
        "task": "glut_onset_0_to_1",
        "f1_target": F1_TARGET,
        "target_met": selected["f1"] >= F1_TARGET,
        "archive_sha256": checksum,
        "versions": {"lightgbm": lightgbm.__version__, "polars": pl.__version__},
        "clipping_fit_through": str(MARCH_START),
        "train_target_end": str(APRIL_START),
        "validation_target_end": str(MAY_START),
        "test_target_end": str(TEST_END),
        "validation": [models[label][0] for label in labels],
        "baseline": baseline,
        "selected_model": selected,
        "test_f1_difference": selected["f1"] - baseline["f1"],
    }
    if with_catboost:
        results["versions"]["catboost"] = catboost.__version__
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    print(
        f"May held-out F1 {selected['f1']:.2%}. Same-cohort baseline {baseline['f1']:.2%}."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--write-market-keys", action="store_true")
    parser.add_argument("--threads", type=int, default=3)
    parser.add_argument("--with-catboost", action="store_true")
    args = parser.parse_args()
    if args.output is None and not args.prepare_only:
        parser.error("--output is required unless --prepare-only is set")
    base, cohort = prepare_sources(
        args.archive, args.work_dir, write_market_keys=args.write_market_keys
    )
    if not args.prepare_only:
        run_benchmark(
            base, cohort, args.archive, args.output, args.threads, args.with_catboost
        )


if __name__ == "__main__":
    main()
