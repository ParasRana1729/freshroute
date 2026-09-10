# Data sources (all real, downloadable, cited)

## 1. Primary dataset — real food-bank distribution records
- **File:** `data/raw/brafb_virginia_foodbank.csv` (untouched download)
- **Source:** Federation of Virginia Food Banks — Blue Ridge Area Food Bank (BRAFB),
  via Virginia Open Data Portal
- **Direct download:** https://data.virginia.gov/dataset/d41d41d4-30c6-4c83-8b94-f2824d88dd9e/resource/399f142b-0195-47d0-b2ec-0bd7f73f3517/download/rows.csv
- **Coverage:** monthly records by locality, Jan 2019 – Jun 2021, 1020 rows × 8 cols
- **Columns:** Year, Month, Locality, Households Served, Individuals Served,
  Pounds of Food Distributed, Children Served (non-federal programs),
  Pounds via child-nutrition programs
- **License:** public open data (Virginia portal terms)
- **Role in project:** the distribution-side data the optimizer learns from
  (real food-bank ops: demand served + volumes moved per locality-month).

## 2. India supply anchor — real UNEP waste estimates
- **File:** `data/raw/food_waste_by_country.csv` (untouched download)
- **Source:** UNEP Food Waste Index Report 2021, via Kaggle mirror + GitHub mirror
  (https://github.com/Sidhi-03/Food-Security)
- **India row (real):** 50 kg/capita/yr household (68,760,163 tonnes/yr),
  retail 16 kg/capita/yr (21,371,087 t), food service 28 kg/capita/yr (37,778,821 t)
- **Role in project:** anchors the India supply side of the optimizer framing;
  every India parameter traces to this row or a cited assumption (see spec sheet).

## 3. Derived target — disclosed, not observed
- `redistribution_priority` (Low/Medium/High) is **derived by a published rule**
  (bottom-tercile supply-per-person + top-half need → High; top-tercile supply → Low;
  else Medium). Thresholds are saved in `data/processed/cleaning_report.json`.
- It is a triage label for the optimizer demo, not a measured quantity.
  Stated openly in the spec sheet and report.
