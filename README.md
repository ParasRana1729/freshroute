# FreshRoute — Food Bank Optimizer (India)

CE-1 Iteration-1: dataset refined, cleaned, analysed, ML-ready.

**Start here:** `docs/CE1_PRODUCT_SPEC.md` — full 12-point CE-1 spec (title → future scope).

## Quickstart

```bash
pip install -r requirements.txt
python scripts/generate_dataset.py   # -> data/raw/freshroute_foodbank_raw.csv (636 x 20)
python scripts/clean_dataset.py      # -> data/processed/* + reports/figures/*.png
```

Colab: open `notebooks/CE1_data_preparation.ipynb`, upload the raw CSV, run all.

## Data contract (frozen for CE-2)

- Cleaned: `data/processed/freshroute_foodbank_cleaned.csv` — 618 rows x 25 cols, 0 missing
- Encoded: `data/processed/freshroute_foodbank_encoded.csv` — 618 x 45 (One-Hot + label y)
- `y = redistribution_priority` (High 122 / Medium 456 / Low 40 — stratified split required)
- `X = 44 columns` (see `data/processed/cleaning_report.json` → `X_columns`)
- Figures: `reports/figures/01..06_*.png` with observations in spec §8

Previous web-demo version archived in `archive/main-20260907` + tag `archive/pre-reset-20260907`.
