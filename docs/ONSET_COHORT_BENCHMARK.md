# May glut-onset benchmark

This benchmark forecasts the same Track 1A 0-to-1 transition at the same state, mandi, commodity, variety and grade grain. It scores all eligible normal-market rows on consecutive reporting dates with active commodity groups on both days.

- Clipping bounds use reports through February 28, 2026. This freezes preprocessing before the first out-of-sample forecasts used to train the stack.
- March out-of-sample predictions train the stack. The base models for April and May use reports through March 31.
- April 2–30 target dates select the model and its alert thresholds. The model uses separate thresholds when they improve validation F1 by more than 0.05 percentage points.
- May 2–31 target dates are held out. Changing the threshold by current rule state leaves the full eligible cohort in the evaluation.

The projected cohort uses current reports and reports from the equivalent forecast weekday in the preceding four weeks. It gives peers a reporting weight based on their recent history, including peers that had not reported on the feature date, and ranks forecast levels in that weighted distribution. The richer model also fits separate classifiers for which glut condition is missing today and estimates next-day changes in arrival and price. Both model families use the same raw data and eligible rows.

## Results

| Model | April validation F1 | May held-out F1 |
| --- | ---: | ---: |
| Baseline stack | 46.95% | 46.64% |
| Projected reporting cohort | 46.98% | |
| Baseline and cohort ensemble | 47.25% | |
| Baseline and cohort ensemble with CatBoost | **47.28%** | **47.49%** |

The April-selected model gained **0.85 percentage points** over the baseline on the same **381,513** eligible May rows. It detected **5,793 of 10,712** onsets with **42.32% precision** and **54.08% recall**. The central 95% of differences in 10,000 paired resamples of the 30 target dates ran from +0.40 to +1.27 percentage points. The **80% target remains unmet**. Another claim of held-out performance after further model selection will require a later chronological test.

## Development findings

In the preliminary April ablation, the projected peer distribution reduced next-day arrival-rank MAE from 0.06877 to 0.06103. Price-rank MAE moved from 0.06704 to 0.06899. Separately, two-day-lead GFS forecasts covered 53.94% of eligible April rows using the 180 highest-volume districts with usable coordinates. Adding those forecasts to the preliminary stack reduced validation F1 from 47.00% to 46.91%. The frozen candidate uses the archive and reporting-cohort features. [Open-Meteo Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api)

As a development diagnostic, providing the actual next-day high-arrival classification while forecasting the low-price classification yielded 66.86% April F1. Providing the actual low-price classification and forecasting high arrivals yielded 72.72%. The diagnostic thresholds came from March, and both variants used an observed future outcome. The scores describe these two specific experiments. Pre-market supply and buying signals remain worth evaluating with verified issue timestamps.

A subsequent [cross-commodity local-context experiment](ONSET_LOCAL_CONTEXT_EXPERIMENT.md) added current and lagged market, district, and state reporting conditions. It reduced April validation F1 from 47.25% to 46.96%, so the candidate was rejected without scoring May.

## Reproduce

Use the same full India Data Portal export as the [April archive benchmark](ONSET_ARCHIVE_BENCHMARK.md). The archive supplies report dates in place of original publication timestamps. Report-date availability is assumed for this backtest. Deployment timing can be checked with prospective snapshots that record when each report first appears.

```bash
python -m pip install -r requirements.txt
python -m pip install polars==2.2.0 lightgbm==4.7.0 pyarrow==26.0.1 catboost==1.2.10
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_onset_cohort.py \
  --archive data/external/agmarknet_full.csv \
  --work-dir data/external/onset_cohort \
  --output data/processed/onset_cohort_metrics.json \
  --with-catboost
python -m pytest -q
```

The [May metrics](../data/processed/onset_cohort_metrics.json) record candidate validation scores, final threshold(s), the number of held-out examples, and per-date test results.
