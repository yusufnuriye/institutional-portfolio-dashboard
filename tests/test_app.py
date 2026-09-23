"""Smoke test for the reproducible Streamlit interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_demo_starts_without_exception() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path, default_timeout=30).run()

    assert not app.exception
    assert app.title[0].value == "Harbourstone Foundation"
    assert any("DEMONSTRATION MODE" in warning.value for warning in app.warning)
    assert len(app.tabs) == 5
