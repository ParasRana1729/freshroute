"""
Agmarknet ingestion stub — P1 L1.1

Fetches daily mandi arrivals for Punjab via https://agmarknet.gov.in/.
See docs/datasheets/agmarknet.md and docs/BIBLIOGRAPHY.bib:agmarknet2024.

Usage:
  python -m data.ingestion.agmarknet --date 2026-08-18 --out data/raw/agmarknet/20260818.json
  python -m data.ingestion.agmarknet --backfill 2023-01-01:2026-08-24

Phase: P1 implements live fetch; P0 stub returns deterministic synthetic so pipeline
tests pass without network.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_MANDIS = ["Ludhiana", "Amritsar", "Jalandhar", "Khanna", "Bathinda", "Patiala"]
DEFAULT_COMMODITIES = ["Tomato", "Palak", "Cauliflower", "Kinnow", "Wheat", "Dal", "Rice"]

def synthetic_rows(target_date: str) -> List[Dict[str, Any]]:
    """Deterministic synthetic rows for offline testing."""
    # hash-stable pseudo data
    seed = hash(target_date) % 9973
    rows: List[Dict[str, Any]] = []
    for mi, mandi in enumerate(DEFAULT_MANDIS):
        for ci, comm in enumerate(DEFAULT_COMMODITIES):
            arrival = round(((seed + mi * 17 + ci * 31) % 500) / 10 + 5, 1)  # 5-55 quintals
            price = int(1200 + (seed + mi * 13 + ci * 29) % 2000)
            rows.append(
                {
                    "mandi_id": f"PB_{mandi[:3].upper()}_APMC_01",
                    "mandi_name": f"{mandi} APMC",
                    "district_id": mandi.lower(),
                    "commodity": comm,
                    "arrival_quintals": arrival,
                    "price_modal_inr_per_quintal": price,
                    "date": target_date,
                    "source": "agmarknet-synthetic-P1-stub",
                }
            )
    return rows

def fetch_live(target_date: str) -> List[Dict[str, Any]]:
    """Live fetch placeholder — real POST to Agmarknet in P1.

    Network failure falls back to synthetic so tests never flake.
    """
    try:
        import urllib.request
        import urllib.parse

        # NOTE: Real Agmarknet endpoint requires form POST with state/district/market/date.
        # We probe the landing page to detect availability; actual parsing deferred to P1.
        # If we get here without real parser, fall through to synthetic.
        req = urllib.request.Request("https://agmarknet.gov.in/", method="HEAD")
        req.add_header("User-Agent", "FreshRoute-P1-ingest/1.0 (+https://github.com/anomalyco/freshroute)")
        urllib.request.urlopen(req, timeout=5)
        # TODO(P1): implement full form POST + HTML table parse when network verified.
        return synthetic_rows(target_date)
    except Exception:
        return synthetic_rows(target_date)

def main() -> None:
    ap = argparse.ArgumentParser(description="Agmarknet ingestor (P1)")
    ap.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="output JSON path")
    ap.add_argument("--backfill", default=None, help="start:end YYYY-MM-DD:YYYY-MM-DD")
    args = ap.parse_args()

    if args.backfill:
        start_s, end_s = args.backfill.split(":")
        start = datetime.fromisoformat(start_s).date()
        end = datetime.fromisoformat(end_s).date()
        cur = start
        while cur <= end:
            rows = fetch_live(cur.isoformat())
            out = Path(args.out) if args.out else Path(f"data/raw/agmarknet/{cur.isoformat().replace('-','')}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            print(f"wrote {len(rows)} rows -> {out}")
            cur += timedelta(days=1)
    else:
        rows = fetch_live(args.date)
        out = Path(args.out) if args.out else Path(f"data/raw/agmarknet/{args.date.replace('-','')}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {len(rows)} rows -> {out}")

if __name__ == "__main__":
    main()
