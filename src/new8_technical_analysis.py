"""
NEW-8: Technical Analysis — 2s10s Spread
=========================================
Computes standard technical indicators on the 2s10s spread to identify
entry timing signals: moving averages, RSI, Bollinger Bands, ATR,
and support/resistance levels.

Uses: US 2yr10yr spread from data_steepener.xlsx

Output: Console technical snapshot + S/R levels
        ../output/new8_technical_analysis.txt
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


# ─── LOAD DATA ───
print("Loading data...")
spread_raw = load_bloomberg_sheet("US 2yr10yr spread")

# Normalize to bp
if abs(spread_raw.iloc[-1]) < 10:
    spread = spread_raw * 100  # convert to bp
else:
    spread = spread_raw.copy()

print("\n" + "=" * 70)
print("NEW-8: TECHNICAL ANALYSIS — 2s10s SPREAD")
print("=" * 70)
print(f"\n  Data: {spread.index[0].date()} to {spread.index[-1].date()} ({len(spread)} obs)")

# ─── MOVING AVERAGES ───
sma_50 = spread.rolling(50).mean()
sma_200 = spread.rolling(200).mean()
ema_21 = spread.ewm(span=21).mean()

cur = spread.iloc[-1]
sma50_cur = sma_50.iloc[-1]
sma200_cur = sma_200.iloc[-1]
ema21_cur = ema_21.iloc[-1]

print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  MOVING AVERAGES                                      │")
print(f"  ├──────────────────────────────────────────────────────┤")
print(f"  │  Current Spread:   {cur:.0f}bp                           │")
print(f"  │  21D EMA:          {ema21_cur:.0f}bp ({cur - ema21_cur:+.0f}bp from current)   │")
print(f"  │  50D SMA:          {sma50_cur:.0f}bp ({cur - sma50_cur:+.0f}bp from current)   │")
print(f"  │  200D SMA:         {sma200_cur:.0f}bp ({cur - sma200_cur:+.0f}bp from current)  │")
print(f"  ├──────────────────────────────────────────────────────┤")

# MA regime
if cur > sma50_cur > sma200_cur:
    ma_regime = "BULLISH — price > 50D > 200D (uptrend)"
elif cur < sma50_cur < sma200_cur:
    ma_regime = "BEARISH — price < 50D < 200D (downtrend)"
elif sma50_cur > sma200_cur:
    ma_regime = "MIXED BULLISH — 50D > 200D but price near/below 50D"
else:
    ma_regime = "MIXED BEARISH — 50D < 200D, potential bottoming"

# Golden/Death cross
# Check if 50D crossed 200D recently (last 20 days)
recent_50 = sma_50.iloc[-20:]
recent_200 = sma_200.iloc[-20:]
if not recent_50.isna().all() and not recent_200.isna().all():
    cross_diff = recent_50 - recent_200
    cross_diff_clean = cross_diff.dropna()
    if len(cross_diff_clean) > 1:
        if cross_diff_clean.iloc[0] < 0 and cross_diff_clean.iloc[-1] > 0:
            ma_regime += " — GOLDEN CROSS (bullish signal)"
        elif cross_diff_clean.iloc[0] > 0 and cross_diff_clean.iloc[-1] < 0:
            ma_regime += " — DEATH CROSS (bearish signal)"

print(f"  │  Regime: {ma_regime:<42} │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── RSI(14) ───
delta = spread.diff()
gain = delta.clip(lower=0)
loss = (-delta).clip(lower=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
rsi_cur = rsi.iloc[-1]

print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  RSI(14)                                               │")
print(f"  ├──────────────────────────────────────────────────────┤")
print(f"  │  Current RSI: {rsi_cur:.1f}                                 │")
print(f"  │  ", end="")
if rsi_cur > 70:
    print(f"OVERBOUGHT (>70) — potential pullback risk            │")
elif rsi_cur < 30:
    print(f"OVERSOLD (<30) — potential bounce / entry signal       │")
elif rsi_cur < 40:
    print(f"NEAR OVERSOLD (30-40) — approaching entry zone        │")
elif rsi_cur > 60:
    print(f"NEAR OVERBOUGHT (60-70) — momentum strong             │")
else:
    print(f"NEUTRAL (40-60) — no extreme signal                   │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── BOLLINGER BANDS (20, 2) ───
bb_mid = spread.rolling(20).mean()
bb_std = spread.rolling(20).std()
bb_upper = bb_mid + 2 * bb_std
bb_lower = bb_mid - 2 * bb_std
bb_width = (bb_upper - bb_lower)

bb_mid_cur = bb_mid.iloc[-1]
bb_upper_cur = bb_upper.iloc[-1]
bb_lower_cur = bb_lower.iloc[-1]
bb_width_cur = bb_width.iloc[-1]
bb_pct = (cur - bb_lower_cur) / (bb_upper_cur - bb_lower_cur) * 100 if bb_upper_cur != bb_lower_cur else 50

# Bollinger Band squeeze detection
bb_width_pctile = (bb_width.dropna() < bb_width_cur).mean() * 100

print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  BOLLINGER BANDS (20, 2)                               │")
print(f"  ├──────────────────────────────────────────────────────┤")
print(f"  │  Upper Band:  {bb_upper_cur:.0f}bp                              │")
print(f"  │  Middle Band: {bb_mid_cur:.0f}bp                              │")
print(f"  │  Lower Band:  {bb_lower_cur:.0f}bp                              │")
print(f"  │  Current:     {cur:.0f}bp (%B = {bb_pct:.0f}%)                   │")
print(f"  │  Band Width:  {bb_width_cur:.0f}bp ({bb_width_pctile:.0f}th percentile)           │")
print(f"  │  ", end="")
if bb_pct > 100:
    print(f"ABOVE UPPER BAND — overbought / breakout              │")
elif bb_pct < 0:
    print(f"BELOW LOWER BAND — oversold / breakdown               │")
elif bb_pct > 80:
    print(f"NEAR UPPER — momentum but extended                    │")
elif bb_pct < 20:
    print(f"NEAR LOWER — potential mean reversion entry           │")
else:
    print(f"MID-RANGE — neutral                                   │")
if bb_width_pctile < 20:
    print(f"  │  SQUEEZE DETECTED — low vol, breakout imminent          │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── ATR(14) ───
# For spread (single series), ATR = average of absolute daily changes
atr = spread.diff().abs().rolling(14).mean()
atr_cur = atr.iloc[-1]

print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  ATR(14) — VOLATILITY                                  │")
print(f"  ├──────────────────────────────────────────────────────┤")
print(f"  │  Current ATR: {atr_cur:.1f}bp/day                           │")
print(f"  │  Stop calibration (2x ATR): {2*atr_cur:.0f}bp from entry       │")
print(f"  │  Entry at {cur:.0f}bp → ATR stop at {cur - 2*atr_cur:.0f}bp              │")
print(f"  │  vs Fundamental stop: 42bp                             │")

atr_stop = cur - 2 * atr_cur
if atr_stop > 42:
    print(f"  │  ATR stop ({atr_stop:.0f}bp) is TIGHTER than fundamental (42bp)  │")
    print(f"  │  → Use ATR stop for initial risk management              │")
else:
    print(f"  │  ATR stop ({atr_stop:.0f}bp) is WIDER than fundamental (42bp)   │")
    print(f"  │  → Fundamental stop is appropriate                       │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── SUPPORT / RESISTANCE LEVELS ───
# Find local minima and maxima over rolling 63-day windows
print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  SUPPORT & RESISTANCE LEVELS                           │")
print(f"  ├──────────────────────────────────────────────────────┤")

# Use last 2 years of data
recent = spread.loc[spread.index >= spread.index[-1] - pd.Timedelta(days=504)]

# Find local minima (support) and maxima (resistance) using rolling windows
window = 63
local_min_mask = (recent == recent.rolling(window, center=True).min())
local_max_mask = (recent == recent.rolling(window, center=True).max())

local_mins = recent[local_min_mask].dropna()
local_maxs = recent[local_max_mask].dropna()

# Cluster nearby levels (within 3bp)
def cluster_levels(levels, threshold=3):
    if len(levels) == 0:
        return []
    sorted_vals = sorted(levels.values)
    clusters = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] < threshold:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [(np.mean(c), len(c)) for c in clusters]

support_clusters = cluster_levels(local_mins)
resistance_clusters = cluster_levels(local_maxs)

# Sort by proximity to current level
support_below = [(lvl, n) for lvl, n in support_clusters if lvl < cur]
resistance_above = [(lvl, n) for lvl, n in resistance_clusters if lvl > cur]

support_below.sort(key=lambda x: x[0], reverse=True)  # nearest first
resistance_above.sort(key=lambda x: x[0])  # nearest first

print(f"  │  Current: {cur:.0f}bp                                      │")
print(f"  │                                                        │")
print(f"  │  RESISTANCE (above):                                   │")
for i, (lvl, n) in enumerate(resistance_above[:4]):
    strength = "strong" if n >= 3 else "moderate" if n >= 2 else "weak"
    print(f"  │    R{i+1}: {lvl:.0f}bp ({strength}, {n} touches)                    │")
if not resistance_above:
    print(f"  │    No clear resistance levels identified               │")

print(f"  │  SUPPORT (below):                                      │")
for i, (lvl, n) in enumerate(support_below[:4]):
    strength = "strong" if n >= 3 else "moderate" if n >= 2 else "weak"
    print(f"  │    S{i+1}: {lvl:.0f}bp ({strength}, {n} touches)                    │")
if not support_below:
    print(f"  │    No clear support levels identified                  │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── OVERALL TECHNICAL ASSESSMENT ───
print(f"\n  ┌──────────────────────────────────────────────────────┐")
print(f"  │  OVERALL TECHNICAL ASSESSMENT                          │")
print(f"  ├──────────────────────────────────────────────────────┤")

signals = []
if cur > sma50_cur:
    signals.append(("50D SMA", "BULLISH", "price above"))
else:
    signals.append(("50D SMA", "BEARISH", "price below"))

if cur > sma200_cur:
    signals.append(("200D SMA", "BULLISH", "price above"))
else:
    signals.append(("200D SMA", "BEARISH", "price below"))

if rsi_cur < 30:
    signals.append(("RSI", "BULLISH", f"oversold at {rsi_cur:.0f}"))
elif rsi_cur > 70:
    signals.append(("RSI", "BEARISH", f"overbought at {rsi_cur:.0f}"))
else:
    signals.append(("RSI", "NEUTRAL", f"at {rsi_cur:.0f}"))

if bb_pct < 20:
    signals.append(("Bollinger", "BULLISH", "near lower band"))
elif bb_pct > 80:
    signals.append(("Bollinger", "BEARISH", "near upper band"))
else:
    signals.append(("Bollinger", "NEUTRAL", "mid-range"))

bullish = sum(1 for _, s, _ in signals if s == "BULLISH")
bearish = sum(1 for _, s, _ in signals if s == "BEARISH")

for name, signal, detail in signals:
    print(f"  │  {name:<12} {signal:<10} ({detail}){'':>20}│")

print(f"  ├──────────────────────────────────────────────────────┤")
if bullish > bearish:
    print(f"  │  NET: BULLISH ({bullish}/{len(signals)} signals)                    │")
    print(f"  │  Entry timing: FAVORABLE                               │")
elif bearish > bullish:
    print(f"  │  NET: BEARISH ({bearish}/{len(signals)} signals)                    │")
    print(f"  │  Entry timing: WAIT for pullback or confirmation       │")
else:
    print(f"  │  NET: MIXED — no clear directional signal               │")
    print(f"  │  Entry timing: NEUTRAL — use fundamentals for timing    │")
print(f"  └──────────────────────────────────────────────────────┘")

# ─── WRITE RESULTS ───
results_path = "../output/new8_technical_analysis.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 70 + "\n")
    f.write("NEW-8: Technical Analysis — 2s10s Spread\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Current spread: {cur:.0f}bp\n")
    f.write(f"21D EMA: {ema21_cur:.0f}bp  50D SMA: {sma50_cur:.0f}bp  200D SMA: {sma200_cur:.0f}bp\n")
    f.write(f"RSI(14): {rsi_cur:.1f}\n")
    f.write(f"Bollinger %B: {bb_pct:.0f}%  Width: {bb_width_cur:.0f}bp\n")
    f.write(f"ATR(14): {atr_cur:.1f}bp/day\n\n")
    f.write(f"MA Regime: {ma_regime}\n\n")
    f.write(f"Support levels: {', '.join(f'{lvl:.0f}bp' for lvl, _ in support_below[:3])}\n")
    f.write(f"Resistance levels: {', '.join(f'{lvl:.0f}bp' for lvl, _ in resistance_above[:3])}\n\n")
    f.write(f"Signals: {bullish} bullish, {bearish} bearish, {len(signals)-bullish-bearish} neutral\n")

print(f"\nResults written to {results_path}")
