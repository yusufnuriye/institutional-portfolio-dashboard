# CV and LinkedIn copy

## CV project entry

**Harbourstone Investment Portfolio Project | Independent | September 2026**

- Built a tested Streamlit portfolio dashboard for a fictional £100 million UK charity, translating a CPI +3% objective, 3% spending policy and investment constraints into five portfolios across seven liquid ETF and ETC proxies.
- Implemented performance, downside and tail-risk metrics, contribution analysis, constrained optimisation, sensitivity and stress testing in Python; reconciled weights and contribution totals through 63 automated tests and presented a provisional allocation in an investment memo and five-slide committee deck.

## Concise LinkedIn post

I’ve completed v1 of my Harbourstone institutional portfolio project, built around a fictional £100 million UK charitable foundation.

The project translates a client mandate into five portfolio approaches across seven liquid asset-class proxies. I implemented annualised return and volatility, Sharpe and Sortino ratios, drawdown, beta, VaR, Expected Shortfall, return and risk contributions, constrained optimisation, sensitivity analysis and hypothetical stress tests.

The main lesson was that a mathematically attractive portfolio is not automatically the right client portfolio. My maximum-Sharpe result concentrated in three sleeves, so I treated it as a diagnostic and advanced a more diversified policy allocation for further due diligence.

Evidence completed:

- 63 automated tests
- Clean-start Streamlit smoke test
- Reconciled portfolio weights and return/risk contributions
- Investment memo and five-slide committee summary

One limitation matters: Yahoo Finance rate-limited the final live-data run, so the committed numerical results use clearly labelled deterministic synthetic data. The app and calculation workflow are validated; historical performance is not claimed.

Repository: https://github.com/yusufnuriye/institutional-portfolio-dashboard

#Python #Streamlit #AssetManagement #PortfolioManagement #InvestmentResearch
