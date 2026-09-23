"""Streamlit decision dashboard for the Harbourstone v1 analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from src.data_pipeline import DataPipelineError
from src.v1 import V1Results, build_v1_results


ROOT = Path(__file__).resolve().parent
ASSET_CONFIG = ROOT / "config" / "assets.yml"
PORTFOLIO_LABELS = {
    "equal_weight": "Equal weight",
    "sixty_forty": "60/40 reference",
    "user_defined": "Diversified policy",
    "minimum_variance": "Minimum variance",
    "maximum_sharpe": "Maximum Sharpe",
}
METRIC_LABELS = {
    "annualised_geometric_return": "Annualised return",
    "annualised_volatility": "Annualised volatility",
    "sharpe_ratio": "Sharpe ratio",
    "sortino_ratio": "Sortino ratio",
    "maximum_drawdown": "Maximum drawdown",
    "beta_to_vwrl": "Beta to VWRL",
    "historical_var_95": "95% daily VaR",
    "historical_expected_shortfall_95": "95% daily expected shortfall",
}
PERCENT_METRICS = {
    "annualised_geometric_return",
    "annualised_volatility",
    "maximum_drawdown",
    "historical_var_95",
    "historical_expected_shortfall_95",
}


@st.cache_data
def load_asset_config() -> dict:
    """Load the reviewed asset-universe configuration."""
    with ASSET_CONFIG.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


@st.cache_data(show_spinner=False)
def run_analysis(mode: str, refresh: bool = False) -> V1Results:
    """Run a provenance-aware v1 analysis."""
    return build_v1_results(mode=mode, refresh=refresh)


def _format_metric_table(metrics: pd.DataFrame) -> pd.DataFrame:
    display = metrics[list(METRIC_LABELS)].copy()
    display.index = [PORTFOLIO_LABELS.get(value, value) for value in display.index]
    display = display.rename(columns=METRIC_LABELS)
    for source, label in METRIC_LABELS.items():
        if source in PERCENT_METRICS:
            display[label] = display[label].map(lambda value: f"{value:.2%}")
        else:
            display[label] = display[label].map(lambda value: f"{value:.2f}")
    return display


def _percentage_table(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.index = [PORTFOLIO_LABELS.get(value, value) for value in result.index]
    result.columns = [str(value).replace("_", " ").title() for value in result.columns]
    return result.map(lambda value: f"{value:.1%}")


st.set_page_config(
    page_title="Harbourstone Portfolio Dashboard",
    page_icon="⚓",
    layout="wide",
)

config = load_asset_config()
st.sidebar.title("Analysis controls")
selected_mode = st.sidebar.radio(
    "Data source",
    ("Reproducible demonstration", "Live Yahoo Finance"),
    help="Live mode is accepted only after the full common-history validation passes.",
)
mode = "demo" if selected_mode.startswith("Reproducible") else "live"
refresh = st.sidebar.button("Refresh live data", disabled=mode != "live")

st.title("Harbourstone Foundation")
st.subheader("Institutional multi-asset portfolio strategy and risk dashboard")
st.caption("Credible v1 · mandate, analytics, optimisation, stress and suitability")

try:
    results = run_analysis(mode, refresh)
except DataPipelineError as error:
    st.error(f"Live analysis stopped safely: {error}")
    st.info(
        "No partial or stale live results are displayed. Select Reproducible "
        "demonstration in the sidebar to inspect the complete application offline."
    )
    st.stop()

if results.mode == "demo":
    st.warning(
        "DEMONSTRATION MODE — every performance and risk result below uses deterministic "
        "synthetic data. Results are not historical evidence, a forecast or investment advice."
    )
else:
    st.success("LIVE MODE — validated adjusted prices on complete common dates.")

overview, portfolios_tab, risk_tab, decision_tab, methodology_tab = st.tabs(
    ["Overview", "Portfolios", "Risk & stress", "Decision", "Methodology"]
)

with overview:
    st.markdown(
        """
        **Mandate.** A fictional £100 million UK charitable foundation seeking UK CPI +3%
        annualised over rolling five-year periods, with 3% annual spending, moderate risk,
        a 40% maximum per asset, at least 30% fixed income, long-only investing and no leverage.
        """
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Portfolios compared", len(results.portfolios.weights))
    metric_columns[1].metric("Investments", len(results.portfolios.weights.columns))
    metric_columns[2].metric("Daily observations", f"{len(results.asset_returns.daily):,}")
    metric_columns[3].metric(
        "Recommendation status", results.recommendation["status"].capitalize()
    )

    scatter = results.portfolios.metrics.reset_index()
    scatter["Portfolio label"] = scatter["Portfolio"].map(PORTFOLIO_LABELS)
    figure = px.scatter(
        scatter,
        x="annualised_volatility",
        y="annualised_geometric_return",
        color="Portfolio label",
        size=[18] * len(scatter),
        labels={
            "annualised_volatility": "Annualised volatility",
            "annualised_geometric_return": "Annualised return",
        },
        title="Growth and risk comparison",
    )
    figure.update_xaxes(tickformat=".0%")
    figure.update_yaxes(tickformat=".0%")
    figure.update_layout(showlegend=True, legend_title_text="Portfolio")
    st.plotly_chart(figure, width="stretch")
    st.dataframe(_format_metric_table(results.portfolios.metrics), width="stretch")

with portfolios_tab:
    st.subheader("Allocation")
    weight_long = (
        results.portfolios.weights.rename(index=PORTFOLIO_LABELS)
        .reset_index()
        .melt(id_vars="Portfolio", var_name="Ticker", value_name="Weight")
    )
    weight_figure = px.bar(
        weight_long,
        x="Portfolio",
        y="Weight",
        color="Ticker",
        title="Portfolio weights",
    )
    weight_figure.update_yaxes(tickformat=".0%")
    st.plotly_chart(weight_figure, width="stretch")
    st.dataframe(_percentage_table(results.portfolios.weights), width="stretch")

    st.subheader("Cumulative £100 growth")
    wealth = (1.0 + results.portfolios.daily_returns).cumprod() * 100.0
    wealth = wealth.rename(columns=PORTFOLIO_LABELS)
    wealth_figure = px.line(
        wealth,
        labels={"value": "Demonstration wealth (£)", "Date": "Date", "variable": "Portfolio"},
    )
    wealth_figure.update_layout(legend_title_text="Portfolio")
    st.plotly_chart(wealth_figure, width="stretch")

    st.subheader("Annualised arithmetic return contributions")
    st.caption(
        "Weights × mean monthly asset return × 12. Contributions add to arithmetic "
        "portfolio return; they do not decompose geometric CAGR."
    )
    st.dataframe(
        _percentage_table(results.portfolios.annualised_arithmetic_return_contributions),
        width="stretch",
    )

with risk_tab:
    chosen_portfolio = st.selectbox(
        "Portfolio for risk decomposition",
        options=list(results.portfolios.weights.index),
        index=list(results.portfolios.weights.index).index("user_defined"),
        format_func=lambda value: PORTFOLIO_LABELS.get(value, value),
    )
    risk_table = results.risk_contributions.loc[chosen_portfolio].copy()
    risk_figure = px.bar(
        risk_table.reset_index(),
        x="Ticker",
        y="percentage_of_total_risk",
        title=f"Volatility-risk contributions — {PORTFOLIO_LABELS[chosen_portfolio]}",
    )
    risk_figure.update_yaxes(tickformat=".0%")
    st.plotly_chart(risk_figure, width="stretch")
    risk_display = risk_table.copy()
    for column in risk_display.columns:
        risk_display[column] = risk_display[column].map(lambda value: f"{value:.2%}")
    st.dataframe(risk_display, width="stretch")

    st.subheader("Hypothetical stress scenarios")
    st.caption("One-period asset shocks are assumptions, not forecasts or historical replicas.")
    stress_long = (
        results.stresses.rename(columns=PORTFOLIO_LABELS)
        .reset_index()
        .melt(id_vars="Scenario", var_name="Portfolio", value_name="Return")
    )
    stress_figure = px.bar(
        stress_long,
        x="Scenario",
        y="Return",
        color="Portfolio",
        barmode="group",
    )
    stress_figure.update_yaxes(tickformat=".0%")
    st.plotly_chart(stress_figure, width="stretch")
    st.dataframe(
        results.stresses.rename(columns=PORTFOLIO_LABELS).map(lambda value: f"{value:.1%}"),
        width="stretch",
    )
    with st.expander("See asset shock assumptions"):
        st.dataframe(results.stress_scenarios.map(lambda value: f"{value:.1%}"), width="stretch")

with decision_tab:
    st.subheader("Provisional client conclusion")
    recommendation_label = PORTFOLIO_LABELS.get(
        results.recommendation["portfolio"], results.recommendation["portfolio"]
    )
    st.info(
        f"**{recommendation_label} — {results.recommendation['status']}.** "
        f"{results.recommendation['rationale']}"
    )
    st.markdown(
        "The optimiser outputs are sensitivity tools. They are not selected automatically: "
        "estimated means and covariances are sample-dependent, and the CPI+3% objective cannot "
        "be tested until CPI data and validated live market history are available."
    )

    suitability_display = results.suitability.copy()
    suitability_display.index = [
        PORTFOLIO_LABELS.get(value, value) for value in suitability_display.index
    ]
    for column in (
        "fixed_income_weight",
        "demonstration_maximum_drawdown",
        "worst_hypothetical_stress",
    ):
        suitability_display[column] = suitability_display[column].map(
            lambda value: f"{value:.1%}"
        )
    st.dataframe(suitability_display, width="stretch")

    st.subheader("Optimisation sensitivity")
    sensitivity_display = results.sensitivity.copy()
    for column in (
        "maximum_asset_weight",
        "minimum_fixed_income_weight",
        "annualised_arithmetic_return",
        "annualised_volatility",
    ):
        sensitivity_display[column] = sensitivity_display[column].map(
            lambda value: "—" if pd.isna(value) else f"{value:.1%}"
        )
    sensitivity_display["sharpe_ratio"] = sensitivity_display["sharpe_ratio"].map(
        lambda value: "—" if pd.isna(value) else f"{value:.2f}"
    )
    st.dataframe(sensitivity_display, width="stretch", hide_index=True)

with methodology_tab:
    st.subheader("Data and calculation controls")
    st.json(results.data_metadata)
    st.markdown(
        """
        - Adjusted prices; complete common dates only; no forward-filling.
        - Monthly returns for strategic CAGR and optimisation; daily returns for risk statistics.
        - Monthly rebalancing for portfolio paths and additive return contributions.
        - Volatility uses sample standard deviation and square-root-of-time annualisation.
        - VaR and Expected Shortfall use the historical lower 5% tail and are positive loss magnitudes.
        - Optimisation uses SLSQP with long-only 0–40% bounds, weights summing to 100%, and at least 30% fixed income.
        """
    )
    asset_columns = (
        "ticker",
        "instrument_type",
        "asset_class",
        "role",
        "hedging_policy",
        "income_treatment",
    )
    st.dataframe(
        [
            {column: asset.get(column, "") for column in asset_columns}
            for asset in config["assets"]
        ],
        width="stretch",
        hide_index=True,
    )
    st.error(
        "Known limitation: Yahoo Finance rate-limited the live validation attempt on "
        "23 September 2026. Demo-mode values are synthetic; fees, taxes, transaction "
        "costs, liabilities and CPI history are not modelled."
    )

st.caption(
    "Educational portfolio-research project for a fictional foundation. "
    "No output is a recommendation to buy or sell an investment."
)
