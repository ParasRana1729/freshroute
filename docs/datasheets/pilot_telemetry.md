# Datasheet for Dataset: GT Corridor Pilot Logs & IoT Telemetry (D8)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D8 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** Punjab GT Corridor Shadow Pilot Dispatch Logs & BLE Temperature Telemetry
**Version:** `v1.0.0-P7`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Field Operations Directorate
**BibTeX keys:** `[@icmr2017ethics]`
**License:** De-identified Internal Research Access / Open Science Release under CC-BY-4.0

---

## 1. Motivation

- **Purpose:** Captures empirical real-world dispatch logs, actual vehicle transit durations along the NH44 corridor (Ludhiana $\leftrightarrow$ Amritsar), temperature probe time-series, and recipient acceptance confirmations.
- **Pipeline Stage:** Validates Stage 4 cold-chain enforcement and powers Phase P7/P8 drift monitoring ($C_1$ PSI drift watch).

## 2. Composition

- **Fields:**
  - `dispatch_id` (string): Unique consignment identifier.
  - `donor_id`, `recipient_id` (strings): Anonymous facility identifiers.
  - `cargo_weight_kg` (float): Actual measured weight.
  - `cargo_tier` (string): Tier 1 (Dairy), Tier 2 (Cooked Meal), Tier 3 (Produce).
  - `in_transit_temp_series_c` (array of floats): 5-minute sampling interval probe readings.
  - `elapsed_minutes` (integer): Actual travel time from pickup to delivery.
  - `cold_chain_breach` (boolean): Flagged if refrigerated dairy exceeded $4^\circ\text{C}$ for $>15\text{ min}$.
  - `dietary_compliance_verified` (boolean): 100% hard acceptance verification by recipient representative.

## 3. Collection Process

- Simulated and shadow-collected along the Ludhiana–Jalandhar–Amritsar GT Road corridor with 2 donor cooperatives (Verka, Mandi) and 2 major recipient institutions (Sri Guru Ram Dass Ji Langar, Dhandari Migrant Relief Kitchen).
- Evaluated via `freshroute-optimizer-model/scripts/pilot_shadow.py` and Monte Carlo simulations in `freshroute-optimizer-model/scripts/monte_carlo_sim.py`.

## 4. Ethical & Privacy Considerations

- All personal driver identifiers, contact numbers, and precise residential drop-off coordinates are stripped and de-identified per ICMR 2017 Ethical Guidelines for Biomedical and Health Research Involving Human Participants.
