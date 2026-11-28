# FreshRoute — Food Bank Distribution Optimizer (India)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ParasRana1729/freshroute/blob/main/notebooks/FreshRoute_Colab.ipynb)

**In one line:** every day, Indian farm markets (*mandis*) experience sudden supply gluts that can spoil before redistribution. FreshRoute uses strictly historical (`<= t`) APMC arrival and price signals to forecast next-day (`t+1`) **glut-onset transitions** and **arrival surges**, producing a ranked move-first dispatch list for food banks.

> Honest note: the `surplus_cs` label is a *disclosed cross-sectional proxy rule* (`p_arr >= 0.70` and `p_price <= 0.30` within active commodity-day slices `n_comm_day >= 10`), not measured food waste. Data provenance and gaps are documented in `data/SOURCES.md`.

## Pipeline Architecture (Plan v3.1, Leak-Free)

1. **Deterministic Row Cleaning (`scripts/clean_dataset.py`):**
   - Filters `394,258` raw APMC records (`2025-10-27`–`2025-11-19`) to Quintal-consistent rows (`10,503` non-Quintal rows dropped).
   - Applies 5-key same-day deduplication on `(state_name, market_center_name, commodity_name, variety, grade, date)`, resolving `61` duplicates (`383,753` → `383,692` rows across `46,070` unique entities, `0` missing values, `21.48 MB` RAM).
   - Zero cross-split statistics (`price_z`, `arrival_z`, `surplus_S`, and global IQR winsorization removed from `X_columns` and `data/processed/cleaning_report.json`).
2. **Train-Only Features & Chronological Splitting (`scripts/build_features.py`, `configs/experiment_config.yaml`):**
   - Computes `34` strictly `<= t` features (`FEATURE_COLS`): Train-only per-commodity IQR clipping (`price_iqr_k=3.0`, `arrival_iqr_k=5.0`), backward lags (`t-1..t-3`), day-`t` cross-sectional percentiles (`n_comm_day(t) >= 10`), same-day spatial spillover ratios, cyclical weekday encodings, and Train-fitted 4-level state-qualified shrinkage priors.
   - Constructs exact `(t, t+1)` pairs (`273,726` total; `269,632` active with `n_comm_day >= 10` on both `t` and `t+1`) under a strict **`10d / 7d / 4d` chronological `target_date` split** (`Train = 136,105`, `Val = 76,184` with `7/7` weekdays, `Test = 36,841`, `20,502` boundary-purged pairs), enforcing `train["target_date"].max() < val["date"].min()` and `val["target_date"].max() < test["date"].min()`.
3. **Dual-Track Modeling (`scripts/train_model.py`):**
   - **Track 1A — Glut Onset (`0 -> 1`):** Predicts `y_onset = surplus_cs(t+1)` on currently normal markets (`surplus_cs(t) == 0`).
   - **Track 1B — Arrival Residuals & Surge Ranking:** Models `delta_log_arr = log(1 + arrival_{t+1}) - log(1 + arrival_t)` with `XGBRegressor (reg:absoluteerror)` (retaining `Naive Persistence` for 1-day price: Test log-price `RMSE = 0.1038`, `MAE = 0.0522`, `R² = 0.9704`).

## Verified v3.1 Benchmarks (`10d_7d_4d` Test Split)

All metrics below are directly recorded in `data/processed/model_metrics.json`:

### Track 1A — Glut Onset (`Test n = 32,363`, `883` positives, base rate `0.0273`)

| Model | `PR-AUC` (Lift vs. Base Rate) | `ROC-AUC` | `F1` (Val-tuned) | `Recall@20` | `Recall@50` | `Recall@100` |
|---|---|---|---|---|---|---|
| `Naive Persistence` | `0.0273` (`1.00×`) | `0.5000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` |
| `LogisticRegression` (OHE) | `0.1666` (`6.11×`) | `0.8741` | `0.2677` | `0.0045` | `0.0113` | `0.0272` |
| **`XGBClassifier` (`scale_pos_weight=1.0`)** | **`0.2276` (`8.34×`)** | **`0.9082`** | **`0.3019`** | **`0.0147`** | **`0.0351`** | **`0.0578`** |

### Track 1B — Arrival Residual `delta_log_arr` & Surge Ranking (`Test n = 36,841`, `26.98%` exact `0.0`, `393` slices)

| Model | Role | `RMSE` | `MAE` | `Residual R²` | `Reconstructed R²` | Surge `NDCG@5` | Surge `NDCG@10` |
|---|---|---|---|---|---|---|---|
| `Naive Persistence` (`Δ = 0`) | Baseline | `0.4113` | `0.1607` | `-0.0001` | `0.9235` | — | — |
| `Mean-Reversion` (`-diff_prior_arr`) | Ranking baseline | `0.4666` | `0.1811` | `-0.2868` | `0.9015` | `0.5082` | `0.5442` |
| **`XGBRegressor (reg:absoluteerror)`** | **Default** | **`0.3556`** | **`0.1441`** | **`0.2527`** | **`0.9428`** | **`0.5566`** | **`0.5876`** |
| `XGBRegressor (reg:squarederror)` | Secondary | `0.3533` | `0.1531` | `0.2622` | `0.9435` | `0.5048` | `0.5395` |
| `XGBRegressor (reg:pseudohubererror)` | Secondary | `0.3512` | `0.1479` | `0.2710` | `0.9442` | `0.5232` | `0.5586` |

### Track 1A F1 experiment (80% target)

The candidate reached **41.97% held-out F1** on the original 10d/7d/4d split.
The existing XGBoost trainer reached **31.15%** when rerun on the same data and
software versions, a gain of **10.81 percentage points**. The candidate found
427 of the 883 glut onsets among 32,363 eligible test rows, with 37.07%
precision and 48.36% recall. The 80% target remains unmet.

The model uses recent market observations, cumulative peer statistics through
day `t`, and distances to past commodity-level arrival and price cutoffs.
Model selection, tree count, and the alert threshold use validation F1.
The [experiment report](data/processed/onset_f1_metrics.json) includes the
trial results and a breakdown for the four held-out dates.

```bash
python scripts/fetch_benchmark_data.py
python scripts/clean_dataset.py
python scripts/train_onset_f1.py
```

The [extended archive benchmark](docs/ONSET_ARCHIVE_BENCHMARK.md) tests the same
onset definition on a separate month-long holdout after training on several
months of reports.
The [May follow-up](docs/ONSET_COHORT_BENCHMARK.md) compares projected market
reporting cohorts with a baseline on a common held-out population.
The [local-context experiment](docs/ONSET_LOCAL_CONTEXT_EXPERIMENT.md) records a
peer-selection issue and the corrected feature builder.
The [historical analog experiment](docs/ONSET_ANALOG_EXPERIMENT.md) compares
similar past transitions on April validation.

## Anti-Leakage & Pipeline Verification (`tests/`)

Running `python -m pytest -v tests/test_pipeline_integrity.py tests/test_phase2_pipelines.py tests/test_audit_and_dispatch.py` passes **15 automated tests**:

### Core Anti-Leakage Suite (`tests/test_pipeline_integrity.py` — 5 tests)
- `test_1_target_date_non_overlap` — Enforces `train["target_date"].max() < val["date"].min()`, `val["target_date"].max() < test["date"].min()`, and `7/7` weekday coverage on `Val`.
- `test_2_feature_allowlist_and_formula_guard` — Verifies zero `t+1` fields or legacy `price_z`/`arrival_z`/`surplus_S` columns in `FEATURE_COLS`, `cleaning_report.json`, and `model_metrics.json`.
- `test_3_zero_future_filtering_in_features` — AST/signature check plus `t+1` drop/perturbation invariance on `build_features()`.
- `test_4_shuffled_target_collapse` — Permuted-target `XGBClassifier` collapses to Test base rate (`±0.01` `PR-AUC`) and `ROC-AUC ∈ [0.45, 0.55]`; permuted-target `XGBRegressor` (`reg:absoluteerror` and `reg:squarederror`) collapses to `R² <= 0.01`, `MAE >= persistence_MAE`, and `RMSE >= persistence_RMSE`.
- `test_5_mandatory_baseline_reporting` — Verifies `model_metrics.json` contains non-null metrics for `Naive Persistence`, `LogisticRegression`, `Mean-Reversion (-diff_prior_arr)`, `XGBClassifier`, and `XGBRegressor (reg:absoluteerror)`.

## Phase 2 (Scoped Multi-Year Weather & APMC), Hardening & Constrained Dispatch

- **District Weather & Scoped APMC (`scripts/fetch_weather.py`, `scripts/fetch_apmc_history.py`, `scripts/train_phase2_walkforward.py`):**
  - Covers `226` districts across the top `6` agricultural states (`213` non-imputed raw mandi medians + `13` verified Census/LGD centroids; zero state-median imputed coordinates) and `10` high-volume perishables.
  - Fetched and disk-cached `730` days (`2023-11-21`–`2025-11-19`, `164,980` rows) via Open-Meteo; on the `10d_7d_4d` scoped 24-day ablation (`data/processed/phase2_walkforward_metrics.json`, `50` features vs. `34` base), adding weather + causal seasonal/calendar features lifted Track 1A `XGBClassifier` Test `PR-AUC` from `0.2438` (`8.58×`) to **`0.2638` (`9.29×`)** and `ROC-AUC` from `0.9346` to **`0.9445`**, while Track 1B `reg:absoluteerror` achieved `RMSE = 0.2313` (vs. `0.2618`), `MAE = 0.0893` (vs. `0.0989`), and Surge `NDCG@10 = 0.5845` (vs. `0.5472`).
- **Calibration, Per-State Parity & Drift Monitoring (`scripts/audit_model.py`, `scripts/monitor_drift.py`):**
  - Val-only Isotonic calibration reduced Track 1A Test `ECE` from `0.008063` to **`0.003119`** (`Brier` `0.024224` → **`0.023501`**); **`16 / 16`** audited states beat `Naive Persistence` on both Track 1B `RMSE` and `MAE` (`data/processed/model_audit_report.json`).
  - Feature drift monitoring (`data/processed/drift_report.json`) confirms `30 / 34` features remain stable (`PSI < 0.10`) from Train to Test (the 4 shifted features are `dow_cos`/`dow_sin` from the 4-day Sat–Tue Test window plus `past_report_count`/`n_comm_day`) with steady onset base rate (`0.0282` Train → `0.0273` Test).
- **Demand Layer `V_d` & LP Hub-Routing Optimizer (`scripts/optimize_dispatch.py`):**
  - Combines NFSA/PDS demand weights `V_d` (`--pds-csv` or disclosed regional reference hubs), perishability weights `w_perish`, and Haversine distance/capacity constraints via HiGHS LP (`scipy.optimize.linprog`), producing `44` optimal routes (`533.32` tonnes at `127.01 km` weighted average haul, `+5.534` utility lift over greedy nearest routing in `data/processed/optimized_dispatch_plan.csv`).

## Try It Yourself

```bash
pip install -r requirements.txt
python scripts/clean_dataset.py
python scripts/build_features.py
python scripts/train_model.py
python scripts/audit_model.py
python scripts/monitor_drift.py
python scripts/optimize_dispatch.py
python -m pytest -v tests/test_pipeline_integrity.py tests/test_phase2_pipelines.py tests/test_audit_and_dispatch.py
```

- Raw data (`data/raw/apmc_arrivals_prices.csv`) is git-ignored; download steps are in `data/SOURCES.md`.
- Phase 2 weather/APMC fetchers: `python scripts/fetch_weather.py` (no key needed) and `python scripts/fetch_apmc_history.py --source ceda` (requires `CEDA_API_KEY`) or `--source agmarknet --import-dir <dir>`, followed by `python scripts/train_phase2_walkforward.py`.
- Key outputs: `data/processed/freshroute_foodbank_cleaned.csv`, `data/processed/cleaning_report.json`, `data/processed/model_metrics.json`, `data/processed/model_audit_report.json`, `data/processed/drift_report.json`, `data/processed/dispatch_list_demo.csv`, and `data/processed/optimized_dispatch_plan.csv`.
- Engineering roadmap & specs: `IMPROVEMENT_PLAN_v3_1.md` and `docs/CE1_PRODUCT_SPEC.md`.
