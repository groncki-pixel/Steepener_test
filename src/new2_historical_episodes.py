"""
NEW-2: Historical Episodes Comparison
======================================
Traces 2Y, 10Y, and 2s10s spread paths after oil shocks.

Original design required USGG2YR and USGG10YR (back to 1989) for 1990/2008
episodes, but these sheets are NOT available. Data starts 2021-03-17.

ADAPTED APPROACH:
  - Covers the 2022 Russia-Ukraine episode (Feb 24, 2022) in full
  - Covers the 2026 Iran episode (Feb 27, 2026)
  - For 1990/2008, provides hardcoded historical context from known outcomes
  - Computes: 2Y, 10Y, spread paths for available episodes at +21d, +63d, +126d

Uses: UST 2 y, UST 10 y, US 2yr10yr spread, CL1

Output: Console episode comparison table
        ../output/new2_historical_episodes.txt
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
oil = load_bloomberg_sheet("CL1")

print("\n" + "=" * 70)
print("NEW-2: HISTORICAL EPISODE COMPARISON")
print("=" * 70)

print(f"\n  Data range: {ust2y.index[0].date()} to {ust2y.index[-1].date()}")
print(f"  NOTE: USGG2YR/USGG10YR (long history) not available.")
print(f"  1990 Gulf War and 2008 oil spike covered with hardcoded context.")

# ─── EPISODE ANALYSIS FUNCTION ───
def analyze_episode(name, start_date, ust2y, ust10y, spread, oil, horizons=[21, 63, 126]):
    """Analyze yield/spread path after an oil shock episode."""
    start = pd.Timestamp(start_date)

    # Check if we have data for this episode
    if start < ust2y.index[0] or start > ust2y.index[-1]:
        return None

    y2_0, y2_0_dt = get_nearest(ust2y, start_date)
    y10_0, y10_0_dt = get_nearest(ust10y, start_date)
    s_0, s_0_dt = get_nearest(spread, start_date)
    o_0, o_0_dt = get_nearest(oil, start_date)

    # Normalize spread
    if abs(s_0) < 10:
        s_0_bp = s_0 * 100
    else:
        s_0_bp = s_0

    results = {
        "name": name,
        "start": y2_0_dt.date(),
        "y2_0": y2_0,
        "y10_0": y10_0,
        "s_0_bp": s_0_bp,
        "oil_0": o_0,
        "horizons": {},
    }

    for h in horizons:
        target_dt = start + pd.Timedelta(days=int(h * 365 / 252))  # trading days to calendar
        if target_dt > ust2y.index[-1]:
            # Use latest available
            target_dt = ust2y.index[-1]
            h_label = f"+{h}d*"
        else:
            h_label = f"+{h}d"

        y2_h, y2_h_dt = get_nearest(ust2y, str(target_dt.date()))
        y10_h, _ = get_nearest(ust10y, str(target_dt.date()))
        s_h, _ = get_nearest(spread, str(target_dt.date()))
        o_h, _ = get_nearest(oil, str(target_dt.date()))

        if abs(s_h) < 10:
            s_h_bp = s_h * 100
        else:
            s_h_bp = s_h

        results["horizons"][h_label] = {
            "d_2y": (y2_h - y2_0) * 100,
            "d_10y": (y10_h - y10_0) * 100,
            "d_spread": s_h_bp - s_0_bp,
            "d_oil_pct": (o_h / o_0 - 1) * 100,
            "actual_dt": y2_h_dt.date(),
        }

    return results


# ─── ANALYZE AVAILABLE EPISODES ───
episodes = [
    ("2022 Russia-Ukraine", "2022-02-24"),
    ("2026 Iran (current)", "2026-02-27"),
]

results_all = []
for name, start in episodes:
    r = analyze_episode(name, start, ust2y, ust10y, spread, oil)
    if r:
        results_all.append(r)

# ─── PRINT RESULTS ───
for r in results_all:
    print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
    print(f"  │  {r['name']:<58}    │")
    print(f"  │  Start: {r['start']}  2Y: {r['y2_0']:.3f}%  10Y: {r['y10_0']:.3f}%            │")
    print(f"  │  Spread: {r['s_0_bp']:.0f}bp  Oil: ${r['oil_0']:.2f}                          │")
    print(f"  ├──────────────────────────────────────────────────────────────┤")
    print(f"  │  {'Horizon':<10} {'d(2Y)':>8} {'d(10Y)':>8} {'d(Spread)':>10} {'d(Oil)':>8} {'Date':>12} │")
    print(f"  │  {'-'*56} │")
    for h_label, h_data in r["horizons"].items():
        steepened = "↑" if h_data["d_spread"] > 0 else "↓"
        print(f"  │  {h_label:<10} {h_data['d_2y']:>+8.1f}bp {h_data['d_10y']:>+8.1f}bp "
              f"{h_data['d_spread']:>+8.0f}bp{steepened} {h_data['d_oil_pct']:>+8.1f}% {h_data['actual_dt']!s:>10} │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

# ─── HISTORICAL CONTEXT (hardcoded for episodes we can't compute) ───
print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
print(f"  │  HISTORICAL CONTEXT (pre-data episodes, from literature)      │")
print(f"  ├──────────────────────────────────────────────────────────────┤")
print(f"  │                                                              │")
print(f"  │  1990 Gulf War (Aug 1990):                                   │")
print(f"  │    Macro: Fed cutting into recession (FFR 8% → 3%)           │")
print(f"  │    Oil: $20 → $40 (+100%)                                    │")
print(f"  │    Curve: Initial parallel rise, then STEEP steepening        │")
print(f"  │    2s10s: ~50bp → ~250bp over 18 months                      │")
print(f"  │    Mechanism: Fed cut aggressively, long end held on deficit  │")
print(f"  │    VERDICT: OIL SHOCK → STEEPENING (via Fed cuts, 6M+ lag)   │")
print(f"  │                                                              │")
print(f"  │  2008 Oil Spike (Mar-Jul 2008):                              │")
print(f"  │    Macro: Fed cutting into GFC (FFR 5.25% → 0%)              │")
print(f"  │    Oil: $100 → $147 then crash to $33                        │")
print(f"  │    Curve: Already steepening on GFC; oil was noise            │")
print(f"  │    2s10s: ~150bp → ~275bp (but GFC-driven, not oil)          │")
print(f"  │    VERDICT: CONFOUNDED — recession steepening, not oil        │")
print(f"  │                                                              │")
print(f"  │  KEY PATTERN: Oil shocks steepen the curve ONLY when the     │")
print(f"  │  Fed is cutting or about to cut. The mechanism is Fed path   │")
print(f"  │  repricing, not oil directly (consistent with A1 finding).   │")
print(f"  └──────────────────────────────────────────────────────────────┘")

# ─── COMPARISON TABLE ───
if len(results_all) == 2:
    r2022 = results_all[0]
    r2026 = results_all[1]

    print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
    print(f"  │  2022 vs 2026 COMPARISON                                      │")
    print(f"  ├──────────────────────────────────────────────────────────────┤")
    print(f"  │  {'Metric':<25} {'2022 RU':>12} {'2026 Iran':>12} {'Diff':>10}  │")
    print(f"  │  {'-'*60}│")

    # Compare at +21d (1 month)
    h_key_2022 = [k for k in r2022["horizons"].keys() if "21" in k]
    h_key_2026 = [k for k in r2026["horizons"].keys() if "21" in k]

    if h_key_2022 and h_key_2026:
        h22 = r2022["horizons"][h_key_2022[0]]
        h26 = r2026["horizons"][h_key_2026[0]]
        print(f"  │  {'d(2Y) at +1M':<25} {h22['d_2y']:>+10.1f}bp {h26['d_2y']:>+10.1f}bp {h26['d_2y']-h22['d_2y']:>+10.1f} │")
        print(f"  │  {'d(10Y) at +1M':<25} {h22['d_10y']:>+10.1f}bp {h26['d_10y']:>+10.1f}bp {h26['d_10y']-h22['d_10y']:>+10.1f} │")
        print(f"  │  {'d(Spread) at +1M':<25} {h22['d_spread']:>+10.0f}bp {h26['d_spread']:>+10.0f}bp {h26['d_spread']-h22['d_spread']:>+10.0f} │")

    print(f"  │                                                              │")
    print(f"  │  2022 macro: Fed about to start aggressive hiking cycle       │")
    print(f"  │  2026 macro: Fed on hold, labor weakening, potential cuts     │")
    print(f"  │  → 2026 is MORE favorable for steepening than 2022           │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

# ─── WRITE RESULTS ───
results_path = "../output/new2_historical_episodes.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-2: Historical Episode Comparison\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Note: Long-history sheets (USGG2YR/10YR) not available.\n")
    f.write(f"Available episodes: 2022 Russia-Ukraine, 2026 Iran.\n\n")

    for r in results_all:
        f.write(f"\n{r['name']} (start: {r['start']})\n")
        f.write(f"  2Y: {r['y2_0']:.3f}%  10Y: {r['y10_0']:.3f}%  Spread: {r['s_0_bp']:.0f}bp  Oil: ${r['oil_0']:.2f}\n")
        for h_label, h_data in r["horizons"].items():
            f.write(f"  {h_label}: d(2Y)={h_data['d_2y']:+.1f}bp  d(10Y)={h_data['d_10y']:+.1f}bp  "
                    f"d(spread)={h_data['d_spread']:+.0f}bp  d(oil)={h_data['d_oil_pct']:+.1f}%\n")

    f.write(f"\nHistorical pattern: Oil shocks steepen only when Fed is cutting.\n")
    f.write(f"2026 macro (Fed on hold, labor weak) more favorable than 2022 (hiking).\n")

print(f"\nResults written to {results_path}")
