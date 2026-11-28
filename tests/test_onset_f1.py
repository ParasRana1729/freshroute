import numpy as np
import pandas as pd

from scripts import build_features as bf
from scripts.train_onset_f1 import add_causal_history, add_peer_cutoffs


def test_onset_history_uses_only_available_daily_reports() -> None:
    rows = []
    for market, reports in (
        ("A", [(1, 0), (2, 1), (4, 0)]),
        ("B", [(1, 0), (2, 0), (3, 1), (4, 1)]),
        ("C", [(1, 0), (3, 1)]),
    ):
        for day, surplus in reports:
            rows.append({
                "state_name": "STATE",
                "market_center_name": market,
                "commodity_name": "TOMATO",
                "variety": "V",
                "grade": "G",
                "date": pd.Timestamp(2025, 11, day),
                "surplus_cs": surplus,
                "log_arrival": np.float32(day),
                "log_price": np.float32(2 * day),
                "p_arr_t": np.float32(0.4 + 0.1 * day),
                "p_price_t": np.float32(0.3),
            })
    # A prior report for C exists, but the gap makes C's onset status unknown.
    reports = pd.DataFrame(rows).sample(frac=1, random_state=19)
    reports = bf._add_backward_lag_features(reports, bf.ENTITY_KEYS)
    cutoff = pd.Timestamp(2025, 11, 3)
    complete, peer_columns, history_columns = add_causal_history(reports, bf.ENTITY_KEYS)
    truncated, _, _ = add_causal_history(reports.loc[reports["date"] <= cutoff], bf.ENTITY_KEYS)
    surplus_config = bf.load_config()["surplus_cs"]
    complete, cutoff_columns = add_peer_cutoffs(complete, surplus_config)
    truncated, _ = add_peer_cutoffs(truncated, surplus_config)
    columns = [*bf.ENTITY_KEYS, "date", *peer_columns, *history_columns, *cutoff_columns]
    pd.testing.assert_frame_equal(
        complete.loc[complete["date"] <= cutoff, columns].reset_index(drop=True),
        truncated[columns],
    )

    day_two = complete.loc[complete["date"].dt.day.eq(2)]
    np.testing.assert_allclose(day_two["history_commodity_observed_onset"], [0.5, 0.5])
    day_three = complete.loc[complete["date"].dt.day.eq(3)]
    np.testing.assert_allclose(day_three["history_commodity_observed_onset"], [2 / 3, 2 / 3])
    market_a_last = complete.loc[
        complete["market_center_name"].eq("A") & complete["date"].dt.day.eq(4)
    ].iloc[0]
    assert market_a_last["history_entity_observed_onset"] == 1
    assert market_a_last["days_since_observed_surplus"] == 2
