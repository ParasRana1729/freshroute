# FreshRoute — Food Bank Distribution Optimizer (India)

Forecasts **next-day redistribution priority (Low / Medium / High)** for APMC
mandi gluts so the most urgent surplus moves first. India-native pilot on real
APMC arrivals + prices; XGBoost forecaster + move-first dispatch demo.

## Real data only (India)
- `data/raw/apmc_arrivals_prices.csv` — 394k real APMC records (DMI via
  data.gov.in / CEDA mirror, 28 states, 304 commodities, git-ignored 81 MB;
  re-download steps in `data/SOURCES.md`).
- The priority label is **derived by a published glut-proxy rule**
  (`S = arrival_z * (-price_z)`, thresholds in `cleaning_report.json`);
  disclosed, not presented as observed.

## Project status
- **CE-1 (done):** 394k×22 raw → 383,753×22 clean (0 missing) → 383,753×62
  encoded; 6 frozen EDA figures + 3 bias/operations supplements (Figs 7–9);
  full report: `reports/CE1_Report_FreshRoute.pdf`; spec: `docs/CE1_PRODUCT_SPEC.md`.
- **CE-2 (done):** next-day forecast X(t)→y(t+1), 352k pairs, time split
  (train ≤ Nov 13, test last 6 days). Test F1-macro: XGBoost **0.517**,
  RandomForest 0.516, LogReg 0.304, majority baseline 0.181.
  Winner drives a 50-row `dispatch_list_demo.csv` (predicted-High ranked by
  P(High) × tonnage). Metrics: `data/processed/model_metrics.json`;
  matrices/importance: Figs 10–11.

## Reproduce
```bash
pip install -r requirements.txt
python scripts/clean_dataset.py   # CE-1: cleaned/encoded/report/Figs 1-6
python scripts/train_model.py     # CE-2: metrics, dispatch demo, Figs 10-11
```
Notebook mirror: `notebooks/CE1_data_preparation.ipynb`.

## Future implementations
1. **Demand layer:** Maharashtra PDS AAY/PHH → vulnerability `V_d`, so ranking
   weighs need, not just glut size.
2. **Longer history:** WFP HDX prices (1994–present) for seasonality; retrain
   with richer temporal features.
3. **True optimizer:** hub capacities + Haversine mandi→hub distances;
   constrained dispatch instead of ranked list.
4. **Model upgrades:** probability calibration, per-state audits, drift
   monitoring on new mandi feeds.
5. **Field readiness:** volunteer dispatch flow, FSSAI-aligned logging, pilot
   with a partner food bank before any impact claim.
