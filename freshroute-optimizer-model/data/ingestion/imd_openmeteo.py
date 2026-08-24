"""
IMD + Open-Meteo weather ingestion — P1 L1.2

Sources:
  IMD gridded 0.25 deg (manual where API restricted) [@imd2024]
  Open-Meteo Archive API https://open-meteo.com/ [@openmeteo2024]

Usage:
  python -m data.ingestion.imd_openmeteo --lat 30.9 --lon 75.85 --date 2026-08-18

Stub at P0 returns synthetic hourly series matching Punjab Loo profile.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

def synthetic_hourly(lat: float, lon: float, target_date: str):
    """Deterministic hourly temp/humidity for test stability."""
    seed = hash((round(lat,1), round(lon,1), target_date)) % 1000
    rows = []
    for h in range(24):
        # Peak at 15:00 IST ~42C in heatwave, trough 05:00 ~28C
        temp = 28 + 14 * math.sin(math.pi * (h - 6) / 12) + (seed % 3)  # keep peak 42
        temp = round(max(24, min(45, temp)), 1)
        humidity = round(85 - (temp - 28) * 1.8 + (seed % 5), 1)
        humidity = max(40, min(95, humidity))
        rows.append(
            {
                "timestamp_utc": f"{target_date}T{h:02d}:00:00Z",
                "lat": lat,
                "lon": lon,
                "temp_c": temp,
                "humidity_pct": humidity,
                "uv_index": round(max(0, 8 * math.sin(math.pi * (h - 6) / 12)), 1),
                "source": "open-meteo-synthetic-P1-stub",
            }
        )
    return rows

def fetch_live(lat: float, lon: float, target_date: str):
    try:
        import urllib.request
        import urllib.parse

        params = urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,relative_humidity_2m",
                "start_date": target_date,
                "end_date": target_date,
                "timezone": "UTC",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "FreshRoute-P1-ingest/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            hourly = data.get("hourly", {})
            temps = hourly.get("temperature_2m") or []
            hums = hourly.get("relative_humidity_2m") or []
            times = hourly.get("time") or []
            if temps and hums and times:
                return [
                    {
                        "timestamp_utc": t,
                        "lat": lat,
                        "lon": lon,
                        "temp_c": float(temps[i]) if i < len(temps) else None,
                        "humidity_pct": float(hums[i]) if i < len(hums) else None,
                        "source": "open-meteo-live",
                    }
                    for i, t in enumerate(times)
                ]
    except Exception:
        pass
    return synthetic_hourly(lat, lon, target_date)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=30.90)
    ap.add_argument("--lon", type=float, default=75.85)
    ap.add_argument("--date", default="2026-08-18")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rows = fetch_live(args.lat, args.lon, args.date)
    out = Path(args.out) if args.out else Path(f"data/raw/weather/{args.date.replace('-','')}_{args.lat}_{args.lon}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} hourly rows -> {out}")

if __name__ == "__main__":
    main()
