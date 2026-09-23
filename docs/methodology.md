# Methodology

## Purpose and decision boundary

The project tests whether a liquid seven-sleeve portfolio can be evaluated consistently against Harbourstone Foundation's fictional mandate. It compares three transparent allocations with constrained minimum-variance and maximum-Sharpe portfolios. The optimisers inform the decision; they do not select the recommendation automatically.

The committed numerical evidence uses deterministic synthetic data. It verifies calculation and interface behaviour but cannot support claims about realised market performance. Live mode must pass every data check before any historical result is used.

## Data provenance

The configured universe contains five ETFs and two ETCs. Prices are expressed through their London-listed GBP lines. A GBP trading line does not prove that the economic exposure is currency hedged. AGBP is explicitly GBP-hedged; VWRL, SGLN and AGCP retain material unhedged exposure.

Live mode requests adjusted closing prices through `yfinance` with `auto_adjust=True`. Adjusted prices are needed because several products distribute income. The project caches the price frame with request metadata so that a repeat analysis can identify the requested tickers and dates.

The default offline mode generates a deterministic multivariate return sample with seed `20260923`. Target means, volatility and factor loadings create plausible correlations, but the paths are synthetic. The interface, evidence manifest and documents label them as demonstrations.

## Data integrity

The live workflow applies these checks before calculating returns:

1. All seven tickers must be present with numeric positive prices.
2. Dates must be unique and increasing.
3. Missing observations remain visible until alignment. They are never forward-filled.
4. The common sample keeps only dates on which every asset has a valid price.
5. At least 1,260 common observations spanning five years are required.
6. Any adjusted-price move larger than 50% in one day stops the workflow for manual review.
7. Compounded daily returns must reconstruct each asset's end-to-start adjusted-price growth within numerical tolerance.

Forward-filling is excluded because it would assert that an unobserved price was unchanged. That could create an artificial 0% return and distort volatility, correlation, beta and portfolio risk.

## Return calculations

For price \(P_t\), the simple return is:

\[
r_t = \frac{P_t}{P_{t-1}} - 1
\]

All code inputs use decimals, so `0.05` means 5%. Daily returns support risk measurement. Month-end returns support strategic CAGR, portfolio contributions and optimisation.

The annualised geometric return over \(n\) monthly observations is:

\[
R_g = \left(\prod_{t=1}^{n}(1+r_t)\right)^{12/n}-1
\]

Portfolio returns use monthly target weights. Daily portfolio paths drift within each month and reset to their target weights at the next calendar-month boundary.

## Risk metrics

Annualised volatility is the sample standard deviation of daily returns multiplied by \(\sqrt{252}\).

Sharpe ratio uses mean daily excess return, annualised arithmetically, divided by annualised volatility. The default annual risk-free rate is 0%.

Sortino ratio replaces total volatility with downside deviation below a 0% annual minimum acceptable return. Large positive returns increase volatility but do not enter downside deviation.

Maximum drawdown is the worst decline from a prior cumulative-wealth peak. It is shown as a negative decimal.

Beta to VWRL is:

\[
\beta_i = \frac{\operatorname{Cov}(r_i,r_m)}{\operatorname{Var}(r_m)}
\]

Historical 95% VaR is the positive loss magnitude at the 5th percentile of daily returns. Expected Shortfall is the positive mean loss at or beyond that threshold. Neither measure is a maximum possible loss.

## Portfolio construction

The equal-weight portfolio assigns 1/7 to every sleeve. The 60/40 reference holds 40% VWRL, 20% CUKX, and 40% across IGLT, AGBP and SLXX. The diversified policy portfolio holds 35% VWRL, 10% CUKX, 45% fixed income and 10% across gold and commodities.

Every mandate-constrained portfolio must satisfy:

\[
\sum_i w_i=1,\quad 0\leq w_i\leq0.40,\quad
\sum_{i\in FI}w_i\geq0.30
\]

The minimum-variance portfolio minimises \(w^T\Sigma w\). The maximum-Sharpe portfolio maximises \((w^T\mu-r_f)/\sqrt{w^T\Sigma w}\). Both use SLSQP with monthly sample means and covariance annualised by 12. The program rejects unsuccessful solver output and validates the returned weights again.

Sensitivity analysis repeats both objectives for 30%, 35% and 40% asset caps and 30%, 40% and 50% fixed-income floors. Each run records success, annualised arithmetic return, volatility and Sharpe ratio.

## Contribution analysis

Periodic arithmetic return contribution is \(w_i r_{i,t}\). Contributions sum exactly to portfolio return in each month. Annualised contributions are the mean monthly contribution multiplied by 12. They do not add to geometric CAGR because geometric growth compounds across periods.

For annual covariance \(\Sigma\) and portfolio volatility \(\sigma_p\), marginal volatility is \(\Sigma w/\sigma_p\). Component volatility is \(w_i(\Sigma w)_i/\sigma_p\). Component values reconcile to \(\sigma_p\), and percentage contributions reconcile to 100%. Negative contributions are possible when an asset diversifies portfolio risk.

## Stress testing

The project applies three visible one-period shock sets:

| Scenario | Main assumptions |
| --- | --- |
| Growth shock | Global equities -25%, UK equities -22%, defensive bonds +3% to +4%, gold +8% |
| Inflation shock | Equities -10% to -12%, bonds -8% to -10%, gold +6%, commodities +15% |
| Rates and credit shock | Equities -8% to -10%, gilts -12%, global bonds -10%, sterling credit -15% |

Portfolio stress return is the weighted sum of the asset shocks. The method is easy to audit but omits nonlinear pricing, dynamic correlation, illiquidity and rebalancing during the event.

## Suitability logic

The engine checks full investment, long-only weights, the 40% cap, the 30% fixed-income floor, number of active sleeves, demonstration drawdown and the worst hypothetical stress result. It provisionally identifies the diversified policy portfolio because it meets the coded mandate and retains all seven sleeves.

This conclusion remains conditional. The CPI +3% objective is untested, live history is unvalidated, liabilities are not modelled and the proposed allocation would need formal governance, cost and implementation review before use by a real investor.

## Reproducibility and tests

Run:

```bash
python -m pytest -q
python -m src.v1 --mode demo --output-dir outputs/demo
python -m streamlit run app.py
```

The 63-test suite covers input units, annualisation, reconstruction, missing-data treatment, weight constraints, monthly rebalancing, contributions, both optimisers, deliberate solver failure, sensitivity runs, scenario arithmetic, suitability logic and the Streamlit demo path.

## Limitations

- The committed results are synthetic because Yahoo Finance rate-limited the live validation attempt on 23 September 2026.
- The model does not ingest CPI, external fees, tax, transaction costs, market impact, liabilities or charitable withdrawals.
- Optimisation is in-sample and unstable when estimated inputs change.
- FX effects remain embedded in GBP-listed prices and are not decomposed.
- Proxies overlap, and publicly traded products can still become difficult to trade under stress.
- Linear hypothetical shocks cannot reproduce a complete crisis.
- Historical and synthetic statistics cannot guarantee future outcomes.
