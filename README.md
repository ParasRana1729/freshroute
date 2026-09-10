# FreshRoute — Food Bank Distribution Optimizer (India)

Predicts **redistribution priority (Low / Medium / High)** for food-bank
distribution records so the most urgent supply moves first. India pilot design
anchored on real UNEP waste volumes.

## Real data only
- `data/raw/brafb_virginia_foodbank.csv` — 1020 real food-bank distribution
  records (Virginia Open Data Portal). Provenance in `data/SOURCES.md`.
- `data/raw/food_waste_by_country.csv` — real UNEP Food Waste Index (India row
  saved to `data/reference/india_waste_anchor.csv`).
- The priority label is **derived by a published rule** (see spec §7/report);
  disclosed, not presented as observed.

## Reproduce (CE-1)
```bash
pip install -r requirements.txt
python scripts/clean_dataset.py
```
Outputs: `data/processed/freshroute_foodbank_cleaned.csv` (1020×16, 0 missing),
`freshroute_foodbank_encoded.csv` (1020×58), `cleaning_report.json`,
6 figures in `reports/figures/`. Spec: `docs/CE1_PRODUCT_SPEC.md`.
Notebook mirror: `notebooks/CE1_data_preparation.ipynb`.
