"""FreshRoute Core — optimizer modules.

Stages:
  Stage 1: core.arrhenius_decay — ThermalDecayEngine
  Stage 2: core.demand_forecaster — HungerDemandForecaster
  Stage 3: core.pareto_matcher — ParetoMatchingEngine
  Stage 4: core.vrp_router — VRPRouter

See docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md and docs/IMPLEMENTATION_PLAN.md.
"""

__all__ = ["arrhenius_decay", "pareto_matcher", "vrp_router", "demand_forecaster"]
