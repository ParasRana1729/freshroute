"""Phase 2 unit and anti-leakage tests for fetch_weather.py and fetch_apmc_history.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import fetch_apmc_history as fah  # noqa: E402
from scripts import fetch_weather as fw  # noqa: E402


def test_weighted_call_estimator_matches_plan() -> None:
    # 220 districts * (730 / 14) * (5 / 10) = 5,735.71 weighted calls
    w5 = fw.estimate_weighted_calls(220, 730, 5)
    w10 = fw.estimate_weighted_calls(220, 730, 10)
    assert 5700 <= w5 <= 5750
    assert 11400 <= w10 <= 11500


def test_district_centroids_exclude_imputed_and_cover_top6(tmp_path: Path) -> None:
    cfg = fw.load_config()
    raw_path = ROOT / cfg["paths"]["raw_apmc"]
    if not raw_path.exists():
        pytest.skip("Raw APMC CSV not present locally")

    out_csv = tmp_path / "district_centroids.csv"
    centroids = fw.extract_verified_district_centroids(
        raw_csv_path=raw_path,
        target_states=cfg["phase_2"]["states"],
        output_csv=out_csv,
    )
    assert out_csv.exists()
    assert len(centroids) == 226
    assert set(centroids["coord_source"]).issubset({"raw_mandi_median", "census_lgd_centroid"})
    assert "state_median_imputed" not in set(centroids["coord_source"])
    assert (centroids["coord_source"] == "census_lgd_centroid").sum() == 13
    assert centroids[["latitude", "longitude"]].isna().sum().sum() == 0


def test_weather_cache_and_quota_guard(tmp_path: Path) -> None:
    centroids = pd.DataFrame(
        [
            {"state_name": "TAMIL NADU", "district_name": "CHENGALPATTU", "latitude": 12.69, "longitude": 79.97, "coord_source": "census_lgd_centroid"},
            {"state_name": "TAMIL NADU", "district_name": "KARUR", "latitude": 10.95, "longitude": 78.08, "coord_source": "census_lgd_centroid"},
            {"state_name": "MAHARASHTRA", "district_name": "PUNE", "latitude": 18.52, "longitude": 73.85, "coord_source": "raw_mandi_median"},
        ]
    )
    vars_list = ["precipitation_sum", "temperature_2m_max", "relative_humidity_2m_mean"]

    def _fake_payload(lat: float, lon: float) -> dict:
        return {
            "latitude": lat,
            "longitude": lon,
            "daily": {
                "time": ["2025-11-01", "2025-11-02", "2025-11-03", "2025-11-04"],
                "precipitation_sum": [1.0, 2.0, 0.0, 5.0],
                "temperature_2m_max": [30.0, 31.0, 32.0, 29.0],
                "relative_humidity_2m_mean": [70.0, 75.0, 80.0, 85.0],
            },
        }

    mock_session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [
        _fake_payload(12.69, 79.97),
        _fake_payload(10.95, 78.08),
    ]
    mock_session.get.return_value = resp

    # Budget allows only 2 of 3 locations (4 days, 3 vars => 0.0857/loc => 0.1714 for 2)
    df1, stats1 = fw.fetch_open_meteo_weather(
        centroids_df=centroids,
        start_date="2025-11-01",
        end_date="2025-11-04",
        variables=vars_list,
        cache_dir=tmp_path / "cache",
        batch_size=3,
        max_weighted_budget=0.20,
        session=mock_session,
    )
    assert stats1["n_fetched_this_run"] == 2
    assert stats1["n_deferred_for_next_batch"] == 1
    assert mock_session.get.call_count == 1
    assert len(df1) == 8

    # Second run fetches only the 1 remaining district (cached 2 make 0 HTTP calls)
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = _fake_payload(18.52, 73.85)  # single-dict response
    mock_session.get.return_value = resp2

    df2, stats2 = fw.fetch_open_meteo_weather(
        centroids_df=centroids,
        start_date="2025-11-01",
        end_date="2025-11-04",
        variables=vars_list,
        cache_dir=tmp_path / "cache",
        batch_size=3,
        max_weighted_budget=0.20,
        session=mock_session,
    )
    assert stats2["n_cached_before_run"] == 2
    assert stats2["n_fetched_this_run"] == 1
    assert stats2["n_deferred_for_next_batch"] == 0
    assert len(df2) == 12

    # Causal check: changing day 4 weather must not alter day 1-3 engineered features
    eng_base = fw.engineer_weather_features(df2)
    df2_pert = df2.copy()
    df2_pert.loc[df2_pert["date"] == "2025-11-04", "precipitation_sum"] = 999.0
    eng_pert = fw.engineer_weather_features(df2_pert)
    mask_early = eng_base["date"] < "2025-11-04"
    pd.testing.assert_frame_equal(eng_base[mask_early], eng_pert[mask_early])


def test_apmc_rejects_forbidden_datagov_and_causal_walk_forward() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        fah.validate_apmc_source_url("https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070")

    # Build 8 months of synthetic scoped APMC data (including 1 same-day duplicate & 1 out-of-scope crop)
    dates = pd.date_range("2024-01-01", "2024-08-31", freq="D")
    rows = []
    for d in dates:
        rows.append(
            {
                "Price Date": d.strftime("%Y-%m-%d"),
                "State": "Maharashtra",
                "District": "Pune",
                "Market": "Pune Mandi",
                "Commodity": "Tomato",
                "Variety": "Local",
                "Grade": "FAQ",
                "Arrivals (Tonnes)": 10.0 + (d.day % 5),
                "Modal Price (Rs./Quintal)": 2000.0 + (d.month * 50),
            }
        )
    # Duplicate on 2024-01-01 + out-of-scope crop
    rows.append(
        {
            "Price Date": "2024-01-01",
            "State": "Maharashtra",
            "District": "Pune",
            "Market": "Pune Mandi",
            "Commodity": "Tomato",
            "Variety": "Local",
            "Grade": "FAQ",
            "Arrivals (Tonnes)": 5.0,
            "Modal Price (Rs./Quintal)": 2300.0,
        }
    )
    rows.append(
        {
            "Price Date": "2024-01-01",
            "State": "Maharashtra",
            "District": "Pune",
            "Market": "Pune Mandi",
            "Commodity": "Saffron",
            "Variety": "Local",
            "Grade": "FAQ",
            "Arrivals (Tonnes)": 1.0,
            "Modal Price (Rs./Quintal)": 99000.0,
        }
    )
    raw = pd.DataFrame(rows)
    norm = fah.normalize_and_dedupe_apmc(raw, ["MAHARASHTRA"], ["TOMATO", "ONION"])
    assert len(norm) == len(dates)
    assert set(norm["commodity_name"]) == {"TOMATO"}
    jan1 = norm[norm["date"] == "2024-01-01"].iloc[0]
    assert np.isclose(jan1["arrival_tonnes"], 16.0, atol=1e-4)  # 11.0 + 5.0
    assert np.isclose(jan1["price_per_kg"], (11 * 20.5 + 5 * 23.0) / 16.0, atol=1e-3)

    enriched = fah.add_calendar_season_features(fah.build_seasonal_baselines(norm))
    assert {"arr_mean_30d", "arr_mean_90d", "prior_year_month_log_arr", "days_to_major_festival", "is_kharif_harvest_peak"}.issubset(enriched.columns)

    folds = fah.generate_walk_forward_folds(enriched, min_train_months=6, test_window_months=1, n_folds=3)
    assert len(folds) == 2  # months 7 and 8
    for fold in folds:
        assert fold["train"]["target_date"].max() < fold["test"]["date"].min()
