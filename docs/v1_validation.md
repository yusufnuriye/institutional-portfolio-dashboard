# V1 validation record

## Environment

- Validation date: 23 September 2026
- Python: 3.12
- Operating mode: deterministic demonstration
- Seed: 20260923
- Demonstration period: 2 January 2018 to 22 September 2026
- Live-data status: Yahoo Finance returned rate-limit errors for all seven tickers

## Automated evidence

```text
63 passed in 13.25s
```

The suite covers configuration, ingestion, cache matching, missing observations, common-date alignment, price validity, extreme-move review, return reconstruction, metric units and signs, weight constraints, monthly rebalancing, return contribution reconciliation, deterministic demo generation, both optimisers, solver failure, sensitivity analysis, risk contribution reconciliation, stress arithmetic, suitability and Streamlit startup.

## Manual checks

| Check | Result |
| --- | --- |
| Clean virtual environment installed from `requirements.txt` | Passed |
| All five portfolio weight sums equal 1.0 | Passed |
| All weights are long only and no weight exceeds 40% | Passed |
| Every portfolio holds at least 30% fixed income | Passed |
| Annualised arithmetic return contributions reconcile | Passed |
| Component volatility contributions reconcile | Passed |
| Expected Shortfall is at least VaR for every portfolio | Passed |
| Both core optimiser runs converge and pass post-solver validation | Passed |
| Eighteen sensitivity runs complete | Passed |
| Streamlit clean-start health endpoint returns `ok` | Passed |

## Commands

```bash
python -m pytest -q
python -m src.v1 --mode demo --output-dir outputs/demo
python -m streamlit run app.py --server.headless true
```

## Claim boundary

The code, calculations, demonstration workflow and interface are validated. Historical performance is not validated because the live provider rate-limited the final attempt. All committed numerical findings are labelled synthetic.
