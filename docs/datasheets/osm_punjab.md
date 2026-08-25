# Datasheet for Dataset: OpenStreetMap Punjab Extract & OSRM Distance Matrix (D3)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D3 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** OpenStreetMap Punjab Road Network & OSRM GT Corridor Distance Matrix (`data/gold/osm_distance_matrix.parquet`)
**Version:** `v1.0.0-P1`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Routing Governance Working Group
**BibTeX keys:** `[@osm2024; @osrm2024]`
**License:** Open Database License (ODbL) 1.0 — attribution "© OpenStreetMap contributors"

---

## 1. Motivation

- **Purpose:** Supplies realistic road distances and transit travel time estimations for Punjab donor-recipient pairs across the NH44 Grand Trunk (GT) corridor (Ludhiana, Amritsar, Jalandhar, Patiala, Bathinda).
- **Pipeline Stage:** Powers Stage 3 Proximity scoring ($w_3=0.20$) in `core/pareto_matcher.py:339` and Stage 4 VRPTW vehicle routing in `core/vrp_router.py:27`.
- **Gap filled:** Replaces crude Euclidean/Haversine approximations with topological turn-by-turn road network metrics considering Highway bypasses (e.g., Phagwara bypass).

## 2. Composition

- **Records:** Matrix of origin-destination pairs with road distance (km) and estimated travel duration (minutes).
- **Schema:**
  - `donor_id` (string): Unique donor node identifier (e.g., `donor-verka-ludhiana-01`).
  - `recipient_id` (string): Unique recipient node identifier (e.g., `recip-amritsar-langar-01`).
  - `distance_km` (float): Driving distance in kilometers.
  - `duration_min` (float): Driving transit time under normal traffic.
  - `source` (string): `osrm-live` with `haversine-fallback`.
- **Example Record:**
```json
{
  "donor_id": "donor-verka-ludhiana-01",
  "recipient_id": "recip-amritsar-langar-01",
  "distance_km": 137.07,
  "source": "osrm-live"
}
```

## 3. Collection Process

- **Source:** OpenStreetMap extracts for Punjab via Geofabrik (`https://download.geofabrik.de/asia/india.html`) queried through the Open Source Routing Machine (OSRM) HTTP API engine.
- **Fallbacks:** In offline/airgapped environments, the system falls back to Haversine distance with a 1.25 urban winding circuity factor.
- **Coverage:** Primary GT Road logistics nodes (Ludhiana, Jalandhar, Amritsar, Khanna, Phagwara, Patiala, Bathinda).

## 4. Preprocessing / Cleaning

- Extracted via `freshroute-optimizer-model/scripts/build_gold_osm.py`.
- Validation: Verified by `tests/test_integration_p4p5p3.py:test_d3_gold_matrix_lookup`.
- Quality Gate: `data_manifest.json` tracks SHA256 checksum with DVC tracking (`osm_distance_matrix.parquet.dvc`).

## 5. Uses

- **Intended Use:** Vehicle route planning, proximity scoring in Pareto multi-objective optimization, and transit feasibility validation against Arrhenius $t_{safe}$.
- **Out of scope:** Micro-pedestrian routing inside dense informal settlement alleyways without motorized vehicle access.

## 6. Distribution & Maintenance

- Stored in `freshroute-optimizer-model/data/gold/osm_distance_matrix.parquet`.
- Refreshed weekly for infrastructure updates and seasonal monsoon road maintenance diversions.

## 7. Ethical Considerations

- Open access, no PII. ODbL attribution honored in all published reports.

## 8. Citation

```bibtex
@misc{osm2024,
  author = {{OpenStreetMap contributors}},
  title  = {Punjab Road Network Extract},
  year   = {2024},
  url    = {https://www.openstreetmap.org}
}
@misc{osrm2024,
  author = {Luxen, Dennis and Vetter, Christian},
  title  = {Open Source Routing Machine (OSRM)},
  year   = {2024},
  url    = {http://project-osrm.org/}
}
```
