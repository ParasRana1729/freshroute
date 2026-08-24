# Datasheet for Dataset: Punjab Districts HVI Base Table (D7/D6 overlap)

**Dataset:** `freshroute-optimizer-model/data/punjab_districts.json` — 23 districts with Hunger Vulnerability Index
**Version:** v1.0.0-P1  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** 2026-08-24
**BibTeX keys:** `[@census2011; @niti2023mpi; @nfhs5; @wfp2024hungermap]`
**License:** Internal CC-BY-4.0 upon release (derived, attribution to sources required)
**Path:** `data/punjab_districts.json` → `data/gold/punjab_districts.parquet`

## 1. Motivation

Supports `spec §4.1` 23-district hunger fabric for `core/demand_forecaster.py` (`Deficit(j)` weighted `w2=0.30`) and ops console `src/App.jsx:67` + `src/data/mockData.js:403-449` gap bars. Synthetic prior `mockData.js` provided 5-district sample; this extends to 23 post-2022 admin units.

## 2. Composition

- 23 records (see JSON). Fields: `district_id, district_name, zone, coordinates [lat, lon], hunger_vulnerability_index 0-100, weekly_forecast_demand_lbs, scheduled_rescue_lbs, gap_lbs, primary_need, trend, population_2026_est, mpi_rank_state`.
- Missingness: `population_2026_est` interpolated (Census 2011× state growth 1.08); `mpi_rank_state` ordinal within state.
- Coordinates: district centroid (±5km) for proximity scoring `core/pareto_matcher.py:339`.

## 3. Collection

Census 2011 tables (ORGI) + projection factor from NITI; MPI headcount from `niti2023mpi`; NFHS-5 stunting/wasting for nutrition flags; WFP HungerMap cross-check. Manual curation 2026-08-24, reviewed against mockData subset (Ludhiana 95, Amritsar 92 etc. consistent).

## 4. Preprocessing

- HVI formula (P3 L3.3 draft): `HVI = 0.4*norm(MPI) + 0.3*norm(informal_settlement_share) + 0.2*(100 - cold_storage_proxy) + 0.1*nutrition_flag`, scaled 0-100.
- Weekly demand `weekly_forecast_demand_lbs` initially = `mockData` plus scaling by population; `scheduled_rescue_lbs` from mock; `gap = scheduled - forecast`.
- Outlier: Faridkot small district; verified `gap` small magnitude justified.

## 5. Uses

Intended: district deficit ranking; `DistrictDemand` feature in forecaster; matcher `Deficit(j) = urgency_score`. Unintended: inter-state comparison (not normalized beyond Punjab), precise poverty measurement (use MPI directly).

## 6. Distribution

JSON committed; parquet gold after P1 validation. DOI at gate. Update quarterly with NITI release.

## 7. Maintenance & Limitations

Census projection uncertainty ±8%; Malerkotla 2021 district thin history; HVI not yet regressed against actual consumption logs (pilot will calibrate — see `docs/IMPLEMENTATION_PLAN.md:P7`).
