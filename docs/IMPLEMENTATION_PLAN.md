# FreshRoute AI: Food Redistribution Optimizer — Phased Implementation Plan

**Companion to:** `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md` v1.0.0-Release
**Plan Version:** 1.0.0-Draft — 2026-08-24
**Lifecycle Model:** Phase-Gate with Nested Iterative Loops (Inner Sprint Loop + Outer Validation Loop + Cross-Cutting Governance Loops)
**Publication Target:** Peer-reviewed journal (Nature Food / J. Cleaner Production / ACM COMPASS) + Open-science artifact with DOI
**License for Artifacts:** Code MIT, Data CC-BY-4.0 / ODbL (OSM) compatible, Paper CC-BY

---

## Table of Contents

1. [Executive Summary & Guiding Principles](#1-executive-summary--guiding-principles)
2. [Reference Architecture Recap](#2-reference-architecture-recap)
3. [Documentation & Citation Governance (Publication-Grade)](#3-documentation--citation-governance-publication-grade)
4. [Phase Map Overview](#4-phase-map-overview)
5. [Detailed Phase Breakdown with Loops](#5-detailed-phase-breakdown-with-loops)
6. [Cross-Cutting Continuous Loops](#6-cross-cutting-continuous-loops)
7. [Dataset Registry & Datasheet Obligations](#7-dataset-registry--datasheet-obligations)
8. [Literature & Theory Citation Corpus (by Module)](#8-literature--theory-citation-corpus-by-module)
9. [Evaluation Framework & KPI Hierarchy](#9-evaluation-framework--kpi-hierarchy)
10. [Risk, Ethics & Mitigation Matrix](#10-risk-ethics--mitigation-matrix)
11. [Timeline, Milestones & RACI](#11-timeline-milestones--raci)
12. [Definition of Done per Phase Gate](#12-definition-of-done-per-phase-gate)
13. [Appendices](#13-appendices)

---

## 1. Executive Summary & Guiding Principles

This plan operationalizes the 4-stage optimizer specified in `FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md:19-62`:

1. `core/arrhenius_decay.py:272-322` — Dynamic Arrhenius Expiry & Safe Transit Window
2. `core/demand_forecaster.py` — Spatial-Temporal LSTM/LightGBM Hunger Forecaster (23 Punjab districts)
3. `core/pareto_matcher.py:335-419` — Multi-Objective Pareto Surplus-to-Recipient Matcher (MILP)
4. `core/vrp_router.py` — Cold-Chain Vehicle Assignment & VRPTW via OR-Tools

**Why phases + loops:** Food redistribution under Indian ambient logistics is non-stationary (44°C Loo, monsoon H>70%, mandi seasonality, Langar pilgrim surges). A single waterfall build will overfit to a single climate window. Phases provide gate-controlled maturity; loops provide climate-season coverage, data-drift correction, and community-feedback integration.

### 1.1 First Principles

| Principle | Operationalization | Audit Artifact |
| :--- | :--- | :--- |
| **Reproducibility (NeurIPS Checklist)** | Seeded RNGs, pinned `requirements.txt`, Docker digest, DVC-tracked data | `reproducibility.md` + MLflow run bundle |
| **FAIR Data (Wilkinson et al. 2016)** | Findable DOI via Zenodo, Accessible API, Interoperable JSON schemas (§3.2 in spec), Reusable CC-BY | `data/<dataset>/datasheet.md` |
| **Datasheets & Model Cards** | Every dataset → Gebru et al. 2021 template; every model → Mitchell et al. 2019 template | `docs/datasheets/`, `docs/model-cards/` |
| **Verifiability** | Spec §6 KPIs frozen; CI executes `tests/test_optimizer.py:511-525` on every commit | GitHub Actions + pytest badge |
| **Community Grounded** | FSSAI, Langar Rehat, Halal boards co-sign dietary matrix `§1.2` | Ethics annex + MoU logs |
| **Minimal Citation Debt** | No dataset, parameter, or constant without a citable source or lab calibration note | `docs/BIBLIOGRAPHY.bib` + citation audit table |

### 1.2 Loop Taxonomy Used Throughout

```
OUTER LOOP (Phase Gate):  Plan → Execute Loops → Peer Review → Citation Audit → Gate Decision (Proceed / Iterate / Abort)
        │
        └─ INNER LOOP (Sprint, 1-2 weeks):  Research → Prototype → Test → Document → Demo
                    │
                    └─ MICRO LOOP (Day): Code → Unit Test → Log (MLflow/DVC) → Push
```

- **Inner Loop** velocity: 1–2 weeks, exits with a tagged pre-release.
- **Outer Loop** cadence: end of each Phase (4–6 weeks), exits with peer review + artifact DOI.
- **Cross-Cutting Loops** (always-on, §6): Data drift watch, ethics/diets review, latency/regression watch.

---

## 2. Reference Architecture Recap

```
[Agmarknet §3.1] --┐
[IMD / Open-Meteo] --┼─> STAGE 1 Arrhenius (Phi_env, t_safe) ─> STAGE 2 Demand LSTM/LGBM (HVI, surge)
[FSSAI / Dietary] --┘                                            │
                                                                 v
                                              STAGE 3 Pareto Matcher (S_ij, MILP, w=[0.35,0.30,0.20,0.15])
                                                                 │
                                                                 v
                                              STAGE 4 VRPTW Router (OR-Tools, Vehicle Tiering Matrix §3.1)
                                                                 │
                                                                 v
                                              FastAPI Gateway (/api/v1/predict/shelf-life, /optimize/match)
                                                                 │
                                              Frontend Console (src/App.jsx:292, OperationsApp) + Driver App
```

**Frozen interfaces:** JSON schemas `SurplusBatch` and `RecipientNode` (`spec §3.2`), REST contracts `§5.1-§5.2`, directory layout `spec §4.1`.

---

## 3. Documentation & Citation Governance (Publication-Grade)

### 3.1 Documentation Stack

| Layer | Tool | Location | Rule |
| :--- | :--- | :--- | :--- |
| Literature registry | BibTeX + Zotero group | `docs/BIBLIOGRAPHY.bib` | Every `α=0.048`, `β=0.008`, `Ea/R`, `w_i`, vehicle capacity must cite line in `.bib` |
| Dataset datasheet | Gebru et al. template | `docs/datasheets/<name>.md` | Compulsory before ingestion; includes license, PII risk, sampling bias |
| Model card | Mitchell et al. template | `docs/model-cards/<model>.md` | Intended use, limits (e.g., “not validated >48°C”), metrics by tier |
| Experiment log | MLflow + DVC | `mlruns/`, `data.dvc` | One run = one config hash; no “final model” without MLflow ID |
| ADR | Architecture Decision Record | `docs/adr/NNN-title.md` | Any deviation from spec (e.g., replacing MILP with NSGA-II) requires ADR |
| API docs | OpenAPI 3.1 via FastAPI | `api/openapi.json` | Auto-generated, versioned per release |
| Provenance | Zenodo DOI + Git tag | `CITATION.cff` | Paper cites code DOI, not bare GitHub URL |

**Citation style:** Chicago author-date for paper narrative; BibTeX keys `labuza1993shelflife`, `arrhenius1889` etc. in `BIBLIOGRAPHY.bib`, rendered bibliography section in each deliverable.

### 3.2 Citation Audit Protocol (At Every Outer Loop Gate)

1. `rg -n "TODO.*cite|FIXME|XXX"` must be 0.
2. Every numeric constant in `core/*.py:264-273` traces to `BIBLIOGRAPHY.bib` or `docs/calibration/<food>.md` lab note.
3. `scripts/citation_audit.py` parses `BIBLIOGRAPHY.bib` and checks every `\cite{}` / `[@key]` resolves.
4. External reviewer signs `docs/reviews/phase-N-review.md`.

### 3.3 Reproducibility Package (Per Phase)

```
freshroute-paper-bundle/
├── paper.pdf
├── BIBLIOGRAPHY.bib
├── data_manifest.json   # hashes + DOIs for every external pull
├── environment.lock     # pip freeze + docker image digest
├── mlruns/              # selected runs
└── replay.sh            # one-command reproduction of KPIs §6.1
```

---

## 4. Phase Map Overview

| Phase | Title | Primary Spec Module | Duration | Outer Gate Deliverable | DOI? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | Project Charter, Ethics & Doc Infra | All | 2 wks | `CITATION.cff`, `BIBLIOGRAPHY.bib`, datasheet/model-card templates, IRB/MoU | No |
| **P1** | Data Foundation & Ingestion Loop | §3 | 4–5 wks | Versioned lake `data/` + 7 datasheets + Great Expectations suite | Zenodo v0.1 |
| **P2** | Module 1 — Arrhenius Decay Kinetics Engine | §2.1–2.3 / `arrhenius_decay.py` | 4 wks | Calibrated `ThermalDecayEngine` + lab validation report + model card | Zenodo v0.2 |
| **P3** | Module 4 — Spatial-Temporal Demand Forecaster | §4.1 / `demand_forecaster.py` | 5 wks | LSTM & LightGBM baselines + HVI + 7-day forecast API + model card | — |
| **P4** | Module 2 — Pareto Matcher (MILP) | §2.1–2.2 / `pareto_matcher.py` | 4 wks | `ParetoMatchingEngine` + MILP solver proofs + fairness audit | — |
| **P5** | Module 3 — VRPTW & Vehicle Assignment | §3.1–3.2 / `vrp_router.py` | 4 wks | OR-Tools VRP with time windows + vehicle tiering optimizer + OSRM benchmark | — |
| **P6** | Pipeline Integration & FastAPI Gateway | §5 | 3–4 wks | Unified `api/app.py`, OpenAPI, sub-100ms latency proof | Zenodo v1.0-rc |
| **P7** | Verification, Field Pilot & Human Loop | §6 | 6 wks (monsoon overlap) | Punjab GT corridor pilot (Ludhiana–Amritsar–Jalandhar), human-in-the-loop eval, KPI dashboard | Zenodo v1.0 |
| **P8** | MLOps, Telemetry & Handover | §7 Phases 2-4 | 3 wks | Docker + CI/CD + IoT MQTT ingest + drift alerts + maintainer guide | — |
| **P9** | Publication & Open-Science Release | — | 4 wks (parallel) | Submitted paper + reproducibility bundle + datasets with DOIs | Paper DOI |

Dependency graph: `P0 → P1 → (P2 || P3) → P4 → P5 → P6 → P7 → P8`; `P9` starts at `P6` gate.

Each phase internally runs 2–4 **inner loops** (see §5).

---

## 5. Detailed Phase Breakdown with Loops

### Phase P0 — Project Charter, Ethics & Documentation Infrastructure

**Goal:** No code without citation/monitoring infra.

- **Inputs:** Spec v1.0.0, `src/data/mockData.js:1-498` as synthetic prior, university/publisher guidelines.
- **Inner Loops:**
  - **L0.1 Infra Loop (1 wk):** Init `freshroute-optimizer-model/` per `spec §4.1`; pin `requirements.txt` (FastAPI, Pydantic v2, OR-Tools, PuLP, LightGBM, PyTorch, MLflow, DVC, Great Expectations); `Dockerfile` with digest; `CITATION.cff` (Brand et al.).
  - **L0.2 Ethics & Diet Loop (1 wk):** Stakeholder mapping (SGPC Langar committee, Verka, mandi boards, child/senior homes); draft dietary constraint matrix formalization (`Strict_Lacto_Vegetarian` etc.); IRB/ethics checklist (WFP ethics, Indian ICMR guidelines); MoU templates. See Mitchell et al. on model cards for vulnerable groups.
- **Outputs:** `docs/BIBLIOGRAPHY.bib` seeded (§8), `docs/datasheets/TEMPLATE.md`, `docs/model-cards/TEMPLATE.md`, `docs/adr/000-record-architecture-decisions.md`, ethics annex.
- **Exit Criteria:** `pre-commit` hooks enforce `black`, `ruff`, `mypy`, `citation_audit.py`; CI green on mock-data contract tests.
- **Citations to lock:** Wilkinson et al. 2016 (FAIR), Gebru et al. 2021 (Datasheets), Mitchell et al. 2019 (Model Cards), Brand et al. (CITATION.cff).

---

### Phase P1 — Data Foundation & Ingestion Loop

**Goal:** Replace `src/data/mockData.js` with versioned, citable, quality-checked data.

- **Inputs:** External sources listed in `spec §3.1:179-182`; synthetic mocks as fallback.

- **Inner Loops (each loop adds one source family + GE tests):**

  - **L1.1 Agmarknet Mandi Loop (1.5 wks):**
    - Scraper/API: `https://agmarknet.gov.in/` daily arrivals, commodities, prices. Rate-limited, headless fetch with `data/ingestion/agmarknet.py`.
    - Coverage: Punjab mandis (Ludhiana, Amritsar, Jalandhar, Khanna, Bathinda, Patiala) × commodities Tier 3/5.
    - Datasheet obligations: provenance (Govt of India, OGD license), completeness gaps (weekend reporting lag), price vs quantity reconciliation.
    - Calibration artifact: mandi seasonality curve → feature for P3 forecaster.
  - **L1.2 Weather Telemetry Loop (1 wk):**
    - IMD gridded (0.25°) + Open-Meteo Archive API hourly `temp`, `humidity`, `uv_index`; fallback to `https://api.open-meteo.com/v1/forecast`.
    - Validation: compare IMD vs Open-Meteo bias for Punjab Loo days (>42°C); store correction factor.
    - Datasheet: spatiotemporal resolution, gapfill method (linear vs ERA5 reanalysis).
  - **L1.3 OSM / OSRM Routing Loop (1 wk):**
    - OSM Punjab extract via Geofabrik; OSRM India profile (car + truck). Precompute distance matrix for donor↔recipient pairs used in `pareto_matcher.py:339-345`.
    - License note: ODbL attribution + share-alike for derived distance matrix.
  - **L1.4 FSSAI & Dietary Standards Loop (0.5 wk):**
    - FSSAI Food Safety and Standards (Licensing) Regulations, Cold-chain appendix; permissible temps `spec §3.1:182` (milk ≤4°C, hot >65°C).
    - Also encode `Standardized JSON Schemas` `spec §3.2:186-226` as Pydantic v2 models `api/schemas.py`.
  - **L1.5 Hunger & Demographic Loop (1 wk):**
    - Census 2011 + projected 2026 (ORGI), NFHS-5 child nutrition, NITI Aayog MPI, WFP hunger maps → derive Hunger Vulnerability Index (HVI) per `spec §4.1` `punjab_districts.json` (23 districts).
    - Historical consumption: `mockData.js` `DISTRICT_DEMAND_FORECAST:403-449` as synthetic prior; replace with pilot logs when available.

- **Quality Gates (Great Expectations):**
  - `expect_temp_c_between_-10_55` , `humidity_0_100`, `distance_km>0`, `shelf_life_hours>0`, `dietary_flags` enum closed.
  - Data versioning: DVC + Git LFS; `data_manifest.json` with SHA256 per file.
- **Outputs:** `data/` lake (raw/bronze → silver → gold), 7 datasheets, `data/indian_commodities.json` with `Ea/R` initial priors, `data/punjab_districts.json` with HVI v0, nightly ingestion cron.
- **Exit Criteria:** All GE suites pass; ingestion replay from scratch reproduces identical gold tables; citation audit shows each source in `BIBLIOGRAPHY.bib` (see §7 row 1–7).
- **Key Citations:** Gebru et al. 2021; Wilkinson et al. 2016; OSM contributors; IMD; Agmarknet documentation.

---

### Phase P2 — Module 1: Dynamic Arrhenius Shelf-Life & Microbial Decay Predictor

**Goal:** Ship `core/arrhenius_decay.py:272-322` as calibrated, lab-grounded physics + humidity extension, not a toy exponential.

- **Theory anchor:** `k(T)=A·exp(-Ea/RT)` (`spec §2.1:94`) + `Φ_env(T,H)` (`spec §2.2:104`) + `t_safe` (`spec §2.3:117`).

- **Inner Loops:**

  - **L2.1 Literature Calibration Loop (1 wk):**
    - Extract `Ea/R`, `base_hours_at_20C`, `critical_temp_c` per Tier from:
      - Labuza & Fu 1997 kinetics, Taoukis et al. 1997 (TTI), Man & Jones Shelf Life (2000).
      - Dairy-specific: milk spoilage at ambient (Kumar & Prasad 2010; FSSAI milk hygiene survey).
      - Tier baselines in spec `§1.1` (Tier 1: 24–36h @20°C / 4–8h @38°C Loo etc.) are priors, not ground truth — propose to fit `α=0.048`, `β=0.008` from Punjab summer data, logging fit residuals.
    - Deliverable: `data/indian_commodities.json` with `Ea_over_R` + confidence intervals + source BibTeX key per commodity.
  - **L2.2 Controlled Validation Loop (1.5 wks):**
    - Lab or literature replication: incubate Tier samples at 20°C, 32°C, 38°C, 44°C × 60% vs 80% RH; plate counts / sensory failure times → fit `α, β` via non-linear least squares; report `R²`, RMSE on `t_safe`.
    - Edge: if lab unavailable, use published decay curves with explicit “secondary data” limitation in model card.
  - **L2.3 Hazard Classification Tuning Loop (1 wk):**
    - Thresholds `spec §2.3:117-119` (`t_safe ≤ t_transit+1h → CRITICAL_HAZARD`, `≤4h`, `≤12h`) tuned on precision/recall for spoilage prevention vs false criticals. Use `tests/test_optimizer.py:511-518` (`decay_multiplier ≥3.0 @44°C dairy`) as regression.
  - **L2.4 API Exposure Loop (0.5 wk):**
    - Implements `POST /api/v1/predict/shelf-life` (`spec §5.1:425-451`), Pydantic validation, <20ms p95, property tests (`hypothesis`).

- **Outputs:** `core/arrhenius_decay.py` with docstrings citing equations, `docs/model-cards/arrhenius.md`, `docs/calibration/<tier>.md` with fitted curves, Jupyter `notebooks/arrhenius_validation.ipynb` reproducible.
- **Exit Criteria:** Dairy `decay_multiplier ≥3.0` at 44°C/80% holds; RMSE on `t_safe` < 1.2h on validation; model card documents limits (e.g., not validated for frozen chain).
- **Key Citations:** Arrhenius 1889; Van’t Hoff Q10 model; Labuza & Schmidl 1985, Labuza & Fu 1993, Taoukis et al. 1997; FSSAI 2011 Regulations; Kumar et al. on Indian dairy spoilage (§8, Block A).

---

### Phase P3 — Module 4: Spatial-Temporal Neighborhood Demand Forecaster

**Goal:** 7-day meal shortfall forecast across 23 Punjab districts, with festive/pilgrim surges — proactive, not reactive (`spec §4.1`).

- **Inputs:** Gold tables from P1 (mandi seasonality, weather, HVI, 90-day moving avg meals), calendar features.
- **Inner Loops:**

  - **L3.1 Feature Engineering Loop (1.5 wks):**
    - Feature space `spec §4.1:168-172`: demography (density, informal settlement, MPI), calendar (Gurpurab, Diwali, Ramadan, Navratri, Langar schedules), weather telemetry, 90-day consumption.
    - Encode Gurpurab / pilgrim surge as binary + lead/lag windows; mandi glut as negative demand proxy.
    - Datasets cited: Census, NFHS, NITI MPI, Open-Meteo history.
  - **L3.2 Baseline & Model Loop (2 wks):**
    - Baselines: naïve seasonal, LightGBM (Ke et al. 2017) — fast, interpretable, handles categorical.
    - Sequence model: LSTM (Hochreiter & Schmidhuber 1997) with district embeddings; optional TFT (Lim et al. 2021) as stretch.
    - Train per-district vs global multi-task; walk-forward CV (expanding window) to avoid leakage; metrics RMSE, MAE, WAPE, coverage of prediction interval.
  - **L3.3 HVI Integration Loop (1 wk):**
    - HVI = weighted MPI + stock-hours + child/senior nutrition flags; fuse forecast deficit with HVI to rank `Deficit(j)` used by P4 matcher (`w2=0.30`).
    - Validate against `mockData.js:403-449` districts — gap `gapLbs` sign should correlate with HVI (Spearman ρ>0.6).
  - **L3.4 API & Drift Loop (0.5 wk):**
    - `GET /api/v1/forecast/demand` (`spec` mock `AI_INTEGRATION_ENDPOINTS:489-497`); return horizon, interval, HVI; monitor drift (PSI, ADWIN).

- **Outputs:** `core/demand_forecaster.py`, `docs/model-cards/demand_forecaster.md`, notebook with walk-forward results, `data/punjab_districts.json` updated.
- **Exit Criteria:** WAPE < 18% on 7-day horizon across districts; pilgrim surge weeks recall >0.75; latency <80ms for 23 districts.
- **Key Citations:** Hochreiter & Schmidhuber 1997 (LSTM); Ke et al. 2017 (LightGBM); Lim et al. 2021 (TFT); WFP Hunger Map; NITI Aayog MPI report (§8 Block D).

---

### Phase P4 — Module 2: Multi-Objective Pareto Surplus-to-Recipient Matcher

**Goal:** Implement `core/pareto_matcher.py:335-419` with strict feasibility, auditably weighted composite `S_ij` (`spec §2.1:128`), and optional MILP → Pareto frontier upgrade.

- **Inputs:** `t_safe` from P2, `Deficit(j)` from P3, distance matrix from P1, dietary matrix `spec §1.2`.

- **Inner Loops:**

  - **L4.1 Scoring & Constraint Loop (1 wk):**
    - Code `score_match()` (`spec §4.3:347-380`): `Urgency(i)=100-2.5*t_safe`, `Deficit(j)` = HVI-scaled, `Proximity=100-1.5*km`, `DietMatch` binary gate.
    - Strict constraints `spec §2.1:131-133`: `DietMatch==1.0`, `t_transit ≤ t_safe`, `Capacity≥Weight`. Unit test `test_dietary_compatibility_rejection:519-524` must pass (non-veg → Langar = 0.0).
    - Haversian `core/pareto_matcher.py:339-345` cross-checked vs OSRM.
  - **L4.2 Weight Elicitation & Sensitivity Loop (1 wk):**
    - Default `w=[0.35,0.30,0.20,0.15]` (`spec §2.2`) derived via Analytic Hierarchy Process (Saaty 1980) with stakeholder interviews; run Sobol sensitivity → rank `w_urgency > w_deficit`.
    - Log alternative weight sets in MLflow; publish Pareto frontier exploration capability.
  - **L4.3 MILP / Pareto Frontier Loop (1.5 wks):**
    - Spec calls solver “Mixed-Integer Linear Optimization (MILP) pairing solver” but reference impl is greedy `rank_allocations:382-418`. Phase delivers both:
      - v0 greedy (spec reference) for sub-100ms (`spec §6.1:504`).
      - v1 MILP via PuLP/OR-Tools CP-SAT or `pymoo` NSGA-II (Deb et al. 2002) enumerating Pareto-optimal assignments under constraints.
    - Benchmark: MILP vs greedy hypervolume, spacing, latency on `N=500` nodes; require MILP optimality gap <5% where used.
  - **L4.4 Fairness & Diet Audit Loop (0.5 wk):**
    - Metrics: dietary violation rate (must be 0), Gini of allocations vs HVI, perishability-weighted waste.
    - Adversarial tests: Halal, Jain (no onion/garlic), child/senior priority.

- **Outputs:** `core/pareto_matcher.py` (greedy + MILP path), `docs/model-cards/pareto_matcher.md`, `docs/adr/00x-matcher-solver-choice.md`, MILP formulation doc with objective `spec §2.1:128`.
- **Exit Criteria:** 100% dietary compliance on test suite; latency p95 <100ms greedy, <800ms MILP for N=100; spoilage-prevention proxy ≥92% in simulation.
- **Key Citations:** Deb et al. 2002 (NSGA-II); Saaty 1980 (AHP); Toth & Vigo vehicle/matrices—for assignment analogy; FSSAI dietary regs (§8 Block B).

---

### Phase P5 — Module 3: Cold-Chain Vehicle Assignment & VRPTW Route Optimizer

**Goal:** Implement `core/vrp_router.py` — minimizes `Σ c_uw x_uvw + λ Σ t_delivery/t_safe` (`spec §3.2:162`) with Indian vehicle tiering matrix (`spec §3.1:148-156`).

- **Inputs:** Matched pairs from P4, `t_safe`, fleet `INITIAL_FLEET:164-237`, OSRM live matrix.

- **Inner Loops:**

  - **L5.1 Vehicle Tiering Loop (1 wk):**
    - Encode tiering `spec §3.1:148-156`: E-Rickshaw 300–500kg <8km, Tata Ace EV 1000kg 10–30km, Reefer Sprinter 1500kg 20–80km, Heavy Reefer 4000kg+ 50–250km.
    - Utility: select min-capacity feasible vehicle fulfilling cold-chain (`cold_chain_mandatory` from P2) + range; energy vs cost model for EV (Tata Ace EV specs).
  - **L5.2 OR-Tools VRPTW Loop (2 wks):**
    - Use Google OR-Tools `RoutingModel` with time windows from `SurplusBatch.pickup_window` + `t_safe` as delivery deadline; capacity, temperature compartments.
    - Objective weights: route cost + perishability penalty `λ` tuned (grid λ∈[0.5,5]).
    - Benchmark vs Solomon instances; validate on `mockData` corridors (Ludhiana→Amritsar NH44 ~130km, Jalandhar→Amritsar ~80km).
  - **L5.3 Traffic & Weather-Aware Routing Loop (1 wk):**
    - Integrate live NH44 congestion (`mockData` `Ludhiana → Amritsar Via Phagwara Bypass` bypass scenario `src/App.jsx:189-203`); re-solve on delay >15 min.
    - Weather penalty: add `Φ_env` to transit time uncertainty per P2.

- **Outputs:** `core/vrp_router.py`, `api` endpoint `POST /api/v1/optimize/routing` (`mockData.js:475-485`), benchmark notebook vs Solomon, `docs/model-cards/vrp_router.md`.
- **Exit Criteria:** Feasible routes for all `CRITICAL_HAZARD` batches within `t_safe`; cost vs baseline (nearest-neighbor) improvement ≥15%; p95 solve time <2s for 50 nodes.
- **Key Citations:** Toth & Vigo 2014 (Vehicle Routing); Solomon 1987 (VRPTW benchmarks); Google OR-Tools docs; Tata Motors EV specs (§8 Block C).

---

### Phase P6 — Pipeline Integration & FastAPI Gateway

**Goal:** Unified service `api/app.py`, `api/routes.py`, `api/schemas.py` (`spec §4.1`) with spec-compliant contracts and latency SLA.

- **Inner Loops:**

  - **L6.1 Schema & Contract Loop (1 wk):**
    - Pydantic v2 models from `spec §3.2:186-226` + FSSAI temp enums; JSON Schema validation on ingress.
    - Endpoints (`spec §5.1-5.2`): `POST /api/v1/predict/shelf-life`, `POST /api/v1/optimize/match` (adds vehicle selection), `GET /api/v1/forecast/demand`, `POST /api/v1/optimize/routing`.
    - OpenAPI + `src/data/mockData.js:451-498` `AI_INTEGRATION_ENDPOINTS` alignment.
  - **L6.2 Orchestration Loop (1 wk):**
    - Pipeline DAG: `ingest → decay → forecast → match → route → notify`; async worker (Celery/RQ) for MILP/VRP; sync path for greedy <100ms.
    - Error handling: `CRITICAL_HAZARD` without reefer → hard 422, logged.
  - **L6.3 Latency & Load Loop (1 wk):**
    - Profiling: matcher <100ms @N=500 (`spec §6.1:504`), shelf-life <20ms, VRP <2s; `wrk`/`k6` load 100 RPS; OpenTelemetry traces.
    - Caching: distance matrix + `Φ_env` memoization.

- **Outputs:** Docker image `freshroute-optimizer-api:1.0-rc`, `tests/test_optimizer.py` expanded + contract tests (Schemathesis), latency report, `docs/adr/00x-pipeline-orchestration.md`.
- **Exit Criteria:** CI runs full `§5` example payloads end-to-end; OpenAPI published; latency SLA met on GCP/AWS t3.medium class.
- **Key Citations:** FastAPI / Pydantic docs; OpenAPI 3.1; observability (OpenTelemetry).

---

### Phase P7 — Verification, Field Pilot & Human-in-the-Loop

**Goal:** Prove `spec §6.1 KPIs` in the Punjab GT corridor, not just on synthetic data.

- **KPIs (frozen):** Spoilage prevention ≥95%, latency <100ms (MILP path tracked separately), cold-chain compliance 100% for Tier 1, dietary compliance 100% strict.

- **Inner Loops (season-aware):**

  - **L7.1 Simulation & Shadow Mode Loop (2 wks):**
    - Replay historical 90 days of mandi+weather through pipeline; Monte Carlo heatwave injection (44°C Loo) mirroring `src/App.jsx:106-133` heatwave scenario.
    - Shadow deploy: prod traffic duplicated to new service, compare decisions vs human dispatcher.
  - **L7.2 Controlled Pilot Loop (3 wks):**
    - Live pilot: 2 donors (Verka Ludhiana + one mandi) × 2 recipients (Amritsar Langar + Dhandari nutrition center) × fleet `van-01..04`.
    - Metrics dashboard: rescued lbs, `spoilagePreventionRate`, `coldChainCompliant`, `co2SavedKg` (`src/App.jsx:70-77` stats definitions).
    - IoT hook: BLE/MQTT temp sensors `spec §7:534` feeding back into P2 `Φ_env` (close the telemetry loop).
  - **L7.3 Human Factors & Diet Audit Loop (1 wk):**
    - Structured interviews with Langar Sewadars, drivers, shelter managers on diet trust; A/B rationale phrasing (`aiRationale` in `mockData.js:265`).
    - Bias audit: allocations vs HVI, vs distance (detect “nearby bias” overriding need).

- **Outputs:** Pilot report with KPI table vs `spec §6.1`, field datasheet, updated model cards with field limits, `docs/reviews/phase-7-review.md` signed by domain partner.
- **Exit Criteria:** ≥95% spoilage prevention on field batches, zero dietary violations, cold-chain breach 0; pilot data deposited with datasheet.
- **Key Citations:** Pilot methodology (e.g., ACM COMPASS field studies); WFP pilot evaluation frameworks (§8 Block E).

---

### Phase P8 — MLOps, Telemetry & Handover

**Goal:** System survives monsoon → winter transition without silent drift.

- **Inner Loops:**

  - **L8.1 Deploy & CI Loop (1 wk):**
    - Docker → GCP Cloud Run / AWS ECS, GitHub Actions (test, build, push, deploy), blue/green; infra as Terraform.
  - **L8.2 Drift & Alert Loop (1 wk):**
    - Data drift detectors: `Φ_env` distribution, mandi volume seasonality shift, demand forecast residual drift (Kolmogorov-Smirnov, PSI).
    - Auto-retrain trigger for P3 forecaster; P2 `α,β` seasonal refit.
  - **L8.3 Handover Loop (1 wk):**
    - Maintainer guide, runbook for `CRITICAL_HAZARD` escalation, cost model (EV vs reefer), handover to FreshRoute ops.

- **Outputs:** Deployed URL, Grafana dashboards, on-call runbook, `docs/maintainer.md`.
- **Exit Criteria:** Drift alert fires on synthetic monsoon shift within 24h; rollback tested.

---

### Phase P9 — Publication & Open-Science Release (Overlaps P6–P8)

**Goal:** Publish with artifacts, not PDF alone.

- **Inner Loops:**

  - **L9.1 Paper Draft Loop (2 wks):** Sections mirror spec: Indian contextual constraints, kinetics, Pareto matcher, VRPTW, pipeline, pilot. Every claim cites `BIBLIOGRAPHY.bib`.
  - **L9.2 Repro Bundle Loop (1 wk):** `replay.sh` + Zenodo deposition (code DOI, data DOIs). License audit.
  - **L9.3 Peer Review Loop (1 wk+):** Internal review → submit to target venue → response prep.

- **Outputs:** `paper.pdf`, `paper/` LaTeX source, Zenodo DOIs, `CITATION.cff` update with paper DOI cross-ref.
- **Target Venues:** Nature Food (food systems), Journal of Cleaner Production (waste), Transportation Research Part E (VRP), ACM COMPASS / AAAI AI for Social Good.

---

## 6. Cross-Cutting Continuous Loops

| Loop ID | Cadence | Owner | Trigger | Action |
| :--- | :--- | :--- | :--- | :--- |
| **C1 Data Drift** | Daily | P1/P3 | PSI>0.2 or weather bias >1.5°C | Re-ingest, GE fail → Slack, optional auto-retrain |
| **C2 Dietary Compliance** | Every match | P4 | Zero-tolerance | Block + audit log + stakeholder notice; never silent downgrade |
| **C3 Latency Regression** | Per commit | P6 | p95 > SLA | CI fail on `pytest --benchmark`; flamegraph |
| **C4 Citation Debt** | Per PR | P0 | New constant/parameter | Block merge until `BIBLIOGRAPHY.bib` entry + ADR if needed |
| **C5 Ethics Review** | Monthly | P0 | New district / recipient type | Review board sign-off; update model card “intended use” |
| **C6 Climate Season** | Quarterly | P2 | Season change (Loo→Monsoon→Winter) | Refits `α,β`, re-validates hazard thresholds |

---

## 7. Dataset Registry & Datasheet Obligations

Every row becomes a `docs/datasheets/<slug>.md` (Gebru et al.) + entry in `data_manifest.json` with SHA, DOI, retrieval date, license, BibTeX key.

| # | Dataset / Feed | Use In | Source & Access | License & Attribution | Update Freq | Datasheet Required Fields |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | Agmarknet daily mandi arrivals | P1 L1.1, P3 seasonality, P4 supply | `https://agmarknet.gov.in/` (Govt OGD) scraper `data/ingestion/agmarknet.py` | Govt Open Data License – India (GODL) | Daily | Collection lag, mandi coverage gaps, price/quantity unit normalization |
| D2 | IMD gridded weather + Open-Meteo archive | P1 L1.2, P2 `Φ_env`, P3 features | IMD `https://mausam.imd.gov.in/`, Open-Meteo `https://open-meteo.com/` | IMD terms; Open-Meteo CC-BY-4.0 | Hourly | IMD vs Open-Meteo bias correction, gapfill, 44°C extreme tail count |
| D3 | OpenStreetMap Punjab extract + OSRM | P1 L1.3, P4 proximity, P5 routing | Geofabrik `https://download.geofabrik.de/asia/india.html`, OSRM `http://project-osrm.org/` | ODbL 1.0 – attribution “© OpenStreetMap contributors” | Weekly | OSM snapshot date, routing profile, truck restrictions, NH44 fidelity |
| D4 | FSSAI Food Safety & Standards Regulations | P1 L1.4, P2 critical_temps, P4 dietary | `https://www.fssai.gov.in/` Compendium | Govt publication – fair use with citation | Static + annual review | Extracted clauses, temp thresholds per tier, onion/garlic rule source |
| D5 | Census of India 2011 + ORGI projections | P1 L1.5, P3 demography, HVI | `https://censusindia.gov.in/` | GOV India | Decadal + interpolated | Projection method, informal settlement estimation uncertainty |
| D6 | NFHS-5 + NITI Aayog MPI + WFP hunger maps | P1 L1.5, P3 HVI | `http://rchiips.org/nfhs/`, `https://www.niti.gov.in/`, WFP HungerMap | CC-BY where noted; WFP terms | Annual | MPI indicator weights, NFHS sampling bias, WFP resolution limits |
| D7 | Punjab district base tables & historical meals | P1 L1.5, P3 90-day avg | `data/punjab_districts.json`, `mockData.js:403-449` DISTRICT_DEMAND_FORECAST (synthetic prior) | Internal (CC-BY-4.0 upon release) | Weekly (pilot) | Synthetic vs real provenance flag, pilot log schema |
| D8 | Pilot field logs + IoT temp telemetry | P7 L7.2, P8 drift | MQTT/BLE sensors `spec §7:534`, driver app | Internal – de-identified | Real-time | Sensor calibration cert, missing packet rate, PII scrub |
| D9 | Vehicle specs (Tata Ace EV, Ashok Leyland etc.) | P5 L5.1 | OEM datasheets (Tata Motors, Ashok Leyland, Mahindra, Eicher) | Fair use – cite datasheet | Static | Capacity, range, reefer temp band, EV energy (kWh/km) |

**Datasheet template mandatory sections (Gebru et al. 2021):** Motivation, Composition, Collection Process, Preprocessing/Cleaning, Uses, Distribution, Maintenance (mirrored in `docs/datasheets/TEMPLATE.md`).

---

## 8. Literature & Theory Citation Corpus (by Module)

> Seed `docs/BIBLIOGRAPHY.bib` must contain at minimum the keys below. Format: BibTeX `@article{key, ...}` with DOI. Paper text uses `[@key]` or `\cite{key}`.

### Block A — Kinetics & Food Science (P2 Arrhenius)

| Key | Citation | What it Grounds |
| :--- | :--- | :--- |
| `arrhenius1889` | Arrhenius, S. (1889). Über die Reaktionsgeschwindigkeit... Z. Phys. Chem. 4. DOI:10.1515/zpch-1889-0408 | `k(T)=A·exp(-Ea/RT)` (`spec §2.1`) |
| `labuza1984shelflife` | Labuza, T.P. & Schmidl, M.K. (1985). Accelerated shelf-life testing... Food Technol. | `Ea/R`, `base_hours_at_20C` priors `spec §4.2:264-270` |
| `labuza1993kinetics` | Labuza, T.P. & Fu, B. (1993). Kinetics of quality deterioration... J. Food Sci. | Humidity-extended kinetics `Φ_env` form; `α`, `β` interpretation |
| `taoukis1997tti` | Taoukis, P.S. et al. (1997). Time-temperature integrators... Food Technol. | Hazard threshold derivation (`CRITICAL_HAZARD ≤4h`) |
| `man2002shelflife` | Man, C.M.D. & Jones, A.A. (2000/2002). Shelf Life Evaluation of Foods. Aspen. | Tier 1–5 shelf-life bands `spec §1.1` |
| `fssai2011` | FSSAI. Food Safety and Standards Regulations, 2011 (as amended). | `critical_temp_c` per Tier, milk ≤4°C rule `spec §3.1:182` |
| `kumar2010dairy` | Kumar, A. & Prasad, S. (2010). Kinetics of microbial spoilage in pasteurized milk... J. Food Sci. Technol. (India) | Dairy Ea/R ~6800 K calibration |
| `uneap2024waste` | UNEP Food Waste Index Report 2024. | India 68.7 Mt waste context `spec Executive Summary` |

### Block B — Matching, Pareto & MILP (P4)

| Key | Citation | What it Grounds |
| :--- | :--- | :--- |
| `deb2002nsga2` | Deb, K. et al. (2002). A fast and elitist multiobjective GA: NSGA-II. IEEE TEC 6(2). DOI:10.1109/4235.996017 | Pareto frontier for `S_ij`, hypervolume metric |
| `saaty1980ahp` | Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill. | Weight elicitation `w_i` `spec §2.2` |
| `pareto1896` | Pareto, V. (1896). Cours d’économie politique. | Pareto optimality definition |
| `wolsey1998integer` | Wolsey, L.A. (1998). Integer Programming. Wiley. | MILP formulation correctness |
| `orgtools2024` | Google OR-Tools. CP-SAT & Linear Solver docs `https://developers.google.com/optimization` | MILP/CP-SAT implementation |
| `pulp2011` | Mitchell, S. et al. PuLP docs. | Alternative MILP solver |

### Block C — Vehicle Routing (P5 VRPTW)

| Key | Citation | What it Grounds |
| :--- | :--- | :--- |
| `toth2014vrp` | Toth, P. & Vigo, D. (2014). Vehicle Routing: Problems, Methods, Applications. SIAM. | VRPTW formulation, objective `spec §3.2:162` |
| `solomon1987` | Solomon, M.M. (1987). Algorithms for VRPTW. Oper. Res. 35. | Benchmark instances, time-window handling |
| `orgtoolsvrp2024` | Google OR-Tools Routing `https://developers.google.com/optimization/routing` | `RoutingModel` VRPTW impl |
| `dantzig1959truck` | Dantzig, G. & Ramser, J. (1959). Truck dispatching problem. | Historical VRP grounding |
| `tataaceevspec` | Tata Motors. Ace EV spec sheet (payload, range, kWh). | Tiering matrix `spec §3.1:148-156` |

### Block D — Demand Forecasting (P3)

| Key | Citation | What it Grounds |
| :--- | :--- | :--- |
| `hochreiter1997lstm` | Hochreiter, S. & Schmidhuber, J. (1997). Long short-term memory. Neural Comput. 9(8). | LSTM model |
| `ke2017lightgbm` | Ke, G. et al. (2017). LightGBM. NeurIPS 31. | Gradient boosting baseline |
| `lim2021tft` | Lim, B. et al. (2021). Temporal Fusion Transformers. Int. J. Forecast. 37. | Stretch sequence model |
| `niti2023mpi` | NITI Aayog. National Multidimensional Poverty Index 2023. | HVI MPI component |
| `nfhs5` | IIPS & ICF. NFHS-5 (2019-21). | Child/senior nutrition flags |
| `wfp2024hungermap` | WFP HungerMap Live `https://hungermap.wfp.org/` | Cross-validation for HVI |

### Block E — Documentation, Reproducibility & Ethics (P0/P7/P9)

| Key | Citation | What it Grounds |
| :--- | :--- | :--- |
| `gebru2021datasheets` | Gebru, T. et al. (2021). Datasheets for Datasets. CACM 64(12). DOI:10.1145/3458723 | Datasheet template (`P1`) |
| `mitchell2019modelcards` | Mitchell, M. et al. (2019). Model Cards. FAT* 2019. DOI:10.1145/3287560.3287596 | Model card template (`P2-P5`) |
| `wilkinson2016fair` | Wilkinson, M. et al. (2016). FAIR Principles. Sci. Data 3. DOI:10.1038/sdata.2016.18 | FAIR governance (`§3.1`) |
| `brand2015cff` | Druskat, S. et al. CITATION.cff spec `https://citation-file-format.github.io/` | Code citation |
| `neurips2023checklist` | NeurIPS Reproducibility checklist 2023. | `reproducibility.md` + `replay.sh` |
| `gustavsson2011foodloss` | Gustavsson, J. et al. (2011). Global Food Losses & Waste. FAO. | Global waste framing |
| `icmr2017ethics` | ICMR National Ethical Guidelines 2017. | Pilot ethics |

> **Action:** Populate `docs/BIBLIOGRAPHY.bib` with full BibTeX (copy DOI via https://doi.org). No citation may be “personal communication” without `docs/calibration/*.md` lab-note + date + sign-off.

---

## 9. Evaluation Framework & KPI Hierarchy

### 9.1 Frozen KPIs from Spec §6.1 (Gate Criteria)

| KPI | Spec Target `spec:503-506` | Measurement Protocol | Gate |
| :--- | :--- | :--- | :--- |
| Spoilage Prevention Rate | ≥95% | `meals consumed before t_safe / total surplus weight` on field batches (weighbridge + Langar consumption log) | P7 |
| Algorithm Latency (greedy) | <100 ms @ N=500 | `pytest --benchmark` on `rank_allocations:382`, p95 | P6 |
| Cold-Chain Compliance Tier 1 | 100% | BLE logs: zero breaches >6°C during dairy transit | P7 |
| Dietary Compliance | 100% strict | Audit log of `DietMatch` gate `pareto_matcher.py:354-356`; adversarial suite passes | P4,P7 |

### 9.2 Extended Academic Metrics (for paper)

| Tier | Metric | Collector |
| :--- | :--- | :--- |
| Decay | `Φ_env` multiplier RMSE vs lab, hazard Precision/Recall | P2 notebook |
| Forecast | RMSE/MAE/WAPE 7-day, surge Recall, PSI drift | P3 MLflow |
| Matching | Hypervolume & spacing (NSGA-II), Gini fairness, waste-vs-hunger trade-off | P4 |
| Routing | Cost vs nearest-neighbor %, on-time window %, CO₂ saved (`weight*2.5` in `pareto_matcher.py:416`) | P5 |
| System | End-to-end latency p50/p95/p99, uptime, pilot rescued lbs vs `stats.rescuedLbs:71` | P6,P7 |
| Human | Trust Likert (Langar/sewadar), dispatch override rate | P7 L7.3 |

### 9.3 Ablation Expectations (Paper § Results)

- No `Φ_env` vs with `α,β` → dairy waste Δ.
- Greedy vs MILP vs NSGA-II → latency vs hypervolume.
- No HVI vs with HVI → Gini improvement.
- No traffic-aware routing vs with OSRM live → on-time delivery Δ.

---

## 10. Risk, Ethics & Mitigation Matrix

| # | Risk | Likelihood | Impact | Mitigation (Loop) | Owner |
| --- | --- | --- | --- | --- | --- |
| R1 | Agmarknet rate-limit / schema change | M | H | Cache + fallback to previous day + adapter pattern + alert (C1) | P1 |
| R2 | 44°C+ climate beyond calibrated `α,β` | M | H | Seasonal refit (C6); widen Reefer mandatory band; flag “out-of-calibration” in model card | P2 |
| R3 | Dietary violation due to data entry error | L | C (cultural harm) | Two-person rule for `dietary_flags`; hard DB constraint; C2 zero-tolerance | P4 |
| R4 | MILP latency breaks 100 ms SLA | H | M | Keep greedy as default; MILP as batch/offline; `λ` tuning; ADR | P4,P6 |
| R5 | Pilot low participation (Langar trust) | M | H | Co-design with SGPC; paper trail of Langar Rehat compliance; non-extractive data use agreement | P0,P7 |
| R6 | OSM rural road missing / OSRM error | M | M | Manual NH44 corridor validation; driver feedback loop; OSM edit-back | P5 |
| R7 | Forecast overfits to 2024 monsoon | M | H | Walk-forward CV; hold-out monsoon season; PSI drift alert C1 | P3 |
| R8 | Sensor dropout (BLE) → false compliance | M | H | Redundant logger + manual temp check; flag gaps in `cold_chain_mandatory` | P8 |
| R9 | Citation debt (un-sourced constant) | H | H (desk reject) | C4 pre-commit citation audit; reviewer sign-off per gate | P0 |

**Ethics principles:** Do no harm (Langar sanctity), beneficence (child/senior priority `spec §1.2:83`), autonomy (recipient opt-in), justice (HVI prevents “nearest-richest” bias). Document in `docs/ethics.md` citing ICMR 2017.

---

## 11. Timeline, Milestones & RACI

### 11.1 Indicative Timeline (32 weeks wall-clock; P9 overlaps)

```
Wk 1-2   P0 Charter & Ethics
Wk 3-7   P1 Data Foundation (ends with Zenodo v0.1)
Wk 8-11  P2 Arrhenius (overlaps P3 Wk 8-12)
Wk 8-12  P3 Forecaster (ends with HVI v1)
Wk 13-16 P4 Pareto Matcher
Wk 17-20 P5 VRPTW Router
Wk 21-24 P6 Integration & FastAPI (→ v1.0-rc + paper draft start)
Wk 25-30 P7 Field Pilot (must span ≥1 heatwave or monsoon peak)
Wk 31-33 P8 MLOps & Handover
Wk 21-34 P9 Paper & Open-Science (submit target Wk 34)
```

Gantt is maintained in `docs/GANTT.md` (Mermaid) and updated at each gate.

### 11.2 RACI (Condensed)

| Activity | Eng Lead | Data Eng | ML | Domain Partner (Langar/Verka) | Reviewer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 Ethics & Templates | A | C | C | C | R |
| P1 Ingestion & Datasheets | C | A/R | C | I | R |
| P2 Kinetics calibration | C | C | A/R | C | R |
| P3 Forecaster | C | C | A/R | I | R |
| P4 Matcher & Fairness | A | C | A/R | R(diet) | R |
| P5 VRPTW | A | C | R | I | R |
| P6 FastAPI & Latency | A/R | C | C | I | R |
| P7 Pilot & KPI | A | C | R | A/R | R |
| P9 Paper | A | C | A | C | R |

A=Accountable, R=Responsible, C=Consulted, I=Informed. One `A` per row.

---

## 12. Definition of Done per Phase Gate

A phase cannot close unless **all** are true:

- [ ] `BIBLIOGRAPHY.bib` + datasheet/model-card set for that phase merged.
- [ ] `tests/` covers new code with ≥85% line coverage + `test_arrhenius_heatwave_spoilage` & `test_dietary_compatibility_rejection` green.
- [ ] MLflow/DVC bundle reproducible via `replay.sh` on clean clone.
- [ ] Model card “Limitations” updated with field season tested.
- [ ] ADR filed for any spec deviation.
- [ ] Citation audit `scripts/citation_audit.py` passes (0 unresolved citations).
- [ ] External reviewer (domain + technical) signed `docs/reviews/phase-N-review.md`.
- [ ] Artifact deposited where required (Zenodo DOI for P1/P2/P6/P7).

Phase gate decision: `Proceed` / `Proceed with debt` (ADR-tracked) / `Iterate loop` / `Abort`.

---

## 13. Appendices

### Appendix A — Datasheet Template (Skeleton, file: `docs/datasheets/TEMPLATE.md`)

```markdown
# Datasheet for Dataset: <name> (Gebru et al. 2021)

## Motivation
## Composition (records, fields, missingness heatmap)
## Collection Process (tools, consent, funding)
## Preprocessing / Cleaning (scripts with hash)
## Uses (intended + unintended + misuses)
## Distribution (DOI, license, access)
## Maintenance (update cadence, contact)
## Citation: BibTeX key `<key>`
```

### Appendix B — Model Card Template (Skeleton, file: `docs/model-cards/TEMPLATE.md`)

```markdown
# Model Card: <model> (Mitchell et al. 2019)

## Model Details (version, type, paper ref)
## Intended Use (users, geography: Punjab GT corridor)
## Factors (climate, diet, vehicle class)
## Metrics (table with confidence intervals, slices by Tier/district)
## Evaluation Data (datasheet keys)
## Training Data (datasheet keys)
## Quantitative Analyses (ablation)
## Ethical Considerations (dietary, hunger equity)
## Caveats & Limitations (e.g., not validated >48°C, not for frozen fish)
## Citation: BibTeX key `<key>`
```

### Appendix C — Citation Audit Script Contract (`scripts/citation_audit.py`)

- Input: `docs/BIBLIOGRAPHY.bib`, all `*.py` + `*.md`.
- Checks: every numeric literal tagged `CITED` or un-tagged constant < threshold; every `\cite{}` resolves; every datasheet listed in `data_manifest.json`.
- Exit 0 = pass; else print table of violations.

### Appendix D — ADHD (Architecture Decision Record) Minimal Template

```markdown
# ADR-00N: Title
Date: YYYY-MM-DD
Status: Proposed|Accepted|Rejected|Superseded
Context:
Decision:
Consequences:
Citations: [@key]
```

### Appendix E — Paper Skeleton (for `P9`)

```
Abstract → 1 Indian Context & Gap (FAO/UNEP/WFP + FSSAI) → 2 Related Work (shelf-life kinetics, food-rescue
matching, VRPTW, hunger forecasting) → 3 Model (Arrhenius+Φ, Pareto+ MILP, VRPTW+λ, LSTM/LGBM+HVI)
→ 4 Data (.datasheets, FAIR) → 5 Experiments (simulation + field pilot) → 6 Results (KPIs + ablations)
→ 7 Limitations & Ethics (model cards) → 8 Deployment → 9 Conclusion → References (BIBLIOGRAPHY.bib)
→ Appendices (schemas, proofs, reproducibility bundle)
```

### Appendix F — Starter `BIBLIOGRAPHY.bib` Keys (to be expanded with full entries)

```bibtex
@article{arrhenius1889, author={Arrhenius, Svante}, journal={Z. Phys. Chem.}, year={1889}, doi={10.1515/zpch-1889-0408}}
@article{labuza1993kinetics, author={Labuza, T.P. and Fu, B.}, journal={J. Food Sci.}, year={1993}}
@article{taoukis1997tti, author={Taoukis, P.S. and Labuza, T.P.}, journal={Food Technol.}, year={1997}}
@book{man2002shelflife, author={Man, C.M.D. and Jones, A.A.}, publisher={Aspen}, year={2000}}
@misc{fssai2011, author={{FSSAI}}, title={Food Safety and Standards Regulations}, year={2011}, url={https://www.fssai.gov.in/}}
@techreport{uneap2024waste, author={{UNEP}}, title={Food Waste Index Report 2024}, year={2024}}
@article{deb2002nsga2, author={Deb, K. and others}, journal={IEEE TEC}, year={2002}, doi={10.1109/4235.996017}}
@book{saaty1980ahp, author={Saaty, T.L.}, publisher={McGraw-Hill}, year={1980}}
@book{toth2014vrp, author={Toth, P. and Vigo, D.}, publisher={SIAM}, year={2014}}
@article{solomon1987, author={Solomon, M.M.}, journal={Oper. Res.}, year={1987}}
@article{hochreiter1997lstm, author={Hochreiter, S. and Schmidhuber, J.}, journal={Neural Comput.}, year={1997}, doi={10.1162/neco.1997.9.8.1735}}
@inproceedings{ke2017lightgbm, author={Ke, G. and others}, booktitle={NeurIPS}, year={2017}}
@article{lim2021tft, author={Lim, B. and others}, journal={Int. J. Forecast.}, year={2021}, doi={10.1016/j.ijforecast.2019.12.001}}
@article{gebru2021datasheets, author={Gebru, T. and others}, journal={CACM}, year={2021}, doi={10.1145/3458723}}
@inproceedings{mitchell2019modelcards, author={Mitchell, M. and others}, booktitle={FAT*}, year={2019}, doi={10.1145/3287560.3287596}}
@article{wilkinson2016fair, author={Wilkinson, M. and others}, journal={Sci. Data}, year={2016}, doi={10.1038/sdata.2016.18}}
@misc{brand2015cff, author={Druskat, S. and others}, title={Citation File Format}, url={https://citation-file-format.github.io/}}
```

### Appendix G — Immediate Next Actions (Week 1)

- [ ] `git checkout -b docs/plan-phase0` → merge this plan.
- [ ] Initialize `docs/BIBLIOGRAPHY.bib` with Appendix F expanded to full BibTeX (fetch DOIs).
- [ ] Scaffold `freshroute-optimizer-model/` per `spec §4.1` + `CITATION.cff`.
- [ ] Create `docs/datasheets/TEMPLATE.md`, `docs/model-cards/TEMPLATE.md`, `scripts/citation_audit.py` stub.
- [ ] Schedule ethics kickoff with SGPC/Verka/mandi contacts; log MoUs.
- [ ] Set up DVC + MLflow local; commit `src/data/mockData.js` as `data/synthetic/mockData.v1.json` with datasheet.

---

*Plan approved for execution by FreshRoute Engineering Core. Every phase gate requires signed review and citation audit. No artifact ships without a model card and datasheet.*
