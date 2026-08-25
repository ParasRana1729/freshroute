"""API contract tests — spec 5.1-5.2 + fallback for frontend mock payloads."""

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "healthy"


def test_openapi_exists():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    j = r.json()
    assert "/api/v1/predict/shelf-life" in str(j)


def test_predict_shelf_life_contract():
    payload = {"category": "Dairy", "ambient_temp_c": 42.0, "humidity_pct": 78.0, "elapsed_hours": 2.0}
    r = client.post("/api/v1/predict/shelf-life", json=payload)
    assert r.status_code == 200
    b = r.json()
    assert b["decay_multiplier"] >= 3.0
    assert b["cold_chain_mandatory"] is True
    assert b["risk_classification"] == "CRITICAL_HAZARD"


def test_optimize_match_spec_example():
    # Mirrors spec 5.2 request shape
    payload = {
        "surplus_batch": {
            "batch_id": "VERKA-LUD-882",
            "donor_id": "donor-verka-ludhiana-01",
            "category": "Dairy",
            "item_description": "Pasteurized Cow Milk Pouches",
            "gross_weight_kg": 950.0,
            "origin_coordinates": [30.9325, 75.8350],
            "dietary_flags": {"is_pure_veg": True},
        },
        "ambient_weather": {"temp_c": 38.0, "humidity_pct": 72.0},
    }
    r = client.post("/api/v1/optimize/match", json=payload)
    assert r.status_code == 200
    b = r.json()
    assert b["match_score"] > 40
    assert "assigned_vehicle" in b
    assert b["safe_transit_window_hours"] > 0


def test_forecast_demand_get():
    r = client.get("/api/v1/forecast/demand?district_id=ludhiana&horizon_days=7")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list) and len(arr) == 1
    assert len(arr[0]["forecast_demand_lbs"]) == 7
    assert arr[0]["forecast_demand_lower_lbs"] is not None
    assert arr[0]["forecast_demand_upper_lbs"] is not None
    assert len(arr[0]["forecast_demand_lower_lbs"]) == 7
    assert len(arr[0]["forecast_demand_upper_lbs"]) == 7
    for low, mid, high in zip(arr[0]["forecast_demand_lower_lbs"], arr[0]["forecast_demand_lbs"], arr[0]["forecast_demand_upper_lbs"]):
        assert low <= mid <= high


def test_routing():
    r = client.post(
        "/api/v1/optimize/routing",
        json={
            "pickup_nodes": [{"batch_id": "b1", "origin_coordinates": [30.9325, 75.8350], "gross_weight_kg": 500, "cold_chain_mandatory": True}],
            "dropoff_nodes": [{"recipient_id": "r1", "coordinates": [31.62, 74.8765]}],
        },
    )
    assert r.status_code == 200
    b = r.json()
    assert b["total_distance_km"] > 0
