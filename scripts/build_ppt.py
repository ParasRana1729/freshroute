"""Build FreshRoute CE-1 PPT by cloning the Chitkara template (keeps masters/logos/footers)."""
from pathlib import Path
from copy import deepcopy
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(r"C:\Users\paras\.t3\userdata\attachments\4590ee11-5adc-4120-bfd4-376c594da19c-0da3de38-c8ed-41f6-9a98-e39e4dbbc42c-pptx.pptx")
OUT = ROOT / "docs" / "FreshRoute_CE1_Presentation.pptx"
FIG = ROOT / "reports" / "figures"
PROC = ROOT / "data" / "processed"

prs = Presentation(str(TEMPLATE))
CHITKARA_RED = RGBColor(0xB3, 0x1B, 0x1B)
DARK = RGBColor(0x22, 0x22, 0x22)

def set_text(shape, text, size=54, bold=True, italic=False, font="Calibri", color=None, align=PP_ALIGN.CENTER):
    shape.text_frame.clear()
    p = shape.text_frame.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    if color:
        r.font.color.rgb = color

def add_body(slide, bullets, left=1.2, top=2.0, width=13.2, height=4.8, size=15):
    tx = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tx.text_frame
    tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(6)
        p.level = 0
        # bold lead before '—' or ':'
        r = p.add_run()
        r.text = "• " + b
        r.font.size = Pt(size)
        r.font.name = "Arial"
        r.font.color.rgb = DARK
    return tx

def add_table(slide, rows, cols, data, left=1.2, top=2.1, width=13.2, height=3.6, fs=12):
    tx = slide.shapes.add_table(len(data), len(data[0]), Inches(left), Inches(top), Inches(width), Inches(height))
    tbl = tx.table
    for j in range(len(data[0])):
        tbl.columns[j].width = Inches(width / len(data[0]))
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                p.space_after = Pt(1)
                for r in p.runs:
                    r.font.size = Pt(fs if i else fs + 1)
                    r.font.name = "Arial"
                    r.font.bold = (i == 0)
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else DARK
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = CHITKARA_RED
    return tx

def find_shape(slide, substr):
    for shp in slide.shapes:
        if shp.has_text_frame and substr.lower() in shp.text.lower():
            return shp
    return None

# ---- SLIDE 1: title + team ----
s1 = prs.slides[0]
t = find_shape(s1, "Project Title")
if t: set_text(t, "FreshRoute — Food Bank Optimizer Model (for India)", size=32, bold=True, italic=True, font="Calibri")
team = find_shape(s1, "TEAM DETAILS")
if team:
    team.text_frame.clear()
    lines = ["TEAM DETAILS:", "Member 1 — Name, Roll No.  •  Member 2 — Name, Roll No.",
             "Member 3 — Name, Roll No.  •  Member 4 — Name, Roll No.", "CE-1 • AI/ML 24CSE0316 • B.E. CSE 5th Sem"]
    for i, ln in enumerate(lines):
        p = team.text_frame.paragraphs[0] if i == 0 else team.text_frame.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = ln
        r.font.size = Pt(14 if i == 0 else 12); r.font.bold = (i == 0)
        r.font.name = "Times New Roman"

# ---- SLIDE 2: overview ----
add_body(prs.slides[1], [
    "What: predicts redistribution_priority (Low / Medium / High) for each surplus donation — who should get it first.",
    "Users: food banks, langars / messes / wedding halls (donors), NGOs & shelters (receivers), volunteers.",
    "Inputs → output: donor + food type + qty + shelf-life + storage + distance + demand → priority + ranked destination.",
    "CE-1 scope: dataset refined, cleaned (618×25, 0 missing), encoded (618×45), analysed — model training in CE-2.",
])

# ---- SLIDE 3: problem ----
add_body(prs.slides[2], [
    "Real problem: surplus is perishable & scattered (cooked meals ~8h); donors don't know which food bank has need/capacity.",
    "Result: edible food spoils while nearby shelters face shortages — especially at festivals/weddings & langar surplus peaks.",
    "ML fix: learn priority from supply × urgency × logistics × demand instead of fixed rules; CE-2 adds dispatch ranking.",
    "CE-1 frames it as supervised classification with frozen X/y contract and audited bias (73% Medium).",
])

# ---- SLIDE 4: objectives (replace example text) ----
s4 = prs.slides[3]
for shp in list(s4.shapes):
    if shp.has_text_frame and "Define 3" in shp.text:
        shp.text_frame.clear()
        objs = [
            "1. Build India-relevant dataset: 600+ records, 7 donor types, 7 food types, 5 food banks (Pb + Chd + Delhi + Jaipur).",
            "2. Deliver zero-missing, de-duplicated data with group-aware imputation — ready for train_test_split.",
            "3. Encode correctly (One-Hot nominals, Label target) + engineer 5 features; freeze X (44) / y contract.",
            "4. EDA with 6 figures + observations to justify features and expose imbalance for CE-2 mitigation.",
        ]
        for i, o in enumerate(objs):
            p = shp.text_frame.paragraphs[0] if i == 0 else shp.text_frame.add_paragraph()
            p.space_after = Pt(8)
            r = p.add_run(); r.text = o
            r.font.size = Pt(15); r.font.name = "Arial"; r.font.color.rgb = DARK

# ---- SLIDE 5: dataset ----
add_table(prs.slides[4], 0, 0, [
    ["File", "Shape", "Note"],
    ["raw", "636 × 20", "seed-42 synthetic, Jan–Mar 2026; 18 dups + errors injected"],
    ["cleaned", "618 × 25", "0 missing; +5 engineered features"],
    ["encoded", "618 × 45", "29 dummies + label y; X=44, stratify needed"],
    ["target y", "M456/H122/L40", "Medium 73.8% — imbalanced by design"],
], fs=12)

# ---- SLIDE 6: cleaning ----
add_body(prs.slides[5], [
    "Duplicates: 18 exact rows removed (636 → 618), verified in cleaning_report.json.",
    "Dropped irrelevant: donor_contact_number, remarks (PII/noise).",
    "Normalised: city/food/transport/priority casing (amritsar→Amritsar, y→Yes, med→Medium).",
    "Fixed incorrect → NaN → imputed: –ve qty/dist, shelf 0/500h, temp 60°C; available>donated capped.",
    "Types: donation_date → datetime + month/weekday; counts cast to int.",
])

# ---- SLIDE 7: missing ----
add_table(prs.slides[6], 0, 0, [
    ["Column", "Was missing", "Treatment"],
    ["storage_temp_C", "49 (7.9%)", "Median BY storage_condition (Cold≠Room)"],
    ["quantity_available_kg", "29", "Global median (robust)"],
    ["shelf_life_hours", "18", "Global median"],
    ["beneficiaries_count", "13", "Median → int"],
    ["transport_available", "30", "Mode = Yes"],
    ["After", "0 total", "Verified: isna().sum()==0"],
], fs=12)

# ---- SLIDE 8: encoding ----
add_body(prs.slides[7], [
    "One-Hot (drop_first, int): city, state, donor_type, food_type, storage_condition, foodbank_id, transport_available → 29 dummies.",
    "Why: all nominal (no order); drop_first avoids dummy trap.",
    "Label target only: High→0, Low→1, Medium→2 (saved in cleaning_report.json); use F1-macro, not accuracy.",
    "Dropped from X: donation_id, donation_date (kept month/weekday). Scaling deferred to CE-2 pipeline.",
])

# ---- SLIDE 9: EDA (2x2 images + observations in notes) ----
s9 = prs.slides[8]
imgs = ["01_priority_dist.png", "03_shelf_priority.png", "04_donor_counts.png", "05_distance_need.png"]
pos = [(0.6, 2.1), (5.4, 2.1), (10.1, 2.1), (0.6, 5.2)]
# use 3 across top + 1 wide? fit 4: 2x2
pos = [(0.7, 2.0), (8.0, 2.0), (0.7, 5.0), (8.0, 5.0)]
for (l, t), fn in zip(pos, imgs):
    p = FIG / fn
    if p.exists():
        s9.shapes.add_picture(str(p), Inches(l), Inches(t), Inches(6.8), Inches(2.8))
cap = s9.shapes.add_textbox(Inches(0.7), Inches(7.85), Inches(14.2), Inches(0.6))
cap.text_frame.word_wrap = True
p0 = cap.text_frame.paragraphs[0]
r = p0.add_run()
r.text = "Obs: High = short shelf (~8–12h) + near + high-need; Langar/Restaurant dominate; 73% Medium → stratify + class weights. Full 6 figs in reports/figures/."
r.font.size = Pt(12); r.font.name = "Arial"; r.font.color.rgb = DARK

# ---- SLIDE 10: features ----
add_body(prs.slides[9], [
    "Engineered: stock_pressure, surplus_ratio, need_per_km (=bene/(dist+1)), is_perishable (<24h), cold_chain_ok.",
    "Corr check: no |r|>0.85 — keep all; CE-2 selects via RF importance / mutual-info.",
    "X = 44 cols (15 numeric/eng + 29 dummies) | y = redistribution_priority (0/1/2).",
    "Contract: train_test_split(stratify=y, random_state=42) mandatory. Full X list in cleaning_report.json.",
], size=14)

# ---- SLIDE 11: screenshot (generate head PNG + embed) ----
dfc = pd.read_csv(PROC / "freshroute_foodbank_cleaned.csv")
head = dfc.head(8)[["donation_id", "city", "donor_type", "food_type", "quantity_available_kg",
                     "shelf_life_hours", "distance_to_foodbank_km", "beneficiaries_count",
                     "transport_available", "redistribution_priority"]]
fig, ax = plt.subplots(figsize=(13, 3.2))
ax.axis("off")
tbl = ax.table(cellText=head.values, colLabels=head.columns, loc="center")
tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 1.1)
plt.tight_layout()
shot = PROC / "screenshot_head.png"
plt.savefig(shot, dpi=150, bbox_inches="tight")
plt.close()
s11 = prs.slides[10]
s11.shapes.add_picture(str(shot), Inches(0.5), Inches(2.0), Inches(14.6), Inches(3.6))
cap2 = s11.shapes.add_textbox(Inches(0.5), Inches(5.9), Inches(14.6), Inches(1.2))
cap2.text_frame.word_wrap = True
p0 = cap2.text_frame.paragraphs[0]
r = p0.add_run()
r.text = f"Cleaned 618×25, missing=0  •  Encoded 618×45  •  y: Medium 456 / High 122 / Low 40  •  Reproduce: python scripts/generate_dataset.py → python scripts/clean_dataset.py"
r.font.size = Pt(13); r.font.name = "Arial"; r.font.color.rgb = DARK

# ---- SLIDE 12: conclusion ----
add_body(prs.slides[11], [
    "CE-1 done: messy 636×20 → clean 618×25 → encoded 618×45, frozen X/y, 6 EDA figs, scripts + Colab notebook.",
    "Finding: priority driven by perishability × need-per-km, not quantity alone.",
    "Biases logged: imbalance + langar dominance + winter-only dates → mitigations in CE-2.",
])

# ---- SLIDE 13: future ----
add_body(prs.slides[12], [
    "CE-2 models: Logistic / RandomForest / XGBoost on F1-macro; stratified split; class weights/SMOTE; per-donor audit + SHAP.",
    "Routing layer: priority + need_per_km + stock_pressure → ranked food-bank / dept / shelter + volunteer dispatch.",
    "App + pilot logs (FSSAI/state data), summer data, cold-chain IoT later.",
])

# ---- SLIDE 14: thank you ----
s14 = prs.slides[13]
t14 = None
for shp in s14.shapes:
    if shp.has_text_frame and shp.name.startswith("Google Shape;266"):
        t14 = shp
if t14:
    set_text(t14, "Thank You — Viva Ready (10 min)", size=32, bold=True, font="Calibri")
    # add subtitle box
    bx = s14.shapes.add_textbox(Inches(2.5), Inches(4.2), Inches(10.6), Inches(2.2))
    bx.text_frame.word_wrap = True
    p0 = bx.text_frame.paragraphs[0]; p0.alignment = PP_ALIGN.CENTER
    r = p0.add_run()
    r.text = "FreshRoute CE-1 • 618-row ML-ready dataset • 6 EDA observations • Live demo: raw → cleaned → encoded"
    r.font.size = Pt(16); r.font.name = "Arial"; r.font.color.rgb = DARK

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print(f"Saved -> {OUT}")
