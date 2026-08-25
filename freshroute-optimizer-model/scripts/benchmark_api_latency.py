#!/usr/bin/env python3
"""
API latency p95 benchmark — P6 L6.3 (spec 6.1: matcher <100ms, shelf-life <20ms).

Runs N=50 requests per endpoint via TestClient and reports p50/p95/p99.

Usage: python scripts/benchmark_api_latency.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from fastapi.testclient import TestClient

from api.app import app


def pct(arr):
    a = np.asarray(arr) * 1000  # ms
    return f"p50 {np.percentile(a, 50):.1f} p95 {np.percentile(a, 95):.1f} p99 {np.percentile(a, 99):.1f} ms"


def main() -> None:
    client = TestClient(app)
    N = 50

    shelf_payload = {"category": "Dairy", "ambient_temp_c": 42.0, "humidity_pct": 78.0, "elapsed_hours": 2.0}
    shelf_times = []
    for _ in range(N):
        t0 = time.perf_counter()
        r = client.post("/api/v1/predict/shelf-life", json=shelf_payload)
        assert r.status_code == 200
        shelf_times.append(time.perf_counter() - t0)
    print(f"shelf-life (target <20ms):   {pct(shelf_times)}")

    match_payload = {
        "surplus_batch": {
            "batch_id": "BENCH-001",
            "donor_id": "donor-verka-ludhiana-01",
            "category": "Dairy",
            "item_description": "Milk",
            "gross_weight_kg": 950,
            "origin_coordinates": [30.9325, 75.835],
            "dietary_flags": {"is_pure_veg": True},
        },
        "ambient_weather": {"temp_c": 38.0, "humidity_pct": 72.0},
    }
    match_times = []
    for _ in range(N):
        t0 = time.perf_counter()
        r = client.post("/api/v1/optimize/match", json=match_payload)
        assert r.status_code == 200
        match_times.append(time.perf_counter() - t0)
    print(f"match greedy (target <100ms): {pct(match_times)}")

    route_payload = {
        "pickup_nodes": [{"batch_id": "b1", "origin_coordinates": [30.9325, 75.835], "gross_weight_kg": 500, "cold_chain_mandatory": True}],
        "dropoff_nodes": [{"recipient_id": "r1", "coordinates": [31.62, 74.8765]}],
    }
    route_times = []
    for _ in range(N):
        t0 = time.perf_counter()
        r = client.post("/api/v1/optimize/routing", json=route_payload)
        assert r.status_code == 200
        route_times.append(time.perf_counter() - t0)
    print(f"routing heuristic:           {pct(route_times)}")

    fc_times = []
    for _ in range(N):
        t0 = time.perf_counter()
        r = client.get("/api/v1/forecast/demand?district_id=ludhiana&horizon_days=7")
        assert r.status_code == 200
        fc_times.append(time.perf_counter() - t0)
    print(f"forecast (target <80ms):     {pct(fc_times)}")


if __name__ == "__main__":
    main()
