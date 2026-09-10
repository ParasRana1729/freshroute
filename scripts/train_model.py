"""FreshRoute CE-2: next-day glut forecasting + dispatch ranking.
Design (grilled + locked):
  - Forecast: features at day t -> priority at day t+1 (same market-commodity).
    No leakage: S/z-scores at t are legit predictors of the FUTURE label.
  - Time split: train on early target-dates, test on last 6 days.
  - Models: LogReg / RandomForest / XGBoost compared on F1-macro; winner picked.
  - Ranking demo: test predicted-High rows ranked into a move-first dispatch list.
Run: python scripts/train_model.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (f1_score, classification_report, confusion_matrix,
                             accuracy_score)
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "processed" / "freshroute_foodbank_cleaned.csv"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
MAP = {"High": 0, "Low": 1, "Medium": 2}
INV = {v: k for k, v in MAP.items()}

df = pd.read_csv(CLEAN, low_memory=False, parse_dates=["date"])
df = df.sort_values(["market_center_name", "commodity_name", "date"]).reset_index(drop=True)

# ---------- forecast pairs: X(t) -> y(t+1) ----------
key = ["market_center_name", "commodity_name"]
df["y_next"] = df.groupby(key)["redistribution_priority"].shift(-1)
df["date_next"] = df.groupby(key)["date"].shift(-1)
df["arr_next"] = df.groupby(key)["arrival_tonnes"].shift(-1)
pairs = df.dropna(subset=["y_next"]).copy()
pairs["y"] = pairs["y_next"].map(MAP).astype(int)
print(f"pairs: {len(pairs)} ({len(pairs)/len(df):.1%} of rows; one dropped per group-tail)")

FEAT_NUM = ["latitude", "longitude", "geo_missing", "arrival_tonnes", "modal_price",
            "price_per_kg", "price_z", "arrival_z", "surplus_S",
            "log_arrival", "price_spread", "month_num", "day_num", "is_weekend"]
pairs["commodity_top"] = pairs["commodity_name"].where(
    pairs["commodity_name"].isin(pairs["commodity_name"].value_counts().nlargest(20).index),
    "OTHER")

# ---------- time split on TARGET date: last 6 days = test ----------
cut = pairs["date_next"].sort_values().unique()[-6]
tr, te = pairs[pairs["date_next"] < cut], pairs[pairs["date_next"] >= cut]
print(f"train target-dates < {cut.date()} ({len(tr)}), test >= ({len(te)})")
print("train dist:", tr["y_next"].value_counts().to_dict())
print("test dist:", te["y_next"].value_counts().to_dict())

Xtr_raw = pd.get_dummies(tr[FEAT_NUM + ["state_name", "commodity_top"]],
                         columns=["state_name", "commodity_top"], dtype=int)
Xte_raw = pd.get_dummies(te[FEAT_NUM + ["state_name", "commodity_top"]],
                         columns=["state_name", "commodity_top"], dtype=int)
Xte_raw = Xte_raw.reindex(columns=Xtr_raw.columns, fill_value=0)
ytr, yte = tr["y"].to_numpy(), te["y"].to_numpy()

def cf_matrix_plot(cm, title, path):
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1, 2], ["High", "Low", "Med"])
    ax.set_yticks([0, 1, 2], ["High", "Low", "Med"])
    ax.set_xlabel("predicted"); ax.set_ylabel("actual (next day)")
    ax.set_title(title)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=9)
    fig.colorbar(im); plt.tight_layout(); plt.savefig(path); plt.close()

results, fitted = {}, {}
# majority baseline (honesty anchor)
maj = int(np.bincount(ytr).argmax())
base_pred = np.full_like(yte, maj)
results["Baseline_majority"] = {"f1_macro": round(float(f1_score(yte, base_pred, average="macro")), 4),
                                "accuracy": round(float(accuracy_score(yte, base_pred)), 4)}

pipe_lr = Pipeline([("sc", StandardScaler()),
                    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
rf = RandomForestClassifier(n_estimators=150, class_weight="balanced_subsample",
                            n_jobs=-1, random_state=42)
xgb = XGBClassifier(n_estimators=300, learning_rate=0.08, max_depth=7,
                    subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                    objective="multi:softprob", num_class=3, n_jobs=-1,
                    random_state=42, eval_metric="mlogloss")
for name, model in [("LogReg", pipe_lr), ("RandomForest", rf), ("XGBoost", xgb)]:
    model.fit(Xtr_raw, ytr)
    pred = model.predict(Xte_raw)
    f1m = f1_score(yte, pred, average="macro")
    results[name] = {"f1_macro": round(float(f1m), 4),
                     "accuracy": round(float(accuracy_score(yte, pred)), 4),
                     "report": classification_report(yte, pred,
                         target_names=["High", "Low", "Medium"], output_dict=True)}
    fitted[name] = (model, pred)
    cf_matrix_plot(confusion_matrix(yte, pred), f"Next-day priority — {name} (time-split test)",
                   FIG / f"10_confusion_{name}.png")
    print(f"{name}: F1-macro={f1m:.4f} acc={results[name]['accuracy']:.4f}")

winner = max(["LogReg", "RandomForest", "XGBoost"], key=lambda m: results[m]["f1_macro"])
print("WINNER:", winner)
wmodel, wpred = fitted[winner]

# feature importance from winner (tree) or |coef| (logreg)
plt.figure(figsize=(8, 6))
if winner == "LogReg":
    imp = pd.Series(abs(wmodel.named_steps["clf"].coef_).mean(axis=0), index=Xtr_raw.columns)
else:
    clf = wmodel if winner == "RandomForest" else wmodel
    imp = pd.Series(clf.feature_importances_, index=Xtr_raw.columns)
imp.nlargest(15).sort_values().plot(kind="barh", color="#264653")
plt.title(f"Top 15 features — {winner} (next-day glut forecast)")
plt.tight_layout(); plt.savefig(FIG / "11_feature_importance.png"); plt.close()

# ---------- ranking demo: predicted-High test rows -> move-first list ----------
proba = wmodel.predict_proba(Xte_raw)[:, MAP["High"]]
out = te[["date_next", "state_name", "district_name", "market_center_name",
          "commodity_name", "arrival_tonnes", "price_per_kg", "surplus_S"]].copy()
out["P_High_next"] = proba.round(3)
out["pred_next"] = [INV[p] for p in wpred]
dispatch = (out[out["pred_next"] == "High"]
            .sort_values(["P_High_next", "arrival_tonnes"], ascending=False)
            .head(50))
dispatch.to_csv(PROC / "dispatch_list_demo.csv", index=False)

metrics = {"task": "next-day priority forecast X(t)->y(t+1), time split",
           "test_target_dates": [str(te['date_next'].min().date()), str(te['date_next'].max().date())],
           "n_train": len(tr), "n_test": len(te),
           "results": {k: {kk: vv for kk, vv in v.items() if kk != "report"} for k, v in results.items()},
           "winner": winner,
           "dispatch_demo_rows": len(dispatch)}
(PROC / "model_metrics.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
