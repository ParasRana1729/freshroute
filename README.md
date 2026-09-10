# FreshRoute — Food Bank Distribution Optimizer (India)

**In one line:** every day, Indian farm markets (*mandis*) get sudden gluts of
produce that can rot before anyone moves it. FreshRoute looks at today's arrivals
and prices, predicts *tomorrow's* urgent gluts, and hands volunteers a
**move-first dispatch list** so the most perishable surplus goes first.

## How it works (3 steps)
1. **Watch the mandis.** 394,000 real daily records from 2,705 markets across
   28 states (government APMC feed via data.gov.in).
2. **Spot the glut.** When arrivals suddenly surge *and* prices suddenly crash
   at the same market, that's a glut — scored as `S = arrival surge × price drop`.
3. **Forecast + dispatch.** An XGBoost model predicts tomorrow's High/Medium/Low
   priority for every market-crop, and predicted Highs are ranked into a top-50
   dispatch list by urgency × tonnage.

> Honest note: the priority label is a *disclosed proxy rule*, not measured food
> waste. Real row-level waste logs aren't public in India — the reports in this
> repo document exactly what exists and what's missing (`data/SOURCES.md`).

## Key observations
1. **Urgency separates on surge × drop, not raw volume.** Big arrivals alone
   don't flag High — the price crash must confirm nobody's buying.
2. **Perishables lead the glut table.** Onion, potato, tomato and green chilli
   top arrivals — the spoilage framing fits the data.
3. **Big state ≠ most urgent.** Tamil Nadu holds ~34% of rows but its High-rate
   (0.232) sits *below* average — volume dominance doesn't drive the labels.
4. **Perishables vs staples gap is small** (0.270 vs 0.257) — consistent with
   the story, not proof of it in a 24-day window.
5. **Trees beat linear by a mile** (F1 0.52 vs 0.30): glut formation is
   nonlinear, which justifies the XGBoost pick.
6. **Modest scores = honest signal.** F1-macro 0.517 is ~3× the baseline; a
   leaking model would print 0.95+. The fix for higher scores is longer history,
   not tuning tricks.

## Project status
| Stage | Status | Output |
|---|---|---|
| CE-1 data prep | Done | 383,753×22 clean (0 missing) → 383,753×62 encoded; Figs 1–9 |
| CE-2 forecasting | Done | XGBoost F1-macro **0.517**; 50-row dispatch demo; Figs 10–11 |
| Full report | Done | `reports/CE1_Report_FreshRoute.pdf` (12 CE-1 sections + CE-2 appendix) |

## Try it yourself
```bash
pip install -r requirements.txt
python scripts/clean_dataset.py   # CE-1: cleaned/encoded/report/Figs 1-6
python scripts/train_model.py     # CE-2: metrics, dispatch demo, Figs 10-11
```
- Raw data (81 MB) is git-ignored; re-download steps: `data/SOURCES.md`.
- Notebook mirror: `notebooks/CE1_data_preparation.ipynb`.
- Details: `docs/CE1_PRODUCT_SPEC.md`.

## What's next
1. **Demand layer** — ration-card data → need score, so ranking weighs hunger, not just glut size.
2. **Longer history** — 1994–present price series for seasonality; retrain richer.
3. **True optimizer** — hub capacities + travel distances; constrained dispatch.
4. **Model hardening** — calibration, per-state audits, drift monitoring.
5. **Field pilot** — volunteer flow + food-safety logging with a partner food bank.
