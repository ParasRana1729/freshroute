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
