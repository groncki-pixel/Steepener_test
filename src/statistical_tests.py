"""
Steepener Trade Thesis — Statistical Tests
============================================
Eight robustness tests for the steepener analysis:

TIER 1 (Core diagnostics):
  1. Newey-West HAC standard errors on all regressions
  2. Stationarity tests (ADF + KPSS) on all series
  3. VIF on Analysis 2 regressors
  4. Ljung-Box autocorrelation on all regression residuals

TIER 2 (Robustness):
  5. Rolling 252-day betas (Analysis 2)
  6. Bootstrap confidence intervals (Analysis 2)
  7. Permutation test on oil regimes (Analysis 4)
  8. Oil threshold sensitivity (Analysis 4)

Output: console tables + rolling_betas.png + permutation_test.png
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from numpy.linalg import lstsq
import warnings
warnings.filterwarnings("ignore")

# statsmodels imports
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.regression.linear_model import OLS

DATA_FILE = "../data/data_steepener.xlsx"

# ─────────────────────────────────────────────────────────
# DATA LOADING (same pattern as analysis.py)
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

# Build aligned daily dataframe
daily = pd.DataFrame({
    "oil": cl1, "ust2y": ust2y, "ust10y": ust10y,
    "be2y": be2y, "be10y": be10y, "spread": spread, "acm": acm
}).dropna()

# Weekly data
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

# Daily changes
daily["rate_exp"] = daily["ust10y"] - daily["acm"]
d_daily = pd.DataFrame({
    "d_spread":   daily["spread"].diff(),
    "d_acm":      daily["acm"].diff(),
    "d_rate_exp": daily["ust10y"].diff() - daily["acm"].diff(),
    "d_oil_pct":  daily["oil"].pct_change() * 100,
    "d_be2y":     daily["be2y"].diff(),
    "d_be10y":    daily["be10y"].diff(),
}).dropna()

print(f"Sample: {daily.index[0].date()} to {daily.index[-1].date()}")
print(f"  Daily obs:  {len(daily)}")
print(f"  Weekly obs: {len(wk_chg)}")


# ═════════════════════════════════════════════════════════
#  TIER 1 TESTS
# ═════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────
# TEST 1: Newey-West HAC Standard Errors
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 1: Newey-West HAC Standard Errors on All Regressions")
print("=" * 75)

def run_ols_with_hac(y, X, reg_name):
    """Run OLS and compute both standard and Newey-West HAC standard errors.
    X should NOT include a constant — it will be added here.
    Returns dict with results.
    """
    X_const = sm.add_constant(X)
    model = OLS(y, X_const).fit()
    # HAC with automatic bandwidth (Newey-West 1994)
    nobs = len(y)
    # Automatic bandwidth: floor(4*(T/100)^(2/9))
    auto_lag = int(np.floor(4 * (nobs / 100) ** (2 / 9)))
    model_hac = OLS(y, X_const).fit(cov_type="HAC",
                                     cov_kwds={"maxlags": auto_lag})
    n_params = len(model.params)
    param_names = ["const"] + [f"x{j+1}" for j in range(n_params - 1)]
    return {
        "name": reg_name,
        "params": np.asarray(model.params),
        "se_ols": np.asarray(model.bse),
        "pval_ols": np.asarray(model.pvalues),
        "se_hac": np.asarray(model_hac.bse),
        "pval_hac": np.asarray(model_hac.pvalues),
        "param_names": param_names,
        "nobs": nobs,
        "auto_lag": auto_lag,
        "resid": np.asarray(model.resid),
    }

# Analysis 1 regressions
# 1a: Oil → spread (weekly)
res1a = run_ols_with_hac(wk_chg["d_spread"].values,
                         wk_chg[["oil_pct"]].values,
                         "A1a: Oil% -> d(Spread) [weekly]")

# 1b: Oil → 2Y yield (weekly)
res1b = run_ols_with_hac(wk_chg["d_ust2y"].values,
                         wk_chg[["oil_pct"]].values,
                         "A1b: Oil% -> d(2Y) [weekly]")

# 1c: Oil → 10Y yield (weekly)
res1c = run_ols_with_hac(wk_chg["d_ust10y"].values,
                         wk_chg[["oil_pct"]].values,
                         "A1c: Oil% -> d(10Y) [weekly]")

# Analysis 2: Multivariate — d(spread) = b0 + b1*d(rate_exp) + b2*d(acm)
res2 = run_ols_with_hac(d_daily["d_spread"].values,
                        d_daily[["d_rate_exp", "d_acm"]].values,
                        "A2: d(RateExp)+d(TP) -> d(Spread) [daily]")

# Analysis 3 regressions
# 3a: Oil → 2Y BE (weekly)
res3a = run_ols_with_hac(wk_chg["d_be2y"].values,
                         wk_chg[["oil_pct"]].values,
                         "A3a: Oil% -> d(2Y BE) [weekly]")

# 3b: Oil → 10Y BE (weekly)
res3b = run_ols_with_hac(wk_chg["d_be10y"].values,
                         wk_chg[["oil_pct"]].values,
                         "A3b: Oil% -> d(10Y BE) [weekly]")

all_regs = [res1a, res1b, res1c, res2, res3a, res3b]

print(f"\nAutomatic bandwidth: Newey-West (1994) formula: floor(4*(T/100)^(2/9))")
print(f"{'Regression':<45} {'Coef':<8} {'OLS SE':<10} {'HAC SE':<10} "
      f"{'OLS p':<10} {'HAC p':<10} {'HAC lag':>7}")
print("-" * 140)

for reg in all_regs:
    for i, pname in enumerate(reg["param_names"]):
        if pname == "const":
            coef_label = "const"
        elif i == 1:
            coef_label = "x1"
        else:
            coef_label = f"x{i}"
        label = f"{reg['name']} [{coef_label}]" if len(reg["param_names"]) > 2 else f"{reg['name']}"
        if pname == "const" and len(reg["param_names"]) <= 2:
            continue  # skip const for simple regressions to reduce clutter
        if pname == "const":
            continue
        print(f"{label:<45} {reg['params'][i]:+.5f} "
              f"{reg['se_ols'][i]:<10.5f} {reg['se_hac'][i]:<10.5f} "
              f"{reg['pval_ols'][i]:<10.4f} {reg['pval_hac'][i]:<10.4f} "
              f"{reg['auto_lag']:>7d}")

print("\nKey: If HAC SE > OLS SE, standard errors were underestimated (autocorrelation present).")
print("     If HAC p-value still < 0.05, result is robust to autocorrelation correction.")


# ─────────────────────────────────────────────────────────
# TEST 2: Stationarity — ADF + KPSS
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 2: Stationarity Tests (ADF + KPSS)")
print("=" * 75)

series_dict = {
    "Spread (2s10s)":   daily["spread"],
    "ACM Term Premium": daily["acm"],
    "Rate Expectations": daily["rate_exp"],
    "2Y Breakeven":     daily["be2y"],
    "10Y Breakeven":    daily["be10y"],
    "Oil (WTI)":        daily["oil"],
    "2Y Yield":         daily["ust2y"],
    "10Y Yield":        daily["ust10y"],
}

def stationarity_conclusion(adf_pval, kpss_pval):
    """Determine I(0)/I(1)/ambiguous from ADF and KPSS p-values."""
    adf_reject = adf_pval < 0.05       # ADF H0: unit root → reject = stationary
    kpss_reject = kpss_pval < 0.05     # KPSS H0: stationary → reject = non-stationary
    if adf_reject and not kpss_reject:
        return "I(0) - Stationary"
    elif not adf_reject and kpss_reject:
        return "I(1) - Non-stationary"
    elif adf_reject and kpss_reject:
        return "Ambiguous (both reject)"
    else:
        return "Ambiguous (neither rejects)"

print(f"\n{'Series':<22} {'Level':<6} {'ADF p':<10} {'KPSS p':<10} {'Conclusion':<28} | "
      f"{'1st Diff':<6} {'ADF p':<10} {'KPSS p':<10} {'Conclusion':<28}")
print("-" * 150)

for name, s in series_dict.items():
    s_clean = s.dropna()

    # Levels
    adf_stat, adf_p, *_ = adfuller(s_clean, autolag="AIC")
    kpss_stat, kpss_p, *_ = kpss(s_clean, regression="c", nlags="auto")
    concl_level = stationarity_conclusion(adf_p, kpss_p)

    # First differences
    s_diff = s_clean.diff().dropna()
    adf_stat_d, adf_p_d, *_ = adfuller(s_diff, autolag="AIC")
    kpss_stat_d, kpss_p_d, *_ = kpss(s_diff, regression="c", nlags="auto")
    concl_diff = stationarity_conclusion(adf_p_d, kpss_p_d)

    print(f"{name:<22} {'Level':<6} {adf_p:<10.4f} {kpss_p:<10.4f} {concl_level:<28} | "
          f"{'Diff':<6} {adf_p_d:<10.4f} {kpss_p_d:<10.4f} {concl_diff:<28}")

print("\nNote: ADF H0 = unit root (reject → stationary). KPSS H0 = stationary (reject → non-stationary).")
print("      Regressions use first differences, so I(1) in levels is acceptable if I(0) in differences.")


# ─────────────────────────────────────────────────────────
# TEST 3: VIF on Analysis 2
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 3: Variance Inflation Factor (VIF) — Analysis 2 Regressors")
print("=" * 75)

X_a2 = d_daily[["d_rate_exp", "d_acm"]].values
X_a2_const = sm.add_constant(X_a2)

vif_rate_exp = variance_inflation_factor(X_a2_const, 1)
vif_term_prem = variance_inflation_factor(X_a2_const, 2)

print(f"\n  VIF(d_rate_expectations): {vif_rate_exp:.3f}")
print(f"  VIF(d_term_premium):     {vif_term_prem:.3f}")
print()
if max(vif_rate_exp, vif_term_prem) < 5:
    print("  Interpretation: VIF < 5 for both regressors — no multicollinearity concern.")
elif max(vif_rate_exp, vif_term_prem) < 10:
    print("  Interpretation: VIF between 5 and 10 — moderate multicollinearity, monitor.")
else:
    print("  Interpretation: VIF >= 10 — severe multicollinearity, results may be unreliable.")

corr_re_tp = d_daily["d_rate_exp"].corr(d_daily["d_acm"])
print(f"  Correlation(d_rate_exp, d_acm): {corr_re_tp:.4f}")


# ─────────────────────────────────────────────────────────
# TEST 4: Ljung-Box on All Regression Residuals
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 4: Ljung-Box Test for Autocorrelation in Residuals")
print("=" * 75)

def get_residuals(y, X, name):
    """Fit OLS, return residuals."""
    X_const = sm.add_constant(X)
    model = OLS(y, X_const).fit()
    return model.resid, name

residual_sets = [
    get_residuals(wk_chg["d_spread"].values, wk_chg[["oil_pct"]].values,
                  "A1a: Oil% -> d(Spread)"),
    get_residuals(wk_chg["d_ust2y"].values, wk_chg[["oil_pct"]].values,
                  "A1b: Oil% -> d(2Y)"),
    get_residuals(wk_chg["d_ust10y"].values, wk_chg[["oil_pct"]].values,
                  "A1c: Oil% -> d(10Y)"),
    get_residuals(d_daily["d_spread"].values, d_daily[["d_rate_exp", "d_acm"]].values,
                  "A2: d(RE)+d(TP) -> d(Spread)"),
    get_residuals(wk_chg["d_be2y"].values, wk_chg[["oil_pct"]].values,
                  "A3a: Oil% -> d(2Y BE)"),
    get_residuals(wk_chg["d_be10y"].values, wk_chg[["oil_pct"]].values,
                  "A3b: Oil% -> d(10Y BE)"),
]

lags_to_test = [5, 10, 20]

print(f"\n{'Regression':<35}", end="")
for lag in lags_to_test:
    print(f"  {'Lag ' + str(lag) + ' LB stat':>14} {'p-value':>10}", end="")
print()
print("-" * 115)

for resid, name in residual_sets:
    print(f"{name:<35}", end="")
    for lag in lags_to_test:
        lb_result = acorr_ljungbox(resid, lags=[lag], return_df=True)
        lb_stat = lb_result["lb_stat"].values[0]
        lb_pval = lb_result["lb_pvalue"].values[0]
        flag = " *" if lb_pval < 0.05 else "  "
        print(f"  {lb_stat:>14.3f} {lb_pval:>9.4f}{flag}", end="")
    print()

print("\n  * = significant at 5% (autocorrelation detected — HAC correction warranted)")
print("  If most regressions show significant LB stats, Test 1's HAC corrections are essential.")


# ═════════════════════════════════════════════════════════
#  TIER 2 TESTS
# ═════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────
# TEST 5: Rolling 252-Day Betas (Analysis 2)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 5: Rolling 252-Day Betas — Analysis 2")
print("=" * 75)

window = 252
y_roll = d_daily["d_spread"].values
X_roll = d_daily[["d_rate_exp", "d_acm"]].values
dates_roll = d_daily.index

beta_re_list = []
beta_tp_list = []
date_list = []

for i in range(window, len(y_roll)):
    y_w = y_roll[i - window:i]
    X_w = X_roll[i - window:i]
    X_w_c = sm.add_constant(X_w)
    try:
        b, _, _, _ = lstsq(X_w_c, y_w, rcond=None)
        beta_re_list.append(b[1])
        beta_tp_list.append(b[2])
        date_list.append(dates_roll[i])
    except Exception:
        continue

beta_re_arr = np.array(beta_re_list)
beta_tp_arr = np.array(beta_tp_list)

# Full-sample betas for reference
X_full_c = sm.add_constant(X_roll)
b_full, _, _, _ = lstsq(X_full_c, y_roll, rcond=None)

print(f"\n  Window: {window} trading days (~1 year)")
print(f"  Rolling windows computed: {len(beta_re_list)}")
print(f"\n  {'Statistic':<25} {'beta(Rate Exp)':<20} {'beta(Term Prem)':<20}")
print(f"  {'-'*65}")
print(f"  {'Full-sample':<25} {b_full[1]:+.4f}{'':>14} {b_full[2]:+.4f}")
print(f"  {'Rolling mean':<25} {beta_re_arr.mean():+.4f}{'':>14} {beta_tp_arr.mean():+.4f}")
print(f"  {'Rolling std':<25} {beta_re_arr.std():.4f}{'':>15} {beta_tp_arr.std():.4f}")
print(f"  {'Rolling min':<25} {beta_re_arr.min():+.4f}{'':>14} {beta_tp_arr.min():+.4f}")
print(f"  {'Rolling max':<25} {beta_re_arr.max():+.4f}{'':>14} {beta_tp_arr.max():+.4f}")

# Plot
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(date_list, beta_tp_arr, color="#e74c3c", linewidth=1.5, label="beta(Term Premium)")
ax.plot(date_list, beta_re_arr, color="#3498db", linewidth=1.5, label="beta(Rate Expectations)")
ax.axhline(b_full[2], color="#e74c3c", linestyle="--", linewidth=1, alpha=0.5, label=f"Full-sample TP beta: {b_full[2]:.3f}")
ax.axhline(b_full[1], color="#3498db", linestyle="--", linewidth=1, alpha=0.5, label=f"Full-sample RE beta: {b_full[1]:.3f}")
ax.axhline(0, color="gray", linewidth=0.5)
ax.set_xlabel("Date")
ax.set_ylabel("Rolling Beta Coefficient")
ax.set_title("Rolling 252-Day Regression Betas: d(Spread) = b0 + b1*d(Rate Exp) + b2*d(Term Premium)", fontweight="bold")
ax.legend(loc="best", fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("../output/rolling_betas.png", dpi=150, bbox_inches="tight")
print(f"\n  Chart saved to ../output/rolling_betas.png")


# ─────────────────────────────────────────────────────────
# TEST 6: Bootstrap Confidence Intervals
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 6: Bootstrap Confidence Intervals (10,000 resamples)")
print("=" * 75)

n_boot = 10000
np.random.seed(42)

y_a2 = d_daily["d_spread"].values
X_a2_raw = d_daily[["d_rate_exp", "d_acm"]].values
n_obs = len(y_a2)

# Also need BE data for ratio
be2y_wk = wk_chg["d_be2y"].values
be10y_wk = wk_chg["d_be10y"].values
oil_wk = wk_chg["oil_pct"].values
n_wk = len(oil_wk)

# Full-sample point estimates
X_a2_c = sm.add_constant(X_a2_raw)
b_fs, _, _, _ = lstsq(X_a2_c, y_a2, rcond=None)
y_hat_fs = X_a2_c @ b_fs
ss_res_fs = np.sum((y_a2 - y_hat_fs) ** 2)
ss_tot_fs = np.sum((y_a2 - y_a2.mean()) ** 2)
r2_fs = 1 - ss_res_fs / ss_tot_fs

# BE ratio (from weekly oil regressions)
s_be2_fs, _, _, _, _ = stats.linregress(oil_wk, be2y_wk)
s_be10_fs, _, _, _, _ = stats.linregress(oil_wk, be10y_wk)
be_ratio_fs = s_be2_fs / s_be10_fs if s_be10_fs != 0 else float("inf")

boot_beta_tp = np.empty(n_boot)
boot_beta_re = np.empty(n_boot)
boot_r2 = np.empty(n_boot)
boot_be_ratio = np.empty(n_boot)

for b in range(n_boot):
    # Bootstrap daily data for Analysis 2
    idx_d = np.random.randint(0, n_obs, size=n_obs)
    y_b = y_a2[idx_d]
    X_b = X_a2_raw[idx_d]
    X_b_c = sm.add_constant(X_b)
    try:
        betas_b, _, _, _ = lstsq(X_b_c, y_b, rcond=None)
        y_hat_b = X_b_c @ betas_b
        ss_res_b = np.sum((y_b - y_hat_b) ** 2)
        ss_tot_b = np.sum((y_b - y_b.mean()) ** 2)
        boot_beta_re[b] = betas_b[1]
        boot_beta_tp[b] = betas_b[2]
        boot_r2[b] = 1 - ss_res_b / ss_tot_b if ss_tot_b != 0 else 0
    except Exception:
        boot_beta_re[b] = np.nan
        boot_beta_tp[b] = np.nan
        boot_r2[b] = np.nan

    # Bootstrap weekly data for BE ratio
    idx_w = np.random.randint(0, n_wk, size=n_wk)
    oil_b = oil_wk[idx_w]
    be2_b = be2y_wk[idx_w]
    be10_b = be10y_wk[idx_w]
    s2_b, _, _, _, _ = stats.linregress(oil_b, be2_b)
    s10_b, _, _, _, _ = stats.linregress(oil_b, be10_b)
    boot_be_ratio[b] = s2_b / s10_b if abs(s10_b) > 1e-10 else np.nan

print(f"\n  {'Statistic':<30} {'Point Est':>12} {'5th Pctile':>12} {'95th Pctile':>12}")
print(f"  {'-'*68}")

for name, point, boots in [
    ("beta(Term Premium)", b_fs[2], boot_beta_tp),
    ("beta(Rate Expectations)", b_fs[1], boot_beta_re),
    ("2Y/10Y BE Oil Sensitivity", be_ratio_fs, boot_be_ratio),
    ("R-squared (Analysis 2)", r2_fs, boot_r2),
]:
    b_clean = boots[~np.isnan(boots)]
    p5 = np.percentile(b_clean, 5)
    p95 = np.percentile(b_clean, 95)
    print(f"  {name:<30} {point:>12.4f} {p5:>12.4f} {p95:>12.4f}")

print(f"\n  Resamples: {n_boot:,} | Confidence level: 90% (5th to 95th percentile)")
print("  If zero is NOT in the interval, the estimate is significant at the 10% level.")


# ─────────────────────────────────────────────────────────
# TEST 7: Permutation Test — Oil Regime Analysis (Analysis 4)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 7: Permutation Test — Oil Shock Regime (Analysis 4)")
print("=" * 75)

# Define oil shock regime: >20% rolling 3-month (~63 trading day) WTI move
oil_roll_3m = daily["oil"].pct_change(periods=63) * 100
spread_fwd = daily["spread"].shift(-63) - daily["spread"]  # forward 3-month spread change

# Align and drop NAs
regime_df = pd.DataFrame({
    "oil_3m_pct": oil_roll_3m,
    "spread_fwd": spread_fwd,
}).dropna()

shock_threshold = 20.0
regime_df["oil_shock"] = (regime_df["oil_3m_pct"].abs() > shock_threshold).astype(int)

shock_mask = regime_df["oil_shock"] == 1
normal_mask = regime_df["oil_shock"] == 0

actual_shock_mean = regime_df.loc[shock_mask, "spread_fwd"].mean()
actual_normal_mean = regime_df.loc[normal_mask, "spread_fwd"].mean()
actual_gap = actual_shock_mean - actual_normal_mean

print(f"\n  Oil shock definition: |rolling 3-month WTI move| > {shock_threshold}%")
print(f"  Shock days:  {shock_mask.sum():>6d}  |  Mean fwd 3M spread change: {actual_shock_mean:+.3f}bp")
print(f"  Normal days: {normal_mask.sum():>6d}  |  Mean fwd 3M spread change: {actual_normal_mean:+.3f}bp")
print(f"  Actual gap (shock - normal): {actual_gap:+.3f}bp")

# Permutation test
n_perm = 10000
np.random.seed(123)
labels = regime_df["oil_shock"].values.copy()
outcomes = regime_df["spread_fwd"].values
n_shock = int(labels.sum())
perm_gaps = np.empty(n_perm)

for i in range(n_perm):
    perm_labels = np.random.permutation(labels)
    shock_mean = outcomes[perm_labels == 1].mean()
    normal_mean = outcomes[perm_labels == 0].mean()
    perm_gaps[i] = shock_mean - normal_mean

# Two-sided p-value
perm_pval = np.mean(np.abs(perm_gaps) >= np.abs(actual_gap))

print(f"\n  Permutation test ({n_perm:,} shuffles):")
print(f"  p-value (two-sided): {perm_pval:.4f}")
if perm_pval < 0.05:
    print("  Result: SIGNIFICANT — the spread outcome difference between oil shock and normal")
    print("          regimes is unlikely due to chance.")
else:
    print("  Result: NOT significant at 5% — cannot reject that the gap is due to chance.")

# Histogram
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(perm_gaps, bins=80, color="#bdc3c7", edgecolor="white", alpha=0.8, label="Permutation distribution")
ax.axvline(actual_gap, color="#e74c3c", linewidth=2.5, linestyle="--",
           label=f"Actual gap: {actual_gap:+.2f}bp")
ax.axvline(-abs(actual_gap), color="#e74c3c", linewidth=1.5, linestyle=":", alpha=0.5)
ax.axvline(abs(actual_gap), color="#e74c3c", linewidth=1.5, linestyle=":", alpha=0.5)
ax.set_xlabel("Mean Spread Change Gap (Shock - Normal, bp)")
ax.set_ylabel("Frequency")
ax.set_title(f"Permutation Test: Oil Shock vs Normal Regime Spread Outcome\n"
             f"p-value = {perm_pval:.4f} ({n_perm:,} permutations)", fontweight="bold")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("../output/permutation_test.png", dpi=150, bbox_inches="tight")
print(f"  Histogram saved to ../output/permutation_test.png")


# ─────────────────────────────────────────────────────────
# TEST 8: Oil Threshold Sensitivity (Analysis 4)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("TEST 8: Oil Threshold Sensitivity — Regime Definition Robustness")
print("=" * 75)

thresholds = [15, 20, 25, 30]
windows_months = {"1-month": 21, "3-month": 63, "6-month": 126}

print(f"\n  Mean forward spread change (bp) during oil shock regime")
print(f"  (shock = |rolling N-day WTI move| > threshold)")
print(f"\n  {'Threshold':<12}", end="")
for wname in windows_months:
    print(f"  {wname + ' shock':>16} {'n_shock':>8} {wname + ' normal':>16} {'n_normal':>8} {'gap':>10}", end="")
print()
print(f"  {'-' * 182}")

for thresh in thresholds:
    print(f"  {thresh:>3d}%{'':>8}", end="")
    for wname, wdays in windows_months.items():
        oil_roll = daily["oil"].pct_change(periods=wdays) * 100
        spread_fwd_w = daily["spread"].shift(-wdays) - daily["spread"]
        df_temp = pd.DataFrame({"oil_roll": oil_roll, "spread_fwd": spread_fwd_w}).dropna()
        shock_m = df_temp["oil_roll"].abs() > thresh
        normal_m = ~shock_m

        if shock_m.sum() > 0:
            s_mean = df_temp.loc[shock_m, "spread_fwd"].mean()
            n_mean = df_temp.loc[normal_m, "spread_fwd"].mean()
            gap = s_mean - n_mean
            print(f"  {s_mean:>+16.2f} {shock_m.sum():>8d} {n_mean:>+16.2f} {normal_m.sum():>8d} {gap:>+10.2f}", end="")
        else:
            print(f"  {'N/A':>16} {'0':>8} {'N/A':>16} {'N/A':>8} {'N/A':>10}", end="")
    print()

print(f"\n  Interpretation: Consistent sign of the gap across thresholds/windows strengthens")
print(f"  the oil regime effect. Larger gaps at higher thresholds suggest a dose-response relationship.")


# ─────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 75)
print("STATISTICAL TESTS COMPLETE")
print("=" * 75)
print("""
Files produced:
  - rolling_betas.png     (Test 5: rolling coefficient stability)
  - permutation_test.png  (Test 7: permutation distribution)

Key questions answered:
  1. HAC SEs: Are regressions robust to autocorrelation?
  2. Stationarity: Are we regressing stationary series?
  3. VIF: Is multicollinearity biasing Analysis 2?
  4. Ljung-Box: How much autocorrelation is in the residuals?
  5. Rolling betas: Are the relationships stable over time?
  6. Bootstrap CIs: Are point estimates statistically robust?
  7. Permutation: Is the oil regime effect real or noise?
  8. Sensitivity: Does the regime result depend on threshold choice?
""")


# ═════════════════════════════════════════════════════════
# WRITE RESULTS FILE
# ═════════════════════════════════════════════════════════
results_path = "../output/statistical_tests_results.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 75 + "\n")
    f.write("STATISTICAL TESTS RESULTS (T1-T8)\n")
    f.write("=" * 75 + "\n\n")

    # T1: HAC SEs
    f.write("T1: Newey-West HAC Standard Errors\n")
    f.write(f"{'Regression':<45} {'Coef':>8} {'OLS SE':>10} {'HAC SE':>10} {'OLS p':>10} {'HAC p':>10}\n")
    f.write("-" * 95 + "\n")
    for reg in all_regs:
        for i, pname in enumerate(reg["param_names"]):
            if pname == "const":
                continue
            label = f"{reg['name']} [x{i}]" if len(reg["param_names"]) > 2 else reg["name"]
            f.write(f"{label:<45} {reg['params'][i]:>+8.4f} {reg['se_ols'][i]:>10.4f} {reg['se_hac'][i]:>10.4f} "
                    f"{reg['pval_ols'][i]:>10.4f} {reg['pval_hac'][i]:>10.4f}\n")
    f.write("\n")

    # T2: Stationarity
    f.write("T2: Stationarity (ADF + KPSS)\n")
    f.write(f"{'Series':<22} {'ADF p (lvl)':>12} {'KPSS p (lvl)':>13} {'Verdict (lvl)':<28} {'ADF p (diff)':>13} {'Verdict (diff)':<28}\n")
    f.write("-" * 120 + "\n")
    for name, s in series_dict.items():
        s_clean = s.dropna()
        adf_p = adfuller(s_clean, autolag="AIC")[1]
        kpss_p = kpss(s_clean, regression="c", nlags="auto")[1]
        concl_level = stationarity_conclusion(adf_p, kpss_p)
        s_diff = s_clean.diff().dropna()
        adf_p_d = adfuller(s_diff, autolag="AIC")[1]
        kpss_p_d = kpss(s_diff, regression="c", nlags="auto")[1]
        concl_diff = stationarity_conclusion(adf_p_d, kpss_p_d)
        f.write(f"{name:<22} {adf_p:>12.4f} {kpss_p:>13.4f} {concl_level:<28} {adf_p_d:>13.4f} {concl_diff:<28}\n")
    f.write("\n")

    # T3: VIF
    f.write("T3: VIF on Analysis 2\n")
    f.write(f"  VIF(rate_exp):   {vif_rate_exp:.3f}\n")
    f.write(f"  VIF(term_prem):  {vif_term_prem:.3f}\n")
    f.write(f"  Correlation:     {corr_re_tp:.4f}\n\n")

    # T4: Ljung-Box
    f.write("T4: Ljung-Box Autocorrelation\n")
    f.write(f"{'Regression':<35}")
    for lag in lags_to_test:
        f.write(f" {'LB('+str(lag)+') p':>10}")
    f.write("\n" + "-" * 60 + "\n")
    for resid, name in residual_sets:
        f.write(f"{name:<35}")
        for lag in lags_to_test:
            lb_result = acorr_ljungbox(resid, lags=[lag], return_df=True)
            lb_pval = lb_result["lb_pvalue"].values[0]
            f.write(f" {lb_pval:>10.4f}")
        f.write("\n")
    f.write("\n")

    # T5: Rolling Betas
    f.write("T5: Rolling 252-Day Betas (Analysis 2)\n")
    f.write(f"  {'Stat':<20} {'beta(RateExp)':>14} {'beta(TermPrem)':>15}\n")
    f.write(f"  {'Full-sample':<20} {b_full[1]:>+14.4f} {b_full[2]:>+15.4f}\n")
    f.write(f"  {'Rolling mean':<20} {beta_re_arr.mean():>+14.4f} {beta_tp_arr.mean():>+15.4f}\n")
    f.write(f"  {'Rolling std':<20} {beta_re_arr.std():>14.4f} {beta_tp_arr.std():>15.4f}\n")
    f.write(f"  {'Rolling min':<20} {beta_re_arr.min():>+14.4f} {beta_tp_arr.min():>+15.4f}\n")
    f.write(f"  {'Rolling max':<20} {beta_re_arr.max():>+14.4f} {beta_tp_arr.max():>+15.4f}\n")
    pct_pos_tp = np.mean(beta_tp_arr > 0) * 100
    f.write(f"  % positive beta(TP): {pct_pos_tp:.0f}%\n\n")

    # T6: Bootstrap CIs
    f.write("T6: Bootstrap Confidence Intervals (90%)\n")
    f.write(f"  {'Statistic':<30} {'Point Est':>12} {'5th Pctile':>12} {'95th Pctile':>12}\n")
    f.write("  " + "-" * 68 + "\n")
    for name_bs, point, boots in [
        ("beta(Term Premium)", b_fs[2], boot_beta_tp),
        ("beta(Rate Expectations)", b_fs[1], boot_beta_re),
        ("2Y/10Y BE Oil Sensitivity", be_ratio_fs, boot_be_ratio),
        ("R-squared (Analysis 2)", r2_fs, boot_r2),
    ]:
        b_clean = boots[~np.isnan(boots)]
        p5 = np.percentile(b_clean, 5)
        p95 = np.percentile(b_clean, 95)
        f.write(f"  {name_bs:<30} {point:>12.4f} {p5:>12.4f} {p95:>12.4f}\n")
    f.write("\n")

    # T7: Permutation Test
    f.write("T7: Permutation Test (Oil Regime)\n")
    f.write(f"  Shock mean: {actual_shock_mean:+.3f}bp\n")
    f.write(f"  Normal mean: {actual_normal_mean:+.3f}bp\n")
    f.write(f"  Gap: {actual_gap:+.3f}bp\n")
    f.write(f"  p-value: {perm_pval:.4f}\n\n")

    # T8: Threshold Sensitivity
    f.write("T8: Threshold Sensitivity\n")
    f.write(f"  {'Thresh':>6} {'Window':>8}")
    f.write(f" {'Shock Mean':>12} {'Normal Mean':>12} {'Gap':>10}\n")
    f.write("  " + "-" * 50 + "\n")
    for thresh in thresholds:
        for wname, wdays in windows_months.items():
            oil_roll = daily["oil"].pct_change(periods=wdays) * 100
            spread_fwd_w = daily["spread"].shift(-wdays) - daily["spread"]
            df_temp = pd.DataFrame({"oil_roll": oil_roll, "spread_fwd": spread_fwd_w}).dropna()
            shock_m = df_temp["oil_roll"].abs() > thresh
            if shock_m.sum() > 0:
                s_mean = df_temp.loc[shock_m, "spread_fwd"].mean()
                n_mean = df_temp.loc[~shock_m, "spread_fwd"].mean()
                gap = s_mean - n_mean
                f.write(f"  {thresh:>5d}% {wname:>8} {s_mean:>+12.2f} {n_mean:>+12.2f} {gap:>+10.2f}\n")

print(f"Results written to {results_path}")
