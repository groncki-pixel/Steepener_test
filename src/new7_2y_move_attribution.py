"""
NEW-7: 2Y Move Attribution & Target Calibration
================================================
PRIORITY: CRITICAL — Run first, determines trade target.

Decomposes the +34bp 2Y nominal move (Feb 27 → Mar 16) into:
  Component A: Breakeven inflation change (oil-driven, war-reversible)
  Component B: Real yield change (Fed path repricing, less reversible)
  Component C: Technical correction from pre-war oversold levels

Uses: USGGT02y (2Y TIPS real yield), US 2 year breakeven, UST 2 y, USGG2YR

Output: Console decomposition table + target calibration matrix
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"

# ─── DATA LOADING ───

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

def load_tips_sheet():
    """Load USGGT02y which has date in col 0, value in col 1."""
    df = pd.read_excel(DATA_FILE, sheet_name="USGGT02y", header=None)
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    data = df.iloc[header_row + 1:, :2].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    return data.dropna().set_index("Date").sort_index()["Value"]

# ─── LOAD DATA ───
print("Loading data...")
ust2y_nom = load_bloomberg_sheet("UST 2 y")
be2y = load_bloomberg_sheet("US 2 year breakeven")
tips_2y = load_tips_sheet()
usgg2yr = load_bloomberg_sheet("USGG2YR", date_col=0, val_col=1)  # long history, date in col 0

# ─── KEY DATES ───
PRE_WAR = "2026-02-27"
CURRENT = "2026-03-16"  # latest common date across all series
MID_FEB = "2026-02-13"  # mid-Feb level before the pre-war rally

# ─── DECOMPOSITION ───
print("\n" + "=" * 70)
print("NEW-7: 2Y YIELD MOVE ATTRIBUTION (Feb 27 → Mar 16)")
print("=" * 70)

# Get values on key dates (find nearest available)
def get_nearest(series, date_str):
    target = pd.Timestamp(date_str)
    idx = series.index.searchsorted(target)
    if idx >= len(series):
        idx = len(series) - 1
    # Check if exact or nearest
    if idx > 0 and abs(series.index[idx] - target) > abs(series.index[idx-1] - target):
        idx = idx - 1
    return series.iloc[idx], series.index[idx]

nom_pre, nom_pre_dt = get_nearest(ust2y_nom, PRE_WAR)
nom_cur, nom_cur_dt = get_nearest(ust2y_nom, CURRENT)
be_pre, be_pre_dt = get_nearest(be2y, PRE_WAR)
be_cur, be_cur_dt = get_nearest(be2y, CURRENT)
tips_pre, tips_pre_dt = get_nearest(tips_2y, PRE_WAR)
tips_cur, tips_cur_dt = get_nearest(tips_2y, CURRENT)

# Mid-Feb reference for technical correction estimate
nom_mid, nom_mid_dt = get_nearest(ust2y_nom, MID_FEB)

print(f"\n  Dates used:")
print(f"    Pre-war:  {nom_pre_dt.date()} (nominal), {be_pre_dt.date()} (BE), {tips_pre_dt.date()} (TIPS)")
print(f"    Current:  {nom_cur_dt.date()} (nominal), {be_cur_dt.date()} (BE), {tips_cur_dt.date()} (TIPS)")
print(f"    Mid-Feb:  {nom_mid_dt.date()} (nominal)")

# The decomposition
d_nominal = (nom_cur - nom_pre) * 100  # convert to bp
d_breakeven = (be_cur - be_pre) * 100
d_real = (tips_cur - tips_pre) * 100

print(f"\n  ┌──────────────────────────────────────────────┐")
print(f"  │  2Y MOVE DECOMPOSITION                        │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  2Y Nominal:    {nom_pre:.3f}% → {nom_cur:.3f}% = {d_nominal:+.1f}bp │")
print(f"  │  2Y Breakeven:  {be_pre:.3f}% → {be_cur:.3f}% = {d_breakeven:+.1f}bp │")
print(f"  │  2Y Real (TIPS): {tips_pre:.3f}% → {tips_cur:.3f}% = {d_real:+.1f}bp │")
print(f"  └──────────────────────────────────────────────┘")

print(f"\n  SANITY CHECK: Nominal ≈ Breakeven + Real")
print(f"    {d_nominal:+.1f}bp ≈ {d_breakeven:+.1f}bp + {d_real:+.1f}bp = {d_breakeven + d_real:+.1f}bp")
residual = d_nominal - (d_breakeven + d_real)
print(f"    Residual: {residual:+.1f}bp {'(TIPS liquidity/measurement noise)' if abs(residual) < 10 else '(WARNING: large residual)'}")

# Technical correction estimate
d_tech = (nom_pre - nom_mid) * 100  # how much the 2Y fell from mid-Feb to pre-war
print(f"\n  TECHNICAL CORRECTION ESTIMATE:")
print(f"    Mid-Feb level: {nom_mid:.3f}% ({nom_mid_dt.date()})")
print(f"    Pre-war level: {nom_pre:.3f}% ({nom_pre_dt.date()})")
print(f"    Pre-war rally: {d_tech:+.1f}bp (this was the overshoot that corrected)")

# ─── ATTRIBUTION TABLE ───
print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  ATTRIBUTION                                          │")
print(f"  ├──────────────────────────────────────────────────────┤")
print(f"  │  Breakeven (oil/inflation): {d_breakeven:+.1f}bp               │")
print(f"  │    → Reverses if war resolves & oil normalizes        │")
print(f"  │  Real yield change:         {d_real:+.1f}bp               │")
print(f"  │    → Reverses if Fed cuts / Warsh confirmed           │")
print(f"  │  Technical correction:      ~{-d_tech:+.1f}bp (est.)         │")
print(f"  │    → Already happened, NOT coming back                │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── TARGET CALIBRATION ───
print(f"\n  TARGET CALIBRATION:")
print(f"  If ONLY war resolves → 2Y falls ~{abs(d_breakeven):.0f}bp → spread widens ~{abs(d_breakeven):.0f}bp")
print(f"  If war + Warsh cuts → 2Y falls ~{abs(d_breakeven) + max(0, -d_real):.0f}bp → spread widens more")
print(f"  If war + Warsh + labor weakness → full unwind potential")

war_only_spread = 54 + abs(d_breakeven)  # current spread ~54bp + front-end unwind
warsh_spread = 54 + abs(d_breakeven) + max(0, -d_real)
print(f"\n  Spread targets:")
print(f"    War-only scenario:    ~{war_only_spread:.0f}bp")
print(f"    War + Warsh scenario: ~{warsh_spread:.0f}bp")
print(f"    Current 70bp target requires: {70 - 54:.0f}bp of steepening")
print(f"    Oil-reversible component provides: ~{abs(d_breakeven):.0f}bp")
print(f"    Gap to fill from other catalysts: ~{max(0, 16 - abs(d_breakeven)):.0f}bp")

# ─── DECISION GATE ───
oil_reversible = abs(d_breakeven)
print(f"\n  ═══ DECISION GATE ═══")
print(f"  Oil-reversible component: {oil_reversible:.1f}bp")
if oil_reversible > 8:
    print(f"  ✓ PASSES (>{8}bp threshold) — war unwind alone provides meaningful P&L")
else:
    print(f"  ✗ FAILS (<{8}bp threshold) — war unwind alone is insufficient")
    print(f"    → Need Warsh + labor catalysts for target. Consider reducing target or widening stop.")

# ─── WRITE RESULTS ───
results_path = "../output/new7_2y_move_attribution.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-7: 2Y Move Attribution & Target Calibration\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Period: {nom_pre_dt.date()} to {nom_cur_dt.date()}\n\n")
    f.write(f"2Y Nominal change:    {d_nominal:+.1f}bp\n")
    f.write(f"2Y Breakeven change:  {d_breakeven:+.1f}bp (oil-reversible)\n")
    f.write(f"2Y Real yield change: {d_real:+.1f}bp (Fed path / structural)\n")
    f.write(f"Technical correction: ~{-d_tech:+.1f}bp (pre-war overshoot, already reversed)\n\n")
    f.write(f"Oil-reversible component: {oil_reversible:.1f}bp\n")
    f.write(f"Decision gate (>8bp): {'PASS' if oil_reversible > 8 else 'FAIL'}\n")

print(f"\nResults written to {results_path}")
