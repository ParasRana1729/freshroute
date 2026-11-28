# Historical analogs for next-day glut onset

This experiment tests whether earlier transitions from the same state, market,
commodity, variety, and grade help predict an onset. The benchmark preserves
the national Track 1A target and the full eligible population.

Each forecast date uses up to 56 calendar days of earlier transitions at the
same reporting entity. Each transition's outcome must be resolved on or before
the forecast date. Two fixed similarity scales weight past transitions by the
distance between observed ranks and levels, recency, weekday, and current rule
state. The eight features summarize the weight available, the next-day glut
rate, and the next-day changes in log arrival and price. With zero weight, the
rate and changes are missing and the model still scores the row.

The comparison holds the base and projected-cohort head predictions fixed.
March forecasts train the stacking models. April 2–30 selects model settings
and alert thresholds on the full validation population. The archive records
report dates, which the experiment uses as a proxy for availability.

## April validation

| Model | Positive-class F1 | Average precision |
| --- | ---: | ---: |
| Projected cohort and baseline ensemble | **47.248%** | 44.095% |
| Ensemble with historical analogs | 47.241% | **44.457%** |

The two models scored the same 359,896 eligible rows, including 10,378 positive
onsets. Historical analogs were available for 355,360 rows. They improved average
precision by 0.36 percentage points. F1 changed by −0.007 percentage points,
so the validation comparison did not promote the analog candidate. This run
used neither May scores nor a new holdout. The [metrics artifact](../data/processed/onset_analog_metrics.json)
records the selected thresholds and exact sample counts.

## Reproduce

Use the archive and dependencies from [the May benchmark](ONSET_COHORT_BENCHMARK.md).

```bash
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_onset_cohort.py \
  --archive data/external/agmarknet_full.csv \
  --work-dir data/external/onset_cohort --prepare-only
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_onset_analogs.py \
  --work-dir data/external/onset_cohort \
  --output data/processed/onset_analog_metrics.json
python -m pytest -q tests/test_onset_archive.py
```
