"""Streamlit entry point for the institutional portfolio dashboard."""

from pathlib import Path

import streamlit as st
import yaml


ROOT = Path(__file__).resolve().parent
ASSET_CONFIG = ROOT / "config" / "assets.yml"


@st.cache_data
def load_asset_config() -> dict:
    """Load the reviewed Day 1 asset-universe configuration."""
    with ASSET_CONFIG.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


st.set_page_config(
    page_title="Institutional Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
)

config = load_asset_config()

st.title("Institutional Multi-Asset Portfolio Strategy and Risk Dashboard")
st.caption("Day 2 implementation complete — live data validation pending")
st.warning(
    "The ingestion, validation and return engine is complete, but no live "
    "data-quality report is bundled. The universe remains provisional and no "
    "portfolio recommendation exists yet."
)

st.subheader("Fictional mandate")
st.markdown(
    """
    **Harbourstone Foundation** is a fictional UK institutional investor with a
    **£100 million** balanced-growth portfolio, a horizon of at least five years,
    and an aspirational objective of **UK CPI +3% annualised** over rolling
    five-year periods. The risk profile is moderate and the historical drawdown
    reference is approximately 15–20%, not a guaranteed limit.
    """
)

st.subheader("Provisional asset universe")
display_columns = (
    "ticker",
    "instrument_type",
    "asset_class",
    "role",
    "listing_currency",
    "hedging_policy",
    "lse_listing_date",
)
st.dataframe(
    [
        {column: asset.get(column, "") for column in display_columns}
        for asset in config["assets"]
    ],
    width="stretch",
    hide_index=True,
)

st.subheader("Day 2 data engine")
st.markdown(
    """
    - Adjusted daily-close ingestion with request-aware local caching
    - Complete-date alignment across all seven assets without forward-filling
    - Data-quality checks for missing series, non-positive prices, insufficient
      common history and suspicious one-day moves
    - Daily and month-end simple returns plus a cumulative-growth reconstruction check
    """
)
st.code("python -m src.returns --refresh", language="bash")

st.info(
    "This project is an educational simulation, not investment advice or a "
    "guarantee of future performance."
)
