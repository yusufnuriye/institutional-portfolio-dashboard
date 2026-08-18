# Assumption Register

This register separates locked design decisions from items that must be validated with data. Any change should record a reason rather than silently rewriting history.

| ID | Assumption or decision | Status | Reason / validation required |
| --- | --- | --- | --- |
| A01 | The client is the fictional Harbourstone Foundation with £100m in assets. | Locked | Creates a concrete institutional decision context without claiming real-money management. |
| A02 | GBP is the reporting and base currency. | Locked | The client is UK based. |
| A03 | The objective is UK CPI +3% annualised over rolling five-year periods, before transaction costs and tax. | Locked and user-verified | Matches a balanced-growth real-return mandate; it is aspirational, not guaranteed. Approved by Yusuf on 10 Aug 2026 after an understanding check. |
| A04 | The core model does not ingest or forecast CPI. | Locked for core | The inflation objective will be contextual; adding a robust inflation pipeline is lower priority than the required portfolio and risk engine. |
| A05 | The drawdown reference is approximately 15–20%, not a hard guaranteed limit. | Locked and user-verified | Historical drawdown cannot cap future loss. Approved by Yusuf on 10 Aug 2026 after correctly explaining drawdown, recovery asymmetry and moderate risk. |
| A06 | Portfolios are long only, unlevered, fully invested and capped at 40% per asset. | Locked and user-verified | Core client and optimisation constraints. Approved by Yusuf on 10 Aug 2026 after explaining concentration, long-only investing and leverage. |
| A07 | Mandate-constrained portfolios hold at least 30% across IGLT, AGBP and SLXX. | Locked and user-verified | Provides a minimum liquid fixed-income allocation for a moderate-risk client. Approved by Yusuf on 10 Aug 2026 after identifying all three bond sleeves and verifying the 30% calculation. |
| A08 | The initial universe contains seven LSE-listed GBP proxies whose tickers, exposure and instrument types are confirmed by official provider pages. | Instrument structure locked and user-verified; data quality provisional | Day 2 must still confirm actual data availability, common history, numeric observations and missing values. Yusuf approved the official-source verification on 18 Aug 2026 after distinguishing ETFs from ETCs. |
| A09 | The earliest common sample is expected to begin no earlier than 23 Nov 2017. | Provisional | AGBP is the youngest selected LSE listing; the actual Yahoo history may start later. |
| A10 | Adjusted market prices will be requested from Yahoo Finance through `yfinance` with `auto_adjust=True`. | Implementation locked and user-verified; live feed pending | The pipeline extracts adjusted closes and rejects unusable series. Day 2 must still inspect the live returned observations. Approved by Yusuf on 18 Aug 2026 after explaining distribution adjustment and validation. |
| A11 | Downloaded adjusted-close data and request metadata will be cached locally and refreshed only on explicit request or when the request changes. | Locked and user-verified | Supports reproducibility, records the requested tickers and dates, and avoids needless repeated downloads. Approved by Yusuf on 18 Aug 2026 after an understanding check. |
| A12 | Missing prices will not be forward-filled; common history uses only dates with a valid price for all seven assets. | Locked and user-verified | Forward-filling would create artificial 0% returns and could distort volatility and correlation. Approved by Yusuf on 18 Aug 2026 after an understanding check. |
| A13 | Daily simple returns are used for daily risk statistics; month-end simple returns are used for optimisation inputs. | Locked and user-verified | Daily observations capture short-term fluctuations, while monthly observations reduce daily noise and better match the strategic horizon. Approved by Yusuf on 18 Aug 2026. |
| A14 | CAGR is calculated geometrically from cumulative wealth and elapsed time, not confused with arithmetic mean return. | Locked design | Required conceptual distinction. |
| A15 | Annualisation uses 252 trading days for daily statistics and 12 periods for monthly statistics. | Locked | Conventional approximation, to be labelled. |
| A16 | Historical portfolio paths assume monthly rebalancing to target weights. | Locked design | More defensible for a strategic institutional portfolio than implicit daily rebalancing. |
| A17 | The default annual risk-free rate is 0%, clearly labelled and user-adjustable later if time allows. | Locked for core | Avoids mixing a current cash rate with a long historical sample. |
| A18 | Historical VaR and Expected Shortfall use a 95% confidence level by default. | Locked for core | Transparent core tail-risk setting. |
| A19 | VWRL is the equity-market benchmark for beta. | Provisional | It represents the core global growth exposure; confirm data quality on Day 2. |
| A20 | A GBP exchange listing is not treated as proof of currency hedging. | Locked | VWRL, SGLN and AGCP retain underlying foreign-currency or USD-linked economic exposure. |
| A21 | The model will not decompose returns into local-asset and FX components. | Locked for core | Currency effects remain embedded in GBP-listed prices and will be disclosed as a limitation. |
| A22 | Fees embedded in product prices remain in observed returns; external fees, tax, spreads, trading costs and market impact are excluded. | Locked for core | Keeps the core model feasible while preventing a false claim of net client performance. |
| A23 | Optimisation and headline historical comparisons are in-sample unless explicitly labelled otherwise. | Locked | No out-of-sample design has yet been implemented. |
| A24 | Historical stress windows will be defined independently of portfolio results. | Locked design | Reduces cherry-picking risk. |
| A25 | Hypothetical scenario loss is initially the weighted sum of visible asset shocks. | Locked for core | Transparent and testable, but ignores nonlinear effects, changing correlations and liquidity stress. |
| A26 | Harbourstone plans to distribute approximately 3% annually, initially about £3m. | Locked and user-verified | Broadly aligns spending with the real-growth component of the CPI +3% objective, before fees and costs; achievement is not guaranteed. Approved by Yusuf on 10 Aug 2026 after an understanding check. |
| A27 | The next 12 months of planned grants should remain in cash or readily saleable investments. | Locked and user-verified | Supports timely grant payments without forcing sales of illiquid or depressed assets. Approved by Yusuf on 10 Aug 2026 after an understanding check. |
| A28 | Historical portfolio performance will not deduct actual charitable withdrawals. | Locked for core | Keeps the investment engine focused, but means the dashboard does not model Harbourstone's complete post-spending asset path. |
| A29 | SGLN and AGCP are ETCs rather than ETFs: SGLN is physically backed by gold, while AGCP is a debt security using a synthetic, fully funded collateralised swap for broad commodity-futures exposure. | Locked and user-verified | Records the legal and replication structures accurately instead of labelling every proxy as an ETF. Approved by Yusuf on 18 Aug 2026 after an understanding check. |
| A30 | The validated common history must contain at least 1,260 complete daily observations spanning at least five years; adjusted-price moves above 50% in one day require manual review. | Locked and user-verified | Ensures the sample can support five-year analysis and prevents a possible unit, split or provider error entering silently. Approved by Yusuf on 18 Aug 2026. |
| A31 | Compounded daily returns must reconstruct each asset's end-to-start adjusted-price growth within numerical tolerance. | Locked and user-verified | A failed reconstruction indicates a calculation or data inconsistency and stops the pipeline. Approved by Yusuf on 18 Aug 2026 after an understanding check. |

## Change log

| Date | IDs changed | Change | Reason |
| --- | --- | --- | --- |
| 10 Aug 2026 | A01–A25 | Initial Day 1 register created. | Establish the mandate before financial analysis begins. |
| 10 Aug 2026 | A03 | Investment objective user-verified and approved. | Yusuf demonstrated the CPI +3% calculation and explained why the target is not guaranteed. |
| 10 Aug 2026 | A05 | Risk tolerance user-verified and approved. | Yusuf calculated drawdown and explained recovery asymmetry, uncertainty and the meaning of moderate risk. |
| 10 Aug 2026 | A26–A28 | Spending and liquidity policy user-verified and approved. | Yusuf linked the 3% spending policy to the CPI +3% objective and explained the need for 12 months of liquid grant funding. |
| 10 Aug 2026 | A06–A07 | Strategic investment constraints user-verified and approved. | Yusuf explained the concentration and fixed-income rules, distinguished the three bond sleeves and stated why historical optimisation is not a forecast. |
| 18 Aug 2026 | A08–A09, A29 | Official product sources and instrument structures user-verified and approved. | Confirmed the seven LSE tickers, corrected the expected earliest common listing date to 23 Nov 2017, and distinguished the two ETCs from the five ETFs. |
| 18 Aug 2026 | A10–A11 | Adjusted-price ingestion and caching implementation user-verified and approved. | The pipeline reads the configured universe, requests adjusted closes, validates basic structure, preserves missing observations and reuses only a matching cache. |
| 18 Aug 2026 | A12, A30 | Common-history alignment and validation implementation user-verified and approved. | Uses complete shared dates, reports every removed observation, avoids forward-filling, enforces minimum history and flags extreme daily moves for review. |
| 18 Aug 2026 | A13, A31 | Daily, monthly and cumulative-return implementation user-verified and approved. | Yusuf calculated a negative simple return correctly, distinguished daily risk from monthly strategy and explained the reconstruction check. |
