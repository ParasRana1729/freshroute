"""
FreshRoute AI: FastAPI Application Gateway

Exposes optimizer pipeline as REST per spec 5 and plan P6.
Run:
  uvicorn api.app:app --reload --port 8000
  # then open http://localhost:8000/docs (OpenAPI 3.1)
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Ensure sibling imports resolve when launched from repo root
_root = _Path(__file__).resolve().parents[1]
if str(_root) not in _sys.path:
    _sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="FreshRoute Food Redistribution Optimizer API",
    version="1.0.0-RC",
    description=(
        "Modular AI + OR pipeline for Punjab ambient cold-chain: "
        "Arrhenius shelf-life (Stage 1), demand forecasting (Stage 2), "
        "Pareto matching (Stage 3), and VRPTW routing (Stage 4). "
        "See docs/FOOD_REDISTRIBUTION_OPTIMIZER_AI_SPEC.md:5 and docs/BIBLIOGRAPHY.bib."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "FreshRoute AI Architecture Core", "url": "https://github.com/anomalyco/freshroute"},
    license_info={"name": "MIT"},
)

# CORS for frontend (src/App.jsx console)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Versioned router
app.include_router(router, prefix="/api/v1")

# Also mount unversioned alias for frontend convenience (mockData expects /api/v1/*)
@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "ok", "service": "freshroute-optimizer-api", "version": "1.0.0-RC"}

@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "healthy", "checks": {"arrhenius": "ok", "matcher": "ok", "vrp": "ok", "forecaster": "ok"}}

# Convenience: support frontend proxy expecting POST /api/v1/predict/match alias for match
@app.post("/api/v1/predict/match", tags=["alias"], include_in_schema=False)
def alias_predict_match(payload: dict):  # type: ignore[no-untyped-def]
    """Alias so frontend AI_INTEGRATION_ENDPOINTS sample payloads work verbatim."""
    from .schemas import MatchRequest
    from .routes import optimize_match

    req = MatchRequest.model_validate(payload)
    return optimize_match(req)
