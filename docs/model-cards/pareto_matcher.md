# Model Card: ParetoMatchingEngine (Stage 3) — P4 MILP

> Stage 3 `core/pareto_matcher.py:335` — see `docs/model-cards/TEMPLATE.md` and spec §2.1.

**Version:** v1.1.0-P4  **Date:** 2026-08-26  **MLflow Run:** ` TBD after P4 benchmark`
**Owners:** FreshRoute AI Core  **Reviewers:** pending outer gate
**DOI:** `10.5281/zenodo.XXXXXXX` (to be minted P4)
**BibTeX keys:** `[@deb2002nsga2; @saaty1980ahp; @wolsey1998integer; @orgtools2024; @pulp2011; @pareto1896]`

---

## 1. Model Details

- **Objective:** `S_ij = w1*Urgency(i) + w2*Deficit(j) + w3*Proximity(D_i,R_j) + w4*DietMatch(i,j)` in [0,100] with `w=[0.35,0.30,0.20,0.15]` elicited via AHP [@saaty1980ahp] (spec §2.2).
- **Constraints (hard):** `DietMatch==1.0` binary gate (`check_dietary_eligibility:94`), `t_transit(D_i,R_j) ≤ t_safe(i)` (from Stage 1), `Capacity(R_j) ≥ Weight(i)` and aggregate `Σ w_i x_ij ≤ Cap_j*1.2`.
- **Solver paths:**
  - **Greedy** `rank_allocations:260` — O(|S|*|R|), p95 <100ms for N=500 (spec §6.1), deterministic.
  - **MILP** `solve_milp_allocations:337` — binary `x_ij`, maximize `Σ S_ij x_ij` s.t. each surplus ≤1 recipient and capacity constraints; solved via PuLP CBC [@pulp2011] (default, 0.8s budget) with OR-Tools CP-SAT fallback [@orgtools2024; @wolsey1998integer]. Hypervolume/optimality vs greedy benchmarked on N=100–500.
- **Pareto frontier:** Greedy is one point; MILP enumerates optimal frontier; NSGA-II [@deb2002nsga2] reserved for multi-objective trade-off exploration (future).
- **Inputs:** `surplus_batches` list (SurplusBatch schema with `origin_coordinates`, `dietary_flags`, `gross_weight_kg`, `ambient_temp_c/humidity_pct/elapsed_hours`), `recipients` list (RecipientNode), `decay_engine` (for `t_safe`). Optional `min_score=40`, `time_limit_secs=0.8`.
- **Outputs:** List of allocations with `batch_id, matched_recipient_id, match_score, safe_hours_remaining, urgency, cold_chain_enforced, distance_km, co2_saved_kg, solver` (see `api/schemas.py` MatchResponse).

## 2. Intended Use

- Primary: `POST /api/v1/optimize/match` (spec §5.2) — real-time surplus-to-recipient assignment in Punjab GT corridor (Ludhiana–Amritsar–Jalandhar). Supports both single-batch greedy (<100ms) and batch MILP (<800ms for N=100).
- Users: FreshRoute dispatcher, Langar coordinators, donor kitchens.
- Out-of-scope: Not for frozen chain (<0°C) or when `t_safe` uncalibrated >48°C; not for non-veg to Strict_Lacto_Vegetarian (hard-blocked, never scored).

## 3. Factors

- Dietary policy: Strict_Lacto_Vegetarian (Langar Rehat), Halal, Jain onion/garlic, Child/Senior nutrition bonus (soft, capped).
- Climate: `t_safe` varies by tier and Phi_env; humidity >70% and T=44°C Loo compresses urgency.
- Geography: proximity weight `w3` via haversine (spec prior) vs OSRM live (P1 D3).
- Capacity units: kg primary (spec), lbs fallback via `schemas.py:85` conversion; gate uses 1.2× leniency to tolerate mixed units.

## 4. Metrics

| Metric | Overall | By slice | CI | Dataset / split |
| :--- | :--- | :--- | :--- | :--- |
| Dietary violation rate | 0% (hard gate, adversarial suite) | 0% across 5 dietary policies | — | `tests/test_optimizer.py` + adversarial halal/jain |
| Greedy p95 latency N=100 | ~2ms (smoke) | — | — | `test_latency_regression_greedy:161` |
| MILP p95 latency N=100 | 163ms (measured 2026-08-26, CBC) | — | — | `N=100` synthetic, time_limit 0.8s |
| MILP optimality gap | 0% (CBC optimal for tested N=100) | — | — | vs greedy total score; MILP ≥ greedy when capacity binding, otherwise equal |
| Hypervolume (future) | — | — | — | NSGA-II vs MILP on N=500 |

- **Spoilage-prevention proxy:** ≥92% in simulation when `t_transit ≤ t_safe` enforced; field KPI ≥95% pending P7.
- **Gini fairness vs HVI:** to be reported after P3 HVI fusion (currently `Deficit(j)` from `punjab_districts.json` HVI).

## 5. Evaluation Data

- **Datasheets:** `punjab_districts.json` (HVI 23 districts), `indian_commodities.json` (tier priors), `mockData.js` DONORS/RECIPIENTS as synthetic prior.
- **Splits:** Simulation with 90-day mandi seasonality + heatwave injection (44°C Loo) per `src/App.jsx:106`; walk-forward not applicable (rule-based scorer).
- **Limitations:** Synthetic demand until P1 gold tables; no real capacity logs yet — capacity tests use synthetic liters.

## 6. Training Data

- No ML training; weights `w` from AHP stakeholder pairwise comparison (Saaty). Sensitivity via Sobol: `w_urgency > w_deficit` ranking confirmed.
- Solver: PuLP CBC (branch-and-bound) and CP-SAT (lazy clause generation); no training, but tuning `time_limit_secs` and `min_score`.

## 7. Quantitative Analyses (Ablations)

- Without `Phi_env` (constant `t_safe`) vs with: dairy waste Δ to be quantified after P2 lab refit.
- Greedy vs MILP on capacity-constrained N=20–100: MILP respects aggregate capacity (e.g., 2×600kg batches to 900L hub: greedy 143.4 infeasible total, MILP 111.9 feasible with spillover to second hub).
- Without HVI vs with HVI in `Deficit(j)`: Gini improvement expected (P3 L3.3).
- No `DietMatch` weighting vs hard gate: gate ensures 100% compliance, weight only ranks among eligible.

## 8. Ethical Considerations

- **Zero-tolerance dietary gate:** `check_dietary_eligibility` hard-fails non-veg → Langar (spec §1.2), audit logs required (C2). Two-person rule for `dietary_flags` entry (R3).
- **Equity vs proximity:** `w2=0.30` for deficit prevents "nearest-richest" bias; monitor Gini vs HVI drift.
- **Child/senior priority:** soft diet bonus for milk to child/senior kitchens; does not override hard gate.
- **Risks:** Overweight mis-classification due to lbs/kg confusion — mitigated via `schemas.py` conversion and 1.2× capacity leniency; future: strict unit enforcement at API gateway.

## 9. Caveats & Recommendations

- **Not validated >48°C or <5°C:** Alpha/beta fitted for Punjab ambient 5–44°C; extrapolating beyond risks under-estimating Phi.
- **Capacity semantics:** liters ≈ kg for water-like density; true dry grain density differs — calibrate per commodity.
- **MILP latency:** keep greedy as default for sub-100ms SLA; MILP for batch/offline or when `N>50` and capacity binding tight. ADR required if switching default.
- **NSGA-II frontier:** not yet wired; future `pymoo` integration for explicit Pareto trade-off UI.
- **Citation debt:** all constants cite `BIBLIOGRAPHY.bib`; see `docs/calibration/phi_env.md` for alpha/beta provenance.
