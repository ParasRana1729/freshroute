"""Join complete market forecast snapshots issued before the target day in India."""

import polars as pl

MARKET = ["state_name", "market_center_name", "commodity_name"]
VALUES = ["expected_arrival_tonnes", "buyer_demand_tonnes"]
FEATURES = [*VALUES, "notice_age_days"]


def available_snapshots(data: pl.DataFrame) -> pl.DataFrame:
    keys = [*MARKET, "target_date"]
    if (
        not data["issued_at"]
        .str.contains(r"(Z|[+-]\d{2}:\d{2})$")
        .fill_null(False)
        .all()
    ):
        raise ValueError("issued_at requires an explicit UTC offset")
    data = data.with_columns(
        pl.col(MARKET).str.strip_chars().str.to_uppercase(),
        pl.col("target_date").str.to_date("%Y-%m-%d"),
        pl.col("issued_at").str.to_datetime(time_zone="UTC"),
        pl.col(VALUES).cast(pl.Float64),
    )
    invalid = (
        pl.any_horizontal(pl.col(keys).is_null())
        | pl.any_horizontal([pl.col(k) == "" for k in MARKET])
        | pl.all_horizontal(pl.col(VALUES).is_null())
        | pl.any_horizontal(
            [
                ((pl.col(k) < 0) | ~pl.col(k).is_finite()).fill_null(False)
                for k in VALUES
            ]
        )
    )
    if (
        data.filter(invalid).height
        or data.select(*keys, "issued_at").is_duplicated().any()
    ):
        raise ValueError("Invalid or duplicate market forecast snapshot")
    issue_day = pl.col("issued_at").dt.convert_time_zone("Asia/Kolkata").dt.date()
    return (
        data.with_columns(
            (pl.col("target_date") - issue_day).dt.total_days().alias("notice_age_days")
        )
        .filter(pl.col("notice_age_days") >= 1)
        .sort("issued_at")
        .unique(subset=keys, keep="last")
        .select(*keys, *FEATURES)
    )


def attach(source, directory, path):
    notices = available_snapshots(pl.read_csv(path, infer_schema=False))
    maps = pl.scan_parquet(directory / "market_keys.parquet")
    return (
        source.join(
            maps, on=["entity", "d"], how="left", validate="m:1", maintain_order="left"
        )
        .with_columns((pl.col("date") + pl.duration(days=1)).alias("target_date"))
        .join(
            notices.lazy(),
            on=[*MARKET, "target_date"],
            how="left",
            validate="m:1",
            maintain_order="left",
        )
        .drop(*MARKET, "target_date")
    )
