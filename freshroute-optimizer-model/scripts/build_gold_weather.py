#!/usr/bin/env python3
"""
Build gold weather_hourly.parquet from IMD/Open-Meteo (P1 L1.2).

Reads live Open-Meteo or synthetic fallback and writes
data/gold/weather_hourly.parquet.

Usage:
  python scripts/build_gold_weather.py --lat 30.9 --lon 75.85 --date 2026-08-18

Citation: [@imd2024; @openmeteo2024]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description="Build weather_hourly gold")
    ap.add_argument("--lat", type=float, default=30.90)
    ap.add_argument("--lon", type=float, default=75.85)
    ap.add_argument("--date", type=str, default=datetime.today().date().isoformat())
    ap.add_argument("--gold", type=str, default="data/gold/weather_hourly.parquet")
    args = ap.parse_args()

    from data.ingestion.imd_openmeteo import fetch_live
    from data.validation.ge_suites import validate_weather_rows

    rows = fetch_live(args.lat, args.lon, args.date)
    res = validate_weather_rows(rows)
    if not res["success"]:
        print(f"[warn] GE weather failed: {res['errors'][:2]}")

    df = pd.DataFrame(rows)
    df["date"] = args.date

    gold_path = Path(args.gold)
    if not gold_path.is_absolute():
        cand = Path(__file__).resolve().parents[1] / args.gold
        gold_path = cand
    if gold_path.exists():
        existing = pd.read_parquet(gold_path)
        df = pd.concat([existing, df], ignore_index=True)
        df = df.drop_duplicates(subset=["timestamp_utc", "lat", "lon"], keep="last")
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(gold_path, index=False)
    print(f"wrote {len(df)} total rows -> {gold_path} ({len(rows)} new)")


if __name__ == "__main__":
    main()
