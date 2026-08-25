# Datasheet for Dataset: Census of India & Demographic Projections (D5)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D5 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** Punjab District Demographic Baselines & 2026 Projections (`data/punjab_districts.json:population`)
**Version:** `v1.0.0-P1`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Demographic Analysis Working Group
**BibTeX keys:** `[@census2011]`
**License:** Government Open Data License (GODL) – India

---

## 1. Motivation

- **Purpose:** Supplies baseline human population figures, population density ($/\text{km}^2$), and urbanization ratios across all 23 administrative districts of Punjab (including post-2021 created Malerkotla district).
- **Pipeline Stage:** Inputs into Stage 2 Spatial-Temporal Demand Forecaster (`core/demand_forecaster.py:168`) and Hunger Vulnerability Index (HVI) calculation.

## 2. Composition

- **Records:** 23 records corresponding to Punjab districts.
- **Fields:**
  - `district_id` (string): Standard slug (e.g., `ludhiana`, `amritsar`, `bathinda`).
  - `district_name` (string): Official name.
  - `population` (integer): Projected 2026 population (based on ORGI growth rate models).
  - `area_sq_km` (float): District geographical area in square kilometers.
  - `population_density` (float): Calculated persons per $\text{km}^2$.
  - `urban_pct` (float): Percentage of urbanized population.

## 3. Collection Process

- **Source:** Office of the Registrar General & Census Commissioner of India (ORGI), Ministry of Home Affairs, Government of India (`https://censusindia.gov.in/`).
- **Interpolation:** 2011 decadal base projected to 2026 using compounding cohort growth methodologies published by the National Commission on Population.

## 4. Preprocessing & Validation

- Ingested and consolidated into `data/punjab_districts.json`.
- Tested through Great Expectations suite in `data/validation/ge_suites.py:validate_forecaster_history`.

## 5. Citation

```bibtex
@misc{census2011,
  author       = {{Office of the Registrar General \& Census Commissioner, India}},
  title        = {Census of India 2011: Primary Census Abstract for Punjab},
  year         = {2011},
  howpublished = {\url{https://censusindia.gov.in/}}
}
```
