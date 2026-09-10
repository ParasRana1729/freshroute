# FreshRoute — Food Bank Distribution Optimizer (India)
## CE-1 Iteration-1 Product Spec Sheet (built on REAL India data)

### 1. Title & overview
FreshRoute predicts a **redistribution priority (Low / Medium / High)** for each
APMC mandi-commodity-day so volunteers move the most urgent glut first.
Primary data: 383,753 real APMC arrivals + price records (DMI, 28 states,
2,705 markets, 304 commodities, 2025-10-27–2025-11-19). India-native, no US proxy.
Reproduce: `python scripts/clean_dataset.py`.

### 2. Problem statement
Edible surplus spoils while nearby shelters face shortages because no one ranks
*what should move first*. APMC mandis see daily volume gluts that crash wholesale
prices — an observable glut signal. Fixed rules ("first come, first served")
ignore the arrival-surge × price-drop tradeoff.

### 3. Objectives
1. Curate a **real India-native cited dataset** (383k records) — no Virginia proxy,
   no invented donation logs.
2. Deliver **zero-missing, encoded, ML-ready data** with a frozen X/y contract.
3. Derive a **disclosed triage label** (Surplus Intensity S + quantile thresholds
   saved, not hidden).
4. Produce **6 EDA figures with observations** that justify features and expose bias.
5. Enable a **Maharashtra/India pilot design** (mandi → priority → ranked hub).

### 4. Dataset collection & description
| File | Shape | Source |
|---|---|---|
| `data/raw/apmc_arrivals_prices.csv` | 394258 × 22 raw | DMI via data.gov.in / CEDA mirror (real mandi ops) |
| `data/processed/freshroute_foodbank_cleaned.csv` | 383753 × 22 | this pipeline |
| `data/processed/freshroute_foodbank_encoded.csv` | 383753 × 62 | this pipeline |
Raw columns: date, state/district/market, commodity/variety/grade,
lat/lon, arrival_quantity, min/max/modal_price, price_unit.
Full provenance: `data/SOURCES.md`.

### 5. Data cleaning
- Duplicates: 0 exact dupes found (checked, not assumed).
- Text: state/district/market/commodity stripped + uppercased; date to datetime.
- Units: Rs./Quintal → Rs./kg (`/100`); 10,503 Bundle/Unit rows dropped
  (not convertible, logged).
- Impossible values: negatives → NaN → dropped/median (logged).
- Geo: 140,784 rows missing lat/lon → state median + `geo_missing` flag.
- Variety/grade NaN → UNKNOWN.
- Outliers: per-commodity IQR winsorize price (k=3), arrivals (k=5).

### 6. Handling missing values
| Column | Missing | Treatment |
|---|---|---|
| modal_price/date/market | 4 total | drop |
| lat/lon | 140,784 (37%) | state median + `geo_missing` flag |
| variety/grade | 1 each | UNKNOWN |
| **After** | **0 total** | verified by assert in script |

### 7. Categorical encoding
- One-Hot (`drop_first=True`, int): state_name (27 cols), commodity_top top-20 + OTHER (20 cols).
- Market/district (2705/528 cards) kept in cleaned for ranking, excluded from X.
- Label target only: High→0, Low→1, Medium→2 (saved in `cleaning_report.json`).
- X = 61 cols (14 numeric/flags + 47 dummies) | y = `redistribution_priority`.
- Contract: `train_test_split(stratify=y, random_state=42)` mandatory in CE-2.

### 8. EDA & visualization (`reports/figures/`)
1. `01_priority_dist.png` — Medium 158k / Low 129k / High 95k: usable, mildly imbalanced → stratify in CE-2.
2. `02_pounds_hist.png` — price_per_kg right-skewed; p99 clip for view.
3. `03_monthly_trend.png` — 24-day window only; no seasonality claim — needs WFP long baseline.
4. `04_top_localities.png` — top commodities Onion/Wheat/Potato/Tomato; Tamil Nadu 35% of rows → state dummies + per-kg features prevent "big state always wins".
5. `05_need_vs_supply.png` — arrival_z vs price_z separates by S, validating the glut rule.
6. `06_corr_heatmap.png` — S correlates with arrival_z / -price_z by construction; no hidden |r|>0.85 among base numerics.
### 8b. Supplementary EDA (bias checks & operations, frozen 01–06 unchanged)
7. `07_state_high_rate.png` — High-rate by state: Tamil Nadu 0.232, below 0.25 average despite ~34% of rows → volume dominance ≠ label dominance.
8. `08_perishable_vs_staple.png` — perishables 0.270 vs staples 0.257: small gap, consistent with spoilage framing but not confirmation in 24 days.
9. `09_top_markets_high.png` — top markets by High count (Tiruvannamalai 376, Gonda 362, Vellore 362); Uzhavar Sandhai density caveat — pair with tonnage before dispatch.

### 9. Features
Engineered: `price_per_kg`, `arrival_tonnes`, `baseline_mean/std`, `arr_mean/std`,
`price_z`, `arrival_z`, `surplus_S`, `log_arrival`, `price_spread`,
`month_num`, `day_num`, `is_weekend`, `geo_missing`.
X = 61 cols | y = `redistribution_priority`.
Contract: `train_test_split(stratify=y, random_state=42)` mandatory in CE-2.

### 10. Pre-processed screenshot
`freshroute_foodbank_cleaned.csv` head (3 rows) — reproduce any time:
`python -c "import pandas as pd; print(pd.read_csv('data/processed/freshroute_foodbank_cleaned.csv').head(3).to_string())"`.
Cleaned 383753×22, missing=0; encoded 383753×62; y = Medium 158026 / Low 129788 / High 95939.

### 11. Conclusion
CE-1 done on fully real India-native data: messy 394k×22 → clean 383k×22 →
encoded 383k×62, frozen X/y, 6 EDA figures, disclosed S-rule, no Virginia proxy.
Finding: redistribution urgency separates on arrival-surge × price-drop (S),
not raw volume.
Biases logged: Tamil Nadu dominance, 24-day window (no seasonality),
37% geo-imputed, perishables over-represented.

### 12. Planning & future scope
CE-2: Logistic/RandomForest/XGBoost on F1-macro, stratified split, per-state
audit. Then demand layer: Maharashtra PDS AAY/PHH → vulnerability `V_d`,
WFP long prices for seasonality, mandi → hub Haversine ranking, volunteer
dispatch, FSSAI-aligned logging. Field pilot needed before any real-world
impact claim.
