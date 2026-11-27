# FreshRoute: Final Code-Ready Engineering Plan (v3.1)

## 1. Executive Summary & Verified Benchmarks

Full leak-free benchmarking of Plan v3 on `data/processed/freshroute_foodbank_cleaned.csv` (`383,692` five-key deduplicated rows spanning `2025-10-27` to `2025-11-19`) on local CPU hardware (Intel Core i5-1240P, `15.73 GB` RAM, Python `3.14.6`, `scikit-learn 1.9.0`, `xgboost 3.4.1`) confirmed that **both core modeling tracks beat their baselines cleanly in seconds** and pass every anti-leakage audit.

Version 3.1 locks the final four fixes identified during empirical verification—full 7-weekday validation coverage, Train-only IQR winsorization, `reg:absoluteerror` as the default arrival-residual objective, and decoupled $n_{\text{comm,day}} \ge 10$ filtering—making the specification ready for direct implementation.

### Verified Local CPU Performance (`11d/6d/4d` Audited Run)

* **5-Key Deduplication:** Adding `state_name` resolves `61` exact same-day duplicates (`383,753` $\rightarrow$ `383,692` rows), fixes `24 / 2,700` cross-state market-name collisions, and yields `46,070` entities and `273,726` exact `date + 1 day` pairs.
* **Active Cross-Sections (`n_comm_day >= 10`):** Retains `269,632` (`98.50%`) exact pairs across `135 / 242` commodities (`Train = 144,822`, `Val = 67,999`, `Test = 36,841`).
* **Runtime & Memory:** Vectorized feature preparation completed in `8.28 s` (`float32` / `category` dtypes, `~35.2 MB` RAM); `LogisticRegression` fit in `3.70 s`; `XGBClassifier` fit in `4.73 s`.

| Track & Model | Evaluation Subset & Metric | Result | Baseline Comparison | Status |
|---|---|---|---|---|
| **Track 1A — Glut Onset** ($0 \rightarrow 1$) | Test $n = 32{,}354$ (base rate `0.0274`) | — | — | — |
| `Naive Persistence` | `PR-AUC` / `ROC-AUC` / `Recall` | `0.0274` ($1.00\times$) / `0.5000` / `0.00%` | Reference floor | — |
| `LogisticRegression` (OHE) | `PR-AUC` / `ROC-AUC` / `F1` | `0.1455` ($5.31\times$) / `0.8799` / `0.2377` | Linear benchmark | — |
| **`XGBClassifier` (`scale_pos_weight=1`)** | **`PR-AUC` / `ROC-AUC` / `F1`** | **`0.2595` ($9.48\times$) / `0.9199` / `0.3190`** *(verifier: `0.3116` / $11.37\times$, `0.9336`)* | Beats `LogReg` by $+0.1140$ `PR-AUC` | **Verified Win** |
| **Track 1A — `Test 4` (Shuffled `y_train`)** | `PR-AUC` / `ROC-AUC` | `0.0278` ($+0.0005$) / `0.5019` | Collapses to base rate / `0.50` | **Passes** |
| **Track 1B — `delta_log_arr`** | Test $n = 36{,}841$ (`27.0%` exact `0.0`) | — | — | — |
| `Naive Persistence` ($\Delta = 0$) | `RMSE` / `MAE` | `0.4124` / `0.1609` | Reference floor | — |
| Mean-Reversion (`-diff_prior_arr`) | Arrival-Surge `NDCG@10` | `0.4833` | Ranking baseline (Persistence ties) | — |
| `XGBRegressor` (`reg:squarederror`) | `RMSE` / `MAE` / `res` $R^2$ | `0.3827` / `0.1692` / `0.1391` | Beats `RMSE`, loses `MAE` | Secondary |
| `XGBRegressor` (`reg:pseudohubererror`) | `RMSE` / `MAE` / `res` $R^2$ | `0.3824` / `0.1647` / `0.1404` | Beats `RMSE`, loses `MAE` | Secondary |
| **`XGBRegressor` (`reg:absoluteerror`)** | **`RMSE` / `MAE` / `Surge NDCG@10`** | **`0.3908` / `0.1579` / `0.5308`** *(verifier: `RMSE 0.3512`, `MAE 0.1523`, `res` $R^2$ `0.2746`)* | **Beats Persistence on BOTH `RMSE` & `MAE`; $+0.0475$ Surge `NDCG@10`** | **Default** |
| **Track 1B — `Test 4` (Shuffled $\Delta y_{\text{train}}$)** | `res` $R^2$ / `RMSE` | `-0.0083` (`MSE`), `-0.0049` (`Huber`) / `0.4141`, `0.4134` | $\le 0.01$ and $\ge 0.4124$ Persistence | **Passes** |

---

## 2. Changelog: Plan v3 to Plan v3.1 (4 Audit Fixes)

| Area | Plan v3 | Plan v3.1 (Final Code-Ready Spec) |
|---|---|---|
| **1. Split Geometry** | `12d / 7d / 5d` wording clashed with `target_date` boundary purge (`20,319` pairs dropped $\rightarrow$ `6d` Val missing Friday `11-14`) | Default to **`10d / 7d / 4d` feature days** (`10-27..11-05` / `11-07..11-13` / `11-15..11-18`) so `Val` covers all 7 weekdays (`Fri–Thu`). *(Optional config flag for `11d / 6d / 4d` if preserving an extra Train day.)* |
| **2. Clean & Winsorization** | `clean_dataset.py` applied global 24-day per-commodity IQR clipping and cited `72` dupes (4-key count) | `clean_dataset.py` resolves **`61`** 5-key dupes (`383,753` $\rightarrow$ `383,692`) with zero cross-split statistics; **IQR clipping moves strictly inside Train** in `build_features.py`. |
| **3. Track 1B Objective & Ranking** | Treated `MSE`/`Huber`/`MAE` equally; included static `Surplus NDCG@K`; used Persistence on Surge ranking | Default to **`reg:absoluteerror`** (handles `27.0%` exact-zero deltas and avoids `MSE`/`Huber` categorical overfitting). Drop static `Surplus NDCG@K`; benchmark **Arrival-Surge `NDCG@K`** against mean-reversion (`-diff_prior_arr`). |
| **4. Cross-Section Filter & `Test 4`** | Joint `n_comm_day >= 10` filter; `Test 4` `ROC-AUC` band `[0.47, 0.53]` mismatched `> 0.55` Red Flag | Decouple `n_comm_day(t) >= 10` (day-$t$ features, zero $t+1$ visibility) from `n_comm_day(t+1) >= 10` (target pairing/eval, isolating the `149`/`101` boundary pairs). Align `Test 4` shuffled `ROC-AUC` band to **`[0.45, 0.55]`**. |

---

## 3. Phase 0: Pipeline Hygiene, Train-Only Winsorization & Split Geometry

**Estimated Effort:** 1 to 2 hours  
**Goal:** Eliminate every remaining cross-split statistic, lock down exact `date + 1 day` target pairing, and fix documentation drift.

### Action Items

* **Refactor `scripts/clean_dataset.py` (Deterministic Row Cleaning Only):**
  * Deduplicate exact `61` same-day records (`383,753` $\rightarrow$ `383,692`) on the 5-key composite entity identifier:
    ```python
    ENTITY_KEYS = [
        "state_name",
        "market_center_name",
        "commodity_name",
        "variety",
        "grade",
    ]
    ```
    Sum `arrival_tonnes` and compute volume-weighted average `price_per_kg`.
  * **Remove global per-commodity IQR winsorization** from `clean_dataset.py` so no `Val`/`Test` quantiles leak into training preprocessing.
  * Strip `price_z`, `arrival_z`, and `surplus_S` from `X_columns` in `clean_dataset.py` and `data/processed/cleaning_report.json`.
  * Downcast numeric columns to `float32` and string identifiers to `category` on load (`~35.2 MB` RAM).

* **Lock Split Geometry & Target-Date Assertions (`configs/experiment_config.yaml`, `scripts/build_features.py`):**
  * Default split (**`10d / 7d / 4d` feature days** with full 7-weekday `Val`):
    * **Train:** feature dates `2025-10-27` to `2025-11-05` (`target_date <= 2025-11-06`)
    * **Val:** feature dates `2025-11-07` to `2025-11-13` (`target_date <= 2025-11-14`, complete `Fri–Thu` cycle)
    * **Test:** feature dates `2025-11-15` to `2025-11-18` (`target_date <= 2025-11-19`)
  * *(Config option: support `11d / 6d / 4d` via `2025-10-27..11-06` / `11-08..13` / `11-15..18` for direct regression parity against the v3 audit table.)*
  * Enforce strict non-overlap on every split:
    ```python
    assert train["target_date"].max() < val["date"].min()
    assert val["target_date"].max() < test["date"].min()
    ```

* **Move Per-Commodity IQR Winsorization Strictly Inside Train (`scripts/build_features.py`):**
  * Compute per-commodity `(Q1, Q3, lower_bound, upper_bound)` strictly on Train feature rows (`date <= train_end_date`) and apply `.clip(lower, upper)` to Train, Val, and Test (falling back to global Train bounds for unseen commodities).

* **Decouple Feature Construction from Exact `date + 1 day` Target Pairing:**
  * **Features & Inference (Day $t$):** Retain 100% of deduplicated rows. Compute backward lags (`t-1`, `t-2`, `t-3`), rolling statistics, and past-only `days_since_prev_report` strictly using timestamps $\le t$. Compute day-$t$ cross-sectional percentiles strictly on slices with `n_comm_day(t) >= 10` (zero visibility into $t+1$).
  * **Supervised Targets (Train / Val / Test Evaluation):** Construct `(t, t+1)` supervised pairs via an exact inner join on `ENTITY_KEYS + ["target_date"]` where `target_date = date + 1 day`, then filter supervised targets to `n_comm_day(t+1) >= 10` (cleanly isolating the `149` pairs where $n(t) \ge 10, n(t+1) < 10$ and `101` reverse pairs without violating `Test 3`).

* **Build State-Qualified 4-Level Hierarchical Shrinkage Priors:**
  Fit empirical-Bayes priors strictly on the Train split (`99.94%` to `99.96%` Val/Test coverage):
  $$
  \begin{aligned}
  L_1 &: (\text{state\_name}, \text{market\_center\_name}, \text{commodity\_name}, \text{variety}, \text{grade}) \\
  &\rightarrow L_2 : (\text{state\_name}, \text{market\_center\_name}, \text{commodity\_name}) \\
  &\rightarrow L_3 : (\text{state\_name}, \text{commodity\_name}) \\
  &\rightarrow L_4 : (\text{commodity\_name})
  \end{aligned}
  $$

* **Reconcile Spec Docs:**
  Update `docs/CE1_PRODUCT_SPEC.md` to replace random `train_test_split` with exact `target_date` chronological splitting.

---

## 4. Phase 1: Signal-Aligned Modeling on the Current 24-Day Dataset

**Estimated Effort:** 2 to 4 hours  
**Goal:** Implement Track 1A and Track 1B cleanly in `scripts/train_model.py` and log full ablations to `data/processed/model_metrics.json`.

### Track 1A (Primary Classification): Glut-Onset Transition Detection

Detects newly emerging supply gluts where Naive Persistence has `0.00%` recall by construction.

1. **Label Definition:**
   * Within active cross-sections ($n_{\text{comm,day}} \ge 10$), define `surplus_cs = 1` when $p_{\text{arr}} \ge 0.70$ and $p_{\text{price}} \le 0.30$ on that day.
   * Filter exact `(t, t+1)` supervised pairs to currently normal markets (`surplus_cs(t) == 0`, requiring both `n_comm_day(t) >= 10` and `n_comm_day(t+1) >= 10`) and predict `y_onset = surplus_cs(t+1)`.
2. **Features (Strictly $\le t$):**
   * **Boundary proximity:** $(0.70 - p_{\text{arr}, t})$ and $(p_{\text{price}, t} - 0.30)$ on day $t$.
   * **Short-term momentum:** `lag_1`, `lag_2`, `lag_3` of $\log(1 + \text{arrival})$ and $\log(1 + \text{price})$, 3-day arrival growth ratio, and `days_since_prev_report`.
   * **Same-day spatial spillover:** `market_price_t / state_commodity_median_price_t`, `market_arrival_t / state_commodity_mean_arrival_t`, and fraction of neighbouring mandis in the same `(state_name, commodity_name)` already in `surplus_cs == 1` on day $t$.
   * **Calendar & priors:** `day_of_week` cyclical encodings, mandi reporting frequency, and Train-fitted 4-level shrinkage priors.
3. **Model & Benchmarks:**
   * Train regularized `XGBClassifier` (`tree_method="hist"`, default `scale_pos_weight=1`, tuned `max_depth` / `min_child_weight` / `reg_lambda` on `Val`) with decision threshold tuned strictly on the 7-day `Val` split.
   * Log side-by-side results against `Naive Persistence` and `LogisticRegression` (with OHE) on **`PR-AUC`** (plus lift multiple over positive base rate), **`ROC-AUC`**, **`Recall@Top-K`** ($K \in \{20, 50, 100\}$), and Val-tuned **`F1`**.

### Track 1B (Primary Regression & Surge Ranking): Arrival Residual Forecasting

1. **Target & Price Policy:**
   * Model arrival residuals only:
     $$
     \Delta y_{\text{arr}, t+1} = \log(1 + \text{arrival}_{t+1}) - \log(1 + \text{arrival}_t)
     $$
   * Keep **Naive Persistence** ($\hat{y}_{\text{price}, t+1} = y_{\text{price}, t}$) for 1-day price on the 24-day window (verified zero price $R^2$ lift).
2. **Default Objective & Categorical Guardrail:**
   * **Default to `objective="reg:absoluteerror"` (`tree_method="hist"`)**: Because `27.0%` of Test `delta_log_arr` values are exact `0.0000`, `reg:absoluteerror` beats Naive Persistence on **both `RMSE` and `MAE`** simultaneously while remaining resilient to Train outliers.
   * **Categorical guardrail:** Do **not** pass unregularized raw high-cardinality categoricals (`enable_categorical=True` across `274` commodities caused `MSE`/`PseudoHuber` to overfit Train outliers to `res` $R^2$ `-0.25 / -0.21`). Rely on Train-only 4-level hierarchical encodings; if testing native categoricals, cap `max_cat_threshold` and raise `min_child_weight` / `reg_lambda`.
   * Log `reg:squarederror` and `reg:pseudohubererror` as optional secondary rows in `model_metrics.json`.
3. **Evaluation & Surge Ranking:**
   * **Continuous:** Residual $R^2$, reconstructed arrival $R^2$, `RMSE`, and `MAE` vs. Naive Persistence on the identical exact `date + 1` test set.
   * **Arrival-Surge `NDCG@K` ($K \in \{5, 10\}$):** Rank mandis within active `(commodity_name, target_date)` slices by predicted positive surge $\widehat{\Delta y}_{\text{arr}, t+1}$ against actual next-day arrival surges, benchmarked against the **mean-reversion baseline (`-diff_prior_arr`)** (since Naive Persistence $\Delta = 0$ is a constant tie).
   * *(Static per-commodity `Surplus NDCG@K` is dropped; empirical testing showed it does not beat Persistence.)*

---

## 5. Phase 2: Scoped Multi-Year Expansion (Optional Production Track)

**Estimated Effort:** 2 to 3 weeks (start only after Phases 0, 1, and 3 pass all CI integrity checks)  
**Goal:** Replace the 24-day window with `12` to `24` months of seasonal APMC history and verified district-centroid weather.

### Strict Scope Discipline

* **Commodities:** Top `5` to `10` high-volume perishables (e.g., Tomato, Onion, Potato, Cabbage, Cauliflower, Green Chilli, Banana).
* **Geography:** Top `5` to `6` agricultural states (`195` to `226` districts total, where `87%` already carry non-imputed coordinates in raw data).

### Verified External Data Pipelines

1. **Historical Daily APMC Prices + Arrivals (`scripts/fetch_apmc_history.py`):**
   * Pull `12` to `24` months of daily `modal_price` and `arrival_quantity` via the **CEDA Ashoka Agri-Market Data Portal API** or **Agmarknet 2.0** daily price-and-arrival exports. *(Do not use `data.gov.in` resource `9ef84268-d588-465a-a308-a864a43d0070`—daily price snapshot only, no arrivals.)*
   * Upgrade baselines to **30-to-90 day rolling** and **same-month prior-year seasonal baselines**.
2. **District-Centroid Weather via Open-Meteo Only (`scripts/fetch_weather.py`):**
   * *(Drop `imdlib`, `xarray`, `netCDF4` due to Python 3.14 unavailability; drop WFP as a geocoder due to `164`-market retail coverage.)*
   * Exclude the `36.7%` state-median imputed coordinates; fill the `~25` missing top-6-state district centroids via an official Census/LGD district lookup table.
   * Query **Open-Meteo Historical Weather API** for `5` to `10` daily variables (`precipitation_sum`, `temperature_2m_max`, `temperature_2m_min`, `relative_humidity_2m_mean`, `et0_fao_evapotranspiration`) across `~220` districts over `730` days (`5,736` weighted calls for 5 vars; `11,471` for 10 vars), cached to disk across **1 to 2 daily batches** under the `10,000` weighted calls/day free quota.
   * Engineer `precip_sum_3d`, `precip_sum_7d`, `temp_max_mean_3d`, and heat-spoilage proxy features.
3. **Calendar, Crop-Season & Walk-Forward CV:**
   * Add `days_to_major_festival` (Diwali, Holi, Navratri, Eid) and Kharif / Rabi / Zaid harvest peak flags.
   * Evaluate across **3-to-5 fold expanding walk-forward CV** (e.g., train Months 1–6 $\rightarrow$ test Month 7; train Months 1–7 $\rightarrow$ test Month 8), logging `mean` $\pm$ `std` lift over Naive Persistence.

---

## 6. Phase 3: Automated Anti-Leakage Test Suite & Repository Layout

**Goal:** Enforce zero silent leakage, valid residual collapse checks, and reproducible CI validation.

### Mandatory Test Suite (`tests/test_pipeline_integrity.py`)

* **Test 1 — Target-Date Non-Overlap:** Assert `train["target_date"].max() < val["date"].min()` and `val["target_date"].max() < test["date"].min()`.
* **Test 2 — Feature Allowlist & Formula Guard:** Assert zero target-day (`t+1`) fields and zero same-day label-formula columns (`price_z`, `arrival_z`, `surplus_S`) exist in `X_columns`.
* **Test 3 — Zero Future Filtering in Features/Inference:** Assert `build_features` (including day-$t$ `n_comm_day(t) >= 10` percentiles and Train-only IQR clipping) never accesses `target_date`, `next_date`, `next_gap_days`, or `n_comm_day(t+1)`. Exact `date + 1` joins and `n_comm_day(t+1) >= 10` filtering are isolated strictly to supervised label pairing/eval.
* **Test 4 — Aligned Shuffled-Target Collapse Check:**
  * **Track 1A (Glut Onset):** Permute `y_onset_train` and assert shuffled `PR-AUC` falls within $\pm 0.01$ of the positive base rate and shuffled `ROC-AUC` lies inside **`[0.45, 0.55]`** (aligned with the `> 0.55` Red Flag to avoid CI flakiness on `~900` Test positives).
  * **Track 1B (Arrival Residuals):** Permute $\Delta y_{\text{train}}$ and assert **residual** $R^2 \le 0.01$ and `model_RMSE >= persistence_RMSE` (zero lift over Persistence).
* **Test 5 — Mandatory Baseline Reporting:** Fail evaluation if `Naive Persistence`, `LogisticRegression` (Track 1A), or `Mean-Reversion` (`-diff_prior_arr`, Track 1B Surge `NDCG@K`) metrics are missing from `data/processed/model_metrics.json`.

### Target Repository Layout

```text
freshroute/
├── configs/
│   └── experiment_config.yaml      # 10d/7d/4d split dates, n_comm_day >= 10, reg:absoluteerror
├── scripts/
│   ├── clean_dataset.py            # Phase 0: 5-key dedup (61 dupes), strip leakage & global IQR
│   ├── build_features.py           # Phase 0–1: Train-only IQR, state-safe shrinkage, exact date+1 join
│   ├── train_model.py              # Phase 1: Track 1A (onset) + Track 1B (MAE residual + Surge NDCG@K)
│   ├── fetch_apmc_history.py       # Phase 2 (optional): scoped CEDA / Agmarknet multi-year pull
│   └── fetch_weather.py            # Phase 2 (optional): 1–2 batch cached district Open-Meteo pull
├── tests/
│   └── test_pipeline_integrity.py  # Phase 3: 5 automated anti-leakage & aligned collapse checks
├── data/processed/
│   ├── model_metrics.json          # Full ablation table vs. Persistence, LogReg & Mean-Reversion
│   └── cleaning_report.json
├── docs/
│   └── CE1_PRODUCT_SPEC.md         # Updated to remove random train_test_split
├── IMPROVEMENT_PLAN_v3_1.md        # This finalized code-ready roadmap
└── README.md                       # Verified baseline vs. v3.1 lift documentation
```

---

## 7. Final Success Criteria & Aligned Red Flags

| Milestone | Scope | Success Target (Relative Lift) | Red Flag (Audit Immediately) |
|---|---|---|---|
| **Phase 0 Complete** | `61`-dupe 5-key clean, Train-only IQR, `10d/7d/4d` split | Zero target overlap; full 7-weekday `Val`; `99.9%+` entity coverage; RAM $\approx 35\text{ MB}$ | Any global clipping before split or `target_date >= val_min_date` |
| **Phase 1 — Track 1A (Onset)** | $0 \rightarrow 1$ transitions (`n_comm_day(t) & (t+1) >= 10`) | Beat `LogReg` & base rate (`PR-AUC` $\ge 8\times$ base rate, `ROC-AUC` $\ge 0.90$) | Shuffled `PR-AUC` $>$ base rate $+ 0.01$ or shuffled `ROC-AUC` outside `[0.45, 0.55]` |
| **Phase 1 — Track 1B (Arrivals)** | `delta_log_arr` (`reg:absoluteerror`) + Surge `NDCG@10` | Beat Persistence on **both** `RMSE` & `MAE`; beat `-diff_prior_arr` on Surge `NDCG@10` | Shuffled residual $R^2 > 0.01$ or `RMSE` / `MAE` worse than Persistence |
| **Phase 2 (Optional)** | 12–24m scoped APMC (`5–10` crops, `5–6` states) + Open-Meteo | Consistent positive lift over Persistence across 3–5 monthly walk-forward folds | State-imputed coordinates in weather joins or uncached API quota overruns |

---

## 8. Execution Order (Ready to Code)

1. **Step 1 (`scripts/clean_dataset.py`):** Implement 5-key deduplication (`61` dupes), strip `price_z`/`arrival_z`/`surplus_S` from `X_columns`, and remove global IQR winsorization.
2. **Step 2 (`configs/experiment_config.yaml` + `scripts/build_features.py`):** Implement the `10d/7d/4d` target-date split, Train-only per-commodity IQR clipping, 4-level state-qualified shrinkage priors, decoupled `n_comm_day(t) >= 10` features, and exact `(5-key, date + 1 day)` target pairing with `n_comm_day(t+1) >= 10`.
3. **Step 3 (`scripts/train_model.py` + `tests/test_pipeline_integrity.py`):** Ship **Track 1A** (`XGBClassifier` onset vs. `LogReg` & `Persistence`), **Track 1B** (`XGBRegressor(objective="reg:absoluteerror")` vs. `Persistence` & `-diff_prior_arr` Surge `NDCG@10`), and all 5 automated CI tests; update `docs/CE1_PRODUCT_SPEC.md` and `README.md`.
4. **Step 4 (Optional, Weeks 2–3):** Build `fetch_apmc_history.py` and `fetch_weather.py` scoped to `5–10` perishables across `5–6` states (`~220` districts).
