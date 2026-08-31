# Harbourstone Completion Sprint 1 Validation Record

**Validation date:** 31 August 2026  
**Status:** Calculation and portfolio engines tested and user-defended; live Yahoo dataset pending  
**Test command:** `python -m pytest -q`

## Scope

Sprint 1 implements and validates:

- Annualised geometric return, annualised volatility, Sharpe ratio and Sortino ratio
- Maximum drawdown, beta to VWRL, historical Value at Risk and Expected Shortfall
- Equal-weight, 60/40 and illustrative user-defined portfolios
- Weight, constraint, unit, missing-data and return-contribution reconciliations

## Frequency, units and sign conventions

| Output | Input frequency | Calculation convention | Reported unit |
| --- | --- | --- | --- |
| Annualised return | Monthly | Geometric compounding, annualised by 12 / observations | Decimal annual rate |
| Volatility | Daily | Sample standard deviation multiplied by square root of 252 | Decimal annual rate |
| Sharpe | Daily | Annualised arithmetic mean excess return divided by annualised volatility | Dimensionless |
| Sortino | Daily | Annualised arithmetic return above target divided by downside deviation | Dimensionless |
| Maximum drawdown | Daily | Worst wealth / previous peak minus one, with starting wealth of 1 | Negative decimal return |
| Beta | Daily | Covariance with VWRL divided by VWRL variance | Dimensionless |
| Historical VaR | Daily | Negative fifth percentile, floored at zero | Positive daily loss magnitude |
| Expected Shortfall | Daily | Mean loss on observations at or below the fifth percentile | Positive daily loss magnitude |

The default annual risk-free rate and minimum acceptable return are both 0%. Historical VaR and Expected Shortfall use 95% confidence. A value such as `0.05` means 5%; ratios and beta are not percentages.

## Independent manual formula checks

These deterministic examples are independently calculable without market data and are also asserted in the tests.

1. Twelve monthly returns of 1% compound to:

   `(1.01 ^ 12) - 1 = 0.126825030132`, or 12.6825% annualised.

2. Returns of -10%, +5% and -20% create wealth of 0.90, 0.945 and 0.756. Starting from 1.00, maximum drawdown is:

   `0.756 / 1.00 - 1 = -0.244`, or -24.4%.

3. If an asset return equals `1% + 2 × benchmark return`, its beta is exactly 2 because the constant has zero covariance with the benchmark.

4. For returns of -10%, -5%, 0%, +5% and +10% at 80% confidence, linear historical VaR is 6% and Expected Shortfall is 10%. Expected Shortfall is at least as severe as VaR.

5. Monthly asset contribution is `target weight × asset monthly return`. Contributions are checked row by row against the portfolio return. Annualised arithmetic contributions are checked against `mean monthly portfolio return × 12`; they are not presented as an additive decomposition of geometric CAGR.

## Portfolio weight reconciliation

| Portfolio | Global equity | UK equity | UK gilts | Global bonds | Sterling credit | Gold | Commodities | Total | Fixed income | Maximum asset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Equal weight | 14.29% | 14.29% | 14.29% | 14.29% | 14.29% | 14.29% | 14.29% | 100.00% | 42.86% | 14.29% |
| 60/40 | 40.00% | 20.00% | 15.00% | 15.00% | 10.00% | 0.00% | 0.00% | 100.00% | 40.00% | 40.00% |
| User defined | 35.00% | 10.00% | 15.00% | 20.00% | 10.00% | 7.00% | 3.00% | 100.00% | 45.00% | 35.00% |

All three are long only, fully invested, at or below the 40% single-asset cap and at or above the 30% fixed-income minimum. The 60/40 reference was corrected from 45%/15% global/UK equity to 40%/20% because the earlier global-equity weight breached Harbourstone's 40% cap.

The user-defined portfolio is an illustrative baseline, not the final recommendation. It combines 45% equity, 45% fixed income and 10% real assets, including a limited 7% allocation to gold.

## Rebalancing and missing-data treatment

- Monthly strategic returns use target weights and therefore represent rebalancing each month.
- The daily portfolio path lets weights drift within each calendar month and resets them at the next month boundary.
- Portfolio calculations accept only the already validated common return rows for all seven assets.
- No price or return is forward-filled; a missing input stops the calculation instead of creating an artificial 0% return.
- Inputs and weights are decimals, and all weight vectors are normalised only after passing the 100% tolerance check.

## Automated evidence

The complete suite currently passes 48 tests covering configuration, data ingestion, data quality, return reconstruction, all eight metrics, portfolio constraints, monthly rebalancing, contribution totals, approval boundaries and output metadata.

## User defence

Yusuf completed the Sprint 1 spoken defence on 31 August 2026. He explained the £100m fictional mandate, CPI +3% objective, spending and portfolio constraints; named and interpreted the eight metrics; distinguished equal capital from equal risk; justified correcting the 60/40 reference; explained the common-date and no-forward-fill rules; described the contribution reconciliation; linked the analysis to client suitability; and stated the historical-data and live-provider limitations. The defence is approved.

## Live-data boundary

The live Yahoo Finance retry on 31 August 2026 returned a rate-limit response for all seven tickers. Therefore no historical asset or portfolio performance values are claimed in this record. The code and deterministic formula checks are validated, but the universe remains provisional until a successful live download passes the existing common-history and data-quality gates.
