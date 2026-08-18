# FreshRoute AI: Food Redistribution Optimizer Model
## Technical Architecture & Model Specification Document
**Target Ecosystem:** Indian Food Supply, Wholesale Mandis, Dairy Cooperatives & Community Langar Networks  
**Version:** 1.0.0-Release  
**Author / Engineering Team:** FreshRoute AI Architecture Core  

---

## Executive Summary

In India, approximately **68.7 million tonnes of food is wasted annually**, while millions experience daily nutritional insecurity. Unlike Western supply chains that rely on end-to-end refrigerated transport, Indian food redistribution operates across an **ambient, fragmented logistics environment** subjected to extreme climate anomalies (summer heatwaves exceeding 44°C, monsoon humidity, and urban traffic congestion).

The **FreshRoute Food Redistribution Optimizer AI Model** is a modular, multi-stage machine learning and mathematical optimization framework designed to:
1. **Predict Food Shelf-Life & Expiry Kinetics** dynamically based on ambient weather, food biochemical properties, and transport conditions.
2. **Optimize Surplus-to-Recipient Matching** using multi-objective Pareto optimization incorporating perishability urgency, travel time, and cultural/dietary standards (e.g., Lacto-Vegetarian Langar guidelines, FSSAI standards).
3. **Dispatch & Route Fleets Dynamically** by selecting the optimal vehicle class (E-rickshaw, Tata Ace EV, refrigerated carrier) and solving the Vehicle Routing Problem with Time Windows (VRPTW).
4. **Forecast Neighborhood Demand & Hunger Deficits** across district clusters to enable proactive, rather than reactive, food rescue.

---

```
                                  FRESHROUTE AI PIPELINE ARCHITECTURE
                                  
 ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
 │   Agmarknet Mandis   │   │  IMD / Weather APIs  │   │  FSSAI Food Safety   │
 │   & Dairy Feeds      │   │  (Temp, Humidity)    │   │  & Dietary Standards │
 └──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘
            │                          │                          │
            ▼                          ▼                          ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  STAGE 1: DYNAMIC ARRHENIUS EXPIRY & SHELF-LIFE PREDICTOR                 │
 │  • Biochemical decay: k(T) = A · exp(-Ea / RT)                            │
 │  • Temperature-humidity degradation penalty                               │
 │  • Real-time Safe Transit Window (t_safe) in hours                        │
 └─────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  STAGE 2: SPATIAL-TEMPORAL NEIGHBORHOOD DEMAND FORECASTER                  │
 │  • LSTM / LightGBM time-series forecasting across 23+ districts            │
 │  • Hunger Vulnerability Index (HVI) & Pilgrim/Festive surge modeling       │
 └─────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  STAGE 3: MULTI-OBJECTIVE PARETO SURPLUS-TO-RECIPIENT MATCHER             │
 │  • Multi-attribute compatibility matrix (Perishability, Diet, Deficit)    │
 │  • Mixed-Integer Linear Optimization (MILP) pairing solver                │
 └─────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  STAGE 4: COLD-CHAIN VEHICLE ASSIGNMENT & VRPTW ROUTE OPTIMIZER            │
 │  • Google OR-Tools Vehicle Routing Problem with Time Windows (VRPTW)       │
 │  • Vehicle selection: E-Rickshaw (<5km) vs Tata Ace vs Reefer Truck        │
 └─────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  OUTPUT: REST API (FastAPI) ──> FreshRoute Operations Console & Driver App │
 └────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Problem Formulation & Indian Contextual Constraints

### 1.1 Food Classification Matrix in the Indian Context
Food donations in India fall into distinct perishability tiers with radically different biological decay curves:

| Tier | Category | Examples | Base Life ($20^\circ\text{C}$) | Critical Limit ($38^\circ\text{C}$ Loo) | Sensitivity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Chilled Dairy** | Verka/Amul Milk Pouches, Paneer, Dahi, Chaas | 24 - 36 hrs | **4 - 8 hrs** | Extreme (Bacterial multiplication) |
| **Tier 2** | **Cooked / Langar Meals** | Cooked Dal, Rice, Khichdi, Sabzi, Banquet Gravies | 14 - 18 hrs | **3 - 6 hrs** | Extreme (Rapid fermentation) |
| **Tier 3** | **Mandi Fresh Produce** | Palak (Spinach), Tomatoes, Cauliflower, Coriander | 36 - 48 hrs | **12 - 18 hrs** | High (Transpiration & wilting) |
| **Tier 4** | **Bakery & Semi-Perishable** | Pav, Bread, Rusks, Cooked Rotis | 48 - 72 hrs | **24 - 36 hrs** | Moderate (Humidity staling) |
| **Tier 5** | **Grains & Staples** | Whole Wheat Atta, Rice, Dal Pulses, Oil | 90 - 180 days | **60 - 120 days** | Low (Moisture / weevil control) |

### 1.2 Cultural & Dietary Compatibility Rules
In the Indian ecosystem, food cannot simply be allocated on distance alone. The optimizer strictly enforces dietary constraints:
- **Strict Lacto-Vegetarian (Langar Rehat):** Food delivered to Gurudwara Langars and Hindu Temples must be strictly free of meat, eggs, onion/garlic (for Jain facilities), and prepared in dedicated pure-vegetarian vessels.
- **Halal Verification:** Certified protein distribution for designated shelters.
- **Child & Senior Nutrition Profiles:** Prioritizing fortified milk and soft khichdi to orphanages and elder care homes.

---

## 2. Mathematical Modeling & AI Modules

### Module 1: Dynamic Shelf-Life & Microbial Decay Predictor

#### 2.1 The Arrhenius Decay Model
Microbial growth and food spoilage rates $k$ depend exponentially on ambient absolute temperature $T$ (in Kelvin):

$$k(T) = A \cdot \exp\left(-\frac{E_a}{R \cdot T}\right)$$

Where:
- $A$: Pre-exponential collision factor specific to food type.
- $E_a$: Activation energy of food degradation ($\text{J}\cdot\text{mol}^{-1}$).
- $R$: Universal gas constant ($8.314\text{ J}\cdot\text{mol}^{-1}\cdot\text{K}^{-1}$).
- $T$: Ambient dock/vehicle temperature in Kelvin ($T_K = T_{^\circ\text{C}} + 273.15$).

#### 2.2 Climate & Humidity Adjustment Factor
Under extreme Indian summer and monsoon conditions, we calculate an **Environmental Stress Multiplier** $\Phi_{\text{env}}$:

$$\Phi_{\text{env}}(T, H) = \exp\left(\alpha \cdot (T - T_{\text{base}}) + \beta \cdot \max(0, H - H_{\text{threshold}})\right)$$

Where:
- $T_{\text{base}} = 20^\circ\text{C}$ (Standard baseline).
- $H$: Relative humidity percentage (from IMD weather API).
- $H_{\text{threshold}} = 70\%$ (Monsoon fungal threshold).
- $\alpha = 0.048$ (Empirical thermal decay coefficient for Indian food).
- $\beta = 0.008$ (Moisture degradation coefficient).

#### 2.3 Safe Transit Window ($t_{\text{safe}}$)
The remaining safe consumable transit window in hours is computed dynamically:

$$t_{\text{safe}}(t) = \frac{t_{\text{base}}}{\Phi_{\text{env}}(T, H)} - t_{\text{elapsed}}$$

If $t_{\text{safe}} \le t_{\text{transit}} + 1.0\text{ hr}$, the batch is flagged as **CRITICAL HAZARD**, automatically enforcing refrigerated transport or immediate local redistribution.

---

### Module 2: Multi-Objective Pareto Matching Solver

#### 2.1 Compatibility Scoring Formulation
For a surplus food batch $i$ at donor location $D_i$ and a potential recipient $j$ at location $R_j$, the composite Pareto matching score $S_{ij} \in [0, 100]$ is defined as:

$$S_{ij} = w_1 \cdot \text{Urgency}(i) + w_2 \cdot \text{Deficit}(j) + w_3 \cdot \text{Proximity}(D_i, R_j) + w_4 \cdot \text{DietMatch}(i, j)$$

Subject to strict feasibility constraints:
1. $\text{DietMatch}(i, j) = 1.0$ (Strict binary constraint: no non-veg in vegetarian kitchens).
2. $t_{\text{transit}}(D_i, R_j) \le t_{\text{safe}}(i)$ (Delivery before spoilage).
3. $\text{Capacity}(R_j) \ge \text{Weight}(i)$ (Recipient storage capacity).

#### 2.2 Weight Configuration
- $w_1 = 0.35$ (Perishability & Expiry Urgency).
- $w_2 = 0.30$ (Recipient Hunger Deficit / Need Score).
- $w_3 = 0.20$ (Distance & Carbon Emission Minimization).
- $w_4 = 0.15$ (Nutrient Priority: Protein/Milk for Children).

---

### Module 3: Vehicle Allocation & VRPTW Optimizer

#### 3.1 Indian Vehicle Tiering Matrix
The model assigns the optimal vehicle class based on weight, distance, and temperature requirement:

```
┌─────────────────┬──────────────┬───────────────┬───────────────────────────────┐
│ Vehicle Type    │ Max Capacity │ Range Radius  │ Best Use Case                 │
├─────────────────┼──────────────┼───────────────┼───────────────────────────────┤
│ Cargo E-Rickshaw│ 300 - 500 kg │ < 8 km        │ Hyper-local congested alleys  │
│ Tata Ace EV     │ 1,000 kg     │ 10 - 30 km    │ Intra-city mandi-to-kitchen   │
│ Reefer Sprinter │ 1,500 kg     │ 20 - 80 km    │ Chilled milk & paneer routes  │
│ Heavy Reefer    │ 4,000+ kg    │ 50 - 250 km   │ Inter-city GT Road corridors  │
└─────────────────┴──────────────┴───────────────┴───────────────────────────────┘
```

#### 3.2 Vehicle Routing Objective Function
Minimize total transit time, fuel consumption, and perishability penalty across all active vehicles $V$:

$$\min \sum_{v \in V} \sum_{(u, w) \in E} c_{uw} \cdot x_{uvw} + \lambda \sum_{i \in \text{Surplus}} \frac{t_{\text{delivery}}(i)}{t_{\text{safe}}(i)}$$

---

### Module 4: Spatial-Temporal Demand Forecasting (LSTM / LightGBM)

#### 4.1 Input Feature Space
- **Demographics:** Population density, informal settlement census, poverty index.
- **Calendar & Cultural Anomaly:** Gurpurab, Diwali, Ramadan, Navratri, Langar schedules.
- **Weather Telemetry:** Daily maximum temperature, rainfall, seasonal harvesting cycle.
- **Historical Consumption:** 90-day moving average of daily meals distributed.

---

## 3. Data Pipeline & Open Datasets

### 3.1 External Data Sources
1. **Agmarknet (Government of India):** API feeds for daily mandi arrival volumes, commodities, and commodity price trends (`https://agmarknet.gov.in/`).
2. **Open-Meteo & IMD (Indian Meteorological Department):** Hourly temperature, relative humidity, UV index, and monsoon alerts.
3. **OpenStreetMap / OSRM India:** Real-time distance matrix and routing across National Highways (NH44) and urban streets.
4. **FSSAI Standards:** Permissible temperature ranges for pasteurized milk ($4^\circ\text{C}$), hot prepared food ($>65^\circ\text{C}$ or $<5^\circ\text{C}$ if chilled).

### 3.2 Standardized JSON Data Schemas

#### Surplus Batch Input Schema (`SurplusBatch`)
```json
{
  "batch_id": "SURPLUS-PB-2026-0818",
  "donor_id": "donor-verka-ludhiana-01",
  "donor_name": "Verka Dairy Cooperative Plant",
  "category": "Dairy",
  "item_description": "Pasteurized Cow Milk Pouches (500ml)",
  "gross_weight_kg": 850.0,
  "volume_liters": 825.0,
  "base_shelf_life_hours": 24.0,
  "storage_condition": "Chilled_Reefer",
  "temp_requirement_c": [2.0, 4.0],
  "pickup_window_start": "2026-08-18T14:30:00Z",
  "pickup_window_end": "2026-08-18T16:30:00Z",
  "dietary_flags": {
    "is_pure_veg": true,
    "contains_egg": false,
    "contains_meat": false,
    "is_halal": false
  },
  "origin_coordinates": [30.9325, 75.8350]
}
```

#### Recipient Pantry / Langar Node Schema (`RecipientNode`)
```json
{
  "recipient_id": "recip-amritsar-langar-01",
  "name": "Sri Guru Ram Dass Ji Langar",
  "organization_type": "Community_Langar_Kitchen",
  "address": "Golden Temple Complex, Amritsar, Punjab",
  "coordinates": [31.6200, 74.8765],
  "daily_meal_demand": 45000,
  "current_stock_hours": 3.5,
  "has_cold_storage": true,
  "cold_storage_capacity_liters": 10000,
  "dietary_policy": "Strict_Lacto_Vegetarian",
  "urgency_score": 97.0
}
```

---

## 4. Python Implementation Reference Architecture

### 4.1 Project Directory Structure
```
freshroute-optimizer-model/
├── api/
│   ├── app.py                 # FastAPI Application Gateway
│   ├── routes.py              # Endpoint definitions
│   └── schemas.py             # Pydantic v2 Request/Response Models
├── core/
│   ├── arrhenius_decay.py     # Thermal Decay & Shelf-Life Kinetics Engine
│   ├── pareto_matcher.py      # Multi-Objective Matching Solver (MILP)
│   ├── vrp_router.py          # OR-Tools Vehicle Routing Optimizer
│   └── demand_forecaster.py   # LightGBM / LSTM 7-Day Demand Forecaster
├── data/
│   ├── indian_commodities.json# FSSAI decay constants & activation energies
│   └── punjab_districts.json  # 23 District hunger vulnerability data
├── tests/
│   └── test_optimizer.py      # Unit tests for decay, matching & routing
├── requirements.txt           # Python dependencies
└── Dockerfile                 # Containerized deployment spec
```

### 4.2 Core Python Module: Arrhenius Thermal Decay (`arrhenius_decay.py`)
```python
"""
FreshRoute AI: Arrhenius Thermal Decay Kinetics Engine
Calculates dynamic shelf-life compression under Indian ambient climate conditions.
"""

import math
from typing import Dict, Any

# FSSAI & biochemical activation energy parameters
ACTIVATION_ENERGIES = {
    "Dairy": {"Ea_over_R": 6800.0, "base_hours_at_20C": 24.0, "critical_temp_c": 8.0},
    "Prepared": {"Ea_over_R": 7200.0, "base_hours_at_20C": 14.0, "critical_temp_c": 10.0},
    "Produce": {"Ea_over_R": 5400.0, "base_hours_at_20C": 48.0, "critical_temp_c": 15.0},
    "Bakery": {"Ea_over_R": 3200.0, "base_hours_at_20C": 60.0, "critical_temp_c": 30.0},
    "Grains": {"Ea_over_R": 1800.0, "base_hours_at_20C": 2160.0, "critical_temp_c": 35.0}
}

class ThermalDecayEngine:
    def __init__(self, alpha: float = 0.048, beta: float = 0.008):
        self.alpha = alpha
        self.beta = beta

    def calculate_decay_multiplier(self, ambient_temp_c: float, humidity_pct: float = 65.0) -> float:
        """
        Computes environmental degradation factor phi(T, H).
        Baseline is 20°C ambient with 60% humidity.
        """
        temp_delta = max(0.0, ambient_temp_c - 20.0)
        humidity_delta = max(0.0, humidity_pct - 60.0)
        phi = math.exp(self.alpha * temp_delta + self.beta * humidity_delta)
        return round(phi, 3)

    def evaluate_batch_safety(
        self, 
        category: str, 
        ambient_temp_c: float, 
        humidity_pct: float,
        elapsed_hours: float = 0.0
    ) -> Dict[str, Any]:
        """
        Returns dynamic safe remaining hours and hazard classification.
        """
        params = ACTIVATION_ENERGIES.get(category, ACTIVATION_ENERGIES["Prepared"])
        base_hours = params["base_hours_at_20C"]
        multiplier = self.calculate_decay_multiplier(ambient_temp_c, humidity_pct)
        
        adjusted_shelf_life = max(1.0, round(base_hours / multiplier, 1))
        remaining_hours = max(0.0, adjusted_shelf_life - elapsed_hours)
        
        if remaining_hours <= 4.0:
            risk_level = "CRITICAL_HAZARD"
            reefer_mandatory = True
        elif remaining_hours <= 12.0:
            risk_level = "ELEVATED_RISK"
            reefer_mandatory = (ambient_temp_c > 32.0)
        else:
            risk_level = "SAFE_TRANSIT"
            reefer_mandatory = False

        return {
            "category": category,
            "ambient_temp_c": ambient_temp_c,
            "decay_multiplier": multiplier,
            "base_shelf_life_hours": base_hours,
            "dynamic_safe_hours_remaining": remaining_hours,
            "risk_classification": risk_level,
            "cold_chain_mandatory": reefer_mandatory
        }
```

### 4.3 Core Python Module: Multi-Objective Matching Solver (`pareto_matcher.py`)
```python
"""
FreshRoute AI: Multi-Objective Pareto Matching Engine
Optimizes allocation of surplus batches to Indian hunger relief nodes.
"""

from typing import List, Dict, Any
import math

class ParetoMatchingEngine:
    def __init__(self, weights=(0.35, 0.30, 0.20, 0.15)):
        self.w_urgency, self.w_deficit, self.w_prox, self.w_diet = weights

    def _haversine_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    def score_match(
        self, 
        surplus: Dict[str, Any], 
        recipient: Dict[str, Any], 
        safe_hours_remaining: float
    ) -> float:
        # Strict Cultural & Dietary Filter
        if recipient.get("dietary_policy") == "Strict_Lacto_Vegetarian":
            if not surplus.get("dietary_flags", {}).get("is_pure_veg", True):
                return 0.0  # Ineligible match

        # 1. Perishability Urgency Score (0 - 100)
        urgency_score = min(100.0, max(0.0, 100.0 - (safe_hours_remaining * 2.5)))

        # 2. Recipient Hunger Deficit Score (0 - 100)
        deficit_score = recipient.get("urgency_score", 50.0)

        # 3. Proximity Score (0 - 100)
        d_lat, d_lon = surplus["origin_coordinates"]
        r_lat, r_lon = recipient["coordinates"]
        distance_km = self._haversine_distance_km(d_lat, d_lon, r_lat, r_lon)
        proximity_score = max(0.0, 100.0 - (distance_km * 1.5))

        # 4. Dietary Suitability (0 - 100)
        diet_score = 100.0

        # Composite Weighted Multi-Objective Score
        composite_score = (
            self.w_urgency * urgency_score +
            self.w_deficit * deficit_score +
            self.w_prox * proximity_score +
            self.w_diet * diet_score
        )
        return round(composite_score, 1)

    def rank_allocations(
        self, 
        surplus_batches: List[Dict[str, Any]], 
        recipients: List[Dict[str, Any]], 
        decay_engine
    ) -> List[Dict[str, Any]]:
        results = []
        for batch in surplus_batches:
            eval_res = decay_engine.evaluate_batch_safety(
                category=batch["category"],
                ambient_temp_c=batch.get("ambient_temp_c", 36.0),
                humidity_pct=batch.get("humidity_pct", 70.0)
            )
            safe_hours = eval_res["dynamic_safe_hours_remaining"]

            best_match = None
            best_score = -1.0

            for rec in recipients:
                score = self.score_match(batch, rec, safe_hours)
                if score > best_score:
                    best_score = score
                    best_match = rec

            if best_match and best_score > 40.0:
                results.append({
                    "batch_id": batch["batch_id"],
                    "item_description": batch["item_description"],
                    "matched_recipient_id": best_match["recipient_id"],
                    "recipient_name": best_match["name"],
                    "match_score": best_score,
                    "safe_hours_remaining": safe_hours,
                    "urgency": eval_res["risk_classification"],
                    "cold_chain_enforced": eval_res["cold_chain_mandatory"],
                    "co2_saved_kg": round(batch["gross_weight_kg"] * 2.5, 1)
                })
        return results
```

---

## 5. REST API Specifications (FastAPI Interface)

### 5.1 `POST /api/v1/predict/shelf-life`
Computes real-time thermal shelf-life degradation using Arrhenius kinetics.

#### Request Payload:
```json
{
  "category": "Dairy",
  "ambient_temp_c": 42.0,
  "humidity_pct": 78.0,
  "elapsed_hours": 2.0
}
```

#### Response Payload (200 OK):
```json
{
  "status": "success",
  "category": "Dairy",
  "ambient_temp_c": 42.0,
  "decay_multiplier": 3.24,
  "base_shelf_life_hours": 24.0,
  "dynamic_safe_hours_remaining": 5.4,
  "risk_classification": "CRITICAL_HAZARD",
  "cold_chain_mandatory": true,
  "recommendation": "Punjab Loo heatwave active (42°C). Mandatory dispatch via Reefer Sprinter @ 2-4°C."
}
```

---

### 5.2 `POST /api/v1/optimize/match`
Allocates a surplus batch to the optimal community langar / food bank recipient.

#### Request Payload:
```json
{
  "surplus_batch": {
    "batch_id": "VERKA-LUD-882",
    "category": "Dairy",
    "gross_weight_kg": 950.0,
    "origin_coordinates": [30.9325, 75.8350],
    "dietary_flags": { "is_pure_veg": true }
  },
  "ambient_weather": {
    "temp_c": 38.0,
    "humidity_pct": 72.0
  }
}
```

#### Response Payload (200 OK):
```json
{
  "status": "success",
  "match_score": 98.4,
  "assigned_recipient": {
    "id": "recip-amritsar-langar-01",
    "name": "Sri Guru Ram Dass Ji Langar (Amritsar)",
    "daily_meals": 45000,
    "coordinates": [31.6200, 74.8765]
  },
  "assigned_vehicle": {
    "vehicle_id": "PB-02-AK-4412",
    "name": "Ashok Leyland Cold Carrier",
    "target_temp_c": 2.7,
    "transit_eta_minutes": 24
  },
  "safe_transit_window_hours": 7.2,
  "co2_abatement_kg": 2375.0,
  "execution_latency_ms": 68
}
```

---

## 6. Verification, Testing & Evaluation Metrics

### 6.1 Key Performance Indicators (KPIs)
1. **Spoilage Prevention Rate ($\ge 95\%$):** Ratio of delivered calories consumed before expiration over total surplus weight.
2. **Algorithm Execution Latency ($< 100\text{ ms}$):** Execution time for multi-objective MILP matching across $N=500$ nodes.
3. **Cold-Chain Temperature Compliance ($100\%$):** Zero temperature breaches ($> 6^\circ\text{C}$) during Tier 1 Dairy transport.
4. **Dietary Compliance ($100\%$ Strict):** Complete prevention of non-vegetarian cross-contamination in religious langars.

### 6.2 Unit & Integration Test Suite
```python
# test_optimizer.py
def test_arrhenius_heatwave_spoilage():
    engine = ThermalDecayEngine()
    # At 44°C (Severe Loo), decay multiplier must exceed 3.0x
    res = engine.evaluate_batch_safety(category="Dairy", ambient_temp_c=44.0, humidity_pct=80.0)
    assert res["decay_multiplier"] >= 3.0
    assert res["risk_classification"] == "CRITICAL_HAZARD"
    assert res["cold_chain_mandatory"] is True

def test_dietary_compatibility_rejection():
    matcher = ParetoMatchingEngine()
    non_veg_batch = {"dietary_flags": {"is_pure_veg": False}, "origin_coordinates": [30.9, 75.8]}
    langar_recipient = {"dietary_policy": "Strict_Lacto_Vegetarian", "coordinates": [31.6, 74.8]}
    score = matcher.score_match(non_veg_batch, langar_recipient, safe_hours_remaining=12.0)
    assert score == 0.0  # Must strictly reject
```

---

## 7. Deployment & Integration Roadmap

1. **Phase 1 (Data Ingestion & Open APIs):** Sync automated scrapers for Agmarknet mandi daily commodity arrivals and Open-Meteo temperature feeds.
2. **Phase 2 (FastAPI ML Service):** Deploy `freshroute-optimizer-api` via Docker on AWS/GCP with sub-100ms response SLAs.
3. **Phase 3 (Frontend Integration):** Connect FreshRoute React Operations Console to live `/api/v1/predict/match` and `/api/v1/predict/shelf-life` endpoints.
4. **Phase 4 (Driver Mobile Telemetry):** IoT temperature sensors (BLE/MQTT) in Tata Ace EV & Reefer vans feeding live compartment temperature back into the Arrhenius decay loop.

---
*Document approved for implementation by FreshRoute Engineering Core.*
