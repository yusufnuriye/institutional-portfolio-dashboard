"""Tests for daily, monthly and cumulative return calculations."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data_pipeline import DataPipelineError
from src.returns import (
    calculate_return_data,
    calculate_simple_returns,
    save_return_data,
    validate_return_reconstruction,
)


def sample_prices() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2026-01-29", "2026-01-30", "2026-02-02", "2026-02-27", "2026-03-02"]
    )
    return pd.DataFrame(
        {
            "ASSET_A": [100.0, 105.0, 103.0, 110.0, 121.0],
            "ASSET_B": [200.0, 202.0, 204.0, 208.0, 212.0],
        },
        index=dates,
    )


def test_simple_return_from_100_to_105_is_five_percent() -> None:
    prices = pd.DataFrame({"ASSET": [100.0, 105.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    returns = calculate_simple_returns(prices)

    assert abs(returns.iloc[0, 0] - 0.05) < 1e-12


def test_daily_returns_have_one_fewer_row_than_prices() -> None:
    prices = sample_prices()
    return_data = calculate_return_data(prices)

    assert len(return_data.daily) == len(prices) - 1


def test_monthly_returns_use_month_end_prices() -> None:
    return_data = calculate_return_data(sample_prices())

    expected_february_return = 110.0 / 105.0 - 1.0
    assert abs(return_data.monthly.loc["2026-02-28", "ASSET_A"] - expected_february_return) < 1e-12


def test_compounded_returns_reconstruct_price_growth() -> None:
    prices = sample_prices()
    return_data = calculate_return_data(prices)

    validate_return_reconstruction(prices, return_data)
    assert abs(return_data.cumulative_growth.iloc[-1]["ASSET_A"] - 1.21) < 1e-12


def test_missing_price_is_rejected_before_returns() -> None:
    prices = sample_prices()
    prices.iloc[2, 0] = float("nan")

    try:
        calculate_simple_returns(prices)
    except DataPipelineError as error:
        assert "complete common dates" in str(error)
    else:
        raise AssertionError("Incomplete prices should fail before return calculation.")


def test_return_outputs_are_saved_separately() -> None:
    return_data = calculate_return_data(sample_prices())

    with TemporaryDirectory() as temporary_directory:
        paths = save_return_data(return_data, Path(temporary_directory))
        filenames = {name: path.name for name, path in paths.items()}

    assert filenames == {
        "daily_returns": "daily_returns.csv",
        "monthly_returns": "monthly_returns.csv",
        "cumulative_growth": "cumulative_growth.csv",
    }
