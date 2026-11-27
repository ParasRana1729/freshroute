"""FreshRoute Phase 0: Deterministic Row Cleaning (Plan v3.1).

Raw: APMC arrivals + prices (Directorate of Marketing & Inspection feed,
     data.gov.in / CEDA Agmarknet mirror) — mandi-level, India-native.

Deterministic cleaning ONLY:
  1. Load raw CSV (394,258 rows) and drop exact duplicate rows.
  2. Parse dates and normalize text columns (strip + uppercase; fill missing
     variety/grade with "UNKNOWN").
  3. Filter to Quintal-priced rows and convert modal/min/max prices to Rs./kg.
  4. Replace negative prices/arrivals with NaN and drop rows missing required
     fields (date, modal_price, price_per_kg, arrival_tonnes, entity keys).
  5. Deduplicate same-day records on ENTITY_KEYS + ["date"]:
     sum arrival_tonnes and compute volume-weighted average prices
     (safely falling back to simple mean if group arrival sum is zero).
  6. Compute purely deterministic row-level columns (log_arrival, price_spread,
     month_num, day_num, is_weekend, geo_missing) with ZERO cross-split
     statistics (no global IQR winsorization, no rolling baselines, no
     price_z/arrival_z/surplus_S, and no global quantile priority labels).
  7. Downcast numerics to float32 and string identifiers to category for low RAM,
     and write cleaned CSV, encoded CSV, cleaning_report.json, and EDA figures.

Run: python scripts/clean_dataset.py
"""
from pathlib import Path
import json
import yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "configs" / "experiment_config.yaml"

with open(CFG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

ENTITY_KEYS = CONFIG["entity_keys"]
RAW_APMC = ROOT / CONFIG["paths"]["raw_apmc"]
PROC = ROOT / "data" / "processed"
FIG = ROOT / CONFIG["paths"]["figures_dir"]

PROC.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def normalize_text_series(series: pd.Series, default: str | None = None) -> pd.Series:
    """Strip and uppercase text values consistently; optionally fill missing."""
    s = series.copy()
    if default is not None:
        s = s.fillna(default)
    s = s.astype(str).str.strip().str.upper()
    if default is not None:
        s = s.replace({"": default, "NAN": default, "NONE": default})
    return s


def deduplicate_same_day(df: pd.DataFrame, entity_keys: list[str]) -> tuple[pd.DataFrame, int]:
    """Deduplicate records sharing entity_keys + ['date'].

    Sums arrival_tonnes and computes volume-weighted average for price_per_kg,
    modal_price, min_per_kg, and max_per_kg (falling back to simple mean when
    total group arrival_tonnes <= 0).
    """
    dedup_keys = entity_keys + ["date"]
    n_before = len(df)
    dup_mask = df.duplicated(subset=dedup_keys, keep=False)
    if not dup_mask.any():
        return df.sort_values(dedup_keys).reset_index(drop=True), 0

    unique_df = df.loc[~dup_mask].copy()
    dup_df = df.loc[dup_mask].copy()

    price_cols = ["modal_price", "price_per_kg", "min_per_kg", "max_per_kg"]
    rows = []
    for key_vals, grp in dup_df.groupby(dedup_keys, sort=False, observed=True):
        rec = dict(zip(dedup_keys, key_vals))
        w = grp["arrival_tonnes"].to_numpy(dtype=np.float64)
        total_arr = float(np.nansum(w))
        rec["arrival_tonnes"] = total_arr

        for pcol in price_cols:
            vals = grp[pcol].to_numpy(dtype=np.float64)
            valid = ~np.isnan(vals)
            if not valid.any():
                rec[pcol] = np.nan
            elif total_arr > 0.0:
                w_valid = w[valid]
                w_sum = float(np.sum(w_valid))
                if w_sum > 0.0:
                    rec[pcol] = float(np.sum(vals[valid] * w_valid) / w_sum)
                else:
                    rec[pcol] = float(np.mean(vals[valid]))
            else:
                rec[pcol] = float(np.mean(vals[valid]))

        rec["district_name"] = grp["district_name"].iloc[0]
        rec["geo_missing"] = int(grp["geo_missing"].min())
        rec["latitude"] = float(grp["latitude"].median())
        rec["longitude"] = float(grp["longitude"].median())
        rows.append(rec)

    agg_df = pd.DataFrame(rows, columns=unique_df.columns)
    combined = pd.concat([unique_df, agg_df], ignore_index=True)
    combined = combined.sort_values(dedup_keys).reset_index(drop=True)
    n_removed = n_before - len(combined)
    return combined, n_removed


def downcast_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast numeric columns to float32/int8 and identifier strings to category."""
    out = df.copy()
    cat_cols = ["state_name", "district_name", "market_center_name",
                "commodity_name", "variety", "grade"]
    for c in cat_cols:
        if c in out.columns:
            out[c] = out[c].astype("category")

    int_cols = ["geo_missing", "month_num", "day_num", "is_weekend"]
    for c in int_cols:
        if c in out.columns:
            out[c] = out[c].astype("int8")

    float_cols = [
        "latitude", "longitude", "arrival_tonnes", "modal_price",
        "price_per_kg", "min_per_kg", "max_per_kg", "log_arrival", "price_spread",
    ]
    for c in float_cols:
        if c in out.columns:
            out[c] = out[c].astype("float32")
    return out


def clean_dataset() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run deterministic Phase 0 cleaning and save outputs."""
    log: dict = {
        "fixes": [],
        "note": "Deterministic row cleaning only (Plan v3.1). Zero cross-split statistics.",
        "entity_keys": ENTITY_KEYS,
    }

    # ---------- 1. load ----------
    df = pd.read_csv(RAW_APMC, low_memory=False)
    log["raw_shape"] = list(df.shape)
    log["raw_missing"] = {k: int(v) for k, v in df.isna().sum().items() if v > 0}
    log["raw_dates"] = [str(df["date"].min()), str(df["date"].max())]

    # ---------- 2. exact dedupe ----------
    n0 = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    log["fixes"].append(f"dropped {n0 - len(df)} exact duplicate rows")

    # ---------- 3. parse date + drop missing required keys ----------
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "modal_price", "commodity_name",
                           "market_center_name", "state_name"]).copy()
    for c in ["state_name", "district_name", "market_center_name", "commodity_name"]:
        if c == "district_name":
            df[c] = normalize_text_series(df[c], default="UNKNOWN")
        else:
            df[c] = normalize_text_series(df[c])
    df["variety"] = normalize_text_series(df["variety"], default="UNKNOWN")
    df["grade"] = normalize_text_series(df["grade"], default="UNKNOWN")
    log["fixes"].append("parsed dates, dropped missing required keys, normalized text + variety/grade->UNKNOWN")

    # ---------- 4. unit standardization: Quintal -> Rs./kg ----------
    quintal = df["price_unit"].astype(str).str.contains("Quintal", na=False)
    log["non_quintal_dropped"] = int((~quintal).sum())
    df = df.loc[quintal].copy()
    log["fixes"].append(
        f"{log['non_quintal_dropped']} non-quintal rows dropped — kept Quintal unit-consistent"
    )

    # ---------- 5. negatives -> NaN, unit conversion ----------
    for c in ["arrival_quantity", "min_price", "max_price", "modal_price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        n_neg = int((df[c] < 0).sum())
        if n_neg:
            log["fixes"].append(f"{n_neg} negative values in '{c}' -> NaN")
            df.loc[df[c] < 0, c] = np.nan

    df["arrival_tonnes"] = pd.to_numeric(df["arrival_quantity"], errors="coerce")
    df = df.dropna(subset=["modal_price", "arrival_tonnes"]).copy()

    # Fill missing min/max with modal_price so row-level spreads and prices have zero NaNs
    df["min_price"] = df["min_price"].fillna(df["modal_price"])
    df["max_price"] = df["max_price"].fillna(df["modal_price"])
    df["price_per_kg"] = df["modal_price"] / 100.0
    df["min_per_kg"] = df["min_price"] / 100.0
    df["max_per_kg"] = df["max_price"] / 100.0

    # ---------- 6. static geo metadata imputation ----------
    cleaned_geo_missing = df[["latitude", "longitude"]].isna().any(axis=1)
    df["geo_missing"] = cleaned_geo_missing.astype("int8")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = df["latitude"].fillna(df.groupby("state_name")["latitude"].transform("median"))
    df["longitude"] = df["longitude"].fillna(df.groupby("state_name")["longitude"].transform("median"))
    df["latitude"] = df["latitude"].fillna(df["latitude"].median())
    df["longitude"] = df["longitude"].fillna(df["longitude"].median())
    log["fixes"].append(
        f"geo missing {int(cleaned_geo_missing.sum())} rows -> state median + geo_missing flag"
    )

    # ---------- 7. 5-key same-day deduplication ----------
    n_pre_dedup = len(df)
    log["dedup_before_rows"] = n_pre_dedup
    df, n_dups_removed = deduplicate_same_day(df, ENTITY_KEYS)
    log["dedup_duplicates_removed"] = int(n_dups_removed)
    log["fixes"].append(
        f"5-key same-day deduplication resolved {n_dups_removed} duplicates ({n_pre_dedup} -> {len(df)} rows)"
    )

    # ---------- 8. deterministic row-level columns ONLY ----------
    df["log_arrival"] = np.log1p(df["arrival_tonnes"].clip(lower=0))
    df["price_spread"] = (
        (df["max_per_kg"] - df["min_per_kg"]) / df["price_per_kg"].replace(0, np.nan)
    ).fillna(0.0).clip(0.0, 5.0).round(3)
    df["month_num"] = df["date"].dt.month
    df["day_num"] = df["date"].dt.day
    df["is_weekend"] = (df["date"].dt.weekday >= 5).astype(int)

    log["engineered"] = [
        "price_per_kg", "min_per_kg", "max_per_kg", "arrival_tonnes",
        "log_arrival", "price_spread", "month_num", "day_num", "is_weekend",
    ]

    keep = [
        "date", "state_name", "district_name", "market_center_name", "commodity_name",
        "variety", "grade", "latitude", "longitude", "geo_missing",
        "arrival_tonnes", "modal_price", "price_per_kg", "min_per_kg", "max_per_kg",
        "log_arrival", "price_spread", "month_num", "day_num", "is_weekend",
    ]
    cleaned = downcast_memory(df[keep])
    assert cleaned.isna().sum().sum() == 0, "missing values remain in cleaned dataframe!"

    log["cleaned_shape"] = list(cleaned.shape)
    log["entity_count"] = int(cleaned.drop_duplicates(subset=ENTITY_KEYS).shape[0])
    log["cleaned_columns"] = list(cleaned.columns)
    log["memory_mb"] = round(float(cleaned.memory_usage(deep=True).sum() / (1024 * 1024)), 2)

    cleaned_out = cleaned.copy()
    cleaned_out["date"] = cleaned_out["date"].dt.strftime("%Y-%m-%d")
    cleaned_out.to_csv(ROOT / CONFIG["paths"]["cleaned_csv"], index=False)

    # ---------- 9. deterministic encoded export (NO price_z / arrival_z / surplus_S) ----------
    enc = cleaned.copy()
    top_comms = enc["commodity_name"].astype(str).value_counts().nlargest(20).index
    enc["commodity_top"] = pd.Categorical(
        enc["commodity_name"].astype(str).where(enc["commodity_name"].astype(str).isin(top_comms), "OTHER")
    )
    enc = pd.get_dummies(enc, columns=["state_name", "commodity_top"], drop_first=True, dtype=int)
    enc = enc.drop(columns=["date", "district_name", "market_center_name",
                            "commodity_name", "variety", "grade"])
    X_cols = list(enc.columns)
    forbidden = {"price_z", "arrival_z", "surplus_S", "redistribution_priority"}
    assert not (forbidden & set(X_cols)), f"Forbidden columns found in X_columns: {forbidden & set(X_cols)}"

    log["X_columns"] = X_cols
    log["encoded_shape"] = list(enc.shape)
    enc.to_csv(ROOT / CONFIG["paths"]["encoded_csv"], index=False)
    (ROOT / CONFIG["paths"]["cleaning_report"]).write_text(json.dumps(log, indent=2), encoding="utf-8")

    # ---------- 10. non-leaking EDA figures ----------
    plt.rcParams.update({"figure.dpi": 120})

    # Daily record counts
    daily_counts = cleaned.groupby("date", observed=True).size()
    daily_counts.index = daily_counts.index.strftime("%m-%d")
    daily_counts.plot(kind="bar", color="#264653", figsize=(9, 4))
    plt.title("Daily cleaned APMC records (24-day window)")
    plt.ylabel("records")
    plt.tight_layout()
    plt.savefig(FIG / "01_priority_dist.png")
    plt.close()

    # Modal price per kg histogram (p99 clipped for readability only in plot)
    p99 = float(cleaned["price_per_kg"].quantile(0.99))
    plt.hist(cleaned["price_per_kg"].clip(upper=p99), bins=50, color="#264653")
    plt.title("Modal price per kg (p99 clipped for display)")
    plt.xlabel("Rs./kg")
    plt.ylabel("records")
    plt.tight_layout()
    plt.savefig(FIG / "02_pounds_hist.png")
    plt.close()

    # Daily total arrivals
    daily_arr = cleaned.groupby("date", observed=True)["arrival_tonnes"].sum()
    daily_arr.plot(marker="o", color="#b31b1b", figsize=(9, 4))
    plt.title("Total arrivals by day (24-day window)")
    plt.ylabel("tonnes")
    plt.tight_layout()
    plt.savefig(FIG / "03_monthly_trend.png")
    plt.close()

    # Top 12 commodities by total arrivals
    top_comm = cleaned.groupby("commodity_name", observed=True)["arrival_tonnes"].sum().nlargest(12)
    top_comm.plot(kind="barh", color="#2a9d8f")
    plt.title("Top 12 commodities by total arrivals")
    plt.xlabel("total tonnes")
    plt.tight_layout()
    plt.savefig(FIG / "04_top_localities.png")
    plt.close()

    # Log-arrival vs log-price scatter (deterministic sample for speed)
    sample = cleaned.sample(n=min(50000, len(cleaned)), random_state=CONFIG["models"]["random_seed"])
    plt.scatter(sample["log_arrival"], np.log1p(sample["price_per_kg"].clip(lower=0)),
                color="#264653", alpha=0.12, s=4)
    plt.title("Log arrival vs log price per kg (50k sample)")
    plt.xlabel("log(1 + arrival_tonnes)")
    plt.ylabel("log(1 + price_per_kg)")
    plt.tight_layout()
    plt.savefig(FIG / "05_need_vs_supply.png")
    plt.close()

    # Deterministic numeric correlation matrix
    num_cols = ["arrival_tonnes", "price_per_kg", "min_per_kg", "max_per_kg",
                "log_arrival", "price_spread"]
    corr = cleaned[num_cols].corr()
    plt.matshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
    plt.colorbar()
    plt.xticks(range(len(num_cols)), num_cols, rotation=45, ha="left")
    plt.yticks(range(len(num_cols)), num_cols)
    plt.title("Deterministic numeric correlation matrix", pad=28)
    plt.savefig(FIG / "06_corr_heatmap.png", bbox_inches="tight")
    plt.close()

    return cleaned, enc, log


if __name__ == "__main__":
    cleaned_df, enc_df, report = clean_dataset()
    print(json.dumps({k: v for k, v in report.items() if k != "X_columns"}, indent=2))
    print(
        f"X: {len(report['X_columns'])} cols | cleaned: {cleaned_df.shape} | "
        f"encoded: {enc_df.shape} | entities: {report['entity_count']} | RAM: {report['memory_mb']} MB"
    )
