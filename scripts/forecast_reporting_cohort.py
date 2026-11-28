"""Causal projection of the next-day reporting cohort and its ranks."""

import polars as pl

LEVELS = ("log_arrival", "log_price")
WEEKLY_LAGS = ((6, 1.0), (13, 0.65), (20, 0.40), (27, 0.25))


def expected_peer_ranks(history: pl.LazyFrame) -> pl.DataFrame:
    """Estimate ranks in the next weekday's reporting cohort using reports through t."""
    identifiers = ["d", "commodity", "entity"]
    levels = [*LEVELS, "log_arrival_mean_7", "log_price_mean_7"]
    observed = history.select(identifiers + levels)
    current = observed.select(
        *identifiers,
        pl.lit(1).cast(pl.UInt8).alias("current"),
        pl.lit(0, dtype=pl.Float32).alias("weekly_weight"),
        *[pl.col(name).alias(f"current_{name}") for name in levels],
        *[pl.lit(0, dtype=pl.Float32).alias(f"weekly_{name}") for name in LEVELS],
    )
    weekly = []
    for days, weight in WEEKLY_LAGS:
        weekly.append(
            observed.select(
                (pl.col("d") + days).alias("d"),
                "commodity",
                "entity",
                pl.lit(0, dtype=pl.UInt8).alias("current"),
                pl.lit(weight, dtype=pl.Float32).alias("weekly_weight"),
                *[
                    pl.lit(None, dtype=pl.Float32).alias(f"current_{name}")
                    for name in levels
                ],
                *[
                    (pl.col(name) * weight).cast(pl.Float32).alias(f"weekly_{name}")
                    for name in LEVELS
                ],
            )
        )
    projected = (
        pl.concat([current, *weekly])
        .group_by(identifiers)
        .agg(
            pl.col("current").sum().alias("has_current"),
            pl.col("weekly_weight").sum(),
            *[pl.col(f"current_{name}").max() for name in levels],
            *[pl.col(f"weekly_{name}").sum() for name in LEVELS],
        )
        .collect(engine="streaming")
    )

    total_weekly_weight = sum(weight for _, weight in WEEKLY_LAGS)
    cohort = projected.with_columns(
        (
            0.1
            + 0.7 * (pl.col("weekly_weight") / total_weekly_weight)
            + 0.2 * pl.col("has_current")
        )
        .cast(pl.Float32)
        .alias("report_weight"),
        *[
            (pl.col(f"weekly_{level}") / pl.col("weekly_weight").replace(0, None))
            .cast(pl.Float32)
            .alias(f"weekly_mean_{level}")
            for level in LEVELS
        ],
    )
    cohort = cohort.with_columns(
        *[
            pl.coalesce(
                0.7 * pl.col(f"current_{level}")
                + 0.3
                * pl.coalesce(
                    pl.col(f"weekly_mean_{level}"), pl.col(f"current_{level}_mean_7")
                ),
                pl.col(f"weekly_mean_{level}"),
            )
            .cast(pl.Float32)
            .alias(f"forecast_{level}")
            for level in LEVELS
        ]
    )
    slices = ["d", "commodity"]
    ranks = []
    for level in LEVELS:
        measure = f"forecast_{level}"
        keys = slices + [measure]
        ordered = (
            cohort.group_by(keys)
            .agg(pl.col("report_weight").sum().alias("tie_weight"))
            .sort(keys)
        )
        ordered = ordered.with_columns(
            (
                (
                    pl.col("tie_weight").cum_sum().over(slices)
                    - 0.5 * pl.col("tie_weight")
                )
                / pl.col("tie_weight").sum().over(slices)
            )
            .cast(pl.Float32)
            .alias(f"forecast_rank_{level}")
        )
        rank = (
            cohort.filter(pl.col("has_current") > 0)
            .select(*identifiers, measure)
            .join(ordered.select(*keys, f"forecast_rank_{level}"), on=keys, how="left")
            .drop(measure)
        )
        ranks.append(rank)
    counts = cohort.group_by(slices).agg(
        pl.col("report_weight").sum().cast(pl.Float32).alias("expected_report_weight"),
        pl.col("has_current").sum().alias("projected_n_current"),
    )
    features = (
        cohort.filter(pl.col("has_current") > 0)
        .select(
            *identifiers,
            "weekly_weight",
            *[f"weekly_mean_{level}" for level in LEVELS],
            *[f"forecast_{level}" for level in LEVELS],
            *[
                (pl.col(f"current_{level}") - pl.col(f"weekly_mean_{level}")).alias(
                    f"deviation_weekday_{level}"
                )
                for level in LEVELS
            ],
        )
        .join(counts, on=slices, how="left")
    )
    for rank in ranks:
        features = features.join(rank, on=identifiers, how="left")
    return features.sort("d", "commodity", "entity")
