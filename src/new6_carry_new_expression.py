"""
NEW-6: Carry & Scenario P&L for New Expression
================================================
Builds carry and scenario P&L analysis for the recommended steepener trade.

Original design required SOFR Strips sheet, which is NOT available.

ADAPTED APPROACH:
  - Uses Fed Funds Rate as overnight financing proxy
  - Uses UST 2 y and UST 10 y for yield levels
  - Computes carry on steepener = (10Y yield - 2Y yield) rolldown + financing
  - Scenario P&L matrix across spread outcomes x holding periods

Expression: Long front-end (benefit from 2Y rally) + short back-end (or neutral)
            Target: SOFR futures SFRZ6/SFRH7 + Micro 10Y short

Uses: UST 2 y, UST 10 y, US 2yr10yr spread, Fed Funds Rate

Output: Console carry table + scenario P&L matrix
        ../output/new6_carry_results.txt
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
ust2y = load_bloomberg_sheet("UST 2 y")
ust10y = load_bloomberg_sheet("UST 10 y")
spread = load_bloomberg_sheet("US 2yr10yr spread")
ffr = load_bloomberg_sheet("Fed Funds Rate")

CURRENT = "2026-03-16"

y2_cur, _ = get_nearest(ust2y, CURRENT)
y10_cur, _ = get_nearest(ust10y, CURRENT)
spread_cur, spread_dt = get_nearest(spread, CURRENT)
ffr_cur, _ = get_nearest(ffr, CURRENT)

# Normalize spread to bp
if abs(spread_cur) < 10:
    spread_bp = spread_cur * 100
else:
    spread_bp = spread_cur

print("\n" + "=" * 70)
print("NEW-6: CARRY & SCENARIO P&L — NEW EXPRESSION")
print("=" * 70)

print(f"\n  DATA NOTE: SOFR Strips sheet not available.")
print(f"  Using Fed Funds Rate as financing proxy for carry calculations.")

# ─── CURRENT LEVELS ───
print(f"\n  ┌──────────────────────────────────────────────┐")
print(f"  │  CURRENT MARKET LEVELS ({spread_dt.date()})     │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  2Y Yield:         {y2_cur:.3f}%                │")
print(f"  │  10Y Yield:        {y10_cur:.3f}%                │")
print(f"  │  2s10s Spread:     {spread_bp:.0f}bp                  │")
print(f"  │  Fed Funds Rate:   {ffr_cur:.2f}%                │")
print(f"  │  2Y-FFR Carry:     {(y2_cur - ffr_cur)*100:+.0f}bp               │")
print(f"  └──────────────────────────────────────────────┘")

# ─── TRADE EXPRESSION ───
print(f"\n  TRADE EXPRESSION:")
print(f"    Recommended: SOFR futures (SFRZ6/SFRH7) + Micro 10Y short")
print(f"    Proxy for analysis: Long 2Y / Short 10Y steepener")
print(f"    Entry: {spread_bp:.0f}bp  |  Target: 70bp  |  Stop: 42bp")
print(f"    Notional: $100,000 per contract (Micro 10Y = $10/bp)")

# ─── DV01 CALCULATIONS ───
# Approximate DV01 for $100k notional
dv01_2y = 100000 * 2.0 / 10000  # ~$20 per bp for 2Y
dv01_10y = 100000 * 8.5 / 10000  # ~$85 per bp for 10Y (Micro 10Y)
# DV01-neutral ratio
ratio = dv01_10y / dv01_2y

print(f"\n  DV01 PROFILE (per $100k notional):")
print(f"    2Y DV01:  ~${dv01_2y:.0f}/bp (duration ~2.0)")
print(f"    10Y DV01: ~${dv01_10y:.0f}/bp (duration ~8.5, Micro 10Y)")
print(f"    DV01-neutral ratio: {ratio:.1f}:1 (2Y:10Y notional)")

# ─── CARRY ANALYSIS ───
# Steepener carry = (positive carry from curve slope) - (financing cost of position)
# For a DV01-neutral steepener:
#   Long 2Y: earn 2Y yield, finance at FFR => carry = (2Y - FFR) * DV01_2y
#   Short 10Y: pay 10Y yield, receive FFR => carry = (FFR - 10Y) * DV01_10y
# Net carry per day = sum / 360

long_2y_carry_annual = (y2_cur - ffr_cur) / 100 * 100000 * (dv01_2y / 100000 * 10000)  # simplified
short_10y_carry_annual = (ffr_cur - y10_cur) / 100 * 100000 * (dv01_10y / 100000 * 10000)

# Simpler: carry in bp/month for DV01-neutral steepener
# Positive carry if 2Y-FFR > FFR-10Y (i.e., if 2Y + 10Y > 2*FFR)
net_carry_bp_annual = (y2_cur - ffr_cur) - (y10_cur - ffr_cur) * (dv01_10y / dv01_2y)
# Actually simpler: for a DV01-neutral steepener, carry = slope of curve * rolldown
# The key cost is: you're short the higher-yielding part of the curve

# Monthly carry in spread bp terms
# Steepener carry ≈ -(10Y - 2Y) * rolldown_factor ≈ slightly negative (you pay the curve)
monthly_carry_bp = -(y10_cur - y2_cur) / 12 * 100  # rough: slope cost per month

print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  CARRY ANALYSIS (approximate)                              │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Curve slope (10Y-2Y): {(y10_cur-y2_cur)*100:+.0f}bp                          │")
print(f"  │  Monthly carry cost:   ~{monthly_carry_bp:.1f}bp/month                    │")
print(f"  │  3-month carry cost:   ~{monthly_carry_bp*3:.1f}bp                          │")
print(f"  │  6-month carry cost:   ~{monthly_carry_bp*6:.1f}bp                          │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Breakeven: spread must widen {abs(monthly_carry_bp*3):.0f}bp in 3M to break even │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── SCENARIO P&L MATRIX ───
print(f"\n  SCENARIO P&L MATRIX")
print(f"  (P&L in bp of spread move, net of carry)")
print(f"  Entry spread: {spread_bp:.0f}bp")

target_spreads = [42, 46, 50, 54, 60, 65, 70, 80]
holding_months = [1, 2, 3, 6]

print(f"\n  {'Spread →':>12}", end="")
for s in target_spreads:
    print(f" {s:>6}bp", end="")
print()
print(f"  {'Holding ↓':>12}", end="")
for s in target_spreads:
    label = "STOP" if s == 42 else ("TGT" if s == 70 else "")
    print(f" {label:>7}", end="")
print()
print(f"  {'-' * (12 + 8 * len(target_spreads))}")

for months in holding_months:
    carry_cost = monthly_carry_bp * months
    print(f"  {months:>2}M carry={carry_cost:+.0f}", end="")
    for s in target_spreads:
        pnl = (s - spread_bp) + carry_cost
        print(f" {pnl:>+7.0f}", end="")
    print()

# ─── RISK/REWARD SUMMARY ───
target_pnl = (70 - spread_bp) + monthly_carry_bp * 3  # 3M holding, target
stop_pnl = (42 - spread_bp) + monthly_carry_bp * 1    # assume stopped out in 1M
rr_ratio = abs(target_pnl / stop_pnl) if stop_pnl != 0 else float("inf")

print(f"\n  ┌──────────────────────────────────────────────┐")
print(f"  │  RISK/REWARD SUMMARY (3M holding period)      │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  Target P&L (70bp, 3M): {target_pnl:+.0f}bp             │")
print(f"  │  Stop P&L (42bp, 1M):   {stop_pnl:+.0f}bp             │")
print(f"  │  Risk/Reward ratio:      {rr_ratio:.1f}:1              │")
print(f"  └──────────────────────────────────────────────┘")

# ─── WRITE RESULTS ───
results_path = "../output/new6_carry_results.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-6: Carry & Scenario P&L — New Expression\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Note: SOFR Strips not available. Using FFR as financing proxy.\n\n")
    f.write(f"Current levels ({spread_dt.date()}):\n")
    f.write(f"  2Y: {y2_cur:.3f}%  10Y: {y10_cur:.3f}%  Spread: {spread_bp:.0f}bp  FFR: {ffr_cur:.2f}%\n\n")
    f.write(f"Entry: {spread_bp:.0f}bp  Target: 70bp  Stop: 42bp\n")
    f.write(f"Monthly carry cost: ~{monthly_carry_bp:.1f}bp\n")
    f.write(f"3M carry cost: ~{monthly_carry_bp*3:.1f}bp\n\n")
    f.write(f"Target P&L (70bp, 3M): {target_pnl:+.0f}bp\n")
    f.write(f"Stop P&L (42bp, 1M): {stop_pnl:+.0f}bp\n")
    f.write(f"Risk/Reward: {rr_ratio:.1f}:1\n")

print(f"\nResults written to {results_path}")
