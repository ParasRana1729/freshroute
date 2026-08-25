# Datasheet for Dataset: Indian Vehicle Fleet Tiers & OEM Specifications (D9)

> Template adapted from Gebru et al. 2021 [@gebru2021datasheets]. Governs dataset D9 in `docs/IMPLEMENTATION_PLAN.md:7`.

**Dataset:** Punjab Cold-Chain Redistribution Fleet Specifications (`core/vrp_router.py:VEHICLE_TIERS`)
**Version:** `v1.0.0-P5`  **DOI:** `10.5281/zenodo.XXXXXXX`  **Date:** `2026-08-25`
**Maintainer:** FreshRoute AI Architecture Core  **Reviewer:** Fleet Logistics Working Group
**BibTeX keys:** `[@tataaceevspec; @ashokleylandspec; @toth2014vrp]`
**License:** Public OEM Technical Datasheets (Fair Use / Reference Standard)

---

## 1. Motivation

- **Purpose:** Defines the 4-tier vehicle capability matrix adapted to Indian road typologies (ranging from ultra-narrow inner-city bazaar lanes to high-speed GT Road freight corridors), matching batch weight, required temperature bands, and operational radius.
- **Pipeline Stage:** Powers vehicle selection in `core/vrp_router.py:select_vehicle` and capacity-constrained VRPTW routing.

## 2. Composition (Vehicle Tiering Matrix — Spec §3.1)

| Tier Name | Representative Model | Capacity (kg) | Range (km) | Refrigeration | Energy/Fuel | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 Micro-EV** | Mahindra Treo Zor / E-Rickshaw | 300 – 500 | 5 – 8 | Insulated Box (Passive Ice) | Electric | Congested inner-city markets, Mandi pickups |
| **Tier 2 Light EV** | Tata Ace EV Reefer | 1,000 | 10 – 30 | Active Reefer ($2^\circ\text{C} - 8^\circ\text{C}$) | Electric ($0.15\text{ kWh/km}$) | Intra-city distribution, urban slums, schools |
| **Tier 3 Medium Reefer** | Ashok Leyland Cold Carrier | 1,500 – 2,500 | 20 – 80 | Active Sub-zero / Chilled ($2^\circ\text{C} - 4^\circ\text{C}$) | Diesel / Hybrid | Inter-city corridor (Ludhiana $\rightarrow$ Amritsar) |
| **Tier 4 Heavy Reefer** | Eicher Pro 3015 Reefer | 4,000+ | 50 – 250 | Multi-compartment Chilled/Frozen | Diesel | State-wide bulk cooperative redistribution |

## 3. Collection Process

- Compiled from OEM technical specifications: Tata Motors Commercial Vehicles (Tata Ace EV Spec Sheet 2023), Ashok Leyland Light Commercial Vehicles, and Ministry of Road Transport and Highways (MoRTH) vehicle classification standards.

## 4. Preprocessing & Validation

- Unit normalized to kilograms ($kg$), kilometers ($km$), and degrees Celsius ($^\circ\text{C}$).
- Tested via unit test `tests/test_optimizer.py:test_vrp_tiering_and_routing` and integration tests in `tests/test_integration_p4p5p3.py:test_vrp_capacity_split`.

## 5. Citation

```bibtex
@misc{tataaceevspec,
  author       = {{Tata Motors Commercial Vehicles}},
  title        = {Tata Ace EV Technical Specification and Cold-Chain Variants},
  year         = {2023},
  howpublished = {\url{https://aceev.tatamotors.com/}}
}
@misc{ashokleylandspec,
  author       = {{Ashok Leyland LCV}},
  title        = {Bada Dost and Partner Insulated Reefer Series},
  year         = {2023},
  howpublished = {\url{https://www.ashokleyland.com/}}
}
```
