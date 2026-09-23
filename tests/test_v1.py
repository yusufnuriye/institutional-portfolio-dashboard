"""Cross-module acceptance tests for the complete v1 analysis."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from src.risk import volatility_risk_contributions
from src.stress import DEFAULT_STRESS_SCENARIOS, apply_stress_scenarios
from src.v1 import build_v1_results, save_v1_evidence


@pytest.fixture(scope="module")
def v1_results():
    return build_v1_results(mode="demo")


def test_v1_contains_five_valid_portfolios(v1_results) -> None:
    weights = v1_results.portfolios.weights

    assert list(weights.index) == [
        "equal_weight",
        "sixty_forty",
        "user_defined",
        "minimum_variance",
        "maximum_sharpe",
    ]
    assert np.allclose(weights.sum(axis="columns"), 1.0)
    assert weights.ge(0.0).all().all()
    assert weights.le(0.40 + 1e-8).all().all()
    assert weights[["IGLT.L", "AGBP.L", "SLXX.L"]].sum(axis="columns").ge(
        0.30 - 1e-8
    ).all()


def test_every_portfolio_metric_is_finite_and_tail_loss_is_ordered(v1_results) -> None:
    metrics = v1_results.portfolios.metrics

    assert np.isfinite(metrics.to_numpy(dtype=float)).all()
    assert metrics["historical_expected_shortfall_95"].ge(
        metrics["historical_var_95"]
    ).all()
    assert metrics["maximum_drawdown"].le(0.0).all()


def test_return_contributions_add_to_arithmetic_portfolio_return(v1_results) -> None:
    contributions = v1_results.portfolios.annualised_arithmetic_return_contributions
    expected = v1_results.portfolios.monthly_returns.mean() * 12.0

    assert np.allclose(contributions.sum(axis="columns"), expected)


def test_risk_contributions_add_to_total_risk(v1_results) -> None:
    for portfolio in v1_results.portfolios.weights.index:
        weights = v1_results.portfolios.weights.loc[portfolio]
        table = volatility_risk_contributions(
            v1_results.asset_returns.monthly,
            weights,
        )
        assert table["percentage_of_total_risk"].sum() == pytest.approx(1.0)
        covariance = v1_results.asset_returns.monthly.cov() * 12.0
        expected_volatility = np.sqrt(weights.to_numpy() @ covariance.to_numpy() @ weights)
        assert table["component_volatility"].sum() == pytest.approx(expected_volatility)


def test_stress_results_are_exact_weighted_sums(v1_results) -> None:
    stresses = apply_stress_scenarios(v1_results.portfolios.weights)
    first_name = next(iter(DEFAULT_STRESS_SCENARIOS))
    first_shocks = np.array(list(DEFAULT_STRESS_SCENARIOS[first_name].values()))
    expected = v1_results.portfolios.weights.to_numpy() @ first_shocks

    assert np.allclose(stresses.loc[first_name].to_numpy(), expected)


def test_suitability_recommendation_is_explicitly_provisional(v1_results) -> None:
    assert v1_results.recommendation["portfolio"] == "user_defined"
    assert "provisional" in v1_results.recommendation["status"]
    assert v1_results.suitability[
        ["fully_invested", "long_only", "within_asset_cap", "meets_fixed_income_floor"]
    ].all().all()


def test_evidence_manifest_records_demo_and_live_data_limitation(v1_results) -> None:
    with TemporaryDirectory() as temporary_directory:
        paths = save_v1_evidence(v1_results, Path(temporary_directory))
        manifest = paths["manifest"].read_text(encoding="utf-8")

    assert '"mode": "demo"' in manifest
    assert "Yahoo Finance rate-limited" in manifest
    assert '"risk_contribution_reconciliation": "passed"' in manifest
