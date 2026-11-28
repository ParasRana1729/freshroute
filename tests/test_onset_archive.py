from datetime import date

import pytest

pl = pytest.importorskip("polars")


def test_notice_snapshot_respects_local_midnight_and_keeps_uncovered_rows(tmp_path):
    from scripts.advance_market_signal import attach

    keys = pl.DataFrame(
        dict(
            entity=[1, 2, 3],
            d=[10, 10, 10],
            state_name=["STATE"] * 3,
            market_center_name=["A", "A", "B"],
            commodity_name=["CROP"] * 3,
        )
    )
    keys.write_parquet(tmp_path / "market_keys.parquet")
    source = keys.select("entity", "d").with_columns(
        pl.lit(date(2026, 3, 1)).alias("date")
    )
    notices = pl.DataFrame(
        dict(
            state_name=["State"] * 3,
            market_center_name=["A"] * 3,
            commodity_name=["Crop"] * 3,
            target_date=["2026-03-02"] * 3,
            issued_at=[
                "2026-03-01T07:00:00Z",
                "2026-03-01T18:29:59Z",
                "2026-03-01T18:30:00Z",
            ],
            expected_arrival_tonnes=[10, 12, 95],
            buyer_demand_tonnes=[None, None, 90],
        )
    )
    path = tmp_path / "notices.csv"
    notices.write_csv(path)
    result = attach(source.lazy(), tmp_path, path).collect()
    assert result["entity"].to_list() == [1, 2, 3]
    assert result["expected_arrival_tonnes"].to_list() == [12, 12, None]
    assert result["buyer_demand_tonnes"].null_count() == 3


@pytest.mark.parametrize("stable_ids", [False, True])
def test_archive_features_use_only_reports_through_feature_day(stable_ids):
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
            prep.history(
                prep.cross_section(
                    source, start, config, stable_ids=stable_ids
                ).collect()
            ),
            config["surplus_cs"],
        )

    if stable_ids:
        # Crossing Enum's 255-category boundary after the forecast must not
        # change hashes used in earlier joins and training-row sampling.
        future = pl.DataFrame(
            [
                {
                    **rows[0],
                    "date": date(2026, 1, 15),
                    "market_center_name": f"NEW-{i}",
                }
                for i in range(300)
            ]
        ).lazy()
        reports = pl.concat([reports, future])
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
    if stable_ids:
        encoded = []
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


def test_announced_price_units_dates_and_uncovered_produce():
    from scripts.onset_support_reference import price_reference

    frame = pl.DataFrame(
        {
            "date": [
                date(2025, 9, 30),
                date(2025, 10, 1),
                date(2025, 5, 28),
                date(2026, 4, 1),
            ],
            "commodity_name": ["WHEAT", "WHEAT", "MAIZE", "TOMATO"],
        }
    )
    assert frame.select(price_reference()).to_series().to_list() == [
        None,
        pytest.approx(25.85),
        24.0,
        None,
    ]


def test_market_leads_use_only_past_fits_and_current_peer_reports():
    import numpy as np
    from polars.testing import assert_frame_equal
    from scripts.onset_market_leads import FEATURES, KEYS, estimates

    rng = np.random.default_rng(99)
    first = (date(2025, 10, 1) - date(1970, 1, 1)).days
    shocks = rng.uniform(0.1, 0.9, 140)
    rows = []
    for i in range(140):
        for market, rank in [(1, shocks[i]), (2, shocks[max(i - 1, 0)]), (3, 0.5)]:
            rows.append(
                dict(
                    state=0,
                    commodity=1,
                    market=market,
                    d=first + i,
                    p_arr=rank,
                    p_price=1 - rank,
                )
            )
    df = pl.DataFrame(rows)
    end = first + 110
    full = estimates(df).filter(pl.col("d") <= end).sort(KEYS)
    prefix = estimates(df.filter(pl.col("d") <= end)).sort(KEYS)
    assert_frame_equal(full, prefix)
    assert np.isfinite(
        full.filter((pl.col("d") == end) & (pl.col("market") == 2))[FEATURES[0]].item()
    )
    # With one observed market only, the model has no independent peer.
    solo = estimates(df.filter(pl.col("market") == 1))
    assert solo["peer_change_p_arr"].is_nan().all()


def test_retail_profiles_use_published_history_and_wrap_december():
    from scripts.onset_retail_season import profiles

    rows = []
    for year in [2018, 2019, 2020]:
        for month in range(1, 13):
            for d in (5, 20):
                for crop in ["Onion", "Tomato", "Potato"]:
                    rows.append(
                        dict(
                            date=date(year, month, d),
                            commodity=crop,
                            state_name="State",
                            price=float(month + 10),
                        )
                    )
    historical = pl.DataFrame(rows)
    newer = pl.DataFrame([{**rows[0], "date": date(2025, 1, 5), "price": 50000.0}])
    from polars.testing import assert_frame_equal

    exact, basket = profiles(historical)
    extra, extra_basket = profiles(pl.concat([historical, newer]))
    assert_frame_equal(
        exact.sort("retail_crop", "fortnight"), extra.sort("retail_crop", "fortnight")
    )
    assert_frame_equal(basket.sort("fortnight"), extra_basket.sort("fortnight"))
    assert basket.height == 24
    assert basket.filter(pl.col("fortnight") == 0)["produce_season_change"].item() < 0
