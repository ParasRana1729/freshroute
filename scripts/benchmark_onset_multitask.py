"""Train a shared neural representation of next-day arrival, price and joint onset."""

import argparse
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import polars as pl
import sklearn
from lightgbm import LGBMClassifier
from sklearn.neural_network import MLPClassifier

from scripts import benchmark_onset_cohort as cohort
from scripts import onset_archive_stack as stack
from scripts.onset_gate_thresholds import alert_thresholds, choose_gate_thresholds
from scripts.train_onset_f1 import f1_metrics


def rank_targets(frame):
    # Tomorrow's ranks are auxiliary training labels only.
    cut = cohort.prep.bf.load_config()["surplus_cs"]
    arrival, price = frame.pop("y_arr_rank"), frame.pop("y_price_rank")
    onset = frame.pop("y").to_numpy()
    labels = [onset]
    labels.extend(arrival >= t for t in (0.5, cut["arrival_pct_min"], 0.85))
    labels.extend(price <= t for t in (0.15, cut["price_pct_max"], 0.5))
    labels.extend((arrival >= a) & (price <= p) for a, p in ((0.6, 0.4), (0.8, 0.2)))
    return np.column_stack(labels).astype(bool)


def numeric_encoder(train, names):
    cols = [c for c in names if c not in stack.CATEGORIES]
    sample = train[cols].iloc[::16].to_numpy(dtype="float32")
    low, med, high = np.nanquantile(sample, (0.1, 0.5, 0.9), axis=0).astype("float32")
    scale = np.where(high > low + 0.01, high - low, 1.0)
    # Frequent names and all gate/weekday categories come only from training.
    indicators = {
        c: train[c].value_counts().head(n).index.to_numpy()
        for c, n in [
            ("state", 35),
            ("commodity", 48),
            ("weekday", 7),
            ("rule_state", 3),
        ]
    }

    def encode(frame):
        values = frame[cols].to_numpy(dtype="float32")
        values = np.clip((values - med) / scale, -6, 6)
        np.nan_to_num(values, copy=False)
        indicator_values = [
            (frame[c].to_numpy()[:, None] == cats) for c, cats in indicators.items()
        ]
        return np.ascontiguousarray(
            np.column_stack([values, *indicator_values]), dtype="float32"
        )

    return encode


def train_epochs(x, y, epochs, shard_dir=None):
    net = MLPClassifier(
        hidden_layer_sizes=(96, 48),
        batch_size=1024,
        alpha=0.02,
        learning_rate_init=0.001,
        random_state=124,
        shuffle=False,
    )
    order = np.random.default_rng(124)
    for epoch in range(1, epochs + 1):
        bucket = (epoch - 1) % 4 if shard_dir is not None else 0
        if bucket:
            inputs = np.load(shard_dir / f"x{bucket}.npy", mmap_mode="r")
            targets = np.load(shard_dir / f"y{bucket}.npy", mmap_mode="r")
        else:
            inputs, targets = x, y
        shuffle = order.permutation(len(targets))
        for indices in np.array_split(shuffle, max(1, len(shuffle) // 16384)):
            net.partial_fit(
                inputs[indices], targets[indices], classes=np.arange(y.shape[1])
            )
        yield epoch, net


def run(directory, shard_dir=None):
    _, source = cohort.open_sources(directory)
    names = cohort.feature_columns(source)
    source = source.filter(pl.col("surplus") == 0)

    def read(start, end, fit=False, negative_bucket=0):
        frame = source.filter(pl.col("date") < end)
        if fit:
            frame = frame.filter(
                (pl.col("y") == 1)
                | (pl.struct("entity", "d").hash(seed=31) % 4 == negative_bucket)
            )
        else:
            frame = frame.filter(pl.col("date") > start)
        targets = ["y", "y_arr_rank", "y_price_rank"] if fit else ["y"]
        return (
            frame.sort("d", *cohort.prep.INT_KEYS)
            .select(*names, *targets)
            .collect()
            .to_pandas()
        )

    train = read(None, cohort.MARCH_START, True)
    y = rank_targets(train)
    encode = numeric_encoder(train, names)
    x = encode(train)
    tree = LGBMClassifier(
        **{
            **stack.default_params(3),
            "n_estimators": 80,
            "num_leaves": 63,
            "max_bin": 127,
        }
    )
    tree.fit(train, y[:, 0], categorical_feature=stack.CATEGORIES)
    del train
    unique_training_rows = len(y)
    if shard_dir is not None:
        for bucket in (1, 2, 3):
            partition = read(None, cohort.MARCH_START, True, bucket)
            targets = rank_targets(partition)
            unique_training_rows += int((~targets[:, 0]).sum())
            np.save(shard_dir / f"x{bucket}.npy", encode(partition))
            np.save(shard_dir / f"y{bucket}.npy", targets)
            del partition, targets
    march = read(cohort.MARCH_START, cohort.APRIL_START)
    labels = march.pop("y").to_numpy()
    m = encode(march)
    base = tree.predict_proba(march)[:, 1]
    gates = march["rule_state"].to_numpy()
    del march
    cuts, baseline = choose_gate_thresholds(labels, base, gates)
    best = dict(epoch=0, weight=0.0, f1=baseline, thresholds=cuts)
    tree_cuts = cuts
    selected_net = None
    trials = [best]
    for epoch, net in train_epochs(x, y, 10, shard_dir):
        if epoch not in (2, 5, 10):
            continue
        pred = net.predict_proba(m)[:, 0]
        for weight in (0.25, 0.5, 0.75, 1.0):
            cuts, f1 = choose_gate_thresholds(
                labels, (1 - weight) * base + weight * pred, gates
            )
            entry = dict(epoch=epoch, weight=weight, f1=f1, thresholds=cuts)
            trials.append(entry)
            if f1 > best["f1"]:
                best = entry
                selected_net = copy.deepcopy(net)
        print("Epoch", epoch, "best March", best["f1"], flush=True)
    del x, m
    april = read(cohort.APRIL_START, cohort.MAY_START)
    labels = april.pop("y").to_numpy()
    gates = april["rule_state"].to_numpy()
    base = tree.predict_proba(april)[:, 1]
    score = base
    if selected_net is not None:
        score = (1 - best["weight"]) * base + best[
            "weight"
        ] * selected_net.predict_proba(encode(april))[:, 0]
    return dict(
        task="Track 1A next-day glut onset",
        selection="March 2–31, 2026",
        development_replay="April 2–30, 2026",
        fresh_test=None,
        sklearn_version=sklearn.__version__,
        training_rows=len(y),
        unique_available_neural_training_rows=unique_training_rows,
        rotating_negatives=(shard_dir is not None),
        training_positives=int(y[:, 0].sum()),
        march_trials=trials,
        selected=best,
        april_control=f1_metrics(labels, base, alert_thresholds(gates, tree_cuts)),
        april_selected=f1_metrics(
            labels, score, alert_thresholds(gates, best["thresholds"])
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rotating-negatives", action="store_true")
    args = parser.parse_args()
    if args.rotating_negatives:
        with TemporaryDirectory(dir=args.work_dir) as scratch:
            report = run(args.work_dir, Path(scratch))
    else:
        report = run(args.work_dir)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("April", report["april_selected"], flush=True)
