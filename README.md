# Institutional Multi-Asset Portfolio Strategy and Risk Dashboard

An educational portfolio-construction project for a fictional UK institutional investor. The project asks how a £100 million balanced-growth portfolio should be allocated across liquid asset classes while balancing return objectives, drawdown risk, diversification, liquidity, inflation sensitivity and resilience under adverse market conditions.

The final output will compare simple, user-defined and constrained-optimisation portfolios, then make a reasoned institutional recommendation. Historical results will be treated as evidence rather than forecasts, and the mathematically optimal portfolio will not automatically become the recommendation.

## Project status

**Day 2 of 10 — 100% of the planned implementation complete.** Official-source verification, adjusted-price ingestion, matching-cache behaviour, common-history validation and daily/monthly return calculations are implemented, tested and user-approved. The first live Yahoo Finance download could not be executed in the build workspace, so the universe remains provisional until a live run creates a passing data-quality report. No portfolio recommendation has been produced.

## Client mandate

Harbourstone Foundation is a fictional UK institutional investor with a £100 million balanced-growth portfolio.

- **Base currency:** GBP
- **Horizon:** At least five years
- **Objective:** Seek UK CPI inflation plus 3% annualised over rolling five-year periods, before transaction costs and tax
- **Risk profile:** Moderate
- **Drawdown reference:** Avoid losses materially beyond approximately 15–20%, while recognising that historical analysis cannot guarantee this outcome
- **Spending policy:** Distribute approximately 3% annually to charitable causes (initially about £3 million)
- **Liquidity:** Use liquid, publicly traded index-fund or exchange-traded product proxies
- **Grant reserve:** Keep the next 12 months of planned grants in cash or readily saleable investments
- **Rebalancing:** Monthly in the core historical portfolio analysis

### Core constraints

- Long only; no leverage and no short selling
- Portfolio weights must sum to 100%
- No individual asset may exceed 40%
- At least 30% must be allocated to the three fixed-income sleeves in mandate-constrained portfolios
- All candidate holdings must be publicly traded and sufficiently liquid for this educational simulation
- Fees, tax, transaction costs and market impact are excluded from the core model
- Historical optimisation is in-sample evidence, not proof of future performance

The full mandate is documented in [`docs/mandate.md`](docs/mandate.md).

## Key question

How should a fictional UK institutional investor allocate a £100 million portfolio across major liquid asset classes while balancing return objectives, drawdown risk, diversification, liquidity and resilience under adverse market conditions?

## Initial asset universe

The shortlist intentionally combines growth, defensive and inflation-sensitive exposures. It remains provisional until Day 2 confirms data quality and a sufficiently long common history.

| Ticker | Vehicle | Exposure | Portfolio role | GBP treatment | LSE listing start |
| --- | --- | --- | --- | --- | --- |
| `VWRL.L` | ETF | Global equities | Core growth | GBP listing; underlying exposure unhedged | 23 May 2012 |
| `CUKX.L` | ETF | UK large-cap equities | Home-market growth tilt | GBP assets and GBP listing | 15 Sep 2010 |
| `IGLT.L` | ETF | UK government bonds | Sovereign defence and duration | GBP assets and GBP listing | 1 Dec 2006 |
| `AGBP.L` | ETF | Global investment-grade bonds | Diversified defensive fixed income | GBP-hedged share class | 23 Nov 2017 |
| `SLXX.L` | ETF | Sterling investment-grade corporate bonds | Credit income and diversification | GBP assets and GBP listing | 29 Mar 2004 |
| `SGLN.L` | Physical-metal ETC | Physical gold | Crisis and inflation-sensitive diversifier | GBP listing; gold exposure unhedged | 11 Apr 2011 |
| `AGCP.L` | Collateralised-swap ETC | Broad commodity futures | Inflation-sensitive diversifier | GBP listing; underlying USD index unhedged | 29 Oct 2007 |

The earliest possible common start is expected to be 23 November 2017 because `AGBP.L` is the youngest LSE listing. Day 2 will verify the actual Yahoo Finance histories, missing observations, adjusted-price behaviour and overlapping date range before the universe is finalised.

## Currency policy

GBP is the reporting currency. London-listed GBP price series will be used where available, but trading in GBP is not treated as equivalent to currency hedging.

- UK equities, gilts and sterling corporate bonds are GBP-denominated exposures.
- `AGBP.L` is explicitly a GBP-hedged global bond share class.
- `VWRL.L`, `SGLN.L` and `AGCP.L` are not currency-hedged. Their GBP market-price returns include the effect of sterling movements as well as the underlying asset exposure.
- The core project will not decompose asset returns into local-market and FX components. This will be stated as a limitation.

## Planned portfolio comparisons

1. Equal weight
2. Transparent 60/40 equity-bond reference
3. User-selected allocation
4. Minimum variance
5. Maximum historical Sharpe ratio
6. Final recommended institutional allocation

The 60/40 reference will initially allocate 45% to global equities, 15% to UK equities, 15% to UK gilts, 15% to GBP-hedged global aggregate bonds and 10% to sterling investment-grade credit.

## Methodology

Planned modules include:

- Adjusted historical-price ingestion, local caching and data-quality checks
- Daily and monthly simple returns, cumulative wealth and CAGR
- Volatility, Sharpe, Sortino, maximum drawdown, beta, historical VaR and Expected Shortfall
- Portfolio construction, return contribution and component risk contribution
- Long-only constrained minimum-variance and maximum-Sharpe optimisation
- Historical stress windows and transparent hypothetical asset shocks
- Client-suitability assessment and an investment recommendation with conditions and caveats

## Project structure

```text
institutional-portfolio-dashboard/
├── app.py
├── README.md
├── requirements.txt
├── config/
│   └── assets.yml
├── data/
│   └── cache/
├── docs/
│   ├── assumptions.md
│   └── mandate.md
├── outputs/
│   └── charts/
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── data_quality.py
│   └── returns.py
└── tests/
    ├── test_config.py
    ├── test_data_pipeline.py
    ├── test_data_quality.py
    └── test_returns.py
```

Day 2 added separate ingestion, data-quality and return modules under `src/`, with calculation tests under `tests/`. Financial calculations remain separate from the Streamlit presentation layer.

## Installation

Python 3.12 is the reference environment.

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app.py
```

## Build the Day 2 data and return outputs

From the project root, run:

```bash
python -m src.returns --refresh
```

This requests adjusted daily closes, writes a matching local cache, aligns all seven assets to complete shared dates, creates a data-quality report and saves daily, month-end and cumulative return files. The command stops rather than publishing outputs if a ticker is missing, the common sample is too short, a price is non-positive, a daily move exceeds the review threshold or compounded returns fail to reconstruct price growth.

The generated files remain under `data/cache/` and are deliberately excluded from Git because they can be downloaded again. A successful live run is required before changing the universe from provisional to final.

## Data sources

- Historical market prices: Yahoo Finance via `yfinance` (pipeline implemented; first live download still required)
- Product exposure, inception and currency facts: official Vanguard, iShares and WisdomTree product pages

`yfinance` is an unofficial research interface and is not affiliated with or endorsed by Yahoo. Downloaded data may contain errors, revisions, missing observations or inconsistent adjusted-price behaviour. Raw downloads will be cached and validated before calculations are performed.

## Assumptions

The live assumption register is in [`docs/assumptions.md`](docs/assumptions.md). Important initial assumptions include 252 trading days per year, 12 monthly periods per year, monthly portfolio rebalancing, a 0% default annual risk-free rate and 95% historical VaR/Expected Shortfall confidence.

## Main findings

Not yet available. Findings will only be written after the data pipeline, calculations and validation tests exist.

## Recommendation

Not yet available. The recommendation will be selected against the client mandate and will not automatically copy an optimiser output.

## Limitations

Known limitations already include proxy choice, a post-2017 common sample, unmodelled transaction costs and tax, unseparated currency effects, in-sample optimisation, unstable historical correlations and simplified hypothetical shocks. These will be refined as evidence is produced.

## Future improvements

Potential extensions such as out-of-sample testing, Black–Litterman, Monte Carlo simulation or factor analysis are out of scope until every core deliverable is complete.

## Educational disclaimer

This repository is an educational simulation using a fictional client. It does not manage real money and does not constitute investment advice, a recommendation to trade, or a guarantee of future performance.
