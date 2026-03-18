"""
NEW-5: Market Positioning & Sentiment Proxy
=============================================
Original design required CFTC Commitments of Traders data, which is NOT
available in the data file.

ADAPTED APPROACH:
  - Uses VIX (VIXCLS) as a sentiment/positioning proxy
  - Uses spread volatility regime to assess crowding risk
  - Computes spread z-score relative to recent history
  - Analyzes co-movement of VIX and spread to infer risk positioning

Uses: US 2yr10yr spread, VIXCLS from data_steepener.xlsx

Output: Console positioning proxy analysis
        ../output/new5_cftc_positioning.txt
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


def load_fred_sheet(sheet):
    """Load FRED-format sheet (observation_date in col 0, value in col 1)."""
    df = pd.read_excel(DATA_FILE, sheet_name=sheet, header=None)
    for i, row in df.iterrows():
        vals = row.astype(str).str.lower()
        if vals.str.contains("date").any() or vals.str.contains("observation").any():
            header_row = i
            break
    else:
        header_row = 0
    data = df.iloc[header_row + 1:, :2].copy()
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
spread = load_bloomberg_sheet("US 2yr10yr spread")
vix = load_fred_sheet("VIXCLS")

# Align
daily = pd.DataFrame({"spread": spread, "vix": vix}).dropna()

# Normalize spread to bp
if abs(daily["spread"].iloc[-1]) < 10:
    daily["spread_bp"] = daily["spread"] * 100
else:
    daily["spread_bp"] = daily["spread"]

CURRENT = "2026-03-16"

print("\n" + "=" * 70)
print("NEW-5: MARKET POSITIONING & SENTIMENT PROXY")
print("=" * 70)

print(f"\n  DATA NOTE: CFTC sheet not available. Using VIX + spread analytics")
print(f"  as positioning proxy.")

# ─── SPREAD STATISTICS ───
lookback_1y = daily.loc[daily.index >= daily.index[-1] - pd.Timedelta(days=252)]
lookback_2y = daily.loc[daily.index >= daily.index[-1] - pd.Timedelta(days=504)]
lookback_6m = daily.loc[daily.index >= daily.index[-1] - pd.Timedelta(days=126)]

spread_cur = daily["spread_bp"].iloc[-1]
spread_mean_1y = lookback_1y["spread_bp"].mean()
spread_std_1y = lookback_1y["spread_bp"].std()
spread_z = (spread_cur - spread_mean_1y) / spread_std_1y if spread_std_1y > 0 else 0

# Percentile rank
pctile_1y = (lookback_1y["spread_bp"] < spread_cur).mean() * 100
pctile_2y = (lookback_2y["spread_bp"] < spread_cur).mean() * 100

spread_min_1y = lookback_1y["spread_bp"].min()
spread_max_1y = lookback_1y["spread_bp"].max()

print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  SPREAD POSITIONING (statistical)                         │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Current spread:    {spread_cur:.0f}bp                              │")
print(f"  │  1Y mean:           {spread_mean_1y:.0f}bp                              │")
print(f"  │  1Y std:            {spread_std_1y:.0f}bp                              │")
print(f"  │  Z-score (1Y):      {spread_z:+.2f}                             │")
print(f"  │  1Y percentile:     {pctile_1y:.0f}th                              │")
print(f"  │  2Y percentile:     {pctile_2y:.0f}th                              │")
print(f"  │  1Y range:          {spread_min_1y:.0f}bp to {spread_max_1y:.0f}bp                  │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── VIX ANALYSIS ───
vix_cur = daily["vix"].iloc[-1]
vix_mean_1y = lookback_1y["vix"].mean()
vix_std_1y = lookback_1y["vix"].std()
vix_z = (vix_cur - vix_mean_1y) / vix_std_1y if vix_std_1y > 0 else 0
vix_pctile_1y = (lookback_1y["vix"] < vix_cur).mean() * 100

print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  VIX SENTIMENT PROXY                                      │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Current VIX:       {vix_cur:.1f}                              │")
print(f"  │  1Y mean:           {vix_mean_1y:.1f}                              │")
print(f"  │  Z-score (1Y):      {vix_z:+.2f}                             │")
print(f"  │  1Y percentile:     {vix_pctile_1y:.0f}th                              │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── VIX-SPREAD CORRELATION ───
# When VIX spikes (risk-off), does the curve steepen or flatten?
daily_changes = pd.DataFrame({
    "d_spread": daily["spread_bp"].diff(),
    "d_vix": daily["vix"].diff(),
}).dropna()

corr_all = daily_changes["d_spread"].corr(daily_changes["d_vix"])

# Correlation during high-VIX periods
high_vix_mask = daily["vix"] > daily["vix"].quantile(0.75)
if high_vix_mask.sum() > 30:
    high_vix_changes = daily_changes.loc[high_vix_mask.reindex(daily_changes.index, fill_value=False)]
    corr_high_vix = high_vix_changes["d_spread"].corr(high_vix_changes["d_vix"])
else:
    corr_high_vix = np.nan

# Recent correlation (last 63 days)
recent_changes = daily_changes.loc[daily_changes.index >= daily_changes.index[-1] - pd.Timedelta(days=63)]
corr_recent = recent_changes["d_spread"].corr(recent_changes["d_vix"])

print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  VIX-SPREAD CO-MOVEMENT                                   │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Full-sample corr(d_spread, d_VIX):  {corr_all:+.3f}               │")
print(f"  │  High-VIX periods corr:              {corr_high_vix:+.3f}               │")
print(f"  │  Recent 3M corr:                     {corr_recent:+.3f}               │")
print(f"  ├──────────────────────────────────────────────────────────┤")
if corr_all < -0.1:
    print(f"  │  INTERPRETATION: VIX spikes → curve FLATTENS              │")
    print(f"  │  Risk-off = flight to long end → 10Y rally → flattening   │")
    print(f"  │  Steepener is a RISK-ON trade (contrarian vs current VIX) │")
elif corr_all > 0.1:
    print(f"  │  INTERPRETATION: VIX spikes → curve STEEPENS              │")
    print(f"  │  Risk-off = front-end rally → steepening                  │")
    print(f"  │  Steepener benefits from further vol expansion             │")
else:
    print(f"  │  INTERPRETATION: No strong VIX-spread relationship         │")
    print(f"  │  Curve dynamics driven by rate expectations, not risk      │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── SPREAD VOLATILITY REGIME ───
spread_vol_21d = daily["spread_bp"].diff().rolling(21).std() * np.sqrt(252)
vol_cur = spread_vol_21d.iloc[-1]
vol_mean = spread_vol_21d.mean()
vol_pctile = (spread_vol_21d < vol_cur).mean() * 100

print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  SPREAD VOLATILITY REGIME                                  │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  21D realized vol (annualized): {vol_cur:.0f}bp                   │")
print(f"  │  Historical mean vol:           {vol_mean:.0f}bp                   │")
print(f"  │  Vol percentile:                {vol_pctile:.0f}th                  │")
if vol_pctile > 75:
    print(f"  │  REGIME: HIGH VOL — position sizing should be smaller      │")
elif vol_pctile < 25:
    print(f"  │  REGIME: LOW VOL — potentially entering before breakout    │")
else:
    print(f"  │  REGIME: NORMAL VOL — standard position sizing             │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── CROWDING ASSESSMENT ───
print(f"\n  ┌──────────────────────────────────────────────────────────┐")
print(f"  │  CROWDING RISK ASSESSMENT                                  │")
print(f"  ├──────────────────────────────────────────────────────────┤")
print(f"  │  Without CFTC positioning data, crowding assessment is     │")
print(f"  │  qualitative:                                              │")
print(f"  │                                                            │")
print(f"  │  1. Wall Street consensus: Multiple desks (GS, JPM, MS)    │")
print(f"  │     recommend steepeners → trade is CONSENSUS              │")
print(f"  │  2. Spread percentile ({pctile_1y:.0f}th): ", end="")
if pctile_1y < 30:
    print(f"LOW — contrarian entry   │")
elif pctile_1y > 70:
    print(f"HIGH — late entry risk   │")
else:
    print(f"MID — neutral            │")
print(f"  │  3. VIX at {vix_cur:.0f} ({vix_pctile_1y:.0f}th pctile): ", end="")
if vix_pctile_1y > 75:
    print(f"ELEVATED — stress     │")
elif vix_pctile_1y > 50:
    print(f"ABOVE AVG             │")
else:
    print(f"BELOW AVG — calm      │")
print(f"  │                                                            │")
print(f"  │  OVERALL: ", end="")
if pctile_1y < 30 and vix_pctile_1y > 60:
    print(f"FAVORABLE — spread cheap + vol elevated          │")
elif pctile_1y > 70:
    print(f"CAUTION — spread already rich                    │")
else:
    print(f"NEUTRAL — consensus trade, standard crowding     │")
print(f"  └──────────────────────────────────────────────────────────┘")

# ─── WRITE RESULTS ───
results_path = "../output/new5_cftc_positioning.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-5: Market Positioning & Sentiment Proxy\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Note: CFTC data not available. Using VIX + spread analytics.\n\n")
    f.write(f"Spread: {spread_cur:.0f}bp (z={spread_z:+.2f}, {pctile_1y:.0f}th pctile 1Y, {pctile_2y:.0f}th pctile 2Y)\n")
    f.write(f"VIX: {vix_cur:.1f} (z={vix_z:+.2f}, {vix_pctile_1y:.0f}th pctile)\n")
    f.write(f"Corr(d_spread, d_VIX): {corr_all:+.3f} (all), {corr_recent:+.3f} (3M)\n")
    f.write(f"Spread vol: {vol_cur:.0f}bp ann ({vol_pctile:.0f}th pctile)\n")

print(f"\nResults written to {results_path}")
