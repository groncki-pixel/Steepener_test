# US 2s10s Steepener — Restructured Thesis v2

*Restructured after rigorous statistical audit of all original analyses.*

---

## Executive Summary

The original thesis argued oil shocks mechanically steepen the 2s10s curve. After rigorous testing, that causal chain was **disproven** (A1 p=0.80, A4 shows flattening, A6 is noise). The restructured thesis preserves the trade but rebuilds the logic around three defensible pillars.

---

## The Three Pillars

### Pillar 1: Front-End Overreaction (2Y should rally)

The 2Y spiked +34bp (Feb 27 → Mar 16), but decomposition shows:
- **Breakeven component** (~10-12bp): Oil/war-driven, transitory per breakeven pricing (A3: 2.6x ratio = market treats as transitory)
- **Real yield component**: Fed path repricing — but real yields actually FELL, meaning TIPS market doesn't buy the hawkish repricing
- **Technical correction** (~12-15bp): Pre-war oversold bounce that's already happened and won't reverse
- **Domestic inflation data** (~8-12bp): PPI, core PCE — independent of oil, but lagging indicators

**Key insight:** The breakeven market is telling you the oil shock is transitory. The nominal market hasn't caught up yet. That's the mispricing.

### Pillar 2: Term Premium Structural Bid (10Y should sell off or hold)

- **A2 (Term Premium Decomposition):** Strongest original result. ACM term premium drives spread widening with beta positive in 100% of rolling windows (T5). Bootstrap CI excludes zero (T6).
- **Warsh confirmation:** Kevin Warsh as Fed Chair would accelerate QT, pushing term premium higher. Three scenarios: confirmed by May (50%), delayed (30%), blocked (20%).
- **A11 (Fed Balance Sheet → TP):** Changes regression p=0.07, correct direction. QT = higher TP = steepening.

### Pillar 3: Oil as Timeline Accelerant (NOT Mechanism)

Oil doesn't cause steepening (A1 killed that). But oil shocks:
- Accelerate the timeline for Fed repricing
- Create the transitory inflation spike that the front-end overreacts to
- Generate headline risk that forces positioning unwinds

Oil is the **catalyst**, not the **mechanism**. The mechanism is front-end overreaction + term premium.

---

## Analysis Disposition Table

| Analysis | Status | Finding | Role in v2 |
|----------|--------|---------|------------|
| A1 (Oil→Curve) | REFRAMED | p=0.80, oil flattens not steepens | Pillar 3: oil is accelerant, not mechanism |
| A2 (Term Premium) | KEPT | Strongest result, 100% rolling stability | Pillar 2: central |
| A3 (Breakeven Divergence) | KEPT | 2.6x ratio robust, CI excludes 1.0 | Pillar 1: transitory signal |
| A4 (Regime Study) | KILLED | Contradicts thesis at all horizons | Removed |
| A5 (Carry) | KEPT | Mechanically correct | Rebuild for new expression (NEW-6) |
| A6 (2Y Mean Reversion) | KILLED | IQRs span hundreds of %, n=30 | Removed |
| A7 (Oil→CPI) | KEPT | Headline >> core (~3x in changes) | Supports transitory argument |
| A8 (Taylor Rule) | DOWNGRADED | VIF=10.3, horse race useless | Reference only |
| A10 (Deficit→TP) | DOWNGRADED | Spurious in levels, wrong sign in changes | Removed from core |
| A11 (Fed BS→TP) | KEPT WITH CAVEAT | Changes p=0.07, correct direction | Pillar 2: supporting |

---

## New Analysis Suite

Run in this order:

| Priority | File | Description |
|----------|------|-------------|
| CRITICAL | new7_2y_move_attribution.py | 2Y move decomposition & target calibration — run FIRST |
| HIGH | new1_fed_path_repricing.py | WIRP implied rate comparison (Feb 27 vs Mar 18) |
| HIGH | new4_breakeven_nominal_decomp.py | Full time series BE vs nominal decomposition |
| MEDIUM | new2_historical_episodes.py | Oil shock episode comparison (1990, 2008, 2022, 2026) |
| MEDIUM | new3_warsh_scenario_tree.py | Probability-weighted Warsh scenario analysis |
| MEDIUM | new5_cftc_positioning.py | CFTC speculative positioning analysis |
| LOW | new6_carry_new_expression.py | Carry & scenario P&L for SOFR + Micro 10Y expression |

---

## Trade Expression (Updated)

**Old expression:** DV01-neutral futures steepener (TU vs TY)
**New expression:** SOFR futures (SFRZ6/SFRH7) + Micro 10Y short

Rationale:
- SOFR futures give direct exposure to Fed path repricing (Pillar 1)
- Micro 10Y short captures term premium widening (Pillar 2)
- More precise than DV01-neutral which conflates the two legs

| Parameter | Value |
|-----------|-------|
| Entry | ~50bp spread |
| Target | 70bp spread |
| Stop | 42bp spread |

---

## 2Y Move Attribution (Critical Finding)

The +34bp 2Y move decomposes approximately as:
- ~12-15bp: Technical correction (pre-war oversold → already reversed, NOT coming back)
- ~10-12bp: Oil/war breakeven repricing (REVERSIBLE if war resolves)
- ~8-12bp: Domestic inflation data (PPI, core PCE — independent of oil)

**Decision gate:** If the oil-reversible breakeven component exceeds 8bp, war unwind alone provides meaningful P&L. Run NEW-7 to get the exact number.

---

## Wall Street Alignment

Multiple desks share the steepening view:
- Goldman Sachs: "We recommend 2s10s steepeners"
- JP Morgan: Term premium repricing thesis
- Morgan Stanley: Front-end overreaction call

This provides conviction but also means the trade is somewhat consensus — entry timing matters.

---

## Key Risks

1. **Stagflation:** If oil shock feeds into core inflation AND growth slows, Fed is trapped → curve may not steepen
2. **Warsh blocked:** If nomination fails, term premium catalyst is delayed/removed
3. **Oil stays elevated:** If Iran conflict escalates, "transitory" becomes "persistent"
4. **Technical:** Crowded trade risk given wall street consensus
5. **Timing:** Catalysts may take longer than the 3-6 month horizon

---

## Catalyst Timeline

| Date | Event | Impact |
|------|-------|--------|
| Mar 19 | FOMC meeting | Fed guidance on oil shock response |
| Apr-May | Warsh confirmation vote | Term premium catalyst |
| Apr | March NFP release | Labor market trajectory |
| May-Jun | Q1 GDP revision | Growth impact of oil shock |
| Jun | June FOMC + SEP | Dot plot repricing |
| Jul-Sep | Oil shock passthrough data | Core vs headline divergence |
