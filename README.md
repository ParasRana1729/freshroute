# FreshRoute — Intelligent Food Bank Redistribution (Punjab Cold-Chain)

**Spec:** `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md` v1.0.0 — 4-stage optimizer
**Plan:** `docs/IMPLEMENTATION_PLAN.md` — phased (P0–P9) + nested loops
**Bibliography:** `docs/BIBLIOGRAPHY.bib` — every constant traced (42 keys)
**API docs (when running):** http://localhost:8000/docs

Pipeline:

```
Agmarknet/IMD/FSSAI → Stage 1 Arrhenius Phi_env (k(T), t_safe) → Stage 2 Demand LSTM/LightGBM (HVI, 23 districts)
                                     ↓
                    Stage 3 Pareto Matcher (S_ij MILP, w=[0.35,0.30,0.20,0.15])
                                     ↓
                    Stage 4 VRPTW Router (OR-Tools, vehicle tiering)
                                     ↓
                         FastAPI Gateway → React Operations Console
```

## Quickstart — Full Stack (P6)

```bash
# 1) Python optimizer (Stage 1-4)
mise use python@3.11   # or python3.11
cd freshroute-optimizer-model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # P0 minimal: fastapi/pydantic enough for tests
# or: mise exec -- pip install -r requirements.txt

# Ingestion stubs (synthetic until P1 live)
python -m data.ingestion.agmarknet --date 2026-08-18
python -m data.ingestion.imd_openmeteo --lat 30.9 --lon 75.85 --date 2026-08-18

# Verify
python -m pytest tests/ -q                # 13 core + 6 API contract tests
python scripts/citation_audit.py --bib ../docs/BIBLIOGRAPHY.bib --root ..
uvicorn api.app:app --reload --port 8000  # → http://localhost:8000/health + /docs

# 2) React console (in another shell, repo root)
npm install
npm run dev                               # → http://localhost:3000  (vite proxy /api → 8000)
```

If the optimizer is not running, the console falls back to `src/data/mockData.js` via `src/lib/freshrouteApi.js` `withFallback()` so the landing page always works.

## Directory Layout

```
docs/
  FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md
  IMPLEMENTATION_PLAN.md
  BIBLIOGRAPHY.bib           # 42 keys: arrhenius, labuza, taoukis, deb, toth, hochreiter, ke, etc.
  datasheets/                # Gebru et al. per dataset (D1-D9)
  model-cards/               # Mitchell et al. per model
  adr/                       # architecture decisions (000-001)
  calibration/phi_env.md     # alpha/beta fit note
  reviews/phase-0-review.md  # P0 gate sign-off
freshroute-optimizer-model/
  api/app.py, routes.py, schemas.py   # FastAPI (Pydantic v2, OpenAPI 3.1)
  core/arrhenius_decay.py             # ThermalDecayEngine (P2)
  core/pareto_matcher.py              # ParetoMatchingEngine (P4)
  core/vrp_router.py                  # VRPRouter heuristic (P5 stub, OR-Tools wired)
  core/demand_forecaster.py           # HungerDemandForecaster stub → LightGBM/LSTM P3
  data/indian_commodities.json        # Tier priors + Phi params (citable)
  data/punjab_districts.json          # 23 districts + HVI
  data/ingestion/                     # agmarknet.py, imd_openmeteo.py
  tests/test_optimizer.py             # spec §6.2 must-pass
  tests/test_api.py                   # contract for spec §5
  requirements.txt + Dockerfile       # pinned, digest recorded at gate
src/
  App.jsx + components/               # React 18 + Leaflet console
  data/mockData.js                    # synthetic priors until P1 gold tables
  lib/freshrouteApi.js                # live → mock fallback client (P6 wiring)
```

## Citation & Reproducibility

```bash
# One-command replay
mise exec -- python -m pytest freshroute-optimizer-model/tests -q
mise exec -- python scripts/citation_audit.py --bib docs/BIBLIOGRAPHY.bib --root .
```

See `docs/reproducibility.md` (NeurIPS checklist, FAIR) and `CITATION.cff`. Datasheets and model cards per `docs/datasheets/TEMPLATE.md` `docs/model-cards/TEMPLATE.md`.

## Phase Gates (Implementation Plan)

- **P0 Charter** ✓ — scaffold + 42-key bibliography + audit green + 19 tests pass
- **P1 Data** → D1 Agmarknet, D2 IMD/Open-Meteo, D3 OSM/OSRM, D4 FSSAI, D6 MPI/NFHS/WFP → `data/gold/*.parquet` + Zenodo v0.1
- **P2 Kinetics** → Phi refit, `alpha=0.048 beta=0.008` field validation, hazard thresholds
- **P3 Forecaster** → LightGBM/LSTM 7-day WAPE<18% + HVI
- **P4 Matcher** → MILP/NSGA-II Pareto frontier vs greedy <100ms
- **P5 VRPTW** → OR-Tools with t_safe deadlines, vehicle tiering
- **P6 Integration** → sub-100ms OpenAPI, vite proxy, latency SLAs
- **P7 Field Pilot** → Ludhiana–Amritsar GT corridor, KPIs (≥95% spoilage prevention, 100% dietary)
- **P8 MLOps** → drift (PSI), retrain, Docker
- **P9 Paper** → bundle with DOI

## Ethics

Langar Rehat `Strict_Lacto_Vegetarian`, Halal, child/senior prioritization — hard gates in `core/pareto_matcher.py:check_dietary_eligibility`, 100% dietary compliance KPI. See `docs/datasheets/*.md` and ICMR 2017.

