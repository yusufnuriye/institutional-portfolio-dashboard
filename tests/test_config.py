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


def test_proxy_selection_checkpoint_is_recorded() -> None:
    """Keep the user's approval separate from final-universe approval."""
    project = load_config()["project"]

    assert project["proxy_selection_status"] == (
        "user_verified_pending_role_currency_and_data_validation"
    )
    assert project["proxy_selection_approved_by"] == "Yusuf"
    assert project["proxy_selection_approved_on"] == "2026-08-11"
    assert project["universe_status"] == (
        "user_verified_pending_historical_data_validation"
    )


def test_investment_role_checkpoint_is_recorded() -> None:
    """Record role approval without prematurely approving the universe."""
    project = load_config()["project"]

    assert project["investment_roles_status"] == (
        "user_verified_pending_currency_and_data_validation"
    )
    assert project["investment_roles_approved_by"] == "Yusuf"
    assert project["investment_roles_approved_on"] == "2026-08-11"
    assert project["universe_status"] == (
        "user_verified_pending_historical_data_validation"
    )


def test_currency_exposure_checkpoint_is_recorded() -> None:
    """Record currency approval without prematurely approving the universe."""
    project = load_config()["project"]

    assert project["currency_exposure_status"] == (
        "user_verified_pending_historical_data_validation"
    )
    assert project["currency_exposure_approved_by"] == "Yusuf"
    assert project["currency_exposure_approved_on"] == "2026-08-11"
    assert project["universe_status"] == (
        "user_verified_pending_historical_data_validation"
    )


def test_provisional_universe_checkpoint_is_recorded() -> None:
    """Record conditional approval while data validation remains pending."""
    project = load_config()["project"]

    assert project["universe_status"] == (
        "user_verified_pending_historical_data_validation"
    )
    assert project["universe_approved_by"] == "Yusuf"
    assert project["universe_approved_on"] == "2026-08-11"


def test_data_and_modelling_rules_checkpoint_is_recorded() -> None:
    """Lock the reviewed rules without claiming implementation is complete."""
    config = load_config()
    project = config["project"]
    methodology = config["methodology"]

    assert project["data_modelling_rules_status"] == (
        "user_verified_pending_implementation_and_data_validation"
    )
    assert project["data_modelling_rules_approved_by"] == "Yusuf"
    assert project["data_modelling_rules_approved_on"] == "2026-08-11"
    assert methodology["price_treatment"] == "adjusted_prices"
    assert methodology["comparison_window"] == "common_history_only"
    assert methodology["large_gap_policy"] == "do_not_fill_automatically"
    assert methodology["daily_return_type"] == "simple"
    assert methodology["strategic_return_frequency"] == "monthly"
    assert methodology["cagr_method"] == "geometric_from_cumulative_wealth"
    assert methodology["rebalancing_frequency"] == "monthly"
    assert methodology["historical_results_are_forecasts"] is False


def test_repository_and_technical_setup_checkpoint_is_recorded() -> None:
    """Approve the repository foundation without closing Day 1 early."""
    project = load_config()["project"]

    assert project["repository_technical_setup_status"] == (
        "user_verified_pending_final_day_1_inspection"
    )
    assert project["repository_technical_setup_approved_by"] == "Yusuf"
    assert project["repository_technical_setup_approved_on"] == "2026-08-11"
    assert project["day_1_status"] == "pending_final_inspection_and_sign_off"
