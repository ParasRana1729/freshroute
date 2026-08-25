"""
TFT stretch stub — Temporal Fusion Transformer (P3 L3.2) [@lim2021tft].

Minimal interface so P3 pipeline can import and benchmark later.
Full TFT requires pytorch-forecasting + static/known future covariates
(district HVI, festival calendar). For now, delegates to LSTM and logs
that TFT is pending — keeps CI green while reserving API.

Usage:
  from core.tft_stub import TFTForecaster
  tft = TFTForecaster()
  tft.forecast("ludhiana", 7)  # delegates to HungerDemandForecaster stub
"""

from __future__ import annotations

from typing import Any, Dict, List

from .demand_forecaster import HungerDemandForecaster


class TFTForecaster(HungerDemandForecaster):
    """Thin TFT wrapper — inherits LightGBM/LSTM but tags model as tft-stub."""

    def forecast(self, district_id: str, horizon_days: int = 7, include_pilgrim_surge: bool = True) -> Dict[str, Any]:  # type: ignore[override]
        base = super().forecast(district_id, horizon_days, include_pilgrim_surge)
        # Tag as TFT stub for future A/B
        base = dict(base)
        base["model"] = "tft-stub-v0"
        base["citation"] = "[@lim2021tft — stub, delegates to LightGBM/LSTM]"
        base["note"] = "TFT not yet trained; using LightGBM/LSTM base. See docs/model-cards/demand_forecaster.md"
        return base

    def batch_forecast(self, horizon_days: int = 7, include_pilgrim_surge: bool = True) -> List[Dict[str, Any]]:  # type: ignore[override]
        return [self.forecast(d.get("district_id", ""), horizon_days, include_pilgrim_surge) for d in self.districts]
