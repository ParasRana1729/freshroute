#!/usr/bin/env python3
"""
Build gold osm_distance_matrix.parquet (P1 L1.3, D3).

Computes donor↔recipient distance matrix for Punjab GT corridor
using OSRM live (fallback haversine) and writes
data/gold/osm_distance_matrix.parquet.

Sources: OSM extract via Geofabrik, OSRM profile
         [@osm2024; @osrm2024] ODbL-1.0

Usage:
  python scripts/build_gold_osm.py
  python scripts/build_gold_osm.py --out data/gold/osm_distance_matrix.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from core.vrp_router import haversine_km
from core.vrp_router import _get_osrm_distance_matrix  # type: ignore


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Build OSM distance matrix gold")
    ap.add_argument("--out", type=str, default="data/gold/osm_distance_matrix.parquet")
    args = ap.parse_args()

    # Example donor/recipient coordinates from mockData.js + punjab_districts
    donors = [
        ("donor-verka-ludhiana-01", [30.9325, 75.8350]),
        ("donor-amritsar-mandi-01", [31.6330, 74.8723]),
        ("donor-jalandhar-01", [31.3260, 75.5762]),
    ]
    recipients = [
        ("recip-amritsar-langar-01", [31.6200, 74.8765]),
        ("recip-ludhiana-slum-02", [30.8750, 75.8850]),
        ("recip-patiala-elder-03", [30.3400, 76.3900]),
        ("recip-bathinda-rural-04", [30.2150, 74.9520]),
    ]

    all_coords = [c for _, c in donors] + [c for _, c in recipients]
    labels = [n for n, _ in donors] + [n for n, _ in recipients]

    # Try OSRM, fallback haversine
    osrm = _get_osrm_distance_matrix(all_coords, timeout=4.0)
    rows = []
    if osrm is not None:
        dist_m, _ = osrm
        for i, (donor, _) in enumerate(donors):
            for j, (recip, _) in enumerate(recipients):
                # donors 0..2, recipients 3..6 in all_coords
                d_m = dist_m[i][len(donors) + j]
                rows.append({"donor_id": donor, "recipient_id": recip, "distance_km": round(d_m / 1000, 2), "source": "osrm-live"})
        print(f"OSRM live: {len(rows)} pairs")
    else:
        for donor, dc in donors:
            for recip, rc in recipients:
                rows.append({"donor_id": donor, "recipient_id": recip, "distance_km": haversine_km(dc[0], dc[1], rc[0], rc[1]), "source": "haversine-fallback"})

    df = pd.DataFrame(rows)
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parents[1] / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"wrote {len(df)} pairs -> {out}")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
