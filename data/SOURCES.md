# Data sources (all real, India-native, downloadable, cited)

## 1. Primary dataset — real India APMC arrivals + prices
- **File:** `data/raw/apmc_arrivals_prices.csv` (untouched download)
- **Source:** Directorate of Marketing & Inspection (DMI), Ministry of Agriculture
  & Farmers Welfare — via data.gov.in API `9ef84268-d588-465a-a308-a864a43d0070`
  (`Current Daily Price of Various Commodities from Various Markets (Mandi)`)
  / CEDA Ashoka Agmarknet mirror
- **Coverage:** 2025-10-27 – 2025-11-19 (24 days), 383,753 usable rows × 22 cols
  after cleaning (394,258 raw), 28 states, 528 districts, 2,705 markets,
  304 commodities
- **Columns:** date, state/district/market, commodity/variety/grade,
  latitude/longitude, arrival_tonnes, min/max/modal_price, price_per_kg,
  price_z, arrival_z, surplus_S
- **License:** Government Open Data License – India (GOLD) / CEDA Open Data
  Terms (free non-commercial academic attribution)
- **Role:** supply-side data the optimizer learns from (arrival surges +
  price depressions = glut proxy at mandi level)
- **Re-download (file is git-ignored, 81 MB local only):**
  - data.gov.in API (free key required):
    `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=<YOUR_KEY>&format=csv&limit=10000`
    paginate with `offset`, save as `data/raw/apmc_arrivals_prices.csv`
  - or CEDA mirror UI/API: `https://agmarknet.ceda.ashoka.edu.in/`
  - then run `python scripts/clean_dataset.py` to regenerate
    `data/processed/` outputs

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
