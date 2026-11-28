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
