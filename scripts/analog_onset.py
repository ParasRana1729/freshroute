"""Estimate next-day transitions from similar completed reports at the same entity."""

import numpy as np
import polars as pl

KEYS = ["entity", "d"]
RANKS = ("p_arr", "p_price")
LEVELS = ("log_arrival", "log_price")
NEXT_LEVELS = ("y_arr_level", "y_price_level")
INPUTS = [*KEYS, *RANKS, *LEVELS, "weekday", "rule_state", "y", *NEXT_LEVELS]
HISTORY_DAYS = 56
SCALES = {"near": 0.13, "broad": 0.30}
SUMMARY = ["weight", "onset_rate", "arrival_step", "price_step"]
FEATURES = [f"analog_{scale}_{item}" for scale in SCALES for item in SUMMARY]


def estimate_transitions(reports: pl.DataFrame) -> pl.DataFrame:
    """An earlier feature date's outcome can first be used one day later."""
    reports = reports.select(INPUTS).sort(KEYS)
    entity, day, weekday, rule = [
        reports[name].to_numpy() for name in ("entity", "d", "weekday", "rule_state")
    ]
    arrival_rank, price_rank = [reports[name].to_numpy() for name in RANKS]
    arrival, price = [reports[name].to_numpy() for name in LEVELS]
    outcomes = [
        reports["y"].to_numpy(),
        reports[NEXT_LEVELS[0]].to_numpy() - arrival,
        reports[NEXT_LEVELS[1]].to_numpy() - price,
    ]
    totals = {
        scale: np.zeros((len(SUMMARY), len(reports)), dtype=np.float64)
        for scale in SCALES
    }
    # One report per entity per calendar day. At most HISTORY_DAYS earlier rows
    # can qualify, regardless of whether an entity reports daily or sparsely.
    for lag in range(1, min(HISTORY_DAYS + 1, len(reports))):
        earlier, current = slice(None, -lag), slice(lag, None)
        age = day[current] - day[earlier]
        eligible = (
            (entity[current] == entity[earlier]) & (age >= 1) & (age <= HISTORY_DAYS)
        )
        if not eligible.any():
            continue
        rank_distance = np.abs(arrival_rank[current] - arrival_rank[earlier]) + np.abs(
            price_rank[current] - price_rank[earlier]
        )
        level_distance = 0.25 * np.abs(
            arrival[current] - arrival[earlier]
        ) + 0.75 * np.abs(price[current] - price[earlier])
        recency = np.exp(-np.maximum(age, 0) / 28.0)
        weekday_weight = np.where(weekday[current] == weekday[earlier], 1.0, 0.55)
        gate_weight = np.where(rule[current] == rule[earlier], 1.0, 0.50)
        for scale, bandwidth in SCALES.items():
            sensitivity = np.exp(-rank_distance / bandwidth - level_distance)
            weight = np.where(
                eligible, sensitivity * recency * weekday_weight * gate_weight, 0.0
            )
            totals[scale][0, current] += weight
            for index, outcome in enumerate(outcomes, start=1):
                totals[scale][index, current] += weight * outcome[earlier]

    features = []
    for scale, total in totals.items():
        with np.errstate(invalid="ignore", divide="ignore"):
            total[1:] /= total[0]
        for item, values in zip(SUMMARY, total):
            features.append(
                pl.Series(f"analog_{scale}_{item}", values.astype(np.float32))
            )
    return reports.select(KEYS).with_columns(features)
