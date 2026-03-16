# US 2s10s Steepener Trade — Quantitative Thesis

## Trade Summary

**Trade:** US 2s10s curve steepener (long 10Y yield vs short 2Y yield, i.e. positioning for the spread to widen)

| Parameter | Value |
|-----------|-------|
| **Entry** | 0.50 (50bp spread) |
| **Target** | 0.70 (70bp spread) |
| **Stop Loss** | 0.42 (42bp spread) |

---

## Thesis

### Why the front-end (2Y) should rally (yields lower)

- **Oil → headline, not core:** MS research shows every 10% oil price increase adds ~35bp to headline CPI but only ~3bp to core CPI. The Fed has historically prioritized core inflation in its reaction function.
- **Market mispricing rate path:** Bond traders have priced out all 2026 rate cuts. This is overdone — JPM recommends taking profit on 2Y shorts.
- **Weak labor market:** NFP printed -92k vs +59k expected. Powell is data-dependent; deteriorating employment is a strong catalyst for easing.
- **Core PCE falling:** Core PCE inflation has continued to decline in 2026 alongside labor market weakening, even as markets have repriced hawkishly.
- **Warsh appointment (May 2026):** Incoming Fed Chair Warsh views oil shocks as "noise," is less data-dependent than Powell, and is predisposed toward lower rates. He is unlikely to let a short-lived conflict derail the easing cycle.
- **Short-lived conflict:** JPM expects rapid munition depletion and poor risk-reward for the US economy to keep the Iran war brief, meaning oil-driven inflation will be transitory.

### Why the back-end (10Y) should sell off (yields higher)

- **Fiscal deficit expansion:** War spending adds to an already deteriorating fiscal outlook, post the Supreme Court ruling (Feb 20) striking down tariff revenue.
- **Increased Treasury issuance:** Larger deficits require more long-duration supply, pushing term premium higher.
- **Quantitative tightening (QT):** As Warsh's appointment approaches, expectations for continued or accelerated QT will pressure long-end supply/demand dynamics.
- **Warsh uncertainty:** Lack of forward guidance from Warsh adds term premium to longer-dated bonds.

### Key Catalysts

1. **Fed meeting — March 18, 2026:** Powell's forward guidance; likely to echo 2022 language calling oil-driven inflation "transitory" to prevent inflation expectations from becoming unanchored.
2. **Iran munitions depletion signals:** Any intelligence suggesting the conflict is winding down supports the short-lived-war thesis and the front-end rally.
3. **Warsh appointment — May 2026:** Shift in Fed leadership and communication style; likely rate-cut-friendly despite headline inflation.

---

## Data File: `data steepener.xlsx`

The spreadsheet contains daily time series data sourced from Bloomberg, organized across the following sheets. Most series cover approximately 5 years of history (mid-2021 to March 2026).

### Sheet-by-Sheet Reference

| Sheet Name | Fields | Date Range | Frequency | Data Points | Description |
|------------|--------|------------|-----------|-------------|-------------|
| **CL1** | Date, Last Price, Open Interest, SMAVG(15) | 2021-02-24 → 2026-03-17 | Daily | 1,280 | **WTI crude oil front-month futures** ($/bbl). The primary driver of the headline inflation channel. Last Price is the settlement price; Open Interest tracks speculative/hedging activity; SMAVG(15) is the 15-day simple moving average for trend smoothing. |
| **UST 2 y** | Date, Last Price | 2021-03-17 → 2026-03-16 | Daily | 1,247 | **US 2-year Treasury yield** (%). The front leg of the steepener trade. Most sensitive to changes in Fed policy expectations. A decline here = trade is working on the front end. |
| **US 2 year breakeven** | Date, Last Price | 2020-09-15 → 2026-03-16 | Daily | 1,371 | **US 2-year breakeven inflation rate** (%). Derived from 2Y nominal yield minus 2Y TIPS real yield. Reflects the market's near-term inflation expectations — this is what should spike on oil but is expected to fade if the conflict is short-lived. |
| **US Core CPI** | Date, Last Price | 2021-03-31 → 2026-01-31 | Monthly | 59 | **US Core CPI YoY** (%). Excludes food and energy. The thesis hinges on oil hitting headline CPI but *not* core — this series is the evidence. Published with ~1 month lag. |
| **UST 10 y** | Date, Last Price | 2021-03-17 → 2026-03-16 | Daily | 1,247 | **US 10-year Treasury yield** (%). The back leg of the steepener trade. Expected to rise on fiscal deficit expansion, increased Treasury issuance, and QT expectations. |
| **FED Balance sheet** | *(placeholder)* | — | — | — | **Federal Reserve total assets** ($bn). Intended to be pulled from FRED. Tracks the pace of quantitative tightening — a shrinking balance sheet means less demand for duration, pushing long-end yields higher. |
| **US 10yr breakeven** | Date, Last Price | 2021-03-17 → 2026-03-16 | Daily | 1,247 | **US 10-year breakeven inflation rate** (%). Reflects longer-term inflation expectations. If 10Y BE rises faster than 2Y BE, the market is pricing inflation as a persistent (not transitory) risk — relevant for monitoring narrative shifts. |
| **US 2yr10yr spread** | Date, Last Price | 2021-03-17 → 2026-03-16 | Daily | 1,247 | **US 2s10s yield curve spread** (bp). Calculated as 10Y yield minus 2Y yield. **This is the direct P&L driver of the trade.** Entry at ~50bp, target 70bp, stop loss 42bp. Positive values = normal/steep curve. |
| **ACM 10yr premium** | Date, Last Price | 2021-03-17 → 2026-03-12 | Daily | 1,245 | **Adrian-Crump-Moench 10-year term premium** (%). Estimated by the NY Fed. Decomposes the 10Y yield into rate expectations + risk compensation. A rising term premium supports the steepener thesis by confirming the back-end selloff is driven by structural supply/fiscal concerns, not just rate expectations. |
| **Sheet5** | — | — | — | — | Empty / unused. |
| **← Raw** | — | — | — | — | Empty / unused placeholder for raw data. |

### Key Relationships to Monitor

- **CL1 vs US 2yr breakeven:** Oil price pass-through to near-term inflation expectations (MS: +35bp headline CPI per 10% oil increase)
- **US 2yr breakeven vs US 10yr breakeven:** If the gap widens (10Y rising faster), inflation is being seen as persistent — risk to the thesis
- **UST 2y vs US Core CPI:** If core CPI stays flat while 2Y yields spike, the front-end is mispriced — supports the trade
- **US 2yr10yr spread vs ACM 10yr premium:** If the spread widens alongside rising term premium, the steepening is structural (supply/fiscal) not just rate expectations — strongest confirmation signal

## Recommended Additional Data Series

To make the thesis more quantitatively rigorous, consider adding:

### Rates & Fed Pricing
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **SOFR OIS implied rates (Dec 2026, Dec 2027)** | Bloomberg SOFR OIS | Directly tracks market-implied rate path — the core mispricing argument |
| **Fed Funds Futures (FF1–FF12)** | CME | Alternative view on number of cuts priced per meeting |
| **US 2Y10Y term premium (ACM model)** | NY Fed ACM | Decomposes the curve into expectations vs. term premium — you want to show term premium is rising on the back end |
| **US 5Y5Y forward rate** | Bloomberg | Market's view of long-run neutral rate; captures fiscal/supply concerns |

### Inflation
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **Core PCE (MoM & YoY)** | BEA | The Fed's preferred inflation gauge — more important than CPI for policy |
| **5Y5Y inflation swap** | Bloomberg | Forward inflation expectations; tests whether oil shock is seen as transitory |
| **Michigan/NY Fed inflation expectations (1Y & 5Y)** | UMich / NY Fed | Consumer inflation expectations — if these stay anchored, supports "transitory" thesis |
| **Gasoline prices (retail)** | EIA | Direct pass-through channel from oil to headline CPI |

### Labor Market
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **NFP (monthly change)** | BLS | Already cited (-92k); tracking the trend strengthens the easing case |
| **Unemployment rate (U3)** | BLS | Sahm Rule trigger level — if rising, it's a recession signal that forces cuts |
| **Initial jobless claims (weekly)** | DOL | Higher frequency labor signal than monthly NFP |
| **JOLTS job openings** | BLS | Leading indicator of labor demand; falling openings = weaker wage pressure |

### Fiscal & Supply
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **US federal deficit (monthly Treasury statement)** | US Treasury | Quantifies the fiscal deterioration driving long-end supply |
| **Treasury net issuance (coupon supply)** | Treasury refunding announcements | Direct measure of duration supply hitting the market |
| **MOVE index** | ICE/BofA | Rates volatility — elevated MOVE = higher term premium = steeper curve |

### Positioning & Flows
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **CFTC COT net speculative positioning (2Y & 10Y futures)** | CFTC | If specs are extremely short the front end, a squeeze supports your trade |
| **Treasury options put/call skew (TY & TU)** | Bloomberg | You mentioned this is at highs — tracking it quantifies sentiment |

### Geopolitical / Oil
| Series | Ticker / Source | Why |
|--------|----------------|-----|
| **Brent crude (CO1)** | ICE | Global oil benchmark; relevant for pass-through to European/global inflation |
| **Oil implied volatility (OVX)** | CBOE | Measures uncertainty around oil prices, not just level |
| **US strategic petroleum reserve (SPR) level** | EIA | Capacity to dampen oil shocks — lower SPR = less buffer |

---

## Key Quantitative Checks to Run

1. **Regression: Oil price changes → 2s10s spread** over past conflicts (Gulf War, Libya 2011, Russia-Ukraine 2022). Does the curve steepen?
2. **Event study: NFP misses → front-end rally magnitude.** How much does the 2Y rally on a large NFP miss historically?
3. **Compare current SOFR OIS pricing vs. realized Fed path** in analogous episodes (2022 oil shock + weak growth). How far off was the market?
4. **Term premium decomposition:** Plot ACM term premium for 2Y vs 10Y. If 10Y term premium is rising while 2Y is flat/falling, the structural steepener is confirmed.
5. **Breakeven spread (10Y BE minus 2Y BE):** If this is widening, the market sees inflation as a long-duration risk, supporting back-end cheapening.
