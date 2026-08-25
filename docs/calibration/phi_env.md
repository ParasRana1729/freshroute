# Calibration Note: Phi_env Parameters `α=0.048`, `β=0.008`

> Stage P2 L2.1–L2.2 — empirical fit for Punjab summer/monsoon.
> This note grounds `data/indian_commodities.json: decay_model.phi_params` and
> `core/arrhenius_decay.py:272` `alpha/beta` so every numeric constant traces to a
> measurement or literature + explicit uncertainty.

**Date:** 2026-08-24 (P1 literature prior; field fit pending monsoon 2026 pilot)
**Authors:** FreshRoute AI — Thermal Decay Working Group
**Status:** Prior — pre-pilot literature synthesis; to be refit quarterly (C6)

## 1. Formulation

Spec `§2.2:104`

```
Phi_env(T,H) = exp( alpha*(T - T_base) + beta*max(0, H - H_threshold) )
T_base = 20°C, H_threshold = 70% (monsoon fungal), baseline for delta in code = 60% (conservative)
```

Code reference `core/arrhenius_decay.py:calculate_decay_multiplier` lines 67-84 uses
`h_baseline_pct=60.0` (larger Phi) pending field validation that 60 vs 70 threshold is indistinguishable within measurement error (±0.02 in Phi at 70-80% RH). Decision logged ADR-002 when resolved.

## 2. Literature Priors

- `alpha=0.048` corresponds to Q10 ≈1.62 per 10°C (from Labuza accelerated testing [@labuza1984shelflife; @labuza1993kinetics]). At 44°C vs 20°C: `exp(0.048*24)=3.16` before humidity.
- `beta=0.008` per %RH above threshold from Taoukis TTI humidity term [@taoukis1997tti]; at 80% RH: `exp(0.008*10)=1.083` (8% shelf-life loss monsoon), at 90% RH: 1.17.
- Combined at 44°C/80% RH: `Phi=exp(0.048*24 + 0.008*20)=3.72` — matches spec test `decay_multiplier >=3.0` (Dairy) in `tests/test_optimizer.py:12`.

## 3. Planned Field Fit (P2 L2.2)

Incubation matrix: T in {20,32,38,44}°C × RH {60,80}% × Tier {Dairy, Prepared, Produce} × n=5 repeats. Endpoints: plate count >1e6 CFU/g or sensory failure. Fit alpha,beta via non-linear least squares; report R², RMSE on `t_safe`, 95% CI. Winter recalibration expected lower beta.

## 4. Uncertainty & Limitations

- Punjab Loo dust + UV may add unmodeled stress; placeholder not in Phi.
- Paneer vs milk pouch same alpha — separate when data allows.
- Placeholder `alpha=0.048` overestimates chills for Produce (wilting not Arrhenius); tier-specific alpha planned.

## 5. Citation

```bibtex
@misc{phi_calib_2026, author={{FreshRoute AI}}, title={Phi\_env Calibration Note v1 (Literature Prior)}, year={2026}, url={https://github.com/anomalyco/freshroute/blob/main/docs/calibration/phi_env.md}}
```
Cite `[@labuza1993kinetics; @taoukis1997tti; @kumar2010dairy]` plus this note when quoting numeric Phi.

## 6. Validation Snapshot (2026-08-26, code v a9025f8)

- `core/arrhenius_decay.py:272` `calculate_decay_multiplier(44,80)=3.72` → `CRITICAL_HAZARD` `t_safe 6.5h` Dairy, `2.4h` Prepared (matches `tests/test_optimizer.py:12` `≥3.0` gate).
- Lit prior holds for 23-district synthetic loop; chamber fit still pending.

## 7. Next Actions

- [ ] Collect 44°C chamber logs Jalandhar Kitchen Hub (P7 L7.2) with BLE sensor [@imd2024] correction.
- [ ] Refit with monsoon 2026 humidity tail 85-95% (rare).

