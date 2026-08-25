#!/usr/bin/env python3
"""
Build gold mandi_daily.parquet from raw agmarknet JSONs (P1 L1.1).

Reads data/raw/agmarknet/*.json (or generates synthetic fallback),
validates via data.validation.ge_suites, and writes
data/gold/mandi_daily.parquet (DVC-tracked, gitignored).

Usage:
  python -m scripts.build_gold_mandi --date 2026-08-18
  python scripts/build_gold_mandi.py --backfill 2026-08-01:2026-08-18

Citation: [@agmarknet2024; @gebru2021datasheets]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure freshroute-optimizer-model on path for `import data.*` when run as script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd


def build_for_date(target_date: str, raw_dir: Path, gold_path: Path) -> int:
    from data.ingestion.agmarknet import fetch_live, synthetic_rows
    from data.validation.ge_suites import validate_agmarknet_rows

    # Try raw file first
    raw_file = raw_dir / f"{target_date.replace('-','')}.json"
    if raw_file.exists():
        rows = json.loads(raw_file.read_text(encoding="utf-8"))
    else:
        rows = fetch_live(target_date)
        if len(rows) < 5:
            rows = synthetic_rows(target_date)

    # Validate
    res = validate_agmarknet_rows(rows)
    if not res["success"]:
        print(f"[warn] GE failed for {target_date}: {res['errors'][:2]}")

    # To DataFrame
    df = pd.DataFrame(rows)
    # Normalize dtypes
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df["arrival_quintals"] = pd.to_numeric(df["arrival_quintals"], errors="coerce")
    df["price_modal_inr_per_quintal"] = pd.to_numeric(df["price_modal_inr_per_quintal"], errors="coerce")

    # Append or create parquet
    if gold_path.exists():
        existing = pd.read_parquet(gold_path)
        df = pd.concat([existing, df], ignore_index=True)
        df = df.drop_duplicates(subset=["mandi_id", "commodity", "date"], keep="last")
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(gold_path, index=False)
    print(f"wrote {len(df)} total rows -> {gold_path} ({target_date} {len(rows)} new)")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build mandi_daily gold")
    ap.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
    ap.add_argument("--backfill", type=str, default=None, help="YYYY-MM-DD:YYYY-MM-DD")
    ap.add_argument("--raw-dir", type=str, default="data/raw/agmarknet")
    ap.add_argument("--gold", type=str, default="data/gold/mandi_daily.parquet")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    gold_path = Path(args.gold)
    # Resolve relative to freshroute-optimizer-model when run from repo root
    if not raw_dir.is_absolute():
        cand = Path(__file__).resolve().parents[1] / args.raw_dir
        if cand.exists() or not raw_dir.exists():
            raw_dir = cand
    if not gold_path.is_absolute():
        cand = Path(__file__).resolve().parents[1] / args.gold
        gold_path = cand if cand.parent.exists() or not gold_path.parent.exists() else gold_path

    if args.backfill:
        s, e = args.backfill.split(":")
        start = datetime.fromisoformat(s).date()
        end = datetime.fromisoformat(e).date()
        cur = start
        total = 0
        while cur <= end:
            total += build_for_date(cur.isoformat(), raw_dir, gold_path)
            cur += timedelta(days=1)
        print(f"backfill done total new {total}")
    else:
        d = args.date or datetime.today().date().isoformat()
        build_for_date(d, raw_dir, gold_path)


if __name__ == "__main__":
    main()
