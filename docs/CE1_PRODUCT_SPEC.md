# FreshRoute — Food Bank Optimizer (India) — CE-1 Iteration-1 Product Spec

> Course: AI/ML 24CSE0316 | CE-1: Data Preparation & Analysis | 20 Marks (Viva 7 + PPT 7 + Idea 3 + Team 3)
> Assessment: 7–11 Sep 2026, Offline, 10 min/group. PPT in Chitkara template. All members present.
> Repo state: Iteration-1 = dataset refined, cleaned, transformed, analysed, ML-ready. No model training yet (CE-2).

---

## 1. Project Title & Overview

**Title: FreshRoute — Food Bank Optimizer Model (for India)**

FreshRoute finds the ideal way to save and redistribute surplus food to the right food bank / department / people in need, before it spoils.

Given a donation event (donor, food type, quantity, shelf-life, storage, distance, demand), the system predicts **redistribution_priority (Low / Medium / High)** and explains *why* (perishability, need-per-km, stock pressure, cold-chain). In CE-2 this becomes a classifier + routing rule: High → immediate dispatch to nearest high-need kitchen/shelter; Medium → schedule next-day pickup; Low → hold / process (e.g., dry-ration conversion).

India context: wedding halls, Gurudwara langars, hostel messes, restaurants, mandis and farms generate large, time-sensitive surplus. Cold-chain gaps + distance + festival spikes make rule-of-thumb redistribution wasteful. FreshRoute learns the pattern from data.

Reproducibility: `python scripts/generate_dataset.py` → raw; `python scripts/clean_dataset.py` → cleaned + encoded + 6 EDA figures. Colab notebook mirrors the same steps: `notebooks/CE1_data_preparation.ipynb`.

## 2. Problem Statement

India wastes ~68 Mt food/year while 190M+ people are undernourished (broad motivation; exact figure varies by source — we cite this as motivation, not as a dataset claim). Surplus is **perishable, scattered, and mismatched**: cooked meals spoil in 6–10h, donors don't know which food bank has capacity/need, and volunteers dispatch ad-hoc.

Real-world problem: *which surplus should move first, where, and by what transport, given shelf-life, storage, distance and live demand?*

How AI/ML addresses it: CE-1 frames this as a **supervised classification** problem on donation records. Features capture supply (quantity, food type), urgency (shelf-life, storage temp), logistics (distance, transport) and demand (beneficiaries, food-bank stock pressure). The model learns priority from historical patterns instead of fixed thresholds, then CE-2 adds demand forecasting + route ranking. CE-1 deliverable is the analysis-ready dataset — no leakage, no dirty labels.

## 3. Objectives (4)

1. Build an India-relevant food-donation dataset (≥600 records, 20 raw features) covering Punjab + Chandigarh UT + Delhi + Rajasthan, 7 donor types, 7 food types, 5 food banks.
2. Produce a **zero-missing, de-duplicated, consistent** dataset with documented cleaning, group-aware imputation, and correct dtypes — ready for `train_test_split`.
3. Encode categoricals correctly (One-Hot for nominals, Label for target) and engineer 5 interpretable features (`stock_pressure`, `surplus_ratio`, `need_per_km`, `is_perishable`, `cold_chain_ok`) with a frozen X/y contract.
4. Deliver EDA with 6 figures + per-graph observations that justify feature selection and expose bias (class imbalance, langar dominance, cold-chain gaps) for CE-2 mitigation.

## 4. Dataset Collection & Description

**Source:** Synthetic-but-grounded primary dataset generated for CE-1 (`scripts/generate_dataset.py`, seed=42). Simulates Jan–Mar 2026 donation logs as a food-bank network would record them. Chosen over Kaggle global food-waste sets because those lack Indian donor types (langar, wedding hall, hostel mess), km-scale distances, and shelf-life/storage columns needed for redistribution. CE-2 will append real pilot logs + FSSAI / state food-supply open data where available.

**Files:**
- Raw: `data/raw/freshroute_foodbank_raw.csv` — 636 rows × 20 cols (includes 18 exact duplicates + injected errors for cleaning demo)
- Cleaned: `data/processed/freshroute_foodbank_cleaned.csv` — **618 rows × 25 cols**, 0 missing
- ML-ready: `data/processed/freshroute_foodbank_encoded.csv` — 618 × 45 (One-Hot + label-encoded y)
- Report: `data/processed/cleaning_report.json`

**Important columns:**

| Column | Type (cleaned) | Meaning |
|---|---|---|
| donation_id | string (ID) | Unique key, dropped before training |
| donation_date + donation_month/dayofweek | date → int | Seasonality (winter Jan–Mar); engineered month, weekday |
| city / state | categorical | 8 cities, 4 states. Punjab-centric (Chitkara catchment) + Delhi/Jaipur for spread |
| donor_type | categorical | 7 types. Gurudwara Langar + Restaurant = largest surplus sources |
| food_type | categorical | 7 types. Drives shelf-life (Cooked 8h … Wheat Flour 120h) |
| quantity_donated_kg / quantity_available_kg | float | Supply. available ≤ donated after fix |
| shelf_life_hours | int | Urgency. Core perishability signal |
| storage_condition / storage_temp_C | cat / float | Cold / Room / No Storage + °C. Cold-chain check |
| distance_to_foodbank_km | float | Logistics cost |
| foodbank_id / capacity / current_stock | cat / int | Destination + `stock_pressure = stock/capacity` |
| beneficiaries_count | int | Demand proxy at destination |
| transport_available | Yes/No | Feasibility gate |
| redistribution_priority | **target y** | Low / Medium / High (rule-generated, then cleaned) |
| donor_contact_number / remarks | string | **Irrelevant — dropped** |

Target distribution (cleaned): Medium 456 (73.8%), High 122 (19.7%), Low 40 (6.5%) — imbalanced, noted for stratified split in CE-2.

## 5. Data Cleaning

Executed in `scripts/clean_dataset.py` (verified: 636 → 618 rows, 0 missing):

1. **Duplicates:** 18 exact duplicate rows removed (`drop_duplicates`). Verified via `cleaning_report.json`.
2. **Irrelevant columns dropped:** `donor_contact_number`, `remarks` — PII/noise, no predictive value.
3. **Inconsistent categoricals fixed:** strip + Title-case; `city` (`amritsar `/`AMRITSAR`→`Amritsar`), `food_type` (`rice `/`RICE`→`Rice`), `transport_available` (`y`/`YES `/`n`→`Yes`/`No`), `redistribution_priority` (`med`→`Medium`, `HIGH `→`High`). Invalid priority rows dropped (none remained after mapping).
4. **Incorrect numerics → NaN then imputed:** `quantity_donated_kg ≤ 0` (8 rows), `distance < 0` (10 rows), `shelf_life` outside 1–240h (0/500h sensor errors), `storage_temp` outside −5…50 °C (60 °C errors), `quantity_available > donated` capped to donated (12 rows).
5. **Types:** `donation_date` → datetime; engineered `donation_month`, `donation_dayofweek`; count columns cast to int.

## 6. Missing Values

| Column | Raw missing | Treatment | Why suitable |
|---|---|---|---|
| storage_temp_C (49, 7.9%) | sensor gaps | **Group-wise median by `storage_condition`** | Cold (~4 °C) vs Room (~25 °C) differ; global median would corrupt cold-chain signal |
| quantity_available_kg (29) | weigh-scale gaps | Global median | Skewed but robust; median preserves mass |
| shelf_life_hours (18) | label missing | Global median | Robust to 0/500 outliers (already NaN'd) |
| beneficiaries_count (13) | headcount delay | Global median + cast int | Robust, keeps counts integral |
| transport_available (30) | field blank | Mode (`Yes`) | Categorical; majority class, preserves feasibility rate |
| remarks (147) | — | Dropped with column | Irrelevant |

**Verification:** `df.isna().sum().sum() == 0` after treatment; asserted in script; `missing_after: 0` in report. Before/after counts stored in `cleaning_report.json`.

## 7. Categorical Data Encoding

- **One-Hot (`drop_first=True`, int dtype):** `city`, `state`, `donor_type`, `food_type`, `storage_condition`, `foodbank_id`, `transport_available` → 29 dummy columns. Correct because these are **nominal** (no order). `drop_first` avoids dummy trap.
- **Label Encoding (target only):** `redistribution_priority`: `High→0, Low→1, Medium→2` (alphabetical via `LabelEncoder`; mapping saved in report). Correct because most classifiers need numeric y; order is not used as ordinal — CE-2 will use stratified split + F1, or switch to ordinal if needed.
- **Kept numeric as-is:** quantities, shelf-life, temps, distances, engineered features. Scaling (StandardScaler) deferred to CE-2 pipeline to avoid leaking test stats now.
- Excluded from X: `donation_id`, `donation_date` (kept engineered month/dow instead).

## 8. Exploratory Data Analysis & Visualization

All in `reports/figures/` (generated, not hand-drawn). Each has a one-line observation for PPT/viva:

1. `01_priority_dist.png` — **Priority is imbalanced (M 456 / H 122 / L 40).** Observation: model will bias to Medium; CE-2 must use stratified split + class weights + F1-macro, not accuracy.
2. `02_foodtype_qty.png` — **Cooked Meals/Dairy show lower available-kg and tighter boxes; grains (Rice/Wheat) higher.** Observation: perishables come in smaller, urgent lots — quantity alone can't drive priority; needs shelf-life interaction.
3. `03_shelf_priority.png` — **High priority median shelf-life ≈ 8–12h vs Low ≈ 70h+.** Observation: perishability is the strongest single separator — validates `is_perishable (<24h)` feature.
4. `04_donor_counts.png` — **Gurudwara Langar + Restaurant dominate volume.** Observation: dataset reflects Punjab reality (langar surplus); but model must not overfit donor — keep donor as feature, audit per-donor recall in CE-2.
5. `05_distance_need.png` — **High-priority cluster: short distance + high beneficiaries (top-left).** Observation: `need_per_km = beneficiaries/(dist+1)` captures the dispatch logic better than either column alone.
6. `06_corr_heatmap.png` — **No |r| > 0.85 among numerics; `stock_pressure` ⊥ `need_per_km`.** Observation: no severe multicollinearity; engineered features add orthogonal signal, safe to keep all for CE-2 selection (mutual-info / RF importance).

## 9. Feature Selection / Engineering

**Engineered (5, all in cleaned CSV):**
- `stock_pressure = current_stock / capacity` — destination fullness; high pressure → reroute.
- `surplus_ratio = available / donated` — spoilage/loss proxy.
- `need_per_km = beneficiaries / (distance+1)` — demand density per logistics cost; core dispatch ranker.
- `is_perishable = 1 if shelf_life < 24h` — binary urgency flag.
- `cold_chain_ok = 1 if (Cold & temp ≤ 8 °C)` — food-safety gate.

**Selection rationale:** drop IDs/PII/dates-as-strings; keep all supply/urgency/logistics/demand signals for CE-2 model-based selection (RandomForest importance / chi²). Correlation check confirms no redundancy requiring an early drop.

**Frozen contract (CE-2 must import as-is):**
- `y = redistribution_priority` (encoded 0/1/2; mapping in `cleaning_report.json`)
- `X = all 44 columns in freshroute_foodbank_encoded.csv except y` (15 numeric/engineered + 29 dummies; full list in report `X_columns`)
- `train_test_split(..., stratify=y, random_state=42)` mandatory due to imbalance.

## 10. Pre-Processing Dataset Screenshot

> For PPT: screenshot the head of `freshroute_foodbank_cleaned.csv` (618 × 25, 0 NaN) + `cleaning_report.json` summary. Text equivalent (first 3 rows, truncated):

```
donation_id donation_date city     donor_type food_type    donated  avail shelf storage  temp  dist FB   cap stock bene transport priority m dow stock_p surplus need/km perish cold_ok
DON-0050    2026-03-02    Jaipur   Restaurant Wheat Flour  116.3    103.3 114   No Storage 23.3  6.6 FB-03 1500 1351  276  Yes       Medium   3 0   0.901   0.888   36.32  0      0
DON-0583    2026-02-02    Amritsar Restaurant Fruits       77.4     52.2  59    Cold       ~4    20.0 FB-03 500  446   98   No        Low      2 0   0.892   0.674   4.67   0      0
DON-0083    2026-01-12    Jaipur   Restaurant Cooked Meals  99.5     86.3  4     Cold       ~4    10.5 FB-02 800  136   183  Yes       High     1 0   0.170   0.867   15.91  1      0
```

Verify locally: `python -c "import pandas as pd; print(pd.read_csv('data/processed/freshroute_foodbank_cleaned.csv').shape, pd.read_csv('data/processed/freshroute_foodbank_cleaned.csv').isna().sum().sum())"` → `(618, 25) 0`.

## 11. Conclusion (CE-1)

CE-1 is complete: raw 636×20 (messy, realistic) → cleaned 618×25 (0 missing, consistent) → encoded 618×45 (ML-ready) with a frozen X/y contract, 6 EDA figures with observations, and reproducible scripts + Colab notebook. Key finding: priority is driven by **perishability × need-per-km**, not quantity alone; imbalance (73% Medium) and langar-dominance are the two biases CE-2 must handle. Dataset is ready for model development.

## 12. Project Planning & Future Scope

**CE-2 (model):** stratified 80/20 split → baselines (Logistic Regression, Random Forest, XGBoost) on F1-macro; class weights/SMOTE; confusion-matrix + per-donor/per-city audit; SHAP for "why High?". **Routing layer:** priority + `need_per_km` + `stock_pressure` → ranked destination list (food bank / dept / shelter). **App:** pickup form + dashboard reusing these exact columns. **Risks:** synthetic-data optimism → mitigate with pilot logs; winter-only dates → collect summer data; no real-time traffic/cold-chain IoT yet → add as features later.
