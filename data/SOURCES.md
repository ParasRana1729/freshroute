# Data sources (all real, India-native, downloadable, cited)

## 1. Primary dataset — real India APMC arrivals + prices
- **File:** `data/raw/apmc_arrivals_prices.csv` (untouched download)
- **Source:** Directorate of Marketing & Inspection (DMI), Ministry of Agriculture
  & Farmers Welfare, through the [India Data Portal's Agmarknet archive](https://indiadataportal.com/p/agriculture-marketing).
- **Coverage:** 2025-10-27 – 2025-11-19 (24 days), 383,692 rows after cleaning and deduplication.
- **Columns:** date, state/district/market, commodity/variety/grade,
  latitude/longitude, arrival quantity and units, and the minimum, maximum,
  and modal prices with their units.
- **Archive license:** Open Data Commons Attribution License.
- **Role:** supply-side data the optimizer learns from (arrival surges +
  price depressions = glut proxy at mandi level)
- **Recover the benchmark:** Run `python scripts/fetch_benchmark_data.py`, then
  `python scripts/clean_dataset.py`. The fetcher extracts the first 394,257 complete
  records from the archive and writes the git-ignored raw CSV. The original
  cleaning report counted a 394,258th raw record with incomplete fields that was
  discarded during cleaning. The archive includes additional reports for November
  19, so filtering the full export by date alone changes the test cohort.

## 2. Derived target — disclosed, not observed
- `redistribution_priority` (Low/Medium/High) is **derived by a published rule**:
  `S = arrival_z * (-price_z)` per market-commodity (6-period rolling baseline,
  min_periods=2, commodity-median fallback); High if S>=p75 (0.319),
  Medium if S>=p40 (0.0), else Low. Thresholds saved in
  `data/processed/cleaning_report.json`.
- It is a triage label for the optimizer demo, not a measured waste quantity.

## 3. Rejected (per empirical reports, not used for training)
- Virginia BRAFB food-bank logs — real ops but wrong country, removed.
- UNEP Food Waste Index India row — single national aggregate (68.7M t/yr),
  no market/time variation, cannot train ML.
- Indiastat (paywall), FAOSTAT (national macro only), synthetic Kaggle logs.

## 4. Planned augmentation (not yet in pipeline)
- WFP India Food Prices (HDX, 1994–present, 164 markets with lat/lon) for
  long-baseline seasonality.
- Maharashtra District PDS Beneficiary Census (36 districts, AAY/PHH) for
  demand-side vulnerability `V_d`.
