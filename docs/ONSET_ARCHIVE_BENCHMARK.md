# Extended glut-onset benchmark

The benchmark uses the original Track 1A positive class. It predicts a next-day glut in a market that is normal today. Glut status uses the contemporary commodity cross section with the configured arrival and price ranks. The eligible cohort requires consecutive reports at the original state, market, commodity, variety and grade grain.

The India Data Portal archive contains reports from October 27, 2025 through May 31, 2026. Training used reports through February 28, 2026. March 2–31 target dates were reserved for model and threshold selection, and April 2–30 target dates for scoring. The split excludes pairs across month boundaries. May remained outside the experiment.

| Exploratory March validation candidate | F1 |
| --- | ---: |
| Direct LightGBM with market and peer history | 45.83% |
| Direct LightGBM with additional rule-state transition histories | 45.92% |
| Stacked joint, arrival and price forecasts | 46.27% |

The reproducible pipeline selected the stack at **46.17% March validation F1**. It reached **46.43% F1** on the April holdout of **359,896** eligible records with **10,378** positives. Precision was **38.16%**, recall was **59.30%** and average precision was **44.07%**. This is a separate evaluation from the four-day 2025 test and remains below the **80%** target.

The stack combines a direct onset forecast, a forecast of passing the arrival gate, and a forecast of passing the price gate. The base models train on every third eligible training date to bound memory while covering all weekdays. January-trained models generate out-of-sample inputs to train the stack in February. The base modules fit through February supply the March and April predictions. March selects the stack and threshold before April scoring.

## Reproduce

Use the full "APMC Arrivals And Prices (New Source)" CSV from the India Data Portal. The checked archive has the SHA-256 digest `f8a4372f3c4d532cc0a1a584933b9cfded8f71a6648e4724497976bcbc0025e3`. The benchmark reads the original export and builds the necessary Parquet intermediates locally. [India Data Portal source](https://indiadataportal.com/p/agriculture-marketing/r/moafw-agmarknet_commodities_new-ol-dl-hic)

```bash
python -m pip install -r requirements.txt
python -m pip install polars==2.2.0 lightgbm==4.7.0 pyarrow==26.0.1
POLARS_MAX_THREADS=4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 \
  python scripts/benchmark_onset_archive.py \
  --archive data/external/agmarknet_full.csv \
  --work-dir data/external/onset_archive \
  --output data/processed/onset_archive_metrics.json
python -m pytest -q tests/test_onset_archive.py
```

`--model direct` runs the direct LightGBM baseline. The [metrics file](../data/processed/onset_archive_metrics.json) contains the validation trials, frozen threshold and per-date held-out metrics for the stack.

## Where the errors come from

In March, about 4% of glut onsets had both the same price and the same arrival quantity as the previous day. A LightGBM cutoff model forecast daily log-price and log-arrival cutoff changes from day of week, peer counts and cutoff lags. It reduced weighted log-arrival cutoff MAE from 0.131 to 0.110 over 3,352 commodity-days. On 339,592 validation rows with both cutoff forecasts available, substituting known next-day price and arrival levels raised the diagnostic F1 from 73.58% with today's cutoffs to 75.81% with forecast cutoffs. Those calculations use next-day outcomes to isolate errors due to cutoff shifts.

Adding those cutoff forecasts and the distances to them moved the exploratory stack from 46.27% to 46.43% on March validation. This candidate has only been evaluated on validation. A larger improvement may require forecasts of price and arrival levels that use advance supply or buyer demand data. The e-NAM guide describes advance demand submissions with a mandi, commodity, quantity and intended date. A usable retrospective feed would also need the original submission timestamp and sufficient coverage across the benchmark. [e-NAM mobile guide](https://enam.gov.in/web/docs/eNAMMobileApp.pdf)
