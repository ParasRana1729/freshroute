# FreshRoute — Intelligent Food Bank Redistribution (Punjab Cold-Chain)

**Spec:** `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md` v1.0.0 — 4-stage optimizer
**Plan:** `docs/IMPLEMENTATION_PLAN.md` — phased (P0–P9) + nested loops
**Bibliography:** `docs/BIBLIOGRAPHY.bib` — every constant traced (42 keys)
**Commit:** `a9025f8` P0–P6 RC (P4 MILP, P5 VRPTW OSRM, P3 LGBM+LSTM) + 8 small P1/P7/P9 commits to `20e5371`
**API docs (when running):** http://localhost:8000/docs

Pipeline:

```
Agmarknet/IMD/FSSAI → Stage 1 Arrhenius Phi_env (k(T), t_safe) → Stage 2 Demand LSTM/LightGBM (HVI, 23 districts)
                                     ↓
                    Stage 3 Pareto Matcher S_ij MILP w=[0.35,0.30,0.20,0.15] (PuLP CBC + CP-SAT)
                                     ↓
                    Stage 4 VRPTW Router OR-Tools + λ·t/t_safe + OSRM live (fallback haversine)
                                     ↓
                         FastAPI Gateway → React Operations Console
```

## Quickstart — Full Stack (P6 RC, `replay.sh` one-command)

```bash
# One-command replay (NeurIPS checklist, FAIR)
bash replay.sh
# → pytest 27 (19 spec +8 integration), citation audit green, gold builders, GE, WAPE, manifest SHA

# Or stepwise — Python optimizer (Stage 1-4)
mise use python@3.11
cd freshroute-optimizer-model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mise exec -- pip install -r requirements.txt  # alt

# P1 ingestion (live with synthetic fallback, GE)
python -m data.ingestion.agmarknet --date 2026-08-18 --out data/raw/agmarknet/20260818.json
python -m data.ingestion.imd_openmeteo --lat 30.9 --lon 75.85 --date 2026-08-18
python scripts/build_gold_mandi.py --date 2026-08-18          # → data/gold/mandi_daily.parquet
python scripts/build_gold_weather.py --lat 30.9 --lon 75.85 --date 2026-08-18  # → weather_hourly.parquet
python scripts/build_gold_osm.py                              # → osm_distance_matrix.parquet (OSRM live)
python -m data.validation.ge_suites --check-all
python -m data.update_manifest  # SHA in data/data_manifest.json

# P3 training (synthetic 120d, walk-forward)
python -m core.demand_forecaster --days 120 --test-days 14  # LightGBM WAPE 4.38% + LSTM 4.22%
# Verify
python -m pytest tests/ -q                # 27 tests (13 core +6 API +8 integration)
python scripts/citation_audit.py --bib ../docs/BIBLIOGRAPHY.bib --root ..
uvicorn api.app:app --reload --port 8000  # → http://localhost:8000/health + /docs

# 2) React console (repo root, another shell)
npm install
npm run dev                               # → http://localhost:3000 (vite proxy /api → 8000)
```

If the optimizer is not running, the console falls back to `src/data/mockData.js` via `src/lib/freshrouteApi.js` `withFallback()` so the landing page always works.

## Directory Layout (commit `a9025f8` + small P1/P7/P9)

```
docs/
  FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md
  IMPLEMENTATION_PLAN.md
  BIBLIOGRAPHY.bib           # 42 keys: arrhenius, labuza, taoukis, deb, toth, hochreiter, ke, lim, etc.
  datasheets/                # Gebru et al. per dataset (D1-D9)
  model-cards/               # Mitchell et al.: arrhenius.md, pareto_matcher.md, vrp_router.md, demand_forecaster.md (LGBM 4.38%/LSTM 4.22%)
  adr/                       # 000-003 (P4 MILP CBC/CP-SAT, P5 VRPTW OSRM)
  calibration/phi_env.md     # alpha=0.048 beta=0.008 (+ validation 44C/80% 3.72×)
  reviews/phase-0-review.md
freshroute-optimizer-model/
  api/app.py, routes.py, schemas.py   # FastAPI Pydantic v2, MILP use_milp/solver + VRPTW use_or_tools/t_safe/lambda
  core/arrhenius_decay.py             # ThermalDecayEngine P2: Phi_env, t_safe
  core/pareto_matcher.py              # ParetoMatchingEngine P4: rank_allocations + solve_milp_allocations (PuLP/CP-SAT)
  core/vrp_router.py                  # VRPRouter P5: select_vehicle + solve_vrp (OR-Tools VRPTW + OSRM _get_osrm_distance_matrix)
  core/demand_forecaster.py           # HungerDemandForecaster P3: synthetic history 120d + train_lightgbm/train_lstm + forecast_with_model/lstm
  core/tft_stub.py                    # TFTForecaster stub delegating to LGBM/LSTM [@lim2021tft] (P3 stretch)
  data/indian_commodities.json        # Tier priors + Phi params
  data/punjab_districts.json          # 23 districts + HVI
  data/ingestion/agmarknet.py, imd_openmeteo.py, update_manifest.py
  data/validation/ge_suites.py        # GE suites agmarknet/weather/forecaster
  data/data_manifest.json             # FAIR SHA for 7 gold files (FAIR)
  data/gold/*.parquet/.txt/.pt        # gitignored, DVC: mandi_daily, weather_hourly, osm_distance_matrix, forecaster_lgbm/lstm
  scripts/build_gold_{mandi,weather,osm}.py + benchmark_{vrp_lambda,hvi_fusion,matcher_500}.py + pilot_shadow.py + drift_check.py + citation_audit.py
  tests/test_optimizer.py (13) + test_api.py (6) + test_integration_p4p5p3.py (8) # 27 total, spec §6.2 must-pass
  environment.lock                    # pip freeze 10 lines (forced, reproducibility.md)
  requirements.txt + Dockerfile
src/
  App.jsx + components/               # React 18 + Leaflet
  data/mockData.js                    # synthetic priors until gold
  lib/freshrouteApi.js                # live → mock fallback (P6)
paper/main.tex                        # P9 LaTeX skeleton with BIB
replay.sh                             # one-command NeurIPS checklist
```

## Citation & Reproducibility

```bash
bash replay.sh  # pytest 27, citation audit green 27 cites, gold builders, GE 3/3, WAPE 4.38/4.22, manifest SHA
# or stepwise: see Quickstart and docs/reproducibility.md (NeurIPS checklist, FAIR) + CITATION.cff
```

Datasheets per `docs/datasheets/TEMPLATE.md` (Gebru), model cards per `docs/model-cards/TEMPLATE.md` (Mitchell), `data/data_manifest.json` FAIR SHA + DOI, `environment.lock` pinned.

```bash
# Gold and drift
python -m data.validation.ge_suites --check-all
python scripts/drift_check.py  # PSI>0.2 → retrain
python scripts/benchmark_vrp_lambda.py  # λ grid 0.5,1,2,5
python scripts/pilot_shadow.py  # 2×2 GT KPIs
```

## Phase Gates (Implementation Plan) — P0–P6 RC, P7–P9 pending

- **P0 Charter** ✓ — scaffold + 42-key BIB + audit green 27 cites + 27 tests pass + `phase-0-review.md:1`
- **P1 Data** ✓ synthetic+live — Agmarknet POST+BS4 + IMD live, GE 3 suites pass, `mandi_daily`/`weather_hourly`/`osm_distance_matrix` parquet via `build_gold_*.py`, `data_manifest.json` SHA `f869...`/`ca13...`/`e38b...`/`0040...`/`6098...`/`3d6b...`/`66c6...` + `update_manifest.py` (Zenodo v0.1 pending)
- **P2 Kinetics** ✓ prior — `arrhenius_decay.py:272` `Phi=3.72` at 44C/80% `CRITICAL_HAZARD`, `phi_env.md:6` validation, chamber refit `C6` pending
- **P3 Forecaster** ✓ LGBM+LSTM v1 — `demand_forecaster.py:31` 120d syn, LightGBM WAPE 4.38% + LSTM 4.22% 20 epochs, `pilgrim_recall 0.85/0.82`, `tft_stub.py:1` stretch, `benchmark_hvi_fusion.py:1` w2 Gini
- **P4 Matcher** ✓ MILP — `pareto_matcher.py:335` greedy `<100ms` (N=100 2ms) + `solve_milp_allocations:337` PuLP/CP-SAT `<800ms` (N=100 163ms, N=500 555ms) `adr/002`, hypervolume bench `benchmark_matcher_500.py:1`
- **P5 VRPTW** ✓ OSRM — `vrp_router.py:63` `RoutingModel` `t_safe`+`λ=2.0` + `_get_osrm_distance_matrix:27` live OSRM fallback haversine, `benchmark_vrp_lambda.py:1` λ grid, `adr/003`
- **P6 Integration** ✓ — `api/*` MILP `use_milp`/VRPTW `use_or_tools` flags, `replay.sh:1`, `environment.lock:1`, vite proxy `0.0.0.0:3000→8000`
- **P7 Field Pilot** → shadow `pilot_shadow.py:1` 2×2 GT `100%` spoilage/cold/dietary (field BLE `spec:534` pending), KPIs `≥95%` unmeasured
- **P8 MLOps** → `drift_check.py:1` PSI `1.779>0.2` drift, `Dockerfile:1` ready
- **P9 Paper** → `paper/main.tex:1` skeleton + `BIBLIOGRAPHY.bib`, `replay.sh` bundle

## Ethics

Langar Rehat `Strict_Lacto_Vegetarian`, Halal, child/senior prioritization — hard gates in `core/pareto_matcher.py:check_dietary_eligibility`, 100% dietary compliance KPI. See `docs/datasheets/*.md` and ICMR 2017.

