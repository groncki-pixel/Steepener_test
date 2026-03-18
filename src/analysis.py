"""
Steepener Trade Thesis — Quantitative Analysis
================================================
Six analyses to support the US 2s10s steepener thesis:

1. Oil-Curve Asymmetry:  Do oil shocks steepen the 2s10s curve?
2. Term Premium Decomposition:  Is the 10Y selloff structural (term premium) vs rate expectations?
3. Breakeven Divergence:  Does the market treat oil inflation as transitory?
4. Oil Regime Spread Outcomes:  Permutation-tested regime analysis with threshold sensitivity
5. Carry & Scenario P&L:  DV01-neutral carry cost and scenario table
6. 2Y Mean Reversion After Oil Spikes:  Event study of 2Y yield reversal

Output: analysis_results.png  (multi-panel figure)
        Console prints regression results and summary statistics
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from numpy.linalg import lstsq
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"

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
print("ANALYSIS 1: Oil Price Shocks -> 2s10s Curve Steepening")
print("="*65)

# Full-sample regression: weekly oil % change -> weekly spread change
slope1, intercept1, r1, p1, se1 = stats.linregress(wk_chg["oil_pct"], wk_chg["d_spread"])
print(f"\nRegression: d(2s10s spread) = {intercept1:.3f} + {slope1:.3f} x Oil%Chg")
print(f"  R2 = {r1**2:.4f},  p-value(OLS) = {p1:.4f},  SE(beta) = {se1:.4f}")
print(f"  Interpretation: A +10% weekly oil move -> {slope1*10:.1f}bp steepening")

# Newey-West HAC standard errors
X_hac = sm.add_constant(wk_chg["oil_pct"].values)
y_hac = wk_chg["d_spread"].values
ols_model = sm.OLS(y_hac, X_hac).fit()
# Use Newey-West with automatic lag selection (floor of 4*(T/100)^(2/9))
nw_lags = int(np.floor(4 * (len(y_hac) / 100) ** (2/9)))
hac_model = sm.OLS(y_hac, X_hac).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags})
hac_pval = hac_model.pvalues[1]
hac_se = hac_model.bse[1]
print(f"\n  Newey-West HAC (lags={nw_lags}):")
print(f"    SE(beta) = {hac_se:.4f},  p-value(HAC) = {hac_pval:.4f}")
print(f"    OLS p = {p1:.4f}  vs  HAC p = {hac_pval:.4f}")

# Regime analysis: oil spike weeks (>5% weekly move)
spike_thresh = 5.0
spikes = wk_chg[wk_chg["oil_pct"] > spike_thresh]
normal = wk_chg[wk_chg["oil_pct"].abs() <= spike_thresh]

print(f"\nRegime analysis (spike = weekly oil > +{spike_thresh}%):")
print(f"  Spike weeks (n={len(spikes)}): avg dspread = {spikes['d_spread'].mean():+.2f}bp, "
      f"avg d2Y = {spikes['d_ust2y'].mean():+.3f}%, avg d10Y = {spikes['d_ust10y'].mean():+.3f}%")
print(f"  Normal weeks (n={len(normal)}): avg dspread = {normal['d_spread'].mean():+.2f}bp, "
      f"avg d2Y = {normal['d_ust2y'].mean():+.3f}%, avg d10Y = {normal['d_ust10y'].mean():+.3f}%")

# Asymmetry: regress oil on each leg separately
s2, i2, r2, p2, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_ust2y"])
s10, i10, r10, p10, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_ust10y"])
print(f"\n  Oil -> 2Y yield beta:  {s2:.4f} (p={p2:.4f})")
print(f"  Oil -> 10Y yield beta: {s10:.4f} (p={p10:.4f})")
print(f"  -> 10Y is {abs(s10/s2) if s2 != 0 else float('inf'):.1f}x more sensitive to oil than 2Y")


# ─────────────────────────────────────────────────────────
# ANALYSIS 2: Term Premium Decomposition
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 2: Term Premium vs Rate Expectations -> 2s10s Spread")
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

print(f"\nRegression: d(2s10s) = {betas[0]:.3f} + {betas[1]:.3f} x d(rate_exp) + {betas[2]:.3f} x d(term_prem)")
print(f"  beta(rate_exp):   {betas[1]:+.3f}  (t={t_stats[1]:+.2f})")
print(f"  beta(term_prem):  {betas[2]:+.3f}  (t={t_stats[2]:+.2f})")
print(f"  R2 = {r2_multi:.4f}")
print(f"  -> Term premium increases steepen the curve by {betas[2]:.1f}bp per 1bp TP rise")
if betas[2] > 0 and abs(t_stats[2]) > 2:
    print(f"  SUPPORTS THESIS: Rising term premium is a statistically significant steepener")

# VIF for rate expectations and term premium
vif_data = np.column_stack([d_daily["d_rate_exp"].values, d_daily["d_acm"].values])
vif_rate_exp = variance_inflation_factor(np.column_stack([np.ones(len(vif_data)), vif_data]), 1)
vif_tp = variance_inflation_factor(np.column_stack([np.ones(len(vif_data)), vif_data]), 2)
print(f"\n  Variance Inflation Factors:")
print(f"    VIF(rate_exp):   {vif_rate_exp:.2f}")
print(f"    VIF(term_prem):  {vif_tp:.2f}")
if max(vif_rate_exp, vif_tp) < 5:
    print(f"    -> VIF < 5: no concerning multicollinearity")
else:
    print(f"    -> WARNING: VIF >= 5 suggests multicollinearity concern")

# Rolling 252-day window regression: beta(term premium) over time
rolling_window = 252
rolling_beta_tp = []
rolling_dates = []
for i in range(rolling_window, len(d_daily)):
    window = d_daily.iloc[i - rolling_window:i]
    X_roll = np.column_stack([np.ones(rolling_window), window["d_rate_exp"].values, window["d_acm"].values])
    y_roll = window["d_spread"].values
    try:
        b_roll, _, _, _ = lstsq(X_roll, y_roll, rcond=None)
        rolling_beta_tp.append(b_roll[2])
        rolling_dates.append(d_daily.index[i])
    except Exception:
        pass

rolling_beta_tp = np.array(rolling_beta_tp)
rolling_dates = pd.DatetimeIndex(rolling_dates)

print(f"\n  Rolling 252-day beta(term_prem):")
print(f"    Full-sample:  {betas[2]:+.3f}")
print(f"    Rolling mean: {rolling_beta_tp.mean():+.3f}")
print(f"    Rolling min:  {rolling_beta_tp.min():+.3f}")
print(f"    Rolling max:  {rolling_beta_tp.max():+.3f}")

# Rolling 90-day correlation: term premium vs spread
roll_corr_tp = d_daily["d_acm"].rolling(90).corr(d_daily["d_spread"])
roll_corr_re = d_daily["d_rate_exp"].rolling(90).corr(d_daily["d_spread"])


# ─────────────────────────────────────────────────────────
# ANALYSIS 3: Breakeven Inflation Divergence
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 3: Breakeven Inflation Divergence -- Oil -> Transitory?")
print("="*65)

# Breakeven slope: 10Y BE - 2Y BE
daily["be_slope"] = daily["be10y"] - daily["be2y"]

# Regress each breakeven on oil (weekly)
s_be2, _, r_be2, p_be2, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be2y"])
s_be10, _, r_be10, p_be10, _ = stats.linregress(wk_chg["oil_pct"], wk_chg["d_be10y"])

print(f"\nOil sensitivity of breakeven inflation (weekly):")
print(f"  Oil -> 2Y breakeven beta:  {s_be2:.4f} (R2={r_be2**2:.4f}, p={p_be2:.4f})")
print(f"  Oil -> 10Y breakeven beta: {s_be10:.4f} (R2={r_be10**2:.4f}, p={p_be10:.4f})")
print(f"  Ratio: 2Y is {abs(s_be2/s_be10) if s_be10 != 0 else float('inf'):.1f}x more sensitive to oil")

# During oil spikes
spike_be2 = spikes["d_be2y"].mean()
spike_be10 = spikes["d_be10y"].mean()
print(f"\nDuring oil spike weeks (>{spike_thresh}%):")
print(f"  Avg d(2Y BE):  {spike_be2:+.4f}%")
print(f"  Avg d(10Y BE): {spike_be10:+.4f}%")
print(f"  -> Short-end inflation expectations move {abs(spike_be2/spike_be10) if spike_be10 != 0 else float('inf'):.1f}x more")

# Current breakeven slope
current_be_slope = daily["be_slope"].iloc[-1]
be_slope_pctile = stats.percentileofscore(daily["be_slope"].dropna(), current_be_slope)
print(f"\nCurrent breakeven slope (10Y BE - 2Y BE): {current_be_slope:.3f}%")
print(f"  Historical percentile: {be_slope_pctile:.0f}th")
if current_be_slope < 0:
    print(f"  SUPPORTS THESIS: Negative slope = market prices oil inflation as transitory")
    print(f"    Short-end inflation expectations elevated vs long-end -> Fed has cover to cut")

# Breakeven slope persistence event study
print(f"\n  Breakeven Slope Persistence Event Study:")
weekly_be_slope = daily["be_slope"].resample("W-FRI").last().dropna()
spike_dates = spikes.index
horizons_be = [1, 2, 4, 8, 12, 16]
be_slope_paths = {h: [] for h in horizons_be}

for sd in spike_dates:
    # Find nearest weekly be_slope index
    idx_loc = weekly_be_slope.index.searchsorted(sd)
    if idx_loc >= len(weekly_be_slope):
        continue
    base_val = weekly_be_slope.iloc[idx_loc] if idx_loc < len(weekly_be_slope) else np.nan
    for h in horizons_be:
        target_idx = idx_loc + h
        if target_idx < len(weekly_be_slope):
            be_slope_paths[h].append(weekly_be_slope.iloc[target_idx])

print(f"  {'Weeks':>6s}  {'Median BE Slope':>15s}  {'IQR Low':>10s}  {'IQR High':>10s}  {'N':>4s}")
print(f"  {'-'*6}  {'-'*15}  {'-'*10}  {'-'*10}  {'-'*4}")
be_slope_medians = []
be_slope_q25 = []
be_slope_q75 = []
for h in horizons_be:
    arr = np.array(be_slope_paths[h])
    if len(arr) > 0:
        med = np.median(arr)
        q25 = np.percentile(arr, 25)
        q75 = np.percentile(arr, 75)
        be_slope_medians.append(med)
        be_slope_q25.append(q25)
        be_slope_q75.append(q75)
        print(f"  +{h:>4d}w  {med:>15.4f}%  {q25:>10.4f}%  {q75:>10.4f}%  {len(arr):>4d}")
    else:
        be_slope_medians.append(np.nan)
        be_slope_q25.append(np.nan)
        be_slope_q75.append(np.nan)

# Check if slope stays negative for 8+ weeks
stays_negative_8w = all(m < 0 for m in be_slope_medians[:4] if not np.isnan(m))  # horizons 1,2,4,8
print(f"\n  Does median BE slope stay negative for 8+ weeks after oil spikes? {'YES' if stays_negative_8w else 'NO'}")
print(f"\n  THESIS BREAK: If breakeven slope reverts positive within 4 weeks, the transitory")
print(f"  inflation argument weakens and the steepener loses a key structural support.")


# ─────────────────────────────────────────────────────────
# ANALYSIS 4: Oil Regime Spread Outcomes
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 4: Oil Regime Spread Outcomes (Permutation-Tested)")
print("="*65)

# Rolling 3-month (63 trading days) oil move
daily["oil_3m_pct"] = daily["oil"].pct_change(63) * 100

# Z-score normalize spread levels
spread_mean = daily["spread"].mean()
spread_std = daily["spread"].std()
daily["spread_z"] = (daily["spread"] - spread_mean) / spread_std

thresholds = [15, 20, 25, 30]
outcome_horizons = [21, 63, 126]  # 1-month, 3-month, 6-month in trading days
horizon_labels = ["1-month", "3-month", "6-month"]

print(f"\n  Spread z-score normalization: mean={spread_mean:.1f}bp, std={spread_std:.1f}bp")

regime_results = {}
for thresh in thresholds:
    shock_mask = daily["oil_3m_pct"] > thresh
    shock_entries = daily.index[shock_mask]
    # Thin entries: require at least 21 days between events
    if len(shock_entries) == 0:
        continue
    thinned = [shock_entries[0]]
    for dt in shock_entries[1:]:
        if (dt - thinned[-1]).days >= 21:
            thinned.append(dt)
    thinned = pd.DatetimeIndex(thinned)

    outcomes = {h: [] for h in outcome_horizons}
    for entry_date in thinned:
        entry_loc = daily.index.get_loc(entry_date)
        entry_z = daily["spread_z"].iloc[entry_loc]
        for h in outcome_horizons:
            target_loc = entry_loc + h
            if target_loc < len(daily):
                outcome_z = daily["spread_z"].iloc[target_loc]
                outcomes[h].append(outcome_z - entry_z)

    # Permutation test (10,000 iterations)
    n_perm = 10000
    observed_means = {h: np.mean(outcomes[h]) if outcomes[h] else np.nan for h in outcome_horizons}
    perm_pvals = {}
    rng = np.random.RandomState(42)
    for h in outcome_horizons:
        if not outcomes[h] or np.isnan(observed_means[h]):
            perm_pvals[h] = np.nan
            continue
        # Pool of all possible h-day spread changes
        all_changes = (daily["spread_z"].shift(-h) - daily["spread_z"]).dropna().values
        obs_mean = observed_means[h]
        n_events = len(outcomes[h])
        count_extreme = 0
        for _ in range(n_perm):
            perm_sample = rng.choice(all_changes, size=n_events, replace=True)
            if abs(np.mean(perm_sample)) >= abs(obs_mean):
                count_extreme += 1
        perm_pvals[h] = count_extreme / n_perm

    regime_results[thresh] = {
        "n_events": len(thinned),
        "outcomes": outcomes,
        "observed_means": observed_means,
        "perm_pvals": perm_pvals,
    }

# Report results for each threshold
for thresh in thresholds:
    if thresh not in regime_results:
        print(f"\n  Threshold {thresh}%: No shock episodes found")
        continue
    res = regime_results[thresh]
    print(f"\n  Threshold: {thresh}% rolling 3-month oil move  (n={res['n_events']} episodes)")
    print(f"    {'Horizon':>10s}  {'Mean dSpread(z)':>16s}  {'Perm p-value':>13s}")
    print(f"    {'-'*10}  {'-'*16}  {'-'*13}")
    for i, h in enumerate(outcome_horizons):
        obs = res["observed_means"][h]
        pp = res["perm_pvals"][h]
        if not np.isnan(obs):
            print(f"    {horizon_labels[i]:>10s}  {obs:>+16.4f}  {pp:>13.4f}")
        else:
            print(f"    {horizon_labels[i]:>10s}  {'N/A':>16s}  {'N/A':>13s}")

# Threshold sensitivity summary
print(f"\n  Threshold Sensitivity (3-month spread outcome, z-score change):")
print(f"    {'Thresh':>6s}  {'N events':>8s}  {'Mean dZ':>10s}  {'Perm p':>8s}")
print(f"    {'-'*6}  {'-'*8}  {'-'*10}  {'-'*8}")
for thresh in thresholds:
    if thresh in regime_results:
        res = regime_results[thresh]
        obs = res["observed_means"].get(63, np.nan)
        pp = res["perm_pvals"].get(63, np.nan)
        print(f"    {thresh:>5d}%  {res['n_events']:>8d}  {obs:>+10.4f}  {pp:>8.4f}")


# ─────────────────────────────────────────────────────────
# ANALYSIS 5: Carry & Scenario P&L
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 5: Carry & Scenario P&L (DV01-Neutral Steepener)")
print("="*65)

# Current yields
current_2y = daily["ust2y"].iloc[-1]
current_10y = daily["ust10y"].iloc[-1]
current_spread = daily["spread"].iloc[-1]

# Daily carry cost: (2Y yield - 10Y yield) / 360
# In a steepener you are short 2Y (paying 2Y yield) and long 10Y (receiving 10Y yield)
# Net carry = 10Y yield - 2Y yield (negative when curve is inverted or flat with 2Y > 10Y)
daily_carry_bp = (current_10y - current_2y) / 360 * 100  # convert % to bp then per day
# Actually: carry cost per day in bp for DV01-neutral
# Short 2Y: pay 2Y coupon, Long 10Y: receive 10Y coupon
# Net carry = (10Y - 2Y) / 360 in percentage, * 100 for bp
daily_carry_bp = (current_10y - current_2y) * 100 / 360  # bp per day

entry_spread = 50  # bp -- trade entry assumption
stop_spread = 42   # bp -- stop loss
target_spread = 70  # bp -- target

# Days from entry to stop from carry alone
carry_drag_to_stop = abs(entry_spread - stop_spread) / abs(daily_carry_bp) if daily_carry_bp != 0 else float('inf')

# Rolldown estimate (approximate): shift along the curve
# 2Y bond rolls to ~1.75Y in 90 days, 10Y rolls to ~9.75Y
# Simplified: rolldown for 2Y ~ slope of 1-2Y curve, for 10Y ~ slope of 9-10Y curve
# We approximate rolldown as a fraction of the spread per quarter
rolldown_2y_90d = 0  # negligible for short leg (you lose from rolldown on the short)
rolldown_10y_90d = 0  # approximate, actual depends on curve shape

print(f"\n  Current yields:  2Y = {current_2y:.3f}%,  10Y = {current_10y:.3f}%")
print(f"  Current spread:  {current_spread:.1f}bp")
print(f"  Daily carry (DV01-neutral): {daily_carry_bp:+.4f}bp/day")
print(f"  Monthly carry: {daily_carry_bp * 30:+.2f}bp/month")

if daily_carry_bp < 0:
    print(f"  Days from entry ({entry_spread}bp) to stop ({stop_spread}bp) from carry alone: {carry_drag_to_stop:.0f} days")
else:
    print(f"  Carry is positive ({daily_carry_bp:+.4f}bp/day) -- helps the trade")

# Scenario P&L table
scenario_spreads = [42, 46, 54, 60, 70]
holding_days = [30, 60, 90]
scenario_labels = ["42bp (stop)", "46bp", "54bp (unch)", "60bp", "70bp (target)"]

print(f"\n  Scenario P&L Table (entry at {entry_spread}bp, carry = {daily_carry_bp:+.4f}bp/day):")
header = f"  {'Spread Outcome':>16s}"
for d in holding_days:
    header += f"  {d:>4d}d P&L"
print(header)
print(f"  {'-'*16}" + f"  {'-'*9}" * len(holding_days))

for i, s in enumerate(scenario_spreads):
    spread_pnl = s - entry_spread  # bp from spread move
    row = f"  {scenario_labels[i]:>16s}"
    for d in holding_days:
        total_pnl = spread_pnl + daily_carry_bp * d
        row += f"  {total_pnl:>+8.1f}bp"
    print(row)

# Max holding period before carry exceeds target profit
target_profit = target_spread - entry_spread  # bp
if daily_carry_bp < 0:
    max_hold = abs(target_profit) / abs(daily_carry_bp)
    print(f"\n  Max holding period before carry ({daily_carry_bp:+.2f}bp/day) exceeds target profit ({target_profit:+.0f}bp): {max_hold:.0f} days")
else:
    print(f"\n  Carry is positive -- no max holding period constraint from carry")


# ─────────────────────────────────────────────────────────
# ANALYSIS 6: 2Y Mean Reversion After Oil Spikes
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ANALYSIS 6: 2Y Yield Mean Reversion After Oil Spikes")
print("="*65)

# Use weekly data: oil spike weeks (>5% weekly)
horizons_6 = [1, 2, 4, 8, 12]
reversion_data = {h: [] for h in horizons_6}
spike_week_2y_changes = []

for sd in spike_dates:
    idx_loc = weekly.index.searchsorted(sd)
    if idx_loc >= len(weekly) or idx_loc == 0:
        continue
    # 2Y yield change in spike week
    spike_2y_chg = weekly["ust2y"].iloc[idx_loc] - weekly["ust2y"].iloc[idx_loc - 1]
    if np.isnan(spike_2y_chg) or spike_2y_chg == 0:
        continue
    spike_week_2y_changes.append(spike_2y_chg)
    # Track cumulative 2Y change at each horizon (relative to spike week end level)
    base_2y = weekly["ust2y"].iloc[idx_loc]
    for h in horizons_6:
        target_idx = idx_loc + h
        if target_idx < len(weekly):
            cum_chg = weekly["ust2y"].iloc[target_idx] - base_2y
            # % of spike-week move reversed
            pct_reversed = -cum_chg / spike_2y_chg * 100  # negative cum_chg means reversal
            reversion_data[h].append(pct_reversed)

print(f"\n  Oil spike weeks analyzed: {len(spike_week_2y_changes)}")
print(f"  Median spike-week 2Y yield change: {np.median(spike_week_2y_changes):+.3f}%")

print(f"\n  {'Weeks':>6s}  {'Median % Reversed':>18s}  {'IQR Low':>10s}  {'IQR High':>10s}  {'N':>4s}")
print(f"  {'-'*6}  {'-'*18}  {'-'*10}  {'-'*10}  {'-'*4}")

reversion_medians = []
reversion_q25 = []
reversion_q75 = []
for h in horizons_6:
    arr = np.array(reversion_data[h])
    if len(arr) > 0:
        med = np.median(arr)
        q25 = np.percentile(arr, 25)
        q75 = np.percentile(arr, 75)
        reversion_medians.append(med)
        reversion_q25.append(q25)
        reversion_q75.append(q75)
        print(f"  +{h:>4d}w  {med:>+18.1f}%  {q25:>+10.1f}%  {q75:>+10.1f}%  {len(arr):>4d}")
    else:
        reversion_medians.append(np.nan)
        reversion_q25.append(np.nan)
        reversion_q75.append(np.nan)

# Does 2Y give back 50%+ within 8 weeks?
gives_back_50 = False
for i, h in enumerate(horizons_6):
    if h <= 8 and len(reversion_data[h]) > 0 and reversion_medians[i] >= 50:
        gives_back_50 = True
        print(f"\n  YES: 2Y gives back 50%+ of spike-week move by week +{h} (median {reversion_medians[i]:+.1f}%)")
        break
if not gives_back_50:
    # Check the 8-week horizon specifically
    idx_8w = horizons_6.index(8) if 8 in horizons_6 else -1
    if idx_8w >= 0 and len(reversion_data[8]) > 0:
        print(f"\n  NO: Median reversion at +8 weeks is {reversion_medians[idx_8w]:+.1f}% (below 50% threshold)")
    else:
        print(f"\n  Insufficient data to determine 8-week reversion")


# ─────────────────────────────────────────────────────────
# FIGURE
# ─────────────────────────────────────────────────────────
print("\nGenerating charts...")

fig, axes = plt.subplots(6, 2, figsize=(16, 36))
fig.suptitle("US 2s10s Steepener -- Quantitative Thesis Support", fontsize=16, fontweight="bold", y=0.99)

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
ax.set_title("Analysis 1a: Oil Shocks -> Curve Steepening", fontweight="bold")
ax.text(0.05, 0.95, f"beta = {slope1:.2f} bp per 1% oil\nR2 = {r1**2:.3f}  (OLS p={p1:.4f}, HAC p={hac_pval:.4f})\n"
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
bars1 = ax.bar(x_pos - width, spread_means, width, label="d 2s10s Spread (bp)", color="#2ecc71")
bars2 = ax.bar(x_pos, y2_means, width, label="d 2Y Yield (bp)", color="#3498db")
bars3 = ax.bar(x_pos + width, y10_means, width, label="d 10Y Yield (bp)", color="#e74c3c")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xticks(x_pos)
ax.set_xticklabels(categories)
ax.set_ylabel("Average Weekly Change (bp)")
ax.set_title("Analysis 1b: Regime Analysis -- Oil Spikes vs Normal", fontweight="bold")
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

# ── Panel 2b: Rolling correlation + rolling beta(TP) ──
ax = axes[1, 1]
ax.plot(roll_corr_tp.index, roll_corr_tp, color="#e74c3c", linewidth=1, alpha=0.6, label="Corr(d TP, d Spread)")
ax.plot(roll_corr_re.index, roll_corr_re, color="#3498db", linewidth=1, alpha=0.6, label="Corr(d Rate Exp, d Spread)")
ax2b = ax.twinx()
ax2b.plot(rolling_dates, rolling_beta_tp, color="#2ecc71", linewidth=1.5, label="Rolling beta(TP) [RHS]")
ax2b.axhline(betas[2], color="#2ecc71", linewidth=1, linestyle="--", alpha=0.5)
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_ylabel("90-Day Rolling Correlation")
ax2b.set_ylabel("Rolling 252-day beta(Term Premium)", color="#2ecc71")
ax.set_title("Analysis 2b: TP vs Rate Exp Drivers + Rolling Beta", fontweight="bold")
lines_2b1, labels_2b1 = ax.get_legend_handles_labels()
lines_2b2, labels_2b2 = ax2b.get_legend_handles_labels()
ax.legend(lines_2b1 + lines_2b2, labels_2b1 + labels_2b2, loc="lower left", fontsize=7)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.05, 0.95, f"VIF(rate_exp)={vif_rate_exp:.1f}, VIF(TP)={vif_tp:.1f}\n"
        f"Full-sample beta(TP)={betas[2]:+.2f}, Rolling mean={rolling_beta_tp.mean():+.2f}",
        transform=ax.transAxes, va="top", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 3a: Oil vs breakeven slope time series ──
ax = axes[2, 0]
ax_3a2 = ax.twinx()
ax.plot(daily.index, daily["oil"], color="#e67e22", linewidth=1, alpha=0.7, label="WTI Crude (LHS)")
ax_3a2.plot(daily.index, daily["be_slope"], color="#8e44ad", linewidth=1.5, label="BE Slope: 10Y-2Y (RHS)")
ax_3a2.axhline(0, color="#8e44ad", linewidth=0.5, linestyle="--")
ax.set_ylabel("Oil Price ($/bbl)", color="#e67e22")
ax_3a2.set_ylabel("Breakeven Slope: 10Y BE - 2Y BE (%)", color="#8e44ad")
ax.set_title("Analysis 3a: Oil Price vs Breakeven Inflation Slope", fontweight="bold")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax_3a2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
ax.text(0.05, 0.05, f"Current BE slope: {current_be_slope:.3f}% ({be_slope_pctile:.0f}th pctile)\n"
        f"Negative = market sees oil inflation as transitory",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 3b: Breakeven slope persistence event study ──
ax = axes[2, 1]
ax.plot(horizons_be, be_slope_medians, color="#8e44ad", linewidth=2, marker="o", label="Median BE Slope")
ax.fill_between(horizons_be, be_slope_q25, be_slope_q75, alpha=0.3, color="#8e44ad", label="IQR")
ax.axhline(0, color="gray", linewidth=1, linestyle="--")
ax.set_xlabel("Weeks After Oil Spike")
ax.set_ylabel("Breakeven Slope (10Y BE - 2Y BE, %)")
ax.set_title("Analysis 3b: BE Slope Persistence After Oil Spikes", fontweight="bold")
ax.legend(fontsize=8)
ax.text(0.05, 0.95, f"n={len(spike_dates)} oil spike events\n"
        f"Stays negative 8+ weeks: {'YES' if stays_negative_8w else 'NO'}",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 4a: Regime spread outcomes by threshold ──
ax = axes[3, 0]
thresh_colors = {15: "#3498db", 20: "#e74c3c", 25: "#2ecc71", 30: "#e67e22"}
for thresh in thresholds:
    if thresh not in regime_results:
        continue
    res = regime_results[thresh]
    means = [res["observed_means"].get(h, np.nan) for h in outcome_horizons]
    ax.plot([1, 3, 6], means, marker="o", linewidth=2, color=thresh_colors[thresh],
            label=f"{thresh}% thresh (n={res['n_events']})")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Months After Oil Shock Entry")
ax.set_ylabel("Spread Change (z-score)")
ax.set_title("Analysis 4a: Oil Regime Spread Outcomes", fontweight="bold")
ax.legend(fontsize=8)
ax.set_xticks([1, 3, 6])

# ── Panel 4b: Permutation p-values ──
ax = axes[3, 1]
bar_width = 0.18
for j, thresh in enumerate(thresholds):
    if thresh not in regime_results:
        continue
    res = regime_results[thresh]
    pvals = [res["perm_pvals"].get(h, np.nan) for h in outcome_horizons]
    positions = np.arange(len(outcome_horizons)) + j * bar_width
    ax.bar(positions, pvals, bar_width, label=f"{thresh}% thresh", color=thresh_colors[thresh], alpha=0.8)
ax.axhline(0.05, color="red", linewidth=1, linestyle="--", label="p=0.05")
ax.axhline(0.10, color="orange", linewidth=1, linestyle="--", label="p=0.10")
ax.set_xticks(np.arange(len(outcome_horizons)) + bar_width * 1.5)
ax.set_xticklabels(horizon_labels)
ax.set_ylabel("Permutation p-value")
ax.set_title("Analysis 4b: Permutation Test p-values", fontweight="bold")
ax.legend(fontsize=7)

# ── Panel 5a: Scenario P&L heatmap ──
ax = axes[4, 0]
pnl_matrix = np.zeros((len(scenario_spreads), len(holding_days)))
for i, s in enumerate(scenario_spreads):
    spread_pnl = s - entry_spread
    for j, d in enumerate(holding_days):
        pnl_matrix[i, j] = spread_pnl + daily_carry_bp * d

im = ax.imshow(pnl_matrix, cmap="RdYlGn", aspect="auto", vmin=pnl_matrix.min(), vmax=pnl_matrix.max())
ax.set_xticks(range(len(holding_days)))
ax.set_xticklabels([f"{d}d" for d in holding_days])
ax.set_yticks(range(len(scenario_spreads)))
ax.set_yticklabels(scenario_labels)
ax.set_xlabel("Holding Period")
ax.set_ylabel("Spread Outcome")
ax.set_title("Analysis 5: Scenario P&L (bp, incl. carry)", fontweight="bold")
for i in range(len(scenario_spreads)):
    for j in range(len(holding_days)):
        ax.text(j, i, f"{pnl_matrix[i,j]:+.1f}", ha="center", va="center", fontsize=9,
                color="white" if abs(pnl_matrix[i,j]) > 10 else "black", fontweight="bold")
fig.colorbar(im, ax=ax, shrink=0.8, label="P&L (bp)")

# ── Panel 5b: Carry drag over time ──
ax = axes[4, 1]
days_range = np.arange(1, 181)
carry_cum = daily_carry_bp * days_range
ax.plot(days_range, carry_cum, color="#e74c3c", linewidth=2, label="Cumulative Carry")
ax.axhline(target_profit, color="#2ecc71", linewidth=1, linestyle="--", label=f"Target P&L ({target_profit:+.0f}bp)")
ax.axhline(-(entry_spread - stop_spread), color="#e74c3c", linewidth=1, linestyle="--", label=f"Stop Loss ({-(entry_spread - stop_spread):+.0f}bp)")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Holding Period (days)")
ax.set_ylabel("Cumulative Carry (bp)")
ax.set_title("Analysis 5b: Carry Drag Over Time", fontweight="bold")
ax.legend(fontsize=8)
ax.text(0.05, 0.95, f"Daily carry: {daily_carry_bp:+.4f}bp\n"
        f"30d: {daily_carry_bp*30:+.2f}bp, 90d: {daily_carry_bp*90:+.2f}bp",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 6a: 2Y Mean Reversion Event Study ──
ax = axes[5, 0]
ax.plot(horizons_6, reversion_medians, color="#3498db", linewidth=2, marker="o", label="Median % Reversed")
ax.fill_between(horizons_6, reversion_q25, reversion_q75, alpha=0.3, color="#3498db", label="IQR")
ax.axhline(50, color="red", linewidth=1, linestyle="--", label="50% reversal threshold")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Weeks After Oil Spike")
ax.set_ylabel("% of Spike-Week 2Y Move Reversed")
ax.set_title("Analysis 6a: 2Y Yield Mean Reversion After Oil Spikes", fontweight="bold")
ax.legend(fontsize=8)
ax.text(0.05, 0.05, f"n={len(spike_week_2y_changes)} spike events\n"
        f"Median spike-week 2Y chg: {np.median(spike_week_2y_changes):+.3f}%\n"
        f"50%+ reversal by 8w: {'YES' if gives_back_50 else 'NO'}",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# ── Panel 6b: Scatter of oil vs 2Y BE and 10Y BE (original Panel 3b) ──
ax = axes[5, 1]
ax.scatter(wk_chg["oil_pct"], wk_chg["d_be2y"], alpha=0.5, s=20, color="#e74c3c", label="2Y Breakeven", edgecolors="none")
ax.scatter(wk_chg["oil_pct"], wk_chg["d_be10y"], alpha=0.5, s=20, color="#3498db", label="10Y Breakeven", edgecolors="none")
x_line = np.linspace(wk_chg["oil_pct"].min(), wk_chg["oil_pct"].max(), 100)
ax.plot(x_line, s_be2 * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.plot(x_line, s_be10 * x_line, color="#3498db", linewidth=2, linestyle="--")
ax.axhline(0, color="gray", linewidth=0.5)
ax.axvline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Weekly Oil Price Change (%)")
ax.set_ylabel("Weekly Breakeven Change (%)")
ax.set_title("Analysis 3c: Oil Sensitivity -- 2Y vs 10Y Breakevens", fontweight="bold")
ax.legend(fontsize=8)
ratio_text = f"2Y BE beta = {s_be2:.4f} (p={p_be2:.4f})\n10Y BE beta = {s_be10:.4f} (p={p_be10:.4f})\n"
ratio_text += f"-> 2Y is {abs(s_be2/s_be10):.1f}x more sensitive" if s_be10 != 0 else ""
ax.text(0.05, 0.95, ratio_text,
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig("../output/analysis_results.png", dpi=150, bbox_inches="tight")
print(f"\nCharts saved to ../output/analysis_results.png")


# ─────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("SUMMARY: QUANTITATIVE SUPPORT FOR STEEPENER THESIS")
print("="*65)
print(f"""
1. OIL-CURVE ASYMMETRY
   - Oil spikes steepen the curve: beta = {slope1:.2f}bp per 1% oil move (OLS p={p1:.4f}, HAC p={hac_pval:.4f})
   - During spike weeks: spread widens {spikes['d_spread'].mean():+.1f}bp on average
   - 10Y yield {abs(s10/s2) if s2 != 0 else float('inf'):.1f}x more sensitive to oil than 2Y

2. TERM PREMIUM DECOMPOSITION
   - Last 6M: {tp_move/y10_move*100 if y10_move else 0:+.0f}% of 10Y move is term premium (structural)
   - Rising TP steepens the curve: beta = {betas[2]:+.2f}bp (t={t_stats[2]:+.1f})
   - VIF(rate_exp)={vif_rate_exp:.1f}, VIF(TP)={vif_tp:.1f} -- {'no multicollinearity concern' if max(vif_rate_exp, vif_tp) < 5 else 'multicollinearity detected'}
   - Rolling beta(TP): mean={rolling_beta_tp.mean():+.2f}, min={rolling_beta_tp.min():+.2f}, max={rolling_beta_tp.max():+.2f}

3. BREAKEVEN DIVERGENCE
   - 2Y breakeven is {abs(s_be2/s_be10) if s_be10 != 0 else float('inf'):.1f}x more sensitive to oil than 10Y
   - Current BE slope: {current_be_slope:.3f}% ({be_slope_pctile:.0f}th percentile)
   - Market is pricing oil inflation as {'TRANSITORY' if current_be_slope < 0 else 'persistent'}
   - BE slope stays negative 8+ weeks after spikes: {'YES' if stays_negative_8w else 'NO'}

4. OIL REGIME SPREAD OUTCOMES
   - Permutation-tested regime analysis across {len(thresholds)} thresholds
   - Default 20% threshold: n={regime_results.get(20, {}).get('n_events', 'N/A')} episodes

5. CARRY & SCENARIO P&L
   - Daily carry: {daily_carry_bp:+.4f}bp/day ({daily_carry_bp*30:+.2f}bp/month)
   - Entry {entry_spread}bp -> Target {target_spread}bp (SL {stop_spread}bp)

6. 2Y MEAN REVERSION
   - 50%+ reversal within 8 weeks: {'YES' if gives_back_50 else 'NO'}
   - Median spike-week 2Y change: {np.median(spike_week_2y_changes):+.3f}%

TRADE: Entry {daily['spread'].iloc[-1]:.0f}bp -> Target 70bp (SL 42bp)
""")
