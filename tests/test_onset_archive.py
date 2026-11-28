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
    keys = ["market", "date"]
    assert_frame_equal(
        full.filter(pl.col("date") <= cutoff).sort(keys), prefix.sort(keys)
    )
    pairs = prep.pair(full)
    assert pairs.height == 60
    assert pairs.filter(
        (pl.col("y") == 1)
        != ((pl.col("y_arr_rank") >= 0.7) & (pl.col("y_price_rank") <= 0.3))
    ).is_empty()
