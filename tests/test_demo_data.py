"""Tests for the explicit deterministic demonstration dataset."""

import pandas as pd

from src.demo_data import DEMO_NOTICE, build_demo_data, build_demo_prices
from src.returns import validate_return_reconstruction


TICKERS = [
    "VWRL.L",
    "CUKX.L",
    "IGLT.L",
    "AGBP.L",
    "SLXX.L",
    "SGLN.L",
    "AGCP.L",
]


def test_demo_prices_are_deterministic_complete_and_positive() -> None:
    first = build_demo_prices(TICKERS)
    second = build_demo_prices(TICKERS)

    pd.testing.assert_frame_equal(first, second)
    assert len(first) >= 1260
    assert not first.isna().any().any()
    assert first.gt(0).all().all()


def test_demo_metadata_is_explicitly_synthetic() -> None:
    demo = build_demo_data(TICKERS)

    assert demo.metadata["synthetic"] is True
    assert demo.metadata["mode"] == "demonstration"
    assert demo.metadata["notice"] == DEMO_NOTICE
    assert demo.metadata["missing_prices"] == 0


def test_demo_returns_reconstruct_generated_prices() -> None:
    demo = build_demo_data(TICKERS)

    validate_return_reconstruction(demo.prices, demo.returns)
