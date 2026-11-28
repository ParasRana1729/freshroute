"""Compare analog features with the existing ensemble on April validation."""

import argparse
import json
import sys
from pathlib import Path

import lightgbm
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import analog_onset as analog  # noqa: E402
from scripts import benchmark_onset_cohort as cohort  # noqa: E402


def forecast_windows(base, projected, threads):
    """Use the May benchmark's March calibration and April validation forecasts."""
    for start, end in (
        (cohort.MARCH_START, cohort.APRIL_START),
        (cohort.APRIL_START, cohort.MAY_START),
    ):
        plain = cohort.score_window(base, start, end, projected=False, threads=threads)
        peers = cohort.score_window(
            projected, start, end, projected=True, threads=threads
        )
        print(f"Forecasts through {end} complete", flush=True)
        yield cohort.design("cohort+ensemble", plain, peers)


def run(directory: Path, output: Path, threads: int) -> None:
    base, projected = [
        source.filter(pl.col("date") < cohort.MAY_START)
        for source in cohort.open_sources(directory)
    ]
    historical = analog.estimate_transitions(base.select(analog.INPUTS).collect())
    calibration, validation = forecast_windows(base, projected, threads)
    analog_calibration, analog_validation = [
        frame.join(
            historical,
            on=analog.KEYS,
            how="left",
            validate="1:1",
            maintain_order="left",
        )
        for frame in (calibration, validation)
    ]
    if analog_validation["analog_broad_weight"].null_count():
        raise RuntimeError("Missing analog features on the validation cohort")

    results = {}
    for name, fit, val in (
        ("cohort+ensemble", calibration, validation),
        ("cohort+ensemble+analogs", analog_calibration, analog_validation),
    ):
        selected, _, _ = cohort.select_model(name, fit, val, threads)
        results[name] = selected
        print(f"April validation {name} F1 {selected['f1']:.4%}", flush=True)

    report = {
        "task": "glut_onset_0_to_1",
        "scope": "full eligible national cohort",
        "evaluation": "chronological development validation",
        "validation_first_target_date": "2026-04-02",
        "validation_last_target_date": "2026-04-30",
        "validation_rows": validation.height,
        "validation_positives": int(validation["y"].sum()),
        "validation_rows_with_analogs": int(
            (analog_validation["analog_broad_weight"] > 0).sum()
        ),
        "analog_features": analog.FEATURES,
        "versions": {"lightgbm": lightgbm.__version__, "polars": pl.__version__},
        "validation": results,
        "validation_f1_difference": results["cohort+ensemble+analogs"]["f1"]
        - results["cohort+ensemble"]["f1"],
        "test": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=3)
    args = parser.parse_args()
    run(args.work_dir, args.output, args.threads)


if __name__ == "__main__":
    main()
