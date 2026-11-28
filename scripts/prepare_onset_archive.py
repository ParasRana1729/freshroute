"""Build causal features for the six-month glut-onset experiment."""

from datetime import date
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_features as bf  # noqa: E402

TRAIN_END = date(2026, 2, 28)
VAL_END = date(2026, 3, 31)
TEST_END = date(2026, 4, 30)
KEYS = bf.ENTITY_KEYS
NAMES = [*KEYS, "district_name"]
LEVELS = ["log_arrival", "log_price", "p_arr", "p_price"]
INT_KEYS = ["state", "market", "commodity", "variety_id", "grade_id"]
DAY_KEYS = ["d", "commodity"]
EPS = 1e-6


def clean_archive(archive: Path, output: Path, end_date: date) -> None:
    """Normalize units and combine daily duplicate records at the existing entity grain."""
    raw_levels = [
        "arrival_quantity",
        "min_price",
        "max_price",
        "modal_price",
        "latitude",
        "longitude",
    ]
    string_columns = [*NAMES, "date", "price_unit", "arrival_units"]
    raw = pl.scan_csv(
        archive,
        schema_overrides={
            **dict.fromkeys(raw_levels, pl.Float64),
            **dict.fromkeys(string_columns, pl.String),
        },
    )
    raw = (
        raw.select(*string_columns, *raw_levels)
        .with_columns(
            pl.col("date").str.to_date(strict=False),
            pl.col(NAMES).str.strip_chars().str.to_uppercase(),
            pl.col("price_unit").str.to_lowercase(),
        )
        .filter(
            pl.col("date") <= end_date,
            pl.col("price_unit").str.contains("quintal"),
            pl.all_horizontal(pl.col(["arrival_quantity", "modal_price"]) >= 0),
            pl.all_horizontal(
                pl.col(
                    ["state_name", "commodity_name", "market_center_name"]
                ).is_not_null()
            ),
        )
        .with_columns(
            pl.col(["variety", "grade", "district_name"])
            .fill_null("UNKNOWN")
            .replace("", "UNKNOWN"),
            pl.when(pl.col("min_price") >= 0)
            .then(pl.col("min_price"))
            .otherwise(pl.col("modal_price"))
            .alias("min_price"),
            pl.when(pl.col("max_price") >= 0)
            .then(pl.col("max_price"))
            .otherwise(pl.col("modal_price"))
            .alias("max_price"),
        )
    )
    cleaned = (
        raw.group_by(*KEYS, "date")
        .agg(
            pl.col("arrival_quantity").sum().cast(pl.Float32).alias("arrival"),
            *[
                pl.when(pl.col("arrival_quantity").sum() > 0)
                .then(
                    (pl.col(p) * pl.col("arrival_quantity")).sum()
                    / pl.col("arrival_quantity").sum()
                    / 100
                )
                .otherwise(pl.col(p).mean() / 100)
                .cast(pl.Float32)
                .alias(p)
                for p in ("modal_price", "min_price", "max_price")
            ],
            pl.col("district_name").first(),
            pl.col(["latitude", "longitude"]).median().cast(pl.Float32),
        )
        .sort(*KEYS, "date")
    )
    cleaned.sink_parquet(output, compression="zstd")


def cross_section(
    cleaned: pl.LazyFrame, fit_through: date, config: dict
) -> pl.LazyFrame:
    """Fit clipping bounds on training dates and compute per-commodity daily ranks."""
    fit = (
        cleaned.filter(pl.col("date") <= fit_through)
        .group_by("commodity_name")
        .agg(
            *[
                pl.col(col).quantile(q, interpolation="linear").alias(f"{col}_q{i}")
                for col in ("arrival", "modal_price")
                for i, q in enumerate((0.25, 0.75), 1)
            ]
        )
    )
    clipped = cleaned.join(fit, on="commodity_name", how="left", maintain_order="left")
    clipping = config["winsorization"]
    for col, mult in [
        ("arrival", clipping["arrival_iqr_k"]),
        ("modal_price", clipping["price_iqr_k"]),
    ]:
        q1, q3 = pl.col(f"{col}_q1"), pl.col(f"{col}_q2")
        iqr = q3 - q1
        clipped = clipped.with_columns(
            pl.when(iqr > 0)
            .then(pl.col(col).clip(q1 - mult * iqr, q3 + mult * iqr))
            .otherwise(pl.col(col))
            .cast(pl.Float32)
            .alias(col)
        )
    cutoff = config["surplus_cs"]
    active_count = config["cross_section"]["min_n_comm_day"]
    frame = (
        clipped.with_columns(
            pl.col("date").cast(pl.Int32).alias("d"),
            pl.col("date").dt.weekday().cast(pl.Int8).alias("weekday"),
            pl.col("date").dt.month().cast(pl.Int8).alias("month"),
            pl.col("arrival").log1p().alias("log_arrival"),
            pl.col("modal_price").log1p().alias("log_price"),
            (
                (
                    (pl.col("max_price") - pl.col("min_price"))
                    / pl.col("modal_price").clip(lower_bound=EPS)
                ).clip(0, 5)
            ).alias("price_spread"),
            **{
                alias: pl.col(col).cast(pl.Categorical).to_physical()
                for alias, col in zip(INT_KEYS, KEYS)
            },
            district=pl.col("district_name").cast(pl.Categorical).to_physical(),
        )
        .drop(
            *[f"{col}_q{i}" for col in ("arrival", "modal_price") for i in (1, 2)],
            *NAMES,
        )
        .with_columns(
            pl.struct(INT_KEYS).hash(seed=13).alias("entity"),
            pl.struct(["state", "market", "commodity"]).hash(seed=17).alias("mkt_comm"),
            pl.struct(["state", "district", "commodity"])
            .hash(seed=19)
            .alias("district_comm"),
            pl.struct(["state", "commodity"]).hash(seed=23).alias("state_comm"),
        )
        .with_columns(
            n_comm=pl.len().over(DAY_KEYS).cast(pl.Int32),
            p_arr=(
                pl.col("arrival").rank("average").over(DAY_KEYS)
                / pl.len().over(DAY_KEYS)
            ).cast(pl.Float32),
            p_price=(
                pl.col("modal_price").rank("average").over(DAY_KEYS)
                / pl.len().over(DAY_KEYS)
            ).cast(pl.Float32),
        )
        .with_columns(
            pl.when(pl.col("n_comm") >= active_count)
            .then(
                (
                    (pl.col("p_arr") >= cutoff["arrival_pct_min"])
                    & (pl.col("p_price") <= cutoff["price_pct_max"])
                ).cast(pl.Int8)
            )
            .alias("surplus"),
            pl.when(pl.col("n_comm") >= active_count)
            .then(
                (
                    (pl.col("p_arr") >= cutoff["arrival_pct_min"]).cast(pl.Int8)
                    + 2 * (pl.col("p_price") <= cutoff["price_pct_max"]).cast(pl.Int8)
                )
            )
            .alias("rule_state"),
        )
    )
    return frame


def history(frame: pl.DataFrame) -> pl.DataFrame:
    """Calculate entity histories from reports available through the feature day."""
    frame = frame.sort(["entity", "d"])
    entity_key = "entity"
    rolls = []
    for col in LEVELS:
        for n in (3, 7, 14, 28):
            rolls.append(
                pl.col(col)
                .rolling_mean(n, min_samples=1)
                .over(entity_key)
                .alias(f"{col}_mean_{n}")
            )
        for n in (7, 28):
            rolls.append(
                pl.col(col)
                .rolling_std(n, min_samples=2)
                .over(entity_key)
                .alias(f"{col}_std_{n}")
            )
        for n in (1, 2, 3, 7):
            rolls.append(pl.col(col).shift(n).over(entity_key).alias(f"{col}_lag_{n}"))
        step = pl.col(col) - pl.col(col).shift().over(entity_key)
        rolls.append(step.alias(f"{col}_step"))
    frame = frame.with_columns(
        *rolls,
        (pl.col("d") - pl.col("d").shift(1).over(entity_key)).alias(
            "days_since_previous"
        ),
        pl.col("d").cum_count().over(entity_key).alias("reports"),
        pl.col("rule_state").shift(1).over(entity_key).alias("previous_state"),
        pl.col("surplus").shift(1).over(entity_key).alias("previous_surplus"),
        (
            pl.col("d")
            - pl.when(pl.col("surplus") == 1)
            .then(pl.col("d"))
            .forward_fill()
            .over(entity_key)
        ).alias("days_since_glut"),
    ).with_columns(
        pl.when(
            (pl.col("previous_surplus") == 0) & (pl.col("days_since_previous") == 1)
        )
        .then(pl.col("surplus"))
        .alias("known_onset")
    )
    frame = frame.with_columns(
        pl.col("known_onset")
        .rolling_mean(14, min_samples=1)
        .over(entity_key)
        .cast(pl.Float32)
        .alias("known_onset_recent"),
        pl.col("known_onset")
        .rolling_mean(28, min_samples=1)
        .over(entity_key)
        .cast(pl.Float32)
        .alias("known_onset_month"),
        *[
            (pl.col(col) - pl.col(f"{col}_mean_7")).alias(f"{col}_anomaly_7")
            for col in LEVELS
        ],
        *[
            (pl.col(col) - pl.col(f"{col}_mean_28")).alias(f"{col}_anomaly_28")
            for col in LEVELS
        ],
    )
    return frame


def peers(frame: pl.DataFrame, cutoff: dict) -> pl.DataFrame:
    """Add historical and same-day peer features to unpaired reports."""
    frame = frame.sort("d")
    for group in ["commodity", "state_comm", "district_comm", "mkt_comm", "entity"]:
        keys = [group, "d"]
        aggregates = [
            *[
                pl.col(col).mean().cast(pl.Float32).alias(f"{group}_{col}_day_mean")
                for col in LEVELS
            ],
            pl.col("surplus")
            .mean()
            .cast(pl.Float32)
            .alias(f"{group}_surplus_day_rate"),
            pl.col("known_onset").sum().alias("onsets"),
            pl.col("known_onset").count().alias("onset_rows"),
            pl.len().cast(pl.Int32).alias(f"{group}_day_count"),
        ]
        if group == "commodity":
            aggregates += [
                pl.col("log_arrival")
                .quantile(cutoff["arrival_pct_min"], interpolation="linear")
                .alias("arrival_cutoff"),
                pl.col("log_price")
                .quantile(cutoff["price_pct_max"], interpolation="linear")
                .alias("price_cutoff"),
            ]
        daily = frame.group_by(keys).agg(*aggregates).sort(keys)
        daily = daily.with_columns(
            (
                pl.col("onsets").cum_sum().over(group)
                / pl.col("onset_rows").cum_sum().over(group).replace(0, None)
            )
            .cast(pl.Float32)
            .alias(f"{group}_onset_rate"),
            (
                pl.col("onsets").rolling_sum(28, min_samples=1).over(group)
                / pl.col("onset_rows")
                .rolling_sum(28, min_samples=1)
                .over(group)
                .replace(0, None)
            )
            .cast(pl.Float32)
            .alias(f"{group}_onset_rate_recent"),
        ).drop("onsets", "onset_rows")
        frame = frame.join(daily, on=keys, how="left")
        if group == "commodity":
            for days in (1, 6, 13, 20):
                lookup = daily.select(
                    group,
                    (pl.col("d") + days).alias("d"),
                    pl.col("arrival_cutoff").alias(f"arrival_cutoff_lag_{days}"),
                    pl.col("price_cutoff").alias(f"price_cutoff_lag_{days}"),
                    pl.col("commodity_day_count").alias(
                        f"commodity_day_count_lag_{days}"
                    ),
                )
                frame = frame.join(lookup, on=keys, how="left")
    return frame


def pair(frame: pl.DataFrame) -> pl.DataFrame:
    """Pair consecutive reports with active commodity groups on both days."""
    lookup = frame.select(
        "entity",
        (pl.col("d") - 1).alias("d"),
        pl.col("surplus").alias("y"),
        pl.col("p_arr").alias("y_arr_rank"),
        pl.col("p_price").alias("y_price_rank"),
        pl.col("log_arrival").alias("y_arr_level"),
        pl.col("log_price").alias("y_price_level"),
    )
    return (
        frame.join(lookup, on=["entity", "d"], how="inner")
        .filter(pl.col("surplus").is_not_null(), pl.col("y").is_not_null())
        .sort("d", *INT_KEYS)
    )


def build_pairs(clean_path: Path, fit_through: date) -> pl.DataFrame:
    """Build causal features before attaching the next-day outcomes."""
    config = bf.load_config()
    historical = history(
        cross_section(pl.scan_parquet(clean_path), fit_through, config).collect()
    )
    return pair(peers(historical, config["surplus_cs"]))
