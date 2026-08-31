"""Adjusted-price ingestion and local caching for the asset universe."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config" / "assets.yml"
DEFAULT_CACHE_DIR = ROOT / "data" / "cache"


class DataPipelineError(ValueError):
    """Raised when downloaded or cached market data is not usable."""


def load_tickers(config_path: Path = DEFAULT_CONFIG_PATH) -> list[str]:
    """Return the configured tickers in their reviewed display order."""
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    tickers = [asset["ticker"] for asset in config["assets"]]
    if not tickers or len(tickers) != len(set(tickers)):
        raise DataPipelineError("The configured ticker list is empty or contains duplicates.")
    return tickers


def _validate_request_dates(start: str, end: str) -> None:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if start_date >= end_date:
        raise DataPipelineError("The start date must be earlier than the exclusive end date.")


def validate_price_frame(prices: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """Validate basic adjusted-close structure without inventing missing prices."""
    if prices.empty:
        raise DataPipelineError("The price download is empty.")

    missing_tickers = [ticker for ticker in tickers if ticker not in prices.columns]
    if missing_tickers:
        raise DataPipelineError(f"Missing adjusted-close series: {missing_tickers}")

    validated = prices.loc[:, list(tickers)].copy()
    validated.index = pd.to_datetime(validated.index, errors="raise").tz_localize(None)
    validated = validated[~validated.index.duplicated(keep="last")].sort_index()
    validated = validated.apply(pd.to_numeric, errors="coerce")

    insufficient = [ticker for ticker in tickers if validated[ticker].count() < 2]
    if insufficient:
        raise DataPipelineError(f"Fewer than two numeric prices for: {insufficient}")

    non_positive = (validated <= 0).where(validated.notna()).any()
    if non_positive.any():
        affected = non_positive[non_positive].index.tolist()
        raise DataPipelineError(f"Non-positive prices found for: {affected}")

    return validated


def extract_adjusted_closes(downloaded: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """Extract adjusted closing prices from a yfinance-style download."""
    if downloaded.empty:
        raise DataPipelineError("The price download is empty.")

    if isinstance(downloaded.columns, pd.MultiIndex):
        if "Close" in downloaded.columns.get_level_values(0):
            closes = downloaded["Close"]
        elif "Close" in downloaded.columns.get_level_values(1):
            closes = downloaded.xs("Close", axis=1, level=1)
        else:
            raise DataPipelineError("The download does not contain a Close field.")
    elif len(tickers) == 1 and "Close" in downloaded.columns:
        closes = downloaded[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        raise DataPipelineError("Unexpected market-data column structure.")

    return validate_price_frame(closes, tickers)


def download_adjusted_closes(
    tickers: Sequence[str],
    start: str,
    end: str,
    *,
    downloader: Callable[..., pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Download daily closes adjusted for distributions and corporate actions.

    The end date follows yfinance convention and is exclusive.
    """
    _validate_request_dates(start, end)

    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    downloaded = downloader(
        tickers=list(tickers),
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        actions=False,
        repair=False,
        progress=False,
        group_by="column",
        threads=False,
        multi_level_index=True,
    )
    return extract_adjusted_closes(downloaded, tickers)


def _load_matching_cache(
    price_path: Path,
    metadata_path: Path,
    requested: dict[str, object],
    tickers: Sequence[str],
) -> pd.DataFrame | None:
    if not price_path.exists() or not metadata_path.exists():
        return None

    with metadata_path.open(encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
    if any(metadata.get(key) != value for key, value in requested.items()):
        return None

    cached = pd.read_csv(price_path, index_col="Date", parse_dates=["Date"])
    return validate_price_frame(cached, tickers)


def load_or_download_adjusted_closes(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
    downloader: Callable[..., pd.DataFrame] | None = None,
    downloaded_at: datetime | None = None,
) -> pd.DataFrame:
    """Reuse a matching cache or download and cache adjusted closes."""
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    tickers = [asset["ticker"] for asset in config["assets"]]
    start = start or config["project"]["expected_earliest_common_start"]
    end = end or date.today().isoformat()
    _validate_request_dates(start, end)

    requested: dict[str, object] = {
        "tickers": tickers,
        "start": start,
        "end_exclusive": end,
        "interval": "1d",
        "auto_adjust": True,
    }
    price_path = cache_dir / "adjusted_close.csv"
    metadata_path = cache_dir / "adjusted_close.metadata.json"

    if not refresh:
        cached = _load_matching_cache(price_path, metadata_path, requested, tickers)
        if cached is not None:
            return cached

    prices = download_adjusted_closes(
        tickers,
        start,
        end,
        downloader=downloader,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    prices.index.name = "Date"
    prices.to_csv(price_path)

    timestamp = downloaded_at or datetime.now(timezone.utc)
    metadata = {
        **requested,
        "downloaded_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance",
        "price_field": "Close with auto_adjust=True",
    }
    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)
        metadata_file.write("\n")

    return prices
