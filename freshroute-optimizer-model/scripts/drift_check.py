#!/usr/bin/env python3
"""
Drift PSI check — P8 C1 (daily).

Compares recent vs baseline forecaster history (demand_lbs) and
weather temp; flags PSI>0.2 for retrain per docs/IMPLEMENTATION_PLAN.md:6.

Usage: python scripts/drift_check.py --baseline-days 60 --recent-days 14
Citation: PSI threshold 0.2 from industry drift practice
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    # Quantile bins from expected
    q = np.linspace(0, 100, bins + 1)
    breaks = np.percentile(expected, q)
    # Avoid duplicates
    breaks = np.unique(breaks)
    if len(breaks) <= 2:
        return 0.0
    e_hist, _ = np.histogram(expected, bins=breaks)
    a_hist, _ = np.histogram(actual, bins=breaks)
    # Smoothing
    e_hist = e_hist + 0.5
    a_hist = a_hist + 0.5
    e_perc = e_hist / e_hist.sum()
    a_perc = a_hist / a_hist.sum()
    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="PSI drift check")
    ap.add_argument("--baseline-days", type=int, default=60)
    ap.add_argument("--recent-days", type=int, default=14)
    args = ap.parse_args()

    from core.demand_forecaster import HungerDemandForecaster

    fc = HungerDemandForecaster()
    df = fc.generate_synthetic_history(days=args.baseline_days + args.recent_days, seed=42)
    baseline = df.head(args.baseline_days * len(fc.districts))["demand_lbs"].values
    recent = df.tail(args.recent_days * len(fc.districts))["demand_lbs"].values
    ps = psi(baseline, recent)
    print(f"PSI demand: {ps:.3f} threshold 0.2 -> {'drift' if ps>0.2 else 'stable'}")
    # Weather temp drift example
    b_temp = df.head(args.baseline_days * len(fc.districts))["temp_c"].values
    r_temp = df.tail(args.recent_days * len(fc.districts))["temp_c"].values
    ps_t = psi(b_temp, r_temp)
    print(f"PSI temp: {ps_t:.3f}")
    if ps > 0.2:
        print("ALERT: retrain forecaster (P3) and refit phi (C6)")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
