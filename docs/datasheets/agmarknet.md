# Datasheet for Dataset: Agmarknet Daily Mandi Arrivals (D1)

> See template `docs/datasheets/TEMPLATE.md` and `docs/BIBLIOGRAPHY.bib:agmarknet2024`.

**Dataset:** Agmarknet Mandi Arrivals — Punjab subset
**Version:** v1.0.0-P1  **DOI:** `10.5281/zenodo.XXXXXXX (pending P1 gate)`  **Date:** 2026-08-24
**Maintainer:** FreshRoute Data Eng  **Reviewer:** TBD Phase P1 gate
**BibTeX key:** `[@agmarknet2024]`
**License:** Government Open Data License – India (GODL-India) — attribution required
**Path:** `data/raw/agmarknet/YYYYMMDD.json` → `data/silver/agmarknet.parquet` → `data/gold/mandi_daily.parquet`

---

## 1. Motivation

Supports `spec §3.1:179` and `docs/IMPLEMENTATION_PLAN.md:P1 L1.1`. Provides daily surplus supply proxy: commodity, arrival volume (quintals), modal price. Informs `core/demand_forecaster.py` seasonality feature and `core/pareto_matcher.py` supply urgency. Gap it fills vs synthetic `src/data/mockData.js:42-61`: real mandi seasonality (wheat glut Apr-May, veg glut Sep-Nov) and price shocks.

## 2. Composition

- ~180 mandis Punjab (filtered to 6 priority: Ludhiana, Amritsar, Jalandhar, Khanna, Bathinda, Patiala) × ~30 commodities (Tier 3/5: tomato, palak, cauliflower, kinnow, wheat, dal, rice).
- Fields: `mandi_id, mandi_name, district_id, commodity, group (Produce/Grains), arrival_quintals, price_modal_inr_per_quintal, date`.
- Missingness: ~8% weekend under-reporting (Sunday closures), festival gaps (Diwali, Gurpurab). Price sometimes null when arrival 0.
- No PII. Spatial accuracy: mandi lat/lon from directory geocode (manual review, ±300m).

Example:

```json
{"mandi_id":"PB_LDH_APMC_01","mandi_name":"Ludhiana Grain Mundi","district_id":"ludhiana","commodity":"Tomato","arrival_quintals":42.5,"price_modal_inr_per_quintal":1800,"date":"2026-08-18"}
```

## 3. Collection Process

Scraper `freshroute-optimizer-model/data/ingestion/agmarknet.py` hits `https://agmarknet.gov.in/` Search API (POST with state=PB, date, commodity). Rate 1 req/2s, retry 3, respects robots. Window: 2023-01-01 → present (backfill), then daily cron 02:00 IST. Inclusion: Punjab state only, arrival>0 or price present. Exclusion: pre-2023 (schema change). Workforce: automated + manual spot check 5% rows vs portal UI.

## 4. Preprocessing / Cleaning

- Unit normalize: quintals → kg (×100), INR → float.
- District map: normalize mandi names to `punjab_districts.json:district_id`.
- Outlier rule: `arrival_quintals > Q99.9 per mandi-commodity` flagged, not dropped; GE `expect_arrival_between_0_5000`.
- Deduplicate by `(mandi_id, commodity, date)`.
- Provenance: raw JSON SHA256 in `data_manifest.json`; DVC `data/raw/agmarknet.dvc`.

## 5. Uses

Intended: time-series feature `mandi_7d_avg_arrival`, `price_volatility_14d` for forecaster; supply volume prior in matcher. Unintended: price prediction for trading (not validated), beyond Punjab without legal check. Users: ML eng, ops console `src/App.jsx:60`.

## 6. Distribution

Access: `data/gold/mandi_daily.parquet` (partitioned by `date`). Versioned via DVC + Zenodo at gate. Retention: full history.

## 7. Maintenance

Contact: data-eng@freshroute (placeholder). Update daily; schema change alert via ingestion log diff. Drift: PSI on `arrival_quintals` distribution; retrain trigger PSI>0.2.

## 8. Ethical Considerations & Limitations

Mandi data reflects *reported* arrivals, not actual farm surplus rescued — overestimates rescuable if wastage on-farm unreported. Price spikes may correlate with hunger but not causally. No community health data linked. Acknowledged gap → synthetic mock fallback when scraper fails.

## 9. Citation

```bibtex
@misc{agmarknet2024, author={{Government of India, Ministry of Agriculture \& Farmers Welfare}}, title={Agmarknet}, year={2024}, url={https://agmarknet.gov.in/}}
```
Cite DOI + `@agmarknet2024`.

