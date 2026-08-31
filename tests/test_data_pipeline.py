"""Tests for adjusted-price ingestion and caching."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data_pipeline import (
    DataPipelineError,
    download_adjusted_closes,
    load_or_download_adjusted_closes,
    load_tickers,
)


TICKERS = ["VWRL.L", "CUKX.L", "IGLT.L", "AGBP.L", "SLXX.L", "SGLN.L", "AGCP.L"]


def synthetic_download() -> pd.DataFrame:
    """Create a small yfinance-shaped frame with one visible missing value."""
    dates = pd.to_datetime(["2017-11-23", "2017-11-24", "2017-11-27"])
    columns = pd.MultiIndex.from_product([["Close"], TICKERS])
    values = [
        [100.0, 200.0, 10.0, 5.0, 120.0, 20.0, 15.0],
        [101.0, 201.0, 10.1, 5.1, 120.5, 20.2, float("nan")],
        [102.0, 202.0, 10.2, 5.2, 121.0, 20.4, 15.2],
    ]
    return pd.DataFrame(values, index=dates, columns=columns)


def fake_downloader(**_: object) -> pd.DataFrame:
    return synthetic_download()


def test_load_tickers_preserves_reviewed_order() -> None:
    assert load_tickers() == TICKERS


def test_download_extracts_adjusted_closes_and_preserves_gaps() -> None:
    prices = download_adjusted_closes(
        TICKERS,
        "2017-11-23",
        "2017-11-28",
        downloader=fake_downloader,
    )

    assert prices.columns.tolist() == TICKERS
    assert pd.isna(prices.loc["2017-11-24", "AGCP.L"])


def test_download_disables_parallel_requests_to_reduce_rate_limit_pressure() -> None:
    captured: dict[str, object] = {}

    def recording_downloader(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return synthetic_download()

    download_adjusted_closes(
        TICKERS,
        "2017-11-23",
        "2017-11-28",
        downloader=recording_downloader,
    )

    assert captured["threads"] is False
    assert captured["auto_adjust"] is True


def test_matching_cache_avoids_a_second_download() -> None:
    calls = 0

    def counting_downloader(**_: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return synthetic_download()

    with TemporaryDirectory() as temporary_directory:
        cache_dir = Path(temporary_directory)
        kwargs = {
            "cache_dir": cache_dir,
            "start": "2017-11-23",
            "end": "2017-11-28",
            "downloader": counting_downloader,
            "downloaded_at": datetime(2026, 8, 18, tzinfo=timezone.utc),
        }
        first = load_or_download_adjusted_closes(**kwargs)
        second = load_or_download_adjusted_closes(**kwargs)

    pd.testing.assert_frame_equal(first, second, check_freq=False)
    assert calls == 1


def test_missing_ticker_is_rejected() -> None:
    incomplete = synthetic_download().drop(columns=("Close", "AGCP.L"))

    def incomplete_downloader(**_: object) -> pd.DataFrame:
        return incomplete

    try:
        download_adjusted_closes(
            TICKERS,
            "2017-11-23",
            "2017-11-28",
            downloader=incomplete_downloader,
        )
    except DataPipelineError as error:
        assert "AGCP.L" in str(error)
    else:
        raise AssertionError("A missing ticker should fail validation.")
