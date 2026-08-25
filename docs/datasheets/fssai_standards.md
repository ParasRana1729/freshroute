# Datasheet for Dataset: FSSAI Food Safety & Cold-Chain Standards (D4)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D4 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** Food Safety and Standards Authority of India (FSSAI) Regulatory Compendium (`data/indian_commodities.json:critical_temp_c`)
**Version:** `v1.0.0-P1`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Food Safety Governance Working Group
**BibTeX keys:** `[@fssai2011; @icmr2017ethics]`
**License:** Government of India Open Access / Statutory Regulations (Fair Use)

---

## 1. Motivation

- **Purpose:** Codifies mandatory food safety temperatures, maximum permissible transit durations, and strict cultural/religious dietary segregation policies under Indian law.
- **Pipeline Stage:** Enforces Stage 1 Arrhenius critical hazard temperatures ($T_{crit}$) in `core/arrhenius_decay.py:272` and Stage 3 hard feasibility dietary gating (`check_dietary_eligibility:94`) in `core/pareto_matcher.py`.
- **Statutory Mandate:** Compliance with the Food Safety and Standards (Licensing and Registration of Food Businesses) Regulations, 2011.

## 2. Composition

- **Key Rules & Thresholds:**
  - **Tier 1 (Dairy):** Pasteurized cow/buffalo milk pouches require continuous cold-chain holding at $\le 4^\circ\text{C}$ (`critical_temp_c: 4`). Maximum permissible ambient exposure is 4 hours before microbial threshold breach ($E_a/R \approx 6800\text{ K}$).
  - **Tier 2 (Prepared Meals / Langar Dal & Roti):** Cooked food must be maintained either $> 65^\circ\text{C}$ (hot holding) or $\le 4^\circ\text{C}$ (rapid chill). In ambient transit, consumable shelf life drops to $\le 6\text{h}$ under Punjab summer temperatures ($>38^\circ\text{C}$).
  - **Tier 3 (Cut Produce):** Fresh fruits and sliced vegetables require holding at $\le 12^\circ\text{C}$.
  - **Dietary Constraints:** Strict segregation of `Strict_Lacto_Vegetarian` (Langar Rehat Maryada — no eggs, meat, fish, animal rennet) and `Halal` certifications. Zero-tolerance hard constraint gate ($S_{ij} = 0.0$ on violation).

## 3. Collection Process

- Extracted from official Gazette notifications, FSSAI Guidance Notes on Food Redistribution (2019), and Indian Council of Medical Research (ICMR) dietary guidelines.

## 4. Preprocessing & Validation

- Encoded into machine-readable JSON structure `data/indian_commodities.json`.
- Tested via `tests/test_optimizer.py:test_dietary_compatibility_rejection` and `tests/test_optimizer.py:test_arrhenius_heatwave_spoilage`.

## 5. Uses

- Primary validation benchmark for real-time safety gating and cold-chain compliance tracking in the dispatcher console.

## 6. Citation

```bibtex
@misc{fssai2011,
  author       = {{Food Safety and Standards Authority of India (FSSAI)}},
  title        = {Food Safety and Standards (Licensing and Registration of Food Businesses) Regulations, 2011},
  year         = {2011},
  howpublished = {\url{https://www.fssai.gov.in/}}
}
```
