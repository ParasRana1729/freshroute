# Cross-commodity local-context experiment

This development experiment keeps the Track 1A target, national cohort, and
state–market–commodity–variety–grade grain unchanged. It asks whether reports
from other commodities in the same market, district, or state improve the
projected reporting-cohort model.

The corrected feature builder uses reports available on or before the feature date.
The compact candidate
uses current market, district, and state report counts and glut-gate rates. It
also uses market values from the preceding day and the equivalent forecast
weekday one week earlier. Exact calendar joins create the lag features. A
future-row invariance test checks that adding later reports does not change
earlier feature values.

## Withdrawn result

| Model | April 2–30 validation F1 |
| --- | ---: |
| Projected cohort and baseline ensemble | **47.25%** |
| Ensemble with cross-commodity local context | 46.96% |

The original experiment selected peer identities using the full table of paired
reports. That membership could depend on reports from after the feature date.
The original 46.96% score is withdrawn. The corrected implementation uses all
unpaired reports and their same-day ranks. It has no reported score here.
The May benchmark's separate projection takes its peers directly from unpaired
reports and retains its 47.49% held-out score.

The current India Data Portal new-source archive ends on May 31, 2026. The
Agmarknet 2.0 public market-details endpoint has later daily reports, but its
response is aggregated to market–commodity and omits variety and grade. It
therefore cannot construct a fresh test set for the unchanged Track 1A target.
[India Data Portal source](https://indiadataportal.com/p/agriculture-marketing/r/moafw-agmarknet_commodities_new-ol-dl-hic)
[Agmarknet](https://agmarknet.gov.in/home)

## Reproduce

Use the CSV and dependencies from [the May benchmark](ONSET_COHORT_BENCHMARK.md).
Rebuild the work directory to include unpaired report metadata before rerunning
the local-context experiment.

```bash
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_onset_cohort.py \
  --archive data/external/agmarknet_full.csv \
  --work-dir data/external/onset_cohort --prepare-only
POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_local_context.py \
  --work-dir data/external/onset_cohort \
  --output data/external/onset_local_context_rerun.json
python -m pytest -q
```

The historical [metrics artifact](../data/processed/onset_local_context_metrics.json)
retains the original audit trail and identifies the withdrawn score.
