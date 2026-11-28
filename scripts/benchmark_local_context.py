"""Measure cross-commodity local context on the chronological April window."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import benchmark_onset_cohort as cohort
from scripts.local_reporting_context import GROUPS, local_reporting_context


def selected_context_columns() -> list[str]:
    """Compact feature set chosen before the chronological comparison."""
    rates = (
        "report_count",
        "surplus_rate",
        "high_arrival_rate",
        "low_price_rate",
        "mean_arrival_rank",
        "mean_price_rank",
    )
    columns = [f"local_market_{measure}" for measure in rates]
    columns.extend(
        f"local_market_{measure}_lag_{lag}" for lag in (1, 6) for measure in rates
    )
    for group in ("district", "state"):
        columns.extend(
            f"local_{group}_{measure}"
            for measure in (
                "report_count",
                "surplus_rate",
                "high_arrival_rate",
                "low_price_rate",
                "mean_arrival_rank",
                "mean_price_rank",
            )
        )
    return columns


def build_context(directory: Path, output: Path) -> None:
    """Use identities and ranks from each day's reports before target pairing."""
    source = pl.scan_parquet(directory / "peer_history.parquet")
    columns = [
        *cohort.COHORT_KEYS,
        *GROUPS,
        "p_arr",
        "p_price",
        "surplus",
        "log_arrival",
        "log_price",
    ]
    if set(columns) - set(source.collect_schema().names()):
        raise ValueError(
            "Rebuild the cohort work directory with benchmark_onset_cohort.py"
        )
    local_reporting_context(source.select(columns).collect()).select(
        *cohort.IDENTITY, *selected_context_columns()
    ).write_parquet(output, compression="zstd")


def run(directory: Path, output: Path, threads: int) -> None:
    base, projected = cohort.open_sources(directory)
    context_path = directory / "local_reporting_context_unpaired.parquet"
    build_context(directory, context_path)
    local_columns = selected_context_columns()
    context = pl.scan_parquet(context_path).select(*cohort.IDENTITY, *local_columns)
    local = projected.join(
        context,
        on=cohort.IDENTITY,
        how="left",
        validate="m:1",
        maintain_order="left",
    )
    current_columns = [
        f"local_{group}_report_count" for group in ("market", "district", "state")
    ]
    missing = (
        local.select(
            pl.any_horizontal(pl.col(current_columns).is_null()).any().alias("missing")
        )
        .collect()
        .item()
    )
    if missing:
        raise RuntimeError("local context did not cover every paired report")

    base_fit = cohort.score_window(
        base, cohort.MARCH_START, cohort.APRIL_START, projected=False, threads=threads
    )
    base_val = cohort.score_window(
        base, cohort.APRIL_START, cohort.MAY_START, projected=False, threads=threads
    )
    projected_fit = cohort.score_window(
        projected,
        cohort.MARCH_START,
        cohort.APRIL_START,
        projected=True,
        threads=threads,
    )
    projected_val = cohort.score_window(
        projected,
        cohort.APRIL_START,
        cohort.MAY_START,
        projected=True,
        threads=threads,
    )
    local_fit = cohort.score_window(
        local,
        cohort.MARCH_START,
        cohort.APRIL_START,
        projected=True,
        threads=threads,
        additional_metadata=local_columns,
    )
    local_val = cohort.score_window(
        local,
        cohort.APRIL_START,
        cohort.MAY_START,
        projected=True,
        threads=threads,
        additional_metadata=local_columns,
    )

    cases = {
        "cohort+ensemble": (
            cohort.design("cohort+ensemble", base_fit, projected_fit),
            cohort.design("cohort+ensemble", base_val, projected_val),
        ),
        "local_context+ensemble": (
            cohort.design("cohort+ensemble", base_fit, local_fit),
            cohort.design("cohort+ensemble", base_val, local_val),
        ),
    }
    results = {}
    for name, (fit, validation) in cases.items():
        selected = cohort.select_model(name, fit, validation, threads)[0]
        results[name] = selected
        print("April validation", name, selected["f1"], flush=True)
    artifact = {
        "task": "glut_onset_0_to_1",
        "scope": "full eligible national cohort",
        "selection_window": "2026-04-02 through 2026-04-30",
        "test_window": None,
        "claim_status": "development_validation_only",
        "local_context_features": local_columns,
        "validation": results,
        "validation_f1_difference": (
            results["local_context+ensemble"]["f1"] - results["cohort+ensemble"]["f1"]
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=3)
    args = parser.parse_args()
    run(args.work_dir, args.output, args.threads)


if __name__ == "__main__":
    main()
