"""Transparent hypothetical stress scenarios for Harbourstone portfolios."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from src.data_pipeline import DataPipelineError


DEFAULT_STRESS_SCENARIOS: dict[str, dict[str, float]] = {
    "growth_shock": {
        "VWRL.L": -0.25,
        "CUKX.L": -0.22,
        "IGLT.L": 0.04,
        "AGBP.L": 0.03,
        "SLXX.L": -0.05,
        "SGLN.L": 0.08,
        "AGCP.L": -0.12,
    },
    "inflation_shock": {
        "VWRL.L": -0.12,
        "CUKX.L": -0.10,
        "IGLT.L": -0.10,
        "AGBP.L": -0.08,
        "SLXX.L": -0.09,
        "SGLN.L": 0.06,
        "AGCP.L": 0.15,
    },
    "rates_and_credit_shock": {
        "VWRL.L": -0.10,
        "CUKX.L": -0.08,
        "IGLT.L": -0.12,
        "AGBP.L": -0.10,
        "SLXX.L": -0.15,
        "SGLN.L": 0.02,
        "AGCP.L": -0.05,
    },
}


def apply_stress_scenarios(
    weights: pd.DataFrame,
    scenarios: Mapping[str, Mapping[str, float]] = DEFAULT_STRESS_SCENARIOS,
) -> pd.DataFrame:
    """Apply one-period asset shocks as a transparent weighted sum."""
    if weights.empty or weights.isna().any().any():
        raise DataPipelineError("Stress testing requires complete portfolio weights.")
    if not np.allclose(weights.sum(axis="columns"), 1.0, atol=1e-10, rtol=1e-10):
        raise DataPipelineError("Stress-test portfolio weights must sum to one.")
    results: dict[str, pd.Series] = {}
    for scenario_name, mapping in scenarios.items():
        missing = sorted(set(weights.columns) - set(mapping))
        extra = sorted(set(mapping) - set(weights.columns))
        if missing or extra:
            raise DataPipelineError(
                f"Stress scenario {scenario_name} has missing={missing}, extra={extra}."
            )
        shocks = pd.Series(mapping, dtype=float).reindex(weights.columns)
        if not np.isfinite(shocks.to_numpy()).all():
            raise DataPipelineError(f"Stress scenario {scenario_name} contains invalid shocks.")
        results[scenario_name] = weights.mul(shocks, axis="columns").sum(axis="columns")
    table = pd.DataFrame(results).T
    table.index.name = "Scenario"
    table.columns.name = "Portfolio"
    return table
