# AGENTS.md — FreshRoute AI: Food Redistribution Optimizer

> Maintainer and agent guide. This file describes the verified state of the repository at commit `d62462e` (`docs(screenshots): capture authentic browser PNG screenshots and update README showcase`, 2026-08-26). Keep it synchronized with `docs/IMPLEMENTATION_PLAN.md` and update the status section when work closes a gate.

## 1. What the project does

FreshRoute is a Punjab-focused food-rescue optimizer and operations-console prototype. It models the path from perishable surplus to a feasible, culturally compliant delivery:

```text
Agmarknet / weather / FSSAI inputs
        ↓
1. Thermal safety: Arrhenius decay + humidity → Phi_env, t_safe, hazard class
        ↓
2. Demand: LightGBM/LSTM-style 7-day forecasts for 23 districts + HVI deficit
        ↓
3. Matching: Pareto score and optional MILP allocation with dietary hard gates
        ↓
4. Routing: vehicle tier selection and OR-Tools VRPTW with OSRM/haversine distances
        ↓
FastAPI/OpenAPI gateway → React/Vite/Leaflet operations console
```

The domain constraints are part of the design, not presentation-only features: Punjab heatwave conditions around 44°C, monsoon humidity, FSSAI temperature bands, NH44 corridor logistics, reefer tiers, and zero-tolerance dietary compatibility for `Strict_Lacto_Vegetarian`, vegetarian, Jain, and Halal recipients. The matcher must never route an ineligible batch to a recipient merely to improve a score.

This is currently a reproducible research/demo system with synthetic defaults and simulation results. It is not yet a field-proven or production-operated dispatch service.

## 2. Repository and runtime

| Area | Location | Notes |
| --- | --- | --- |
| Frozen specification and plan | `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md`, `docs/IMPLEMENTATION_PLAN.md` | Mathematical formulas, schemas, KPIs, phase gates |
| Backend | `freshroute-optimizer-model/` | Python 3.11; run from this directory for direct imports |
| Core engines | `freshroute-optimizer-model/core/` | `arrhenius_decay.py`, `demand_forecaster.py`, `pareto_matcher.py`, `vrp_router.py` |
| API | `freshroute-optimizer-model/api/` | FastAPI app, Pydantic v2 schemas, four primary routes plus health/alias routes |
| Data | `freshroute-optimizer-model/data/` | 5 commodity tiers, 23 district/HVI records, ingestion/build scripts, DVC pointers |
| Frontend | `src/` | React 18 + Vite + Leaflet; `OperationsApp` is the interactive console |
| Frontend fallback | `src/data/mockData.js`, `src/lib/freshrouteApi.js` | The UI remains usable when the API is unavailable |
| Reproducibility | `replay.sh`, `docs/reproducibility.md`, `scripts/citation_audit.py` | Full replay and citation governance |
| Publication | `paper/main.tex`, `docs/BIBLIOGRAPHY.bib` | Manuscript source and 42-key bibliography |
| CI/quality | `.github/workflows/ci.yml`, `.pre-commit-config.yaml` | Python tests, GE, forecaster smoke, Monte Carlo, citation audit |

The pinned toolchain is `mise.toml` (`python = "3.11"`). Python dependencies are in `freshroute-optimizer-model/requirements.txt`; frontend dependencies are in `package.json`. There is a backend Dockerfile at `freshroute-optimizer-model/Dockerfile`. An `environment.lock` file is not currently committed; `.gitignore` ignores that filename.

## 3. Current phase status

The phase reviews document “Proceed” decisions through P6, but their reviewer/sign-off sections are not fully completed. Treat the system as an RC/demo with open outer-gate and field-validation work.

| Phase | Verified state |
| --- | --- |
| **P0 — Charter** | Documentation, bibliography, ADRs, templates, calibration note, and reproducibility scaffolding exist. Formal sign-offs remain open in the review artifact. |
| **P1 — Data** | Commodity and district priors, 9 datasheets, GE checks, manifest, DVC pointers, and gold-table builders exist. Agmarknet/Open-Meteo adapters attempt live fetches but intentionally fall back to deterministic synthetic rows. Gold parquet/model binaries are ignored locally and represented by DVC pointers; manifest DOI fields are still pending/placeholders. |
| **P2 — Thermal decay** | `ThermalDecayEngine` is implemented and API-exposed. The `Phi_env` prior and demo refit pass the heatwave regression, but chamber/field validation and seasonal refitting of `alpha`/`beta` remain outstanding. |
| **P3 — Demand** | LightGBM and LSTM training/forecast code, prediction bounds, HVI deficit scoring, metrics, and model artifacts/metadata exist. Reported WAPE is 4.38%/4.22% on synthetic history. `core/tft_stub.py` is deliberately a delegating stub, and real meal-consumption logs are not yet the training source. |
| **P4 — Matcher** | Greedy and PuLP MILP paths, OR-Tools fallback, capacity handling, OSRM-matrix lookup, and hard dietary gates exist. N=100 MILP is within the 800 ms budget; the current standalone 500×500 greedy benchmark is ~896 ms, so the plan’s `<100 ms @ N=500` SLA is not met. HVI benchmark uplift is currently 0 on the corridor because proximity and HVI align. |
| **P5 — Router** | Heuristic and OR-Tools VRPTW paths, 4 vehicle tiers, `t_safe` windows, lambda tuning, OSRM live attempt, and haversine fallback exist. Full Solomon benchmarking, true pickup/delivery precedence, per-tier timing, and production traffic/sensor inputs remain incomplete. |
| **P6 — Gateway/UI** | Four primary APIs and OpenAPI are implemented: shelf life, match, forecast, and routing. The console has map, queue, thermal matrix, 23-district forecast, scenarios, live health polling, API sandbox, and greedy/MILP controls. It is resilient through API fallback; it is not an authenticated/hosted production gateway. |
| **P7 — Pilot** | Shadow-mode, real-data-simulation, and Monte Carlo scripts exist and pass the synthetic KPI checks. The planned live 2-donor × 2-recipient GT-corridor pilot, BLE/MQTT telemetry, human-factor review, and signed P7 review do not exist yet. |
| **P8 — MLOps** | CI, pre-commit configuration, DVC pointers, and a synthetic PSI drift script exist. Production deployment, dashboards/alerts, automatic retraining/refit, infrastructure-as-code, rollback validation, environment lock, and maintainer runbook are still absent. |
| **P9 — Paper** | `paper/main.tex` and `replay.sh` exist with draft results. PDF rendering, clean-clone artifact verification, real data/code Zenodo deposits, final DOIs, and `CITATION.cff` release cross-references remain outstanding. |

## 4. API and UI contract

Backend routes are mounted under `/api/v1`:

- `POST /api/v1/predict/shelf-life`
- `POST /api/v1/optimize/match`
- `GET` or `POST /api/v1/forecast/demand`
- `POST /api/v1/optimize/routing`
- `GET /health` and `GET /openapi.json`

`api/schemas.py` accepts the spec’s kg/°C fields and the frontend mock’s legacy lbs weight alias; the UI also presents some telemetry in °F. Normalize units at the API/schema boundary; do not add lbs/°F conversion to the core engines. Coordinates are `[latitude, longitude]` in application payloads; OSRM requests reverse them to `[longitude, latitude]` as required by that service.

The frontend uses the Vite proxy for `/api` and `/health`. `withFallback()` in `src/lib/freshrouteApi.js` falls back to `src/data/mockData.js` when FastAPI is down. Do not mistake fallback data or UI scenario changes for live operational data.

## 5. How to run

From the repository root:

```bash
# Install backend dependencies
cd freshroute-optimizer-model
mise exec -- python -m pip install -r requirements.txt

# Verify backend, integration, and GE behavior
cd ..
mise exec -- python -m pytest freshroute-optimizer-model/tests/ -q
mise exec -- python scripts/citation_audit.py --bib docs/BIBLIOGRAPHY.bib --root .

# Build the frontend
npm install
npm run build
```

Run the backend from its Python root:

```bash
cd freshroute-optimizer-model
mise exec -- uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in a second shell from the repository root:

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

Open `http://localhost:3000/#console`, `http://localhost:8000/docs`, and `http://localhost:8000/health`.

Build synthetic gold tables when needed by tests or local experiments:

```bash
cd freshroute-optimizer-model
mise exec -- python scripts/build_gold_mandi.py --date 2026-08-18
mise exec -- python scripts/build_gold_weather.py --lat 30.9 --lon 75.85 --date 2026-08-18
mise exec -- python scripts/build_gold_osm.py
```

`bash replay.sh` runs the full eight-step replay, including generated/ignored gold data and manifest synchronization. It can change ignored data and update the tracked manifest, so inspect `git diff` afterward. The real-feed helpers are `scripts/fetch_real_mandi.py` and `scripts/fetch_real_weather.py`; they require network access and must not silently be treated as proof of field provenance.

## 6. Verified checks at this snapshot

Run on 2026-08-26 from this workspace:

- `mise exec -- python -m pytest freshroute-optimizer-model/tests/ -q`: **29 passed**; warnings include HTTPX, Torch/NVML, and Great Expectations deprecations.
- `mise exec -- python scripts/citation_audit.py --bib docs/BIBLIOGRAPHY.bib --root .`: **0 TODO-cite, 0 unresolved bibliography keys**.
- `npm run build`: **passed** with Vite production output.
- API latency script: shelf-life p95 **2.6 ms**, greedy match p95 **2.4 ms**, heuristic routing p95 **3.1 ms**, forecast p95 **17.2 ms**.
- Standalone matcher scale benchmark: greedy N=500 **~896 ms** (fails the planned `<100 ms` target); MILP N=100 **~254 ms** in this run (within the `<800 ms` budget).
- HVI fusion benchmark: **0 uplift** on the current 12-pair corridor fixture; this is a limitation of the fixture, not evidence that the equity objective has no effect generally.
- Lambda grid: all tested 5-stop synthetic routes feasible; a full Solomon instance was not run.

## 7. Work that needs to be done, in priority order

1. **Make data provenance real.** Capture and retain real Agmarknet and weather pulls, validate source/row provenance, complete the gold DVC workflow, replace placeholder/pending DOIs, and make synthetic-vs-real status explicit in manifests and model cards.
2. **Validate thermal safety.** Run the planned 20/32/38/44°C × 60/80% RH chamber or field study, fit confidence intervals for `alpha`, `beta`, and tier parameters, and update `docs/calibration/phi_env.md` and `docs/model-cards/arrhenius.md`.
3. **Replace synthetic demand assumptions.** Train/evaluate against real district meal demand and pilot logs, validate prediction intervals and seasonal performance, and either implement a real TFT model or remove the misleading stub path from the supported-model surface.
4. **Resolve matcher scale and fairness evidence.** Profile the 500×500 greedy path, then optimize/index it or revise the SLA through an ADR. Add fixtures where HVI and proximity conflict, measure fairness trade-offs, and preserve zero-tolerance dietary/audit behavior.
5. **Finish routing validation.** Run the available Solomon data through the benchmark, implement true pickup-and-delivery precedence and per-tier travel times, verify that every infeasible/fallback route is surfaced as unsafe, and document OSRM availability/road-distance provenance.
6. **Run the field pilot.** Obtain domain partner approval, operate the 2×2 Ludhiana–Amritsar/Jalandhar shadow-to-live pilot, collect calibrated BLE/MQTT temperature and weighbridge/consumption logs, perform human/diet audits, and sign `docs/reviews/phase-7-review.md`.
7. **Harden operations.** Add authentication/authorization, durable audit logs, deployment/IaC, monitoring and alerting, retraining/refit jobs, locked environments, rollback procedures, and an on-call runbook. Keep the offline UI fallback but label it clearly as simulated.
8. **Close publication gates.** Render and review the paper, reproduce results from a clean checkout, deposit code/data artifacts with real Zenodo DOIs, update `CITATION.cff`, and complete technical/domain reviewer signatures for the phase reviews.

## 8. Non-negotiable engineering rules

- Keep `test_arrhenius_heatwave_spoilage` and `test_dietary_compatibility_rejection` green. The dietary gate is a hard safety/cultural constraint, not a ranking preference.
- Every new numeric constant, dataset, model, or external source needs a bibliography entry or dated calibration note, a datasheet/model card where applicable, and a passing citation audit.
- Any change to `Phi_env`, weights `w=[0.35, 0.30, 0.20, 0.15]`, vehicle capacities/tiers, solver defaults, unit semantics, or frozen API contracts requires an ADR under `docs/adr/`.
- Keep the spec in kg and °C internally. Preserve compatibility conversion only at `api/schemas.py`/client boundaries.
- Keep raw and gold binaries out of Git; retain DVC pointers, manifest hashes, retrieval metadata, and reproducible builder/fetch scripts.
- Treat OSRM and external ingestion as fallible. Preserve deterministic fallbacks for tests, but surface `source`, fallback, stale-data, and unsafe-route state to operators.
- Do not claim synthetic simulation KPIs as field outcomes. Model cards must state the data source, geography, calibration limits, and fallback behavior.
- Run Python with `mise exec --` and respect the `freshroute-optimizer-model` directory name; its hyphen means it is a source root, not a normal importable package.
- Do not expand scope or alter frozen objectives without an ADR and corresponding documentation/review update.

## 9. Useful references

- Specification: `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md`
- Plan and phase definitions: `docs/IMPLEMENTATION_PLAN.md`
- Reproduction: `docs/reproducibility.md` and `replay.sh`
- Data manifest: `freshroute-optimizer-model/data/data_manifest.json`
- Model cards: `docs/model-cards/`
- Dataset datasheets: `docs/datasheets/`
- Architecture decisions: `docs/adr/`
- Phase reviews: `docs/reviews/`
- Public/demo documentation and screenshots: `README.md` and `screenshots/`

*Do not expand scope without an ADR. Keep this file and `docs/IMPLEMENTATION_PLAN.md` in sync.*
