from __future__ import annotations

import re
from pathlib import Path


CSS_PATH = Path(__file__).resolve().parents[1] / "www" / "public-demo.css"


def test_public_demo_css_hides_external_controls_without_hiding_reporting_navset() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    executable_css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

    assert '.card:has(#reporting-recipe_upload)' not in executable_css
    assert '.shiny-input-container:has(input[type="file"])' in executable_css
    assert '#load_upload' in executable_css
    assert '[id$="-load_target"]' in executable_css
    assert '[id$="-validate_recipe"]' in executable_css
    assert '[id$="-restore_recipe"]' in executable_css
