"""
FreshRoute AI: Spatial-Temporal Demand Forecaster (Stage 2)

Predicts 7-day meal shortfall across 23 Punjab districts (spec 4.1).

Feature space (spec 4.1:168-172):
  - Demographics: population density, informal settlement, MPI (NITI 2023)
  - Calendar & cultural anomaly: Gurpurab, Diwali, Ramadan, Navratri, Langar schedules
  - Weather telemetry: daily max temp, rainfall, harvesting cycle (Agmarknet/mandi)
  - Historical consumption: 90-day moving average of daily meals distributed

Models (P3):
  - LightGBM baseline [@ke2017lightgbm] — tabular, categorical, WAPE target <18%
  - LSTM sequence [@hochreiter1997lstm] with district embeddings
  - Stretch: Temporal Fusion Transformer [@lim2021tft] multi-horizon
  - HVI fusion: deficit(j) weighted into matcher w2=0.30

Status (P0/P1): Stub with synthetic priors from src/data/mockData.js
 DISTRICT_DEMAND_FORECAST; full ML training arrives in P3 loops.
 Implements same interface expected by pipeline so Stages 3-4 can integrate now.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


class HungerDemandForecaster:
    """7-day demand forecaster stub (P1) → trained model (P3).

    Methods
    -------
    forecast(district_id, horizon_days=7) -> dict with gap_lbs, intervals
    batch_forecast(horizon_days=7) -> list of districts with forecast
    """

    def __init__(self, districts_path: str | Path | None = None) -> None:
        if districts_path is None:
            default = Path(__file__).parent.parent / "data" / "punjab_districts.json"
            if default.exists():
                districts_path = default
        self.districts: List[Dict[str, Any]] = []
        self._path = districts_path
        if districts_path is not None and Path(districts_path).exists():
            try:
                data = json.loads(Path(districts_path).read_text(encoding="utf-8"))
                self.districts = data.get("districts", [])
            except Exception:
                self.districts = []

    def _synthetic_daily_series(self, weekly_lbs: float, days: int = 7) -> List[float]:
        """Generate deterministic synthetic daily demand around weekly/7."""
        base_daily = weekly_lbs / 7.0
        rng = random.Random(hash((weekly_lbs, days)) % (2**32))
        return [round(base_daily * (1 + rng.uniform(-0.08, 0.12)), 1) for _ in range(days)]

    def forecast(self, district_id: str, horizon_days: int = 7, include_pilgrim_surge: bool = True) -> Dict[str, Any]:
        """Forecast single district.

        In P3 this will call LightGBM/LSTM with engineered features.
        Today returns deterministic synthetic based on punjab_districts.json weekly values,
        with pilgrim surge injection for Amritsar during festival weeks.

        Returns
        -------
        dict: district_id, district_name, horizon_days, forecast_demand_lbs (list),
              weekly_total, gap_lbs_estimate, hunger_vulnerability_index, primary_need
        """
        district = next((d for d in self.districts if d.get("district_id") == district_id), None)
        if district is None:
            # Fallback to synthetic
            return {
                "district_id": district_id,
                "district_name": district_id,
                "horizon_days": horizon_days,
                "forecast_demand_lbs": [0.0] * horizon_days,
                "weekly_total_lbs": 0.0,
                "gap_lbs_estimate": 0.0,
                "hunger_vulnerability_index": 50,
                "error": "district not found in base table; using zeros",
            }

        weekly = float(district.get("weekly_forecast_demand_lbs", 0))
        gap = float(district.get("gap_lbs", 0))
        # Pilgrim surge: +8% in Amritsar if flag set (spec mockData)
        if include_pilgrim_surge and district_id == "amritsar":
            weekly = weekly * 1.08

        daily = self._synthetic_daily_series(weekly, horizon_days)
        return {
            "district_id": district_id,
            "district_name": district.get("district_name", district_id),
            "horizon_days": horizon_days,
            "forecast_demand_lbs": daily,
            "weekly_total_lbs": round(sum(daily), 1),
            "gap_lbs_estimate": round(gap * (horizon_days / 7.0), 1),
            "hunger_vulnerability_index": district.get("hunger_vulnerability_index", 50),
            "primary_need": district.get("primary_need", ""),
            "coordinates": district.get("coordinates"),
            "model": "stub-synthetic-v1",
            "citation": "[@ke2017lightgbm; @hochreiter1997lstm — stub, see P3]",
        }

    def batch_forecast(self, horizon_days: int = 7, include_pilgrim_surge: bool = True) -> List[Dict[str, Any]]:
        """Forecast all 23 districts."""
        return [self.forecast(d.get("district_id", ""), horizon_days, include_pilgrim_surge) for d in self.districts]

    def get_deficit_score(self, district_id: str) -> float:
        """Return Deficit(j) 0-100 for matcher w2 — maps HVI + gap."""
        d = next((x for x in self.districts if x.get("district_id") == district_id), None)
        if not d:
            return 50.0
        hvi = float(d.get("hunger_vulnerability_index", 50))
        gap = float(d.get("gap_lbs", 0))
        # Deficit higher when gap negative (shortfall) and HVI high
        gap_penalty = max(0.0, min(20.0, -gap / 200.0))  # -3500 => +17.5
        return round(min(100.0, hvi * 0.8 + gap_penalty + 10.0), 1)
