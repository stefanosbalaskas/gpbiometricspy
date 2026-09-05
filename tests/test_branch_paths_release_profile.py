from __future__ import annotations

import pytest

import gpbiometricspy as gp


def test_release_profile_public_input_guardrails(tmp_path):
    with pytest.raises(ValueError):
        gp.audit_gazepoint_release_readiness(
            tmp_path,
            required_files=[None],
        )

    with pytest.raises(ValueError):
        gp.summarize_gazepoint_feature_coverage(
            tmp_path,
            exports=[],
            patterns={"": "import"},
        )

    with pytest.raises(ValueError):
        gp.create_gazepoint_release_checklist(include_optional="yes")

    with pytest.raises(ValueError):
        gp.audit_gazepoint_release_readiness(
            tmp_path,
            required_files=[],
            require_pkgdown="yes",
        )


def test_release_readiness_without_expected_exports(tmp_path):
    out = gp.audit_gazepoint_release_readiness(
        tmp_path,
        required_files=[],
        expected_exports=None,
        roadmap_terms=None,
        require_pkgdown=False,
    )
    assert not (out["checks"]["check"] == "expected_exports").any()


def test_export_profile_rejects_existing_non_directory(tmp_path):
    target = tmp_path / "not-a-folder.csv"
    target.write_text("x\n1\n")
    with pytest.raises(ValueError):
        gp.profile_gazepoint_export_folder(target)


def test_export_profile_comparison_residual_paths(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    p1 = gp.profile_gazepoint_export_folder(left)
    p2 = gp.profile_gazepoint_export_folder(right)

    combined = gp.compare_gazepoint_export_profiles([p1, p2])
    assert list(combined["labels"]) == ["profile_1", "profile_2"]
    assert combined["role_coverage"].empty

    with pytest.raises(ValueError):
        gp.compare_gazepoint_export_profiles(p1)

    with pytest.raises(ValueError):
        gp.compare_gazepoint_export_profiles(
            p1,
            p2,
            labels=["only-one"],
        )


def test_export_profile_write_guardrails(tmp_path):
    with pytest.raises(TypeError):
        gp.write_gazepoint_export_profile({}, tmp_path / "invalid")

    source = tmp_path / "source"
    source.mkdir()
    profile = gp.profile_gazepoint_export_folder(source)
    out_dir = tmp_path / "out"
    gp.write_gazepoint_export_profile(
        profile,
        out_dir,
        prefix="collision",
    )
    with pytest.raises(FileExistsError):
        gp.write_gazepoint_export_profile(
            profile,
            out_dir,
            prefix="collision",
        )
