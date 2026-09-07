"""
FreshRoute — Iteration 1: CE-1 cleaning / encoding / EDA pipeline.
Input : data/raw/freshroute_foodbank_raw.csv
Outputs:
  data/processed/freshroute_foodbank_cleaned.csv  (cleaned, readable)
  data/processed/freshroute_foodbank_encoded.csv  (ML-ready)
  data/processed/cleaning_report.json
  reports/figures/*.png (6 EDA graphs)
Run: python scripts/clean_dataset.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "freshroute_foodbank_raw.csv"
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
FIG = Path(__file__).resolve().parents[1] / "reports" / "figures"
PROC.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW)
report = {"raw_rows": len(df), "raw_cols": len(df.columns)}
report["missing_before"] = df.isna().sum()[df.isna().sum() > 0].to_dict()
report["exact_duplicates_before"] = int(df.duplicated().sum())

# 1. Drop exact duplicates
df = df.drop_duplicates().reset_index(drop=True)
report["rows_after_dedup"] = len(df)

# 2. Drop irrelevant columns (not useful for redistribution model)
df = df.drop(columns=["donor_contact_number", "remarks"])
report["dropped_irrelevant"] = ["donor_contact_number", "remarks"]

# 3. Normalise categoricals: strip, title-case, map variants
def norm_city(x):
    if pd.isna(x): return x
    x = str(x).strip().title()
    return x
def norm_generic(x):
    if pd.isna(x): return x
    return str(x).strip().title()

for c in ["city", "state", "donor_type", "food_type", "storage_condition", "foodbank_id"]:
    df[c] = df[c].apply(lambda x: str(x).strip() if pd.isna(x) is False and c == "foodbank_id" else (norm_city(x) if c == "city" else norm_generic(x)))

# transport Yes/No variants
trans_map = {"Yes": "Yes", "Y": "Yes", "No": "No", "N": "No", "Nan": np.nan}
def norm_trans(x):
    if pd.isna(x): return np.nan
    t = str(x).strip().title()
    if t in ("Yes", "Y"): return "Yes"
    if t in ("No", "N"): return "No"
    if t in ("Med",): return t  # safety, not here
    return t
df["transport_available"] = df["transport_available"].apply(norm_trans)
df["transport_available"] = df["transport_available"].replace({"Y": "Yes", "N": "No"})

# priority variants: med -> Medium
def norm_pri(x):
    if pd.isna(x): return x
    t = str(x).strip().title()
    if t == "Med": return "Medium"
    return t
df["redistribution_priority"] = df["redistribution_priority"].apply(norm_pri)
df["redistribution_priority"] = df["redistribution_priority"].replace({"Med": "Medium"})
# keep only valid levels
df = df[df["redistribution_priority"].isin(["Low", "Medium", "High"])].reset_index(drop=True)

# donation_date -> datetime + engineered month/dayofweek
df["donation_date"] = pd.to_datetime(df["donation_date"], errors="coerce")
df["donation_month"] = df["donation_date"].dt.month
df["donation_dayofweek"] = df["donation_date"].dt.dayofweek

# 4. Fix incorrect numerics -> NaN for later median imputation
num_cols = ["quantity_donated_kg", "quantity_available_kg", "shelf_life_hours",
            "storage_temp_C", "distance_to_foodbank_km", "foodbank_capacity_kg",
            "current_stock_kg", "beneficiaries_count"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df.loc[df["quantity_donated_kg"] <= 0, "quantity_donated_kg"] = np.nan
df.loc[df["distance_to_foodbank_km"] < 0, "distance_to_foodbank_km"] = np.nan
df.loc[~df["shelf_life_hours"].between(1, 240), "shelf_life_hours"] = np.nan
df.loc[~df["storage_temp_C"].between(-5, 50), "storage_temp_C"] = np.nan
# available cannot exceed donated -> cap at donated where both known
mask = df["quantity_available_kg"].notna() & df["quantity_donated_kg"].notna()
df.loc[mask & (df["quantity_available_kg"] > df["quantity_donated_kg"]), "quantity_available_kg"] = \
    df.loc[mask & (df["quantity_available_kg"] > df["quantity_donated_kg"]), "quantity_donated_kg"]
report["incorrect_fixed"] = "negatives/0/500h/60C capped to NaN; available>donated capped"

# 5. Missing values: median (numeric), mode (categorical)
# storage_temp_C -> group-wise median by storage_condition (cold vs room differ)
if df["storage_temp_C"].isna().any():
    df["storage_temp_C"] = df.groupby("storage_condition")["storage_temp_C"].transform(
        lambda s: s.fillna(s.median()))
    # fallback if a group is all-NaN
    df["storage_temp_C"] = df["storage_temp_C"].fillna(df["storage_temp_C"].median())
for c in num_cols + ["donation_month", "donation_dayofweek"]:
    if c == "storage_temp_C":
        continue
    if df[c].isna().any():
        df[c] = df[c].fillna(df[c].median())
# cast count-like floats back to int
for c in ["shelf_life_hours", "beneficiaries_count", "foodbank_capacity_kg", "current_stock_kg"]:
    df[c] = df[c].round(0).astype(int)
for c in ["city", "state", "donor_type", "food_type", "storage_condition",
          "foodbank_id", "transport_available", "storage_temp_C"]:
    if c in df.columns and df[c].isna().any():
        df[c] = df[c].fillna(df[c].mode()[0])
# donation_date NaT (if any) -> mode date
if df["donation_date"].isna().any():
    df["donation_date"] = df["donation_date"].fillna(df["donation_date"].mode()[0])
report["missing_after"] = int(df.isna().sum().sum())

# 6. Feature engineering (interpretable, India-relevant)
df["stock_pressure"] = (df["current_stock_kg"] / df["foodbank_capacity_kg"]).round(3)
df["surplus_ratio"] = (df["quantity_available_kg"] / df["quantity_donated_kg"]).round(3)
df["need_per_km"] = (df["beneficiaries_count"] / (df["distance_to_foodbank_km"] + 1)).round(2)
df["is_perishable"] = df["shelf_life_hours"].apply(lambda x: 1 if x < 24 else 0)
df["cold_chain_ok"] = ((df["storage_condition"] == "Cold") & (df["storage_temp_C"] <= 8)).astype(int)

# Save cleaned (readable)
df_clean = df.copy()
df_clean.to_csv(PROC / "freshroute_foodbank_cleaned.csv", index=False)

# 7. Encoding -> ML-ready
cat_onehot = ["city", "state", "donor_type", "food_type", "storage_condition",
              "foodbank_id", "transport_available"]
df_enc = pd.get_dummies(df_clean, columns=cat_onehot, drop_first=True, dtype=int)
le = LabelEncoder()
df_enc["redistribution_priority"] = le.fit_transform(df_clean["redistribution_priority"])
report["label_mapping"] = {cls: int(i) for i, cls in enumerate(le.classes_)}
# donation_date -> drop string, keep engineered month/dow
df_enc = df_enc.drop(columns=["donation_id", "donation_date"])
df_enc.to_csv(PROC / "freshroute_foodbank_encoded.csv", index=False)

# X / y definition
target = "redistribution_priority"
X_cols = [c for c in df_enc.columns if c != target]
report["X_shape"] = [int(df_enc.shape[0]), int(len(X_cols))]
report["y_distribution"] = df_clean["redistribution_priority"].value_counts().to_dict()
report["X_columns"] = X_cols
report["final_rows"] = len(df_clean)

with open(PROC / "cleaning_report.json", "w") as f:
    json.dump(report, f, indent=2)

# 8. EDA figures (6)
sns.set(style="whitegrid")
plt.rcParams["figure.figsize"] = (8, 5)

def save(figpath):
    plt.tight_layout()
    plt.savefig(figpath, dpi=150)
    plt.close()

# F1: priority distribution
ax = df_clean["redistribution_priority"].value_counts().reindex(["Low", "Medium", "High"]).plot(kind="bar")
plt.title("Redistribution priority distribution")
plt.xlabel("Priority (target y)"); plt.ylabel("Donations")
save(FIG / "01_priority_dist.png")

# F2: food type vs available qty
sns.boxplot(data=df_clean, x="food_type", y="quantity_available_kg")
plt.title("Available quantity by food type"); plt.xticks(rotation=20)
save(FIG / "02_foodtype_qty.png")

# F3: shelf life vs priority
sns.boxplot(data=df_clean, x="redistribution_priority", y="shelf_life_hours",
            order=["Low", "Medium", "High"])
plt.title("Shelf life by priority (perishables -> High)")
save(FIG / "03_shelf_priority.png")

# F4: donor type counts
df_clean["donor_type"].value_counts().plot(kind="bar")
plt.title("Donations by donor type (Langars = key surplus source)")
plt.xlabel("Donor type"); plt.ylabel("Count"); plt.xticks(rotation=20)
save(FIG / "04_donor_counts.png")

# F5: distance vs beneficiaries scatter by priority
sns.scatterplot(data=df_clean, x="distance_to_foodbank_km", y="beneficiaries_count",
                hue="redistribution_priority", hue_order=["Low", "Medium", "High"], alpha=0.7)
plt.title("Need vs distance (near + high-need = High priority)")
save(FIG / "05_distance_need.png")

# F6: correlation heatmap (numeric)
num = ["quantity_donated_kg", "quantity_available_kg", "shelf_life_hours",
       "distance_to_foodbank_km", "beneficiaries_count", "stock_pressure",
       "surplus_ratio", "need_per_km"]
plt.figure(figsize=(9, 7))
sns.heatmap(df_clean[num].corr(), annot=True, fmt=".2f", cmap="YlGnBu")
plt.title("Numeric feature correlations")
save(FIG / "06_corr_heatmap.png")

print(json.dumps(report, indent=2))
print(f"Cleaned: {df_clean.shape} -> {PROC/'freshroute_foodbank_cleaned.csv'}")
print(f"Encoded: {df_enc.shape} -> {PROC/'freshroute_foodbank_encoded.csv'}")
