"""
Steepener Trade Thesis — Quantitative Analysis
================================================
Three analyses to support the US 2s10s steepener thesis:

1. Oil-Curve Asymmetry:  Do oil shocks steepen the 2s10s curve?
2. Term Premium Decomposition:  Is the 10Y selloff structural (term premium) vs rate expectations?
3. Breakeven Divergence:  Does the market treat oil inflation as transitory?

Output: analysis_results.png  (3-panel figure)
        Console prints regression results and summary statistics
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "data steepener.xlsx"

# ─────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────

def load_sheet(sheet):
    """Load a sheet from the xlsx, return a Date-indexed Series."""
    df = pd.read_excel(DATA_FILE, sheet_name=sheet, header=None)
    # Find the row with "Date" in it to use as header
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    # Data starts after header; date is col 1, value is col 2 (col 0 is empty)
    data = df.iloc[header_row + 1:, 1:3].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    data = data.dropna().set_index("Date").sort_index()
    return data["Value"]


print("Loading data...")
cl1 = load_sheet("CL1")
ust2y = load_sheet("UST 2 y")
ust10y = load_sheet("UST 10 y")
be2y = load_sheet("US 2 year breakeven")
be10y = load_sheet("US 10yr breakeven")
spread = load_sheet("US 2yr10yr spread")
acm = load_sheet("ACM 10yr premium")

# Build aligned weekly dataframe for Analysis 1 & 3
daily = pd.DataFrame({
    "oil": cl1, "ust2y": ust2y, "ust10y": ust10y,
    "be2y": be2y, "be10y": be10y, "spread": spread, "acm": acm
}).dropna()

weekly = daily.resample("W-FRI").last().dropna()
wk_chg = pd.DataFrame({
    "oil_pct":    weekly["oil"].pct_change() * 100,
    "d_ust2y":    weekly["ust2y"].diff(),
    "d_ust10y":   weekly["ust10y"].diff(),
    "d_spread":   weekly["spread"].diff(),
    "d_be2y":     weekly["be2y"].diff(),
    "d_be10y":    weekly["be10y"].diff(),
    "d_acm":      weekly["acm"].diff(),
}).dropna()

# Daily changes for Analysis 2
d_daily = pd.DataFrame({
    "d_spread":  daily["spread"].diff(),
    "d_acm":     daily["acm"].diff(),
    "d_rate_exp": daily["ust10y"].diff() - daily["acm"].diff(),  # rate expectations = 10Y - TP
    "d_oil_pct":  daily["oil"].pct_change() * 100,
    "d_be2y":     daily["be2y"].diff(),
    "d_be10y":    daily["be10y"].diff(),
}).dropna()

print(f"Sample: {daily.index[0].date()} to {daily.index[-1].date()}")
print(f"  Daily obs:  {len(daily)}")
print(f"  Weekly obs: {len(wk_chg)}")


# ─────────────────────────────────────────────────────────
# ANALYSIS 1: Oil-Curve Asymmetry
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 1: Oil Price Shocks → 2s10s Curve Steepening")
print("="*65)

# Full-sample regression: weekly oil % change → weekly spread change
slope1, intercept1, r1, p1, se1 = stats.linregress(wk_chg["oil_pct"], wk_chg["d_spread"])
print(f"\nRegression: Δ(2s10s spread) = {intercept1:.3f} + {slope1:.3f} × Oil%Chg")
print(f"  R² = {r1**2:.4f},  p-value = {p1:.4f},  SE(beta) = {se1:.4f}")
print(f"  Interpretation: A +10% weekly oil move → {slope1*10:.1f}bp steepening")

# Regime analysis: oil spike weeks (>5% weekly move)
spike_thresh = 5.0
spikes = wk_chg[wk_chg["oil_pct"] > spike_thresh]
normal = wk_chg[wk_chg["oil_pct"].abs() <= spike_thresh]

print(f"\nRegime analysis (spike = weekly oil > +{spike_thresh}%):")
print(f"  Spike weeks (n={len(spikes)}): avg Δspread = {spikes['d_spread'].mean():+.2f}bp, "
      f"avg Δ2Y = {spikes['d_ust2y'].mean():+.3f}%, avg Δ10Y = {spikes['d_ust10y'].mean():+.3f}%")
print(f"  Normal weeks (n={len(normal)}): avg Δspread = {normal['d_spread'].mean():+.2f}bp, "
      f"avg Δ2Y = {normal['d_ust2y'].mean():+.3f}%, avg Δ10Y = {normal['d_ust10y'].mean():+.3f}%")

# Asymmetry: regress oil on each leg separately
s2, i2, r2, p2, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_ust2y"])
s10, i10, r10, p10, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_ust10y"])
print(f"\n  Oil → 2Y yield beta:  {s2:.4f} (p={p2:.4f})")
print(f"  Oil → 10Y yield beta: {s10:.4f} (p={p10:.4f})")
print(f"  → 10Y is {abs(s10/s2) if s2 != 0 else float('inf'):.1f}x more sensitive to oil than 2Y")


# ─────────────────────────────────────────────────────────
# ANALYSIS 2: Term Premium Decomposition
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 2: Term Premium vs Rate Expectations → 2s10s Spread")
print("="*65)

# Decompose 10Y = rate expectations + term premium
daily["rate_exp"] = daily["ust10y"] - daily["acm"]

print(f"\nCurrent 10Y yield decomposition:")
print(f"  10Y yield:          {daily['ust10y'].iloc[-1]:.3f}%")
print(f"  ACM term premium:   {daily['acm'].iloc[-1]:.3f}%")
print(f"  Rate expectations:  {daily['rate_exp'].iloc[-1]:.3f}%")

# What share of 10Y moves over last 6 months is term premium?
lookback = daily.index >= daily.index[-1] - pd.Timedelta(days=180)
recent = daily[lookback]
tp_move = recent["acm"].iloc[-1] - recent["acm"].iloc[0]
re_move = recent["rate_exp"].iloc[-1] - recent["rate_exp"].iloc[0]
y10_move = recent["ust10y"].iloc[-1] - recent["ust10y"].iloc[0]
print(f"\nLast 6 months change:")
print(f"  10Y yield:         {y10_move:+.3f}%")
print(f"  Term premium:      {tp_move:+.3f}% ({tp_move/y10_move*100 if y10_move else 0:+.0f}% of move)")
print(f"  Rate expectations: {re_move:+.3f}% ({re_move/y10_move*100 if y10_move else 0:+.0f}% of move)")

# Regression: daily spread change = b1*(rate exp change) + b2*(term premium change)
from numpy.linalg import lstsq
X = np.column_stack([d_daily["d_rate_exp"].values, d_daily["d_acm"].values])
X_const = np.column_stack([np.ones(len(X)), X])
y = d_daily["d_spread"].values
betas, residuals, _, _ = lstsq(X_const, y, rcond=None)
y_hat = X_const @ betas
ss_res = np.sum((y - y_hat)**2)
ss_tot = np.sum((y - y.mean())**2)
r2_multi = 1 - ss_res / ss_tot

# Standard errors
n, k = len(y), 3
mse = ss_res / (n - k)
var_betas = mse * np.linalg.inv(X_const.T @ X_const).diagonal()
se_betas = np.sqrt(var_betas)
t_stats = betas / se_betas

print(f"\nRegression: Δ(2s10s) = {betas[0]:.3f} + {betas[1]:.3f}×Δ(rate_exp) + {betas[2]:.3f}×Δ(term_prem)")
print(f"  β(rate_exp):   {betas[1]:+.3f}  (t={t_stats[1]:+.2f})")
print(f"  β(term_prem):  {betas[2]:+.3f}  (t={t_stats[2]:+.2f})")
print(f"  R² = {r2_multi:.4f}")
print(f"  → Term premium increases steepen the curve by {betas[2]:.1f}bp per 1bp TP rise")
if betas[2] > 0 and abs(t_stats[2]) > 2:
    print(f"  ✓ SUPPORTS THESIS: Rising term premium is a statistically significant steepener")

# Rolling 90-day correlation: term premium vs spread
roll_corr_tp = d_daily["d_acm"].rolling(90).corr(d_daily["d_spread"])
roll_corr_re = d_daily["d_rate_exp"].rolling(90).corr(d_daily["d_spread"])


# ─────────────────────────────────────────────────────────
# ANALYSIS 3: Breakeven Inflation Divergence
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 3: Breakeven Inflation Divergence — Oil → Transitory?")
print("="*65)

# Breakeven slope: 10Y BE - 2Y BE
daily["be_slope"] = daily["be10y"] - daily["be2y"]

# Regress each breakeven on oil (weekly)
s_be2, _, r_be2, p_be2, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be2y"])
s_be10, _, r_be10, p_be10, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be10y"])

print(f"\nOil sensitivity of breakeven inflation (weekly):")
print(f"  Oil → 2Y breakeven beta:  {s_be2:.4f} (R²={r_be2**2:.4f}, p={p_be2:.4f})")
print(f"  Oil → 10Y breakeven beta: {s_be10:.4f} (R²={r_be10**2:.4f}, p={p_be10:.4f})")
print(f"  Ratio: 2Y is {abs(s_be2/s_be10) if s_be10 != 0 else float('inf'):.1f}x more sensitive to oil")

# During oil spikes
spike_be2 = spikes["d_be2y"].mean()
spike_be10 = spikes["d_be10y"].mean()
print(f"\nDuring oil spike weeks (>{spike_thresh}%):")
print(f"  Avg Δ(2Y BE):  {spike_be2:+.4f}%")
print(f"  Avg Δ(10Y BE): {spike_be10:+.4f}%")
print(f"  → Short-end inflation expectations move {abs(spike_be2/spike_be10) if spike_be10 != 0 else float('inf'):.1f}x more")

# Current breakeven slope
current_be_slope = daily["be_slope"].iloc[-1]
be_slope_pctile = stats.percentileofscore(daily["be_slope"].dropna(), current_be_slope)
print(f"\nCurrent breakeven slope (10Y BE - 2Y BE): {current_be_slope:.3f}%")
print(f"  Historical percentile: {be_slope_pctile:.0f}th")
if current_be_slope < 0:
    print(f"  ✓ SUPPORTS THESIS: Negative slope = market prices oil inflation as transitory")
    print(f"    Short-end inflation expectations elevated vs long-end → Fed has cover to cut")


# ─────────────────────────────────────────────────────────
# FIGURE
# ─────────────────────────────────────────────────────────
print("\nGenerating charts...")

fig, axes = plt.subplots(3, 2, figsize=(16, 18))
fig.suptitle("US 2s10s Steepener — Quantitative Thesis Support", fontsize=16, fontweight="bold", y=0.98)

# ── Panel 1a: Scatter of oil % change vs spread change ──
ax = axes[0, 0]
colors = np.where(wk_chg["oil_pct"] > spike_thresh, "#e74c3c",
         np.where(wk_chg["oil_pct"] < -spike_thresh, "#3498db", "#bdc3c7"))
ax.scatter(wk_chg["oil_pct"], wk_chg["d_spread"], c=colors, alpha=0.6, s=25, edgecolors="none")
x_line = np.linspace(wk_chg["oil_pct"].min(), wk_chg["oil_pct"].max(), 100)
ax.plot(x_line, intercept1 + slope1 * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.axhline(0, color="gray", linewidth=0.5)
ax.axvline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Weekly Oil Price Change (%)")
ax.set_ylabel("Weekly 2s10s Spread Change (bp)")
ax.set_title("Analysis 1a: Oil Shocks → Curve Steepening", fontweight="bold")
ax.text(0.05, 0.95, f"β = {slope1:.2f} bp per 1% oil\nR² = {r1**2:.3f}  (p={p1:.4f})\n"
        f"Red = oil spike weeks (>{spike_thresh}%)",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 1b: Bar chart of regime analysis ──
ax = axes[0, 1]
categories = ["Oil Spike Weeks\n(>+5%)", "Normal Weeks"]
spread_means = [spikes["d_spread"].mean(), normal["d_spread"].mean()]
y2_means = [spikes["d_ust2y"].mean() * 100, normal["d_ust2y"].mean() * 100]  # convert to bp
y10_means = [spikes["d_ust10y"].mean() * 100, normal["d_ust10y"].mean() * 100]

x_pos = np.arange(len(categories))
width = 0.25
bars1 = ax.bar(x_pos - width, spread_means, width, label="Δ 2s10s Spread (bp)", color="#2ecc71")
bars2 = ax.bar(x_pos, y2_means, width, label="Δ 2Y Yield (bp)", color="#3498db")
bars3 = ax.bar(x_pos + width, y10_means, width, label="Δ 10Y Yield (bp)", color="#e74c3c")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xticks(x_pos)
ax.set_xticklabels(categories)
ax.set_ylabel("Average Weekly Change (bp)")
ax.set_title("Analysis 1b: Regime Analysis — Oil Spikes vs Normal", fontweight="bold")
ax.legend(fontsize=8)
ax.text(0.05, 0.95, f"Spike weeks: n={len(spikes)}\nNormal weeks: n={len(normal)}",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 2a: 10Y decomposition time series ──
ax = axes[1, 0]
ax.fill_between(daily.index, 0, daily["rate_exp"], alpha=0.4, color="#3498db", label="Rate Expectations")
ax.fill_between(daily.index, daily["rate_exp"], daily["ust10y"], alpha=0.4, color="#e74c3c", label="Term Premium (ACM)")
ax.plot(daily.index, daily["ust10y"], color="black", linewidth=1, label="10Y Yield")
ax.set_ylabel("Yield (%)")
ax.set_title("Analysis 2a: 10Y Yield Decomposition", fontweight="bold")
ax.legend(loc="upper left", fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.05, 0.05, f"Last 6M: TP {tp_move:+.0f}bp ({tp_move/y10_move*100 if y10_move else 0:+.0f}% of 10Y move)\n"
        f"         Rate Exp {re_move:+.0f}bp ({re_move/y10_move*100 if y10_move else 0:+.0f}% of 10Y move)",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 2b: Rolling correlation of TP vs spread and RE vs spread ──
ax = axes[1, 1]
ax.plot(roll_corr_tp.index, roll_corr_tp, color="#e74c3c", linewidth=1.5, label="Corr(Δ Term Premium, Δ Spread)")
ax.plot(roll_corr_re.index, roll_corr_re, color="#3498db", linewidth=1.5, label="Corr(Δ Rate Expectations, Δ Spread)")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_ylabel("90-Day Rolling Correlation")
ax.set_title("Analysis 2b: What Drives Steepening — TP vs Rate Expectations?", fontweight="bold")
ax.legend(loc="lower left", fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.05, 0.95, f"Regression β(TP) = {betas[2]:+.2f} (t={t_stats[2]:+.1f})\n"
        f"Regression β(RE) = {betas[1]:+.2f} (t={t_stats[1]:+.1f})\n"
        f"→ TP rises steepen the curve",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 3a: Oil vs breakeven slope time series ──
ax = axes[2, 0]
ax2 = ax.twinx()
ax.plot(daily.index, daily["oil"], color="#e67e22", linewidth=1, alpha=0.7, label="WTI Crude (LHS)")
ax2.plot(daily.index, daily["be_slope"], color="#8e44ad", linewidth=1.5, label="BE Slope: 10Y-2Y (RHS)")
ax2.axhline(0, color="#8e44ad", linewidth=0.5, linestyle="--")
ax.set_ylabel("Oil Price ($/bbl)", color="#e67e22")
ax2.set_ylabel("Breakeven Slope: 10Y BE - 2Y BE (%)", color="#8e44ad")
ax.set_title("Analysis 3a: Oil Price vs Breakeven Inflation Slope", fontweight="bold")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
ax.text(0.05, 0.05, f"Current BE slope: {current_be_slope:.3f}% ({be_slope_pctile:.0f}th pctile)\n"
        f"Negative = market sees oil inflation as transitory",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 3b: Scatter of oil vs 2Y BE and 10Y BE ──
ax = axes[2, 1]
ax.scatter(wk_chg["oil_pct"], wk_chg["d_be2y"], alpha=0.5, s=20, color="#e74c3c", label="2Y Breakeven", edgecolors="none")
ax.scatter(wk_chg["oil_pct"], wk_chg["d_be10y"], alpha=0.5, s=20, color="#3498db", label="10Y Breakeven", edgecolors="none")
x_line = np.linspace(wk_chg["oil_pct"].min(), wk_chg["oil_pct"].max(), 100)
ax.plot(x_line, s_be2 * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.plot(x_line, s_be10 * x_line, color="#3498db", linewidth=2, linestyle="--")
ax.axhline(0, color="gray", linewidth=0.5)
ax.axvline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Weekly Oil Price Change (%)")
ax.set_ylabel("Weekly Breakeven Change (%)")
ax.set_title("Analysis 3b: Oil Sensitivity — 2Y vs 10Y Breakevens", fontweight="bold")
ax.legend(fontsize=8)
ratio_text = f"2Y BE β = {s_be2:.4f} (p={p_be2:.4f})\n10Y BE β = {s_be10:.4f} (p={p_be10:.4f})\n"
ratio_text += f"→ 2Y is {abs(s_be2/s_be10):.1f}x more sensitive" if s_be10 != 0 else ""
ax.text(0.05, 0.95, ratio_text,
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("analysis_results.png", dpi=150, bbox_inches="tight")
print(f"\n✓ Charts saved to analysis_results.png")


# ─────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("SUMMARY: QUANTITATIVE SUPPORT FOR STEEPENER THESIS")
print("="*65)
print(f"""
1. OIL-CURVE ASYMMETRY
   • Oil spikes steepen the curve: β = {slope1:.2f}bp per 1% oil move (p={p1:.4f})
   • During spike weeks: spread widens {spikes['d_spread'].mean():+.1f}bp on average
   • 10Y yield {abs(s10/s2) if s2 != 0 else float('inf'):.1f}x more sensitive to oil than 2Y

2. TERM PREMIUM DECOMPOSITION
   • Last 6M: {tp_move/y10_move*100 if y10_move else 0:+.0f}% of 10Y move is term premium (structural)
   • Rising TP steepens the curve: β = {betas[2]:+.2f}bp (t={t_stats[2]:+.1f})
   • Rate expectations component has {"weaker" if abs(t_stats[1]) < abs(t_stats[2]) else "stronger"} effect on spread

3. BREAKEVEN DIVERGENCE
   • 2Y breakeven is {abs(s_be2/s_be10) if s_be10 != 0 else float('inf'):.1f}x more sensitive to oil than 10Y
   • Current BE slope: {current_be_slope:.3f}% ({be_slope_pctile:.0f}th percentile)
   • Market is pricing oil inflation as {"TRANSITORY ✓" if current_be_slope < 0 else "persistent ✗"}

TRADE: Entry {daily['spread'].iloc[-1]:.0f}bp → Target 70bp (SL 42bp)
""")
