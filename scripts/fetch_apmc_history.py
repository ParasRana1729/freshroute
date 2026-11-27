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
    backoff_seconds: float = 1.5,
) -> pd.DataFrame:
    """Pull scoped daily arrivals + prices from CEDA Ashoka Agri-Market Data API with caching."""
    validate_apmc_source_url(base_url)
    key = api_key or os.environ.get("CEDA_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing CEDA_API_KEY environment variable (or --api-key). "
            "Register at https://ceda.ashoka.edu.in/ to generate an API key, or pass "
            "--source agmarknet --import-dir <path> for local Agmarknet 2.0 exports."
        )

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    endpoint = f"{base_url.rstrip('/')}/v1/agmarknet/prices-arrivals"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}

    own_session = session is None
    client = requests.Session() if own_session else session
    records: list[pd.DataFrame] = []

    try:
        for state in target_states:
            for commodity in target_commodities:
                cfile = cache_path / f"ceda__{_slugify(state)}__{_slugify(commodity)}__{start_date}__{end_date}.json"
                if cfile.exists():
                    payload = json.loads(cfile.read_text(encoding="utf-8"))
                else:
                    params = {
                        "state": state,
                        "commodity": commodity,
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                    payload = None
                    last_err: Exception | None = None
                    for attempt in range(max_retries):
                        try:
                            resp = client.get(endpoint, headers=headers, params=params, timeout=30)
                            if resp.status_code in (429, 500, 502, 503, 504):
                                raise requests.HTTPError(
                                    f"CEDA transient HTTP {resp.status_code}", response=resp
                                )
                            resp.raise_for_status()
                            payload = resp.json()
                            break
                        except Exception as exc:
                            last_err = exc
                            if attempt < max_retries - 1:
                                time.sleep(backoff_seconds * (2**attempt))
                    if payload is None:
                        raise RuntimeError(
                            f"CEDA fetch failed for ({state}, {commodity}): {last_err}"
                        )
                    cfile.write_text(json.dumps(payload), encoding="utf-8")

                rows = payload.get("data", payload) if isinstance(payload, dict) else payload
                if rows:
                    records.append(pd.DataFrame(rows))
    finally:
        if own_session:
            client.close()

    if not records:
        return pd.DataFrame()
    return normalize_and_dedupe_apmc(
        pd.concat(records, ignore_index=True), target_states, target_commodities
    )


def build_seasonal_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Compute strictly <= t 30d/90d rolling baselines & prior-year same-month baselines."""
    if df.empty:
        return df.copy()

    out = df.copy()
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
    parser.add_argument("--start-date", type=str, default="2024-01-01")
    parser.add_argument("--end-date", type=str, default="2025-11-19")
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
        scoped = fetch_ceda_history(
            target_states=p2["states"],
            target_commodities=p2["commodities"],
            start_date=args.start_date,
            end_date=args.end_date,
            cache_dir=ROOT / acfg["cache_dir"],
            base_url=acfg["ceda_base_url"],
            api_key=args.api_key,
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
