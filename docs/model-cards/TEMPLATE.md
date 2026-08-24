# Model Card: <MODEL_NAME>

> Adapted from Mitchell et al. 2019 [@mitchell2019modelcards]. Required for every model in `freshroute-optimizer-model/core/` before phase gate closure. See `docs/IMPLEMENTATION_PLAN.md:3.1`.

**Model:** `<ArrheniusDecayEngine / DemandForecaster / ParetoMatcher / VRPRouter>`
**Version:** `vX.Y.Z`  **Date:** `YYYY-MM-DD`  **MLflow Run:** `<run-id>`
**Owners:** `<name>`  **Reviewers:** `<name>`  **DOI:** `10.5281/zenodo.XXXXXXX`
**BibTeX keys:** `[@arrhenius1889, @labuza1993kinetics, ...]`

---

## 1. Model Details

- Architecture, parameters (e.g., `α=0.048`, `β=0.008`, `Ea/R` per tier), training data keys.
- Input/output schema (link `api/schemas.py`, JSON example).
- Version history and paper reference.

## 2. Intended Use

- Primary use, users, geography (Punjab GT corridor: Ludhiana–Amritsar–Jalandhar), time horizon.
- Out-of-scope uses (e.g., not for frozen fish beyond `critical_temp_c`, not validated >48°C).
- Integration point in pipeline (Stage 1–4) and latency SLA.

## 3. Factors

- Relevant factors (climate, humidity, vehicle class, dietary policy, district HVI) and evaluation slices.
- Groups that may be disadvantaged if factor mis-estimated.

## 4. Metrics

| Metric | Overall | By Tier / District slice | Confidence interval | Dataset / split |
| :--- | :--- | :--- | :--- | :--- |
| e.g., Φ RMSE |  |  |  |  |
| Hazard precision/recall |  |  |  |  |
| WAPE 7-day |  |  |  |  |
| Hypervolume |  |  |  |  |

- Thresholds: hazard ≤4h (CRITICAL), ≤12h (ELEVATED) etc.
- Compute cost and p95 latency.

## 5. Evaluation Data

- Datasheet keys, split (train/val/test, walk-forward), time window, geography.
- Why this split and its limitations.

## 6. Training Data

- Datasheet keys, preprocessing, feature list, leakage controls.

## 7. Quantitative Analyses (Ablations)

- Without `Φ_env` vs with, greedy vs MILP, etc.
- Sensitivity (Sobol for `w_i`, `λ`), robustness to 44°C extreme.

## 8. Ethical Considerations

- Dietary strictness (Lacto-Vegetarian, Jain, Halal), hunger-equity fairness (Gini vs HVI), child/senior prioritization.
- Risks and mitigations (zero-tolerance gate `pareto_matcher.py:354-356`).

## 9. Caveats & Recommendations

- Seasonal recalibration need (C6), out-of-calibration flag, fallback behavior (hard 422 if no reefer for CRITICAL_HAZARD).
- Monitoring: drift detectors, alert thresholds, retrain trigger.

## 10. Citation & Provenance

```bibtex
@misc{key,
}
```
Cite: `<DOI>` + model version + paper DOI.

---

*Gate checklist:* metrics reproduced via `replay.sh` MLflow ID, limitations explicitly state climate/diet bounds, reviewer signed.
