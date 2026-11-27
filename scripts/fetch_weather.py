"""FreshRoute Phase 2: District-Centroid Weather Pipeline (Open-Meteo Only).

Plan v3.1 requirements:
  - Exclude the 36.7% state-median imputed coordinates; extract verified raw
    district centroids and fill the missing top-6-state district centroids via
    verified Census/LGD district-headquarters coordinates.
  - Query Open-Meteo Historical Weather API (`archive-api.open-meteo.com/v1/archive`)
    for 5-10 daily variables across ~226 top-6-state districts, disk-cached per
    district/window so 12-24 month pulls complete in 1-2 daily batches under the
    10,000 weighted calls/day free quota.
  - Engineer strictly <= t rolling weather features (`precip_sum_3d`,
    `precip_sum_7d`, `temp_max_mean_3d`, `humidity_mean_3d`, `et0_sum_3d`,
    `heat_spoilage_index`).

Run:
  python scripts/fetch_weather.py --dry-run
  python scripts/fetch_weather.py --start-date 2025-10-27 --end-date 2025-11-19 --limit-districts 5
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "experiment_config.yaml"

# Verified Census/LGD district-headquarters coordinates for top-6-state districts
# where raw APMC records had 100% missing lat/lon (never state-median imputed).
CENSUS_LGD_CENTROIDS: dict[tuple[str, str], tuple[float, float]] = {
    ("TAMIL NADU", "CHENGALPATTU"): (12.69184, 79.97661),
    ("TAMIL NADU", "CUDDALORE"): (11.75617, 79.76693),
    ("TAMIL NADU", "DHARMAPURI"): (12.12770, 78.15794),
    ("TAMIL NADU", "KANCHEEPURAM"): (12.83515, 79.70006),
    ("TAMIL NADU", "KARUR"): (10.95771, 78.08095),
    ("TAMIL NADU", "KRISHNAGIRI"): (12.51921, 78.21382),
    ("TAMIL NADU", "PERAMBALUR"): (11.23333, 78.88333),
    ("TAMIL NADU", "RANIPET"): (12.92471, 79.33331),
    ("TAMIL NADU", "SIVAGANGA"): (9.84701, 78.48358),
    ("TAMIL NADU", "THE NILGIRIS"): (11.41340, 76.69521),
    ("TAMIL NADU", "THENI"): (10.01115, 77.47772),
    ("TAMIL NADU", "THIRUVALLUR"): (13.14376, 79.90889),
    ("TAMIL NADU", "TIRUCHIRAPPALLI"): (10.81550, 78.69651),
}


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).strip().upper()).strip("_")


def estimate_weighted_calls(n_locations: int, n_days: int, n_variables: int) -> float:
    """Open-Meteo weighted call formula: nLocations * (nDays / 14) * (nVars / 10)."""
    if n_locations <= 0 or n_days <= 0 or n_variables <= 0:
        return 0.0
    return float(n_locations) * (float(n_days) / 14.0) * (float(n_variables) / 10.0)


def extract_verified_district_centroids(
    raw_csv_path: Path | str,
    target_states: list[str],
    fallback_centroids: dict[tuple[str, str], tuple[float, float]] | None = None,
    output_csv: Path | str | None = None,
) -> pd.DataFrame:
    """Build district centroids from NON-IMPUTED raw APMC rows + Census/LGD fallback."""
    fallback = CENSUS_LGD_CENTROIDS if fallback_centroids is None else fallback_centroids
    states_upper = {s.strip().upper() for s in target_states}

    usecols = ["state_name", "state_code", "district_name", "district_code", "latitude", "longitude"]
    raw = pd.read_csv(raw_csv_path, usecols=usecols, low_memory=False)
    raw["state_name"] = raw["state_name"].astype(str).str.strip().str.upper()
    raw["district_name"] = raw["district_name"].astype(str).str.strip().str.upper()
    raw = raw[raw["state_name"].isin(states_upper)].copy()
    raw = raw.dropna(subset=["state_name", "district_name"])

    all_districts = (
        raw.groupby(["state_name", "district_name"], as_index=False)
        .agg(
            state_code=("state_code", "first"),
            district_code=("district_code", "first"),
            n_total_rows=("district_name", "size"),
        )
    )

    non_imputed = raw.dropna(subset=["latitude", "longitude"]).copy()
    non_imputed = non_imputed[
        (non_imputed["latitude"].between(-90.0, 90.0))
        & (non_imputed["longitude"].between(-180.0, 180.0))
    ]
    observed = (
        non_imputed.groupby(["state_name", "district_name"], as_index=False)
        .agg(
            latitude=("latitude", "median"),
            longitude=("longitude", "median"),
            n_non_imputed_rows=("latitude", "size"),
        )
    )

    centroids = all_districts.merge(observed, on=["state_name", "district_name"], how="left")
    centroids["n_non_imputed_rows"] = centroids["n_non_imputed_rows"].fillna(0).astype(int)
    centroids["coord_source"] = np.where(
        centroids["latitude"].notna() & centroids["longitude"].notna(),
        "raw_mandi_median",
        "missing",
    )

    missing_mask = centroids["coord_source"] == "missing"
    for idx in centroids.index[missing_mask]:
        key = (str(centroids.at[idx, "state_name"]), str(centroids.at[idx, "district_name"]))
        if key in fallback:
            lat, lon = fallback[key]
            centroids.at[idx, "latitude"] = float(lat)
            centroids.at[idx, "longitude"] = float(lon)
            centroids.at[idx, "coord_source"] = "census_lgd_centroid"

    unresolved = centroids[centroids["coord_source"] == "missing"]
    if not unresolved.empty:
        pairs = list(zip(unresolved["state_name"], unresolved["district_name"]))
        raise ValueError(f"Unresolved district centroids without imputed fallback: {pairs}")

    centroids = centroids.sort_values(["state_name", "district_name"]).reset_index(drop=True)
    if output_csv is not None:
        out_path = Path(output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        centroids.to_csv(out_path, index=False)
    return centroids


def _cache_file_path(
    cache_dir: Path, state_name: str, district_name: str, start_date: str, end_date: str
) -> Path:
    return cache_dir / f"{_slugify(state_name)}__{_slugify(district_name)}__{start_date}__{end_date}.json"


def _parse_single_location_payload(
    row: pd.Series, payload: dict[str, Any], variables: list[str]
) -> pd.DataFrame:
    daily = payload.get("daily", {})
    times = daily.get("time", [])
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(times),
            "state_name": str(row["state_name"]),
            "district_name": str(row["district_name"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "coord_source": str(row["coord_source"]),
        }
    )
    for var in variables:
        out[var] = pd.to_numeric(daily.get(var, [np.nan] * len(times)), errors="coerce")
    return out


def fetch_open_meteo_weather(
    centroids_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    variables: list[str],
    cache_dir: Path | str,
    endpoint: str = "https://archive-api.open-meteo.com/v1/archive",
    batch_size: int = 25,
    max_weighted_budget: float = 8500.0,
    output_csv: Path | str | None = None,
    session: requests.Session | None = None,
    max_retries: int = 5,
    backoff_seconds: float = 1.5,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch district daily weather with disk cache and weighted-call quota guard."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    n_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days + 1
    if n_days <= 0:
        raise ValueError(f"end_date ({end_date}) must be >= start_date ({start_date})")

    cached_frames: list[pd.DataFrame] = []
    pending_rows: list[pd.Series] = []
    for _, row in centroids_df.iterrows():
        cfile = _cache_file_path(
            cache_path, str(row["state_name"]), str(row["district_name"]), start_date, end_date
        )
        if cfile.exists():
            payload = json.loads(cfile.read_text(encoding="utf-8"))
            cached_frames.append(_parse_single_location_payload(row, payload, variables))
        else:
            pending_rows.append(row)

    weighted_used = 0.0
    http_requests = 0
    fetched_count = 0
    deferred_count = 0
    own_session = session is None
    client = requests.Session() if own_session else session

    try:
        for i in range(0, len(pending_rows), batch_size):
            batch = pending_rows[i : i + batch_size]
            batch_weight = estimate_weighted_calls(len(batch), n_days, len(variables))
            if weighted_used + batch_weight > max_weighted_budget:
                # Shrink batch if a partial batch still fits within remaining budget
                per_loc_weight = estimate_weighted_calls(1, n_days, len(variables))
                fit_n = int((max_weighted_budget - weighted_used) // max(per_loc_weight, 1e-9))
                if fit_n <= 0:
                    deferred_count += len(pending_rows) - i
                    break
                deferred_count += len(pending_rows) - (i + fit_n)
                batch = batch[:fit_n]
                batch_weight = estimate_weighted_calls(len(batch), n_days, len(variables))
                stop_after_batch = True
            else:
                stop_after_batch = False

            params = {
                "latitude": ",".join(f"{float(r['latitude']):.6f}" for r in batch),
                "longitude": ",".join(f"{float(r['longitude']):.6f}" for r in batch),
                "start_date": start_date,
                "end_date": end_date,
                "daily": ",".join(variables),
                "timezone": "Asia/Kolkata",
            }

            payload = None
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    resp = client.get(endpoint, params=params, timeout=30)
                    if resp.status_code == 429:
                        msg = resp.text[:300]
                        if "daily" in msg.lower():
                            raise RuntimeError(f"Open-Meteo daily quota exceeded: {msg}")
                        retry_after = resp.headers.get("Retry-After")
                        wait_s = float(retry_after) if retry_after else (62.0 if "minutely" in msg.lower() else backoff_seconds * (2**attempt))
                        last_err = requests.HTTPError(
                            f"Open-Meteo rate limit HTTP 429: {msg}", response=resp
                        )
                        if attempt < max_retries - 1:
                            if backoff_seconds > 0:
                                time.sleep(wait_s)
                            continue
                        raise last_err
                    if resp.status_code in (500, 502, 503, 504):
                        raise requests.HTTPError(
                            f"Open-Meteo transient HTTP {resp.status_code}: {resp.text[:200]}",
                            response=resp,
                        )
                    resp.raise_for_status()
                    payload = resp.json()
                    break
                except RuntimeError:
                    raise
                except Exception as exc:
                    last_err = exc
                    if attempt < max_retries - 1 and backoff_seconds > 0:
                        time.sleep(backoff_seconds * (2**attempt))
            if payload is None:
                raise RuntimeError(f"Open-Meteo request failed after {max_retries} attempts: {last_err}")

            http_requests += 1
            weighted_used += batch_weight
            items = [payload] if isinstance(payload, dict) else list(payload)
            if len(items) != len(batch):
                raise ValueError(
                    f"Open-Meteo returned {len(items)} location payloads for {len(batch)} requested districts"
                )

            for row, loc_payload in zip(batch, items):
                cfile = _cache_file_path(
                    cache_path, str(row["state_name"]), str(row["district_name"]), start_date, end_date
                )
                cfile.write_text(json.dumps(loc_payload), encoding="utf-8")
                cached_frames.append(_parse_single_location_payload(row, loc_payload, variables))
                fetched_count += 1

            if stop_after_batch:
                break
    finally:
        if own_session:
            client.close()

    weather_df = (
        pd.concat(cached_frames, ignore_index=True)
        if cached_frames
        else pd.DataFrame(
            columns=["date", "state_name", "district_name", "latitude", "longitude", "coord_source", *variables]
        )
    )
    if not weather_df.empty:
        weather_df = weather_df.sort_values(["state_name", "district_name", "date"]).reset_index(drop=True)

    if output_csv is not None and not weather_df.empty:
        out_path = Path(output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        weather_df.to_csv(out_path, index=False)

    stats = {
        "n_districts_requested": len(centroids_df),
        "n_cached_before_run": len(centroids_df) - len(pending_rows),
        "n_fetched_this_run": fetched_count,
        "n_deferred_for_next_batch": deferred_count,
        "http_requests": http_requests,
        "weighted_calls_used": round(weighted_used, 2),
        "weighted_budget": max_weighted_budget,
        "rows": len(weather_df),
    }
    return weather_df, stats


def engineer_weather_features(weather_df: pd.DataFrame) -> pd.DataFrame:
    """Compute strictly <= t district weather features (no future rows accessed)."""
    if weather_df.empty:
        return weather_df.copy()

    df = weather_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["state_name", "district_name", "date"]).reset_index(drop=True)
    grp = df.groupby(["state_name", "district_name"], sort=False)

    if "precipitation_sum" in df.columns:
        df["precip_sum_3d"] = grp["precipitation_sum"].transform(lambda s: s.rolling(3, min_periods=1).sum())
        df["precip_sum_7d"] = grp["precipitation_sum"].transform(lambda s: s.rolling(7, min_periods=1).sum())
    if "temperature_2m_max" in df.columns:
        df["temp_max_mean_3d"] = grp["temperature_2m_max"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    if "relative_humidity_2m_mean" in df.columns:
        df["humidity_mean_3d"] = grp["relative_humidity_2m_mean"].transform(
            lambda s: s.rolling(3, min_periods=1).mean()
        )
    if "et0_fao_evapotranspiration" in df.columns:
        df["et0_sum_3d"] = grp["et0_fao_evapotranspiration"].transform(
            lambda s: s.rolling(3, min_periods=1).sum()
        )
    if {"temp_max_mean_3d", "humidity_mean_3d"}.issubset(df.columns):
        df["heat_spoilage_index"] = df["temp_max_mean_3d"] * (df["humidity_mean_3d"] / 100.0)

    for col in [
        "precip_sum_3d",
        "precip_sum_7d",
        "temp_max_mean_3d",
        "humidity_mean_3d",
        "et0_sum_3d",
        "heat_spoilage_index",
    ]:
        if col in df.columns:
            df[col] = df[col].astype("float32")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute Phase 2: Open-Meteo district weather fetcher")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument("--limit-districts", type=int, default=None)
    parser.add_argument("--max-budget", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    p2 = cfg["phase_2"]
    wcfg = p2["weather"]

    end_d = date.fromisoformat(args.end_date) if args.end_date else date(2025, 11, 19)
    start_d = (
        date.fromisoformat(args.start_date)
        if args.start_date
        else end_d - timedelta(days=int(wcfg["lookback_days"]) - 1)
    )
    start_str, end_str = start_d.isoformat(), end_d.isoformat()

    centroids = extract_verified_district_centroids(
        raw_csv_path=ROOT / cfg["paths"]["raw_apmc"],
        target_states=p2["states"],
        output_csv=ROOT / wcfg["centroids_csv"],
    )
    if args.limit_districts is not None:
        centroids = centroids.head(args.limit_districts).copy()

    n_days = (end_d - start_d).days + 1
    vars_list = list(wcfg["daily_variables"])
    est_calls = estimate_weighted_calls(len(centroids), n_days, len(vars_list))
    max_budget = float(args.max_budget if args.max_budget is not None else wcfg["safety_weighted_budget_per_run"])

    print(
        json.dumps(
            {
                "districts": len(centroids),
                "coord_sources": centroids["coord_source"].value_counts().to_dict(),
                "date_range": [start_str, end_str],
                "n_days": n_days,
                "n_variables": len(vars_list),
                "estimated_total_weighted_calls": round(est_calls, 2),
                "max_weighted_budget_per_run": max_budget,
                "estimated_batches_at_daily_quota": int(np.ceil(est_calls / max_budget)) if est_calls else 0,
            },
            indent=2,
        )
    )
    if args.dry_run:
        return

    weather_df, stats = fetch_open_meteo_weather(
        centroids_df=centroids,
        start_date=start_str,
        end_date=end_str,
        variables=vars_list,
        cache_dir=ROOT / wcfg["cache_dir"],
        endpoint=wcfg["endpoint"],
        batch_size=int(wcfg["batch_locations"]),
        max_weighted_budget=max_budget,
        output_csv=ROOT / wcfg["output_csv"],
    )
    enriched = engineer_weather_features(weather_df)
    if not enriched.empty:
        enriched.to_csv(ROOT / wcfg["output_csv"], index=False)
    print("Fetch stats:", json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
