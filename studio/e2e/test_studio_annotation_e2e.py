from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
from shiny.playwright import controller
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _load_demo_participant(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    participant_path = Path(gp.kiosk_demo_files()[0])
    page.locator("#upload").set_input_files(str(participant_path))

    def _participant_uploaded(value) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
            and value[0].get("name") == participant_path.name
        )

    controller.AppTestValues(page).expect_input("upload", _participant_uploaded, timeout=30.0)
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    assert int(page.locator("#row_count").inner_text().replace(",", "")) == 1_920


def _plot_point(page: Page, x_fraction: float, y_fraction: float) -> tuple[float, float]:
    # Shiny binds plot click/brush handlers to the output container only after
    # the rendered image's load event, then marks the bound container crosshair.
    plot = page.locator("#annotation-signal_plot.crosshair")
    expect(plot).to_be_visible(timeout=60_000)
    box = plot.bounding_box()
    assert box is not None
    return (
        box["x"] + box["width"] * x_fraction,
        box["y"] + box["height"] * y_fraction,
    )


def _download_recipe(page: Page) -> dict:
    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    page.get_by_text("Project recipe", exact=True).click()
    expect(page.get_by_text("Save project recipe", exact=True)).to_be_visible()

    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    path = download_info.value.path()
    assert path is not None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_manual_annotation_export_and_provenance(page: Page, app: ShinyAppProc) -> None:
    _load_demo_participant(page, app)

    page.get_by_text("Annotation", exact=True).click()
    expect(page.get_by_text("Annotation controls", exact=True)).to_be_visible()
    expect(
        page.get_by_text(
            "Annotations are expert-review metadata. They do not infer emotion, stress, cognition, trust, preference, or diagnosis.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.locator("#annotation-signal_col")).to_have_value("GSR_US")
    expect(page.locator("#annotation-time_col")).to_have_value("TIME")
    expect(page.locator("#annotation-signal_plot img")).to_be_visible(timeout=60_000)
    expect(page.locator("#annotation-signal_plot.crosshair")).to_be_visible(timeout=60_000)

    page.locator("#annotation-note").fill("reviewed peak")
    peak_x, peak_y = _plot_point(page, 0.55, 0.50)
    page.mouse.click(peak_x, peak_y)
    expect(page.locator("#annotation-selection_info")).to_contain_text("Click x=", timeout=30_000)
    page.locator("#annotation-add_peak").click()
    expect(page.locator("#annotation-status")).to_contain_text("Manual peak added.", timeout=30_000)

    page.locator("#annotation-note").fill("motion artifact")
    start_x, brush_y = _plot_point(page, 0.35, 0.55)
    end_x, _ = _plot_point(page, 0.65, 0.55)
    page.mouse.move(start_x, brush_y)
    page.mouse.down()
    page.mouse.move(end_x, brush_y, steps=12)
    page.mouse.up()
    expect(page.locator("#annotation-selection_info")).to_contain_text("Brush x=[", timeout=30_000)
    page.locator("#annotation-add_artifact").click()
    expect(page.locator("#annotation-status")).to_contain_text("Artifact interval added.", timeout=30_000)

    expect(page.locator("#annotation-annotations")).to_be_visible()
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#annotation-download_annotations").click()
    path = download_info.value.path()
    assert path is not None
    rows = list(csv.DictReader(io.StringIO(Path(path).read_text(encoding="utf-8"))))
    assert len(rows) == 2
    assert [row["annotation_type"] for row in rows] == ["manual_peak", "artifact_interval"]
    assert [row["note"] for row in rows] == ["reviewed peak", "motion artifact"]
    assert rows[0]["time"] not in {"", "nan"}
    assert rows[1]["start"] not in {"", "nan"}
    assert rows[1]["end"] not in {"", "nan"}

    recipe = _download_recipe(page)
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    annotation_types = [row["annotation_type"] for row in recipe["annotations"]]
    assert annotation_types == ["manual_peak", "artifact_interval"]
    operations = [row["operation"] for row in recipe["provenance"]]
    assert operations.count("add_annotation") == 2
