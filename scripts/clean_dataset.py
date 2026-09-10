"""FreshRoute CE-1 pipeline on REAL data.
Raw: Blue Ridge Area Food Bank distribution records (Virginia Open Data Portal)
     + UNEP Food Waste Index (India anchor).
Steps: load -> dedupe -> fix negatives -> missing-value treatment ->
       type fixes -> feature engineering -> derived priority label ->
       encode -> save cleaned/encoded/report/figures.
Run: python scripts/clean_dataset.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW_BRAFB = ROOT / "data" / "raw" / "brafb_virginia_foodbank.csv"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
RNG = np.random.RandomState(42)

log = {"fixes": []}
PROC.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# ---------- load ----------
df = pd.read_csv(RAW_BRAFB)
log["raw_shape"] = list(df.shape)
log["raw_missing"] = {k: int(v) for k, v in df.isna().sum().items() if v > 0}

# ---------- dedupe ----------
n0 = len(df)
df = df.drop_duplicates().reset_index(drop=True)
log["fixes"].append(f"dropped {n0 - len(df)} exact duplicate rows")

# ---------- normalize text ----------
df["Month"] = df["Month"].str.strip().str.upper()
df["Locality"] = df["Locality"].str.strip().str.upper()

# ---------- negatives -> NaN (physically impossible) ----------
num_cols = ["Households Served", "Individuals Served",
            "Pounds of Food Distributed",
            "Children Served via non-federal child nutrition programs",
            "Pounds of food distributed via non-federal child nutrition prog."]
neg = {c: int((df[c] < 0).sum()) for c in num_cols}
log["negatives_fixed"] = {k: v for k, v in neg.items() if v}
for c in num_cols:
    df.loc[df[c] < 0, c] = np.nan

# ---------- missing values ----------
# PITTSYLVANIA-style rows: program-only records (no household service that month).
# Households/Individuals NaN + zero pounds -> true zeros, flagged.
prog_only = df["Households Served"].isna() & df["Individuals Served"].isna()
df["is_program_only_record"] = prog_only
df.loc[prog_only, ["Households Served", "Individuals Served"]] = 0
log["fixes"].append(
    f"{int(prog_only.sum())} program-only rows: Households/Individuals NaN -> 0 + flag")
# Children-served col is 58% missing -> median impute + missingness flag (keeps signal).
df["child_data_missing"] = df[
    "Children Served via non-federal child nutrition programs"].isna()
med_child = df[
    "Children Served via non-federal child nutrition programs"].median()
df["Children Served via non-federal child nutrition programs"] = df[
    "Children Served via non-federal child nutrition programs"].fillna(med_child)
log["fixes"].append(
    f"children-served NaN -> median ({med_child:.1f}) + child_data_missing flag")
# Any leftover NaN in numerics -> median.
for c in num_cols:
    if df[c].isna().any():
        df[c] = df[c].fillna(df[c].median())
        log["fixes"].append(f"leftover NaN in '{c}' -> median")

# ---------- types: counts are whole people, pounds to 1dp ----------
for c in ["Households Served", "Individuals Served",
          "Children Served via non-federal child nutrition programs"]:
    df[c] = df[c].round().astype(int)
df["Pounds of Food Distributed"] = df["Pounds of Food Distributed"].round(1)
df["Pounds of food distributed via non-federal child nutrition prog."] = df[
    "Pounds of food distributed via non-federal child nutrition prog."].round(1)
df["Month"] = pd.Categorical(df["Month"], categories=MONTHS, ordered=True)
df["Year"] = df["Year"].astype(int)
log["fixes"].append("counts rounded to int; pounds to 1dp; Month ordered JAN..DEC")

# ---------- feature engineering ----------
df["pounds_per_household"] = (df["Pounds of Food Distributed"]
                              / df["Households Served"].replace(0, np.nan)).fillna(0).round(2)
df["pounds_per_individual"] = (df["Pounds of Food Distributed"]
                               / df["Individuals Served"].replace(0, np.nan)).fillna(0).round(2)
df["child_pound_share"] = (df["Pounds of food distributed via non-federal child nutrition prog."]
                           / df["Pounds of Food Distributed"].replace(0, np.nan)
                           ).fillna(0).clip(0, 1).round(3)
df["is_covid_era"] = (df["Year"] >= 2020).astype(int)
df["month_num"] = df["Month"].cat.codes + 1
log["engineered"] = ["pounds_per_household", "pounds_per_individual",
                     "child_pound_share", "is_covid_era", "month_num",
                     "is_program_only_record", "child_data_missing"]

# ---------- derived priority label (DISCLOSED rule, not observed) ----------
# High need + thin supply-per-person -> High; ample supply-per-person -> Low.
served = df.loc[~df["is_program_only_record"], "Individuals Served"]
supply = df.loc[~df["is_program_only_record"], "pounds_per_individual"]
need_hi = served.quantile(0.50)
sup_lo = supply.quantile(1 / 3)
sup_hi = supply.quantile(2 / 3)
log["priority_rule"] = {
    "note": "DERIVED label for triage demo, not an observed quantity",
    "need_hi_individuals": float(round(need_hi, 1)),
    "supply_lo_ppi": float(round(sup_lo, 3)),
    "supply_hi_ppi": float(round(sup_hi, 3)),
    "rule": ("High if individuals>=need_hi AND ppi<=supply_lo "
             "(program-only rows default Medium); "
             "Low if ppi>=supply_hi; else Medium"),
}
cond_high = ((df["Individuals Served"] >= need_hi)
             & (df["pounds_per_individual"] <= sup_lo)
             & (~df["is_program_only_record"]))
cond_low = (df["pounds_per_individual"] >= sup_hi) & (~df["is_program_only_record"])
df["redistribution_priority"] = np.where(cond_high, "High",
                                         np.where(cond_low, "Low", "Medium"))
log["target_distribution"] = {k: int(v) for k, v in
                              df["redistribution_priority"].value_counts().items()}
log["target_mapping"] = {"High": 0, "Low": 1, "Medium": 2}

assert df.isna().sum().sum() == 0, "missing values remain!"
df.to_csv(PROC / "freshroute_foodbank_cleaned.csv", index=False)

# ---------- encode ----------
enc = df.copy()
enc["redistribution_priority"] = enc["redistribution_priority"].map(
    log["target_mapping"])
nominals = ["Month", "Locality"]
enc = pd.get_dummies(enc, columns=nominals, drop_first=True, dtype=int)
drop = []  # keep all engineered + dummies; nothing PII-like present
X_cols = [c for c in enc.columns if c != "redistribution_priority"]
log["X_columns"] = X_cols
log["encoded_shape"] = list(enc.shape)
enc.to_csv(PROC / "freshroute_foodbank_encoded.csv", index=False)
(PROC / "cleaning_report.json").write_text(json.dumps(log, indent=2))

# ---------- figures ----------
plt.rcParams.update({"figure.dpi": 120})
df["redistribution_priority"].value_counts().reindex(
    ["High", "Medium", "Low"]).plot(kind="bar", color=["#b31b1b", "#e09f3e", "#2a9d8f"])
plt.title("Derived priority distribution (real base data)")
plt.ylabel("records")
plt.tight_layout(); plt.savefig(FIG / "01_priority_dist.png"); plt.close()

plt.hist(df["Pounds of Food Distributed"], bins=40, color="#264653")
plt.title("Pounds distributed per locality-month (real)")
plt.xlabel("pounds"); plt.ylabel("records")
plt.tight_layout(); plt.savefig(FIG / "02_pounds_hist.png"); plt.close()

ms = df.groupby("Month", observed=True)["Pounds of Food Distributed"].mean()
ms.reindex(MONTHS).plot(marker="o", color="#b31b1b")
plt.title("Avg pounds distributed by month (real, Jan19–Jun21)")
plt.ylabel("avg pounds")
plt.tight_layout(); plt.savefig(FIG / "03_monthly_trend.png"); plt.close()

top = df.groupby("Locality")["Pounds of Food Distributed"].sum().nlargest(12)
top.plot(kind="barh", color="#2a9d8f")
plt.title("Top 12 localities by total pounds (real)")
plt.xlabel("total pounds"); plt.tight_layout()
plt.savefig(FIG / "04_top_localities.png"); plt.close()

plt.scatter(df["Individuals Served"], df["pounds_per_individual"],
            c=df["redistribution_priority"].map(
                {"High": "#b31b1b", "Medium": "#e09f3e", "Low": "#2a9d8f"}),
            alpha=0.6)
plt.title("Need vs supply-per-person (color = derived priority)")
plt.xlabel("individuals served"); plt.ylabel("pounds per individual")
plt.tight_layout(); plt.savefig(FIG / "05_need_vs_supply.png"); plt.close()

num = df[["Households Served", "Individuals Served", "Pounds of Food Distributed",
          "pounds_per_household", "pounds_per_individual", "child_pound_share"]]
plt.matshow(num.corr(), cmap="RdYlGn", vmin=-1, vmax=1)
plt.colorbar(); plt.xticks(range(len(num.columns)), num.columns, rotation=45, ha="left")
plt.yticks(range(len(num.columns)), num.columns)
plt.title("Numeric correlation matrix", pad=28)
plt.savefig(FIG / "06_corr_heatmap.png", bbox_inches="tight"); plt.close()

print(json.dumps({k: v for k, v in log.items() if k != "X_columns"}, indent=2))
print("X:", len(X_cols), "cols | cleaned:", df.shape, "| encoded:", enc.shape)
