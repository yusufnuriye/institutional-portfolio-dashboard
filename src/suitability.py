"""Rule-based client-suitability checks for the fictional mandate."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def evaluate_suitability(
    weights: pd.DataFrame,
    metrics: pd.DataFrame,
    stresses: pd.DataFrame,
    *,
    fixed_income_tickers: Sequence[str],
    maximum_asset_weight: float,
    minimum_fixed_income_weight: float,
) -> pd.DataFrame:
    """Evaluate mandate compliance without pretending to prove client suitability."""
    rows: dict[str, dict[str, object]] = {}
    for portfolio in weights.index:
        portfolio_weights = weights.loc[portfolio]
        fixed_income_weight = float(portfolio_weights.loc[list(fixed_income_tickers)].sum())
        worst_stress = float(stresses[portfolio].min())
        drawdown = float(metrics.loc[portfolio, "maximum_drawdown"])
        rows[portfolio] = {
            "fully_invested": abs(float(portfolio_weights.sum()) - 1.0) <= 1e-8,
            "long_only": bool((portfolio_weights >= -1e-10).all()),
            "within_asset_cap": bool(
                (portfolio_weights <= maximum_asset_weight + 1e-8).all()
            ),
            "fixed_income_weight": fixed_income_weight,
            "meets_fixed_income_floor": fixed_income_weight + 1e-8
            >= minimum_fixed_income_weight,
            "number_of_allocations": int((portfolio_weights > 1e-8).sum()),
            "demonstration_maximum_drawdown": drawdown,
            "worst_hypothetical_stress": worst_stress,
        }
    result = pd.DataFrame.from_dict(rows, orient="index")
    result.index.name = "Portfolio"
    return result


def provisional_recommendation(suitability: pd.DataFrame) -> dict[str, str]:
    """Choose the diversified policy portfolio only if its mandate checks pass."""
    candidate = "user_defined"
    required = [
        "fully_invested",
        "long_only",
        "within_asset_cap",
        "meets_fixed_income_floor",
    ]
    if candidate not in suitability.index or not bool(suitability.loc[candidate, required].all()):
        return {
            "portfolio": "none",
            "status": "not suitable",
            "rationale": "The policy portfolio failed one or more mandate constraints.",
        }
    return {
        "portfolio": candidate,
        "status": "provisional for further due diligence",
        "rationale": (
            "It satisfies the coded mandate, retains all seven sleeves and balances "
            "growth, fixed income and real assets. The optimised portfolios are "
            "sensitivity tools, not automatic client recommendations."
        ),
    }
