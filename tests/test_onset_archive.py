from datetime import date

import pytest

pl = pytest.importorskip("polars")


def test_archive_features_use_only_reports_through_feature_day():
    from polars.testing import assert_frame_equal
    from scripts import prepare_onset_archive as prep

    start = date(2026, 1, 1)
    cutoff = date(2026, 1, 4)
    rows = []
    for day in range(1, 7):
        for market in range(12):
            rows.append(
                {
                    "date": start.replace(day=day),
                    "state_name": "STATE",
                    "district_name": "DISTRICT",
                    "market_center_name": f"MARKET {market:02d}",
                    "source_market": market,
                    "commodity_name": "TOMATO",
                    "variety": "LOCAL",
                    "grade": "FAQ",
                    "arrival": float((market + day * 2) % 12),
                    "modal_price": float(13 - market),
                    "min_price": float(12 - market),
                    "max_price": float(14 - market),
                    "latitude": 10.0,
                    "longitude": 78.0,
                }
            )
    config = prep.bf.load_config()
    reports = pl.DataFrame(rows).lazy()

    def features(source):
        return prep.peers(
            prep.history(prep.cross_section(source, start, config).collect()),
            config["surplus_cs"],
        )

    full = features(reports)
    prefix = features(reports.filter(pl.col("date") <= cutoff))
    # Compare rows by source identity. Polars may assign different categorical
    # codes during independent collections, even for the same market names.
    encoded = [
        *prep.INT_KEYS,
        "district",
        "entity",
        "mkt_comm",
        "district_comm",
        "state_comm",
    ]
    keys = ["source_market", "date"]
    assert_frame_equal(
        full.filter(pl.col("date") <= cutoff).drop(encoded).sort(keys),
        prefix.drop(encoded).sort(keys),
    )
    pairs = prep.pair(full)
    assert pairs.height == 60
    assert pairs.filter(
        (pl.col("y") == 1)
        != ((pl.col("y_arr_rank") >= 0.7) & (pl.col("y_price_rank") <= 0.3))
    ).is_empty()


def test_projected_peer_ranks_do_not_use_future_reports():
    from polars.testing import assert_frame_equal
    from scripts.forecast_reporting_cohort import expected_peer_ranks

    reports = pl.DataFrame(
        [
            dict(
                d=day,
                commodity=0,
                entity=market,
                log_arrival=float(day + market),
                log_price=float(day - market),
                log_arrival_mean_7=float(day + market - 1),
                log_price_mean_7=float(day - market + 1),
            )
            for day in range(1, 35)
            for market in range(12)
            if (day + market) % 4 != 0
        ],
        schema_overrides={
            column: pl.Float32
            for column in (
                "log_arrival",
                "log_price",
                "log_arrival_mean_7",
                "log_price_mean_7",
            )
        },
    )
    cutoff = 25
    full = expected_peer_ranks(reports.lazy()).filter(pl.col("d") <= cutoff)
    prefix = expected_peer_ranks(reports.lazy().filter(pl.col("d") <= cutoff))
    assert_frame_equal(full, prefix, check_exact=False)
    assert len(prefix) == reports.filter(pl.col("d") <= cutoff).height
    assert prefix.filter(pl.col("d") == cutoff)["weekly_weight"].max() > 0


def test_analog_features_use_only_resolved_same_entity_outcomes():
    import math

    from polars.testing import assert_frame_equal
    from scripts.analog_onset import estimate_transitions

    reports = pl.DataFrame(
        {
            "entity": [2, 1, 1, 1],
            "d": [9, 10, 11, 13],
            "p_arr": [0.6, 0.6, 0.6, 0.6],
            "p_price": [0.2, 0.2, 0.2, 0.2],
            "log_arrival": [2.0, 2.0, 2.0, 2.0],
            "log_price": [4.0, 4.0, 4.0, 4.0],
            "weekday": [1, 2, 3, 5],
            "rule_state": [2, 2, 2, 2],
            "y": [1, 1, 0, 0],
            "y_arr_level": [2.8, 3.0, 1.2, 2.4],
            "y_price_level": [3.5, 3.0, 4.2, 4.1],
        }
    )
    result = estimate_transitions(reports)
    first = result.filter(pl.col("entity") == 1, pl.col("d") == 10).row(0, named=True)
    assert first["analog_near_weight"] == 0
    assert math.isnan(first["analog_near_onset_rate"])

    next_day = result.filter(pl.col("entity") == 1, pl.col("d") == 11).row(
        0, named=True
    )
    assert next_day["analog_near_onset_rate"] == 1
    assert next_day["analog_near_arrival_step"] == 1
    assert next_day["analog_near_price_step"] == -1

    prefix = reports.filter(pl.col("d") <= 11).with_columns(
        pl.when(pl.col("d") == 11).then(1).otherwise(pl.col("y")).alias("y"),
        pl.when(pl.col("d") == 11)
        .then(8.0)
        .otherwise(pl.col("y_arr_level"))
        .alias("y_arr_level"),
        pl.when(pl.col("d") == 11)
        .then(1.0)
        .otherwise(pl.col("y_price_level"))
        .alias("y_price_level"),
    )
    assert_frame_equal(result.filter(pl.col("d") <= 11), estimate_transitions(prefix))
