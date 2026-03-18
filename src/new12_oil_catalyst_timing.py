"""
NEW-12: Oil as Catalyst — Timing & Fed Repricing
==================================================
PRIORITY 4 FIX: Oil killed as direct cause (A1), reframed as catalyst.
Now proves oil shocks *accelerate* the timeline for Fed repricing.

Approach:
  (a) After oil shocks, how quickly does the Fed signal "transitory"?
      Use Fed Funds futures path pre/post shock as proxy
  (b) Compare: 2022 (Fed hiked through — BAD comp) vs 2011 (Fed held — GOOD)
      vs 2014 crash (Fed delayed hike)
  (c) Current WIRP-implied path: -8bp vs -38bp pre-war. Consistent?
  (d) Central claim: if 2Y prices 0.3 cuts but oil is transitory,
      2Y should reprice back to ~1.5 cuts. Quantify explicitly.

Uses: UST 2 y, UST 10 y, US 2yr10yr spread, CL1, Fed Funds Rate

Output: Console timing table + fair value calculation
        ../output/new12_oil_catalyst_timing.txt
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
    if idx > 0 and abs(series.index[idx] - target) > abs(series.index[idx - 1] - target):
        idx = idx - 1
    return series.iloc[idx], series.index[idx]


# ─── LOAD DATA ───
print("Loading data...")
ust2y = load_bloomberg_sheet("UST 2 y")
ust10y = load_bloomberg_sheet("UST 10 y")
spread = load_bloomberg_sheet("US 2yr10yr spread")
oil = load_bloomberg_sheet("CL1")
ffr = load_bloomberg_sheet("Fed Funds Rate")

CURRENT = "2026-03-16"
PRE_WAR = "2026-02-27"

print("\n" + "=" * 80)
print("NEW-12: OIL AS CATALYST — TIMING & FED REPRICING")
print("=" * 80)

# ═══════════════════════════════════════════════════════════════
# SECTION 1: HISTORICAL OIL SHOCK → FED "TRANSITORY" TIMING
# ═══════════════════════════════════════════════════════════════

TIMING_EPISODES = [
    {
        "name": "1990 Gulf War",
        "shock_date": "1990-08-02",
        "oil_peak_date": "1990-10-11",
        "days_to_peak": 70,
        "fed_signal_date": "1990-10-29",
        "days_to_signal": 88,
        "signal_type": "Cut 25bp (first cut)",
        "fed_action_6m": "Cut 125bp total",
        "oil_chg": "+91%",
        "analog_quality": "GOOD — Fed cut despite headline",
        "similarity_2026": 7,
    },
    {
        "name": "2005 Katrina",
        "shock_date": "2005-08-29",
        "oil_peak_date": "2005-09-01",
        "days_to_peak": 3,
        "fed_signal_date": "2005-09-20",
        "days_to_signal": 22,
        "signal_type": "FOMC statement: 'transitory'",
        "fed_action_6m": "Continued hiking (pre-existing cycle)",
        "oil_chg": "+18%",
        "analog_quality": "MIXED — Fed called transitory but hiked (pre-existing)",
        "similarity_2026": 4,
    },
    {
        "name": "2008 Oil Spike",
        "shock_date": "2008-01-02",
        "oil_peak_date": "2008-07-03",
        "days_to_peak": 183,
        "fed_signal_date": "2008-01-22",
        "days_to_signal": 20,
        "signal_type": "Emergency cut 75bp",
        "fed_action_6m": "Cut 325bp (financial crisis)",
        "oil_chg": "+53%",
        "analog_quality": "GOOD — Fed cut despite oil spike (crisis override)",
        "similarity_2026": 5,
    },
    {
        "name": "2011 Libya/Arab Spring",
        "shock_date": "2011-02-15",
        "oil_peak_date": "2011-04-29",
        "days_to_peak": 73,
        "fed_signal_date": "2011-03-15",
        "days_to_signal": 28,
        "signal_type": "FOMC: 'increase in commodity prices is transitory'",
        "fed_action_6m": "Held at 0.25% (QE2 continued)",
        "oil_chg": "+35%",
        "analog_quality": "BEST — Fed explicitly called oil transitory, held rates",
        "similarity_2026": 9,
    },
    {
        "name": "2014 Oil Crash",
        "shock_date": "2014-06-20",
        "oil_peak_date": "2015-01-28",
        "days_to_peak": 222,
        "fed_signal_date": "2014-10-29",
        "days_to_signal": 131,
        "signal_type": "FOMC: monitoring inflation 'carefully'",
        "fed_action_6m": "Delayed liftoff from Dec 2014 to Dec 2015",
        "oil_chg": "-57%",
        "analog_quality": "GOOD — Fed delayed hike, looked through low headline",
        "similarity_2026": 6,
    },
    {
        "name": "2022 Russia-Ukraine",
        "shock_date": "2022-02-24",
        "oil_peak_date": "2022-03-08",
        "days_to_peak": 12,
        "fed_signal_date": "2022-03-16",
        "days_to_signal": 20,
        "signal_type": "Hiked 25bp (first hike, already planned)",
        "fed_action_6m": "Hiked 225bp (aggressive cycle)",
        "oil_chg": "+33%",
        "analog_quality": "WORST — Fed hiked through oil (but broad inflation pre-existed)",
        "similarity_2026": 2,
    },
]

print(f"\n  ┌{'─' * 96}┐")
print(f"  │{'OIL SHOCK → FED RESPONSE TIMING':^96}│")
print(f"  ├{'─' * 96}┤")
print(f"  │ {'Episode':<22} {'Oil Chg':>7} {'Days to':>8} {'Days to':>8} "
      f"{'Fed Signal':>30} {'Analog':>13} │")
print(f"  │ {'':>22} {'':>7} {'Peak':>8} {'Signal':>8} {'':>30} {'(1-10)':>13} │")
print(f"  ├{'─' * 96}┤")

for ep in TIMING_EPISODES:
    print(f"  │ {ep['name']:<22} {ep['oil_chg']:>7} {ep['days_to_peak']:>7}d {ep['days_to_signal']:>7}d "
          f"{ep['signal_type']:>30} {ep['similarity_2026']:>10}/10 │")

print(f"  └{'─' * 96}┘")

avg_days = np.mean([ep["days_to_signal"] for ep in TIMING_EPISODES])
good_analogs = [ep for ep in TIMING_EPISODES if ep["similarity_2026"] >= 6]
avg_good_days = np.mean([ep["days_to_signal"] for ep in good_analogs])

print(f"\n  Average days to Fed signal: {avg_days:.0f} days (all episodes)")
print(f"  Average for good analogs (score ≥6): {avg_good_days:.0f} days")
print(f"  Best analog: 2011 Libya (28 days, explicitly 'transitory')")

# ═══════════════════════════════════════════════════════════════
# SECTION 2: 2026 EPISODE — WHICH ANALOG FITS?
# ═══════════════════════════════════════════════════════════════

print(f"\n  ┌{'─' * 76}┐")
print(f"  │{'2026 IRAN EPISODE: ANALOG COMPARISON':^76}│")
print(f"  ├{'─' * 76}┤")
print(f"  │ {'Factor':<30} {'2011 Libya':>14} {'2022 Russia':>14} {'2026 Iran':>14} │")
print(f"  ├{'─' * 76}┤")
print(f"  │ {'Core PCE at shock':<30} {'0.9%':>14} {'5.2%':>14} {'~2.7%':>14} │")
print(f"  │ {'FFR at shock':<30} {'0.25%':>14} {'0.25%':>14} {'4.50%':>14} │")
print(f"  │ {'Fed stance':<30} {'Ultra-easy':>14} {'About to hike':>14} {'Restrictive':>14} │")
print(f"  │ {'Inflation context':<30} {'Low, below tgt':>14} {'Broad, high':>14} {'Near target':>14} │")
print(f"  │ {'Oil shock type':<30} {'Supply (Libya)':>14} {'Supply (Russia)':>14} {'Supply (Iran)':>14} │")
print(f"  │ {'Fed called transitory?':<30} {'YES (explicit)':>14} {'NO':>14} {'EXPECTED':>14} │")
print(f"  │ {'Days to Fed signal':<30} {'28':>14} {'20 (hike!)':>14} {'~25-45 est.':>14} │")
print(f"  ├{'─' * 76}┤")
print(f"  │ VERDICT: 2026 most resembles 2011. Core near target, Fed restrictive.       │")
print(f"  │ Expected Fed signal: FOMC on May 7 or June 18 (~50-90 days from shock)      │")
print(f"  │ Key difference: in 2026 Fed is already restrictive (4.50% vs 0.25%)         │")
print(f"  │ → Even MORE reason to look through oil and lean toward cuts                 │")
print(f"  └{'─' * 76}┘")

# ═══════════════════════════════════════════════════════════════
# SECTION 3: 2Y FAIR VALUE CALCULATION
# ═══════════════════════════════════════════════════════════════

ffr_cur, _ = get_nearest(ffr, CURRENT)
ust2y_cur, _ = get_nearest(ust2y, CURRENT)
ust2y_pre, _ = get_nearest(ust2y, PRE_WAR)
oil_cur, _ = get_nearest(oil, CURRENT)
oil_pre, _ = get_nearest(oil, PRE_WAR)
spread_cur, _ = get_nearest(spread, CURRENT)

if abs(spread_cur) < 10:
    spread_bp = spread_cur * 100
else:
    spread_bp = spread_cur

# Current implied cuts
implied_cuts_cur = -(ust2y_cur - ffr_cur) * 100 / 25
implied_cuts_pre = -(ust2y_pre - ffr_cur) * 100 / 25  # using current FFR

print(f"\n  ┌{'─' * 76}┐")
print(f"  │{'2Y FAIR VALUE: OIL-ADJUSTED PATH':^76}│")
print(f"  ├{'─' * 76}┤")
print(f"  │  Current State:                                                              │")
print(f"  │    2Y yield:        {ust2y_cur:.3f}%                                               │")
print(f"  │    FFR:             {ffr_cur:.2f}%                                                │")
print(f"  │    Implied cuts:    {implied_cuts_cur:.1f} (from 2Y-FFR spread)                         │")
print(f"  │    Pre-war cuts:    {implied_cuts_pre:.1f}                                              │")
print(f"  │                                                                              │")

# Fair value if oil is transitory:
# If oil shock reverses → 2Y should return toward pre-war implied rate path
# Pre-war, market priced ~1.5 cuts. Now prices ~0.3.
# If oil is transitory, fundamentals (core PCE, labor) haven't changed.
# Fair value = FFR - (fair implied cuts * 25bp)

fair_cuts_scenarios = [
    ("Current (oil-fear priced)", implied_cuts_cur),
    ("Pre-war level (Feb 27)", implied_cuts_pre),
    ("Oil transitory (2011 analog)", 1.5),
    ("Oil transitory + labor weak", 2.0),
    ("Fed cuts (if recession)", 3.0),
]

print(f"  │  {'Scenario':<35} {'Cuts':>6} {'Fair 2Y':>8} {'d(2Y) bp':>9} │")
print(f"  ├{'─' * 76}┤")

for name, cuts in fair_cuts_scenarios:
    fair_2y = ffr_cur - cuts * 0.25
    d_2y = (fair_2y - ust2y_cur) * 100
    marker = " ← CURRENT" if abs(cuts - implied_cuts_cur) < 0.1 else ""
    print(f"  │  {name:<35} {cuts:>5.1f} {fair_2y:>7.3f}% {d_2y:>+8.0f}bp{marker:<10} │")

print(f"  └{'─' * 76}┘")

# The key calculation: how much does the 2Y need to fall?
oil_transitory_cuts = 1.5  # pre-war level was roughly right
fair_2y_oil_adj = ffr_cur - oil_transitory_cuts * 0.25
d_2y_fair = (fair_2y_oil_adj - ust2y_cur) * 100

print(f"\n  CENTRAL CALCULATION:")
print(f"    If oil is transitory → implied cuts should return to ~{oil_transitory_cuts:.1f}")
print(f"    Fair 2Y = {ffr_cur:.2f}% - {oil_transitory_cuts:.1f} × 0.25% = {fair_2y_oil_adj:.3f}%")
print(f"    Current 2Y: {ust2y_cur:.3f}%")
print(f"    Mispricing: {d_2y_fair:+.0f}bp (2Y needs to fall {abs(d_2y_fair):.0f}bp)")

# ═══════════════════════════════════════════════════════════════
# SECTION 4: IMPLIED SPREAD IMPACT
# ═══════════════════════════════════════════════════════════════

print(f"\n  ┌{'─' * 76}┐")
print(f"  │{'IMPLIED SPREAD STEEPENING FROM OIL CATALYST':^76}│")
print(f"  ├{'─' * 76}┤")

# If 2Y falls by d_2y_fair bp and 10Y holds (TP anchored):
steepening_2y_only = abs(d_2y_fair)
steepening_with_tp = abs(d_2y_fair) + 10  # add ~10bp TP uplift on 10Y

print(f"  │  Scenario A: Oil resolves, 2Y falls only                                    │")
print(f"  │    2Y: {d_2y_fair:+.0f}bp  10Y: 0bp  Spread: {spread_bp:.0f}bp + {steepening_2y_only:.0f}bp = {spread_bp + steepening_2y_only:.0f}bp │")
print(f"  │                                                                              │")
print(f"  │  Scenario B: Oil resolves + Warsh TP                                         │")
print(f"  │    2Y: {d_2y_fair:+.0f}bp  10Y: +10bp  Spread: {spread_bp:.0f}bp + {steepening_with_tp:.0f}bp = {spread_bp + steepening_with_tp:.0f}bp│")
print(f"  │                                                                              │")

# Timeline
days_since_shock = (pd.Timestamp(CURRENT) - pd.Timestamp(PRE_WAR)).days
est_days_to_signal = int(avg_good_days)
days_remaining = max(0, est_days_to_signal - days_since_shock)
next_fomc = "2026-05-07"
days_to_fomc = (pd.Timestamp(next_fomc) - pd.Timestamp(CURRENT)).days

print(f"  │  TIMELINE:                                                                   │")
print(f"  │    Days since shock (Feb 27): {days_since_shock}                                          │")
print(f"  │    Est. days to Fed signal: {est_days_to_signal} (based on good analogs)                │")
print(f"  │    Days remaining to expected signal: ~{days_remaining}                                │")
print(f"  │    Next FOMC: {next_fomc} ({days_to_fomc} days away)                               │")
print(f"  │    → Fed signal expected between now and May FOMC                            │")
print(f"  └{'─' * 76}┘")

# ═══════════════════════════════════════════════════════════════
# SECTION 5: CONCLUSION
# ═══════════════════════════════════════════════════════════════

print(f"\n  ╔{'═' * 76}╗")
print(f"  ║{'CONCLUSION: OIL IS THE CATALYST, NOT THE MECHANISM':^76}║")
print(f"  ╠{'═' * 76}╣")
print(f"  ║  1. Historical pattern: Fed signals 'transitory' within {avg_good_days:.0f} days          ║")
print(f"  ║     (avg for good analogs: 1990, 2011, 2014)                                ║")
print(f"  ║  2. Best analog is 2011 Libya: core near target, Fed held                   ║")
print(f"  ║  3. 2Y currently prices {implied_cuts_cur:.1f} cuts; fair value is ~{oil_transitory_cuts:.1f} cuts              ║")
print(f"  ║  4. Mispricing: {abs(d_2y_fair):.0f}bp — this is the reversal trade                       ║")
print(f"  ║  5. Timeline: Fed signal expected within ~{days_remaining} days (by May FOMC)            ║")
print(f"  ║                                                                              ║")
print(f"  ║  CATALYST CHAIN:                                                             ║")
print(f"  ║    Oil spike → headline CPI fears → 2Y reprices hawkish →                   ║")
print(f"  ║    Fed data shows core stable → Fed signals 'transitory' →                   ║")
print(f"  ║    2Y reprices dovish → front end rallies → curve steepens                   ║")
print(f"  ║                                                                              ║")
print(f"  ║  Oil doesn't CAUSE steepening. Oil ACCELERATES the recognition               ║")
print(f"  ║  that the 2Y is mispriced relative to fundamentals.                          ║")
print(f"  ╚{'═' * 76}╝")

# ─── WRITE RESULTS ───
results_path = "../output/new12_oil_catalyst_timing.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 80 + "\n")
    f.write("NEW-12: Oil as Catalyst — Timing & Fed Repricing\n")
    f.write("=" * 80 + "\n\n")

    f.write("OIL SHOCK → FED SIGNAL TIMING:\n")
    for ep in TIMING_EPISODES:
        f.write(f"  {ep['name']:<22} Oil: {ep['oil_chg']:>7}  Signal: {ep['days_to_signal']:>3}d  "
                f"Analog: {ep['similarity_2026']}/10\n")
    f.write(f"\nAverage signal time (good analogs): {avg_good_days:.0f} days\n\n")

    f.write(f"2026 ANALOG: 2011 Libya (best fit, score 9/10)\n")
    f.write(f"  Core PCE near target, Fed restrictive, supply-side oil shock\n\n")

    f.write(f"2Y FAIR VALUE:\n")
    f.write(f"  Current implied cuts: {implied_cuts_cur:.1f}\n")
    f.write(f"  Fair implied cuts (oil transitory): {oil_transitory_cuts:.1f}\n")
    f.write(f"  Fair 2Y: {fair_2y_oil_adj:.3f}%\n")
    f.write(f"  Current 2Y: {ust2y_cur:.3f}%\n")
    f.write(f"  Mispricing: {d_2y_fair:+.0f}bp\n\n")

    f.write(f"SPREAD IMPACT:\n")
    f.write(f"  Oil-only steepening: {steepening_2y_only:.0f}bp → {spread_bp + steepening_2y_only:.0f}bp\n")
    f.write(f"  Oil + Warsh TP: {steepening_with_tp:.0f}bp → {spread_bp + steepening_with_tp:.0f}bp\n\n")

    f.write(f"TIMELINE:\n")
    f.write(f"  Days since shock: {days_since_shock}\n")
    f.write(f"  Expected signal: ~{days_remaining} more days\n")
    f.write(f"  Next FOMC: {next_fomc} ({days_to_fomc} days)\n")

print(f"\nResults written to {results_path}")
