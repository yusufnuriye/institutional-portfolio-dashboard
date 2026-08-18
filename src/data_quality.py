"""Common-history alignment and transparent market-data quality checks."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.data_pipeline import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG_PATH,
    DataPipelineError,
    load_or_download_adjusted_closes,
    load_tickers,
    validate_price_frame,
)


def _iso_date(value: pd.Timestamp) -> str:
    return value.date().isoformat()


def align_and_validate_prices(
    prices: pd.DataFrame,
    tickers: Sequence[str],
    *,
    minimum_common_rows: int = 1_260,
    minimum_common_years: float = 5.0,
    maximum_absolute_daily_return: float = 0.50,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Align on complete dates and report every observation removed.

    No missing value is filled. A large one-day move is rejected for manual
    review because it may indicate a unit, split or provider error.
    """
    validated = validate_price_frame(prices, tickers)
    raw_returns = validated.pct_change(fill_method=None)
    suspicious = raw_returns.abs() > maximum_absolute_daily_return
    if suspicious.any().any():
        affected = suspicious.any()[suspicious.any()].index.tolist()
        raise DataPipelineError(
            "Daily adjusted-price moves above "
            f"{maximum_absolute_daily_return:.0%} require manual review: {affected}"
        )

    common = validated.dropna(how="any")
    if len(common) < minimum_common_rows:
        raise DataPipelineError(
            f"Only {len(common)} complete common rows; at least "
            f"{minimum_common_rows} are required."
        )
    if common.empty:
        raise DataPipelineError("No date contains valid prices for all tickers.")

    elapsed_years = (common.index[-1] - common.index[0]).days / 365.2425
    if elapsed_years < minimum_common_years:
        raise DataPipelineError(
            f"The common history spans only {elapsed_years:.2f} years; at least "
            f"{minimum_common_years:.2f} years are required."
        )

    raw_rows = len(validated)
    common_rows = len(common)
    asset_quality: dict[str, dict[str, object]] = {}
    for ticker in tickers:
        series = validated[ticker]
        asset_quality[ticker] = {
            "first_valid_date": _iso_date(series.first_valid_index()),
            "last_valid_date": _iso_date(series.last_valid_index()),
            "valid_observations": int(series.count()),
            "missing_observations_in_union": int(series.isna().sum()),
            "missing_percentage_in_union": round(float(series.isna().mean() * 100), 4),
        }

    report: dict[str, object] = {
        "tickers": list(tickers),
        "raw_union_start": _iso_date(validated.index[0]),
        "raw_union_end": _iso_date(validated.index[-1]),
        "raw_union_rows": raw_rows,
        "common_start": _iso_date(common.index[0]),
        "common_end": _iso_date(common.index[-1]),
        "common_rows": common_rows,
        "rows_removed_for_common_alignment": raw_rows - common_rows,
        "percentage_rows_removed": round((raw_rows - common_rows) / raw_rows * 100, 4),
        "common_elapsed_years": round(elapsed_years, 4),
        "alignment_policy": "Intersection of dates with a valid price for every ticker",
        "forward_fill_used": False,
        "maximum_absolute_daily_return_check": maximum_absolute_daily_return,
        "asset_quality": asset_quality,
    }
    common.index.name = "Date"
    return common, report


def save_common_history(
    common_prices: pd.DataFrame,
    report: dict[str, object],
    cache_dir: Path = DEFAULT_CACHE_DIR,
    *,
    validated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Persist the aligned data and its auditable quality report."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    price_path = cache_dir / "common_adjusted_close.csv"
    report_path = cache_dir / "data_quality_report.json"

    common_prices.to_csv(price_path)
    timestamp = validated_at or datetime.now(timezone.utc)
    output_report = {
        **report,
        "validated_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
    }
    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(output_report, report_file, indent=2)
        report_file.write("\n")
    return price_path, report_path


def build_validated_common_history(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Download/cache, align, validate and save the common price history."""
    tickers = load_tickers(config_path)
    prices = load_or_download_adjusted_closes(
        config_path=config_path,
        cache_dir=cache_dir,
        start=start,
        end=end,
        refresh=refresh,
    )
    common, report = align_and_validate_prices(prices, tickers)
    save_common_history(common, report, cache_dir)
    return common, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh and validate Harbourstone market data.")
    parser.add_argument("--refresh", action="store_true", help="Ignore a matching local cache.")
    parser.add_argument(
        "--end",
        default=date.today().isoformat(),
        help="Exclusive end date in YYYY-MM-DD format.",
    )
    args = parser.parse_args()

    _, report = build_validated_common_history(refresh=args.refresh, end=args.end)
    print(
        "Validated common history: "
        f"{report['common_start']} to {report['common_end']} "
        f"({report['common_rows']} observations)."
    )


if __name__ == "__main__":
    main()
