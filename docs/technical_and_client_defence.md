# Technical and client defence

## Why use geometric return for growth but arithmetic return for contribution

Geometric return measures compounded wealth across periods. Arithmetic portfolio return is a weighted sum in each period, so asset contributions reconcile additively to it. Geometric CAGR is not additively decomposable.

## Why use daily returns for risk and monthly returns for strategy

Daily observations capture short-term variation and provide a larger sample for volatility, drawdown, beta, VaR and Expected Shortfall. Month-end observations reduce daily noise and match the strategic horizon used for CAGR and optimisation.

## Why exclude forward-filled prices

Forward-filling asserts that an unobserved price was unchanged. It can create an artificial 0% return and distort volatility, correlation, beta and risk contributions. The pipeline therefore keeps only dates on which every asset has a valid price.

## What VaR and Expected Shortfall mean

The 95% historical VaR is the daily loss threshold reached or exceeded in roughly the worst 5% of observed days. Expected Shortfall is the average loss within that tail. Both are positive loss magnitudes in this project. Neither is a maximum possible loss.

## Why equal weight is not equal risk

Assets have different volatility and correlation. In the demonstration policy portfolio, global and UK equities hold 45% of capital but contribute about 82% of covariance-based volatility.

## Why not recommend maximum Sharpe

The maximum-Sharpe result depends on fitted sample means and covariance. It concentrates in VWRL, IGLT and AGBP, omitting four sleeves. The diversified policy portfolio is easier to govern, meets the formal constraints and retains growth, defensive and inflation-sensitive exposures.

## What the optimisation constraints do

Both optimisers require weights to sum to 100%, keep each asset between 0% and 40%, hold at least 30% across IGLT, AGBP and SLXX, and avoid leverage and short selling. Successful solver output is validated a second time; a failed solver raises a visible error.

## What the client recommendation actually claims

The diversified policy portfolio is a provisional comparator for further due diligence. It is not an implementation recommendation and does not claim to achieve CPI +3%. A real decision would require validated live data, CPI history, product costs, a grant reserve, governance rules and out-of-sample analysis.

## How the live-data limitation is handled

The final Yahoo Finance attempt was rate-limited for all seven tickers. The application therefore defaults to deterministic synthetic data with a prominent warning. Live mode fails closed instead of showing partial or stale results. This preserves a reproducible demo without presenting synthetic values as market history.
