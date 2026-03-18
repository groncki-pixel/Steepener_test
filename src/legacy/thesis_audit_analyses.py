# ═══════════════════════════════════════════════════════════════
# LEGACY FILE — DO NOT USE FOR CURRENT THESIS
# ═══════════════════════════════════════════════════════════════
# This file contains the ORIGINAL analyses from thesis v1.
# After rigorous sniff-testing and statistical audit, the following
# were found to be problematic:
#
# analysis.py:
#   A1 (Oil→Curve): REFRAMED — p=0.80, no relationship. Oil flattens, not steepens.
#   A4 (Regime Study): KILLED — contradicts thesis (flattening at all horizons).
#   A6 (2Y Mean Reversion): KILLED — statistical noise, IQRs span hundreds of %.
#   A2 (Term Premium): KEPT — strongest result, central to Pillar 2.
#   A3 (Breakeven Divergence): KEPT — 2.6x ratio robust, central to Pillar 1.
#   A5 (Carry): KEPT — mechanically correct, needs rebuild for new expression.
#
# statistical_tests.py:
#   All 8 tests remain valid diagnostics. Key findings:
#   - HAC corrections essential (Ljung-Box significant on most regressions)
#   - Bootstrap CI on BE ratio [2.19, 3.15] excludes 1.0 (robust)
#   - Rolling beta(TP) positive 100% of windows (stable)
#
# thesis_audit_analyses.py:
#   A7 (Oil→CPI): KEPT — headline >> core confirmed (~3x ratio in changes)
#   A8 (Taylor Rule): DOWNGRADED — VIF=10.3, horse race useless
#   A10 (Deficit→TP): DOWNGRADED — spurious in levels, wrong sign in changes
#   A11 (Fed BS→TP): KEPT WITH CAVEAT — changes p=0.07, correct direction
#
# See src/ for the new analysis suite and docs/thesis_restructured.md for
# the restructured thesis.
# ═══════════════════════════════════════════════════════════════

"""
Thesis Audit — New Analyses (07, 08, 10, 11)
=============================================
These analyses address gaps identified in the thesis audit:

Analysis 07: Oil → Headline CPI vs Core CPI passthrough regression
Analysis 08: Taylor Rule — does the Fed react to core or headline?
Analysis 10: Federal deficit → ACM term premium regression
Analysis 11: Fed balance sheet (QT) → ACM term premium regression

Output: thesis_audit_results.png (multi-panel figure)
        Console prints regression results
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.stattools import adfuller, kpss, coint
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"
BLOOMBERG_FILE = "../data/data_steepener.xlsx"

# ─────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────

def load_fred_sheet(sheet, file=DATA_FILE):
    """Load a FRED-format sheet (observation_date, value) from xlsx."""
    df = pd.read_excel(file, sheet_name=sheet, header=None)
    # Find header row
    for i, row in df.iterrows():
        vals = row.astype(str).str.lower()
        if vals.str.contains('date').any() or vals.str.contains('observation').any():
            header_row = i
            break
    else:
        header_row = 0
    data = df.iloc[header_row + 1:, :2].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    data = data.dropna().set_index("Date").sort_index()
    return data["Value"]


def load_bloomberg_sheet(sheet, file=DATA_FILE):
    """Load a Bloomberg-format sheet (Date in col 1, value in col 2) from xlsx."""
    df = pd.read_excel(file, sheet_name=sheet, header=None)
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    data = df.iloc[header_row + 1:, 1:3].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    data = data.dropna().set_index("Date").sort_index()
    return data["Value"]


print("Loading data...")

# New FRED data
cpi_index = load_fred_sheet("CPIAUCSL")          # Headline CPI index
core_pce_index = load_fred_sheet("PCEPILFE")      # Core PCE price index
headline_pce_index = load_fred_sheet("PCEPI")     # Headline PCE price index
unemployment = load_fred_sheet("UNRATE")           # Unemployment rate
deficit = load_fred_sheet("MTSDS133FMS")           # Monthly federal deficit ($M)

# Bloomberg data from same file
oil = load_bloomberg_sheet("CL1")
acm = load_bloomberg_sheet("ACM 10yr premium")
fed_bs = load_bloomberg_sheet("FED Balance sheet")
fed_funds = load_bloomberg_sheet("Fed Funds Rate")
core_cpi_yoy = load_bloomberg_sheet("US Core CPI")  # Already YoY

# Compute YoY changes
cpi_yoy = cpi_index.pct_change(12) * 100  # 12-month % change
core_pce_yoy = core_pce_index.pct_change(12) * 100
headline_pce_yoy = headline_pce_index.pct_change(12) * 100

# Oil monthly (use end-of-month, then shift index to start-of-month for alignment)
oil_monthly = oil.resample("ME").last()
oil_monthly.index = oil_monthly.index.to_period("M").to_timestamp()
oil_yoy = oil_monthly.pct_change(12) * 100

# ACM monthly
acm_monthly = acm.resample("ME").last()
acm_monthly.index = acm_monthly.index.to_period("M").to_timestamp()

# Fed balance sheet monthly
fed_bs_monthly = fed_bs.resample("ME").last()
fed_bs_monthly.index = fed_bs_monthly.index.to_period("M").to_timestamp()

# Fed funds monthly
fed_funds_monthly = fed_funds.resample("ME").last()
fed_funds_monthly.index = fed_funds_monthly.index.to_period("M").to_timestamp()

# Also normalize FRED series indices to start-of-month
cpi_index.index = cpi_index.index.to_period("M").to_timestamp()
core_pce_index.index = core_pce_index.index.to_period("M").to_timestamp()
headline_pce_index.index = headline_pce_index.index.to_period("M").to_timestamp()
unemployment.index = unemployment.index.to_period("M").to_timestamp()
deficit.index = deficit.index.to_period("M").to_timestamp()
core_cpi_yoy.index = core_cpi_yoy.index.to_period("M").to_timestamp()

print(f"CPI index: {cpi_index.index[0].date()} to {cpi_index.index[-1].date()} ({len(cpi_index)} obs)")
print(f"Core PCE index: {core_pce_index.index[0].date()} to {core_pce_index.index[-1].date()} ({len(core_pce_index)} obs)")
print(f"Headline PCE index: {headline_pce_index.index[0].date()} to {headline_pce_index.index[-1].date()} ({len(headline_pce_index)} obs)")
print(f"Unemployment: {unemployment.index[0].date()} to {unemployment.index[-1].date()} ({len(unemployment)} obs)")
print(f"Deficit: {deficit.index[0].date()} to {deficit.index[-1].date()} ({len(deficit)} obs)")
print(f"Oil (CL1): {oil.index[0].date()} to {oil.index[-1].date()} ({len(oil)} obs)")
print(f"ACM TP: {acm.index[0].date()} to {acm.index[-1].date()} ({len(acm)} obs)")
print(f"Fed BS: {fed_bs.index[0].date()} to {fed_bs.index[-1].date()} ({len(fed_bs)} obs)")
print(f"Fed Funds: {fed_funds.index[0].date()} to {fed_funds.index[-1].date()} ({len(fed_funds)} obs)")

# Print latest values for verification
print(f"\n--- Latest Values ---")
print(f"Headline CPI YoY (latest): {cpi_yoy.dropna().iloc[-1]:.2f}%")
print(f"Core PCE YoY (latest): {core_pce_yoy.dropna().iloc[-1]:.2f}%")
print(f"Headline PCE YoY (latest): {headline_pce_yoy.dropna().iloc[-1]:.2f}%")
print(f"Unemployment (latest): {unemployment.iloc[-1]:.1f}%")
print(f"Deficit (latest): ${deficit.iloc[-1]/1000:.1f}B")
print(f"Fed Funds (latest): {fed_funds.iloc[-1]:.2f}%")
print(f"Fed BS (latest): ${fed_bs.iloc[-1]:.0f}B")
print(f"Core CPI YoY (latest, Bloomberg): {core_cpi_yoy.iloc[-1]:.2f}%")


# ═════════════════════════════════════════════════════════
# ANALYSIS 07: Oil → Headline CPI vs Core CPI Passthrough
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("ANALYSIS 07: Oil Price → CPI Passthrough (Headline vs Core)")
print("=" * 75)
print("Tests MS claim: 'every 10% oil increase adds ~35bp to headline CPI but only ~3bp to core CPI'")

# Build monthly aligned dataset
a07 = pd.DataFrame({
    "oil_yoy": oil_yoy,
    "cpi_yoy": cpi_yoy,
    "core_pce_yoy": core_pce_yoy,
    "headline_pce_yoy": headline_pce_yoy,
}).dropna()

# Also compute 3-month oil changes for more granular analysis
oil_3m = oil_monthly.pct_change(3) * 100
cpi_3m_chg = cpi_yoy.diff(3)
core_pce_3m_chg = core_pce_yoy.diff(3)
headline_pce_3m_chg = headline_pce_yoy.diff(3)

a07_3m = pd.DataFrame({
    "oil_3m": oil_3m,
    "d_cpi_yoy": cpi_3m_chg,
    "d_core_pce_yoy": core_pce_3m_chg,
    "d_headline_pce_yoy": headline_pce_3m_chg,
}).dropna()

print(f"\nSample (YoY levels): {a07.index[0].date()} to {a07.index[-1].date()} ({len(a07)} monthly obs)")
print(f"Sample (3M changes): {a07_3m.index[0].date()} to {a07_3m.index[-1].date()} ({len(a07_3m)} monthly obs)")

# Regression 1: Oil YoY → Headline CPI YoY (levels)
X_oil = sm.add_constant(a07["oil_yoy"].values)
y_cpi = a07["cpi_yoy"].values
y_core = a07["core_pce_yoy"].values
y_head_pce = a07["headline_pce_yoy"].values

model_cpi = OLS(y_cpi, X_oil).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
model_core = OLS(y_core, X_oil).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
model_head_pce = OLS(y_head_pce, X_oil).fit(cov_type="HAC", cov_kwds={"maxlags": 6})

print(f"\n--- YoY Level Regressions (monthly) ---")
print(f"{'Dep Var':<25} {'Oil Beta':>10} {'SE(HAC)':>10} {'p-value':>10} {'R2':>8}")
print("-" * 70)
for name, model in [("Headline CPI YoY", model_cpi),
                     ("Core PCE YoY", model_core),
                     ("Headline PCE YoY", model_head_pce)]:
    b = model.params[1]
    se = model.bse[1]
    p = model.pvalues[1]
    r2 = model.rsquared
    print(f"{name:<25} {b:>+10.4f} {se:>10.4f} {p:>10.4f} {r2:>8.4f}")

# Interpretation in terms of "per 10% oil increase"
beta_headline = model_cpi.params[1]
beta_core_pce = model_core.params[1]
beta_headline_pce = model_head_pce.params[1]

print(f"\n--- Passthrough per 10% Oil Price Increase (YoY) ---")
print(f"  Headline CPI:  {beta_headline * 10:+.2f}pp  (i.e., {beta_headline * 10 * 100:+.0f}bp)")
print(f"  Core PCE:      {beta_core_pce * 10:+.2f}pp  (i.e., {beta_core_pce * 10 * 100:+.0f}bp)")
print(f"  Headline PCE:  {beta_headline_pce * 10:+.2f}pp  (i.e., {beta_headline_pce * 10 * 100:+.0f}bp)")
print(f"  Ratio (Headline CPI / Core PCE): {abs(beta_headline / beta_core_pce):.1f}x")

# Now do the 3M change regressions for robustness
X_oil_3m = sm.add_constant(a07_3m["oil_3m"].values)
y_d_cpi = a07_3m["d_cpi_yoy"].values
y_d_core = a07_3m["d_core_pce_yoy"].values
y_d_head = a07_3m["d_headline_pce_yoy"].values

model_d_cpi = OLS(y_d_cpi, X_oil_3m).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
model_d_core = OLS(y_d_core, X_oil_3m).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
model_d_head = OLS(y_d_head, X_oil_3m).fit(cov_type="HAC", cov_kwds={"maxlags": 4})

print(f"\n--- 3-Month Change Regressions (robustness) ---")
print(f"{'Dep Var':<25} {'Oil Beta':>10} {'SE(HAC)':>10} {'p-value':>10} {'R2':>8}")
print("-" * 70)
for name, model in [("d(Headline CPI YoY)", model_d_cpi),
                     ("d(Core PCE YoY)", model_d_core),
                     ("d(Headline PCE YoY)", model_d_head)]:
    b = model.params[1]
    se = model.bse[1]
    p = model.pvalues[1]
    r2 = model.rsquared
    print(f"{name:<25} {b:>+10.4f} {se:>10.4f} {p:>10.4f} {r2:>8.4f}")

beta_d_headline = model_d_cpi.params[1]
beta_d_core = model_d_core.params[1]

print(f"\n  3M passthrough per 10% oil increase:")
print(f"  d(Headline CPI YoY):  {beta_d_headline * 10:+.2f}pp  ({beta_d_headline * 10 * 100:+.0f}bp)")
print(f"  d(Core PCE YoY):      {beta_d_core * 10:+.2f}pp  ({beta_d_core * 10 * 100:+.0f}bp)")
if beta_d_core != 0:
    print(f"  Ratio: {abs(beta_d_headline / beta_d_core):.1f}x")

print(f"\n  MS CLAIM VERDICT: MS says ~35bp headline, ~3bp core per 10% oil increase.")
print(f"  OUR RESULT: {beta_headline * 10 * 100:+.0f}bp headline CPI, {beta_core_pce * 10 * 100:+.0f}bp core PCE per 10% oil (YoY)")
print(f"  The directional claim (headline >> core) is {'CONFIRMED' if abs(beta_headline) > abs(beta_core_pce) * 2 else 'NOT confirmed'}.")
print(f"  The specific magnitudes may differ from MS due to sample period and methodology.")


# ═════════════════════════════════════════════════════════
# ANALYSIS 08: Taylor Rule — Core vs Headline in Fed Reaction
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("ANALYSIS 08: Taylor Rule — Does the Fed React to Core or Headline?")
print("=" * 75)
print("Tests claim F4: 'The Fed has historically prioritized core inflation in its reaction function'")

# Build monthly aligned dataset
a08 = pd.DataFrame({
    "fed_funds": fed_funds_monthly,
    "core_pce_yoy": core_pce_yoy,
    "headline_pce_yoy": headline_pce_yoy,
    "unemployment": unemployment,
}).dropna()

# Compute changes (Taylor rule in changes form)
a08["d_ff"] = a08["fed_funds"].diff()
a08["d_core_pce"] = a08["core_pce_yoy"].diff()
a08["d_headline_pce"] = a08["headline_pce_yoy"].diff()
a08["d_unemployment"] = a08["unemployment"].diff()

# Also add lagged inflation for forward-looking Taylor rule
a08["core_pce_lag1"] = a08["core_pce_yoy"].shift(1)
a08["headline_pce_lag1"] = a08["headline_pce_yoy"].shift(1)
a08["unemp_lag1"] = a08["unemployment"].shift(1)

a08 = a08.dropna()

print(f"\nSample: {a08.index[0].date()} to {a08.index[-1].date()} ({len(a08)} monthly obs)")
print(f"Fed Funds range: {a08['fed_funds'].min():.2f}% to {a08['fed_funds'].max():.2f}%")

# Taylor Rule Level Regression: FF = a + b1*inflation + b2*unemployment
# Model 1: Core PCE only
X1 = sm.add_constant(a08[["core_pce_yoy", "unemployment"]].values)
y_ff = a08["fed_funds"].values
model_core_tr = OLS(y_ff, X1).fit(cov_type="HAC", cov_kwds={"maxlags": 12})

# Model 2: Headline PCE only
X2 = sm.add_constant(a08[["headline_pce_yoy", "unemployment"]].values)
model_head_tr = OLS(y_ff, X2).fit(cov_type="HAC", cov_kwds={"maxlags": 12})

# Model 3: Both core and headline (horse race)
X3 = sm.add_constant(a08[["core_pce_yoy", "headline_pce_yoy", "unemployment"]].values)
model_both_tr = OLS(y_ff, X3).fit(cov_type="HAC", cov_kwds={"maxlags": 12})

print(f"\n--- Taylor Rule: FF = a + b1*Inflation + b2*Unemployment ---")
print(f"\nModel 1 (Core PCE + Unemployment):")
print(f"  beta(Core PCE):     {model_core_tr.params[1]:+.4f}  (t={model_core_tr.tvalues[1]:+.2f}, p={model_core_tr.pvalues[1]:.4f})")
print(f"  beta(Unemployment): {model_core_tr.params[2]:+.4f}  (t={model_core_tr.tvalues[2]:+.2f}, p={model_core_tr.pvalues[2]:.4f})")
print(f"  R2 = {model_core_tr.rsquared:.4f},  AIC = {model_core_tr.aic:.1f}")

print(f"\nModel 2 (Headline PCE + Unemployment):")
print(f"  beta(Headline PCE): {model_head_tr.params[1]:+.4f}  (t={model_head_tr.tvalues[1]:+.2f}, p={model_head_tr.pvalues[1]:.4f})")
print(f"  beta(Unemployment): {model_head_tr.params[2]:+.4f}  (t={model_head_tr.tvalues[2]:+.2f}, p={model_head_tr.pvalues[2]:.4f})")
print(f"  R2 = {model_head_tr.rsquared:.4f},  AIC = {model_head_tr.aic:.1f}")

print(f"\nModel 3 (Horse Race: Core PCE + Headline PCE + Unemployment):")
print(f"  beta(Core PCE):     {model_both_tr.params[1]:+.4f}  (t={model_both_tr.tvalues[1]:+.2f}, p={model_both_tr.pvalues[1]:.4f})")
print(f"  beta(Headline PCE): {model_both_tr.params[2]:+.4f}  (t={model_both_tr.tvalues[2]:+.2f}, p={model_both_tr.pvalues[2]:.4f})")
print(f"  beta(Unemployment): {model_both_tr.params[3]:+.4f}  (t={model_both_tr.tvalues[3]:+.2f}, p={model_both_tr.pvalues[3]:.4f})")
print(f"  R2 = {model_both_tr.rsquared:.4f},  AIC = {model_both_tr.aic:.1f}")

# Changes form (more appropriate for policy changes)
print(f"\n--- Taylor Rule in Changes: d(FF) = a + b1*d(Inflation) + b2*d(Unemployment) ---")

d_y = a08["d_ff"].values
X_d1 = sm.add_constant(a08[["d_core_pce", "d_unemployment"]].values)
X_d2 = sm.add_constant(a08[["d_headline_pce", "d_unemployment"]].values)
X_d3 = sm.add_constant(a08[["d_core_pce", "d_headline_pce", "d_unemployment"]].values)

model_d1 = OLS(d_y, X_d1).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
model_d2 = OLS(d_y, X_d2).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
model_d3 = OLS(d_y, X_d3).fit(cov_type="HAC", cov_kwds={"maxlags": 6})

print(f"\nChanges Model 1 (d(Core PCE) + d(Unemployment)):")
print(f"  beta(d Core PCE):     {model_d1.params[1]:+.4f}  (t={model_d1.tvalues[1]:+.2f}, p={model_d1.pvalues[1]:.4f})")
print(f"  beta(d Unemployment): {model_d1.params[2]:+.4f}  (t={model_d1.tvalues[2]:+.2f}, p={model_d1.pvalues[2]:.4f})")
print(f"  R2 = {model_d1.rsquared:.4f}")

print(f"\nChanges Model 2 (d(Headline PCE) + d(Unemployment)):")
print(f"  beta(d Headline PCE): {model_d2.params[1]:+.4f}  (t={model_d2.tvalues[1]:+.2f}, p={model_d2.pvalues[1]:.4f})")
print(f"  beta(d Unemployment): {model_d2.params[2]:+.4f}  (t={model_d2.tvalues[2]:+.2f}, p={model_d2.pvalues[2]:.4f})")
print(f"  R2 = {model_d2.rsquared:.4f}")

print(f"\nChanges Model 3 (Horse Race):")
print(f"  beta(d Core PCE):     {model_d3.params[1]:+.4f}  (t={model_d3.tvalues[1]:+.2f}, p={model_d3.pvalues[1]:.4f})")
print(f"  beta(d Headline PCE): {model_d3.params[2]:+.4f}  (t={model_d3.tvalues[2]:+.2f}, p={model_d3.pvalues[2]:.4f})")
print(f"  beta(d Unemployment): {model_d3.params[3]:+.4f}  (t={model_d3.tvalues[3]:+.2f}, p={model_d3.pvalues[3]:.4f})")
print(f"  R2 = {model_d3.rsquared:.4f}")

# Verdict
core_sig_levels = model_both_tr.pvalues[1] < 0.05
head_sig_levels = model_both_tr.pvalues[2] < 0.05
core_sig_changes = model_d3.pvalues[1] < 0.05
head_sig_changes = model_d3.pvalues[2] < 0.05

print(f"\n  VERDICT on F4 ('Fed prioritizes core'):")
print(f"  Levels horse race: Core sig={core_sig_levels} (p={model_both_tr.pvalues[1]:.4f}), Headline sig={head_sig_levels} (p={model_both_tr.pvalues[2]:.4f})")
print(f"  Changes horse race: Core sig={core_sig_changes} (p={model_d3.pvalues[1]:.4f}), Headline sig={head_sig_changes} (p={model_d3.pvalues[2]:.4f})")
if core_sig_levels and not head_sig_levels:
    print(f"  CONFIRMED: Core PCE is significant, headline is not → Fed prioritizes core.")
elif core_sig_levels and head_sig_levels:
    print(f"  PARTIALLY CONFIRMED: Both are significant, but compare AIC and coefficients.")
    print(f"  Core-only AIC={model_core_tr.aic:.1f} vs Headline-only AIC={model_head_tr.aic:.1f}")
    print(f"  {'Core model fits better' if model_core_tr.aic < model_head_tr.aic else 'Headline model fits better'}")
else:
    print(f"  NUANCED: Results depend on specification. See detailed output above.")


# ═════════════════════════════════════════════════════════
# ANALYSIS 10: Federal Deficit → ACM Term Premium
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("ANALYSIS 10: Federal Deficit → ACM 10Y Term Premium")
print("=" * 75)
print("Tests claims B1/B2: 'Fiscal deficit expansion pushes term premium higher'")

# Build monthly aligned dataset
a10 = pd.DataFrame({
    "deficit": deficit,
    "acm_tp": acm_monthly,
}).dropna()

# Convert deficit to positive = larger deficit (deficit is negative in data)
a10["deficit_abs"] = -a10["deficit"] / 1000  # Convert to $B, positive = larger deficit

# Rolling 12-month cumulative deficit
a10["deficit_12m"] = a10["deficit"].rolling(12).sum() / 1000  # $B
a10["deficit_12m_abs"] = -a10["deficit_12m"]  # positive = larger deficit

# Changes
a10["d_deficit"] = a10["deficit_abs"].diff()
a10["d_acm"] = a10["acm_tp"].diff()
a10["d_deficit_12m"] = a10["deficit_12m_abs"].diff()

a10_clean = a10.dropna()

print(f"\nSample: {a10_clean.index[0].date()} to {a10_clean.index[-1].date()} ({len(a10_clean)} monthly obs)")
print(f"Latest 12M cumulative deficit: ${a10_clean['deficit_12m_abs'].iloc[-1]:.0f}B")
print(f"Latest monthly deficit: ${a10_clean['deficit_abs'].iloc[-1]:.0f}B")
print(f"Latest ACM TP: {a10_clean['acm_tp'].iloc[-1]:.3f}%")

# Level regression: ACM TP = a + b * 12M deficit
X_def = sm.add_constant(a10_clean["deficit_12m_abs"].values)
y_tp = a10_clean["acm_tp"].values
model_def_level = OLS(y_tp, X_def).fit(cov_type="HAC", cov_kwds={"maxlags": 12})

print(f"\n--- Level Regression: ACM TP = a + b * 12M Cumulative Deficit ---")
print(f"  beta(Deficit 12M): {model_def_level.params[1]:+.6f}  (t={model_def_level.tvalues[1]:+.2f}, p={model_def_level.pvalues[1]:.4f})")
print(f"  R2 = {model_def_level.rsquared:.4f}")
print(f"  Interpretation: A $100B increase in 12M deficit → {model_def_level.params[1] * 100:+.3f}pp change in TP")

# Changes regression: d(ACM TP) = a + b * d(12M deficit)
X_d_def = sm.add_constant(a10_clean["d_deficit_12m"].values)
y_d_tp = a10_clean["d_acm"].values
model_def_change = OLS(y_d_tp, X_d_def).fit(cov_type="HAC", cov_kwds={"maxlags": 6})

print(f"\n--- Changes Regression: d(ACM TP) = a + b * d(12M Deficit) ---")
print(f"  beta(d Deficit): {model_def_change.params[1]:+.6f}  (t={model_def_change.tvalues[1]:+.2f}, p={model_def_change.pvalues[1]:.4f})")
print(f"  R2 = {model_def_change.rsquared:.4f}")

# Correlation
corr_level = a10_clean["deficit_12m_abs"].corr(a10_clean["acm_tp"])
corr_change = a10_clean["d_deficit_12m"].corr(a10_clean["d_acm"])
print(f"\n  Correlation (levels): {corr_level:+.4f}")
print(f"  Correlation (changes): {corr_change:+.4f}")

print(f"\n  VERDICT on B1/B2:")
if model_def_level.pvalues[1] < 0.05 and model_def_level.params[1] > 0:
    print(f"  CONFIRMED: Larger deficits are significantly associated with higher term premium (levels)")
elif model_def_level.pvalues[1] < 0.10 and model_def_level.params[1] > 0:
    print(f"  WEAKLY CONFIRMED: Positive but only marginally significant (p={model_def_level.pvalues[1]:.4f})")
else:
    print(f"  NOT CONFIRMED in levels (p={model_def_level.pvalues[1]:.4f})")

if model_def_change.pvalues[1] < 0.05 and model_def_change.params[1] > 0:
    print(f"  Changes regression also significant (p={model_def_change.pvalues[1]:.4f})")
else:
    print(f"  Changes regression not significant (p={model_def_change.pvalues[1]:.4f})")


# ═════════════════════════════════════════════════════════
# ANALYSIS 11: Fed Balance Sheet (QT) → Term Premium
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("ANALYSIS 11: Fed Balance Sheet → ACM 10Y Term Premium")
print("=" * 75)
print("Tests claim B3: 'QT pressures long-end supply/demand → higher term premium'")

# Build monthly aligned dataset
a11 = pd.DataFrame({
    "fed_bs": fed_bs_monthly,
    "acm_tp": acm_monthly,
}).dropna()

# Changes
a11["d_bs"] = a11["fed_bs"].diff()
a11["d_acm"] = a11["acm_tp"].diff()
# BS change as % of total
a11["d_bs_pct"] = a11["fed_bs"].pct_change() * 100

a11_clean = a11.dropna()

print(f"\nSample: {a11_clean.index[0].date()} to {a11_clean.index[-1].date()} ({len(a11_clean)} monthly obs)")
print(f"Fed BS range: ${a11_clean['fed_bs'].min():.0f}B to ${a11_clean['fed_bs'].max():.0f}B")
print(f"Latest Fed BS: ${a11_clean['fed_bs'].iloc[-1]:.0f}B")
print(f"Latest ACM TP: {a11_clean['acm_tp'].iloc[-1]:.3f}%")

# Level regression: ACM TP = a + b * Fed BS
X_bs = sm.add_constant(a11_clean["fed_bs"].values)
y_tp11 = a11_clean["acm_tp"].values
model_bs_level = OLS(y_tp11, X_bs).fit(cov_type="HAC", cov_kwds={"maxlags": 6})

print(f"\n--- Level Regression: ACM TP = a + b * Fed BS ---")
print(f"  beta(Fed BS): {model_bs_level.params[1]:+.8f}  (t={model_bs_level.tvalues[1]:+.2f}, p={model_bs_level.pvalues[1]:.4f})")
print(f"  R2 = {model_bs_level.rsquared:.4f}")
print(f"  Interpretation: $100B BS reduction → {-model_bs_level.params[1] * 100:+.4f}pp change in TP")

# Changes regression: d(ACM TP) = a + b * d(Fed BS)
X_d_bs = sm.add_constant(a11_clean["d_bs"].values)
y_d_tp11 = a11_clean["d_acm"].values
model_bs_change = OLS(y_d_tp11, X_d_bs).fit(cov_type="HAC", cov_kwds={"maxlags": 4})

print(f"\n--- Changes Regression: d(ACM TP) = a + b * d(Fed BS) ---")
print(f"  beta(d Fed BS): {model_bs_change.params[1]:+.8f}  (t={model_bs_change.tvalues[1]:+.2f}, p={model_bs_change.pvalues[1]:.4f})")
print(f"  R2 = {model_bs_change.rsquared:.4f}")

# Correlation
corr_bs_level = a11_clean["fed_bs"].corr(a11_clean["acm_tp"])
corr_bs_change = a11_clean["d_bs"].corr(a11_clean["d_acm"])
print(f"\n  Correlation (levels): {corr_bs_level:+.4f}")
print(f"  Correlation (changes): {corr_bs_change:+.4f}")

# Expected sign: NEGATIVE — as BS shrinks (QT), TP should rise
# So beta should be negative (lower BS = higher TP)
print(f"\n  Expected sign: beta < 0 (BS shrinks → TP rises)")
print(f"  Actual sign: beta = {model_bs_level.params[1]:+.8f}")

if model_bs_level.params[1] < 0 and model_bs_level.pvalues[1] < 0.05:
    print(f"  CONFIRMED: Smaller BS significantly associated with higher TP")
elif model_bs_level.params[1] < 0 and model_bs_level.pvalues[1] < 0.10:
    print(f"  WEAKLY CONFIRMED: Correct sign but marginal significance (p={model_bs_level.pvalues[1]:.4f})")
elif model_bs_level.params[1] < 0:
    print(f"  DIRECTIONALLY CORRECT but not significant (p={model_bs_level.pvalues[1]:.4f})")
else:
    print(f"  WRONG SIGN or NOT CONFIRMED — BS and TP move in same direction in this sample")
    print(f"  This may reflect the QE-era confound: BS expanded when TP was low (risk-off)")
    print(f"  Consider subsample analysis or controlling for risk sentiment")


# ═════════════════════════════════════════════════════════
# ADDITIONAL: Core PCE vs Core CPI Divergence Chart
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("ADDITIONAL: Core PCE vs Core CPI Divergence (for claim F5)")
print("=" * 75)

# Align core PCE YoY and core CPI YoY
divergence = pd.DataFrame({
    "core_pce_yoy": core_pce_yoy,
    "core_cpi_yoy": core_cpi_yoy,
}).dropna()

print(f"\nLatest Core PCE YoY: {core_pce_yoy.dropna().iloc[-1]:.2f}%")
print(f"Latest Core CPI YoY: {core_cpi_yoy.dropna().iloc[-1]:.2f}%")
print(f"Gap (Core PCE - Core CPI): {core_pce_yoy.dropna().iloc[-1] - core_cpi_yoy.dropna().iloc[-1]:.2f}pp")
print(f"\nF5 CLAIM: 'Core PCE has continued to decline in 2026'")
# Check if core PCE is declining
recent_core_pce = core_pce_yoy.dropna().tail(6)
print(f"Last 6 months of Core PCE YoY:")
for date, val in recent_core_pce.items():
    print(f"  {date.strftime('%Y-%m')}: {val:.2f}%")
trend = "DECLINING" if recent_core_pce.iloc[-1] < recent_core_pce.iloc[0] else "NOT DECLINING"
print(f"Trend: {trend}")


# ═════════════════════════════════════════════════════════
# DIAGNOSTIC SUMMARY (D1-D4)
# ═════════════════════════════════════════════════════════

def stationarity_conclusion(adf_pval, kpss_pval):
    adf_reject = adf_pval < 0.05
    kpss_reject = kpss_pval < 0.05
    if adf_reject and not kpss_reject:
        return "I(0) - Stationary"
    elif not adf_reject and kpss_reject:
        return "I(1) - Non-stationary"
    elif adf_reject and kpss_reject:
        return "Ambiguous (both reject)"
    else:
        return "Ambiguous (neither rejects)"

# ═══ D1: STATIONARITY ON ALL THESIS AUDIT SERIES ═══
print("\n" + "=" * 75)
print("DIAGNOSTIC D1: Stationarity Tests (ADF + KPSS) on Thesis Audit Series")
print("=" * 75)

d1_series = {
    "Oil YoY (%)":          oil_yoy.dropna(),
    "CPI YoY (%)":          cpi_yoy.dropna(),
    "Core PCE YoY (%)":     core_pce_yoy.dropna(),
    "Headline PCE YoY (%)": headline_pce_yoy.dropna(),
    "Fed Funds (%)":        fed_funds_monthly.dropna(),
    "Unemployment (%)":     unemployment.dropna(),
    "Deficit 12M ($B)":     a10_clean["deficit_12m_abs"],
    "ACM TP (%)":           acm_monthly.dropna(),
    "Fed BS ($B)":          fed_bs_monthly.dropna(),
}

d1_results = {}
print(f"\n{'Series':<24} {'ADF p (level)':<14} {'KPSS p (level)':<15} {'Verdict (level)':<28} {'ADF p (diff)':<14} {'Verdict (diff)':<28}")
print("-" * 130)

for name, s in d1_series.items():
    s_clean = s.dropna()
    if len(s_clean) < 20:
        print(f"{name:<24} {'insufficient data'}")
        continue
    adf_p = adfuller(s_clean, autolag="AIC")[1]
    kpss_p = kpss(s_clean, regression="c", nlags="auto")[1]
    concl_level = stationarity_conclusion(adf_p, kpss_p)
    s_diff = s_clean.diff().dropna()
    adf_p_d = adfuller(s_diff, autolag="AIC")[1]
    kpss_p_d = kpss(s_diff, regression="c", nlags="auto")[1]
    concl_diff = stationarity_conclusion(adf_p_d, kpss_p_d)
    d1_results[name] = {"adf_p": adf_p, "kpss_p": kpss_p, "level": concl_level,
                         "adf_p_d": adf_p_d, "diff": concl_diff}
    print(f"{name:<24} {adf_p:<14.4f} {kpss_p:<15.4f} {concl_level:<28} {adf_p_d:<14.4f} {concl_diff:<28}")

# Flag spurious regressions
acm_i1 = "I(1)" in d1_results.get("ACM TP (%)", {}).get("level", "")
fedbs_i1 = "I(1)" in d1_results.get("Fed BS ($B)", {}).get("level", "")
deficit_i1 = "I(1)" in d1_results.get("Deficit 12M ($B)", {}).get("level", "")

print()
if acm_i1 and fedbs_i1:
    print("  *** WARNING: ACM TP and Fed BS are both I(1) in levels.")
    print("      A11 levels regression (r={:.3f}) is LIKELY SPURIOUS. Lead with changes regression.".format(corr_bs_level))
if acm_i1 and deficit_i1:
    print("  *** WARNING: ACM TP and Deficit 12M are both I(1) in levels.")
    print("      A10 levels regression may be spurious. See cointegration test (D1b).")


# ═══ D1b: COINTEGRATION TEST (ENGLE-GRANGER) ═══
print("\n" + "=" * 75)
print("DIAGNOSTIC D1b: Cointegration Tests (Engle-Granger)")
print("=" * 75)

# A11: Fed BS vs ACM TP
coint_stat_11, coint_p_11, _ = coint(a11_clean["fed_bs"], a11_clean["acm_tp"])
print(f"\n  A11 (Fed BS vs ACM TP):")
print(f"    EG test statistic: {coint_stat_11:.4f}")
print(f"    p-value: {coint_p_11:.4f}")
if coint_p_11 < 0.05:
    a11_coint_verdict = "COINTEGRATED (levels regression captures real long-run relationship)"
else:
    a11_coint_verdict = "NOT cointegrated (levels regression is SPURIOUS)"
print(f"    Verdict: {a11_coint_verdict}")

# A10: Deficit vs ACM TP
coint_stat_10, coint_p_10, _ = coint(a10_clean["deficit_12m_abs"], a10_clean["acm_tp"])
print(f"\n  A10 (Deficit 12M vs ACM TP):")
print(f"    EG test statistic: {coint_stat_10:.4f}")
print(f"    p-value: {coint_p_10:.4f}")
if coint_p_10 < 0.05:
    a10_coint_verdict = "COINTEGRATED (levels regression captures real long-run relationship)"
else:
    a10_coint_verdict = "NOT cointegrated (levels regression is SPURIOUS)"
print(f"    Verdict: {a10_coint_verdict}")


# ═══ D2: VIF ON A08 TAYLOR RULE HORSE RACE ═══
print("\n" + "=" * 75)
print("DIAGNOSTIC D2: VIF on A08 Taylor Rule Horse Race")
print("=" * 75)

X_vif_08 = sm.add_constant(a08[["core_pce_yoy", "headline_pce_yoy"]].values)
vif_core_08 = variance_inflation_factor(X_vif_08, 1)
vif_head_08 = variance_inflation_factor(X_vif_08, 2)
corr_ch = a08["core_pce_yoy"].corr(a08["headline_pce_yoy"])

print(f"\n  VIF(Core PCE YoY):     {vif_core_08:.2f}")
print(f"  VIF(Headline PCE YoY): {vif_head_08:.2f}")
print(f"  Correlation(Core, Headline): {corr_ch:.4f}")

if max(vif_core_08, vif_head_08) >= 10:
    d2_verdict = "SEVERE MULTICOLLINEARITY"
    print(f"\n  *** {d2_verdict}. Horse race CANNOT reliably distinguish core from headline.")
    print(f"      Do NOT claim headline dominates. Report both models separately.")
elif max(vif_core_08, vif_head_08) >= 5:
    d2_verdict = "MODERATE multicollinearity"
    print(f"\n  {d2_verdict}. Interpret horse race coefficients with caution.")
else:
    d2_verdict = "No multicollinearity concern"
    print(f"\n  {d2_verdict} (VIF < 5).")


# ═══ D3: LJUNG-BOX ON A07/A08/A10/A11 RESIDUALS ═══
print("\n" + "=" * 75)
print("DIAGNOSTIC D3: Ljung-Box Autocorrelation on Thesis Audit Residuals")
print("=" * 75)

d3_models = [
    ("A07: Oil->Headline CPI", model_cpi),
    ("A07: Oil->Core PCE", model_core),
    ("A08: Core TR (levels)", model_core_tr),
    ("A08: Headline TR (levels)", model_head_tr),
    ("A10: Deficit->TP (levels)", model_def_level),
    ("A11: Fed BS->TP (levels)", model_bs_level),
]

lags_to_test = [5, 10]
print(f"\n{'Regression':<35}", end="")
for lag in lags_to_test:
    print(f"  {'LB(' + str(lag) + ') p':>10}", end="")
print(f"  {'Autocorrelation?':>18}")
print("-" * 85)

for name, model in d3_models:
    print(f"{name:<35}", end="")
    any_sig = False
    for lag in lags_to_test:
        lb_result = acorr_ljungbox(model.resid, lags=[lag], return_df=True)
        lb_pval = lb_result["lb_pvalue"].values[0]
        flag = "*" if lb_pval < 0.05 else " "
        if lb_pval < 0.05:
            any_sig = True
        print(f"  {lb_pval:>9.4f}{flag}", end="")
    print(f"  {'YES - HAC warranted' if any_sig else 'No':>18}")

print("\n  Ljung-Box detected autocorrelation -> HAC standard errors are warranted.")
print("  All regressions above use HAC, which corrects for the autocorrelation detected here.")


# ═══ D4: DIAGNOSTIC → ANALYSIS MAPPING ═══
print("\n" + "=" * 75)
print("DIAGNOSTIC D4: Diagnostic -> Analysis Mapping")
print("=" * 75)

print(f"""
  Analysis 07 (Oil->CPI):     HAC SEs warranted (D3). Stationarity checked (D1).
  Analysis 08 (Taylor Rule):  VIF={max(vif_core_08, vif_head_08):.1f} -> horse race {'UNRELIABLE' if max(vif_core_08, vif_head_08) >= 10 else 'interpret with caution' if max(vif_core_08, vif_head_08) >= 5 else 'reliable'} (D2).
  Analysis 10 (Deficit->TP):  {'I(1)/I(1)' if acm_i1 and deficit_i1 else 'Mixed order'} -> {a10_coint_verdict.split('(')[0].strip()} (D1/D1b).
  Analysis 11 (Fed BS->TP):   {'I(1)/I(1)' if acm_i1 and fedbs_i1 else 'Mixed order'} -> {a11_coint_verdict.split('(')[0].strip()} (D1/D1b).
  All regressions:            HAC SEs throughout (D3 confirms warranted).
""")


# ═════════════════════════════════════════════════════════
# FIGURE
# ═════════════════════════════════════════════════════════
print("\nGenerating charts...")

fig, axes = plt.subplots(4, 2, figsize=(16, 28))
fig.suptitle("Thesis Audit — New Analyses (07, 08, 10, 11)", fontsize=16, fontweight="bold", y=0.99)

# Panel 07a: Oil YoY vs CPI/Core PCE YoY scatter
ax = axes[0, 0]
ax.scatter(a07["oil_yoy"], a07["cpi_yoy"], alpha=0.6, s=30, color="#e74c3c", label="Headline CPI YoY", edgecolors="none")
ax.scatter(a07["oil_yoy"], a07["core_pce_yoy"], alpha=0.6, s=30, color="#3498db", label="Core PCE YoY", edgecolors="none")
x_line = np.linspace(a07["oil_yoy"].min(), a07["oil_yoy"].max(), 100)
ax.plot(x_line, model_cpi.params[0] + model_cpi.params[1] * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.plot(x_line, model_core.params[0] + model_core.params[1] * x_line, color="#3498db", linewidth=2, linestyle="--")
ax.set_xlabel("Oil Price YoY Change (%)")
ax.set_ylabel("Inflation YoY (%)")
ax.set_title("Analysis 07a: Oil → Headline CPI vs Core PCE", fontweight="bold")
ax.legend(fontsize=8)
ax.text(0.05, 0.95, f"Per 10% oil increase:\n  Headline CPI: {beta_headline*10*100:+.0f}bp\n  Core PCE: {beta_core_pce*10*100:+.0f}bp\n  Ratio: {abs(beta_headline/beta_core_pce):.1f}x",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# Panel 07b: Time series of CPI, Core PCE, Oil
ax = axes[0, 1]
ax2 = ax.twinx()
cpi_plot = cpi_yoy.dropna()
core_pce_plot = core_pce_yoy.dropna()
oil_yoy_plot = oil_yoy.dropna()
ax.plot(cpi_plot.index, cpi_plot, color="#e74c3c", linewidth=1.5, label="Headline CPI YoY")
ax.plot(core_pce_plot.index, core_pce_plot, color="#3498db", linewidth=1.5, label="Core PCE YoY")
ax2.plot(oil_yoy_plot.index, oil_yoy_plot, color="#e67e22", linewidth=1, alpha=0.5, label="Oil YoY (RHS)")
ax.axhline(2.0, color="gray", linewidth=1, linestyle="--", alpha=0.5, label="2% target")
ax.set_ylabel("Inflation YoY (%)")
ax2.set_ylabel("Oil YoY (%)", color="#e67e22")
ax.set_title("Analysis 07b: CPI, Core PCE, and Oil Over Time", fontweight="bold")
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=7)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))

# Panel 08a: Taylor Rule fitted values
ax = axes[1, 0]
ax.plot(a08.index, a08["fed_funds"], color="black", linewidth=1.5, label="Actual Fed Funds")
fitted_core = model_core_tr.predict(sm.add_constant(a08[["core_pce_yoy", "unemployment"]].values))
fitted_head = model_head_tr.predict(sm.add_constant(a08[["headline_pce_yoy", "unemployment"]].values))
ax.plot(a08.index, fitted_core, color="#3498db", linewidth=1.5, linestyle="--", label=f"Core PCE model (R²={model_core_tr.rsquared:.3f})")
ax.plot(a08.index, fitted_head, color="#e74c3c", linewidth=1.5, linestyle="--", label=f"Headline PCE model (R²={model_head_tr.rsquared:.3f})")
ax.set_ylabel("Fed Funds Rate (%)")
ax.set_title("Analysis 08a: Taylor Rule — Core vs Headline PCE", fontweight="bold")
ax.legend(fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))

# Panel 08b: Core PCE vs Core CPI divergence
ax = axes[1, 1]
if len(divergence) > 0:
    ax.plot(divergence.index, divergence["core_pce_yoy"], color="#3498db", linewidth=1.5, label="Core PCE YoY")
    ax.plot(divergence.index, divergence["core_cpi_yoy"], color="#e74c3c", linewidth=1.5, label="Core CPI YoY")
    ax.axhline(2.0, color="gray", linewidth=1, linestyle="--", alpha=0.5, label="2% target")
    ax.fill_between(divergence.index, divergence["core_pce_yoy"], divergence["core_cpi_yoy"],
                     alpha=0.2, color="#8e44ad", label="Gap")
    ax.set_ylabel("YoY (%)")
    ax.set_title("F5 Audit: Core PCE vs Core CPI Divergence", fontweight="bold")
    ax.legend(fontsize=8)
    latest_pce = core_pce_yoy.dropna().iloc[-1]
    latest_cpi = core_cpi_yoy.dropna().iloc[-1]
    ax.text(0.05, 0.95, f"Latest Core PCE: {latest_pce:.2f}%\nLatest Core CPI: {latest_cpi:.2f}%\nGap: {latest_pce - latest_cpi:+.2f}pp",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))

# Panel 10a: Deficit vs Term Premium (levels)
ax = axes[2, 0]
ax2 = ax.twinx()
ax.plot(a10_clean.index, a10_clean["deficit_12m_abs"], color="#e74c3c", linewidth=1.5, label="12M Cumulative Deficit ($B)")
ax2.plot(a10_clean.index, a10_clean["acm_tp"], color="#3498db", linewidth=1.5, label="ACM 10Y TP (%)")
ax.set_ylabel("12M Deficit ($B)", color="#e74c3c")
ax2.set_ylabel("ACM Term Premium (%)", color="#3498db")
ax.set_title("Analysis 10a: Fiscal Deficit vs Term Premium", fontweight="bold")
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.05, 0.05, f"Corr(levels): {corr_level:+.3f}\nbeta: {model_def_level.params[1]:+.6f} (p={model_def_level.pvalues[1]:.4f})",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# Panel 10b: Deficit vs TP scatter
ax = axes[2, 1]
ax.scatter(a10_clean["deficit_12m_abs"], a10_clean["acm_tp"], alpha=0.6, s=30, color="#8e44ad", edgecolors="none")
x_line = np.linspace(a10_clean["deficit_12m_abs"].min(), a10_clean["deficit_12m_abs"].max(), 100)
ax.plot(x_line, model_def_level.params[0] + model_def_level.params[1] * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.set_xlabel("12M Cumulative Deficit ($B)")
ax.set_ylabel("ACM 10Y Term Premium (%)")
ax.set_title("Analysis 10b: Deficit → TP Scatter", fontweight="bold")
ax.text(0.05, 0.95, f"beta={model_def_level.params[1]:+.6f}\nR²={model_def_level.rsquared:.4f}\np={model_def_level.pvalues[1]:.4f}",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# Panel 11a: Fed BS vs Term Premium (levels)
ax = axes[3, 0]
ax2 = ax.twinx()
ax.plot(a11_clean.index, a11_clean["fed_bs"], color="#2ecc71", linewidth=1.5, label="Fed Total Assets ($B)")
ax2.plot(a11_clean.index, a11_clean["acm_tp"], color="#3498db", linewidth=1.5, label="ACM 10Y TP (%)")
ax.set_ylabel("Fed Total Assets ($B)", color="#2ecc71")
ax2.set_ylabel("ACM Term Premium (%)", color="#3498db")
ax.set_title("Analysis 11a: Fed Balance Sheet vs Term Premium", fontweight="bold")
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.text(0.05, 0.05, f"Corr(levels): {corr_bs_level:+.3f}\nbeta: {model_bs_level.params[1]:+.8f} (p={model_bs_level.pvalues[1]:.4f})",
        transform=ax.transAxes, va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

# Panel 11b: Fed BS vs TP scatter
ax = axes[3, 1]
ax.scatter(a11_clean["fed_bs"], a11_clean["acm_tp"], alpha=0.6, s=30, color="#2ecc71", edgecolors="none")
x_line = np.linspace(a11_clean["fed_bs"].min(), a11_clean["fed_bs"].max(), 100)
ax.plot(x_line, model_bs_level.params[0] + model_bs_level.params[1] * x_line, color="#e74c3c", linewidth=2, linestyle="--")
ax.set_xlabel("Fed Total Assets ($B)")
ax.set_ylabel("ACM 10Y Term Premium (%)")
ax.set_title("Analysis 11b: Fed BS → TP Scatter", fontweight="bold")
ax.text(0.05, 0.95, f"beta={model_bs_level.params[1]:+.8f}\nR²={model_bs_level.rsquared:.4f}\np={model_bs_level.pvalues[1]:.4f}",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="wheat", alpha=0.8))

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig("../output/thesis_audit_results.png", dpi=150, bbox_inches="tight")
print(f"\nCharts saved to ../output/thesis_audit_results.png")


# ═════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════
print("\n" + "=" * 75)
print("THESIS AUDIT ANALYSES — SUMMARY")
print("=" * 75)
print(f"""
ANALYSIS 07: Oil → CPI Passthrough
  Per 10% oil price increase:
    Headline CPI: {beta_headline * 10 * 100:+.0f}bp
    Core PCE: {beta_core_pce * 10 * 100:+.0f}bp
    Ratio: {abs(beta_headline / beta_core_pce):.1f}x
  MS claimed: ~35bp headline, ~3bp core (ratio ~12x)
  Our data: Headline >> Core CONFIRMED, specific magnitudes differ

ANALYSIS 08: Taylor Rule
  Core PCE model R²:     {model_core_tr.rsquared:.4f}
  Headline PCE model R²: {model_head_tr.rsquared:.4f}
  Horse race (levels):   Core p={model_both_tr.pvalues[1]:.4f}, Headline p={model_both_tr.pvalues[2]:.4f}
  Horse race (changes):  Core p={model_d3.pvalues[1]:.4f}, Headline p={model_d3.pvalues[2]:.4f}

ANALYSIS 10: Deficit → Term Premium
  Level regression: beta={model_def_level.params[1]:+.6f} (p={model_def_level.pvalues[1]:.4f})
  Correlation (levels): {corr_level:+.4f}

ANALYSIS 11: Fed BS → Term Premium
  Level regression: beta={model_bs_level.params[1]:+.8f} (p={model_bs_level.pvalues[1]:.4f})
  Correlation (levels): {corr_bs_level:+.4f}

CORE PCE STATUS (for claim F5):
  Latest Core PCE YoY: {core_pce_yoy.dropna().iloc[-1]:.2f}%
  Latest Core CPI YoY: {core_cpi_yoy.dropna().iloc[-1]:.2f}%
  Core PCE is {'above' if core_pce_yoy.dropna().iloc[-1] > 3.0 else 'below'} 3% — {'NOT declining as claimed' if core_pce_yoy.dropna().iloc[-1] > 3.0 else 'declining'}
""")


# ═════════════════════════════════════════════════════════
# WRITE RESULTS FILE
# ═════════════════════════════════════════════════════════
results_path = "../output/thesis_audit_results.txt"
with open(results_path, "w") as f:
    f.write(f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}\n")
    f.write("=" * 75 + "\n")
    f.write("THESIS AUDIT RESULTS\n")
    f.write("=" * 75 + "\n\n")

    # A07
    f.write("A07: Oil -> CPI Passthrough\n")
    f.write(f"{'Dep Var':<25} {'Oil Beta':>10} {'SE(HAC)':>10} {'p-value':>10} {'R2':>8}\n")
    f.write("-" * 65 + "\n")
    for name, model in [("Headline CPI YoY", model_cpi),
                         ("Core PCE YoY", model_core),
                         ("Headline PCE YoY", model_head_pce)]:
        f.write(f"{name:<25} {model.params[1]:>+10.4f} {model.bse[1]:>10.4f} {model.pvalues[1]:>10.4f} {model.rsquared:>8.4f}\n")
    f.write(f"\nPer 10% oil increase:\n")
    f.write(f"  Headline CPI: {beta_headline * 10 * 100:+.0f}bp\n")
    f.write(f"  Core PCE:     {beta_core_pce * 10 * 100:+.0f}bp\n")
    f.write(f"  Headline PCE: {beta_headline_pce * 10 * 100:+.0f}bp\n")
    f.write(f"  Ratio (Headline/Core): {abs(beta_headline / beta_core_pce):.1f}x\n")
    f.write(f"  MS comparison: ~35bp headline, ~3bp core\n\n")

    # 3M changes
    f.write("A07 (3M changes):\n")
    for name, model in [("d(Headline CPI YoY)", model_d_cpi),
                         ("d(Core PCE YoY)", model_d_core),
                         ("d(Headline PCE YoY)", model_d_head)]:
        f.write(f"  {name:<25} beta={model.params[1]:+.4f} p={model.pvalues[1]:.4f} R2={model.rsquared:.4f}\n")
    f.write("\n")

    # A08
    f.write("A08: Taylor Rule\n")
    f.write(f"{'Model':<30} {'R2':>8} {'AIC':>10}\n")
    f.write("-" * 50 + "\n")
    f.write(f"{'Core PCE + Unemployment':<30} {model_core_tr.rsquared:>8.4f} {model_core_tr.aic:>10.1f}\n")
    f.write(f"{'Headline PCE + Unemployment':<30} {model_head_tr.rsquared:>8.4f} {model_head_tr.aic:>10.1f}\n\n")
    f.write(f"Core-only:     beta(core)={model_core_tr.params[1]:+.4f} p={model_core_tr.pvalues[1]:.4f}, beta(unemp)={model_core_tr.params[2]:+.4f} p={model_core_tr.pvalues[2]:.4f}\n")
    f.write(f"Headline-only: beta(head)={model_head_tr.params[1]:+.4f} p={model_head_tr.pvalues[1]:.4f}, beta(unemp)={model_head_tr.params[2]:+.4f} p={model_head_tr.pvalues[2]:.4f}\n")
    f.write(f"Horse race:    beta(core)={model_both_tr.params[1]:+.4f} p={model_both_tr.pvalues[1]:.4f}, beta(head)={model_both_tr.params[2]:+.4f} p={model_both_tr.pvalues[2]:.4f}\n\n")
    f.write(f"Changes models:\n")
    f.write(f"  d(Core):     beta={model_d1.params[1]:+.4f} p={model_d1.pvalues[1]:.4f} R2={model_d1.rsquared:.4f}\n")
    f.write(f"  d(Headline): beta={model_d2.params[1]:+.4f} p={model_d2.pvalues[1]:.4f} R2={model_d2.rsquared:.4f}\n")
    f.write(f"  Horse race:  beta(core)={model_d3.params[1]:+.4f} p={model_d3.pvalues[1]:.4f}, beta(head)={model_d3.params[2]:+.4f} p={model_d3.pvalues[2]:.4f}\n")
    f.write(f"  Core-Headline PCE correlation: {corr_ch:.4f}\n\n")

    # A10
    f.write("A10: Deficit -> Term Premium\n")
    f.write(f"  Levels: beta={model_def_level.params[1]:+.6f} t={model_def_level.tvalues[1]:+.2f} p={model_def_level.pvalues[1]:.4f} R2={model_def_level.rsquared:.4f}\n")
    f.write(f"  Per $100B: {model_def_level.params[1] * 100:+.3f}pp\n")
    f.write(f"  Changes: beta={model_def_change.params[1]:+.6f} t={model_def_change.tvalues[1]:+.2f} p={model_def_change.pvalues[1]:.4f} R2={model_def_change.rsquared:.4f}\n")
    f.write(f"  Corr (levels): {corr_level:+.4f}  Corr (changes): {corr_change:+.4f}\n")
    f.write(f"  Latest: 12M deficit=${a10_clean['deficit_12m_abs'].iloc[-1]:.0f}B, ACM TP={a10_clean['acm_tp'].iloc[-1]:.3f}%\n\n")

    # A11
    f.write("A11: Fed BS -> Term Premium\n")
    f.write(f"  Levels: beta={model_bs_level.params[1]:+.8f} t={model_bs_level.tvalues[1]:+.2f} p={model_bs_level.pvalues[1]:.4f} R2={model_bs_level.rsquared:.4f}\n")
    f.write(f"  Per $100B reduction: {-model_bs_level.params[1] * 100:+.4f}pp\n")
    f.write(f"  Changes: beta={model_bs_change.params[1]:+.8f} t={model_bs_change.tvalues[1]:+.2f} p={model_bs_change.pvalues[1]:.4f} R2={model_bs_change.rsquared:.4f}\n")
    f.write(f"  Corr (levels): {corr_bs_level:+.4f}  Corr (changes): {corr_bs_change:+.4f}\n")
    f.write(f"  Latest: Fed BS=${a11_clean['fed_bs'].iloc[-1]:.0f}B, ACM TP={a11_clean['acm_tp'].iloc[-1]:.3f}%\n")
    if model_bs_level.rsquared > 0.50:
        f.write(f"  *** FLAG: Levels R2={model_bs_level.rsquared:.4f} > 0.50 — LIKELY SPURIOUS, see D1/D1b\n")
    f.write("\n")

    # F5
    f.write("F5: Core PCE Status\n")
    f.write(f"  Latest Core PCE YoY: {core_pce_yoy.dropna().iloc[-1]:.2f}%\n")
    f.write(f"  Latest Core CPI YoY: {core_cpi_yoy.dropna().iloc[-1]:.2f}%\n")
    f.write(f"  Gap (PCE - CPI): {core_pce_yoy.dropna().iloc[-1] - core_cpi_yoy.dropna().iloc[-1]:.2f}pp\n")
    f.write(f"  Last 6 months Core PCE YoY:\n")
    for date, val in recent_core_pce.items():
        f.write(f"    {date.strftime('%Y-%m')}: {val:.2f}%\n")
    f.write(f"  Trend: {trend}\n\n")

    # Diagnostics
    f.write("=" * 75 + "\n")
    f.write("DIAGNOSTICS\n")
    f.write("=" * 75 + "\n\n")

    # D1
    f.write("D1: Stationarity\n")
    f.write(f"{'Series':<24} {'ADF p':>8} {'KPSS p':>8} {'Verdict (level)':<28} {'Verdict (diff)':<28}\n")
    f.write("-" * 100 + "\n")
    for name, res in d1_results.items():
        f.write(f"{name:<24} {res['adf_p']:>8.4f} {res['kpss_p']:>8.4f} {res['level']:<28} {res['diff']:<28}\n")
    f.write("\n")

    # D1b
    f.write("D1b: Cointegration (Engle-Granger)\n")
    f.write(f"  A10 (Deficit vs ACM TP): EG stat={coint_stat_10:.4f}, p={coint_p_10:.4f}\n")
    f.write(f"    Verdict: {a10_coint_verdict}\n")
    f.write(f"  A11 (Fed BS vs ACM TP):  EG stat={coint_stat_11:.4f}, p={coint_p_11:.4f}\n")
    f.write(f"    Verdict: {a11_coint_verdict}\n\n")

    # D2
    f.write("D2: VIF on A08 Horse Race\n")
    f.write(f"  VIF(Core PCE):     {vif_core_08:.2f}\n")
    f.write(f"  VIF(Headline PCE): {vif_head_08:.2f}\n")
    f.write(f"  Correlation:       {corr_ch:.4f}\n")
    f.write(f"  Verdict: {d2_verdict}\n\n")

    # D3
    f.write("D3: Ljung-Box Autocorrelation\n")
    f.write(f"{'Regression':<35} {'LB(5) p':>10} {'LB(10) p':>10} {'Autocorr?':>12}\n")
    f.write("-" * 70 + "\n")
    for name, model in d3_models:
        lb5 = acorr_ljungbox(model.resid, lags=[5], return_df=True)["lb_pvalue"].values[0]
        lb10 = acorr_ljungbox(model.resid, lags=[10], return_df=True)["lb_pvalue"].values[0]
        any_sig = lb5 < 0.05 or lb10 < 0.05
        f.write(f"{name:<35} {lb5:>10.4f} {lb10:>10.4f} {'YES' if any_sig else 'No':>12}\n")
    f.write("\n")

    # D4
    f.write("D4: Diagnostic -> Analysis Mapping\n")
    f.write(f"  A07 (Oil->CPI):     HAC SEs warranted (D3)\n")
    f.write(f"  A08 (Taylor Rule):  VIF={max(vif_core_08, vif_head_08):.1f} (D2)\n")
    f.write(f"  A10 (Deficit->TP):  {a10_coint_verdict.split('(')[0].strip()} (D1/D1b)\n")
    f.write(f"  A11 (Fed BS->TP):   {a11_coint_verdict.split('(')[0].strip()} (D1/D1b)\n")
    f.write(f"  All regressions:    HAC SEs throughout (D3)\n")

print(f"Results written to {results_path}")
