"""Portfolio risk-contribution calculations and reconciliation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_pipeline import DataPipelineError


def volatility_risk_contributions(
    monthly_asset_returns: pd.DataFrame,
    weights: pd.Series,
) -> pd.DataFrame:
    """Decompose annualised volatility into marginal and component contributions."""
    if list(monthly_asset_returns.columns) != list(weights.index):
        raise DataPipelineError("Risk-contribution inputs must share the same ticker order.")
    if monthly_asset_returns.isna().any().any():
        raise DataPipelineError("Risk contributions require complete common returns.")
    annual_covariance = monthly_asset_returns.cov() * 12.0
    covariance_times_weight = annual_covariance.to_numpy() @ weights.to_numpy()
    variance = float(weights.to_numpy() @ covariance_times_weight)
    volatility = float(np.sqrt(max(variance, 0.0)))
    if volatility <= np.finfo(float).eps:
        raise DataPipelineError("Portfolio volatility must be positive for risk contributions.")

    marginal = covariance_times_weight / volatility
    component = weights.to_numpy() * marginal
    percentage = component / volatility
    if not np.isclose(component.sum(), volatility, atol=1e-10, rtol=1e-10):
        raise DataPipelineError("Component risk contributions do not reconcile to volatility.")
    if not np.isclose(percentage.sum(), 1.0, atol=1e-10, rtol=1e-10):
        raise DataPipelineError("Percentage risk contributions do not sum to 100%.")

    table = pd.DataFrame(
        {
            "weight": weights,
            "marginal_volatility": marginal,
            "component_volatility": component,
            "percentage_of_total_risk": percentage,
        },
        index=weights.index,
    )
    table.index.name = "Ticker"
    return table
