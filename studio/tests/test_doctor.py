
from __future__ import annotations

import json

from studio.doctor import doctor_payload, format_doctor, main, run_doctor


def test_doctor_reports_required_local_product_surfaces():
    checks = {check.name: check for check in run_doctor()}
    assert checks["shiny_dependency"].passed is True
    assert checks["studio_app"].passed is True
    assert checks["studio_css"].passed is True
    assert checks["localhost_bind"].passed is True


def test_doctor_payload_and_text_are_privacy_safe_and_actionable():
    payload = doctor_payload()
    assert payload["product"] == "gpbiometricspy Studio"
    assert isinstance(payload["checks"], list)
    text = format_doctor(payload)
    assert "Studio doctor" in text
    assert "Overall: READY" in text


def test_doctor_json_cli(capsys):
    assert main(["--json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["ok"] is True
