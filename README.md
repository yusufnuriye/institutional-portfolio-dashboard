# Harbourstone Institutional Portfolio Dashboard

A tested portfolio-construction and risk dashboard for a fictional £100 million UK charitable foundation. The project converts a client mandate into transparent allocations, performance and risk analytics, constrained optimisation, stress testing and a provisional client conclusion.

> **Data status:** the application opens in a deterministic demonstration mode because Yahoo Finance rate-limited the live validation attempt on 23 September 2026. Demonstration results are synthetic. They prove that the workflow is reproducible; they are not historical evidence, forecasts or investment advice.

## What v1 delivers

- Seven liquid LSE-listed proxies across global and UK equities, government and corporate bonds, gold and broad commodities
- Complete-date adjusted-price handling with no forward-filling
- Annualised return, volatility, Sharpe, Sortino, maximum drawdown, beta, historical VaR and Expected Shortfall
- Equal-weight, 60/40 and diversified policy portfolios
- Long-only constrained minimum-variance and maximum-Sharpe portfolios
- Weight, unit, return-contribution and volatility-risk-contribution reconciliations
- Optimisation sensitivity across asset caps and fixed-income floors
- Three transparent hypothetical stress scenarios
- Rule-based mandate and client-suitability checks
- A five-tab Streamlit dashboard, investment memo and five-slide committee summary
- 63 automated tests plus a clean-start Streamlit health check

## Client mandate

Harbourstone Foundation is fictional. Its investment brief is:

| Item | Requirement |
| --- | --- |
| Portfolio | £100 million, GBP reporting currency |
| Objective | Seek UK CPI +3% annualised over rolling five-year periods |
| Spending | Approximately 3% a year |
| Horizon and risk | At least five years; moderate risk |
| Asset bounds | Long only, no leverage, 0–40% per asset |
| Defensive floor | At least 30% across IGLT, AGBP and SLXX |
| Liquidity | Publicly traded proxies; retain one year of planned grants in liquid assets |

The objective and drawdown reference are aspirations, not guarantees. The model does not ingest CPI, so it does not claim that any portfolio has achieved CPI +3%.

## Reproduce the project

Python 3.12 is the reference environment.

```bash
git clone https://github.com/yusufnuriye/institutional-portfolio-dashboard.git
cd institutional-portfolio-dashboard
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.v1 --mode demo --output-dir outputs/demo
python -m streamlit run app.py
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.v1 --mode demo --output-dir outputs/demo
python -m streamlit run app.py
```

Open `http://localhost:8501`. The default mode works without a network connection and always recreates the same results with seed `20260923`.

To retry the validated live path:

```bash
python -m src.v1 --mode live --refresh --output-dir outputs/live
```

Live mode stops instead of publishing partial results when a ticker is absent, prices are invalid, the common sample is shorter than five years, a one-day adjusted move exceeds 50%, or compounded returns do not reconstruct price growth.

## Demonstration portfolios

| Portfolio | Purpose | Key allocation feature |
| --- | --- | --- |
| Equal weight | Naive diversification reference | 14.3% in each sleeve |
| 60/40 reference | Transparent equity and bond comparator | 60% equity, 40% fixed income |
| Diversified policy | Client-oriented policy comparator | 45% equity, 45% fixed income, 10% real assets |
| Minimum variance | Constraint sensitivity | Minimises in-sample covariance-based volatility |
| Maximum Sharpe | Constraint sensitivity | Maximises in-sample arithmetic excess return per unit of volatility |

All five portfolios are fully invested, long only, capped at 40% per asset and hold at least 30% fixed income.

## Demonstration findings

These values come from deterministic synthetic returns from 2 January 2018 to 22 September 2026.

| Portfolio | CAGR | Volatility | Sharpe | Max drawdown | 95% daily ES |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal weight | 1.6% | 7.4% | 0.20 | -27.3% | 0.95% |
| 60/40 reference | 4.6% | 9.9% | 0.47 | -17.1% | 1.28% |
| Diversified policy | 3.9% | 8.0% | 0.48 | -15.4% | 1.03% |
| Minimum variance | 2.3% | 5.6% | 0.37 | -16.8% | 0.72% |
| Maximum Sharpe | 4.4% | 7.0% | 0.61 | -12.5% | 0.90% |

The diversified policy portfolio is the **provisional client comparator**, subject to live-data validation and fuller due diligence. It holds all seven sleeves and satisfies the coded mandate. The maximum-Sharpe result is not selected automatically because it is concentrated in only three sleeves and depends on in-sample estimates.

The policy portfolio remains equity-risk-led: VWRL and CUKX contribute about 82% of covariance-based portfolio volatility in the demonstration. Its worst hypothetical result is -10.0% in the growth shock, compared with -13.8% for the 60/40 reference. These scenarios are weighted asset-shock assumptions, not forecasts.

## Methodology controls

- Inputs are decimal returns: `0.01` means 1%.
- CAGR uses monthly compounded returns.
- Volatility, Sharpe, Sortino, drawdown, beta, VaR and Expected Shortfall use daily returns.
- Volatility uses sample standard deviation and square-root-of-time annualisation.
- The default annual risk-free rate and minimum acceptable return are 0%.
- VaR and Expected Shortfall use the lower 5% historical tail and are shown as positive daily loss magnitudes.
- Portfolio paths reset to target weights at each calendar-month boundary.
- Arithmetic return contributions equal weight × mean monthly return × 12 and reconcile to arithmetic portfolio return. They do not decompose geometric CAGR.
- Component volatility contributions equal weight × marginal volatility and reconcile to total covariance-based portfolio volatility.
- Optimisation uses SLSQP with explicit bounds and equality/inequality constraints. Failed solvers raise a visible error.

Full formulas, validation rules and scenario definitions are in [`docs/methodology.md`](docs/methodology.md). The evidence outputs are in [`outputs/demo`](outputs/demo).

## Repository map

```text
.
├── app.py                         # Streamlit interface
├── config/assets.yml              # Universe, mandate and reference weights
├── src/
│   ├── data_pipeline.py           # Adjusted-price download and caching
│   ├── data_quality.py            # Common-history integrity checks
│   ├── demo_data.py               # Explicit deterministic demonstration data
│   ├── metrics.py                 # Eight performance and risk metrics
│   ├── portfolios.py              # Portfolio paths and return contributions
│   ├── optimisation.py            # Constrained optimisers and sensitivity
│   ├── risk.py                    # Volatility-risk contributions
│   ├── stress.py                  # Hypothetical asset shocks
│   ├── suitability.py             # Mandate checks and provisional conclusion
│   └── v1.py                      # End-to-end workflow and evidence export
├── tests/                          # 63 automated tests
├── docs/                           # Mandate, methodology, memo and IC deck
└── outputs/demo/                   # Reproducible evidence tables and manifest
```

## Evidence

Validated on 23 September 2026 in a clean Python 3.12 virtual environment:

```text
63 passed
Streamlit clean-start health endpoint: ok
Five portfolio weight sums: 1.0
Return contribution reconciliation: passed
Risk contribution reconciliation: passed
Optimisation solver status: passed
```

## Known limitations

1. Yahoo Finance rate-limited the live validation attempt, so the committed numerical results are synthetic demonstrations rather than market-history findings.
2. `yfinance` is an unofficial research interface. Provider data can be revised, missing or inconsistent.
3. The core model does not ingest CPI, forecast inflation or prove delivery of CPI +3%.
4. Optimisation is in-sample and sensitive to estimated means, covariance, the sample window and constraint choices.
5. External fees, tax, bid–ask spreads, transaction costs, market impact and charitable withdrawals are not modelled.
6. GBP-listed prices embed currency effects. The model does not separate local-asset and foreign-exchange returns.
7. Stress scenarios are linear one-period shocks. They omit nonlinear payoffs, changing correlations, trading suspensions and liquidity stress.
8. The seven funds and ETCs are proxies. Overlap exists across global and UK equities, bond sleeves, gold and commodities.
9. Historical or synthetic risk measures cannot bound future losses. VaR and Expected Shortfall do not represent the maximum possible loss.

## Documents

- [`docs/methodology.md`](docs/methodology.md)
- [`docs/investment_memo.md`](docs/investment_memo.md)
- `docs/Harbourstone_Investment_Memo.docx`
- `docs/Harbourstone_IC_Summary.pptx`
- [`docs/v1_validation.md`](docs/v1_validation.md)
- [`docs/technical_and_client_defence.md`](docs/technical_and_client_defence.md)
- [`docs/cv_and_linkedin.md`](docs/cv_and_linkedin.md)

## Disclaimer

This repository is an educational simulation for a fictional client. It does not manage real money and does not constitute investment advice or a recommendation to trade.
