"""Constrained portfolio optimisation and sensitivity analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.data_pipeline import DataPipelineError
from src.portfolios import validate_weights


@dataclass(frozen=True)
class OptimisationResult:
    """Validated weights and transparent solver diagnostics."""

    name: str
    weights: pd.Series
    annualised_arithmetic_return: float
    annualised_volatility: float
    sharpe_ratio: float
    solver_message: str


def _moments(monthly_returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    if monthly_returns.empty or len(monthly_returns) < 2:
        raise DataPipelineError("Optimisation requires at least two monthly observations.")
    numeric = monthly_returns.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise DataPipelineError("Optimisation inputs must be complete finite returns.")
    return numeric.mean() * 12.0, numeric.cov() * 12.0


def _portfolio_statistics(
    weights: np.ndarray,
    expected_returns: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
) -> tuple[float, float, float]:
    annual_return = float(weights @ expected_returns.to_numpy())
    variance = float(weights @ covariance.to_numpy() @ weights)
    annual_volatility = float(np.sqrt(max(variance, 0.0)))
    if annual_volatility <= np.finfo(float).eps:
        raise DataPipelineError("Optimised portfolio volatility must be positive.")
    return annual_return, annual_volatility, (annual_return - risk_free_rate) / annual_volatility


def optimise_portfolio(
    monthly_returns: pd.DataFrame,
    *,
    name: str,
    objective: str,
    fixed_income_tickers: Sequence[str],
    maximum_asset_weight: float = 0.40,
    minimum_fixed_income_weight: float = 0.30,
    annual_risk_free_rate: float = 0.0,
    solver: Callable[..., object] = minimize,
) -> OptimisationResult:
    """Solve and validate a long-only minimum-variance or maximum-Sharpe portfolio."""
    if objective not in {"minimum_variance", "maximum_sharpe"}:
        raise DataPipelineError(f"Unknown optimisation objective: {objective}.")
    tickers = list(monthly_returns.columns)
    expected_returns, covariance = _moments(monthly_returns)
    fixed_positions = [tickers.index(ticker) for ticker in fixed_income_tickers]
    initial = np.full(len(tickers), 1.0 / len(tickers), dtype=float)

    def variance(weights: np.ndarray) -> float:
        return float(weights @ covariance.to_numpy() @ weights)

    def negative_sharpe(weights: np.ndarray) -> float:
        annual_return = float(weights @ expected_returns.to_numpy())
        annual_volatility = np.sqrt(max(variance(weights), np.finfo(float).eps))
        return -float((annual_return - annual_risk_free_rate) / annual_volatility)

    result = solver(
        variance if objective == "minimum_variance" else negative_sharpe,
        initial,
        method="SLSQP",
        bounds=[(0.0, maximum_asset_weight)] * len(tickers),
        constraints=[
            {"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)},
            {
                "type": "ineq",
                "fun": lambda weights: float(
                    np.sum(np.asarray(weights)[fixed_positions]) - minimum_fixed_income_weight
                ),
            },
        ],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not bool(getattr(result, "success", False)):
        message = str(getattr(result, "message", "unknown solver failure"))
        raise DataPipelineError(f"{name} optimisation failed: {message}")

    raw_weights = pd.Series(np.asarray(result.x, dtype=float), index=tickers, name=name)
    raw_weights[np.abs(raw_weights) < 1e-10] = 0.0
    raw_weights = raw_weights / raw_weights.sum()
    weights = validate_weights(
        raw_weights,
        tickers,
        fixed_income_tickers=fixed_income_tickers,
        maximum_asset_weight=maximum_asset_weight,
        minimum_fixed_income_weight=minimum_fixed_income_weight,
        tolerance=1e-7,
    ).rename(name)
    annual_return, annual_volatility, sharpe = _portfolio_statistics(
        weights.to_numpy(),
        expected_returns,
        covariance,
        annual_risk_free_rate,
    )
    return OptimisationResult(
        name=name,
        weights=weights,
        annualised_arithmetic_return=annual_return,
        annualised_volatility=annual_volatility,
        sharpe_ratio=sharpe,
        solver_message=str(result.message),
    )


def optimisation_sensitivity(
    monthly_returns: pd.DataFrame,
    *,
    fixed_income_tickers: Sequence[str],
    maximum_weights: Sequence[float] = (0.30, 0.35, 0.40),
    minimum_fixed_income_weights: Sequence[float] = (0.30, 0.40, 0.50),
) -> pd.DataFrame:
    """Re-run both objectives across a compact constraint grid."""
    rows: list[dict[str, object]] = []
    for maximum_weight in maximum_weights:
        for minimum_fixed_income in minimum_fixed_income_weights:
            for objective in ("minimum_variance", "maximum_sharpe"):
                try:
                    result = optimise_portfolio(
                        monthly_returns,
                        name=objective,
                        objective=objective,
                        fixed_income_tickers=fixed_income_tickers,
                        maximum_asset_weight=maximum_weight,
                        minimum_fixed_income_weight=minimum_fixed_income,
                    )
                    rows.append(
                        {
                            "objective": objective,
                            "maximum_asset_weight": maximum_weight,
                            "minimum_fixed_income_weight": minimum_fixed_income,
                            "status": "success",
                            "annualised_arithmetic_return": result.annualised_arithmetic_return,
                            "annualised_volatility": result.annualised_volatility,
                            "sharpe_ratio": result.sharpe_ratio,
                            "message": result.solver_message,
                        }
                    )
                except DataPipelineError as error:
                    rows.append(
                        {
                            "objective": objective,
                            "maximum_asset_weight": maximum_weight,
                            "minimum_fixed_income_weight": minimum_fixed_income,
                            "status": "failed",
                            "annualised_arithmetic_return": np.nan,
                            "annualised_volatility": np.nan,
                            "sharpe_ratio": np.nan,
                            "message": str(error),
                        }
                    )
    return pd.DataFrame(rows)
