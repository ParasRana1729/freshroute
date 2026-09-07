"""
FreshRoute — Iteration 1: Raw dataset generator (India food-bank optimizer)
- Simulates realistic food-donation / redistribution records for CE-1.
- Intentionally injects duplicates, missing values, inconsistent casing,
  incorrect negatives and irrelevant columns so Data Cleaning can be demoed.
- Deterministic with seed=42. Output: data/raw/freshroute_foodbank_raw.csv
Run: python scripts/generate_dataset.py
"""
import random
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
N = 600
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "freshroute_foodbank_raw.csv"

random.seed(SEED)
np.random.seed(SEED)

cities_states = [
    ("Amritsar", "Punjab"), ("Ludhiana", "Punjab"), ("Jalandhar", "Punjab"),
    ("Patiala", "Punjab"), ("Bathinda", "Punjab"), ("Chandigarh", "Chandigarh UT"),
    ("Delhi", "Delhi"), ("Jaipur", "Rajasthan"),
]
donor_types = ["Restaurant", "Gurudwara Langar", "Supermarket", "Farm",
               "Wedding Hall", "Hostel Mess", "Household"]
food_types = ["Cooked Meals", "Rice", "Wheat Flour", "Vegetables",
              "Fruits", "Dairy", "Bread/Bakery"]
storage_conds = ["Cold", "Room", "No Storage"]
foodbanks = ["FB-01", "FB-02", "FB-03", "FB-04", "FB-05"]

# Base shelf-life per food type (hours) — used to derive realistic values
shelf_base = {"Cooked Meals": 8, "Rice": 72, "Wheat Flour": 120,
              "Vegetables": 36, "Fruits": 48, "Dairy": 24, "Bread/Bakery": 18}

def priority_rule(q_avail, shelf, beneficiaries, dist, transport):
    # Simple explainable rule so EDA shows signal (not random noise)
    score = 0
    score += 2 if q_avail > 80 else (1 if q_avail > 30 else 0)
    score += 2 if shelf < 12 else (1 if shelf < 30 else 0)
    score += 2 if beneficiaries > 300 else (1 if beneficiaries > 120 else 0)
    score += 1 if dist < 15 else 0
    score += 1 if str(transport).strip().lower() in ("yes", "y") else 0
    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"

rows = []
for i in range(N):
    city, state = cities_states[np.random.choice(len(cities_states))]
    donor = np.random.choice(donor_types, p=[0.18, 0.22, 0.15, 0.12, 0.10, 0.13, 0.10])
    food = np.random.choice(food_types)
    q_don = round(float(np.random.gamma(5, 18) + 5), 1)  # 5..~300kg skewed
    q_don = min(q_don, 500.0)
    # available <= donated with small loss
    q_avail = round(q_don * np.random.uniform(0.55, 0.98), 1)
    shelf = int(np.random.normal(shelf_base[food], shelf_base[food] * 0.3))
    shelf = max(2, shelf)
    storage = np.random.choice(storage_conds, p=[0.35, 0.45, 0.20])
    temp = {"Cold": np.random.normal(4, 1.5), "Room": np.random.normal(25, 3),
            "No Storage": np.random.normal(30, 4)}[storage]
    temp = round(float(temp), 1)
    dist = round(float(np.random.gamma(3, 5) + 0.5), 1)
    fb = np.random.choice(foodbanks)
    cap = int(np.random.choice([500, 800, 1000, 1500]))
    stock = int(np.random.uniform(0.1, 0.95) * cap)
    bene = int(np.random.gamma(4, 60) + 10)
    transport = np.random.choice(["Yes", "No"], p=[0.72, 0.28])
    pri = priority_rule(q_avail, shelf, bene, dist, transport)
    date = pd.Timestamp("2026-01-05") + pd.Timedelta(days=int(np.random.randint(0, 65)))
    rows.append([f"DON-{i+1:04d}", date.date().isoformat(), city, state, donor, food,
                 q_don, q_avail, shelf, storage, temp, dist, fb, cap, stock,
                 bene, transport, pri,
                 f"+91-98{np.random.randint(1000000, 9999999)}",
                 np.random.choice(["ok", "urgent pickup", "festival surplus", ""])])
cols = ["donation_id", "donation_date", "city", "state", "donor_type", "food_type",
        "quantity_donated_kg", "quantity_available_kg", "shelf_life_hours",
        "storage_condition", "storage_temp_C", "distance_to_foodbank_km",
        "foodbank_id", "foodbank_capacity_kg", "current_stock_kg",
        "beneficiaries_count", "transport_available", "redistribution_priority",
        "donor_contact_number", "remarks"]
df = pd.DataFrame(rows, columns=cols)

# ---- Inject messiness for CE-1 cleaning demo ----
# 1. Duplicates (~3%)
dupes = df.sample(18, random_state=SEED).copy()
df = pd.concat([df, dupes], ignore_index=True)

# 2. Missing values
rng = np.random.RandomState(SEED)
for col, frac in [("storage_temp_C", 0.08), ("quantity_available_kg", 0.05),
                  ("transport_available", 0.05), ("shelf_life_hours", 0.03),
                  ("beneficiaries_count", 0.02)]:
    idx = rng.choice(df.index, size=int(len(df) * frac), replace=False)
    df.loc[idx, col] = np.nan

# 3. Inconsistent casing / whitespace
def mess(s, variants):
    if pd.isna(s):
        return s
    return rng.choice(variants.get(s, [s]))
city_map = {"Amritsar": ["amritsar ", "AMRITSAR", "Amritsar"],
            "Ludhiana": ["ludhiana", "LUDHIANA ", "Ludhiana"],
            "Chandigarh": ["chandigarh ", "CHANDIGARH", "Chandigarh"]}
df["city"] = df["city"].apply(lambda x: mess(x, city_map))
food_map = {"Rice": ["rice ", "RICE", "Rice"], "Vegetables": ["vegetables", "VEGETABLES ", "Vegetables"],
            "Cooked Meals": ["cooked meals ", "COOKED MEALS", "Cooked Meals"]}
df["food_type"] = df["food_type"].apply(lambda x: mess(x, food_map))
trans_map = {"Yes": ["yes", "Y", "YES ", "Yes"], "No": ["no ", "N", "NO", "No"]}
df["transport_available"] = df["transport_available"].apply(
    lambda x: mess(x, trans_map) if pd.notna(x) else x)
pri_map = {"High": ["high", "HIGH ", "High"], "Medium": ["med", "MEDIUM ", "Medium"],
           "Low": ["low ", "LOW", "Low"]}
df["redistribution_priority"] = df["redistribution_priority"].apply(lambda x: mess(x, pri_map))

# 4. Incorrect values
idx = rng.choice(df.index, size=8, replace=False)
df.loc[idx, "quantity_donated_kg"] = -df.loc[idx, "quantity_donated_kg"]  # negatives
idx = rng.choice(df.index, size=10, replace=False)
df.loc[idx, "distance_to_foodbank_km"] = -df.loc[idx, "distance_to_foodbank_km"]
idx = rng.choice(df.index, size=6, replace=False)
df.loc[idx, "shelf_life_hours"] = rng.choice([0, 500], size=6)  # impossible
idx = rng.choice(df.index, size=12, replace=False)  # available > donated
df.loc[idx, "quantity_available_kg"] = df.loc[idx, "quantity_donated_kg"] * 1.4
idx = rng.choice(df.index, size=5, replace=False)
df.loc[idx, "storage_temp_C"] = 60.0  # sensor error

# Shuffle
df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)
print(f"Wrote {len(df)} rows x {len(df.columns)} cols -> {OUT}")
print("Missing per col:\n", df.isna().sum()[df.isna().sum() > 0])
print("Dups:", df.duplicated().sum())
