"""
NEW-1: Fed Path Repricing Analysis
===================================
Quantifies how the market has repriced the Fed path since the oil shock.

Original design required Wirp_02_27 and Wirp_03_18 sheets (WIRP implied rates),
but these sheets are NOT available in the data file.

ADAPTED APPROACH:
  - Uses Fed Funds Rate + UST 2 y spread to infer implied easing
  - Computes the 2Y-FFR spread pre-war vs current to quantify how many
    cuts have been priced out
  - Uses A7 passthrough estimates to argue whether repricing is justified

Uses: Fed Funds Rate, UST 2 y, CL1 from data_steepener.xlsx

Output: Console repricing table + ../output/new1_fed_path_repricing.txt
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"


def load_bloomberg_sheet(sheet, date_col=1, val_col=2):
    """Load Bloomberg-format sheet."""
    df = pd.read_excel(DATA_FILE, sheet_name=sheet, header=None)
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    data = df.iloc[header_row + 1:, [date_col, val_col]].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    return data.dropna().set_index("Date").sort_index()["Value"]


def get_nearest(series, date_str):
    target = pd.Timestamp(date_str)
    idx = series.index.searchsorted(target)
    if idx >= len(series):
        idx = len(series) - 1
    if idx > 0 and abs(series.index[idx] - target) > abs(series.index[idx-1] - target):
        idx = idx - 1
    return series.iloc[idx], series.index[idx]


# ─── LOAD DATA ───
print("Loading data...")
ffr = load_bloomberg_sheet("Fed Funds Rate")
ust2y = load_bloomberg_sheet("UST 2 y")
ust10y = load_bloomberg_sheet("UST 10 y")
oil = load_bloomberg_sheet("CL1")

# ─── KEY DATES ───
PRE_WAR = "2026-02-27"
CURRENT = "2026-03-16"
PRE_OIL = "2026-02-01"   # before any oil shock effects
YE_2025 = "2025-12-31"   # year-end reference

print("\n" + "=" * 70)
print("NEW-1: FED PATH REPRICING ANALYSIS")
print("=" * 70)

# ─── FED FUNDS vs 2Y SPREAD (implied easing proxy) ───
# The 2Y-FFR spread approximates how many cuts the market expects over 2 years
# More negative = more cuts priced in

ffr_pre, ffr_pre_dt = get_nearest(ffr, PRE_WAR)
ffr_cur, ffr_cur_dt = get_nearest(ffr, CURRENT)
ust2y_pre, ust2y_pre_dt = get_nearest(ust2y, PRE_WAR)
ust2y_cur, ust2y_cur_dt = get_nearest(ust2y, CURRENT)
ust2y_feb1, ust2y_feb1_dt = get_nearest(ust2y, PRE_OIL)

oil_pre, oil_pre_dt = get_nearest(oil, PRE_WAR)
oil_cur, oil_cur_dt = get_nearest(oil, CURRENT)

# 2Y-FFR spread as easing proxy
spread_pre = (ust2y_pre - ffr_pre) * 100  # in bp
spread_cur = (ust2y_cur - ffr_cur) * 100
spread_feb1 = (ust2y_feb1 - get_nearest(ffr, PRE_OIL)[0]) * 100

# Each 25bp cut = 25bp, so implied cuts = spread / 25 (roughly)
# More negative spread = more cuts priced
implied_cuts_pre = -spread_pre / 25
implied_cuts_cur = -spread_cur / 25
implied_cuts_feb1 = -spread_feb1 / 25

d_spread = spread_cur - spread_pre  # positive = hawkish repricing (fewer cuts)
d_cuts = implied_cuts_cur - implied_cuts_pre  # negative = cuts removed

print(f"\n  DATA NOTE: WIRP sheets not available. Using 2Y-FFR spread as easing proxy.")
print(f"  (2Y yield embeds market's expected average Fed Funds rate over 2 years)")

print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
print(f"  │  FED FUNDS RATE & 2Y YIELD                                    │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
print(f"  │  Fed Funds Rate:  {ffr_pre:.2f}% ({ffr_pre_dt.date()}) → {ffr_cur:.2f}% ({ffr_cur_dt.date()})  │")
print(f"  │  2Y Yield:        {ust2y_pre:.3f}% → {ust2y_cur:.3f}% = {(ust2y_cur-ust2y_pre)*100:+.1f}bp      │")
print(f"  │  WTI Oil:         ${oil_pre:.2f} → ${oil_cur:.2f} = {(oil_cur/oil_pre-1)*100:+.1f}%          │")
print(f"  └──────────────────────────────────────────────────────────────┘")

print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
print(f"  │  IMPLIED EASING PROXY (2Y - FFR spread)                       │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
print(f"  │  Date          2Y-FFR(bp)  Implied Cuts(25bp ea.)            │")
print(f"  │  Feb 1:        {spread_feb1:+.0f}bp       ~{implied_cuts_feb1:.1f} cuts                  │")
print(f"  │  Feb 27 (pre): {spread_pre:+.0f}bp       ~{implied_cuts_pre:.1f} cuts                  │")
print(f"  │  Mar 16 (cur): {spread_cur:+.0f}bp       ~{implied_cuts_cur:.1f} cuts                  │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
print(f"  │  Change (Feb 27→Mar 16): {d_spread:+.0f}bp = {d_cuts:+.1f} cuts repriced     │")
print(f"  └──────────────────────────────────────────────────────────────┘")

# ─── REPRICING TIMELINE ───
print(f"\n  REPRICING TIMELINE (2Y yield path):")
key_dates = [
    ("2026-02-01", "Feb 1 (pre-shock)"),
    ("2026-02-14", "Feb 14 (Valentine's)"),
    ("2026-02-27", "Feb 27 (pre-war)"),
    ("2026-03-03", "Mar 3 (week 1)"),
    ("2026-03-07", "Mar 7 (week 2)"),
    ("2026-03-10", "Mar 10"),
    ("2026-03-14", "Mar 14"),
    ("2026-03-16", "Mar 16 (latest)"),
]

print(f"  {'Date':<25} {'2Y Yield':>10} {'d(2Y) bp':>10} {'Oil':>10} {'d(Oil) %':>10}")
print(f"  {'-'*65}")
for date_str, label in key_dates:
    y_val, y_dt = get_nearest(ust2y, date_str)
    o_val, o_dt = get_nearest(oil, date_str)
    d_y = (y_val - ust2y_pre) * 100
    d_o = (o_val / oil_pre - 1) * 100
    print(f"  {label:<25} {y_val:>10.3f}% {d_y:>+10.1f} ${o_val:>9.2f} {d_o:>+10.1f}%")

# ─── JUSTIFICATION CHECK ───
# A7 found: headline CPI +62bp per 10% oil increase, core PCE only +22bp
# Oil has moved X% since Feb 27 — what does that imply?
oil_change_pct = (oil_cur / oil_pre - 1) * 100
implied_headline_cpi = oil_change_pct / 10 * 62  # bp of headline CPI
implied_core_pce = oil_change_pct / 10 * 22     # bp of core PCE
implied_ffr_from_headline = implied_headline_cpi / 100 * 0.5  # Taylor rule: 0.5 * inflation gap
implied_ffr_from_core = implied_core_pce / 100 * 0.5

print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
print(f"  │  IS THE REPRICING JUSTIFIED? (Using A7 Passthrough)           │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
print(f"  │  Oil change since Feb 27: {oil_change_pct:+.1f}%                          │")
print(f"  │  A7 passthrough estimates:                                    │")
print(f"  │    Headline CPI impact:  {implied_headline_cpi:+.0f}bp                              │")
print(f"  │    Core PCE impact:      {implied_core_pce:+.0f}bp                              │")
print(f"  │  Implied FFR adjustment (Taylor rule, 0.5 coef):              │")
print(f"  │    If Fed reacts to headline: {implied_ffr_from_headline:+.1f}bp                     │")
print(f"  │    If Fed reacts to core:     {implied_ffr_from_core:+.1f}bp                     │")
print(f"  │  Actual 2Y repricing:         {(ust2y_cur-ust2y_pre)*100:+.1f}bp                     │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
actual_2y_move = (ust2y_cur - ust2y_pre) * 100
if abs(actual_2y_move) > abs(implied_ffr_from_headline):
    overreaction = actual_2y_move - implied_ffr_from_headline
    print(f"  │  VERDICT: Market overreacted by ~{overreaction:+.0f}bp vs headline,          │")
    print(f"  │  and ~{actual_2y_move - implied_ffr_from_core:+.0f}bp vs core.                                  │")
    print(f"  │  Fed reacts to CORE, not headline (A7/A8 confirmed).       │")
    print(f"  │  → Front-end repricing is EXCESSIVE.                       │")
else:
    print(f"  │  VERDICT: Market repricing is roughly in line with          │")
    print(f"  │  fundamental passthrough estimates.                         │")
print(f"  └──────────────────────────────────────────────────────────────┘")

# ─── WRITE RESULTS ───
results_path = "../output/new1_fed_path_repricing.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-1: Fed Path Repricing Analysis\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Note: WIRP sheets not available. Using 2Y-FFR spread as easing proxy.\n\n")
    f.write(f"Period: {ust2y_pre_dt.date()} to {ust2y_cur_dt.date()}\n\n")
    f.write(f"Fed Funds Rate: {ffr_pre:.2f}% → {ffr_cur:.2f}%\n")
    f.write(f"2Y Yield: {ust2y_pre:.3f}% → {ust2y_cur:.3f}% ({(ust2y_cur-ust2y_pre)*100:+.1f}bp)\n")
    f.write(f"Oil (WTI): ${oil_pre:.2f} → ${oil_cur:.2f} ({oil_change_pct:+.1f}%)\n\n")
    f.write(f"2Y-FFR spread (easing proxy):\n")
    f.write(f"  Pre-war:  {spread_pre:+.0f}bp (~{implied_cuts_pre:.1f} cuts)\n")
    f.write(f"  Current:  {spread_cur:+.0f}bp (~{implied_cuts_cur:.1f} cuts)\n")
    f.write(f"  Change:   {d_spread:+.0f}bp = {d_cuts:+.1f} cuts repriced\n\n")
    f.write(f"A7 passthrough vs actual repricing:\n")
    f.write(f"  Oil change: {oil_change_pct:+.1f}%\n")
    f.write(f"  Headline CPI impact: {implied_headline_cpi:+.0f}bp\n")
    f.write(f"  Core PCE impact: {implied_core_pce:+.0f}bp\n")
    f.write(f"  Implied FFR adjustment (headline): {implied_ffr_from_headline:+.1f}bp\n")
    f.write(f"  Implied FFR adjustment (core): {implied_ffr_from_core:+.1f}bp\n")
    f.write(f"  Actual 2Y repricing: {actual_2y_move:+.1f}bp\n")
    f.write(f"  Overreaction vs core: {actual_2y_move - implied_ffr_from_core:+.1f}bp\n")

print(f"\nResults written to {results_path}")
