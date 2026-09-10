"""FreshRoute CE-1 pipeline on REAL India data.
Raw: APMC arrivals + prices (Directorate of Marketing & Inspection feed,
     data.gov.in / CEDA Agmarknet mirror) — mandi-level, India-native.
Steps: load -> dedupe -> unit standardization (Rs./Quintal -> Rs./kg) ->
       missing-value treatment -> rolling baselines -> Surplus Intensity
       S = arrival_z * (-price_z) -> derived priority label ->
       encode -> save cleaned/encoded/report/figures.
Run: python scripts/clean_dataset.py
Target is DERIVED by published rule (supply glut proxy), not observed.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW_APMC = ROOT / "data" / "raw" / "apmc_arrivals_prices.csv"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"

log = {"fixes": [], "note": "DERIVED priority = surplus-glut proxy, not observed waste"}
PROC.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ---------- load ----------
df = pd.read_csv(RAW_APMC, low_memory=False)
log["raw_shape"] = list(df.shape)
log["raw_missing"] = {k: int(v) for k, v in df.isna().sum().items() if v > 0}
log["raw_dates"] = [str(df["date"].min()), str(df["date"].max())]

# ---------- dedupe ----------
n0 = len(df)
df = df.drop_duplicates().reset_index(drop=True)
log["fixes"].append(f"dropped {n0 - len(df)} exact duplicate rows")

# ---------- normalize text + dates ----------
df["date"] = pd.to_datetime(df["date"], errors="coerce")
for c in ["state_name", "district_name", "market_center_name", "commodity_name"]:
    df[c] = df[c].astype(str).str.strip().str.upper()
df = df.dropna(subset=["date", "modal_price", "commodity_name",
                        "market_center_name", "state_name"]).copy()
log["fixes"].append("dropped rows missing date/modal_price/market/commodity/state")

# ---------- unit standardization: only Quintal -> kg is convertible ----------
# Rs./Bundle and Rs./Unit (flowers etc.) + Bundle/Nos arrivals cannot convert to kg.
quintal = df["price_unit"].astype(str).str.contains("Quintal", na=False)
log["non_quintal_dropped"] = int((~quintal).sum())
df = df[quintal].copy()
log["fixes"].append(
    f"{log['non_quintal_dropped']} non-quintal rows (Bundle/Unit) dropped "
    "— not convertible to Rs./kg, kept pipeline unit-consistent")

# ---------- negatives -> NaN (physically impossible) ----------
for c in ["arrival_quantity", "min_price", "max_price", "modal_price"]:
    n_neg = int((df[c] < 0).sum())
    if n_neg:
        log["fixes"].append(f"{n_neg} negative values in '{c}' -> NaN -> median/market fill")
        df.loc[df[c] < 0, c] = np.nan

df["price_per_kg"] = df["modal_price"] / 100.0
df["min_per_kg"] = df["min_price"] / 100.0
df["max_per_kg"] = df["max_price"] / 100.0
df["arrival_tonnes"] = pd.to_numeric(df["arrival_quantity"], errors="coerce")
df = df.dropna(subset=["price_per_kg", "arrival_tonnes"]).copy()

# ---------- per-commodity IQR winsorize (transcription errors vs real shocks) ----------
def winsorize(s, k=3.0):
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return s
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return s.clip(lo, hi)

n_before = len(df)
df["price_per_kg"] = df.groupby("commodity_name")["price_per_kg"].transform(winsorize)
df["arrival_tonnes"] = df.groupby("commodity_name")["arrival_tonnes"].transform(
    lambda s: winsorize(s, k=5.0))
log["fixes"].append("per-commodity IQR winsorized price (k=3) and arrivals (k=5)")

# ---------- sort for temporal calcs ----------
df = df.sort_values(["market_center_name", "commodity_name", "date"]).reset_index(drop=True)

# ---------- rolling baselines (6-period, min 2) per market-commodity ----------
g_price = df.groupby(["market_center_name", "commodity_name"])["price_per_kg"]
df["baseline_mean"] = g_price.transform(lambda s: s.rolling(6, min_periods=2).mean())
df["baseline_std"] = g_price.transform(lambda s: s.rolling(6, min_periods=2).std())
g_arr = df.groupby(["market_center_name", "commodity_name"])["arrival_tonnes"]
df["arr_mean"] = g_arr.transform(lambda s: s.rolling(6, min_periods=2).mean())
df["arr_std"] = g_arr.transform(lambda s: s.rolling(6, min_periods=2).std())

# fallback to commodity medians when rolling undefined (sparse groups)
df["baseline_mean"] = df["baseline_mean"].fillna(
    df.groupby("commodity_name")["price_per_kg"].transform("median"))
df["baseline_std"] = df["baseline_std"].fillna(
    df.groupby("commodity_name")["price_per_kg"].transform("std").replace(0, 1.0))
df["arr_mean"] = df["arr_mean"].fillna(
    df.groupby("commodity_name")["arrival_tonnes"].transform("median"))
df["arr_std"] = df["arr_std"].fillna(
    df.groupby("commodity_name")["arrival_tonnes"].transform("std").replace(0, 1.0))
for c in ["baseline_std", "arr_std"]:
    df[c] = df[c].replace(0, 1.0).fillna(1.0)

# ---------- Surplus Intensity Index (Report 1, Eq. S) ----------
# S = ((Q - muQ)/sigmaQ) * ((muP - P)/sigmaP) = arrival_z * (-price_z)
df["price_z"] = (df["price_per_kg"] - df["baseline_mean"]) / (df["baseline_std"] + 1e-5)
df["arrival_z"] = (df["arrival_tonnes"] - df["arr_mean"]) / (df["arr_std"] + 1e-5)
df["surplus_S"] = df["arrival_z"] * (-df["price_z"])

# ---------- engineered ----------
df["log_arrival"] = np.log1p(df["arrival_tonnes"].clip(lower=0))
df["price_spread"] = ((df["max_price"] - df["min_price"]) / df["modal_price"].replace(0, np.nan)
                      ).fillna(0).clip(0, 5).round(3)
df["month_num"] = df["date"].dt.month
df["day_num"] = df["date"].dt.day
df["is_weekend"] = (df["date"].dt.weekday >= 5).astype(int)
log["engineered"] = ["price_per_kg", "min_per_kg", "max_per_kg", "arrival_tonnes",
                     "baseline_mean", "baseline_std", "arr_mean", "arr_std",
                     "price_z", "arrival_z", "surplus_S",
                     "log_arrival", "price_spread", "month_num", "day_num", "is_weekend"]

# ---------- derived priority (DISCLOSED, quantile thresholds on S) ----------
s_hi = float(df["surplus_S"].quantile(0.75))
s_med = float(df["surplus_S"].quantile(0.40))
log["priority_rule"] = {
    "note": "DERIVED glut-proxy label, not observed waste",
    "formula": "S = arrival_z * (-price_z); High if S>=p75, Medium if S>=p40, else Low",
    "s_high_p75": round(s_hi, 4),
    "s_med_p40": round(s_med, 4),
}
df["redistribution_priority"] = np.where(
    df["surplus_S"] >= s_hi, "High",
    np.where(df["surplus_S"] >= s_med, "Medium", "Low"))
log["target_distribution"] = {k: int(v) for k, v in
                               df["redistribution_priority"].value_counts().items()}
log["target_mapping"] = {"High": 0, "Low": 1, "Medium": 2}

# keep lean cleaned frame (drop intermediates id/codes, keep geo for ranking)
# geo: 37% lat/lon missing in source — state-median impute + flag (keeps spatial signal)
cleaned_geo_missing = df[["latitude", "longitude"]].isna().any(axis=1)
df["geo_missing"] = cleaned_geo_missing.astype(int)
df["latitude"] = df["latitude"].fillna(df.groupby("state_name")["latitude"].transform("median"))
df["longitude"] = df["longitude"].fillna(df.groupby("state_name")["longitude"].transform("median"))
df["latitude"] = df["latitude"].fillna(df["latitude"].median())
df["longitude"] = df["longitude"].fillna(df["longitude"].median())
df["variety"] = df["variety"].fillna("UNKNOWN")
df["grade"] = df["grade"].fillna("UNKNOWN")
log["fixes"].append(
    f"geo missing {int(cleaned_geo_missing.sum())} rows -> state median + geo_missing flag; "
    "variety/grade NaN -> UNKNOWN")
keep = ["date", "state_name", "district_name", "market_center_name", "commodity_name",
        "variety", "grade", "latitude", "longitude", "geo_missing",
        "arrival_tonnes", "modal_price", "price_per_kg",
        "price_z", "arrival_z", "surplus_S",
        "log_arrival", "price_spread", "month_num", "day_num", "is_weekend",
        "redistribution_priority"]
cleaned = df[keep].copy()
assert cleaned.isna().sum().sum() == 0, "missing values remain!"
cleaned.to_csv(PROC / "freshroute_foodbank_cleaned.csv", index=False)
log["cleaned_shape"] = list(cleaned.shape)

# ---------- encode ----------
enc = cleaned.copy()
enc["redistribution_priority"] = enc["redistribution_priority"].map(log["target_mapping"])
# high-cardinality market/district kept out of X; state + top-commodity dummies only
top_comms = enc["commodity_name"].value_counts().nlargest(20).index
enc["commodity_top"] = enc["commodity_name"].where(enc["commodity_name"].isin(top_comms), "OTHER")
enc = pd.get_dummies(enc, columns=["state_name", "commodity_top"], drop_first=True, dtype=int)
enc = enc.drop(columns=["date", "district_name", "market_center_name",
                         "commodity_name", "variety", "grade"])
X_cols = [c for c in enc.columns if c != "redistribution_priority"]
log["X_columns"] = X_cols
log["encoded_shape"] = list(enc.shape)
enc.to_csv(PROC / "freshroute_foodbank_encoded.csv", index=False)
(PROC / "cleaning_report.json").write_text(json.dumps(log, indent=2))

# ---------- figures ----------
plt.rcParams.update({"figure.dpi": 120})
cleaned["redistribution_priority"].value_counts().reindex(
    ["High", "Medium", "Low"]).plot(kind="bar", color=["#b31b1b", "#e09f3e", "#2a9d8f"])
plt.title("Derived priority distribution (India APMC glut proxy)")
plt.ylabel("records")
plt.tight_layout(); plt.savefig(FIG / "01_priority_dist.png"); plt.close()

plt.hist(cleaned["price_per_kg"].clip(upper=cleaned["price_per_kg"].quantile(0.99)),
         bins=50, color="#264653")
plt.title("Modal price per kg (real, p99 clipped)")
plt.xlabel("Rs./kg"); plt.ylabel("records")
plt.tight_layout(); plt.savefig(FIG / "02_pounds_hist.png"); plt.close()

daily = cleaned.groupby("date")["arrival_tonnes"].sum()
daily.plot(marker="o", color="#b31b1b")
plt.title("Total arrivals by day (real, 24-day window)")
plt.ylabel("tonnes")
plt.tight_layout(); plt.savefig(FIG / "03_monthly_trend.png"); plt.close()

top = cleaned.groupby("commodity_name")["arrival_tonnes"].sum().nlargest(12)
top.plot(kind="barh", color="#2a9d8f")
plt.title("Top 12 commodities by total arrivals (real)")
plt.xlabel("total tonnes"); plt.tight_layout()
plt.savefig(FIG / "04_top_localities.png"); plt.close()

plt.scatter(cleaned["arrival_z"].clip(-4, 6), cleaned["price_z"].clip(-4, 4),
            c=cleaned["redistribution_priority"].map(
                {"High": "#b31b1b", "Medium": "#e09f3e", "Low": "#2a9d8f"}),
            alpha=0.15, s=4)
plt.title("Arrival surge vs price drop (color = derived priority)")
plt.xlabel("arrival_z"); plt.ylabel("price_z")
plt.tight_layout(); plt.savefig(FIG / "05_need_vs_supply.png"); plt.close()

num = cleaned[["arrival_tonnes", "price_per_kg", "price_z",
               "arrival_z", "surplus_S", "log_arrival", "price_spread"]]
plt.matshow(num.corr(), cmap="RdYlGn", vmin=-1, vmax=1)
plt.colorbar(); plt.xticks(range(len(num.columns)), num.columns, rotation=45, ha="left")
plt.yticks(range(len(num.columns)), num.columns)
plt.title("Numeric correlation matrix", pad=28)
plt.savefig(FIG / "06_corr_heatmap.png", bbox_inches="tight"); plt.close()

print(json.dumps({k: v for k, v in log.items() if k != "X_columns"}, indent=2))
print("X:", len(X_cols), "cols | cleaned:", cleaned.shape, "| encoded:", enc.shape)
