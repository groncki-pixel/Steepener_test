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

## Data Tracked in Spreadsheet

| Column | Description |
|--------|-------------|
| `CL1` | WTI crude oil front-month futures ($/bbl) |
| `US2Y` | US 2-year Treasury yield |
| `US2Y Breakeven` | 2-year breakeven inflation rate |
| `US Core CPI` | US core CPI (ex food & energy) |
| `US10Y` | US 10-year Treasury yield |
| `Fed Balance Sheet` | Federal Reserve total assets (proxy for QT pace) |
| `US10Y Breakeven` | 10-year breakeven inflation rate |
| `US2Y10Y Spread` | 2s10s yield curve spread (trade P&L driver) |

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
