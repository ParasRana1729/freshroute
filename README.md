# FreshRoute — Food Bank Distribution Optimizer (India)

Predicts **redistribution priority (Low / Medium / High)** for mandi surplus
records so the most urgent glut moves first. India-native pilot on real
APMC arrivals + prices.

## Real data only (India)
- `data/raw/apmc_arrivals_prices.csv` — 394k real APMC records (DMI via
  data.gov.in / CEDA mirror, 28 states, 304 commodities). Provenance in
  `data/SOURCES.md`.
- The priority label is **derived by a published glut-proxy rule**
  (`S = arrival_z * (-price_z)`, thresholds in `cleaning_report.json`);
  disclosed, not presented as observed.

## Reproduce (CE-1)
```bash
pip install -r requirements.txt
python scripts/clean_dataset.py
```
Outputs: `data/processed/freshroute_foodbank_cleaned.csv` (383753×22, 0 missing),
`freshroute_foodbank_encoded.csv` (383753×62), `cleaning_report.json`,
6 figures in `reports/figures/`. Spec: `docs/CE1_PRODUCT_SPEC.md`.
Notebook mirror: `notebooks/CE1_data_preparation.ipynb`.
