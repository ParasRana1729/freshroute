"""Forecast next-day changes from historically leading same-commodity markets."""

from datetime import date

import numpy as np
import polars as pl

KEYS = ["state", "commodity", "market", "d"]
RANKS = ["p_arr", "p_price"]
FEATURES = [f"peer_{kind}_{rank}" for rank in RANKS for kind in ("change", "strength")]


def peer_forecast(x, y, future, peer_ids):
    """Estimate up to three slopes for each target using pairwise-complete history."""
    observed_x, observed_y = np.isfinite(x), np.isfinite(y)
    left, right = np.nan_to_num(x), np.nan_to_num(y)
    xm, ym = observed_x.astype(float), observed_y.astype(float)
    n = xm.T @ ym
    denom = np.maximum(1, n)
    sum_x, sum_y = left.T @ ym, xm.T @ right
    ssx = (left * left).T @ ym - sum_x**2 / denom
    ssy = xm.T @ (right * right) - sum_y**2 / denom
    cross = left.T @ right - sum_x * sum_y / denom
    good = (n >= 25) & (ssx > 1e-7) & (ssy > 1e-7)
    good[np.arange(len(peer_ids)), peer_ids] = False
    score = np.where(good, cross / np.sqrt(np.maximum(1e-14, ssx * ssy)), 0)
    # Shrink correlations with shorter overlap before selecting the peers.
    score *= n / (n + 40)
    best = np.argsort(-np.abs(score), axis=0, kind="stable")[:3]
    by_target = np.arange(y.shape[1])
    weight = score[best, by_target] ** 2
    slope = (cross / np.maximum(ssx, 1e-7))[best, by_target]
    centering = (sum_x / denom)[best, by_target]
    current = future[:, best]
    available = np.isfinite(current)
    weights = available * weight
    weight_sum = weights.sum(axis=1)
    delta = (weights * slope * (np.nan_to_num(current) - centering)).sum(axis=1)
    delta = np.divide(
        delta, weight_sum, out=np.full_like(delta, np.nan), where=weight_sum > 0
    )
    return delta, np.sqrt(weight_sum)


def estimates(group):
    days, markets = [group[c].to_numpy() for c in ("d", "market")]
    left_day = int(days.min())
    day_index = days - left_day
    market_names, market_index = np.unique(markets, return_inverse=True)
    n_days, n_markets = int(day_index.max()) + 1, len(market_names)
    result = {}
    dates = np.arange(left_day, left_day + n_days).astype("datetime64[D]")
    months, starts = np.unique(dates.astype("datetime64[M]"), return_index=True)
    for rank in RANKS:
        levels = np.full((n_days, n_markets), np.nan)
        levels[day_index, market_index] = group[rank].to_numpy()
        observed = np.isfinite(levels)
        # Departures from the previous seven calendar days, including gaps.
        counts = np.pad(np.cumsum(observed, axis=0), ((1, 0), (0, 0)))
        sums = np.pad(np.cumsum(np.nan_to_num(levels), axis=0), ((1, 0), (0, 0)))
        d = np.arange(n_days)
        prior_count = counts[d] - counts[np.maximum(d - 7, 0)]
        prior_sum = sums[d] - sums[np.maximum(d - 7, 0)]
        anomaly = levels - np.where(
            prior_count >= 2, prior_sum / np.maximum(prior_count, 1), np.nan
        )
        changes = levels[1:] - levels[:-1]
        delta = np.full_like(levels, np.nan)
        strength = np.zeros_like(levels)
        for idx, start in enumerate(starts):
            if start < 26 or n_markets < 2:
                continue
            stop = starts[idx + 1] if idx + 1 < len(months) else n_days
            # The most recent training outcome is on start-1, already observed.
            fit = slice(max(0, start - 100), start - 1)
            coverage = np.isfinite(anomaly[fit]).sum(axis=0)
            peers = np.argsort(-coverage, kind="stable")[:24]
            peers = peers[coverage[peers] >= 25]
            if peers.size:
                delta[start:stop], strength[start:stop] = peer_forecast(
                    anomaly[fit][:, peers],
                    changes[fit],
                    anomaly[start:stop][:, peers],
                    peers,
                )
        result[f"peer_change_{rank}"] = delta[day_index, market_index].astype("float32")
        result[f"peer_strength_{rank}"] = strength[day_index, market_index].astype(
            "float32"
        )
    return group.select(KEYS).with_columns(**result)


def attach(source, directory, last_feature_date):
    history = (
        pl.scan_parquet(directory / "peer_history.parquet")
        .filter(pl.col("d") < (last_feature_date - date(1970, 1, 1)).days)
        .group_by(KEYS)
        .agg(pl.col(RANKS).cast(pl.Float64).mean())
        .sort(KEYS)
        .collect()
    )
    forecasts = pl.concat(
        [
            estimates(group)
            for group in history.partition_by(
                ["state", "commodity"], maintain_order=True
            )
        ]
    )
    return (
        source.join(
            forecasts.lazy(), on=KEYS, how="left", validate="m:1", maintain_order="left"
        ),
        FEATURES,
    )
