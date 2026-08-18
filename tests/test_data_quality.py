"""Tests for common-history alignment and data-quality reporting."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data_pipeline import DataPipelineError
from src.data_quality import align_and_validate_prices, save_common_history


TICKERS = ["VWRL.L", "CUKX.L", "IGLT.L", "AGBP.L", "SLXX.L", "SGLN.L", "AGCP.L"]


def sample_prices() -> pd.DataFrame:
    dates = pd.to_datetime(["2017-11-23", "2017-11-24", "2017-11-27", "2017-11-28"])
    frame = pd.DataFrame(
        {
            ticker: [100.0 + position, 101.0 + position, 102.0 + position, 103.0 + position]
            for position, ticker in enumerate(TICKERS)
        },
        index=dates,
    )
    frame.loc["2017-11-24", "AGCP.L"] = float("nan")
    return frame


def test_alignment_uses_only_dates_shared_by_all_assets() -> None:
    common, report = align_and_validate_prices(
        sample_prices(),
        TICKERS,
        minimum_common_rows=3,
        minimum_common_years=0,
    )

    assert common.index.tolist() == pd.to_datetime(
        ["2017-11-23", "2017-11-27", "2017-11-28"]
    ).tolist()
    assert report["rows_removed_for_common_alignment"] == 1
    assert report["forward_fill_used"] is False
    assert report["asset_quality"]["AGCP.L"]["missing_observations_in_union"] == 1


def test_large_daily_move_requires_manual_review() -> None:
    prices = sample_prices()
    prices.loc["2017-11-27", "SGLN.L"] = 1_000.0

    try:
        align_and_validate_prices(
            prices,
            TICKERS,
            minimum_common_rows=3,
            minimum_common_years=0,
        )
    except DataPipelineError as error:
        assert "SGLN.L" in str(error)
    else:
        raise AssertionError("A suspicious daily move should fail validation.")


def test_common_history_must_be_long_enough() -> None:
    try:
        align_and_validate_prices(
            sample_prices(),
            TICKERS,
            minimum_common_rows=1_260,
            minimum_common_years=5,
        )
    except DataPipelineError as error:
        assert "complete common rows" in str(error)
    else:
        raise AssertionError("An insufficient common history should fail validation.")


def test_quality_report_is_saved_with_validation_time() -> None:
    common, report = align_and_validate_prices(
        sample_prices(),
        TICKERS,
        minimum_common_rows=3,
        minimum_common_years=0,
    )

    with TemporaryDirectory() as temporary_directory:
        price_path, report_path = save_common_history(
            common,
            report,
            Path(temporary_directory),
            validated_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )
        saved_report = report_path.read_text(encoding="utf-8")

    assert price_path.name == "common_adjusted_close.csv"
    assert '"validated_at_utc": "2026-08-18T00:00:00+00:00"' in saved_report
