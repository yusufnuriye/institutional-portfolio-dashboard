"""Acceptance checks for the reviewed Day 1 configuration."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    """Load the asset configuration used by the dashboard."""
    with (ROOT / "config" / "assets.yml").open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def test_asset_universe_has_seven_unique_tickers() -> None:
    """Reject duplicate proxies before any data is downloaded."""
    assets = load_config()["assets"]
    tickers = [asset["ticker"] for asset in assets]

    assert len(assets) == 7
    assert len(tickers) == len(set(tickers))


def test_sixty_forty_reference_is_fully_invested() -> None:
    """The transparent reference portfolio must sum exactly to one."""
    config = load_config()
    tickers = {asset["ticker"] for asset in config["assets"]}
    weights = config["reference_portfolios"]["sixty_forty"]

    assert set(weights) == tickers
    assert sum(weights.values()) == 1.0


def test_sixty_forty_reference_has_expected_growth_defensive_split() -> None:
    """Check the documented 60% equity and 40% fixed-income split."""
    config = load_config()
    weights = config["reference_portfolios"]["sixty_forty"]
    fixed_income = config["constraints"]["fixed_income_tickers"]

    defensive_weight = sum(weights[ticker] for ticker in fixed_income)

    assert defensive_weight == 0.40
    assert sum(weights.values()) - defensive_weight == 0.60


def test_every_asset_records_a_product_source() -> None:
    """Every proxy decision must be traceable to a product page."""
    assets = load_config()["assets"]

    assert all(asset["source_url"].startswith("https://") for asset in assets)


def test_instrument_verification_is_recorded() -> None:
    """The approved official-source check must remain explicit."""
    project = load_config()["project"]

    assert project["instrument_verification_status"] == "approved"
    assert project["ingestion_and_cache_status"] == "approved"
    assert project["alignment_and_validation_status"] == "approved"
    assert project["return_calculation_status"] == "approved"
    assert project["official_sources_verified_on"] == "2026-08-18"
    assert project["expected_earliest_common_start"] == "2017-11-23"


def test_day_two_signoff_preserves_live_data_boundary() -> None:
    """Implementation sign-off must not falsely finalise untested live data."""
    project = load_config()["project"]

    assert project["day_2_status"] == "complete_live_download_pending"
    assert project["universe_status"] == "provisional_until_day_2_validation"


def test_vehicle_types_distinguish_etfs_from_etcs() -> None:
    """Gold and broad commodities are ETCs; the other proxies are ETFs."""
    assets = {asset["ticker"]: asset for asset in load_config()["assets"]}

    assert {ticker for ticker, asset in assets.items() if asset["instrument_type"] == "ETC"} == {
        "SGLN.L",
        "AGCP.L",
    }
    assert all(asset["instrument_type"] == "ETF" for ticker, asset in assets.items() if ticker not in {"SGLN.L", "AGCP.L"})
    assert all("lse_listing_date" in asset for asset in assets.values())
