"""FreshRoute Phase 2: Scoped Multi-Year APMC Arrivals + Prices Pipeline.

Plan v3.1 requirements:
  - Scope strictly to top 5-10 perishables and top 5-6 agricultural states.
  - Pull 12-24 months of daily modal_price + arrival_quantity via CEDA Ashoka
    Agri-Market Data Portal API or Agmarknet 2.0 daily price-and-arrival exports.
  - Explicitly reject data.gov.in resource 9ef84268-d588-465a-a308-a864a43d0070
    (daily price snapshot only, no arrivals).
  - Apply deterministic Quintal -> Rs./kg conversion and 5-key same-day
    deduplication (zero global winsorization), then provide causal 30/90-day and
    prior-year same-month baselines, festival/crop-season flags, and expanding
    3-to-5 fold walk-forward CV splits.

Run:
  python scripts/fetch_apmc_history.py --source local-raw --dry-run
  python scripts/fetch_apmc_history.py --source agmarknet --import-dir data/external/agmarknet_exports
  python scripts/fetch_apmc_history.py --source ceda --start-date 2024-01-01 --end-date 2025-11-19
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "experiment_config.yaml"
FORBIDDEN_DATAGOV_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"

ENTITY_KEYS = [
    "state_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
]

# Approximate major Indian festival dates (Diwali, Holi, Navratri start, Eid al-Fitr)
# covering multi-year 2023-2027 windows for causal calendar proximity features.
MAJOR_FESTIVAL_DATES: list[str] = [
    # 2023
    "2023-03-08", "2023-04-22", "2023-10-15", "2023-11-12",
    # 2024
    "2024-03-25", "2024-04-11", "2024-10-03", "2024-11-01",
    # 2025
    "2025-03-14", "2025-03-31", "2025-09-22", "2025-10-20",
    # 2026
    "2026-03-04", "2026-03-20", "2026-10-11", "2026-11-08",
    # 2027
    "2027-03-22", "2027-03-10", "2027-09-30", "2027-10-29",
]

COLUMN_ALIASES: dict[str, list[str]] = {
    "date": ["date", "price_date", "arrival_date", "reported_date", "Price Date", "Arrival Date"],
    "state_name": ["state_name", "state", "State", "State Name"],
    "district_name": ["district_name", "district", "District", "District Name"],
    "market_center_name": ["market_center_name", "market", "mandi", "Market", "Market Name"],
    "commodity_name": ["commodity_name", "commodity", "Commodity", "Commodity Name"],
    "variety": ["variety", "Variety"],
    "grade": ["grade", "Grade"],
    "arrival_quantity": [
        "arrival_quantity",
        "arrival_tonnes",
        "arrivals",
        "Arrivals (Tonnes)",
        "Arrival Quantity",
    ],
    "modal_price": ["modal_price", "Modal Price", "Modal Price (Rs./Quintal)", "modal_price_rs_qtl"],
    "min_price": ["min_price", "Min Price", "Min Price (Rs./Quintal)"],
    "max_price": ["max_price", "Max Price", "Max Price (Rs./Quintal)"],
    "price_unit": ["price_unit", "Price Unit", "unit"],
}


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_apmc_source_url(url_or_id: str) -> None:
    if FORBIDDEN_DATAGOV_RESOURCE in str(url_or_id):
        raise ValueError(
            f"data.gov.in resource {FORBIDDEN_DATAGOV_RESOURCE} is forbidden for Phase 2 "
            "(daily price snapshot only, no arrivals). Use CEDA Ashoka or Agmarknet 2.0."
        )


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).strip().upper()).strip("_")


def _rename_aliases(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    lower_lookup = {c.strip().lower(): c for c in df.columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            match = lower_lookup.get(alias.strip().lower())
            if match is not None:
                rename_map[match] = canonical
                break
    return df.rename(columns=rename_map)


def normalize_and_dedupe_apmc(
    raw_df: pd.DataFrame,
    target_states: list[str],
    target_commodities: list[str],
) -> pd.DataFrame:
    """Scope to target states/commodities and apply 5-key same-day deduplication."""
    if raw_df.empty:
        return pd.DataFrame()

    df = _rename_aliases(raw_df.copy())
    required = {"date", "state_name", "market_center_name", "commodity_name", "modal_price", "arrival_quantity"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(f"APMC input missing required columns: {sorted(missing_cols)}")

    states_up = {s.strip().upper() for s in target_states}
    comms_up = {c.strip().upper() for c in target_commodities}

    for col in ["state_name", "district_name", "market_center_name", "commodity_name", "variety", "grade"]:
        if col not in df.columns:
            df[col] = "UNKNOWN"
        df[col] = df[col].fillna("UNKNOWN").astype(str).str.strip().str.upper()
        df.loc[df[col].isin(["", "NAN", "NONE"]), col] = "UNKNOWN"

    df = df[df["state_name"].isin(states_up) & df["commodity_name"].isin(comms_up)].copy()
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    if "price_unit" in df.columns:
        quintal_mask = df["price_unit"].fillna("Rs./Quintal").astype(str).str.contains("Quintal", case=False, na=False)
        df = df[quintal_mask].copy()

    for col in ["arrival_quantity", "modal_price", "min_price", "max_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = np.nan

    if "min_price" not in df.columns:
        df["min_price"] = df["modal_price"]
    if "max_price" not in df.columns:
        df["max_price"] = df["modal_price"]
    df["min_price"] = df["min_price"].fillna(df["modal_price"])
    df["max_price"] = df["max_price"].fillna(df["modal_price"])

    df = df.dropna(subset=["arrival_quantity", "modal_price"]).copy()
    df["arrival_tonnes"] = df["arrival_quantity"].astype("float64")
    df["price_per_kg"] = (df["modal_price"] / 100.0).astype("float64")
    df["min_per_kg"] = (df["min_price"] / 100.0).astype("float64")
    df["max_per_kg"] = (df["max_price"] / 100.0).astype("float64")

    # 5-key same-day deduplication (sum arrivals, volume-weighted prices)
    dedup_keys = [*ENTITY_KEYS, "date"]
    df["_w_modal"] = df["modal_price"] * df["arrival_tonnes"]
    df["_w_pkg"] = df["price_per_kg"] * df["arrival_tonnes"]
    df["_w_min"] = df["min_per_kg"] * df["arrival_tonnes"]
    df["_w_max"] = df["max_per_kg"] * df["arrival_tonnes"]

    grouped = df.groupby(dedup_keys, as_index=False, observed=True).agg(
        district_name=("district_name", "first"),
        arrival_tonnes=("arrival_tonnes", "sum"),
        _w_modal=("_w_modal", "sum"),
        _w_pkg=("_w_pkg", "sum"),
        _w_min=("_w_min", "sum"),
        _w_max=("_w_max", "sum"),
        _mean_modal=("modal_price", "mean"),
        _mean_pkg=("price_per_kg", "mean"),
        _mean_min=("min_per_kg", "mean"),
        _mean_max=("max_per_kg", "mean"),
    )

    pos_arr = grouped["arrival_tonnes"] > 0
    grouped["modal_price"] = np.where(pos_arr, grouped["_w_modal"] / grouped["arrival_tonnes"], grouped["_mean_modal"])
    grouped["price_per_kg"] = np.where(pos_arr, grouped["_w_pkg"] / grouped["arrival_tonnes"], grouped["_mean_pkg"])
    grouped["min_per_kg"] = np.where(pos_arr, grouped["_w_min"] / grouped["arrival_tonnes"], grouped["_mean_min"])
    grouped["max_per_kg"] = np.where(pos_arr, grouped["_w_max"] / grouped["arrival_tonnes"], grouped["_mean_max"])
    grouped = grouped.drop(
        columns=["_w_modal", "_w_pkg", "_w_min", "_w_max", "_mean_modal", "_mean_pkg", "_mean_min", "_mean_max"]
    )
    grouped["log_arrival"] = np.log1p(grouped["arrival_tonnes"].clip(lower=0.0))
    grouped["log_price"] = np.log1p(grouped["price_per_kg"].clip(lower=0.0))

    for col in ["arrival_tonnes", "modal_price", "price_per_kg", "min_per_kg", "max_per_kg", "log_arrival", "log_price"]:
        grouped[col] = grouped[col].astype("float32")

    return grouped.sort_values([*ENTITY_KEYS, "date"]).reset_index(drop=True)


def ingest_agmarknet_exports(
    export_dir: Path | str,
    target_states: list[str],
    target_commodities: list[str],
) -> pd.DataFrame:
    """Load and normalize Agmarknet 2.0 daily price + arrival CSV/JSON exports."""
    exp_path = Path(export_dir)
    if not exp_path.exists():
        raise FileNotFoundError(f"Agmarknet export directory not found: {exp_path}")
    files = sorted([*exp_path.glob("*.csv"), *exp_path.glob("*.json")])
    if not files:
        raise FileNotFoundError(f"No CSV or JSON exports found in {exp_path}")

    frames: list[pd.DataFrame] = []
    for f in files:
        if f.suffix.lower() == ".csv":
            frames.append(pd.read_csv(f, low_memory=False))
        else:
            frames.append(pd.read_json(f))
    combined = pd.concat(frames, ignore_index=True)
    return normalize_and_dedupe_apmc(combined, target_states, target_commodities)


def _ceda_get_json_cached(
    client: requests.Session,
    url: str,
    headers: dict[str, str],
    cache_file: Path,
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
    wait_on_hourly_limit: bool = False,
) -> dict[str, Any]:
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.get(url, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait_s = float(resp.headers.get("Retry-After") or resp.headers.get("RateLimit-Reset") or 62.0)
                if wait_s > 120 and not wait_on_hourly_limit:
                    raise RuntimeError(
                        f"CEDA hourly rate limit reached (policy={resp.headers.get('RateLimit-Policy', '40;w=3600')}, "
                        f"reset_in={int(wait_s)}s). Re-run after reset or pass --wait-on-rate-limit."
                    )
                last_err = requests.HTTPError("CEDA rate limit 429", response=resp)
                if attempt < max_retries - 1 and backoff_seconds > 0:
                    time.sleep(wait_s)
                    continue
                raise last_err
            if resp.status_code in (500, 502, 503, 504):
                raise requests.HTTPError(f"CEDA HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            payload = resp.json()
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
            return payload
        except RuntimeError:
            raise
        except Exception as exc:
            last_err = exc
            if attempt < max_retries - 1 and backoff_seconds > 0:
                time.sleep(backoff_seconds * (2**attempt))
    raise RuntimeError(f"CEDA GET failed for {url}: {last_err}")


def _ceda_post_chunk(
    client: requests.Session,
    url: str,
    headers: dict[str, str],
    commodity_id: int,
    state_id: int,
    district_ids: list[int],
    from_date: str,
    to_date: str,
    cache_file: Path,
    request_budget: list[int],
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
    timeout_seconds: int = 45,
    wait_on_hourly_limit: bool = False,
) -> tuple[list[dict[str, Any]], bool]:
    """Return (rows, hit_budget_or_rate_limit)."""
    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        return payload.get("output", {}).get("data", payload.get("data", [])), False

    if request_budget[0] <= 0:
        return [], True

    body = {
        "commodity_id": int(commodity_id),
        "state_id": int(state_id),
        "district_id": [int(d) for d in district_ids],
        "from_date": from_date,
        "to_date": to_date,
    }
    last_err: Exception | None = None
    for attempt in range(max_retries):
        if request_budget[0] <= 0:
            return [], True
        try:
            request_budget[0] -= 1
            resp = client.post(url, headers=headers, json=body, timeout=timeout_seconds)
            if resp.status_code == 429:
                wait_s = float(resp.headers.get("Retry-After") or resp.headers.get("RateLimit-Reset") or 62.0)
                if wait_s > 120 and not wait_on_hourly_limit:
                    return [], True
                last_err = requests.HTTPError("CEDA rate limit 429", response=resp)
                if attempt < max_retries - 1 and backoff_seconds > 0:
                    time.sleep(wait_s)
                    continue
                return [], True
            if resp.status_code in (500, 502, 503, 504):
                raise requests.HTTPError(f"CEDA HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            payload = resp.json()
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
            rem = resp.headers.get("RateLimit-Remaining")
            if rem is not None and str(rem).isdigit() and int(rem) == 0:
                request_budget[0] = 0
            return payload.get("output", {}).get("data", payload.get("data", [])), False
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_err = exc
            if len(district_ids) > 1:
                mid = len(district_ids) // 2
                left, stop_l = _ceda_post_chunk(
                    client, url, headers, commodity_id, state_id, district_ids[:mid],
                    from_date, to_date,
                    cache_file.with_name(cache_file.stem + "_L.json"),
                    request_budget,
                    max_retries=max_retries, backoff_seconds=backoff_seconds,
                    timeout_seconds=timeout_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                )
                if stop_l:
                    return left, True
                right, stop_r = _ceda_post_chunk(
                    client, url, headers, commodity_id, state_id, district_ids[mid:],
                    from_date, to_date,
                    cache_file.with_name(cache_file.stem + "_R.json"),
                    request_budget,
                    max_retries=max_retries, backoff_seconds=backoff_seconds,
                    timeout_seconds=timeout_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                )
                combined = left + right
                if not stop_r:
                    cache_file.write_text(json.dumps({"output": {"data": combined}}), encoding="utf-8")
                return combined, stop_r
            d0, d1 = pd.Timestamp(from_date), pd.Timestamp(to_date)
            if (d1 - d0).days > 7:
                d_mid = d0 + (d1 - d0) // 2
                left, stop_l = _ceda_post_chunk(
                    client, url, headers, commodity_id, state_id, district_ids,
                    from_date, d_mid.strftime("%Y-%m-%d"),
                    cache_file.with_name(cache_file.stem + "_T1.json"),
                    request_budget,
                    max_retries=max_retries, backoff_seconds=backoff_seconds,
                    timeout_seconds=timeout_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                )
                if stop_l:
                    return left, True
                right, stop_r = _ceda_post_chunk(
                    client, url, headers, commodity_id, state_id, district_ids,
                    (d_mid + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), to_date,
                    cache_file.with_name(cache_file.stem + "_T2.json"),
                    request_budget,
                    max_retries=max_retries, backoff_seconds=backoff_seconds,
                    timeout_seconds=timeout_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                )
                combined = left + right
                if not stop_r:
                    cache_file.write_text(json.dumps({"output": {"data": combined}}), encoding="utf-8")
                return combined, stop_r
            if attempt < max_retries - 1 and backoff_seconds > 0:
                time.sleep(backoff_seconds * (2**attempt))
        except Exception as exc:
            last_err = exc
            if attempt < max_retries - 1 and backoff_seconds > 0:
                time.sleep(backoff_seconds * (2**attempt))
    raise RuntimeError(
        f"CEDA POST failed for {url} (state={state_id}, comm={commodity_id}, {from_date}..{to_date}): {last_err}"
    )


def fetch_ceda_history(
    target_states: list[str],
    target_commodities: list[str],
    start_date: str,
    end_date: str,
    cache_dir: Path | str,
    base_url: str = "https://api.ceda.ashoka.edu.in",
    api_key: str | None = None,
    session: requests.Session | None = None,
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
    district_chunk_size: int = 12,
    date_chunk_days: int = 90,
    max_requests: int = 35,
    wait_on_hourly_limit: bool = False,
) -> pd.DataFrame:
    """Pull scoped daily market-level arrivals + prices from CEDA Agmarknet v1 API."""
    validate_apmc_source_url(base_url)
    key = api_key or os.environ.get("CEDA_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing CEDA_API_KEY environment variable (or --api-key / --api-key-file). "
            "Register at https://ceda.ashoka.edu.in/ to generate an API key, or pass "
            "--source agmarknet --import-dir <path> for local Agmarknet 2.0 exports."
        )

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    api_root = f"{base_url.rstrip('/')}/v1/agmarknet"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"}

    own_session = session is None
    client = requests.Session() if own_session else session

    try:
        comm_payload = _ceda_get_json_cached(
            client, f"{api_root}/commodities", headers, cache_path / "ceda_commodities.json",
            max_retries=max_retries, backoff_seconds=backoff_seconds,
            wait_on_hourly_limit=wait_on_hourly_limit,
        )
        geo_payload = _ceda_get_json_cached(
            client, f"{api_root}/geographies", headers, cache_path / "ceda_geographies.json",
            max_retries=max_retries, backoff_seconds=backoff_seconds,
            wait_on_hourly_limit=wait_on_hourly_limit,
        )

        comm_rows = comm_payload.get("output", {}).get("data", comm_payload.get("commodities", []))
        geo_rows = geo_payload.get("output", {}).get("data", geo_payload.get("geographies", []))

        comm_by_name = {
            str(r.get("commodity_name") or r.get("name")).strip().upper(): int(r.get("commodity_id") or r.get("id"))
            for r in comm_rows
        }
        state_districts: dict[str, tuple[int, list[int]]] = {}
        district_names: dict[int, str] = {}
        state_names: dict[int, str] = {}
        for g in geo_rows:
            sid = int(g["census_state_id"])
            sname = str(g["census_state_name"]).strip().upper()
            did = int(g["census_district_id"])
            dname = str(g["census_district_name"]).strip().upper()
            state_names[sid] = sname
            district_names[did] = dname
            if sname not in state_districts:
                state_districts[sname] = (sid, [])
            state_districts[sname][1].append(did)

        date_windows: list[tuple[str, str]] = []
        cur = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        while cur <= end_ts:
            win_end = min(cur + pd.Timedelta(days=date_chunk_days - 1), end_ts)
            date_windows.append((cur.strftime("%Y-%m-%d"), win_end.strftime("%Y-%m-%d")))
            cur = win_end + pd.Timedelta(days=1)

        all_price_rows: list[dict[str, Any]] = []
        all_qty_rows: list[dict[str, Any]] = []
        comm_id_to_name: dict[int, str] = {}
        budget = [int(max_requests)]
        stopped_early = False

        for state in target_states:
            if stopped_early:
                break
            st_up = state.strip().upper()
            if st_up not in state_districts:
                continue
            sid, dist_ids = state_districts[st_up]
            dist_ids = sorted(set(dist_ids))
            dist_batches = [dist_ids[i : i + district_chunk_size] for i in range(0, len(dist_ids), district_chunk_size)]

            for commodity in target_commodities:
                if stopped_early:
                    break
                cm_up = commodity.strip().upper()
                if cm_up not in comm_by_name:
                    continue
                cid = comm_by_name[cm_up]
                comm_id_to_name[cid] = cm_up

                for b_idx, d_batch in enumerate(dist_batches):
                    if stopped_early:
                        break
                    for fdate, tdate in date_windows:
                        p_cache = cache_path / f"ceda_px_s{sid}_c{cid}_b{b_idx}_{fdate}_{tdate}.json"
                        q_cache = cache_path / f"ceda_qty_s{sid}_c{cid}_b{b_idx}_{fdate}_{tdate}.json"
                        p_rows, p_stop = _ceda_post_chunk(
                            client, f"{api_root}/prices", headers, cid, sid, d_batch,
                            fdate, tdate, p_cache, budget, max_retries=max_retries,
                            backoff_seconds=backoff_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                        )
                        all_price_rows.extend(p_rows)
                        if p_stop:
                            stopped_early = True
                            break
                        q_rows, q_stop = _ceda_post_chunk(
                            client, f"{api_root}/quantities", headers, cid, sid, d_batch,
                            fdate, tdate, q_cache, budget, max_retries=max_retries,
                            backoff_seconds=backoff_seconds, wait_on_hourly_limit=wait_on_hourly_limit,
                        )
                        all_qty_rows.extend(q_rows)
                        if q_stop:
                            stopped_early = True
                            break
        if stopped_early:
            print(
                f"[CEDA] Stopped gracefully at hourly budget/rate limit "
                f"(cached {len(all_price_rows)} price & {len(all_qty_rows)} qty rows so far; "
                f"re-run after hourly reset to resume)."
            )
    finally:
        if own_session:
            client.close()

    if not all_price_rows or not all_qty_rows:
        return pd.DataFrame()

    px_df = pd.DataFrame(all_price_rows)
    qty_df = pd.DataFrame(all_qty_rows)
    join_keys = ["date", "commodity_id", "census_state_id", "census_district_id", "market_id"]
    for frame in (px_df, qty_df):
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")

    merged = px_df.merge(qty_df[[*join_keys, "quantity"]], on=join_keys, how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["state_name"] = merged["census_state_id"].map(state_names)
    merged["district_name"] = merged["census_district_id"].map(district_names).fillna("UNKNOWN")
    merged["commodity_name"] = merged["commodity_id"].map(comm_id_to_name)
    merged["market_center_name"] = "CEDA_MKT_" + merged["market_id"].astype(str)
    merged["variety"] = "CEDA_ALL"
    merged["grade"] = "CEDA_ALL"
    merged["arrival_quantity"] = merged["quantity"]
    merged["price_unit"] = "Rs./Quintal"

    return normalize_and_dedupe_apmc(merged, target_states, target_commodities)


def build_seasonal_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Compute strictly <= t 30d/90d rolling baselines & prior-year same-month baselines."""
    if df.empty:
        return df.copy()

    out = df.copy()
    existing_seasonal = [
        c
        for c in (
            "arr_mean_30d",
            "arr_mean_90d",
            "price_mean_30d",
            "price_mean_90d",
            "prior_year_month_log_arr",
            "prior_year_month_log_price",
        )
        if c in out.columns
    ]
    if existing_seasonal:
        out = out.drop(columns=existing_seasonal)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values([*ENTITY_KEYS, "date"]).reset_index(drop=True)

    # Causal 30-day and 90-day time-window rolling averages per entity (strictly <= t)
    def _time_rolling(sub: pd.DataFrame) -> pd.DataFrame:
        indexed = sub.set_index("date")
        r30_arr = indexed["log_arrival"].rolling("30D", min_periods=2).mean().to_numpy()
        r90_arr = indexed["log_arrival"].rolling("90D", min_periods=2).mean().to_numpy()
        r30_px = indexed["log_price"].rolling("30D", min_periods=2).mean().to_numpy()
        r90_px = indexed["log_price"].rolling("90D", min_periods=2).mean().to_numpy()
        return pd.DataFrame(
            {
                "arr_mean_30d": r30_arr,
                "arr_mean_90d": r90_arr,
                "price_mean_30d": r30_px,
                "price_mean_90d": r90_px,
            },
            index=sub.index,
        )

    rolled = pd.concat([_time_rolling(grp) for _, grp in out.groupby(ENTITY_KEYS, sort=False)])
    for col in ["arr_mean_30d", "arr_mean_90d", "price_mean_30d", "price_mean_90d"]:
        out[col] = rolled.loc[out.index, col].astype("float32")

    # Strictly causal prior-year same-month seasonal baseline (year - 1, same calendar month)
    out["_year"] = out["date"].dt.year
    out["_month"] = out["date"].dt.month
    monthly_ref = (
        out.groupby(["state_name", "market_center_name", "commodity_name", "_year", "_month"], as_index=False)
        .agg(
            prior_year_month_log_arr=("log_arrival", "mean"),
            prior_year_month_log_price=("log_price", "mean"),
        )
    )
    monthly_ref["_year"] = monthly_ref["_year"] + 1  # Shift forward 1 year so year Y only sees Y-1
    out = out.merge(
        monthly_ref,
        on=["state_name", "market_center_name", "commodity_name", "_year", "_month"],
        how="left",
    )
    out = out.drop(columns=["_year", "_month"])
    for col in ["prior_year_month_log_arr", "prior_year_month_log_price"]:
        out[col] = out[col].astype("float32")
    return out


def add_calendar_season_features(
    df: pd.DataFrame, festival_dates: list[str] | None = None
) -> pd.DataFrame:
    """Add days_to_major_festival and Indian Kharif/Rabi/Zaid harvest peak flags."""
    if df.empty:
        return df.copy()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    fests = np.array(
        sorted(pd.to_datetime(festival_dates or MAJOR_FESTIVAL_DATES).to_numpy()),
        dtype="datetime64[D]",
    )
    dates_d = out["date"].to_numpy(dtype="datetime64[D]")

    # Minimum absolute days to nearest major festival (calendar-known a priori)
    diffs = np.abs((dates_d[:, None] - fests[None, :]).astype("timedelta64[D]").astype(np.int32))
    out["days_to_major_festival"] = diffs.min(axis=1).astype("int16")

    months = out["date"].dt.month
    out["is_kharif_harvest_peak"] = months.isin([9, 10, 11]).astype("int8")
    out["is_rabi_harvest_peak"] = months.isin([3, 4, 5]).astype("int8")
    out["is_zaid_harvest_peak"] = months.isin([5, 6]).astype("int8")
    return out


def generate_walk_forward_folds(
    df: pd.DataFrame,
    min_train_months: int = 6,
    test_window_months: int = 1,
    n_folds: int = 5,
) -> list[dict[str, Any]]:
    """Build expanding monthly walk-forward CV folds with zero target-date overlap."""
    if df.empty:
        return []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["target_date"] = work["date"] + pd.Timedelta(days=1)

    next_keys = work[[*ENTITY_KEYS, "date", "log_arrival"]].rename(
        columns={"date": "target_date", "log_arrival": "log_arrival_next"}
    )
    pairs = work.merge(next_keys, on=[*ENTITY_KEYS, "target_date"], how="inner")
    if pairs.empty:
        return []

    pairs["delta_log_arr"] = (pairs["log_arrival_next"] - pairs["log_arrival"]).astype("float32")
    pairs["ym"] = pairs["date"].dt.to_period("M")
    all_months = sorted(pairs["ym"].unique())

    folds: list[dict[str, Any]] = []
    for idx in range(min_train_months, len(all_months) - test_window_months + 1):
        if len(folds) >= n_folds:
            break
        train_months = set(all_months[:idx])
        test_months = set(all_months[idx : idx + test_window_months])

        test_df = pairs[pairs["ym"].isin(test_months)].copy()
        test_min_date = test_df["date"].min()
        # Purge boundary pairs whose target_date touches or enters the test window
        train_df = pairs[pairs["ym"].isin(train_months) & (pairs["target_date"] < test_min_date)].copy()
        if train_df.empty or test_df.empty:
            continue
        assert train_df["target_date"].max() < test_df["date"].min()
        folds.append(
            {
                "fold": len(folds) + 1,
                "train_months": [str(m) for m in sorted(train_months)],
                "test_months": [str(m) for m in sorted(test_months)],
                "train": train_df.drop(columns=["ym"]),
                "test": test_df.drop(columns=["ym"]),
            }
        )
    return folds


def main() -> None:
    parser = argparse.ArgumentParser(description="FreshRoute Phase 2: Scoped multi-year APMC history pipeline")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--source", choices=["ceda", "agmarknet", "local-raw"], default="local-raw")
    parser.add_argument("--import-dir", type=Path, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--api-key-file", type=Path, default=None)
    parser.add_argument("--start-date", type=str, default="2024-01-01")
    parser.add_argument("--end-date", type=str, default="2025-11-19")
    parser.add_argument("--max-requests", type=int, default=35)
    parser.add_argument("--wait-on-rate-limit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    p2 = cfg["phase_2"]
    acfg = p2["apmc_history"]
    validate_apmc_source_url(acfg["ceda_base_url"])

    if args.dry_run:
        print(
            json.dumps(
                {
                    "source": args.source,
                    "scoped_commodities": p2["commodities"],
                    "scoped_states": p2["states"],
                    "date_range": [args.start_date, args.end_date],
                    "ceda_base_url": acfg["ceda_base_url"],
                    "output_csv": acfg["output_csv"],
                },
                indent=2,
            )
        )
        return

    if args.source == "local-raw":
        raw = pd.read_csv(ROOT / cfg["paths"]["raw_apmc"], low_memory=False)
        scoped = normalize_and_dedupe_apmc(raw, p2["states"], p2["commodities"])
    elif args.source == "agmarknet":
        if args.import_dir is None:
            raise ValueError("--import-dir is required when --source agmarknet")
        scoped = ingest_agmarknet_exports(args.import_dir, p2["states"], p2["commodities"])
    else:
        api_key = args.api_key
        if not api_key and args.api_key_file is not None:
            api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
        scoped = fetch_ceda_history(
            target_states=p2["states"],
            target_commodities=p2["commodities"],
            start_date=args.start_date,
            end_date=args.end_date,
            cache_dir=ROOT / acfg["cache_dir"],
            base_url=acfg["ceda_base_url"],
            api_key=api_key,
            max_requests=args.max_requests,
            wait_on_hourly_limit=args.wait_on_rate_limit,
        )

    scoped = build_seasonal_baselines(scoped)
    scoped = add_calendar_season_features(scoped)

    out_path = ROOT / acfg["output_csv"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scoped.to_csv(out_path, index=False)
    print(
        json.dumps(
            {
                "rows": len(scoped),
                "unique_entities": int(scoped[ENTITY_KEYS].drop_duplicates().shape[0]) if not scoped.empty else 0,
                "states": sorted(scoped["state_name"].unique().tolist()) if not scoped.empty else [],
                "commodities": sorted(scoped["commodity_name"].unique().tolist()) if not scoped.empty else [],
                "output_csv": str(out_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
