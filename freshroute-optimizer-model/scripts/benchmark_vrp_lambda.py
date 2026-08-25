#!/usr/bin/env python3
"""
VRP λ grid + Solomon-style benchmark (P5 L5.2).

Runs solve_vrp with λ∈[0.5,1,2,5] on a synthetic Punjab corridor
(Ludhiana→Amritsar) and reports cost vs time vs t_safe feasibility.
Solomon format loader is minimal — for full Solomon 1987 instances,
place *.txt in data/solomon/ and loader will parse.

Usage:
  python scripts/benchmark_vrp_lambda.py
  python scripts/benchmark_vrp_lambda.py --solomon data/solomon/C101.txt

Citations: [@toth2014vrp; @solomon1987; @orgtoolsvrp2024]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.vrp_router import VRPRouter


def solomon_loader(path: Path):
    """Minimal Solomon 1987 parser: skips header, reads CUST NO, XCOORD, YCOORD, DEMAND, READY, DUE, SERVICE."""
    nodes = []
    with path.open() as f:
        lines = f.readlines()
    # Find header line with CUST
    start = 0
    for i, l in enumerate(lines):
        if "CUST" in l and "XCOORD" in l:
            start = i + 1
            break
    for l in lines[start:]:
        parts = l.strip().split()
        if len(parts) < 7 or not parts[0].isdigit():
            continue
        nodes.append(
            {
                "id": int(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "demand": float(parts[3]),
                "ready": int(parts[4]),
                "due": int(parts[5]),
                "service": int(parts[6]),
            }
        )
    return nodes


def main() -> None:
    ap = argparse.ArgumentParser(description="VRP lambda grid benchmark")
    ap.add_argument("--solomon", type=str, default=None, help="path to Solomon instance txt")
    ap.add_argument("--lambdas", type=str, default="0.5,1,2,5", help="comma lambda grid")
    args = ap.parse_args()

    lambdas = [float(x) for x in args.lambdas.split(",")]
    router = VRPRouter()

    # Synthetic Punjab GT corridor (NH44) — 5 dropoffs
    pickup = [{"batch_id": "b1", "origin_coordinates": [30.9325, 75.835], "gross_weight_kg": 900, "cold_chain_mandatory": True}]
    dropoffs = [
        {"recipient_id": f"r{i}", "coordinates": [30.9 + 0.15 * i, 75.85 + 0.08 * i], "demand_kg": 300}
        for i in range(5)
    ]

    print("λ grid benchmark (synthetic Punjab corridor, 5 stops):")
    print(f"{'λ':>5} | {'solver':<30} | {'dist km':>8} | {'eta min':>8} | {'feasible':<8}")
    for lam in lambdas:
        t0 = time.perf_counter()
        res = router.solve_vrp(pickup, dropoffs, use_or_tools=True, t_safe_hours=[6] * 5, lambda_penalty=lam, time_limit_secs=1.5)
        dt = (time.perf_counter() - t0) * 1000
        feas = "yes" if res["solver"].startswith("ortools") else "heur"
        print(f"{lam:5.1f} | {res['solver']:<30} | {res['total_distance_km']:8.1f} | {res['total_eta_minutes']:8d} | {feas:<8} ({dt:.0f}ms)")

    if args.solomon and Path(args.solomon).exists():
        nodes = solomon_loader(Path(args.solomon))
        print(f"\nSolomon {Path(args.solomon).name}: {len(nodes)} nodes, first 3: {nodes[:3]}")
        # Map Solomon to VRP (depot 0, rest dropoffs) — scale demand/ready/due to kg/min
        # Quick smoke: use first 5 customers as dropoffs
        s_pickup = [{"batch_id": "b1", "origin_coordinates": [30.9325, 75.835], "gross_weight_kg": sum(n['demand'] for n in nodes[1:6]), "cold_chain_mandatory": False}]
        s_dropoffs = [{"recipient_id": f"s{n['id']}", "coordinates": [30.9 + n["x"] * 0.01, 75.85 + n["y"] * 0.01]} for n in nodes[1:6]]
        res = router.solve_vrp(s_pickup, s_dropoffs, use_or_tools=True, t_safe_hours=[12] * 5)
        print(f"Solomon 5-cust VRP: {res['total_distance_km']}km, solver {res['solver']}")
    else:
        print("\n(no Solomon file — place C101.txt in data/solomon/ for full bench [@solomon1987])")


if __name__ == "__main__":
    main()
