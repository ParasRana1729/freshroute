# ADR-001: Phase P0 Scaffold — Python Subproject Location and Governance

Date: 2026-08-24
Status: Accepted

## Context

Spec `docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md:234` proposes `freshroute-optimizer-model/` as top-level. Repo currently hosts a Vite React frontend at `src/App.jsx:1` with `src/data/mockData.js:1-498`. We must isolate Python optimizer dependencies (FastAPI, OR-Tools, LightGBM) from Node without breaking Git history or CI.

## Decision

- Create `freshroute-optimizer-model/` as a Python subproject at repo root, matching spec layout exactly: `api/`, `core/`, `data/`, `tests/`, `notebooks/`, `scripts/`.
- Keep shared governance at repo root: `docs/BIBLIOGRAPHY.bib`, `docs/datasheets/`, `docs/model-cards/`, `docs/adr/`, `CITATION.cff`, `scripts/citation_audit.py`.
- Duplicate audit script at both `scripts/` and `freshroute-optimizer-model/scripts/` with symlink or copy; root is canonical for CI.
- Frontend mock data remains authoritative synthetic prior until P1 gold tables replace it; `data/synthetic/mockData.v1.json` mirrors `src/data/mockData.js` with datasheet.

## Consequences

- Clean separation; Docker builds context `freshroute-optimizer-model/` only.
- Contributors must `cd freshroute-optimizer-model` for Python work and `pip install -r requirements.txt`.
- Minor duplication of scripts; mitigated by copy and CI check of equality.

## Alternatives Considered

- Put `core/` and `api/` at repo root: rejected (pollutes frontend, confuses bundler, risks `requirements.txt` vs `package.json` clash).
- Separate repo: rejected (loses single-paper reproducibility bundle `replay.sh`; complicates Zenodo concept DOI).

## Citations

- [@wilkinson2016fair] FAIR compartmentalization
- [@gebru2021datasheets] data governance

## Reversibility

Move subproject to root with one `git mv` and update `Dockerfile` context; low-cost revert.
