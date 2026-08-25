# Model Card: HungerDemandForecaster (Stage 2) — P3 Stub

> Stage 2 `core/demand_forecaster.py:31` — see `docs/model-cards/TEMPLATE.md` and spec §4.1.

**Version:** v1.0.0-P3-stub  **Date:** 2026-08-26  **MLflow Run:** ` TBD after P3 training`
**Owners:** FreshRoute AI Core  **Reviewers:** pending
**DOI:** `10.5281/zenodo.XXXXXXX`
**BibTeX keys:** `[@ke2017lightgbm; @hochreiter1997lstm; @lim2021tft; @niti2023mpi; @nfhs5; @wfp2024hungermap; @census2011]`

---

## 1. Model Details

- **Stub (P1):** deterministic synthetic 23×7 daily series from `data/punjab_districts.json` weekly priors (HVI, gap_lbs). `forecast(district_id, horizon_days=7)` returns `forecast_demand_lbs` list, `weekly_total_lbs`, `gap_lbs_estimate`, `hunger_vulnerability_index`, `primary_need`, with pilgrim surge `+8%` for Amritsar when `include_pilgrim_surge=True` (spec mock).
- **Planned P3:** LightGBM baseline [@ke2017lightgbm] (tabular, categorical district + calendar) + LSTM sequence [@hochreiter1997lstm] with district embeddings + optional TFT [@lim2021tft] multi-horizon. Features (spec §4.1:168-172): demography (Census 2011, NITI MPI 2023, NFHS-5), calendar (Gurpurab/Diwali/Ramadan/Langar schedules), weather telemetry (IMD/Open-Meteo), 90-day consumption moving average, mandi seasonality (Agmarknet).
- **Deficit score:** `get_deficit_score(district_id)` → 0–100 for matcher `w2=0.30`: `hvi*0.8 + gap_penalty +10`.
- **Inputs:** `district_id`, `horizon_days` (1–30), `include_pilgrim_surge`.
- **Outputs:** per-district forecast dict and `batch_forecast`.

## 2. Intended Use

- `GET /api/v1/forecast/demand` (and POST) — proactive 7-day meal shortfall for matcher `Deficit(j)` and dispatcher dashboard `DISTRICT_DEMAND_FORECAST`.
- Geography: 23 Punjab districts (post-2022 admin). Not for beyond Punjab without retraining.

## 3. Factors

- MPI rank, informal settlement share, child/senior nutrition flags (NFHS-5), stock_hours inverse, pilgrim seasonality.
- Weather & mandi glut as negative demand proxy.

## 4. Metrics (targets, stub not measured)

| Metric | Target | Current stub | Dataset |
| :--- | :--- | :--- | :--- |
| WAPE 7-day | <18% | — (deterministic) | walk-forward CV (P3) |
| Pilgrim surge recall | >0.75 | 1.0 (hard +8% injection) | Amritsar festival weeks |
| Latency 23 districts | <80ms | <5ms (synthetic) | `batch_forecast` |
| HVI correlation ρ | >0.6 (gap vs HVI) | — | `punjab_districts.json` |

## 5. Evaluation Data

- **Datasheets:** `punjab_districts.json`, `mockData.js` DISTRICT_DEMAND_FORECAST as synthetic prior, Agmarknet/IMD gold tables (future).
- **Splits:** Walk-forward expanding window to avoid leakage; hold-out monsoon season.

## 6. Training Data

- Stub: no training, synthetic priors. P3 will use gold tables + calendar features, with leakage controls (lagged features, district embeddings).

## 7. Quantitative Analyses

- Ablation pending: No HVI vs with HVI → Gini improvement; Naive seasonal vs LightGBM vs LSTM vs TFT.

## 8. Ethical Considerations

- **Equity:** HVI prevents nearest-rich bias; monitor allocations vs HVI Gini.
- **Community:** Gurpurab surge is cultural, not just statistical — validate with Langar Sewadars.
- **No PII:** district-aggregated demand, not individual.

## 9. Caveats

- **Stub:** not validated, no intervals, no drift monitoring. WAPE <18% unmeasured.
- **Season:** Pilgrim surge is binary +8%; real surge varies by calendar year.
- **Training debt:** P3 loops L3.1–L3.4 required before gate; see `docs/IMPLEMENTATION_PLAN.md` §5 P3.
