"""Causal cross-commodity context for each reporting market and region."""

from __future__ import annotations

import polars as pl

GROUPS = ("market", "district", "state")
LAGS = (1, 6, 13, 20)
MEASURES = (
    "report_count",
    "commodity_count",
    "surplus_rate",
    "high_arrival_rate",
    "low_price_rate",
    "mean_arrival_rank",
    "mean_price_rank",
    "mean_log_arrival",
    "mean_log_price",
)


def _region_keys(group: str) -> list[str]:
    return ["state"] if group == "state" else ["state", group]


def _daily_context(frame: pl.DataFrame, group: str) -> pl.DataFrame:
    """Summarize reports visible on each date and attach exact calendar lags."""
    prefix = f"local_{group}"
    keys = _region_keys(group)
    daily = (
        frame.group_by(*keys, "d")
        .agg(
            pl.len().cast(pl.Int32).alias(f"{prefix}_report_count"),
            pl.col("commodity")
            .n_unique()
            .cast(pl.Int32)
            .alias(f"{prefix}_commodity_count"),
            pl.col("surplus").mean().cast(pl.Float32).alias(f"{prefix}_surplus_rate"),
            (pl.col("p_arr") >= 0.7)
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_high_arrival_rate"),
            (pl.col("p_price") <= 0.3)
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_low_price_rate"),
            pl.col("p_arr")
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_mean_arrival_rank"),
            pl.col("p_price")
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_mean_price_rank"),
            pl.col("log_arrival")
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_mean_log_arrival"),
            pl.col("log_price")
            .mean()
            .cast(pl.Float32)
            .alias(f"{prefix}_mean_log_price"),
        )
        .sort(*keys, "d")
    )
    current = [f"{prefix}_{measure}" for measure in MEASURES]
    for lag in LAGS:
        lookup = daily.select(
            *keys,
            (pl.col("d") + lag).alias("d"),
            *[pl.col(column).alias(f"{column}_lag_{lag}") for column in current],
        )
        daily = daily.join(lookup, on=[*keys, "d"], how="left")
    return daily


def local_reporting_context(frame: pl.DataFrame) -> pl.DataFrame:
    """Return same-day and past local context keyed to each entity report."""
    required = {
        "entity",
        "d",
        "market",
        "district",
        "state",
        "commodity",
        "surplus",
        "p_arr",
        "p_price",
        "log_arrival",
        "log_price",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"missing local-context columns: {missing}")

    features = frame.select("entity", "d", *GROUPS)
    for group in GROUPS:
        daily = _daily_context(frame, group)
        features = features.join(daily, on=[*_region_keys(group), "d"], how="left")
    return features.drop(*GROUPS).sort("d", "entity")


def feature_columns() -> list[str]:
    """Stable ordered list of model features emitted by this module."""
    columns = []
    for group in GROUPS:
        for measure in MEASURES:
            name = f"local_{group}_{measure}"
            columns.append(name)
            columns.extend(f"{name}_lag_{lag}" for lag in LAGS)
    return columns
