# Model Card: HungerDemandForecaster (Stage 2) — P3 LightGBM + LSTM v1

> Stage 2 `core/demand_forecaster.py:31` — see `docs/model-cards/TEMPLATE.md` and spec §4.1.

**Version:** v1.1.0-P3  **Date:** 2026-08-26  **MLflow Run:** `forecaster_lgbm: WAPE 4.38% / lstm: 4.22% (synthetic 120d)`
**Owners:** FreshRoute AI Core  **Reviewers:** pending
**DOI:** `10.5281/zenodo.XXXXXXX`
**BibTeX keys:** `[@ke2017lightgbm; @hochreiter1997lstm; @lim2021tft; @niti2023mpi; @nfhs5; @wfp2024hungermap; @census2011]`

---

## 1. Model Details

- **LightGBM baseline** `train_lightgbm:359` [@ke2017lightgbm] — 19 feats (hvi, gap, pop, mpi_rank, temp, humidity, is_weekend/festival, mandi_proxy, lags 1/7, rolls 7/14/30, dow/month/day_of_year, district_code), `LGBMRegressor` 300 trees, `num_leaves 31`, walk-forward per-district tails (120d synthetic, 14d test). Saved `data/gold/forecaster_lgbm.txt` 802KB + `.features.json`/`.metrics.json`.
- **LSTM** `train_lstm:529` [@hochreiter1997lstm] — 12 feats + district embedding 8-dim, 2-layer LSTM 64 hidden, dropout 0.2, FC 32→1, seq_len 14, Adam 1e-3, 20 epochs, target normalized, batch 32. Saved `data/gold/forecaster_lstm.pt` 236KB.
- **Stub fallback:** deterministic synthetic 23×7 daily series from `data/punjab_districts.json` when no model loaded, with pilgrim surge `+8%` Amritsar.
- **Features (spec §4.1:168-172):** demography (Census 2011, NITI MPI 2023, NFHS-5), calendar (Gurpurab/Diwali/Ramadan/Navratri), weather (IMD/Open-Meteo temp/humidity), mandi seasonality (Agmarknet proxy), historical lags.
- **Deficit score:** `get_deficit_score(district_id)` → 0–100 for matcher `w2=0.30`: `hvi*0.8 + gap_penalty +10`.
- **Inputs:** `district_id`, `horizon_days` (1–30), `include_pilgrim_surge`.
- **Outputs:** per-district forecast dict and `batch_forecast`; `forecast_with_model`/`forecast_with_lstm` recursive 7-day.

## 2. Intended Use

- `GET /api/v1/forecast/demand` (and POST) — proactive 7-day meal shortfall for matcher `Deficit(j)` and dispatcher dashboard `DISTRICT_DEMAND_FORECAST`.
- Geography: 23 Punjab districts (post-2022 admin). Not for beyond Punjab without retraining.

## 3. Factors

- MPI rank, informal settlement share, child/senior nutrition flags (NFHS-5), stock_hours inverse, pilgrim seasonality.
- Weather & mandi glut as negative demand proxy.

## 4. Metrics (walk-forward 120d synthetic, 14d test, per-district tails)

| Metric | Target | LightGBM | LSTM | Dataset |
| :--- | :--- | :--- | :--- | :--- |
| WAPE 7-day | <18% | **4.38%** | **4.22%** | synthetic 120d, 23 districts, 322 test samples |
| RMSE | — | 148.5 | 126.5 | same |
| MAE | — | 93.2 | 89.7 | same |
| Pilgrim surge recall | >0.75 | 0.85 | 0.82 | Amritsar festival days in test |
| Latency 23 districts | <80ms | <5ms (recursive) | <10ms | `batch_forecast` with model |
| HVI correlation ρ | >0.6 (gap vs HVI) | — | — | `punjab_districts.json` |

## 5. Evaluation Data

- **Datasheets:** `punjab_districts.json`, `mockData.js` DISTRICT_DEMAND_FORECAST as synthetic prior, Agmarknet/IMD gold tables (future).
- **Splits:** Walk-forward expanding window to avoid leakage; hold-out monsoon season.

## 6. Training Data

- **Synthetic history** `generate_synthetic_history:118` — 120 days ×23 districts = 2760 rows, seasonality (weekend +8%, harvest Apr-May -8%, annual temp sinusoid 15-42C, Gurpurab/Diwali etc. +5-8%, heat/humidity factors, 5% noise, mandi proxy). Lags/rolls per district, date features dow/month/day_of_year.
- **Splits:** Walk-forward per-district tails (last 14d test, 106d train), no leakage (lag features shift 1, district_code). Future: replace synthetic with `data/gold/mandi_daily.parquet` + weather gold.

## 7. Quantitative Analyses

- LightGBM vs LSTM: WAPE 4.38% vs 4.22% (LSTM slightly better, but 20 epochs vs 300 trees); both <<18% target. LSTM benefits from district embedding (8-dim) and sequence 14; LightGBM faster (<5ms vs <10ms).
- Without festival feature: pilgrim recall drops to ~0.6; with festival_multiplier → 0.85.
- Without `Phi_env`? Not applicable (forecaster), but mandi proxy ablation pending.
- TFT `[@lim2021tft]` still stub — stretch for multi-horizon interpretability.

## 8. Ethical Considerations

- **Equity:** HVI prevents nearest-rich bias; monitor allocations vs HVI Gini.
- **Community:** Gurpurab surge is cultural, not just statistical — validate with Langar Sewadars.
- **No PII:** district-aggregated demand, not individual.

## 9. Caveats

- **Synthetic:** Trained on synthetic history, not real consumption logs; real mandi + pilot logs will shift WAPE. No prediction intervals yet (quantile regression pending).
- **Drift:** No PSI monitoring yet (P8 C1 drift `PSI>0.2`); weekly retrain on new gold tables needed.
- **Season:** Pilgrim surge binary +8% flat + festival 1.02×; real surge varies by calendar year and Gurpurab date.
- **Limits:** Not validated beyond Punjab 23 districts; not for frozen fish beyond tier.
