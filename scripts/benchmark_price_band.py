"""Calibrate alert thresholds in March and replay them on April's national cohort."""

import argparse
import hashlib
import json
from pathlib import Path

import polars as pl
from lightgbm import LGBMClassifier

from scripts import advance_market_signal as advance
from scripts import benchmark_onset_cohort as cohort
from scripts import onset_archive_stack as stack
from scripts import onset_support_reference as support
from scripts import onset_retail_season as retail
from scripts import onset_market_leads as leads
from scripts.onset_gate_thresholds import alert_thresholds, choose_gate_thresholds
from scripts.train_onset_f1 import f1_metrics


def price_band(source):
    low, high, modal = map(pl.col, ("min_price", "max_price", "modal_price"))
    lo, hi = low.log1p(), high.log1p()
    cutoff = pl.col("price_cutoff")
    features = {
        "band_modal_position": (modal - low) / (high - low).replace(0, None),
        "band_floor_margin": lo - cutoff,
        "band_ceiling_margin": hi - cutoff,
        "band_cutoff_inside": (lo <= cutoff) & (cutoff <= hi),
        "band_forecast_margin": pl.col("forecast_log_price") - cutoff,
        "band_midpoint_margin": ((high + low) / 2).log1p() - cutoff,
        "band_location_change": pl.col("log_price_mean_7") - (hi + lo) / 2,
        "band_supply_margin": pl.col("log_arrival") - pl.col("arrival_cutoff"),
        "band_forecast_supply_margin": pl.col("forecast_log_arrival")
        - pl.col("arrival_cutoff"),
    }
    return source.with_columns(
        [v.cast(pl.Float32).alias(k) for k, v in features.items()]
    ), list(features)


def run(
    directory,
    notices=None,
    support_prices=False,
    market_leads=False,
    retail_prices=None,
):
    _, source = cohort.open_sources(directory)
    common = cohort.feature_columns(source)
    if retail_prices is not None:
        source, added = retail.attach(source, directory, retail_prices)
        candidate = "retail_season"
    elif market_leads:
        source, added = leads.attach(source, directory, cohort.MAY_START)
        candidate = "market_leads"
    elif support_prices:
        source, added = support.attach(source, directory)
        candidate = "support_prices"
    elif notices is None:
        source, added = price_band(source)
        candidate = "price_band"
    else:
        source, added = advance.attach(source, directory, notices), advance.FEATURES
        candidate = "advance_notices"
    source = source.filter(pl.col("surplus") == 0)
    full = common + added

    def read(rows):
        return (
            rows.sort("d", *cohort.prep.INT_KEYS)
            .select(*full, "y")
            .collect()
            .to_pandas()
        )

    train = read(
        source.filter(
            pl.col("date") < cohort.MARCH_START,
            (pl.col("y") == 1) | (pl.struct("entity", "d").hash(seed=31) % 4 == 0),
        )
    )
    march = read(
        source.filter(
            pl.col("date") > cohort.MARCH_START, pl.col("date") < cohort.APRIL_START
        )
    )
    y = train.pop("y")
    labels = march.pop("y").to_numpy()
    report = {
        "task": "Track 1A next-day glut onset",
        "selection": "March 2-31, 2026",
        "replay": "April 2-30, 2026 (previously used development window)",
        "fresh_test": None,
        "training_rows": len(y),
        "training_positives": int(y.sum()),
        "features_added": added,
        "models": {},
    }
    if retail_prices is not None:
        report["retail_archive_sha256"] = retail.DIGEST
    if notices is not None:
        counts = {
            "sampled_train": int(train["notice_age_days"].count()),
            "march": int(march["notice_age_days"].count()),
        }
        if not min(counts.values()):
            raise ValueError("No timely notices matched training or calibration")
        report["matched_notice_rows"] = counts
        with notices.open("rb") as stream:
            report["notice_csv_sha256"] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
    models = {}
    for name, cols in [("control", common), (candidate, full)]:
        params = {
            **stack.default_params(3),
            "n_estimators": 320,
            "num_leaves": 63,
            "max_bin": 127,
        }
        model = LGBMClassifier(**params).fit(
            train[cols], y, categorical_feature=stack.CATEGORIES
        )
        best = None
        for trees in (80, 160, 240, 320):
            prob = model.predict_proba(march[cols], num_iteration=trees)[:, 1]
            cuts, f1 = choose_gate_thresholds(
                labels, prob, march["rule_state"].to_numpy()
            )
            if best is None or f1 > best["f1"]:
                best = dict(trees=trees, thresholds=cuts, f1=f1)
        report["models"][name] = {"march": best}
        models[name] = (model, cols, best)
        print(name, "March F1", best["f1"], flush=True)
    report["selected_in_march"] = max(models, key=lambda name: models[name][2]["f1"])
    del train, march
    april = read(
        source.filter(
            pl.col("date") > cohort.APRIL_START, pl.col("date") < cohort.MAY_START
        )
    )
    april_y = april.pop("y").to_numpy()
    if notices is not None:
        report["matched_notice_rows"]["april"] = int(april["notice_age_days"].count())
    if retail_prices is not None:
        report["april_retail_coverage"] = {
            k: int(april[k].notna().sum()) for k in ["retail_season", "produce_season"]
        }
    for name, (model, cols, best) in models.items():
        score = model.predict_proba(april[cols], num_iteration=best["trees"])[:, 1]
        cuts = alert_thresholds(april["rule_state"].to_numpy(), best["thresholds"])
        report["models"][name]["april"] = f1_metrics(april_y, score, cuts)
        if support_prices and name == "control":
            covered = april["announced_rs_per_kg"].notna().to_numpy()
            report["april_coverage_diagnostic"] = support.correction_bound(
                april_y, score >= cuts, covered
            )
        print(name, "April", report["models"][name]["april"], flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--notices", type=Path)
    group.add_argument("--support-prices", action="store_true")
    group.add_argument("--market-leads", action="store_true")
    group.add_argument("--retail-prices", type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            run(
                args.work_dir,
                args.notices,
                args.support_prices,
                args.market_leads,
                args.retail_prices,
            ),
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
