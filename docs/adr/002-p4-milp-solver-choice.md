# ADR-002: P4 Pareto Matcher — MILP Solver Choice (PuLP CBC default, OR-Tools CP-SAT fallback)

Date: 2026-08-26
Status: Accepted

## Context

Spec §2.1 defines `S_ij` with MILP “Mixed-Integer Linear Optimization pairing solver” but reference impl is greedy `rank_allocations:382` (<100ms). Inner loop L4.3 requires both v0 greedy and v1 MILP via PuLP/OR-Tools CP-SAT or NSGA-II [@deb2002nsga2] with benchmark hypervolume vs latency. We must choose default solver that satisfies spec §6.1 latency (<100ms greedy, <800ms MILP for N=100) and maintains 100% dietary hard-gate compliance, while keeping dependency optional at P0. Bench needs reproducibility and CI determinism.

## Decision

- **Default MILP solver:** PuLP CBC (`pulp.PULP_CBC_CMD`) [@pulp2011] — chosen for bundling simplicity (CBC ships with PuLP, no external binary beyond `ortools` already required), stable `timeLimit` param, and deterministic `LpStatus` semantics. Time budget default `0.8s` (spec 9.1).
- **Fallback:** OR-Tools CP-SAT (`ortools.sat.python.cp_model`) [@orgtools2024] when `solver="ortools"` requested or PuLP not installed. CP-SAT uses integer scaling (`S_ij*10`, `weight*10` vs `cap*12` for 1.2× leniency) and parallel workers=8.
- **Atomic constraints:** `Σ_j x_ij ≤1` per surplus, `Σ_i w_i x_ij ≤ Cap_j*1.2` per recipient (lenient to tolerate kg/lbs mixed units as in `pareto_matcher.py:339` heuristic), `x_ij=0` if `score_match==0` (diet, t_transit>t_safe, min_score).
- **Fallback chain:** MILP timeout/infeasible → greedy `rank_allocations` (never break pipeline; audit log via `solver` field). Greedy remains default for `POST /api/v1/optimize/match` unless `use_milp=true`.
- **API surface:** `MatchRequest.use_milp`, `solver` (pulp|ortools), `min_score`, `time_limit_secs`, `surplus_batches` batch mode; `MatchResponse.solver` provenance for C2 audit.

## Consequences

- **Pros:** CBC optimal for tested N=100 (163ms), CP-SAT feasible for N=500 within 0.8s (heuristic fallback ensures SLA). Dietary/capacity gates enforced both in `score_match` pre-filter and MILP constraints → 0% violation. Simple install (`pulp==2.8.0` already pinned).
- **Cons:** CBC single-threaded; not fastest for N=500+ sparse. CP-SAT integer scaling loses 0.1 score granularity. NSGA-II frontier not yet wired (future ADR).
- **Operational:** `solve_milp_allocations` sorts results by `match_score` desc for determinism; latency logged via `execution_latency_ms`.

## Alternatives Considered

- **OR-Tools CP-SAT as default:** rejected as primary because CP-SAT needs careful tuning of `num_search_workers` and may return `FEASIBLE` not `OPTIMAL` within budget; CBC gives clearer `Optimal` status for small N. Kept as opt-in.
- **NSGA-II/pymoo as default:** rejected for now — multi-objective hypervolume exploration valuable for paper but adds heavy dependency and non-determinism; reserved for P4 frontier analysis (`[@deb2002nsga2]`).
- **Greedy-only:** rejected — fails aggregate capacity feasibility (e.g., 2×600kg to 900L hub: greedy 143.4 infeasible total, MILP 111.9 feasible via spillover).

## Citations

- [@wolsey1998integer] MILP formulation correctness
- [@pulp2011] PuLP toolkit
- [@orgtools2024] OR-Tools CP-SAT
- [@deb2002nsga2] NSGA-II hypervolume (future)
- [@saaty1980ahp] weight elicitation `w=[0.35,0.30,0.20,0.15]`
- [@pareto1896] Pareto optimality

## Reversibility

Flip default `solver="ortools"` or add `pymoo` NSGA-II behind feature flag; one-line change in `api/routes.py:222` and `ParetoMatchingEngine.solve_milp_allocations` signature. ADR-002 superseded would document new default and latency re-bench.

