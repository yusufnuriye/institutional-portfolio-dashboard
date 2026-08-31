"""Baseline Harbourstone portfolios, returns and reconciliation checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from src.data_pipeline import DEFAULT_CACHE_DIR, DEFAULT_CONFIG_PATH, DataPipelineError
from src.metrics import (
    MetricSettings,
    annualised_geometric_return,
    annualised_sharpe_ratio,
    annualised_sortino_ratio,
    annualised_volatility,
    beta_to_benchmark,
    historical_expected_shortfall,
    historical_value_at_risk,
    maximum_drawdown,
)
from src.returns import ReturnData, build_return_outputs


@dataclass(frozen=True)
class PortfolioResults:
    """Weights, returns, metrics and return-contribution evidence."""

    weights: pd.DataFrame
    monthly_returns: pd.DataFrame
    daily_returns: pd.DataFrame
    metrics: pd.DataFrame
    monthly_return_contributions: pd.DataFrame
    annualised_arithmetic_return_contributions: pd.DataFrame


def equal_weight_portfolio(tickers: Sequence[str]) -> pd.Series:
    """Create a fully invested equal-weight portfolio."""
    if not tickers or len(set(tickers)) != len(tickers):
        raise DataPipelineError("Equal weights require a non-empty unique ticker list.")
    return pd.Series(1.0 / len(tickers), index=list(tickers), dtype=float)


def validate_weights(
    weights: pd.Series | Mapping[str, float],
    tickers: Sequence[str],
    *,
    fixed_income_tickers: Sequence[str],
    maximum_asset_weight: float = 0.40,
    minimum_fixed_income_weight: float = 0.30,
    tolerance: float = 1e-10,
) -> pd.Series:
    """Validate completeness, units and Harbourstone mandate constraints."""
    if not 0 < maximum_asset_weight <= 1:
        raise DataPipelineError("Maximum asset weight must be in (0, 1].")
    if not 0 <= minimum_fixed_income_weight <= 1:
        raise DataPipelineError("Minimum fixed-income weight must be in [0, 1].")

    expected = list(tickers)
    supplied = pd.Series(weights, dtype=float)
    missing = sorted(set(expected) - set(supplied.index))
    extra = sorted(set(supplied.index) - set(expected))
    if missing or extra:
        raise DataPipelineError(
            f"Portfolio tickers do not match the universe; missing={missing}, extra={extra}."
        )
    supplied = supplied.reindex(expected)
    if not np.isfinite(supplied.to_numpy()).all():
        raise DataPipelineError("Portfolio weights must be finite decimal values.")
    if (supplied < -tolerance).any():
        raise DataPipelineError("Portfolio weights must be long only.")
    supplied = supplied.clip(lower=0.0)
    if abs(float(supplied.sum()) - 1.0) > tolerance:
        raise DataPipelineError("Portfolio weights must sum to 1.0 in decimal units.")
    supplied = supplied / float(supplied.sum())
    if (supplied > maximum_asset_weight + tolerance).any():
        offenders = supplied[supplied > maximum_asset_weight + tolerance].index.tolist()
        raise DataPipelineError(f"Portfolio exceeds the maximum asset weight: {offenders}.")

    unknown_fixed_income = sorted(set(fixed_income_tickers) - set(expected))
    if unknown_fixed_income:
        raise DataPipelineError(
            f"Fixed-income tickers are outside the asset universe: {unknown_fixed_income}."
        )
    fixed_income_weight = float(supplied.loc[list(fixed_income_tickers)].sum())
    if fixed_income_weight + tolerance < minimum_fixed_income_weight:
        raise DataPipelineError("Portfolio is below the minimum fixed-income allocation.")
    supplied.name = "weight"
    return supplied


def load_portfolio_definitions(
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> tuple[dict[str, pd.Series], dict[str, object]]:
    """Load, construct and validate all three Sprint 1 portfolios."""
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    tickers = [asset["ticker"] for asset in config["assets"]]
    constraints = config["constraints"]
    definitions: dict[str, pd.Series | Mapping[str, float]] = {
        "equal_weight": equal_weight_portfolio(tickers),
        "sixty_forty": config["reference_portfolios"]["sixty_forty"],
        "user_defined": config["reference_portfolios"]["user_defined"],
    }
    validated = {
        name: validate_weights(
            weights,
            tickers,
            fixed_income_tickers=constraints["fixed_income_tickers"],
            maximum_asset_weight=constraints["maximum_asset_weight"],
            minimum_fixed_income_weight=constraints["minimum_fixed_income_weight"],
        )
        for name, weights in definitions.items()
    }
    context: dict[str, object] = {
        "tickers": tickers,
        "fixed_income_tickers": constraints["fixed_income_tickers"],
        "maximum_asset_weight": constraints["maximum_asset_weight"],
        "minimum_fixed_income_weight": constraints["minimum_fixed_income_weight"],
    }
    return validated, context


def _validate_asset_returns(asset_returns: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    if asset_returns.empty or len(asset_returns) < 2:
        raise DataPipelineError("At least two portfolio return observations are required.")
    if list(asset_returns.columns) != list(tickers):
        raise DataPipelineError("Return columns must match the validated ticker order.")
    if asset_returns.isna().any().any():
        raise DataPipelineError("Portfolio return inputs must contain complete common dates.")
    numeric = asset_returns.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise DataPipelineError("Portfolio return inputs must be finite numeric decimals.")
    if (numeric <= -1).any().any():
        raise DataPipelineError("A simple return cannot be less than or equal to -100%.")
    return numeric.astype(float)


def portfolio_returns(asset_returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Calculate target-weight returns for a rebalanced return period."""
    validated = _validate_asset_returns(asset_returns, weights.index)
    result = validated.mul(weights, axis="columns").sum(axis="columns")
    result.name = weights.name
    return result


def return_contributions(asset_returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Calculate additive simple-return contributions for every period."""
    validated = _validate_asset_returns(asset_returns, weights.index)
    contributions = validated.mul(weights, axis="columns")
    contributions.columns.name = "Ticker"
    return contributions


def monthly_rebalanced_daily_returns(
    daily_asset_returns: pd.DataFrame,
    weights: pd.Series,
) -> pd.Series:
    """Simulate a daily portfolio path with target weights reset each calendar month."""
    validated = _validate_asset_returns(daily_asset_returns, weights.index)
    if not isinstance(validated.index, pd.DatetimeIndex):
        raise DataPipelineError("Daily portfolio returns require a DatetimeIndex.")
    if not validated.index.is_monotonic_increasing or validated.index.has_duplicates:
        raise DataPipelineError("Daily return dates must be unique and increasing.")

    asset_values = weights.astype(float).copy()
    previous_month: tuple[int, int] | None = None
    portfolio_returns_list: list[float] = []
    for timestamp, asset_return in validated.iterrows():
        current_month = (timestamp.year, timestamp.month)
        if previous_month is not None and current_month != previous_month:
            asset_values = float(asset_values.sum()) * weights
        opening_value = float(asset_values.sum())
        period_return = float((asset_values * asset_return).sum() / opening_value)
        portfolio_returns_list.append(period_return)
        asset_values = asset_values * (1.0 + asset_return)
        previous_month = current_month

    return pd.Series(
        portfolio_returns_list,
        index=validated.index,
        name=weights.name,
        dtype=float,
    )


def validate_contribution_reconciliation(
    portfolio_return_series: pd.Series,
    contributions: pd.DataFrame,
    *,
    tolerance: float = 1e-12,
) -> None:
    """Stop if asset contributions do not add back to portfolio returns."""
    contribution_totals = contributions.sum(axis="columns")
    if not np.allclose(
        portfolio_return_series.to_numpy(dtype=float),
        contribution_totals.to_numpy(dtype=float),
        rtol=tolerance,
        atol=tolerance,
    ):
        raise DataPipelineError("Asset return contributions do not reconcile.")


def calculate_portfolio_metrics(
    monthly_portfolio_returns: pd.DataFrame,
    daily_portfolio_returns: pd.DataFrame,
    daily_asset_returns: pd.DataFrame,
    settings: MetricSettings = MetricSettings(),
) -> pd.DataFrame:
    """Calculate the same eight metrics for each baseline portfolio."""
    rows: dict[str, dict[str, float | int]] = {}
    benchmark = daily_asset_returns[settings.benchmark_ticker]
    for portfolio_name in monthly_portfolio_returns.columns:
        monthly = monthly_portfolio_returns[[portfolio_name]]
        daily = daily_portfolio_returns[[portfolio_name]]
        beta_frame = pd.concat([daily, benchmark], axis="columns", sort=False).dropna(how="any")
        rows[portfolio_name] = {
            "annualised_geometric_return": float(
                annualised_geometric_return(monthly, settings.periods_per_year).iloc[0]
            ),
            "annualised_volatility": float(
                annualised_volatility(daily, settings.daily_periods_per_year).iloc[0]
            ),
            "sharpe_ratio": float(
                annualised_sharpe_ratio(
                    daily,
                    periods_per_year=settings.daily_periods_per_year,
                    annual_risk_free_rate=settings.annual_risk_free_rate,
                ).iloc[0]
            ),
            "sortino_ratio": float(
                annualised_sortino_ratio(
                    daily,
                    periods_per_year=settings.daily_periods_per_year,
                    annual_minimum_acceptable_return=settings.annual_minimum_acceptable_return,
                ).iloc[0]
            ),
            "maximum_drawdown": float(maximum_drawdown(daily).iloc[0]),
            "beta_to_vwrl": float(
                beta_to_benchmark(beta_frame, settings.benchmark_ticker)[portfolio_name]
            ),
            "historical_var_95": float(
                historical_value_at_risk(daily, settings.confidence_level).iloc[0]
            ),
            "historical_expected_shortfall_95": float(
                historical_expected_shortfall(daily, settings.confidence_level).iloc[0]
            ),
            "monthly_observations": len(monthly),
            "daily_observations": len(daily),
        }
    metrics = pd.DataFrame.from_dict(rows, orient="index")
    metrics.index.name = "Portfolio"
    return metrics


def calculate_portfolio_results(
    return_data: ReturnData,
    config_path: Path = DEFAULT_CONFIG_PATH,
    settings: MetricSettings = MetricSettings(),
) -> PortfolioResults:
    """Build all three baseline portfolios and prove internal reconciliations."""
    definitions, context = load_portfolio_definitions(config_path)
    tickers = context["tickers"]
    monthly_assets = _validate_asset_returns(return_data.monthly, tickers)
    daily_assets = _validate_asset_returns(return_data.daily, tickers)

    weights_table = pd.DataFrame(definitions).T
    weights_table.index.name = "Portfolio"
    weights_table.columns.name = "Ticker"

    monthly_portfolios: dict[str, pd.Series] = {}
    daily_portfolios: dict[str, pd.Series] = {}
    contribution_frames: dict[str, pd.DataFrame] = {}
    annualised_contributions: dict[str, pd.Series] = {}
    for portfolio_name, weights in definitions.items():
        labelled_weights = weights.rename(portfolio_name)
        monthly = portfolio_returns(monthly_assets, labelled_weights)
        daily = monthly_rebalanced_daily_returns(daily_assets, labelled_weights)
        contributions = return_contributions(monthly_assets, labelled_weights)
        validate_contribution_reconciliation(monthly, contributions)

        monthly_portfolios[portfolio_name] = monthly
        daily_portfolios[portfolio_name] = daily
        contribution_frames[portfolio_name] = contributions
        annualised_contributions[portfolio_name] = contributions.mean() * settings.periods_per_year

    monthly_table = pd.DataFrame(monthly_portfolios)
    daily_table = pd.DataFrame(daily_portfolios)
    contribution_table = pd.concat(contribution_frames, axis="columns", sort=False)
    contribution_table.columns.names = ["Portfolio", "Ticker"]
    annualised_contribution_table = pd.DataFrame(annualised_contributions).T
    annualised_contribution_table.index.name = "Portfolio"
    annualised_contribution_table.columns.name = "Ticker"

    expected_annualised_arithmetic = monthly_table.mean() * settings.periods_per_year
    actual_contribution_totals = annualised_contribution_table.sum(axis="columns")
    if not np.allclose(
        expected_annualised_arithmetic.to_numpy(dtype=float),
        actual_contribution_totals.to_numpy(dtype=float),
        rtol=1e-12,
        atol=1e-12,
    ):
        raise DataPipelineError("Annualised return contributions do not reconcile.")

    metrics = calculate_portfolio_metrics(
        monthly_table,
        daily_table,
        daily_assets,
        settings,
    )
    return PortfolioResults(
        weights=weights_table,
        monthly_returns=monthly_table,
        daily_returns=daily_table,
        metrics=metrics,
        monthly_return_contributions=contribution_table,
        annualised_arithmetic_return_contributions=annualised_contribution_table,
    )


def save_portfolio_results(
    results: PortfolioResults,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> dict[str, Path]:
    """Save portfolio results and a compact reconciliation manifest."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "weights": cache_dir / "portfolio_weights.csv",
        "monthly_returns": cache_dir / "portfolio_monthly_returns.csv",
        "daily_returns": cache_dir / "portfolio_daily_returns.csv",
        "metrics": cache_dir / "portfolio_metrics.csv",
        "monthly_return_contributions": cache_dir / "portfolio_monthly_return_contributions.csv",
        "annualised_arithmetic_return_contributions": (
            cache_dir / "portfolio_annualised_return_contributions.csv"
        ),
        "manifest": cache_dir / "portfolio_reconciliation.json",
    }
    results.weights.to_csv(paths["weights"])
    results.monthly_returns.to_csv(paths["monthly_returns"])
    results.daily_returns.to_csv(paths["daily_returns"])
    results.metrics.to_csv(paths["metrics"])
    results.monthly_return_contributions.to_csv(paths["monthly_return_contributions"])
    results.annualised_arithmetic_return_contributions.to_csv(
        paths["annualised_arithmetic_return_contributions"]
    )

    manifest = {
        "weight_unit": "decimal; 1.0 equals 100%",
        "return_unit": "decimal; 0.01 equals 1%",
        "portfolio_names": results.weights.index.tolist(),
        "weight_sums": results.weights.sum(axis="columns").round(12).to_dict(),
        "monthly_contribution_reconciliation": "passed",
        "annualised_contribution_definition": (
            "weight times arithmetic mean monthly asset return times 12; "
            "contributions do not decompose geometric CAGR"
        ),
        "daily_rebalancing_policy": "target weights reset at each calendar-month boundary",
    }
    with paths["manifest"].open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
        manifest_file.write("\n")
    return paths


def build_portfolio_outputs(
    *,
    refresh: bool = False,
    end: str | None = None,
    settings: MetricSettings = MetricSettings(),
) -> tuple[PortfolioResults, dict[str, object]]:
    """Run the live return pipeline, build portfolios and save outputs."""
    return_data, quality_report = build_return_outputs(refresh=refresh, end=end)
    results = calculate_portfolio_results(return_data, settings=settings)
    save_portfolio_results(results)
    return results, quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Harbourstone Sprint 1 portfolios.")
    parser.add_argument("--refresh", action="store_true", help="Ignore a matching local cache.")
    parser.add_argument("--end", help="Exclusive end date in YYYY-MM-DD format.")
    args = parser.parse_args()

    results, quality_report = build_portfolio_outputs(refresh=args.refresh, end=args.end)
    print(results.weights.to_string(float_format=lambda value: f"{value:.2%}"))
    print(results.metrics.to_string(float_format=lambda value: f"{value:.4f}"))
    print(
        f"Common sample: {quality_report['common_start']} to "
        f"{quality_report['common_end']}."
    )


if __name__ == "__main__":
    main()
