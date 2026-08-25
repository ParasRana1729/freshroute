# Datasheet for Dataset: NITI Aayog Multidimensional Poverty Index & NFHS-5 Nutrition (D6)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D6 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** National Multidimensional Poverty Index (MPI) & NFHS-5 Child Nutrition Indicators (`data/punjab_districts.json:mpi_rank,hunger_vulnerability_index`)
**Version:** `v1.0.0-P1`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Social Equity & Nutrition Working Group
**BibTeX keys:** `[@niti2023mpi; @nfhs5; @wfp2024hungermap]`
**License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)

---

## 1. Motivation

- **Purpose:** Derives the Hunger Vulnerability Index (HVI $\in [0, 100]$) to mathematically prioritize food allocations to severely disadvantaged and undernourished communities, mitigating "nearby-wealthy bias" where food is dumped at convenient central locations.
- **Pipeline Stage:** Injected into Stage 2 Deficit scoring (`core/demand_forecaster.py:1027`) and weighted in Stage 3 Pareto Matcher ($w_2=0.30$) in `core/pareto_matcher.py:350`.

## 2. Composition

- **Key Indicators:**
  - **Headcount Poverty Ratio (%):** Multidimensional poverty headcount from NITI Aayog National MPI 2023.
  - **Child Stunting / Wasting (%):** National Family Health Survey (NFHS-5, 2019-21) child undernutrition rates.
  - **Informal Settlement Population Ratio:** Urban slum and migrant agricultural labor density.
  - **Derived HVI:** Composite score normalized from 0 (lowest vulnerability) to 100 (acute vulnerability, e.g. Muktsar, Fazilka, Firozpur, migrant industrial pockets of Ludhiana).

## 3. Collection Process

- **Sources:**
  - NITI Aayog: *National Multidimensional Poverty Index: A Progress Review 2023* (`https://www.niti.gov.in/`).
  - International Institute for Population Sciences (IIPS): *NFHS-5 State and District Fact Sheets: Punjab* (`http://rchiips.org/nfhs/`).
  - United Nations World Food Programme (WFP): *HungerMap LIVE Global Monitoring* (`https://hungermap.wfp.org/`).

## 4. Preprocessing & Validation

- Normalization and weighting algorithm benchmarked in `freshroute-optimizer-model/scripts/benchmark_hvi_fusion.py`.
- Equity Gini metric verification ensures high-HVI communities receive uplift in surplus allocations.

## 5. Citation

```bibtex
@techreport{niti2023mpi,
  author      = {{NITI Aayog}},
  title       = {National Multidimensional Poverty Index: A Progress Review 2023},
  institution = {Government of India},
  year        = {2023},
  url         = {https://www.niti.gov.in/}
}
@misc{nfhs5,
  author       = {{Ministry of Health and Family Welfare (MoHFW), Government of India}},
  title        = {National Family Health Survey (NFHS-5), 2019--21: Punjab Factsheet},
  year         = {2021},
  howpublished = {\url{http://rchiips.org/nfhs/}}
}
@misc{wfp2024hungermap,
  author       = {{World Food Programme (WFP)}},
  title        = {WFP HungerMap LIVE},
  year         = {2024},
  howpublished = {\url{https://hungermap.wfp.org/}}
}
```
