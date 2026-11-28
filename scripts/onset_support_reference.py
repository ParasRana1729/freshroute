"""Compare day-end mandi price levels with previously announced crop references."""

from datetime import date

import polars as pl

# Rs per quintal. Values from the two PIB releases linked in ONSET_ADVANCE_SIGNALS.md.
KHARIF = {
    "PADDY(COMMON)": 2369,
    "BAJRA(PEARL MILLET/CUMBU)": 2775,
    "RAGI(FINGER MILLET)": 4886,
    "MAIZE": 2400,
    "RED GRAM/ARHAR/TUR(WHOLE)": 8000,
    "GREEN GRAM(MOONG)(WHOLE)": 8768,
    "BLACK GRAM(URD BEANS)(WHOLE)": 7800,
    "GROUNDNUT": 7263,
    "SUNFLOWER/SUNFLOWER SEED": 7721,
    "SESAMUM(SESAME,GINGELLY,TIL)": 9846,
    "NIGER SEED(RAMTIL)": 9537,
}
RABI = {
    "WHEAT": 2585,
    "BARLEY(JAU)": 2150,
    "BENGAL GRAM(GRAM)(WHOLE)": 5875,
    "LENTIL(MASUR)(WHOLE)": 7000,
    "MUSTARD": 6200,
    "SAFFLOWER": 6540,
}


def price_reference():
    name = pl.col("commodity_name")
    announced = [
        pl.when(pl.col("date") >= published).then(
            name.replace_strict(prices, default=None, return_dtype=pl.Float32) / 100
        )
        for published, prices in [
            (date(2025, 5, 28), KHARIF),
            (date(2025, 10, 1), RABI),
        ]
    ]
    return pl.coalesce(*announced).cast(pl.Float32).alias("announced_rs_per_kg")


def attach(source, directory):
    markets = pl.scan_parquet(directory / "market_keys.parquet")
    source = (
        source.join(
            markets.select("entity", "d", "commodity_name"),
            on=["entity", "d"],
            how="left",
            validate="m:1",
            maintain_order="left",
        )
        .with_columns(price_reference())
        .drop("commodity_name")
    )
    reference = pl.col("announced_rs_per_kg").log1p()
    margins = {
        "modal_vs_announced": pl.col("log_price"),
        "daily_low_vs_announced": pl.col("min_price").log1p(),
        "cutoff_vs_announced": pl.col("price_cutoff"),
        "projected_vs_announced": pl.col("forecast_log_price"),
    }
    return source.with_columns(
        [
            (level - reference).cast(pl.Float32).alias(name)
            for name, level in margins.items()
        ]
    ), ["announced_rs_per_kg", *margins]


def correction_bound(labels, decisions, covered):
    """Diagnostic for correcting all covered rows and freezing every other decision."""
    outside = ~covered
    true = labels == 1
    tp = int((outside & decisions & true).sum())
    fp = int((outside & decisions & ~true).sum())
    fn = int((outside & ~decisions & true).sum())
    positives = int((covered & true).sum())
    twice_tp = 2 * (tp + positives)
    return dict(
        covered_rows=int(covered.sum()),
        covered_positives=positives,
        outside_tp=tp,
        outside_fp=fp,
        outside_fn=fn,
        perfect_covered_f1=(
            twice_tp / (twice_tp + fp + fn) if twice_tp + fp + fn else 0.0
        ),
    )
