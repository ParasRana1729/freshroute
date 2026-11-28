# Forecasting next-day glut onset with advance market information

The price-band benchmark trains two direct classifiers on the same historical
rows. It retains all observed training onsets and a deterministic quarter-sample
of negatives. Both models see the raw prices, arrival histories, and projected
reporting cohort. The candidate adds the modal price's position in the day's
range and the distance from the low, high, and midpoint to the commodity price
cutoff. The March 2–31 national validation population selects tree counts,
thresholds, and the candidate. Apply those decisions to April 2–30, a previously
used development window. All eligible rows contribute to each comparison.

## Reproduce

Use the pinned archive and dependencies from the [May benchmark](ONSET_COHORT_BENCHMARK.md).

```bash
export POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3
python -m scripts.benchmark_onset_cohort --prepare-only --write-market-keys \
  --archive data/external/agmarknet_full.csv --work-dir data/external/issued_signals
python -m scripts.benchmark_price_band --work-dir data/external/issued_signals \
  --output data/processed/onset_price_band_metrics.json
```

## Evaluate an authorized archive of advance notices

The alternative candidate accepts complete market–commodity forecast snapshots.
Each CSV row needs `state_name`, `market_center_name`, `commodity_name`,
`target_date` (YYYY-MM-DD), `issued_at` (ISO timestamp with UTC offset), and
the fields `expected_arrival_tonnes` and `buyer_demand_tonnes`. At least one
quantity must be observed. Use aggregate quantities and the time the snapshot
was first available to the forecaster. Omit personal identifiers. A later
revision needs its own issue timestamp and complete replacement snapshot.

For each target day the join takes the most recent snapshot available before
midnight in India. It retains every grade and variety in the evaluation,
including markets without a notice. The benchmark reports matched coverage and
the input file digest. The raw market archive provides report dates and the
backtest assumes day-end availability.

```bash
python -m scripts.benchmark_price_band --work-dir data/external/issued_signals \
  --notices data/external/advance_snapshots.csv --output data/external/notice_replay.json
```

The [e-NAM user guide](https://enam.gov.in/web/docs/eNAMMobileApp.pdf) describes
future buyer-demand listings. Its [public trading dashboard](https://enam.gov.in/trading-details)
reports realized arrivals and traded quantities. To evaluate advance notices,
the pipeline needs historical snapshots covering training, calibration and
evaluation. Independent verification also requires a later national daily
export with actual arrivals and modal prices by state, market, commodity,
variety and grade.

## Public price and market signals

The support-price candidate measures the gap between prices on the reporting
day and minimum support prices already announced for 17 exact commodity names.
The common-paddy reference uses the common rate. Local procurement and grade
eligibility remain unobserved. The benchmark also counts errors outside the
covered crops. Correcting every decision inside the covered crops while
freezing the others gives a diagnostic upper bound for that particular change.
[May 2025 kharif announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2131983)
and [October 2025 rabi announcement](https://www.pib.gov.in/newsite/erelcontent.aspx?lang=2&reg=48&relid=276863).

A second candidate learns whether one market's price or arrival rank leads a
change at another market in the same state for the same commodity. It starts
with unpaired reports and refits peer selection at the start of each month
using only previous months' resolved outcomes. Up to three independent peers
contribute predicted changes on each forecast day.

A third candidate uses a 2024-vintage export of 1,901,416 state retail prices
from the Department of Consumer Affairs. It learns repeating half-month price
patterns from completed historical years. A regional onion, potato and tomato
basket can contribute on days when the exact commodity lacks a retail series.
The input CSV is pinned by SHA-256. [Retail price archive](https://ckandev.indiadataportal.com/dataset/price-monitoring/resource/45f8c494-03d2-46b5-aa1a-a5e3656c3da6).

Build a fresh work directory using the preparation command above. It assigns
category IDs in first-report order, breaks ties by name, and uses fixed-width
integers when hashing identities. This makes the sampled negative rows
independent of thread scheduling and the number of categories reported later.

```bash
python -m scripts.benchmark_price_band --work-dir data/external/issued_signals \
  --support-prices --output data/processed/onset_support_price_metrics.json
python -m scripts.benchmark_price_band --work-dir data/external/issued_signals \
  --market-leads --output data/processed/onset_market_lead_metrics.json
curl --fail --location --output data/external/retail.csv \
  'https://ckandev.indiadataportal.com/dataset/1a59d7e5-baf1-4c4a-b10f-55a6367f82f7/resource/45f8c494-03d2-46b5-aa1a-a5e3656c3da6/download/daily-retail-prices-of-essential-commodities.csv'
python -m scripts.benchmark_price_band --work-dir data/external/issued_signals \
  --retail-prices data/external/retail.csv --output data/processed/onset_retail_season_metrics.json
```

## Fresh national test data

On November 28, 2026 the India Data Portal new-source datastore ended on May
31. Its old-source datastore ended on October 26, 2025 and has no grade field.
A search of all 11 FreshRoute branches and GitHub releases found no later
national export. A June data.gov.in mirror retains variety, grade and prices
but has no arrival quantity. A November public Agmarknet extract has market
totals. Across the pinned archive, 111,486 of 125,490 market–commodity days
with multiple varieties or grades have different quantities across those rows.
Assigning the totals to each variety would change the reference labels.
[June mirror schema](https://subsets.io/datasets/agmarknet-prices) and
[public Agmarknet extract](https://github.com/herrrickshaw/india-mandi-arrivals).

## Neural rank forecasts

The multi-task network trains on previously resolved next-day outcomes. It
predicts three arrival-rank thresholds, three price-rank thresholds, two
alternate joint thresholds and the original onset label. The auxiliary outcomes
serve as training targets. Every forecast uses only today's or earlier inputs.
Training-only numeric scales and frequent category names are frozen in March
and April. March selects the checkpoint, blend weight and alert thresholds.
The complete April population supplies the development replay.

```bash
export POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=3
python -m scripts.benchmark_onset_multitask --work-dir data/external/issued_signals \
  --output data/processed/onset_multitask_metrics.json
```

March selected a 50/50 blend of the direct tree and the neural onset head
after ten epochs. It scored **46.95%** positive-class F1 on the full April
replay, compared with **45.98%** for the matched tree. It detected 6,080 of
10,378 onsets in 359,896 rows, with 39.17% precision and 58.59% recall.
Two independent archive builds produced byte-identical metrics, SHA-256
`5a538537b6bc9d2e6f3f8bd56a1d0386f11f938ac91b086872fbf106656afea1`.
Preliminary runs before stabilizing weighted ties ranged from 46.77% to
47.02%. The [rebuild-verified metrics](../data/processed/onset_multitask_metrics.json)
supersede those figures.

A second run used a different quarter of eligible negatives in each epoch
and exposed the network to all 1,334,463 eligible training rows. It
scored 46.9454% on April. The fixed-sample blend scored 46.9462% and had
higher March validation F1. April outcomes played no part in that selection.

```bash
python -m scripts.benchmark_onset_multitask --work-dir data/external/issued_signals \
  --rotating-negatives --output data/processed/onset_rotating_negatives_metrics.json
```

The first choice for fresh verification is June 2–30, 2026, the first complete
target month after the opened May benchmark with the same boundary-pair
convention. Before looking at that month's labels, freeze the candidate,
thresholds and complete national population. Require both quantity and modal
price at the five-key reporting grain and check source compatibility on known
overlap dates. If a different period becomes available first, designate its
dates before opening outcomes. A development replay cannot verify the 80% target.

## Rebuild and ensemble checks

Cold rebuilding the original direct benchmark changed a few weighted peer
ranks when float32 partial sums split a price or arrival tie. The variant
requested by `--write-market-keys` now accumulates weighted peer contributions
in float64 before constructing ties. Two independent builds of the pinned
archive produced identical projections for all 3,755,454 reporting rows.

The ensemble comparison fits separate neural forecasts of all nine rank and
event outcomes. March out-of-sample heads train the stacking model, and April
selects stack size and thresholds on the full population. March forecasts use
training outcomes through February 28. April forecasts use training outcomes
through March 31. The comparison includes the incumbent joint, price, arrival,
projected-cohort and CatBoost heads on both sides. To reproduce it, use the
CatBoost version pinned in the May benchmark and a fresh work directory.

```bash
export POLARS_MAX_THREADS=2 OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=3
python -m scripts.benchmark_onset_neural_stack --work-dir data/external/issued_signals \
  --output data/processed/onset_neural_stack_metrics.json
```
