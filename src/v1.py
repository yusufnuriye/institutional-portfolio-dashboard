"""End-to-end Harbourstone v1 analysis for demo or validated live data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_pipeline import DataPipelineError
from src.demo_data import DEMO_NOTICE, build_demo_data
from src.metrics import MetricSettings
from src.optimisation import (
    OptimisationResult,
    optimisation_sensitivity,
    optimise_portfolio,
)
from src.portfolios import (
    PortfolioResults,
    calculate_portfolio_metrics,
    load_portfolio_definitions,
    monthly_rebalanced_daily_returns,
    portfolio_returns,
    return_contributions,
    validate_contribution_reconciliation,
    validate_weights,
)
from src.returns import ReturnData, build_return_outputs
from src.risk import volatility_risk_contributions
from src.stress import DEFAULT_STRESS_SCENARIOS, apply_stress_scenarios
from src.suitability import evaluate_suitability, provisional_recommendation


@dataclass(frozen=True)
class V1Results:
    """All tables needed by the dashboard, documents and validation evidence."""

    mode: str
    data_metadata: dict[str, object]
    asset_returns: ReturnData
    portfolios: PortfolioResults
    optimisation_diagnostics: pd.DataFrame
    sensitivity: pd.DataFrame
    risk_contributions: pd.DataFrame
    stress_scenarios: pd.DataFrame
    stresses: pd.DataFrame
    suitability: pd.DataFrame
    recommendation: dict[str, str]


def _calculate_all_portfolios(
    return_data: ReturnData,
    definitions: dict[str, pd.Series],
    *,
    settings: MetricSettings,
) -> PortfolioResults:
    tickers = list(return_data.monthly.columns)
    weights_table = pd.DataFrame(definitions).T.reindex(columns=tickers)
    weights_table.index.name = "Portfolio"
    weights_table.columns.name = "Ticker"

    monthly_portfolios: dict[str, pd.Series] = {}
    daily_portfolios: dict[str, pd.Series] = {}
    contribution_frames: dict[str, pd.DataFrame] = {}
    annualised_contributions: dict[str, pd.Series] = {}
    for name, weights in definitions.items():
        labelled = weights.reindex(tickers).rename(name)
        monthly = portfolio_returns(return_data.monthly, labelled)
        daily = monthly_rebalanced_daily_returns(return_data.daily, labelled)
        contributions = return_contributions(return_data.monthly, labelled)
        validate_contribution_reconciliation(monthly, contributions)
        monthly_portfolios[name] = monthly
        daily_portfolios[name] = daily
        contribution_frames[name] = contributions
        annualised_contributions[name] = contributions.mean() * settings.periods_per_year

    monthly_table = pd.DataFrame(monthly_portfolios)
    daily_table = pd.DataFrame(daily_portfolios)
    contribution_table = pd.concat(contribution_frames, axis="columns", sort=False)
    contribution_table.columns.names = ["Portfolio", "Ticker"]
    annualised_contribution_table = pd.DataFrame(annualised_contributions).T
    annualised_contribution_table.index.name = "Portfolio"
    annualised_contribution_table.columns.name = "Ticker"

    if not np.allclose(
        monthly_table.mean().to_numpy() * settings.periods_per_year,
        annualised_contribution_table.sum(axis="columns").to_numpy(),
        atol=1e-12,
        rtol=1e-12,
    ):
        raise DataPipelineError("Annualised return contributions do not reconcile.")

    return PortfolioResults(
        weights=weights_table,
        monthly_returns=monthly_table,
        daily_returns=daily_table,
        metrics=calculate_portfolio_metrics(
            monthly_table,
            daily_table,
            return_data.daily,
            settings,
        ),
        monthly_return_contributions=contribution_table,
        annualised_arithmetic_return_contributions=annualised_contribution_table,
    )


def build_v1_results(
    *,
    mode: str = "demo",
    refresh: bool = False,
    settings: MetricSettings = MetricSettings(),
) -> V1Results:
    """Run the complete v1 workflow with explicit data provenance."""
    definitions, context = load_portfolio_definitions()
    tickers = list(context["tickers"])
    if mode == "demo":
        demo = build_demo_data(tickers)
        return_data = demo.returns
        metadata = demo.metadata
    elif mode == "live":
        return_data, quality_report = build_return_outputs(refresh=refresh)
        metadata = {
            **quality_report,
            "mode": "live",
            "synthetic": False,
            "notice": "Validated common adjusted-price history from Yahoo Finance via yfinance.",
        }
    else:
        raise DataPipelineError("Mode must be either 'demo' or 'live'.")

    optimisation_results: list[OptimisationResult] = []
    for name, objective in (
        ("minimum_variance", "minimum_variance"),
        ("maximum_sharpe", "maximum_sharpe"),
    ):
        optimisation_results.append(
            optimise_portfolio(
                return_data.monthly,
                name=name,
                objective=objective,
                fixed_income_tickers=context["fixed_income_tickers"],
                maximum_asset_weight=float(context["maximum_asset_weight"]),
                minimum_fixed_income_weight=float(context["minimum_fixed_income_weight"]),
                annual_risk_free_rate=settings.annual_risk_free_rate,
            )
        )
    for result in optimisation_results:
        definitions[result.name] = validate_weights(
            result.weights,
            tickers,
            fixed_income_tickers=context["fixed_income_tickers"],
            maximum_asset_weight=float(context["maximum_asset_weight"]),
            minimum_fixed_income_weight=float(context["minimum_fixed_income_weight"]),
            tolerance=1e-7,
        ).rename(result.name)

    portfolios = _calculate_all_portfolios(return_data, definitions, settings=settings)
    diagnostic_table = pd.DataFrame(
        [
            {
                "portfolio": result.name,
                "annualised_arithmetic_return": result.annualised_arithmetic_return,
                "annualised_volatility": result.annualised_volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "solver_message": result.solver_message,
            }
            for result in optimisation_results
        ]
    ).set_index("portfolio")
    sensitivity = optimisation_sensitivity(
        return_data.monthly,
        fixed_income_tickers=context["fixed_income_tickers"],
    )

    risk_frames: dict[str, pd.DataFrame] = {}
    for name in portfolios.weights.index:
        risk_frames[name] = volatility_risk_contributions(
            return_data.monthly,
            portfolios.weights.loc[name],
        )
    risk_contributions = pd.concat(risk_frames, names=["Portfolio", "Ticker"])

    scenario_table = pd.DataFrame(DEFAULT_STRESS_SCENARIOS).T.reindex(columns=tickers)
    scenario_table.index.name = "Scenario"
    scenario_table.columns.name = "Ticker"
    stresses = apply_stress_scenarios(portfolios.weights)
    suitability = evaluate_suitability(
        portfolios.weights,
        portfolios.metrics,
        stresses,
        fixed_income_tickers=context["fixed_income_tickers"],
        maximum_asset_weight=float(context["maximum_asset_weight"]),
        minimum_fixed_income_weight=float(context["minimum_fixed_income_weight"]),
    )
    recommendation = provisional_recommendation(suitability)
    return V1Results(
        mode=mode,
        data_metadata=metadata,
        asset_returns=return_data,
        portfolios=portfolios,
        optimisation_diagnostics=diagnostic_table,
        sensitivity=sensitivity,
        risk_contributions=risk_contributions,
        stress_scenarios=scenario_table,
        stresses=stresses,
        suitability=suitability,
        recommendation=recommendation,
    )


def save_v1_evidence(results: V1Results, output_dir: Path) -> dict[str, Path]:
    """Save deterministic tables used by the memo, deck and smoke-test evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "weights": output_dir / "portfolio_weights.csv",
        "metrics": output_dir / "portfolio_metrics.csv",
        "return_contributions": output_dir / "annualised_return_contributions.csv",
        "risk_contributions": output_dir / "risk_contributions.csv",
        "stress_results": output_dir / "stress_results.csv",
        "sensitivity": output_dir / "optimisation_sensitivity.csv",
        "suitability": output_dir / "suitability_checks.csv",
        "manifest": output_dir / "evidence_manifest.json",
    }
    results.portfolios.weights.to_csv(paths["weights"])
    results.portfolios.metrics.to_csv(paths["metrics"])
    results.portfolios.annualised_arithmetic_return_contributions.to_csv(
        paths["return_contributions"]
    )
    results.risk_contributions.to_csv(paths["risk_contributions"])
    results.stresses.to_csv(paths["stress_results"])
    results.sensitivity.to_csv(paths["sensitivity"], index=False)
    results.suitability.to_csv(paths["suitability"])
    manifest = {
        "mode": results.mode,
        "notice": results.data_metadata.get("notice", DEMO_NOTICE),
        "metadata": results.data_metadata,
        "portfolio_count": len(results.portfolios.weights),
        "weight_sums": results.portfolios.weights.sum(axis="columns").round(12).to_dict(),
        "return_contribution_reconciliation": "passed",
        "risk_contribution_reconciliation": "passed",
        "optimisation_solver_status": results.optimisation_diagnostics[
            "solver_message"
        ].to_dict(),
        "recommendation": results.recommendation,
        "known_live_data_limitation": (
            "Yahoo Finance rate-limited the 2026-09-23 validation attempt; "
            "demo results are synthetic and are never presented as historical performance."
        ),
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Harbourstone v1 analysis.")
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/demo"))
    args = parser.parse_args()
    results = build_v1_results(mode=args.mode, refresh=args.refresh)
    paths = save_v1_evidence(results, args.output_dir)
    print(results.portfolios.metrics.to_string(float_format=lambda value: f"{value:.4f}"))
    print(f"Saved {len(paths)} evidence files to {args.output_dir}.")


if __name__ == "__main__":
    main()
