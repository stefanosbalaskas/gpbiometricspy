from __future__ import annotations

from gpbiometricspy import mne_eeg_lsl as me


def test_session_info_missing_package_fallback(monkeypatch):
    """Exercise the PackageNotFoundError fallback deterministically on every OS."""
    original_version = me.metadata.version
    missing_name = "gpbiometricspy-definitely-not-installed-coverage-probe"

    def fake_version(name: str) -> str:
        if name == missing_name:
            raise me.metadata.PackageNotFoundError(name)
        return original_version(name)

    monkeypatch.setattr(me.metadata, "version", fake_version)
    info = me.session_info_gazepoint(
        packages=missing_name,
        include_loaded=False,
    )
    row = info["packages"].loc[
        info["packages"]["package"] == missing_name
    ].iloc[0]
    assert row["version"] == "not_installed"
