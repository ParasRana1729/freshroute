#!/usr/bin/env python3
"""
HVI fusion Gini benchmark — P3 L3.3 (spec 4.1).

Compares matcher allocations with vs without HVI-weighted Deficit(j)
(w2=0.30) on synthetic Punjab corridor. Reports Gini of allocations
vs HVI and waste-vs-hunger trade-off.

Usage:
  python scripts/benchmark_hvi_fusion.py

Citation: [@niti2023mpi; @saaty1980ahp]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.arrhenius_decay import ThermalDecayEngine
from core.pareto_matcher import ParetoMatchingEngine
from core.demand_forecaster import HungerDemandForecaster


def gini(arr):
    arr = sorted(arr)
    n = len(arr)
    if n == 0 or sum(arr) == 0:
        return 0.0
    cum = 0
    for i, x in enumerate(arr, 1):
        cum += i * x
    return (2 * cum) / (n * sum(arr)) - (n + 1) / n


def main() -> None:
    eng = ThermalDecayEngine()
    fc = HungerDemandForecaster()
    matcher_hvi = ParetoMatchingEngine(weights=(0.35, 0.30, 0.20, 0.15))
    matcher_no_hvi = ParetoMatchingEngine(weights=(0.35, 0.00, 0.50, 0.15))  # w2=0 -> no deficit

    # Synthetic batches near Ludhiana
    batches = [
        {"batch_id": f"b{i}", "category": "Produce", "gross_weight_kg": 400, "origin_coordinates": [30.9325, 75.835], "dietary_flags": {"is_pure_veg": True}, "ambient_temp_c": 32, "humidity_pct": 70}
        for i in range(10)
    ]
    # Recipients across HVI spectrum — same coords to isolate HVI (proximity equal)
    recipients = []
    for d in fc.districts[:10]:
        recipients.append(
            {
                "recipient_id": d["district_id"],
                "name": d["district_name"],
                "coordinates": [30.9, 75.85],  # equal proximity
                "urgency_score": d["hunger_vulnerability_index"],
                "hunger_vulnerability_index": d["hunger_vulnerability_index"],
                "dietary_policy": "Vegetarian",
                "cold_storage_capacity_liters": 5000,
            }
        )

    alloc_hvi = matcher_hvi.rank_allocations(batches, recipients, eng, min_score=0)
    alloc_no = matcher_no_hvi.rank_allocations(batches, recipients, eng, min_score=0)

    # Gini of allocation counts per HVI bucket
    from collections import Counter

    cnt_hvi = Counter(a["matched_recipient_id"] for a in alloc_hvi)
    cnt_no = Counter(a["matched_recipient_id"] for a in alloc_no)
    # Map to HVI values
    hvi_map = {r["recipient_id"]: r["hunger_vulnerability_index"] for r in recipients}
    # Weighted by HVI: higher HVI should get more allocations with HVI fusion
    vals_hvi = [cnt_hvi.get(rid, 0) * hvi_map[rid] for rid in hvi_map]
    vals_no = [cnt_no.get(rid, 0) * hvi_map[rid] for rid in hvi_map]

    print("HVI fusion benchmark (10 batches, 10 recipients):")
    print(f"  with HVI w2=0.30: {len(alloc_hvi)} allocs, Gini {gini(list(cnt_hvi.values())):.2f}, HVI-weighted {sum(vals_hvi):.0f}")
    print(f"  without HVI w2=0: {len(alloc_no)} allocs, Gini {gini(list(cnt_no.values())):.2f}, HVI-weighted {sum(vals_no):.0f}")
    print(f"  HVI uplift: {sum(vals_hvi)-sum(vals_no):+.0f} (positive = more high-HVI served)")
    # Spearman rho of HVI vs allocation count would be ideal; we report Gini delta


if __name__ == "__main__":
    main()
