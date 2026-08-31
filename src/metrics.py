"""Validated performance and risk metrics for Harbourstone asset returns."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_pipeline import DEFAULT_CACHE_DIR, DataPipelineError
from src.returns import build_return_outputs


@dataclass(frozen=True)
class MetricSettings:
    """Explicit frequency, hurdle-rate and tail-risk assumptions."""

    periods_per_year: int = 12
    daily_periods_per_year: int = 252
    annual_risk_free_rate: float = 0.0
    annual_minimum_acceptable_return: float = 0.0
    confidence_level: float = 0.95
    benchmark_ticker: str = "VWRL.L"
    input_return_unit: str = "decimal"


def _validate_settings(settings: MetricSettings) -> None:
    if settings.periods_per_year <= 0 or settings.daily_periods_per_year <= 0:
        raise DataPipelineError("Annualisation periods must be positive.")
    if settings.annual_risk_free_rate <= -1:
        raise DataPipelineError("The annual risk-free rate must exceed -100%.")
    if settings.annual_minimum_acceptable_return <= -1:
        raise DataPipelineError("The annual minimum acceptable return must exceed -100%.")
    if not 0 < settings.confidence_level < 1:
        raise DataPipelineError("The confidence level must be between zero and one.")
    if not settings.benchmark_ticker:
        raise DataPipelineError("A benchmark ticker is required for beta.")
    if settings.input_return_unit != "decimal":
        raise DataPipelineError("Metric inputs must use decimal returns, not percentages.")


def _validate_returns(returns: pd.DataFrame) -> pd.DataFrame:
    if returns.empty or len(returns) < 2:
        raise DataPipelineError("At least two complete return observations are required.")
    if returns.columns.has_duplicates:
        raise DataPipelineError("Return columns must be unique.")
    if returns.isna().any().any():
        raise DataPipelineError("Metric inputs must contain complete return observations.")

    numeric = returns.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise DataPipelineError("Metric inputs must be finite numeric decimal returns.")
    if (numeric <= -1).any().any():
        raise DataPipelineError("A simple return cannot be less than or equal to -100%.")
    return numeric.astype(float)


def annual_to_periodic_rate(annual_rate: float, periods_per_year: int) -> float:
    """Convert an effective annual rate into an equivalent periodic rate."""
    if annual_rate <= -1 or periods_per_year <= 0:
        raise DataPipelineError("Rate conversion requires a rate above -100% and positive periods.")
    return float((1.0 + annual_rate) ** (1.0 / periods_per_year) - 1.0)


def annualised_geometric_return(
    returns: pd.DataFrame,
    periods_per_year: int = 12,
) -> pd.Series:
    """Calculate compounded annual growth from periodic simple returns."""
    validated = _validate_returns(returns)
    if periods_per_year <= 0:
        raise DataPipelineError("Periods per year must be positive.")

    total_growth = (1.0 + validated).prod()
    return total_growth ** (periods_per_year / len(validated)) - 1.0


def annualised_volatility(
    returns: pd.DataFrame,
    periods_per_year: int = 12,
) -> pd.Series:
    """Annualise sample standard deviation using the square-root-of-time rule."""
    validated = _validate_returns(returns)
    if periods_per_year <= 0:
        raise DataPipelineError("Periods per year must be positive.")
    return validated.std(ddof=1) * np.sqrt(periods_per_year)


def annualised_sharpe_ratio(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 12,
    annual_risk_free_rate: float = 0.0,
) -> pd.Series:
    """Annualise mean periodic excess return divided by sample volatility."""
    validated = _validate_returns(returns)
    periodic_risk_free = annual_to_periodic_rate(
        annual_risk_free_rate,
        periods_per_year,
    )
    excess = validated - periodic_risk_free
    periodic_volatility = excess.std(ddof=1)
    ratio = excess.mean() / periodic_volatility * np.sqrt(periods_per_year)
    return ratio.where(periodic_volatility > np.finfo(float).eps)


def annualised_downside_deviation(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 12,
    annual_minimum_acceptable_return: float = 0.0,
) -> pd.Series:
    """Annualise root-mean-square shortfalls below the periodic target."""
    validated = _validate_returns(returns)
    periodic_target = annual_to_periodic_rate(
        annual_minimum_acceptable_return,
        periods_per_year,
    )
    shortfalls = (validated - periodic_target).clip(upper=0.0)
    return np.sqrt(shortfalls.pow(2).mean()) * np.sqrt(periods_per_year)


def annualised_sortino_ratio(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 12,
    annual_minimum_acceptable_return: float = 0.0,
) -> pd.Series:
    """Compare annualised mean return above target with downside deviation."""
    validated = _validate_returns(returns)
    periodic_target = annual_to_periodic_rate(
        annual_minimum_acceptable_return,
        periods_per_year,
    )
    annualised_mean_excess = (validated.mean() - periodic_target) * periods_per_year
    downside = annualised_downside_deviation(
        validated,
        periods_per_year=periods_per_year,
        annual_minimum_acceptable_return=annual_minimum_acceptable_return,
    )
    ratio = annualised_mean_excess / downside
    return ratio.where(downside > np.finfo(float).eps)


def maximum_drawdown(returns: pd.DataFrame) -> pd.Series:
    """Calculate the worst peak-to-trough loss, including initial wealth of one."""
    validated = _validate_returns(returns)
    wealth = (1.0 + validated).cumprod()
    running_peak = wealth.cummax().clip(lower=1.0)
    return (wealth / running_peak - 1.0).min()


def beta_to_benchmark(
    returns: pd.DataFrame,
    benchmark_ticker: str,
) -> pd.Series:
    """Calculate covariance with the benchmark divided by benchmark variance."""
    validated = _validate_returns(returns)
    if benchmark_ticker not in validated.columns:
        raise DataPipelineError(f"Benchmark {benchmark_ticker} is missing from returns.")
    benchmark = validated[benchmark_ticker]
    benchmark_variance = benchmark.var(ddof=1)
    if benchmark_variance <= np.finfo(float).eps:
        raise DataPipelineError("Benchmark variance must be positive for beta.")
    return validated.apply(lambda series: series.cov(benchmark) / benchmark_variance)


def historical_value_at_risk(
    returns: pd.DataFrame,
    confidence_level: float = 0.95,
) -> pd.Series:
    """Return historical VaR as a positive loss magnitude in decimal units."""
    validated = _validate_returns(returns)
    if not 0 < confidence_level < 1:
        raise DataPipelineError("The confidence level must be between zero and one.")
    lower_tail_quantile = validated.quantile(1.0 - confidence_level, interpolation="linear")
    return (-lower_tail_quantile).clip(lower=0.0)


def historical_expected_shortfall(
    returns: pd.DataFrame,
    confidence_level: float = 0.95,
) -> pd.Series:
    """Return the mean loss at or beyond historical VaR as a positive magnitude."""
    validated = _validate_returns(returns)
    if not 0 < confidence_level < 1:
        raise DataPipelineError("The confidence level must be between zero and one.")

    quantiles = validated.quantile(1.0 - confidence_level, interpolation="linear")
    results: dict[str, float] = {}
    for column in validated.columns:
        tail = validated.loc[validated[column] <= quantiles[column], column]
        if tail.empty:
            raise DataPipelineError(f"No tail observations are available for {column}.")
        results[column] = max(0.0, float(-tail.mean()))
    return pd.Series(results, dtype=float)


def calculate_asset_metrics(
    monthly_returns: pd.DataFrame,
    daily_returns: pd.DataFrame | None = None,
    settings: MetricSettings = MetricSettings(),
) -> pd.DataFrame:
    """Create a labelled eight-metric table for every asset."""
    _validate_settings(settings)
    monthly = _validate_returns(monthly_returns)
    daily = _validate_returns(daily_returns if daily_returns is not None else monthly_returns)
    if set(monthly.columns) != set(daily.columns):
        raise DataPipelineError("Daily and monthly returns must contain the same assets.")
    daily = daily.loc[:, monthly.columns]

    metrics = pd.DataFrame(
        {
            "annualised_geometric_return": annualised_geometric_return(
                monthly,
                settings.periods_per_year,
            ),
            "annualised_volatility": annualised_volatility(
                daily,
                settings.daily_periods_per_year,
            ),
            "sharpe_ratio": annualised_sharpe_ratio(
                daily,
                periods_per_year=settings.daily_periods_per_year,
                annual_risk_free_rate=settings.annual_risk_free_rate,
            ),
            "sortino_ratio": annualised_sortino_ratio(
                daily,
                periods_per_year=settings.daily_periods_per_year,
                annual_minimum_acceptable_return=settings.annual_minimum_acceptable_return,
            ),
            "maximum_drawdown": maximum_drawdown(daily),
            "beta_to_vwrl": beta_to_benchmark(daily, settings.benchmark_ticker),
            "historical_var_95": historical_value_at_risk(
                daily,
                settings.confidence_level,
            ),
            "historical_expected_shortfall_95": historical_expected_shortfall(
                daily,
                settings.confidence_level,
            ),
        }
    )
    metrics.index.name = "Ticker"
    metrics["monthly_observations"] = len(monthly)
    metrics["daily_observations"] = len(daily)
    return metrics


def save_asset_metrics(
    metrics: pd.DataFrame,
    settings: MetricSettings,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Path, Path]:
    """Save metric values and their unit, frequency and sign metadata."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = cache_dir / "asset_metrics.csv"
    metadata_path = cache_dir / "asset_metrics.metadata.json"
    metrics.to_csv(metrics_path)

    metadata = {
        "settings": asdict(settings),
        "input_frequencies": {
            "monthly": [
                "annualised_geometric_return",
            ],
            "daily": [
                "annualised_volatility",
                "sharpe_ratio",
                "sortino_ratio",
                "maximum_drawdown",
                "beta_to_vwrl",
                "historical_var_95",
                "historical_expected_shortfall_95",
            ],
        },
        "units": {
            "annualised_geometric_return": "decimal annual rate",
            "annualised_volatility": "decimal annual rate",
            "sharpe_ratio": "dimensionless",
            "sortino_ratio": "dimensionless",
            "maximum_drawdown": "negative decimal return",
            "beta_to_vwrl": "dimensionless",
            "historical_var_95": "positive daily loss magnitude in decimal units",
            "historical_expected_shortfall_95": "positive daily loss magnitude in decimal units",
        },
        "definitions": {
            "annualised_geometric_return": "compounded monthly growth annualised geometrically",
            "annualised_volatility": "daily sample standard deviation times square root of 252",
            "sharpe_ratio": "annualised arithmetic mean daily excess return divided by annualised volatility",
            "sortino_ratio": "annualised arithmetic mean daily return above target divided by annualised downside deviation",
            "maximum_drawdown": "worst daily peak-to-trough loss from a wealth index starting at one",
            "beta_to_vwrl": "daily covariance with VWRL divided by daily VWRL variance",
            "historical_var_95": "negative fifth percentile of daily returns, floored at zero",
            "historical_expected_shortfall_95": "mean loss on daily returns at or below the fifth percentile",
        },
    }
    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)
        metadata_file.write("\n")
    return metrics_path, metadata_path


def build_metric_outputs(
    *,
    refresh: bool = False,
    end: str | None = None,
    settings: MetricSettings = MetricSettings(),
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Run the validated data pipeline and save all eight asset metrics."""
    return_data, quality_report = build_return_outputs(refresh=refresh, end=end)
    metrics = calculate_asset_metrics(return_data.monthly, return_data.daily, settings)
    save_asset_metrics(metrics, settings)
    return metrics, quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Harbourstone Sprint 1 asset metrics.")
    parser.add_argument("--refresh", action="store_true", help="Ignore a matching local cache.")
    parser.add_argument("--end", help="Exclusive end date in YYYY-MM-DD format.")
    args = parser.parse_args()

    metrics, quality_report = build_metric_outputs(refresh=args.refresh, end=args.end)
    print(metrics.to_string(float_format=lambda value: f"{value:.4f}"))
    print(
        f"Common sample: {quality_report['common_start']} to "
        f"{quality_report['common_end']}."
    )


if __name__ == "__main__":
    main()
