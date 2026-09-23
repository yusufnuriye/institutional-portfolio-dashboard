"""Deterministic demonstration data for an offline, reproducible Harbourstone demo.

The generated series are deliberately labelled as synthetic. They exist so the
analytics and interface can be tested without presenting fabricated market
history as investment evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data_pipeline import DataPipelineError
from src.returns import ReturnData, calculate_return_data


DEMO_SEED = 20260923
DEMO_START = "2018-01-02"
DEMO_END = "2026-09-22"
DEMO_NOTICE = (
    "Deterministic synthetic demonstration data; not historical market data, "
    "not a forecast and not investment advice."
)


@dataclass(frozen=True)
class DemoData:
    """Synthetic prices, calculated returns and provenance metadata."""

    prices: pd.DataFrame
    returns: ReturnData
    metadata: dict[str, object]


def build_demo_prices(
    tickers: list[str],
    *,
    seed: int = DEMO_SEED,
    start: str = DEMO_START,
    end: str = DEMO_END,
) -> pd.DataFrame:
    """Generate correlated, plausible-but-synthetic adjusted price paths."""
    expected = [
        "VWRL.L",
        "CUKX.L",
        "IGLT.L",
        "AGBP.L",
        "SLXX.L",
        "SGLN.L",
        "AGCP.L",
    ]
    if tickers != expected:
        raise DataPipelineError("Demo data requires the configured seven-ticker order.")

    dates = pd.bdate_range(start=start, end=end)
    if len(dates) < 1260:
        raise DataPipelineError("Demo data must span at least five years.")

    annual_returns = np.array([0.075, 0.060, 0.025, 0.035, 0.040, 0.055, 0.045])
    annual_volatility = np.array([0.170, 0.185, 0.075, 0.065, 0.085, 0.155, 0.190])

    # Four broad factors: growth, duration, inflation sensitivity and GBP/USD.
    loadings = np.array(
        [
            [0.85, -0.05, 0.10, 0.20],
            [0.78, -0.05, 0.18, 0.05],
            [-0.08, 0.90, -0.12, 0.00],
            [-0.02, 0.80, -0.05, 0.03],
            [0.18, 0.62, -0.02, 0.00],
            [-0.10, 0.10, 0.72, 0.36],
            [0.20, -0.08, 0.82, 0.28],
        ],
        dtype=float,
    )
    idiosyncratic = np.array([0.50, 0.58, 0.38, 0.34, 0.45, 0.62, 0.68])
    base_covariance = loadings @ loadings.T + np.diag(idiosyncratic**2)
    scale = annual_volatility / np.sqrt(np.diag(base_covariance))
    annual_covariance = np.diag(scale) @ base_covariance @ np.diag(scale)

    daily_mean = np.power(1.0 + annual_returns, 1.0 / 252.0) - 1.0
    daily_covariance = annual_covariance / 252.0
    generator = np.random.default_rng(seed)
    daily_returns = generator.multivariate_normal(
        daily_mean,
        daily_covariance,
        size=len(dates),
    )
    daily_returns = np.clip(daily_returns, -0.25, 0.25)
    prices = 100.0 * pd.DataFrame(
        1.0 + daily_returns,
        index=dates,
        columns=tickers,
    ).cumprod()
    prices.index.name = "Date"
    prices.columns.name = "Ticker"
    return prices


def build_demo_data(tickers: list[str]) -> DemoData:
    """Build deterministic demonstration prices, returns and audit metadata."""
    prices = build_demo_prices(tickers)
    returns = calculate_return_data(prices)
    metadata: dict[str, object] = {
        "mode": "demonstration",
        "synthetic": True,
        "seed": DEMO_SEED,
        "notice": DEMO_NOTICE,
        "start": prices.index.min().date().isoformat(),
        "end": prices.index.max().date().isoformat(),
        "price_observations": len(prices),
        "daily_return_observations": len(returns.daily),
        "monthly_return_observations": len(returns.monthly),
        "missing_prices": int(prices.isna().sum().sum()),
    }
    return DemoData(prices=prices, returns=returns, metadata=metadata)
