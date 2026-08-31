"""Tests for baseline portfolio construction and reconciliation."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest

from src.data_pipeline import DataPipelineError
from src.portfolios import (
    calculate_portfolio_results,
    equal_weight_portfolio,
    load_portfolio_definitions,
    monthly_rebalanced_daily_returns,
    portfolio_returns,
    return_contributions,
    save_portfolio_results,
    validate_contribution_reconciliation,
    validate_weights,
)
from src.returns import ReturnData


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


def synthetic_return_data() -> ReturnData:
    daily_index = pd.date_range("2024-01-02", periods=520, freq="B")
    t_daily = np.arange(len(daily_index), dtype=float)
    daily_values: dict[str, np.ndarray] = {}
    benchmark = 0.0002 + 0.008 * np.sin(t_daily / 7.0)
    for position, ticker in enumerate(TICKERS):
        if ticker == "VWRL.L":
            daily_values[ticker] = benchmark
        else:
            daily_values[ticker] = (
                0.0001
                + (0.15 + position * 0.08) * benchmark
                + 0.002 * np.cos(t_daily / (5.0 + position))
            )
    daily = pd.DataFrame(daily_values, index=daily_index)

    monthly_index = pd.date_range("2024-01-31", periods=24, freq="ME")
    t_monthly = np.arange(len(monthly_index), dtype=float)
    monthly = pd.DataFrame(
        {
            ticker: 0.004
            + position * 0.0004
            + (0.015 - position * 0.001) * np.sin(t_monthly / (2.0 + position / 4.0))
            for position, ticker in enumerate(TICKERS)
        },
        index=monthly_index,
    )
    return ReturnData(
        daily=daily,
        monthly=monthly,
        cumulative_growth=(1.0 + daily).cumprod(),
    )


def test_equal_weight_portfolio_sums_to_one() -> None:
    weights = equal_weight_portfolio(TICKERS)

    assert weights.sum() == pytest.approx(1.0)
    assert weights.eq(1.0 / 7.0).all()


def test_all_three_configured_portfolios_pass_mandate_checks() -> None:
    definitions, context = load_portfolio_definitions()

    assert list(definitions) == ["equal_weight", "sixty_forty", "user_defined"]
    for weights in definitions.values():
        assert weights.sum() == pytest.approx(1.0)
        assert weights.max() <= context["maximum_asset_weight"]
        assert weights.loc[FIXED_INCOME].sum() >= context["minimum_fixed_income_weight"]


def test_sixty_forty_is_60_percent_equity_and_40_percent_fixed_income() -> None:
    definitions, _ = load_portfolio_definitions()
    weights = definitions["sixty_forty"]

    assert weights.loc[["VWRL.L", "CUKX.L"]].sum() == pytest.approx(0.60)
    assert weights.loc[FIXED_INCOME].sum() == pytest.approx(0.40)
    assert weights.max() == pytest.approx(0.40)


def test_user_defined_portfolio_has_45_fixed_income_and_10_real_assets() -> None:
    definitions, _ = load_portfolio_definitions()
    weights = definitions["user_defined"]

    assert weights.loc[FIXED_INCOME].sum() == pytest.approx(0.45)
    assert weights.loc[["SGLN.L", "AGCP.L"]].sum() == pytest.approx(0.10)


@pytest.mark.parametrize(
    ("weights", "message"),
    [
        ({"A": 0.6, "B": 0.3}, "sum to 1.0"),
        ({"A": 1.1, "B": -0.1}, "long only"),
        ({"A": 0.7, "B": 0.3}, "maximum asset weight"),
    ],
)
def test_invalid_weights_are_rejected(weights: dict[str, float], message: str) -> None:
    with pytest.raises(DataPipelineError, match=message):
        validate_weights(
            weights,
            ["A", "B"],
            fixed_income_tickers=["B"],
            maximum_asset_weight=0.60,
            minimum_fixed_income_weight=0.30,
        )


def test_weight_below_fixed_income_minimum_is_rejected() -> None:
    with pytest.raises(DataPipelineError, match="minimum fixed-income"):
        validate_weights(
            {"A": 0.70, "B": 0.30},
            ["A", "B"],
            fixed_income_tickers=["B"],
            maximum_asset_weight=1.0,
            minimum_fixed_income_weight=0.40,
        )


def test_return_contributions_sum_to_portfolio_return() -> None:
    asset_returns = pd.DataFrame(
        {"A": [0.10, -0.05], "B": [0.00, 0.05]},
        index=pd.date_range("2025-01-31", periods=2, freq="ME"),
    )
    weights = pd.Series({"A": 0.60, "B": 0.40}, name="portfolio")

    portfolio = portfolio_returns(asset_returns, weights)
    contributions = return_contributions(asset_returns, weights)
    validate_contribution_reconciliation(portfolio, contributions)

    pd.testing.assert_series_equal(
        contributions.sum(axis="columns"),
        portfolio,
        check_names=False,
    )


def test_daily_path_rebalances_at_calendar_month_boundary() -> None:
    daily = pd.DataFrame(
        {"A": [0.10, 0.10, 0.10], "B": [0.00, 0.00, 0.00]},
        index=pd.to_datetime(["2025-01-30", "2025-01-31", "2025-02-03"]),
    )
    weights = pd.Series({"A": 0.50, "B": 0.50}, name="portfolio")

    result = monthly_rebalanced_daily_returns(daily, weights)

    assert result.iloc[0] == pytest.approx(0.05)
    assert result.iloc[1] == pytest.approx(0.55 / 1.05 * 0.10)
    assert result.iloc[2] == pytest.approx(0.05)


def test_complete_portfolio_results_reconcile_weights_and_contributions() -> None:
    results = calculate_portfolio_results(synthetic_return_data())

    assert np.allclose(results.weights.sum(axis="columns"), 1.0)
    assert results.metrics.shape == (3, 10)
    assert results.metrics["historical_expected_shortfall_95"].ge(
        results.metrics["historical_var_95"]
    ).all()

    annualised_return = results.monthly_returns.mean() * 12
    contribution_total = results.annualised_arithmetic_return_contributions.sum(axis="columns")
    assert np.allclose(annualised_return, contribution_total)

    for portfolio_name in results.monthly_returns.columns:
        contribution_slice = results.monthly_return_contributions[portfolio_name]
        assert np.allclose(
            results.monthly_returns[portfolio_name],
            contribution_slice.sum(axis="columns"),
        )


def test_portfolio_outputs_save_reconciliation_manifest() -> None:
    results = calculate_portfolio_results(synthetic_return_data())

    with TemporaryDirectory() as temporary_directory:
        paths = save_portfolio_results(results, Path(temporary_directory))
        manifest = paths["manifest"].read_text(encoding="utf-8")

    assert all(path.name for path in paths.values())
    assert '"monthly_contribution_reconciliation": "passed"' in manifest
    assert "do not decompose geometric CAGR" in manifest
