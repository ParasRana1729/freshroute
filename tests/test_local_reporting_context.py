import polars as pl

from scripts.local_reporting_context import feature_columns, local_reporting_context


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "entity": [1, 2, 1, 2, 3],
            "d": [10, 10, 11, 11, 20],
            "market": [7, 7, 7, 7, 7],
            "district": [4, 4, 4, 4, 4],
            "state": [2, 2, 2, 2, 2],
            "commodity": [100, 200, 100, 200, 300],
            "surplus": [0, 1, 1, 0, 1],
            "p_arr": [0.2, 0.8, 0.9, 0.4, 0.7],
            "p_price": [0.7, 0.2, 0.1, 0.6, 0.3],
            "log_arrival": [1.0, 2.0, 1.5, 2.5, 3.0],
            "log_price": [4.0, 3.0, 3.5, 4.5, 2.0],
        }
    )


def test_local_context_uses_same_day_and_exact_past_lags():
    result = local_reporting_context(_frame())
    row = result.filter(pl.col("entity") == 1, pl.col("d") == 11).row(0, named=True)
    assert row["local_market_report_count"] == 2
    assert row["local_market_surplus_rate"] == 0.5
    assert row["local_market_report_count_lag_1"] == 2
    assert row["local_market_mean_arrival_rank_lag_1"] == 0.5


def test_future_reports_do_not_change_earlier_context():
    original = local_reporting_context(_frame().filter(pl.col("d") <= 11))
    extended = local_reporting_context(_frame()).filter(pl.col("d") <= 11)
    assert original.select("entity", "d", *feature_columns()).equals(
        extended.select("entity", "d", *feature_columns())
    )


def test_local_context_does_not_pool_same_market_name_across_states():
    reports = _frame().with_columns(
        pl.when(pl.col("entity") == 2).then(5).otherwise(pl.col("state")).alias("state")
    )
    result = local_reporting_context(reports)
    first = result.filter(pl.col("entity") == 1, pl.col("d") == 10).row(0, named=True)
    assert first["local_market_report_count"] == 1
    assert first["local_district_report_count"] == 1
