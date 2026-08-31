"""Tests for Harbourstone performance and risk metrics."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest

from src.data_pipeline import DataPipelineError
from src.metrics import (
    MetricSettings,
    annualised_downside_deviation,
    annualised_geometric_return,
    annualised_sharpe_ratio,
    annualised_sortino_ratio,
    annualised_volatility,
    beta_to_benchmark,
    calculate_asset_metrics,
    historical_expected_shortfall,
    historical_value_at_risk,
    maximum_drawdown,
    save_asset_metrics,
)


def monthly_returns() -> pd.DataFrame:
    values = [0.02, -0.01, 0.03, -0.02] * 3
    return pd.DataFrame(
        {"VWRL.L": values, "ASSET_B": [value / 2 for value in values]},
        index=pd.date_range("2025-01-31", periods=12, freq="ME"),
    )


def daily_returns() -> pd.DataFrame:
    benchmark = np.array([-0.04, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.04])
    return pd.DataFrame(
        {"VWRL.L": benchmark, "ASSET_B": 0.005 + 0.5 * benchmark},
        index=pd.date_range("2025-01-02", periods=len(benchmark), freq="B"),
    )


def test_geometric_return_compounds_monthly_growth() -> None:
    returns = pd.DataFrame(
        {"ASSET": [0.01] * 12},
        index=pd.date_range("2025-01-31", periods=12, freq="ME"),
    )
    result = annualised_geometric_return(returns, periods_per_year=12)

    assert result["ASSET"] == pytest.approx((1.01**12) - 1.0)


def test_volatility_uses_sample_standard_deviation_and_square_root_of_time() -> None:
    returns = monthly_returns()
    result = annualised_volatility(returns, periods_per_year=12)
    expected = returns.std(ddof=1) * np.sqrt(12)

    pd.testing.assert_series_equal(result, expected)


def test_sharpe_is_annualised_arithmetic_excess_return_over_volatility() -> None:
    returns = monthly_returns()
    result = annualised_sharpe_ratio(
        returns,
        periods_per_year=12,
        annual_risk_free_rate=0.0,
    )
    expected = returns.mean() / returns.std(ddof=1) * np.sqrt(12)

    assert np.allclose(result, expected)


def test_sortino_penalises_only_returns_below_the_target() -> None:
    returns = monthly_returns()
    downside = annualised_downside_deviation(
        returns,
        periods_per_year=12,
        annual_minimum_acceptable_return=0.0,
    )
    result = annualised_sortino_ratio(
        returns,
        periods_per_year=12,
        annual_minimum_acceptable_return=0.0,
    )

    shortfalls = returns.clip(upper=0.0)
    expected_downside = np.sqrt(shortfalls.pow(2).mean()) * np.sqrt(12)
    expected_ratio = returns.mean() * 12 / expected_downside
    assert np.allclose(downside, expected_downside)
    assert np.allclose(result, expected_ratio)


def test_maximum_drawdown_includes_starting_wealth() -> None:
    returns = pd.DataFrame({"ASSET": [-0.10, 0.05, -0.20]})

    result = maximum_drawdown(returns)

    assert result["ASSET"] == pytest.approx((0.90 * 1.05 * 0.80) - 1.0)


def test_beta_uses_covariance_over_benchmark_variance() -> None:
    benchmark = pd.Series([-0.03, -0.01, 0.00, 0.02, 0.04])
    returns = pd.DataFrame(
        {"VWRL.L": benchmark, "DOUBLE_BETA": 0.01 + 2.0 * benchmark}
    )

    result = beta_to_benchmark(returns, "VWRL.L")

    assert result["VWRL.L"] == pytest.approx(1.0)
    assert result["DOUBLE_BETA"] == pytest.approx(2.0)


def test_historical_var_and_expected_shortfall_use_positive_loss_magnitudes() -> None:
    returns = pd.DataFrame({"ASSET": [-0.10, -0.05, 0.00, 0.05, 0.10]})

    value_at_risk = historical_value_at_risk(returns, confidence_level=0.80)
    expected_shortfall = historical_expected_shortfall(returns, confidence_level=0.80)

    assert value_at_risk["ASSET"] == pytest.approx(0.06)
    assert expected_shortfall["ASSET"] == pytest.approx(0.10)
    assert expected_shortfall["ASSET"] >= value_at_risk["ASSET"]


def test_metric_table_contains_eight_metrics_and_observation_counts() -> None:
    metrics = calculate_asset_metrics(monthly_returns(), daily_returns())

    assert metrics.index.tolist() == ["VWRL.L", "ASSET_B"]
    assert metrics.columns.tolist() == [
        "annualised_geometric_return",
        "annualised_volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "maximum_drawdown",
        "beta_to_vwrl",
        "historical_var_95",
        "historical_expected_shortfall_95",
        "monthly_observations",
        "daily_observations",
    ]
    assert metrics["monthly_observations"].eq(12).all()
    assert metrics["daily_observations"].eq(8).all()
    assert metrics.loc["VWRL.L", "beta_to_vwrl"] == pytest.approx(1.0)
    assert metrics.loc["VWRL.L", "annualised_volatility"] == pytest.approx(
        daily_returns()["VWRL.L"].std(ddof=1) * np.sqrt(252)
    )


def test_percentage_inputs_are_rejected_by_settings() -> None:
    with pytest.raises(DataPipelineError, match="decimal returns"):
        calculate_asset_metrics(
            monthly_returns(),
            daily_returns(),
            MetricSettings(input_return_unit="percentage"),
        )


def test_invalid_confidence_level_is_rejected() -> None:
    with pytest.raises(DataPipelineError, match="between zero and one"):
        calculate_asset_metrics(
            monthly_returns(),
            daily_returns(),
            MetricSettings(confidence_level=1.0),
        )


def test_missing_benchmark_is_rejected() -> None:
    with pytest.raises(DataPipelineError, match="Benchmark"):
        beta_to_benchmark(daily_returns().drop(columns="VWRL.L"), "VWRL.L")


def test_daily_and_monthly_assets_must_match() -> None:
    with pytest.raises(DataPipelineError, match="same assets"):
        calculate_asset_metrics(
            monthly_returns(),
            daily_returns().rename(columns={"ASSET_B": "OTHER"}),
        )


def test_metric_outputs_save_values_and_auditable_metadata() -> None:
    settings = MetricSettings()
    metrics = calculate_asset_metrics(monthly_returns(), daily_returns(), settings)

    with TemporaryDirectory() as temporary_directory:
        metrics_path, metadata_path = save_asset_metrics(
            metrics,
            settings,
            Path(temporary_directory),
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metrics_path.name == "asset_metrics.csv"
    assert metadata["settings"]["periods_per_year"] == 12
    assert metadata["settings"]["daily_periods_per_year"] == 252
    assert metadata["units"]["sharpe_ratio"] == "dimensionless"
    assert "positive daily loss magnitude" in metadata["units"]["historical_var_95"]
