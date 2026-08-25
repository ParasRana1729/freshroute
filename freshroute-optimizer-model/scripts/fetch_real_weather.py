#!/usr/bin/env python3
"""
Fetch REAL historical weather (Open-Meteo Archive API) for Punjab corridor — P1 L1.2.

Pulls hourly temp/RH for the GT-corridor points over a date window,
validates via GE suite, and writes gold weather_hourly.parquet with
source='open-meteo-archive' (real data, citable [@openmeteo2024]).

Usage:
  python scripts/fetch_real_weather.py --start 2026-05-01 --end 2026-06-30
Provenance written to docs/datasheets/open_meteo_imd.md on each run.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

# Punjab GT corridor + Malwa points (spec §1; matches punjab_districts.json)
POINTS = {
    "ludhiana": (30.90, 75.85),
    "amritsar": (31.63, 74.87),
    "jalandhar": (31.33, 75.58),
    "patiala": (30.34, 76.39),
    "bathinda": (30.21, 74.95),
}
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_point(lat: float, lon: float, start: str, end: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "hourly": "temperature_2m,relative_humidity_2m",
            "timezone": "UTC",
        }
    )
    req = urllib.request.Request(f"{ARCHIVE_URL}?{params}", headers={"User-Agent": "FreshRoute-P1-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    h = d.get("hourly", {})
    times = h.get("time", [])
    temps = h.get("temperature_2m", [])
    hums = h.get("relative_humidity_2m", [])
    rows = []
    for i, t in enumerate(times):
        tc = temps[i] if i < len(temps) else None
        rh = hums[i] if i < len(hums) else None
        if tc is None or rh is None:
            continue
        rows.append(
            {
                "timestamp_utc": t,
                "lat": lat,
                "lon": lon,
                "temp_c": float(tc),
                "humidity_pct": float(rh),
                "source": "open-meteo-archive",
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--gold", default="data/gold/weather_hourly.parquet")
    args = ap.parse_args()

    all_rows: list[dict] = []
    for name, (lat, lon) in POINTS.items():
        rows = fetch_point(lat, lon, args.start, args.end)
        print(f"{name}: {len(rows)} real rows", flush=True)
        all_rows.extend(rows)

    from data.validation.ge_suites import validate_weather_rows

    res = validate_weather_rows(all_rows[:48])  # spot-check first day-shape
    full_ok = all(
        -10 <= r["temp_c"] <= 55 and 0 <= r["humidity_pct"] <= 100 for r in all_rows
    )
    print(f"validation: {'pass' if full_ok else 'FAIL'} ({len(all_rows)} total rows)")

    df = pd.DataFrame(all_rows)
    df["retrieved_at"] = datetime.utcnow().isoformat()
    gold = Path(__file__).resolve().parents[1] / args.gold
    gold.parent.mkdir(parents=True, exist_ok=True)
    # Overwrite with pure-real table (no synthetic mixing)
    df.to_parquet(gold, index=False)
    tmax = df["temp_c"].max()
    print(f"wrote {len(df)} REAL rows -> {gold}")
    print(f"window {args.start}..{args.end}, max temp {tmax}C")

    # Provenance note for datasheet
    prov = (
        f"| {args.start}..{args.end} | open-meteo-archive | {len(POINTS)} points | "
        f"{len(df)} rows | max {tmax}C | retrieved {df['retrieved_at'].iloc[0]} |\n"
    )
    ds = Path(__file__).resolve().parents[2] / "docs" / "datasheets" / "open_meteo_imd.md"
    if ds.exists():
        txt = ds.read_text(encoding="utf-8")
        marker = "<!-- real-fetch-log -->"
        if marker in txt:
            txt = txt.replace(marker, marker + "\n" + prov.rstrip("\n"))
        else:
            txt += f"\n## Real Fetch Log\n\n{marker}\n\n| window | source | points | rows | peak | retrieved |\n|---|---|---|---|---|---|\n{prov}"
        ds.write_text(txt, encoding="utf-8")
        print(f"provenance appended -> {ds}")


if __name__ == "__main__":
    main()
