# FreshRoute — Food Bank Distribution Optimizer (India)
## CE-1 Iteration-1 Product Spec Sheet (built on REAL data)

### 1. Title & overview
FreshRoute predicts a **redistribution priority (Low / Medium / High)** for each
food-bank distribution record so volunteers move the most urgent supply first.
Primary data: 1020 real monthly distribution records from the Blue Ridge Area
Food Bank (Virginia Open Data Portal, Jan 2019–Jun 2021). India framing anchored
on India's real UNEP Food Waste Index row (50 kg/capita/yr household,
68.76M tonnes/yr). Reproduce: `python scripts/clean_dataset.py`.

### 2. Problem statement
Edible surplus spoils while nearby shelters face shortages because no one ranks
*what should move first*. Donors don't see food-bank need; food banks don't see
incoming surplus in time. Fixed rules ("first come, first served") ignore the
perishability × need tradeoff. India wastes ~68.76M tonnes/yr at household level
alone (UNEP 2021) — routing intelligence, not just more food, is the gap.

### 3. Objectives
1. Curate a **real, cited dataset** (1020 records) — no invented donation logs.
2. Deliver **zero-missing, encoded, ML-ready data** with a frozen X/y contract.
3. Derive a **disclosed triage label** (rule + thresholds saved, not hidden).
4. Produce **6 EDA figures with observations** that justify features and expose bias.
5. Anchor an **India pilot design** (donor/hub reference tables) on real UNEP volumes.

### 4. Dataset collection & description
| File | Shape | Source |
|---|---|---|
| `data/raw/brafb_virginia_foodbank.csv` | 1020 × 8 | Virginia Open Data Portal (BRAFB, real ops records) |
| `data/raw/food_waste_by_country.csv` | 214 × 12 | UNEP Food Waste Index 2021 (via mirror) |
| `data/processed/freshroute_foodbank_cleaned.csv` | 1020 × 16 | this pipeline |
| `data/processed/freshroute_foodbank_encoded.csv` | 1020 × 58 | this pipeline |
| `data/reference/india_waste_anchor.csv` | 1 × 9 | India's UNEP row (real) |
| `data/reference/india_network_reference.csv` | 6 × 3 | donor/hub design, sources labeled |
Raw columns: Year, Month, Locality, Households/Individuals Served,
Pounds Distributed, Children Served + Child-nutrition Pounds.
Full provenance: `data/SOURCES.md`.

### 5. Data cleaning
- Duplicates: 0 exact dupes found (checked, not assumed).
- Text: Month/Locality stripped + uppercased; Month cast to ordered JAN..DEC.
- Impossible values: 1 negative pound figure → NaN → median (logged in report).
- Float artifacts from the portal export (e.g. 177361.59854, 386.99 people)
  → counts rounded to int, pounds to 1 decimal.
- Program-only rows (30, e.g. PITTSYLVANIA: no household service, child-program
  activity only) → Households/Individuals NaN treated as true 0 + flag column,
  not silently dropped.

### 6. Handling missing values
| Column | Missing | Treatment |
|---|---|---|
| Households / Individuals Served | 30 (2.9%) | true 0 + `is_program_only_record` flag |
| Children Served | 591 (58%) | median (87) + `child_data_missing` flag (missingness kept as signal) |
| Child-nutrition Pounds | leftover after negative fix | median |
| **After** | **0 total** | verified by assert in script |

### 7. Categorical encoding
- One-Hot (`drop_first=True`, int): Month (11 cols), Locality (30+ cols).
- Label target only: High→0, Low→1, Medium→2 (saved in `cleaning_report.json`).
- Dropped from X: nothing PII-like present. Scaling deferred to CE-2 pipeline.

### 8. EDA & visualization (`reports/figures/`)
1. `01_priority_dist.png` — Medium 425 / Low 330 / High 265: usable, mildly imbalanced → stratify in CE-2.
2. `02_pounds_hist.png` — right-skewed volumes; a few mega-months dominate.
3. `03_monthly_trend.png` — visible 2020 (covid-era) surge → kept as `is_covid_era` feature.
4. `04_top_localities.png` — LYNCHBURG/LOUDOUN dominate → locality dummies + per-capita features prevent "big place always wins".
5. `05_need_vs_supply.png` — priority separates cleanly on need × supply-per-person, validating the rule.
6. `06_corr_heatmap.png` — engineered per-capita cols correlate with parents (expected); no hidden |r|>0.85 surprises among base numerics.

### 9. Features
Engineered: `pounds_per_household`, `pounds_per_individual`, `child_pound_share`,
`is_covid_era`, `month_num`, `is_program_only_record`, `child_data_missing`.
X = 57 cols (9 numeric/flags + 48 dummies) | y = `redistribution_priority`.
Contract: `train_test_split(stratify=y, random_state=42)` mandatory in CE-2.

### 10. Pre-processed screenshot
`freshroute_foodbank_cleaned.csv` head (8 rows) — reproduce table any time:
`python -c "import pandas as pd; print(pd.read_csv('data/processed/freshroute_foodbank_cleaned.csv').head(8).to_string())"`.
Cleaned 1020×16, missing=0; encoded 1020×58; y = Medium 425 / Low 330 / High 265.

### 11. Conclusion
CE-1 done on fully real, cited data: messy 1020×8 → clean 1020×16 →
encoded 1020×58, frozen X/y, 6 EDA figures, disclosed label rule, India anchor.
Finding: distribution urgency separates on need × supply-per-person, not raw volume.
Biases logged: US geography, covid-era surge, program-only rows flagged.

### 12. Planning & future scope
CE-2: Logistic/RandomForest/XGBoost on F1-macro, stratified split, per-locality
audit. Then India pilot layer: donor → priority → ranked hub (Rajpura/Patiala/
Chandigarh), volunteer dispatch, FSSAI-aligned logging. Field pilot needed before
any real-world impact claim.
