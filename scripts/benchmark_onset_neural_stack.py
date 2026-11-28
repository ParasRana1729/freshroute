"""Compare neural rank forecasts inside the incumbent stack on chronological validation."""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from scripts import benchmark_onset_cohort as cohort
from scripts import benchmark_onset_multitask as neural

WINDOWS = [
    (cohort.MARCH_START, cohort.APRIL_START),
    (cohort.APRIL_START, cohort.MAY_START),
]


def incumbent(base, projected, start, end):
    baseline = cohort.score_window(base, start, end, projected=False, threads=3)
    print("Baseline heads complete", end, flush=True)
    rich = cohort.score_window(projected, start, end, projected=True, threads=3)
    print("Projected heads complete", end, flush=True)
    cat = cohort.fit_catboost(projected, start, 3)
    scored = cohort.forecast_catboost(projected, cat, start, end)
    return cohort.design("cohort+ensemble+catboost", baseline, rich, scored)


def rank_forecasts(projected, start, end):
    names = cohort.feature_columns(projected)
    normal = projected.filter(pl.col("surplus") == 0)
    train = (
        normal.filter(
            pl.col("date") < start,
            (pl.col("y") == 1) | (pl.struct("entity", "d").hash(seed=31) % 4 == 0),
        )
        .sort("d", *cohort.prep.INT_KEYS)
        .select(*names, "y", "y_arr_rank", "y_price_rank")
        .collect()
        .to_pandas()
    )
    labels = neural.rank_targets(train)
    encode = neural.numeric_encoder(train, names)
    x = encode(train)
    del train
    # Ten epochs were selected with March labels in the direct experiment.
    for _, net in neural.train_epochs(x, labels, 10):
        pass
    del x
    forecast = (
        normal.filter(pl.col("date") > start, pl.col("date") < end)
        .select(*cohort.IDENTITY, *names)
        .collect()
    )
    pred = net.predict_proba(encode(forecast.select(names).to_pandas()))
    outputs = [
        "joint",
        "arr50",
        "arr70",
        "arr85",
        "price15",
        "price30",
        "price50",
        "joint60_40",
        "joint80_20",
    ]
    return forecast.select(*cohort.IDENTITY).with_columns(
        [
            pl.Series("neural_" + label, pred[:, i].astype(np.float32))
            for i, label in enumerate(outputs)
        ]
    )


def compare(directory, output):
    fit_frames, eval_frames = [], []
    for (start, end), frames in zip(WINDOWS, [fit_frames, eval_frames]):
        control = pl.read_parquet(directory / f"incumbent_{end}.parquet")
        heads = pl.read_parquet(directory / f"neural_{end}.parquet")
        joined = control.join(
            heads, on=cohort.IDENTITY, how="left", validate="1:1", maintain_order="left"
        )
        if joined["neural_joint"].null_count():
            raise ValueError("Expected a neural score for every incumbent prediction")
        frames.extend([control, joined])
    results = {}
    for label, train, validation in zip(
        ["incumbent", "incumbent_plus_neural"], fit_frames, eval_frames
    ):
        result, _, _ = cohort.select_model(label, train, validation, 3)
        results[label] = result
        print(label, "April validation", result["f1"], flush=True)
    report = dict(
        task="National Track 1A next-day glut onset",
        stacking_train="March 2–31, 2026",
        validation="April 2–30, 2026",
        eligible_rows=eval_frames[0].height,
        positives=int(eval_frames[0]["y"].sum()),
        source_availability="Archived reports assumed available at day end",
        validation_results=results,
        fresh_test=None,
    )
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--heads-only", action="store_true")
    parser.add_argument(
        "--reuse-heads",
        action="store_true",
        help="Reuse both sets of scores from this same work directory",
    )
    args = parser.parse_args()
    if not args.heads_only and args.output is None:
        parser.error("--output is required for a comparison")
    base, projected = cohort.open_sources(args.work_dir)
    for start, end in WINDOWS:
        if args.reuse_heads:
            continue
        forecast = incumbent(base, projected, start, end)
        forecast.write_parquet(
            args.work_dir / f"incumbent_{end}.parquet", compression="zstd"
        )
        print("Saved incumbent out-of-sample scores through", end, flush=True)
        rank_forecasts(projected, start, end).write_parquet(
            args.work_dir / f"neural_{end}.parquet", compression="zstd"
        )
        print("Saved neural out-of-sample scores through", end, flush=True)
    if not args.heads_only:
        compare(args.work_dir, args.output)


if __name__ == "__main__":
    main()
