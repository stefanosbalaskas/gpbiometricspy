from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_artifact_missing_reproducible_and_validation():
    dat = pd.DataFrame({
        "participant": np.repeat(["P01", "P02"], 10),
        "time_ms": np.arange(0, 2000, 100),
        "pupil": np.linspace(3.0, 3.19, 20),
        "gsr": np.linspace(0.7, 0.89, 20),
    })
    a = gp.simulate_gazepoint_artifact(dat, ["pupil", "gsr"], artifact="missing_run", n_artifacts=1, artifact_length=3, seed=10)
    b = gp.simulate_gazepoint_artifact(dat, ["pupil", "gsr"], artifact="missing_run", n_artifacts=1, artifact_length=3, seed=10)
    pd.testing.assert_frame_equal(a["artifact_log"], b["artifact_log"])
    pd.testing.assert_frame_equal(a["data"], b["data"])
    assert list(a["artifact_log"].n_samples_modified) == [3, 3]
    assert a["data"].pupil_artifact.isna().any() and a["data"].gsr_artifact.isna().any()
    sim = gp.simulate_gazepoint_artifact(dat[["pupil"]], "pupil", artifact=["flatline", "spike", "noise", "drift"], artifact_length=2, magnitude=1, seed=99)
    assert len(sim["artifact_log"]) == 4
    over = gp.simulate_gazepoint_artifact(dat[["pupil"]], "pupil", artifact="drift", artifact_length=3, magnitude=1, seed=1, overwrite=True)
    assert "pupil_artifact" not in over["data"] and not over["data"].pupil.equals(dat.pupil)
    with pytest.raises(ValueError, match="not found"):
        gp.simulate_gazepoint_artifact(dat, "missing")
    with pytest.raises(TypeError, match="numeric"):
        gp.simulate_gazepoint_artifact(pd.DataFrame({"x": ["a", "b"]}), "x")
    with pytest.raises(ValueError, match="non-negative"):
        gp.simulate_gazepoint_artifact(dat, "pupil", n_artifacts=-1)
    with pytest.raises(ValueError, match="already exists"):
        gp.simulate_gazepoint_artifact(pd.DataFrame({"pupil": [1,2], "pupil_artifact": [0,0]}), "pupil")


def test_manifest_file_metadata_and_roundtrip(tmp_path):
    existing = tmp_path / "input.csv"; existing.write_text("participant,time_ms\nP01,0\n", encoding="utf-8")
    txt = tmp_path / "manifest.txt"; rds = tmp_path / "manifest.rds"
    m = gp.generate_gazepoint_manifest(
        input_paths=[existing, tmp_path / "missing.csv"],
        parameters={"step": "unit-test", "threshold": 0.2}, outputs="qc_table",
        notes="Synthetic test only", write_path=txt, include_session_info=False,
    )
    assert txt.exists() and len(m["input_files"]) == 2
    assert bool(m["input_files"].iloc[0].exists) and not bool(m["input_files"].iloc[1].exists)
    assert m["session_info"] is None and "parameter: step" in txt.read_text()
    m2 = gp.generate_gazepoint_manifest(parameters={"step":"rds-test"}, write_path=rds, include_session_info=False)
    with rds.open("rb") as f: restored = pickle.load(f)
    assert restored["parameters"]["step"] == "rds-test" and m2["parameters"]["step"] == "rds-test"
    with pytest.raises(TypeError, match="list/dict"):
        gp.generate_gazepoint_manifest(parameters="bad")


def test_dictionary_data_files_and_writes(tmp_path):
    dat = pd.DataFrame({"participant": ["P01", "P02", np.nan], "trial": [1,1,2], "pupil": [3.1,np.nan,3.2]})
    d = gp.create_gazepoint_dictionary(dat, units={"pupil":"arbitrary unit"}, descriptions={"participant":"Participant code"}, required_cols=["participant","trial","time_ms"])
    assert "time_ms" in d.column.values and not bool(d.loc[d.column=="time_ms","present"].iloc[0])
    assert d.loc[d.column=="pupil","unit"].iloc[0] == "arbitrary unit"
    assert d.loc[d.column=="participant","description"].iloc[0] == "Participant code"
    csv = tmp_path / "x.csv"; pd.DataFrame({"participant":["P01"],"time_ms":[0],"gsr":[.7]}).to_csv(csv,index=False)
    out_csv=tmp_path/"dictionary.csv"; out_md=tmp_path/"dictionary.md"
    f = gp.create_gazepoint_dictionary(file_paths=csv, required_cols=["participant","time_ms","pupil"], write_path=out_csv)
    assert out_csv.exists() and "pupil" in f.column.values and not bool(f.loc[f.column=="pupil","present"].iloc[0])
    gp.create_gazepoint_dictionary(file_paths=csv, required_cols="participant", write_path=out_md)
    assert out_md.exists() and "| column |" in out_md.read_text()
    with pytest.raises(ValueError, match="Supply either"):
        gp.create_gazepoint_dictionary()
    with pytest.raises(ValueError, match="names"):
        gp.create_gazepoint_dictionary(pd.DataFrame({"x":[1]}), units=["missing-name"])


def test_anonymize_deterministic_mapping():
    dat=pd.DataFrame({"participant":["S02","S01","S02",np.nan],"session":["B","A","B","C"],"value":[1,2,3,4]})
    anon=gp.anonymize_gazepoint_data(dat,["participant","session"],prefix="ID",width=2)
    assert anon.participant.tolist()[:3] == ["ID02","ID01","ID02"] and pd.isna(anon.participant.iloc[3])
    assert anon.session.tolist() == ["ID02","ID01","ID02","ID03"]
    assert set(anon.attrs["id_mapping"].columns) == {"column","original_value","anonymized_value"}
    no=gp.anonymize_gazepoint_data(dat,"participant",keep_mapping=False)
    assert "id_mapping" not in no.attrs
    with pytest.raises(ValueError, match="not found"):
        gp.anonymize_gazepoint_data(dat,"missing")


def test_baseline_correction_and_groups():
    gsr=pd.DataFrame({"trial":[1]*4,"GSR_US":[2.0,2.2,2.5,2.7],"GSRV":[1]*4,"baseline":[True,True,False,False]})
    out=gp.baseline_correct_gazepoint_gsr(gsr,gsr.baseline.to_numpy())
    np.testing.assert_allclose(out.GSR_US_baseline_corrected[:3],[-.1,.1,.4],atol=1e-8)
    assert out.attrs["baseline_summary"].iloc[0].baseline_usable_rows == 2
    assert out.attrs["baseline_summary"].iloc[0].baseline_value == pytest.approx(2.1)
    hr=pd.DataFrame({"participant":["P1"]*3+["P2"]*3,"HR":[70,72,80,60,62,70],"HRV":[1]*6,"baseline":[True,True,False,True,True,False]})
    h=gp.baseline_correct_gazepoint_hr(hr,hr.baseline.to_numpy(),group_columns="participant")
    assert h.HR_baseline_corrected.iloc[2] == pytest.approx(9) and h.HR_baseline_corrected.iloc[5] == pytest.approx(9)
    assert len(h.attrs["baseline_summary"]) == 2
    invalid=pd.DataFrame({"HR":[0,70,90],"HRV":[0,1,1],"baseline":[True,True,False]})
    z=gp.baseline_correct_gazepoint_hr(invalid,invalid.baseline.to_numpy())
    assert z.HR_baseline_corrected.iloc[2] == pytest.approx(20) and z.attrs["baseline_summary"].iloc[0].baseline_usable_rows==1


def test_smoothing_centered_and_validation():
    out=gp.smooth_gazepoint_biometrics(pd.DataFrame({"HR":[70,72,74,76,78]}),"HR",window=3)
    np.testing.assert_allclose(out.HR_smoothed,[71,72,74,76,77])
    with pytest.raises(ValueError, match="positive odd integer"):
        gp.smooth_gazepoint_biometrics(pd.DataFrame({"HR":[70,72,74]}),"HR",window=4)


def test_ibi_filter_units_validity_and_flags():
    dat=pd.DataFrame({"participant":"P1","IBI":[1000,1020,250,1050,2500,1080]})
    r=gp.filter_gazepoint_ibi_implausible(dat,ibi_col="IBI",group_cols="participant",min_ibi_ms=300,max_ibi_ms=2000,max_change_ms=500,max_change_prop=.5)
    assert r["overview"].iloc[0].detected_unit == "ms" and r["row_flags"].flag_too_low.any() and r["row_flags"].flag_too_high.any()
    sec=gp.filter_gazepoint_ibi_implausible(pd.DataFrame({"participant":"P1","IBI":[1.0,1.1,.9]}),group_cols="participant")
    assert sec["overview"].iloc[0].detected_unit=="seconds"; np.testing.assert_allclose(sec["row_flags"].ibi_ms,[1000,1100,900])
    val=gp.filter_gazepoint_ibi_implausible(pd.DataFrame({"participant":"P1","IBI":[1000]*3,"IBIV":[1,0,1]}),validity_col="IBIV",group_cols="participant")
    assert val["row_flags"].flag_invalid_validity.sum()==1 and val["data"].IBI_clean_ms.isna().sum()==1
    with pytest.raises(ValueError,match="ibi_col"):
        gp.filter_gazepoint_ibi_implausible(pd.DataFrame({"IBI":[1000]}),ibi_col="missing")


def test_hr_ibi_consistency_and_filtered_object():
    dat=pd.DataFrame({"participant":"P1","HR":[60,60,100],"IBI":[1000,1000,1000]})
    r=gp.compare_gazepoint_hr_ibi_consistency(dat,group_cols="participant",max_abs_diff_bpm=10)
    assert r["overview"].iloc[0].comparable_rows==3 and r["overview"].iloc[0].inconsistent_rows==1 and r["row_diagnostics"].flag_inconsistent.any()
    dat2=pd.DataFrame({"participant":"P1","HR":[60,55],"IBI":[1000,1090]})
    f=gp.filter_gazepoint_ibi_implausible(dat2,group_cols="participant")
    rr=gp.compare_gazepoint_hr_ibi_consistency(f,ibi_col="IBI_clean_ms",group_cols="participant")
    assert rr["overview"].iloc[0].comparable_rows==2
    with pytest.raises(ValueError,match="hr_col"):
        gp.compare_gazepoint_hr_ibi_consistency(pd.DataFrame({"IBI":[1000]}))


def test_hrv_features_repeat_collapse_short_and_groups():
    dat=pd.DataFrame({"participant":"P1","IBI_clean_ms":[1000,1000,1000,1020,1020,980,980,1010]})
    r=gp.extract_gazepoint_hrv_features(dat,group_cols="participant",min_intervals=3,min_duration_s=0)
    row=r["features"].iloc[0]; assert row.input_interval_rows==8 and row.used_intervals_after_collapse==4 and bool(row.collapsed_repeated_intervals) and row.n_intervals==4 and row.feature_status=="features_computed"
    r2=gp.extract_gazepoint_hrv_features(dat,group_cols="participant",min_intervals=3,min_duration_s=0,collapse_repeated_intervals=False)
    assert r2["features"].iloc[0].n_intervals==8
    x=pd.DataFrame({"participant":"P1","IBI_clean_ms":[1000,1020,980,1010,990]})
    f=gp.extract_gazepoint_hrv_features(x,group_cols="participant",min_intervals=3,min_duration_s=0)
    assert f["overview"].iloc[0].status=="hrv_features_computed" and np.isfinite(f["features"].iloc[0].sdnn_ms) and np.isfinite(f["features"].iloc[0].rmssd_ms)
    short=gp.extract_gazepoint_hrv_features(x,group_cols="participant",min_intervals=3,min_duration_s=30)
    assert short["overview"].iloc[0].status=="warn_short_hrv_duration" and short["features"].iloc[0].feature_status=="warn_short_hrv_duration"
    insuff=gp.extract_gazepoint_hrv_features(pd.DataFrame({"participant":"P1","IBI_clean_ms":[1000,1020]}),group_cols="participant",min_intervals=3)
    assert insuff["overview"].iloc[0].status=="fail_no_hrv_features_computed"
    groups=pd.DataFrame({"participant":["P1"]*4+["P2"]*4,"IBI_clean_ms":[1000,1010,990,1005,800,810,790,805]})
    g=gp.extract_gazepoint_hrv_features(groups,group_cols="participant",min_intervals=3,min_duration_s=0)
    assert len(g["features"])==2 and (g["features"].feature_status=="features_computed").all()
    with pytest.raises(ValueError,match="collapse_repeated_intervals"):
        gp.extract_gazepoint_hrv_features(x,collapse_repeated_intervals=None)
    with pytest.raises(ValueError,match="repeated_tolerance_ms"):
        gp.extract_gazepoint_hrv_features(x,repeated_tolerance_ms=-1)
    with pytest.raises(ValueError,match="min_duration_s"):
        gp.extract_gazepoint_hrv_features(x,min_duration_s=-1)
