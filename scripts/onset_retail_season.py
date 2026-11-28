"""Construct historical retail seasonality from a 2024-vintage public export."""

import hashlib
from datetime import date

import polars as pl

SOURCE = (
    "https://ckandev.indiadataportal.com/dataset/1a59d7e5-baf1-4c4a-b10f-55a6367f82f7/"
    "resource/45f8c494-03d2-46b5-aa1a-a5e3656c3da6/download/"
    "daily-retail-prices-of-essential-commodities.csv"
)
DIGEST = "8325431b8258d22813e9d85c8f220f6b7e0f3c91fcda9a0337a39d4d65aa0c0a"
RELEASE = date(2024, 8, 28)
BASKET = ["POTATO", "ONION", "TOMATO"]
ALIASES = {
    "GUR(JAGGERY)": "GUR",
    "WHEAT ATTA": "ATTA (WHEAT)",
    "BENGAL GRAM DAL(CHANA DAL)": "GRAM DAL",
    "GREEN GRAM DAL(MOONG DAL)": "MOONG DAL",
    "MASUR DAL": "MASOOR DAL",
    "BLACK GRAM DAL(URD DAL)": "URAD DAL",
    "RED GRAM SPLIT/ARHAR DAL/TUR DAL": "TUR/ARHAR DAL",
}
KEYS = ["state_name", "retail_crop", "fortnight"]
FEATURES = [
    "retail_season",
    "retail_season_change",
    "produce_season",
    "produce_season_change",
]


def fortnight(day):
    return (day.dt.month().cast(pl.Int32) - 1) * 2 + (day.dt.day() > 15).cast(pl.Int32)


def profiles(raw):
    normalized = (
        raw.filter(pl.col("price") > 0, pl.col("date") < RELEASE)
        .with_columns(
            pl.col("state_name").str.strip_chars().str.to_uppercase(),
            pl.col("commodity")
            .str.strip_chars()
            .str.to_uppercase()
            .alias("retail_crop"),
            pl.col("date").dt.year().alias("year"),
            fortnight(pl.col("date")).alias("fortnight"),
            pl.col("price").log().alias("log_price"),
        )
        .group_by(*KEYS, "year")
        .agg(pl.col("log_price").median())
        .with_columns(
            (
                pl.col("log_price")
                - pl.col("log_price").median().over("state_name", "retail_crop", "year")
            ).alias("relative"),
            pl.len().over("state_name", "retail_crop", "year").alias("periods"),
        )
        .filter(pl.col("periods") >= 20)
        .group_by(KEYS)
        .agg(
            pl.col("relative").median().alias("retail_season"), pl.len().alias("years")
        )
        .filter(pl.col("years") >= 3)
        .drop("years")
    )
    lag = normalized.select(
        "state_name",
        "retail_crop",
        ((pl.col("fortnight") + 1) % 24).alias("fortnight"),
        pl.col("retail_season").alias("last_period"),
    )
    exact = (
        normalized.join(lag, on=KEYS, how="left")
        .with_columns(
            (pl.col("retail_season") - pl.col("last_period")).alias(
                "retail_season_change"
            )
        )
        .drop("last_period")
    )
    region = (
        exact.filter(pl.col("retail_crop").is_in(BASKET))
        .group_by("state_name", "fortnight")
        .agg(
            pl.col("retail_season").mean().alias("produce_season"),
            pl.col("retail_season_change").mean().alias("produce_season_change"),
            pl.len().alias("crops"),
        )
        .filter(pl.col("crops") == len(BASKET))
        .drop("crops")
    )
    return exact, region


def attach(source, directory, path):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != DIGEST:
            raise ValueError("Expected the pinned August 2024 retail price export")
    raw = pl.read_csv(
        path,
        columns=["date", "commodity", "state_name", "price"],
        schema_overrides={"date": pl.Date, "price": pl.Float64},
    )
    exact, region = profiles(raw)
    names = pl.scan_parquet(directory / "market_keys.parquet").select(
        "entity", "d", "state_name", "commodity_name"
    )
    frame = source.join(
        names, on=["entity", "d"], how="left", validate="m:1", maintain_order="left"
    ).with_columns(
        pl.col("commodity_name").replace(ALIASES).alias("retail_crop"),
        pl.when(pl.col("date") >= RELEASE)
        .then(fortnight(pl.col("date") + pl.duration(days=1)))
        .alias("fortnight"),
    )
    return (
        frame.join(
            exact.lazy(), on=KEYS, how="left", validate="m:1", maintain_order="left"
        )
        .join(
            region.lazy(),
            on=["state_name", "fortnight"],
            how="left",
            validate="m:1",
            maintain_order="left",
        )
        .drop(*KEYS, "commodity_name")
    ), FEATURES
