# Datasheet for Dataset: <DATASET_SLUG>

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Every dataset ingested in `freshroute-optimizer-model/data/` or `data/` must have a completed copy of this template before it is used in training, calibration, or evaluation. See `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** `<Human-readable name>` (`data/<path>`)
**Version:** `vX.Y.Z`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `YYYY-MM-DD`
**Maintainer:** `<name, email>`  **Reviewer:** `<name, date>`
**BibTeX key:** `[@key]` in `docs/BIBLIOGRAPHY.bib`
**License:** `<GODL-India / CC-BY-4.0 / ODbL-1.0 / Internal>`

---

## 1. Motivation

- Why was this dataset created/collected? Which pipeline stage does it serve? (P1 L1.1–L1.5, P2 kinetics, P3 forecaster, P4 matcher, P5 routing)
- Who funded collection? Which FreshRoute phase gate requires it?
- What gap does it fill vs synthetic `src/data/mockData.js:1-498`?

## 2. Composition

- Records, fields, schema (link to `api/schemas.py` or JSON Schema), field types/units.
- Missingness heatmap (% missing per field, per temporal/spatial slice).
- Label distribution (e.g., per commodity tier, per district) and known skew.
- Sensitive attributes: dietary, location precision (coarsened?), PII status (none / de-identified).
- Example record (1–2 rows, anonymized):

```json
{}
```

## 3. Collection Process

- Source: Agmarknet / IMD / Open-Meteo / OSM / FSSAI / Census / NFHS / WFP / field IoT.
- Method: scraper (`data/ingestion/<source>.py` hash), API endpoint, manual log.
- Time window, spatial coverage, sampling strategy, inclusion/exclusion.
- Human subjects: consent, ICMR 2017 compliance, Langar MoU reference.
- Cost, compensation, workforce.

## 4. Preprocessing / Cleaning

- Steps, scripts (git hash), normalization (units, temp C vs F, weight lbs→kg), deduplication, outlier rules.
- Great Expectations suite: `expect_*` checks and pass rate.
- Known noise: Agmarknet weekend lag, IMD vs Open-Meteo bias, OSM missing rural roads.
- Provenance: `data_manifest.json` SHA256, DVC `*.dvc` hash, raw→silver→gold lineage.

## 5. Uses

- Intended uses (which model, which features) and intended users.
- Unintended / out-of-scope uses (e.g., not for frozen-chain fish, not beyond Punjab corridor without recalibration).
- Prior tasks that have used it (phase, MLflow run ID).

## 6. Distribution

- Access: repo path, Zenodo DOI, API, license obligations (attribution string for ODbL, GODL).
- Versioning and update cadence (daily/weekly/quarterly), retention.
- DOI landing page and citation string.

## 7. Maintenance

- Contact, update trigger (season change, schema drift), deprecation policy.
- Drift monitors (PSI, KS) and retrain trigger thresholds (see `docs/IMPLEMENTATION_PLAN.md:6 C1/C6`).
- Errata log.

## 8. Ethical Considerations & Limitations

- Hunger/poverty representation bias (NFHS sampling, Census projection uncertainty).
- Cultural/dietary coverage gaps.
- Re-identification risk, location downsampling, retention period.
- Acknowledged limitations that propagate to model card (e.g., monsoon 80% humidity tail under-sampled).

## 9. Citation

```bibtex
@misc{key,
}
```
Cite this datasheet as: `<DOI>` + BibTeX key.

---

*Checklist before merge:* GE suite green, `data_manifest.json` updated, `BIBLIOGRAPHY.bib` key present, reviewer signed.
