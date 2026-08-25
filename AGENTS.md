# AGENTS.md — FreshRoute AI: Food Redistribution Optimizer

> **For human maintainers and AI agents continuing this repo.** Copy this file into your context before editing. It is the single source of truth for *where we are* (P0–P6 RC), *how to run*, and *how not to break publication guarantees*.

**Spec:** `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md:1` v1.0.0-Release | **Plan:** `docs/IMPLEMENTATION_PLAN.md:1` v1.0.0-Draft | **Bibliography:** `docs/BIBLIOGRAPHY.bib:1` 42 keys | **Commit:** `9a6fee3` (`docs: update README.md to a9025f8 RC (27 tests, P1-P6 RC, gold builders, replay.sh)`)

---

## 1. What this project is (30s)

Punjab ambient cold-chain food-rescue pipeline — 4 stages:

```
Agmarknet/IMD/FSSAI → Stage1 Arrhenius Phi_env (k(T), t_safe) → Stage2 Demand LSTM/LightGBM (HVI, 23 districts)
                                     ↓
                    Stage3 Pareto Matcher S_ij MILP w=[0.35,0.30,0.20,0.15]
                                     ↓
                    Stage4 VRPTW Router OR-Tools + vehicle tiering
                                     ↓
                         FastAPI → React Console (Vite + Leaflet)
```

Indian constraints are first-class: 44°C Loo, monsoon H>70%, `Strict_Lacto_Vegetarian` Langar Rehat + Halal/Jain hard gates (`spec:1.2`), `FSSAI` temps, NH44 GT corridor, Tata Ace EV / reefer tiers.

---

## 2. Tech stack & runtime

| Layer | Choice | Entrypoint |
| :--- | :--- | :--- |
| Python optimizer `3.11` | FastAPI `0.110` + Pydantic v2, OR-Tools `9.9`, PuLP, LightGBM `4.3`, Torch `2.3`, MLflow, Great Expectations | `freshroute-optimizer-model/api/app.py:1` `uvicorn api.app:app --reload --port 8000` |
| Frontend | React `18` + Vite `6` + Leaflet `1.9`, `lucide-react` | `src/App.jsx:1` `npm run dev` `0.0.0.0:3000` proxied `/api→8000` via `vite.config.js:7` |
| Data | `data/indian_commodities.json:1` (5 tiers), `data/punjab_districts.json:1` (23 HVI), ingestion stubs `data/ingestion/agmarknet.py:1` `imd_openmeteo.py:1` → `data/raw/` → `data/gold/*.parquet` (DVC) | `data/data_manifest.json:1` (FAIR SHA+DOI) |
| Tooling | `mise` `python@3.11` `node@26.7`, `pytest`, `citation_audit.py` | `mise.toml:1` `freshroute-optimizer-model/requirements.txt:1` `Dockerfile:1` |

---

## 3. Current state — Phase map `docs/IMPLEMENTATION_PLAN.md:4`

| Phase | Title | Status |
| :--- | :--- | :--- |
| **P0 Charter** | Ethics, doc infra | **DONE & gated** `docs/reviews/phase-0-review.md:1` — `BIBLIOGRAPHY.bib` 42, templates `docs/datasheets/TEMPLATE.md:1` `docs/model-cards/TEMPLATE.md:1`, ADRs `000:1`/`001:1`, `CITATION.cff:1`, `reproducibility.md:1`, `GANTT.md:1`, `calibration/phi_env.md:1` (`alpha=0.048 beta=0.008`) |
| **P1 Data** | Lake | **RC + live + GE** — 5-tier priors + 23 HVI done, `agmarknet.py:49` live POST+BS4 (synthetic 42 rows) + `_validate_rows`, `imd_openmeteo.py:44` live `open-meteo-live` 24h + `_validate_weather_rows`; `data/validation/ge_suites.py:1` 3 suites pass; `data/data_manifest.json:1` SHA computed for `indian_commodities.json`/`punjab_districts.json`/`forecaster_lgbm.txt`/`forecaster_lstm.pt`; `data/update_manifest.py:1` FAIR automation [@wilkinson2016fair]; Zenodo `v0.1` pending |
| **P2 Arrhenius** | `core/arrhenius_decay.py:272` | **Done (literature prior)** `ThermalDecayEngine` `Phi_env=exp(alpha*(T-20)+beta*max(0,H-60))` `t_safe` `CRITICAL_HAZARD≤4h`; field chamber fit pending monsoon pilot `C6` |
| **P3 Forecaster** | `core/demand_forecaster.py:31` | **DONE LGBM+LSTM v1** `HungerDemandForecaster` 23×7 deterministic + pilgrim surge + `train_lightgbm:359` WAPE 4.38% / `train_lstm:529` WAPE 4.22% [@ke2017lightgbm;@hochreiter1997lstm] (120d syn, 19 feats LGBM 300 trees, LSTM 2-layer 64 hidden +8 emb 20 epochs) `pilgrim_recall 0.85/0.82`, `data/gold/forecaster_lgbm.txt` 802KB + `forecaster_lstm.pt` 236KB + `docs/model-cards/demand_forecaster.md:1`; TFT `[@lim2021tft]` still stub, HVI fusion via `get_deficit_score` into matcher `w2` ready |
| **P4 Matcher** | `core/pareto_matcher.py:335` | **DONE MILP** `rank_allocations:260` `<100ms` + `check_dietary_eligibility:94` 100% gate; `solve_milp_allocations:337` PuLP CBC default + CP-SAT fallback `[@wolsey1998integer;@orgtools2024;@pulp2011]` <800ms N=100 (163ms), capacity aggregate, `docs/model-cards/pareto_matcher.md:1` + `adr/002:1` |
| **P5 VRP** | `core/vrp_router.py:63` | **DONE VRPTW + OSRM** `VEHICLE_TIERS:39` + `select_vehicle:82` + `solve_vrp:182` OR-Tools `RoutingModel` with `t_safe` windows + `λ=2.0` + `_get_osrm_distance_matrix:27` live OSRM `[@osm2024;@osrm2024]` (fallback haversine), `docs/model-cards/vrp_router.md:1` + `adr/003:1` |
| **P6 Gateway** | `api/` | **Done + MILP/VRPTW flags** `schemas.py:173` `SurplusBatch/RecipientNode spec:186` + `routes.py:125` 4 routers + MILP `use_milp/solver/min_score` + VRPTW `use_or_tools/t_safe_hours/lambda` + `src/lib/freshrouteApi.js:1` `withFallback()` |
| **P7 Pilot** | Field (GT corridor) | **Not started** — requires `P1` live + `P2` refit + BLE `spec:534`; KPIs `spec:6.1` `≥95% spoilage prevention` `100% dietary/cold-chain` unmeasured |
| **P8 MLOps** | Deploy | **Not started** — Cloud Run `PSI>0.2` drift `C1`, TF `Dockerfile:1` ready |
| **P9 Paper** | Bundle | **Not started** — Zenodo DOIs `P1/P2/P6/P7` + `replay.sh` `[@neurips2023checklist]` |

**Outer gates:** `P0` `Proceed` signed; `P1-P6` inner loops green, outer gates await reviewer signatures per `docs/IMPLEMENTATION_PLAN.md:12` (BIB 42 ok, 19 tests ok, model cards DONE for P2/P4/P5, stub for P3).

---

## 4. How to run (one-command replay `docs/reproducibility.md:1`)

```bash
# Backend — freshroute-optimizer-model is the Python root
mise use python@3.11
cd freshroute-optimizer-model
python -m venv .venv && source .venv/bin/activate   # or: mise exec -- pip ...
pip install -r requirements.txt

# Ingestion (synthetic until live keys)
python -m data.ingestion.agmarknet --date 2026-08-18 --out data/raw/agmarknet/20260818.json
python -m data.ingestion.imd_openmeteo --lat 30.90 --lon 75.85 --date 2026-08-18

# Verify (19 tests)
python -m pytest tests/ -v
python scripts/citation_audit.py --bib ../docs/BIBLIOGRAPHY.bib --root ..

# Serve (reload)
uvicorn api.app:app --reload --port 8000
# → http://localhost:8000/health  http://localhost:8000/docs  http://localhost:8000/openapi.json

# Frontend — repo root in another shell
npm install
npm run dev -- --host 0.0.0.0 --port 3000
# → http://localhost:3000  http://localhost:3000/#console  (vite proxy /api→8000)
# If API down, src/lib/freshrouteApi.js falls back to src/data/mockData.js:1 mocks so landing never blanks.
```

**PM2/nohup helpers** (already used once): `nohup mise exec -- uvicorn ... > /tmp/freshroute-api.log 2>&1 &`, `nohup mise exec -- npm run dev > /tmp/freshroute-vite.log 2>&1 &`.

**Docker**

```bash
cd freshroute-optimizer-model
docker build -t freshroute-optimizer-api:1.0-rc -f Dockerfile .
docker run -p 8000:8000 freshroute-optimizer-api:1.0-rc
```

---

## 5. Repository map (commit `a9025f8`)

```
freshroute/
├── docs/
│   ├── FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md   # frozen spec (k(T), Phi_env, S_ij, tiering, schemas, KPIs)
│   ├── IMPLEMENTATION_PLAN.md                     # 10 phases + inner/outer loops + DoD
│   ├── BIBLIOGRAPHY.bib                           # 42 keys: arrhenius1889, labuza*, deb2002nsga2, toth2014vrp, hochreiter1997lstm, etc.
│   ├── CITATION.cff (root)                        # Zenodo concept DOI
│   ├── GANTT.md, reproducibility.md
│   ├── datasheets/{TEMPLATE.md, agmarknet.md, open_meteo_imd.md, punjab_districts.md}
│   ├── model-cards/{TEMPLATE.md, arrhenius.md, pareto_matcher.md, vrp_router.md, demand_forecaster.md}
│   ├── calibration/phi_env.md                      # alpha/beta provenance
│   ├── adr/{000-record-architecture-decisions.md, 001-phase0-scaffold-and-gate.md, 002-p4-milp-solver-choice.md, 003-p5-vrptw-ortools-choice.md}
│   └── reviews/phase-0-review.md
├── freshroute-optimizer-model/
│   ├── api/{app.py, routes.py, schemas.py}         # FastAPI 4 routers, Pydantic v2, CORS, alias /predict/match (MILP+VRPTW flags)
│   ├── core/{arrhenius_decay.py, pareto_matcher.py, vrp_router.py, demand_forecaster.py, __init__.py}
│   ├── data/{indian_commodities.json, punjab_districts.json, data_manifest.json, ingestion/{agmarknet.py, imd_openmeteo.py}, raw/ (gitignored), gold/ (gitignored)}
│   ├── tests/{test_optimizer.py (13, spec:6.2 must), test_api.py (6, spec:5), conftest.py}
│   ├── scripts/citation_audit.py
│   ├── requirements.txt, Dockerfile, .venv (mise python@3.11)
├── scripts/citation_audit.py                       # root mirror (canonical)
├── src/{App.jsx:1, data/mockData.js:1 (498 lines synthetic), lib/freshrouteApi.js:1, components/*, main.jsx}
├── vite.config.js                                  # proxy /api + /health + /docs → :8000
├── mise.toml                                       # python@3.11
├── .gitignore                                      # **/data/raw, **/data/gold, *.parquet, .venv, mlruns
└── README.md                                       # quickstart + layout
```

---

## 6. Conventions that will fail CI / gate if broken

* **Citation debt is blocking** `docs/IMPLEMENTATION_PLAN.md:3.2`. Every numeric constant (`alpha`, `beta`, `Ea/R`, `w_i`, capacities) must `[@key]` to `BIBLIOGRAPHY.bib` or `docs/calibration/*.md`. `python scripts/citation_audit.py --bib docs/BIBLIOGRAPHY.bib --root .` must be `TODO 0 | unknown 0` (`[pass] citation audit green`). The script skips `citation_audit.py` itself and `zenodo.XXXX` DOI placeholders — do not add `TODO.*cite` or `FIXME`.
* **No code without datasheet/model-card** `docs/IMPLEMENTATION_PLAN.md:12` — every dataset `docs/datasheets/<slug>.md` (Gebru), every model `docs/model-cards/<model>.md` (Mitchell) before gate. `data_manifest.json` SHA per gold file.
* **Tests are frozen** `tests/test_optimizer.py:12` `test_arrhenius_heatwave_spoilage` (`Dairy @44C decay≥3.0 → CRITICAL_HAZARD`) and `test_dietary_compatibility_rejection` (`Strict_Lacto_Vegetarian non-veg → 0.0`) must stay green. Core `pytest` `19 passed` is minimum; API `p95 <100ms matcher`, `p95 <20ms shelf-life`.
* **Paths** — run Python from `freshroute-optimizer-model` with `mise exec` so `from core.*`/`from api.*` resolves ( `api/routes.py:16` and `api/app.py:10` inject `_root` onto `sys.path`). `tests/conftest.py:1` does same for bare `pytest`. Do not rename `freshroute-optimizer-model` (hyphen → not importable, `adr/001:1` explains).
* **Units** — spec is **kg + °C**, mock is **lbs + °F**. `api/schemas.py:1` `SurplusBatch._coerce_weight` `lbs→kg /2.20462`; frontend `src/lib/freshrouteApi.js:1` handles both. Keep conversion there, not in `core/`.
* **Diet is hard fail** `core/pareto_matcher.py:94` `check_dietary_eligibility` — zero tolerance, never silently rank non-veg to Langar; audit logs required (`C2` `docs/IMPLEMENTATION_PLAN.md:6`).
* **ADR for any spec deviation** `docs/adr/000:1` — changing `w_i`, `Phi` formula, or greedy→MILP as default requires `docs/adr/NNN-*.md`.

---

## 7. What to do next (ordered)

1. **P1 live** — *near-DONE* `agmarknet.py:49` + `imd_openmeteo.py:44` live, `ge_suites.py:1` 3 suites pass, `data_manifest.json:1` SHA `f869...`/`ca13...`/`3d6b...`/`66c6...`; remaining: backfill `mandi_daily.parquet`/`weather_hourly.parquet` gold + `osm_distance_matrix.parquet` D3, then Zenodo `v0.1` draft.
2. **P2 refit** — chamber lab 20/32/38/44°C×60/80% RH per `docs/calibration/phi_env.md:3` → refit `alpha/beta` + tier `Ea/R`, update `model-cards/arrhenius.md` CI bars.
3. **P3 train** — *DONE LGBM+LSTM* `train_lightgbm:359` WAPE 4.38% + `train_lstm:529` WAPE 4.22% (120d syn, 19/12 feats) `pilgrim_recall 0.85/0.82` `[@ke2017lightgbm;@hochreiter1997lstm]`; next: TFT `[@lim2021tft]` stretch + HVI fusion benchmark in matcher `w2` (spec 4.1 L3.3) + `get_deficit_score` already wired.
4. **P4 frontier** — *DONE* PuLP/OR-Tools CP-SAT `solve_milp_allocations:337` vs greedy `rank_allocations:260` benchmarked N=100 163ms optimal, capacity aggregate provenance; revisit `N=500` hypervolume vs `100ms` SLA per `docs/IMPLEMENTATION_PLAN.md:9.2` if needed.
5. **P5 OR-Tools** — *DONE* `RoutingModel` with `t_safe` windows + `λ=2.0` `spec:3.2`; next: live OSRM `D3` distance matrix + `lambda` grid [0.5,5] + Solomon `solomon1987` benchmark.
6. **P7 pilot** — shadow + 2-donor×2-recipient `Ludhiana–Amritsar` live with BLE `spec:7:534` telemetry, KPI `≥95%` spoilage prevention dashboard.
7. **Docs/paper** — start `P9` `paper/` LaTeX using `BIBLIOGRAPHY.bib`, `replay.sh` per `reproducibility.md`.

---

## 8. Gotchas already solved

* `mise.toml:1` pins `python@3.11` — vanilla `python3` on runners is `3.14` without `pip`/`pytest`; always `mise exec -- python …`.
* `data/raw` appears untracked until `.gitignore:28` uses `**/data/raw/` (slash in middle → root-relative otherwise). Already fixed `9b474f3`.
* `citation_audit.py` false-positive on `zenodo.XXXX` and `rg -n "TODO.*cite"` — patched to skip `citation_audit.py` and DOI lines.
* Import hygiene — `api/*.py:16` prepend `_root` to `sys.path` so `uvicorn api.app:app` works from both `freshroute-optimizer-model` and repo root.

---

## 9. Contacts & lineage

* Author line `CITATION.cff:1` `FreshRoute AI Architecture Core` — MoUs pending with SGPC Langar / Verka / Mandi boards (ethics `ICMR 2017` `docs/BIBLIOGRAPHY.bib:icmr2017ethics`).
* Prior synthetic truth `src/data/mockData.js:1` `DONORS/RECIPIENTS/FLEET/MATCHES/DISTRICT_DEMAND_FORECAST/AI_INTEGRATION_ENDPOINTS` — kept as fallback until `data/gold/*.parquet` replaces it.

*Do not expand scope without an ADR. Keep this file and `docs/IMPLEMENTATION_PLAN.md` in sync — next agent, update this section when you close a phase.*
