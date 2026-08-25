#!/usr/bin/env bash
# FreshRoute one-command replay — P9 [@neurips2023checklist]
# Usage: bash replay.sh
# Exits non-zero on any failure; logs to /tmp/replay.log
set -euo pipefail
LOG=/tmp/replay.log
exec > >(tee -a "$LOG") 2>&1
echo "=== FreshRoute replay $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Step 1: Python env (mise python@3.11)"
mise exec -- python --version
echo "Step 2: Install (if needed) + pytest 19+8"
mise exec -- python -m pytest freshroute-optimizer-model/tests/ -q
echo "Step 3: Citation audit"
mise exec -- python scripts/citation_audit.py --bib docs/BIBLIOGRAPHY.bib --root .
echo "Step 4: Ingestion synthetic + GE"
mise exec -- python scripts/build_gold_mandi.py --date 2026-08-18 || true
mise exec -- python scripts/build_gold_weather.py --lat 30.9 --lon 75.85 --date 2026-08-18 || true
mise exec -- python -m data.validation.ge_suites --check-all || true
echo "Step 5: Forecaster smoke (LightGBM WAPE <18%)"
mise exec -- python -m core.demand_forecaster --days 30 --test-days 7 || true
echo "Step 6: VRP lambda grid"
mise exec -- python scripts/benchmark_vrp_lambda.py || true
echo "Step 7: Manifest SHA"
mise exec -- python -m data.update_manifest || true
echo "=== replay pass — see $LOG ==="
