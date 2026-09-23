"""Tests for constrained optimisation and solver-failure handling."""

from types import SimpleNamespace

import numpy as np
import pytest

from src.data_pipeline import DataPipelineError
from src.demo_data import build_demo_data
from src.optimisation import optimisation_sensitivity, optimise_portfolio


TICKERS = [
    "VWRL.L",
    "CUKX.L",
    "IGLT.L",
    "AGBP.L",
    "SLXX.L",
    "SGLN.L",
    "AGCP.L",
]
FIXED_INCOME = ["IGLT.L", "AGBP.L", "SLXX.L"]


@pytest.mark.parametrize("objective", ["minimum_variance", "maximum_sharpe"])
def test_optimised_weights_satisfy_every_constraint(objective: str) -> None:
    returns = build_demo_data(TICKERS).returns.monthly
    result = optimise_portfolio(
        returns,
        name=objective,
        objective=objective,
        fixed_income_tickers=FIXED_INCOME,
    )

    assert result.weights.sum() == pytest.approx(1.0)
    assert result.weights.min() >= 0.0
    assert result.weights.max() <= 0.40 + 1e-8
    assert result.weights.loc[FIXED_INCOME].sum() >= 0.30 - 1e-8
    assert result.annualised_volatility > 0.0
    assert np.isfinite(result.sharpe_ratio)


def test_solver_failure_is_reported_instead_of_returning_weights() -> None:
    returns = build_demo_data(TICKERS).returns.monthly

    def failed_solver(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(success=False, message="deliberate failure")

    with pytest.raises(DataPipelineError, match="deliberate failure"):
        optimise_portfolio(
            returns,
            name="minimum_variance",
            objective="minimum_variance",
            fixed_income_tickers=FIXED_INCOME,
            solver=failed_solver,
        )


def test_sensitivity_grid_records_all_eighteen_runs() -> None:
    returns = build_demo_data(TICKERS).returns.monthly
    sensitivity = optimisation_sensitivity(
        returns,
        fixed_income_tickers=FIXED_INCOME,
    )

    assert len(sensitivity) == 18
    assert set(sensitivity["objective"]) == {"minimum_variance", "maximum_sharpe"}
    assert sensitivity["status"].eq("success").all()
