"""
NEW-3: Warsh Scenario Tree
===========================
Probability-weighted scenario analysis for Warsh confirmation timing.
Three scenarios with spread outcome ranges, sensitivity grid, and tornado chart.

Uses: US 2yr10yr spread (current level), A2 beta(TP) = +32.85, NEW-7 results.

Output: Console scenario tree + sensitivity grid
        ../output/new3_warsh_scenario.txt
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


# ─── LOAD CURRENT SPREAD ───
print("Loading data...")
spread = load_bloomberg_sheet("US 2yr10yr spread")
spread_cur, spread_dt = get_nearest(spread, "2026-03-16")
if abs(spread_cur) < 10:
    S0 = spread_cur * 100  # convert to bp
else:
    S0 = spread_cur

# ─── PARAMETERS FROM PRIOR ANALYSES ───
# A2: beta(TP) = +32.8482 (from legacy analysis — d(spread) = b0 + b1*d(RE) + b2*d(TP))
# This means: 1pp increase in TP → ~33bp spread widening
BETA_TP = 32.85  # bp of spread per 1pp of TP change

# NEW-7: Breakeven component = +33.9bp (oil-reversible)
# If war resolves, 2Y falls ~34bp → spread widens ~34bp
BE_COMPONENT = 33.9  # bp, from NEW-7

# Trade params
ENTRY = S0
TARGET = 70
STOP = 42

print("\n" + "=" * 70)
print("NEW-3: WARSH SCENARIO TREE & SENSITIVITY ANALYSIS")
print("=" * 70)

print(f"\n  Input parameters:")
print(f"    Current spread:    {S0:.0f}bp (as of {spread_dt.date()})")
print(f"    A2 beta(TP):       {BETA_TP:.2f} (bp spread per 1pp TP change)")
print(f"    NEW-7 BE component: {BE_COMPONENT:.1f}bp (oil-reversible)")
print(f"    Entry: {ENTRY:.0f}bp  Target: {TARGET}bp  Stop: {STOP}bp")

# ─── THREE SCENARIOS ───
scenarios = [
    {
        "name": "Bull: Warsh confirmed by May + war resolution",
        "prob": 0.30,
        "d_tp_pp": 0.20,       # +20bp TP increase from QT acceleration
        "d_2y_bp": -BE_COMPONENT,  # full BE unwind from war resolution
        "d_10y_bp": 5,          # 10Y slightly higher on TP, offset by flight-to-quality unwind
        "rationale": "Warsh accelerates QT → TP rises. War resolves → 2Y BE unwinds."
    },
    {
        "name": "Base: Warsh delayed, partial oil normalization",
        "prob": 0.45,
        "d_tp_pp": 0.10,       # +10bp TP increase (delayed QT signal)
        "d_2y_bp": -BE_COMPONENT * 0.5,  # partial BE unwind
        "d_10y_bp": 0,
        "rationale": "Warsh delayed to summer. Oil partially normalizes. Gradual repricing."
    },
    {
        "name": "Bear: Warsh blocked, oil stays elevated",
        "prob": 0.25,
        "d_tp_pp": -0.05,      # TP flat to slightly lower (no QT signal)
        "d_2y_bp": BE_COMPONENT * 0.2,  # additional 2Y selloff as oil persists
        "d_10y_bp": -5,         # flight to quality in 10Y
        "rationale": "Warsh blocked. Oil stays high. Stagflation fears → curve flattens."
    },
]

print(f"\n  ┌─────────────────────────────────────────────────────────────────┐")
print(f"  │  SCENARIO TREE                                                   │")
print(f"  ├─────────────────────────────────────────────────────────────────┤")

ev_spread = 0
ev_pnl = 0

for sc in scenarios:
    # Spread outcome = current + TP effect + 2Y effect (via spread)
    # TP effect on spread: beta_TP * d_TP (already in bp per pp)
    tp_effect = BETA_TP * sc["d_tp_pp"]
    # 2Y move affects spread: 2Y falls → spread widens (1:1 if 10Y unchanged)
    front_end_effect = -sc["d_2y_bp"]  # negative 2Y move = positive spread
    back_end_effect = sc["d_10y_bp"]  # higher 10Y = wider spread

    spread_outcome = S0 + tp_effect + front_end_effect + back_end_effect
    pnl = spread_outcome - ENTRY

    ev_spread += sc["prob"] * spread_outcome
    ev_pnl += sc["prob"] * pnl

    print(f"  │                                                                 │")
    print(f"  │  {sc['name']:<60}   │")
    print(f"  │  Probability: {sc['prob']*100:.0f}%                                              │")
    print(f"  │  TP effect:        {tp_effect:+.1f}bp (beta*d_TP={BETA_TP:.0f}*{sc['d_tp_pp']:+.2f})       │")
    print(f"  │  Front-end effect: {front_end_effect:+.1f}bp (2Y move: {sc['d_2y_bp']:+.1f}bp)          │")
    print(f"  │  Back-end effect:  {back_end_effect:+.1f}bp (10Y move)                          │")
    print(f"  │  Spread outcome:   {spread_outcome:.0f}bp (P&L: {pnl:+.0f}bp)                         │")
    print(f"  │  {sc['rationale']:<60}   │")

print(f"  │                                                                 │")
print(f"  ├─────────────────────────────────────────────────────────────────┤")
print(f"  │  PROBABILITY-WEIGHTED EXPECTED VALUE                             │")
print(f"  │  Expected spread:  {ev_spread:.0f}bp                                        │")
print(f"  │  Expected P&L:     {ev_pnl:+.0f}bp                                        │")
print(f"  │  vs Target (70bp): {ev_spread - TARGET:+.0f}bp                                     │")
print(f"  │  vs Stop (42bp):   {ev_spread - STOP:+.0f}bp cushion                              │")
print(f"  └─────────────────────────────────────────────────────────────────┘")

# ─── SENSITIVITY GRID ───
print(f"\n  2D SENSITIVITY GRID: Expected Spread")
print(f"  Rows = Bull scenario probability, Cols = Oil-reversible component (bp)")

bull_probs = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
oil_components = [10, 15, 20, 25, 30, 34, 40]

print(f"\n  {'Bull prob →':>12}", end="")
for oc in oil_components:
    print(f" {oc:>5}bp", end="")
print()
print(f"  {'-' * (12 + 7 * len(oil_components))}")

for bp in bull_probs:
    print(f"  {bp*100:>5.0f}%      ", end="")
    # Recompute scenarios with varying bull prob and oil component
    base_prob = min(0.60, 1.0 - bp - 0.15)  # keep bear at min 15%
    bear_prob = 1.0 - bp - base_prob
    for oc in oil_components:
        # Bull: full unwind of oil component
        bull_spread = S0 + BETA_TP * 0.20 + oc + 5
        # Base: half unwind
        base_spread = S0 + BETA_TP * 0.10 + oc * 0.5
        # Bear: no unwind + some additional pressure
        bear_spread = S0 + BETA_TP * (-0.05) - oc * 0.2 - 5
        ev = bp * bull_spread + base_prob * base_spread + bear_prob * bear_spread
        marker = " *" if abs(ev - 70) < 3 else "  "
        print(f" {ev:>5.0f}{marker}", end="")
    print()

print(f"\n  * = within 3bp of 70bp target")

# ─── TORNADO CHART (text-based) ───
print(f"\n  TORNADO SENSITIVITY (impact on expected spread of ±1 unit change)")

# Baseline expected spread
baseline = ev_spread

# Vary each input
sensitivities = []

# 1. Bull probability ±10pp
for label, delta_bull, delta_base, delta_bear in [
    ("Bull prob +10pp", +0.10, -0.05, -0.05),
    ("Bull prob -10pp", -0.10, +0.05, +0.05),
]:
    probs = [scenarios[i]["prob"] + [delta_bull, delta_base, delta_bear][i] for i in range(3)]
    ev_alt = sum(p * (S0 + BETA_TP * sc["d_tp_pp"] + (-sc["d_2y_bp"]) + sc["d_10y_bp"])
                 for p, sc in zip(probs, scenarios))
    sensitivities.append((label, ev_alt - baseline))

# 2. Oil-reversible component ±10bp
for label, delta in [("Oil comp +10bp", +10), ("Oil comp -10bp", -10)]:
    ev_alt = baseline + delta * (scenarios[0]["prob"] + scenarios[1]["prob"] * 0.5 - scenarios[2]["prob"] * 0.2)
    sensitivities.append((label, ev_alt - baseline))

# 3. Beta TP ±5
for label, delta in [("Beta(TP) +5", +5), ("Beta(TP) -5", -5)]:
    ev_alt = baseline + delta * sum(sc["prob"] * sc["d_tp_pp"] for sc in scenarios)
    sensitivities.append((label, ev_alt - baseline))

print(f"\n  {'Input Change':<25} {'Impact on EV':>15}")
print(f"  {'-'*40}")
# Sort by absolute impact
sensitivities.sort(key=lambda x: abs(x[1]), reverse=True)
for label, impact in sensitivities:
    bar_len = int(abs(impact) / 2)
    bar = "█" * bar_len
    direction = "+" if impact > 0 else "-"
    print(f"  {label:<25} {impact:>+8.1f}bp  {direction}{bar}")

# ─── WRITE RESULTS ───
results_path = "../output/new3_warsh_scenario.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-3: Warsh Scenario Tree & Sensitivity Analysis\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Current spread: {S0:.0f}bp\n")
    f.write(f"Beta(TP): {BETA_TP:.2f}\n")
    f.write(f"NEW-7 BE component: {BE_COMPONENT:.1f}bp\n\n")
    for sc in scenarios:
        tp_eff = BETA_TP * sc["d_tp_pp"]
        fe_eff = -sc["d_2y_bp"]
        be_eff = sc["d_10y_bp"]
        outcome = S0 + tp_eff + fe_eff + be_eff
        f.write(f"{sc['name']}\n")
        f.write(f"  Probability: {sc['prob']*100:.0f}%\n")
        f.write(f"  Spread outcome: {outcome:.0f}bp (P&L: {outcome - ENTRY:+.0f}bp)\n\n")
    f.write(f"Expected spread: {ev_spread:.0f}bp\n")
    f.write(f"Expected P&L: {ev_pnl:+.0f}bp\n")

print(f"\nResults written to {results_path}")
