from __future__ import annotations

from pathlib import Path


CSS_PATH = Path(__file__).resolve().parents[1] / "www" / "public-demo.css"


def test_public_demo_css_hides_external_controls_without_hiding_reporting_navset() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")

    assert '.card:has(#reporting-recipe_upload)' not in css
    assert '.shiny-input-container:has(input[type="file"])' in css
    assert '#load_upload' in css
    assert '[id$="-load_target"]' in css
    assert '[id$="-validate_recipe"]' in css
    assert '[id$="-restore_recipe"]' in css
