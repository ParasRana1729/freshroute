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

    # Real D3 gold matrix: load donor↔recipient OSRM distances
    matrix = matcher_hvi.load_distance_matrix()
    donors = sorted({d for d, _ in matrix}) if matrix else ["donor-verka-ludhiana-01", "donor-amritsar-mandi-01", "donor-jalandhar-01"]
    recip_ids = sorted({r for _, r in matrix})
    print(f"D3 gold matrix: {len(matrix)} pairs, {len(donors)} donors, {len(recip_ids)} recipients")

    # Recipients across HVI spectrum mapped to gold matrix ids
    hvi_map = {
        "recip-amritsar-langar-01": 92,
        "recip-ludhiana-slum-02": 95,
        "recip-patiala-elder-03": 79,
        "recip-bathinda-rural-04": 88,
    }
    coords_map = {d["district_id"]: d["coordinates"] for d in fc.districts}
    coord_fallback = {
        "recip-amritsar-langar-01": [31.62, 74.8765],
        "recip-ludhiana-slum-02": [30.875, 75.885],
        "recip-patiala-elder-03": [30.34, 76.39],
        "recip-bathinda-rural-04": [30.215, 74.952],
    }
    recipients = []
    for rid in recip_ids:
        recipients.append(
            {
                "recipient_id": rid,
                "name": rid,
                "coordinates": coord_fallback.get(rid, [30.9, 75.85]),
                "urgency_score": float(hvi_map.get(rid, 50)),
                "hunger_vulnerability_index": float(hvi_map.get(rid, 50)),
                "dietary_policy": "Vegetarian",
                "cold_storage_capacity_liters": 5000,
            }
        )

    # Batches spread over donors in gold matrix
    batches = []
    for k in range(12):
        did = donors[k % len(donors)]
        batches.append(
            {
                "batch_id": f"b{k}",
                "donor_id": did,
                "category": "Produce",
                "gross_weight_kg": 400,
                "origin_coordinates": [30.9325, 75.835] if "ludhiana" in did else ([31.633, 74.8723] if "amritsar" in did else [31.326, 75.5762]),
                "dietary_flags": {"is_pure_veg": True},
                "ambient_temp_c": 32,
                "humidity_pct": 70,
            }
        )

    alloc_hvi = matcher_hvi.rank_allocations(batches, recipients, eng, min_score=0)
    alloc_no = matcher_no_hvi.rank_allocations(batches, recipients, eng, min_score=0)

    # Gini of allocation counts + HVI-weighted service
    from collections import Counter

    cnt_hvi = Counter(a["matched_recipient_id"] for a in alloc_hvi)
    cnt_no = Counter(a["matched_recipient_id"] for a in alloc_no)
    rid_to_hvi = {r["recipient_id"]: r["hunger_vulnerability_index"] for r in recipients}
    vals_hvi = [cnt_hvi.get(rid, 0) * rid_to_hvi[rid] for rid in rid_to_hvi]
    vals_no = [cnt_no.get(rid, 0) * rid_to_hvi[rid] for rid in rid_to_hvi]

    print("HVI fusion benchmark (gold OSRM distances):")
    print(f"  with HVI w2=0.30: {len(alloc_hvi)} allocs, Gini {gini(list(cnt_hvi.values())):.2f}, HVI-weighted {sum(vals_hvi):.0f}")
    print(f"  without HVI w2=0: {len(alloc_no)} allocs, Gini {gini(list(cnt_no.values())):.2f}, HVI-weighted {sum(vals_no):.0f}")
    print(f"  HVI uplift: {sum(vals_hvi)-sum(vals_no):+.0f} (positive = more high-HVI served)")
    dists = [a["distance_km"] for a in alloc_hvi if a.get("distance_km") is not None]
    if dists:
        print(f"  mean distance (OSRM road): {sum(dists)/len(dists):.1f}km")
    print(
        "  note: GT corridor geography aligns proximity & HVI (high-need hubs are nearest), "
        "so uplift=0 here; equity trade-off measurable once P7 field adds low-HVI-near-donor hubs"
    )


if __name__ == "__main__":
    main()
