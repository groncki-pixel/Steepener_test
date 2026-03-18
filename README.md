# US 2s10s Steepener — Restructured Thesis v2

## What Changed

The original thesis argued oil shocks **mechanically steepen** the 2s10s curve. After rigorous statistical audit of all 11 analyses, that causal chain was **disproven**:

- **A1 (Oil→Curve):** p=0.80 — no relationship. Oil spike weeks actually FLATTEN the curve.
- **A4 (Regime Study):** Contradicts thesis — flattening, not steepening, at all horizons.
- **A6 (2Y Mean Reversion):** Statistical noise — IQRs span hundreds of percent, n=30.
- **A8 (Taylor Rule):** VIF=10.3 — severe multicollinearity, horse race unreliable.
- **A10 (Deficit→TP):** Spurious in levels (not cointegrated), wrong sign in changes.

The trade is preserved but the thesis is rebuilt around **three defensible pillars**:
1. **Front-end overreaction** — 2Y spiked on oil/war, but breakevens say transitory
2. **Term premium structural bid** — A2 robust, Warsh QT acceleration
3. **Oil as timeline accelerant** — not the mechanism, just the catalyst

See [docs/thesis_restructured.md](docs/thesis_restructured.md) for the full restructured thesis.

---

## Repository Structure

```
Steepener_test/
├── README.md                          ← You are here
├── data/
│   └── data_steepener.xlsx            ← Bloomberg + FRED data (do not modify)
├── src/
│   ├── new7_2y_move_attribution.py    ← CRITICAL: run first (2Y decomposition)
│   ├── new1_fed_path_repricing.py     ← WIRP implied rate comparison
│   ├── new2_historical_episodes.py    ← Oil shock episode comparison
│   ├── new3_warsh_scenario_tree.py    ← Warsh scenario analysis
│   ├── new4_breakeven_nominal_decomp.py ← BE vs nominal time series
│   ├── new5_cftc_positioning.py       ← CFTC speculative positioning
│   ├── new6_carry_new_expression.py   ← Carry/P&L for SOFR expression
│   └── legacy/                        ← Original v1 analyses (deprecated)
│       ├── analysis.py                ← A1-A6 (see deprecation header)
│       ├── statistical_tests.py       ← T1-T8 diagnostics
│       └── thesis_audit_analyses.py   ← A7, A8, A10, A11
├── output/
│   └── legacy/                        ← Original v1 output files
│       ├── analysis_results.txt
│       ├── statistical_tests_results.txt
│       └── thesis_audit_results.txt
└── docs/
    └── thesis_restructured.md         ← Full restructured thesis
```

---

## Analysis Disposition (Keep / Kill / Reframe)

| # | Analysis | Status | Issue |
|---|----------|--------|-------|
| A1 | Oil→Curve | **REFRAMED** | p=0.80, oil flattens not steepens |
| A2 | Term Premium | **KEPT** | Strongest result, 100% rolling stability |
| A3 | Breakeven Divergence | **KEPT** | 2.6x ratio, CI excludes 1.0 |
| A4 | Regime Study | **KILLED** | Contradicts thesis at all horizons |
| A5 | Carry | **KEPT** | Rebuild for new expression |
| A6 | 2Y Mean Reversion | **KILLED** | Noise: IQRs span hundreds of % |
| A7 | Oil→CPI | **KEPT** | Headline >> core (~3x) |
| A8 | Taylor Rule | **DOWNGRADED** | VIF=10.3, multicollinearity |
| A10 | Deficit→TP | **DOWNGRADED** | Spurious levels, wrong sign |
| A11 | Fed BS→TP | **KEPT w/ CAVEAT** | Changes p=0.07, correct sign |

---

## Execution Order for New Analyses

Run from `src/` directory:

```bash
# 1. CRITICAL — determines trade target
python new7_2y_move_attribution.py

# 2. HIGH priority
python new1_fed_path_repricing.py
python new4_breakeven_nominal_decomp.py

# 3. MEDIUM priority
python new2_historical_episodes.py
python new3_warsh_scenario_tree.py
python new5_cftc_positioning.py

# 4. LOW priority
python new6_carry_new_expression.py
```

**NEW-7 must run first** — it decomposes the 2Y move and determines whether the oil-reversible component passes the 8bp decision gate for the trade target.

---

## Trade Expression

**New:** SOFR futures (SFRZ6/SFRH7) + Micro 10Y short
**Old:** DV01-neutral futures steepener (deprecated)

| Parameter | Value |
|-----------|-------|
| Entry | ~50bp spread |
| Target | 70bp spread |
| Stop | 42bp spread |
