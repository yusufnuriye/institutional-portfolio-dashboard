"""Return calculations derived from validated common adjusted prices."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_pipeline import DEFAULT_CACHE_DIR, DataPipelineError
from src.data_quality import build_validated_common_history


@dataclass(frozen=True)
class ReturnData:
    """Daily, monthly and cumulative return outputs."""

    daily: pd.DataFrame
    monthly: pd.DataFrame
    cumulative_growth: pd.DataFrame


def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate new price / old price - 1 for every series."""
    if prices.empty or len(prices) < 2:
        raise DataPipelineError("At least two complete price rows are required.")
    if prices.isna().any().any():
        raise DataPipelineError("Return inputs must already have complete common dates.")

    returns = prices.pct_change(fill_method=None).iloc[1:]
    if not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise DataPipelineError("Returns contain a non-finite value.")
    if (returns <= -1).any().any():
        raise DataPipelineError("A simple return cannot be less than or equal to -100%.")

    returns.index.name = "Date"
    return returns


def calculate_return_data(common_prices: pd.DataFrame) -> ReturnData:
    """Calculate daily, month-end and compounded growth series."""
    daily = calculate_simple_returns(common_prices)
    month_end_prices = common_prices.resample("ME").last().dropna(how="any")
    monthly = calculate_simple_returns(month_end_prices)
    cumulative_growth = (1.0 + daily).cumprod()
    cumulative_growth.index.name = "Date"
    return ReturnData(
        daily=daily,
        monthly=monthly,
        cumulative_growth=cumulative_growth,
    )


def validate_return_reconstruction(
    common_prices: pd.DataFrame,
    return_data: ReturnData,
    *,
    tolerance: float = 1e-10,
) -> None:
    """Confirm compounded daily returns reconstruct end-to-start price growth."""
    expected_growth = common_prices.iloc[-1] / common_prices.iloc[0]
    reconstructed_growth = return_data.cumulative_growth.iloc[-1]
    if not np.allclose(
        expected_growth.to_numpy(dtype=float),
        reconstructed_growth.to_numpy(dtype=float),
        rtol=tolerance,
        atol=tolerance,
    ):
        raise DataPipelineError("Compounded returns do not reconstruct price growth.")


def save_return_data(
    return_data: ReturnData,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> dict[str, Path]:
    """Save calculation outputs used by later risk and portfolio modules."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily_returns": cache_dir / "daily_returns.csv",
        "monthly_returns": cache_dir / "monthly_returns.csv",
        "cumulative_growth": cache_dir / "cumulative_growth.csv",
    }
    return_data.daily.to_csv(paths["daily_returns"])
    return_data.monthly.to_csv(paths["monthly_returns"])
    return_data.cumulative_growth.to_csv(paths["cumulative_growth"])
    return paths


def build_return_outputs(*, refresh: bool = False, end: str | None = None) -> tuple[ReturnData, dict[str, object]]:
    """Run the complete Day 2 pipeline and save validated return outputs."""
    common_prices, quality_report = build_validated_common_history(
        refresh=refresh,
        end=end,
    )
    return_data = calculate_return_data(common_prices)
    validate_return_reconstruction(common_prices, return_data)
    save_return_data(return_data)
    return return_data, quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Harbourstone Day 2 return outputs.")
    parser.add_argument("--refresh", action="store_true", help="Ignore a matching local cache.")
    parser.add_argument("--end", help="Exclusive end date in YYYY-MM-DD format.")
    args = parser.parse_args()

    return_data, quality_report = build_return_outputs(refresh=args.refresh, end=args.end)
    print(
        f"Daily returns: {len(return_data.daily)} rows; "
        f"monthly returns: {len(return_data.monthly)} rows; "
        f"common sample: {quality_report['common_start']} to "
        f"{quality_report['common_end']}."
    )


if __name__ == "__main__":
    main()
