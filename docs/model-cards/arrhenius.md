# Model Card: ThermalDecayEngine (Arrhenius + Phi_env)

> Stage 1 `core/arrhenius_decay.py:272` — see `docs/model-cards/TEMPLATE.md`.

**Version:** v1.0.0-P2  **MLflow Run:** ` TBD after calibration loop` **Date:** 2026-08-24
**Citations:** `[@arrhenius1889; @labuza1993kinetics; @taoukis1997tti; @kumar2010dairy; @fssai2011]`

## 1. Details

Physics + empirical humidity: `k(T)=A exp(-Ea/RT)` and `Phi_env=exp(alpha*(T-T_base)+beta*max(0,H-H_threshold))` with `alpha=0.048, beta=0.008, T_base=20C, H_threshold=70%`. Inputs `category, ambient_temp_c, humidity_pct, elapsed_hours`; outputs `dynamic_safe_hours_remaining, risk_classification, cold_chain_mandatory, decay_multiplier`. 5 tiers from `data/indian_commodities.json`.

## 2. Intended Use

Real-time `POST /api/v1/predict/shelf-life` (spec §5.1) for routing feasibility `t_transit ≤ t_safe`. Geography: Punjab ambient corridor (tested 5–44C, 40–90% RH). Latency <20ms p95. Not for frozen (<0C) or retort-stable.

## 3. Factors

Temp, humidity, elapsed_hours, tier. Slices by tier (Dairy most sensitive, Grains least).

## 4. Metrics

| Metric | Dairy @44C | Produce 38C | Overall |
| :--- | :--- | :--- | :--- |
| decay_multiplier | ≥3.0 (spec test) | ~2.2 | monotonic ↑ with T,H |
| remaining_hours RMSE (vs lab held-out) | <1.2h target P2 | <2h | pending L2.2 |

Hazard thresholds: `CRITICAL_HAZARD ≤4h`, `ELEVATED_RISK ≤12h` [@taoukis1997tti].

## 5. Evaluation Data

Literature curves + optional lab incubations (5 repeats per condition). Walk-forward not applicable.

## 6. Training Data

No ML training; literature priors + non-linear least squares fit for alpha/beta if lab available.

## 7. Ablations

Without beta (humidity) vs with: monsoon 80% RH at 36C raises Phi by ~1.08× per spec.

## 8. Ethical

No PII. Failure mode: under-estimating Phi (optimistic t_safe) → spoilage risk; mitigate by hard `cold_chain_mandatory` if `remaining ≤4h` or `temp> critical_temp_c`.

## 9. Caveats

Alpha/beta fitted Punjab summer; winter recalibration needed (C6). Dairy paneer vs milk pouch same params — future split.

