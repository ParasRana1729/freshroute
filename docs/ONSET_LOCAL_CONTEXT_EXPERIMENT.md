# Cross-commodity local-context experiment

This development experiment keeps the Track 1A target, national cohort, and
state–market–commodity–variety–grade grain unchanged. It asks whether reports
from other commodities in the same market, district, or state improve the
projected reporting-cohort model.

All features are available on or before the feature date. The compact candidate
uses current market, district, and state report counts and glut-gate rates. It
also uses market values from the preceding day and the equivalent forecast
weekday one week earlier. Exact calendar joins create the lag features. A
future-row invariance test checks that adding later reports does not change
earlier feature values.

## Result

| Model | April 2–30 validation F1 |
| --- | ---: |
| Projected cohort and baseline ensemble | **47.25%** |
| Ensemble with cross-commodity local context | 46.96% |

The local-context candidate lost **0.29 percentage points** on the full April
validation cohort and was rejected. May was not scored for this candidate, so
this result is not a new held-out performance claim. The latest valid held-out
result remains the 47.49% May score selected by the preceding April comparison.

The current India Data Portal new-source archive ends on May 31, 2026. The
Agmarknet 2.0 public market-details endpoint has later daily reports, but its
response is aggregated to market–commodity and omits variety and grade. It
therefore cannot construct a fresh test set for the unchanged Track 1A target.
[India Data Portal source](https://indiadataportal.com/p/agriculture-marketing/r/moafw-agmarknet_commodities_new-ol-dl-hic)
[Agmarknet](https://agmarknet.gov.in/home)

## Reproduce

First build the May work directory with the command in
[the May benchmark](ONSET_COHORT_BENCHMARK.md). Then run:

```bash
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_local_context.py \
  --work-dir data/external/onset_cohort \
  --output data/processed/onset_local_context_metrics.json
python -m pytest -q
```

The [metrics artifact](../data/processed/onset_local_context_metrics.json)
contains both April scores, selected thresholds, and the exact compact feature
list.
