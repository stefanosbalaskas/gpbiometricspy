from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_scr_habituation_vector_and_groups():
    dat = pd.DataFrame({
        "participant": np.repeat(["P01", "P02"], 5),
        "trial": np.tile(np.arange(1, 6), 2),
        "scr_amplitude": [1, .8, .6, .4, .2, 2, 1.8, 1.5, 1.2, 1],
    })
    out = gp.compute_gazepoint_scr_habituation(dat, amplitude_col="scr_amplitude", trial_col="trial", subject_col="participant")
    assert len(out) == 2
    assert (out.habituation_slope < 0).all()
    assert (out.last_first_ratio < 1).all()
    vec = gp.compute_gazepoint_scr_habituation([1, .8, .6, .4])
    assert len(vec) == 1 and vec.habituation_slope.iloc[0] < 0
    ratio = gp.compute_gazepoint_scr_habituation([1, .8, .6], method="ratio")
    assert np.isnan(ratio.habituation_slope.iloc[0]) and ratio.last_first_ratio.iloc[0] < 1


def test_scr_recovery_and_pupil_events():
    time = np.arange(0, 10.01, .1)
    gsr = np.exp(-((time - 3) ** 2) / .05) * .8
    gsr[time > 3] *= np.exp(-(time[time > 3] - 3) / 2)
    rec = gp.summarize_gazepoint_scr_recovery(pd.DataFrame({"time_s": time, "GSR": gsr}), events=[2], pre=1, post=6)
    assert len(rec) == 1 and rec.peak_amplitude.iloc[0] > .1 and np.isfinite(rec.peak_latency_s.iloc[0])
    pupil = 3 + np.exp(-((time - 3) ** 2) / .2) * .5
    pup = gp.summarize_gazepoint_pupil_events(pd.DataFrame({"time_s": time, "LPD": pupil}), events=[2], pre=1, post=4, pupil_col="LPD")
    assert pup.pupil_peak_dilation.iloc[0] > .2 and pup.pupil_auc.iloc[0] > 0
    empty = gp.summarize_gazepoint_scr_recovery(pd.DataFrame({"time_s": time, "GSR": gsr}), events=[100], pre=1, post=2)
    assert empty.n_samples.iloc[0] == 0 and not empty.recovered.iloc[0]


def test_tracking_and_luminance():
    dat = pd.DataFrame({
        "participant": ["P01", "P01", "P01", "P02"],
        "LPD": [3, np.nan, 3, 3], "LPV": [1, 0, 1, 1],
        "BPOGX": [.1, .2, 2, .3], "BPOGY": [.1, .2, .3, .4],
    })
    out = gp.summarize_gazepoint_tracking(dat, pupil_cols="LPD", group_cols="participant")
    assert len(out) == 2
    assert out.loc[out.participant == "P01", "tracking_ratio"].iloc[0] < 1
    assert out.loc[out.participant == "P02", "tracking_ratio"].iloc[0] == 1
    lum = gp.audit_gazepoint_pupil_luminance(pd.DataFrame({"LPD": np.arange(1, 11), "luminance": np.arange(1, 11)}), pupil_col="LPD", luminance_col="luminance", threshold=.3)
    assert bool(lum.flag_luminance_confound.iloc[0]) and lum.correlation.iloc[0] > .9
    sp = gp.audit_gazepoint_pupil_luminance(pd.DataFrame({"LPD": [1, 2, 3, 4], "luminance": [1, 3, 2, 4]}), method="spearman")
    assert sp.method.iloc[0] == "spearman"


def test_ppg_morphology_quality_and_template():
    time = np.arange(0, 10.001, .01)
    ppg = np.sin(2 * np.pi * time)
    dat = pd.DataFrame({"time_s": time, "PPG": ppg})
    morph = gp.extract_gazepoint_ppg_morphology(dat, min_peak_distance_s=.5)
    assert len(morph) >= 5 and (morph.pulse_amplitude > 0).all() and (morph.rise_time_s >= 0).all()
    assert morph.peak_index.min() >= 1
    qtime = np.arange(0, 20.01, .1); qppg = np.sin(qtime); qppg[(qtime >= 10) & (qtime < 20)] = 1
    quality = gp.flag_gazepoint_ppg_quality(pd.DataFrame({"time_s": qtime, "PPG": qppg}), window_s=10, flat_sd_threshold=.001)
    assert len(quality) >= 2 and (~quality.quality_ok).any()
    peaks = np.arange(.25, 9.26, 1)
    sim = gp.compute_gazepoint_ppg_template_similarity(dat, peaks=peaks)
    assert len(sim["beats"]) >= 8 and sim["summary"].mean_similarity.iloc[0] > .95
    no = gp.compute_gazepoint_ppg_template_similarity(np.ones(20), sampling_rate_hz=10)
    assert len(no["beats"]) == 0


def test_event_import_match_assert_info(tmp_path, capsys):
    p = tmp_path / "events.csv"
    p.write_text("trial,onset,condition\nT1,1,A\nT2,2,B\n")
    ev = gp.import_gazepoint_event_log(p, time_col="onset", event_col="condition", id_col="trial")
    assert ev.event_id.tolist() == ["T1", "T2"] and ev.event_label.tolist() == ["A", "B"] and ev.event_time.tolist() == [1, 2]
    dat = pd.DataFrame({"time_s": np.arange(11), "GSR": np.linspace(0, 1, 11)})
    e = pd.DataFrame({"trial": ["T1"], "onset": [5], "condition": ["A"]})
    windows = gp.match_gazepoint_events_to_biometrics(dat, e, pre=1, post=1, event_time_col="onset", event_id_col="trial", return_="windows")
    summary = gp.match_gazepoint_events_to_biometrics(dat, e, pre=1, post=1, event_time_col="onset", event_id_col="trial", return_="summary")
    assert len(windows) == 3 and summary.n_samples.iloc[0] == 3 and "GSR_mean" in summary.columns
    assert gp.assert_gazepoint_columns(dat, required=["time_s", "GSR"]) is True
    with pytest.raises(ValueError): gp.assert_gazepoint_columns(dat, required=["time_s", "PPG"])
    tab = gp.assert_gazepoint_columns(dat, required=["time_s", "PPG"], optional="GSR", mode="summary")
    assert not tab.loc[tab.column == "PPG", "present"].iloc[0]
    with pytest.warns(RuntimeWarning): gp.assert_gazepoint_columns(dat, required="PPG", mode="warning")
    info = gp.gpbiometrics_info(print=False); assert info["package"] == "gpbiometrics" and info["version"]
    gp.gpbiometrics_info(print=True); assert "gpbiometrics 2.0.0" in capsys.readouterr().out


def test_schema_simulation_sampling_drift():
    dat = pd.DataFrame({"time_s": [1, 2, 3], "GSR": [1, 2, 3]})
    audit = gp.audit_gazepoint_export_schema(dat, expected_roles=["time_s", "GSR", "PPG"])
    assert audit.loc[audit.role == "time_s", "status"].iloc[0] == "present"
    assert audit.loc[audit.role == "PPG", "status"].iloc[0] == "missing"
    with pytest.raises(ValueError): gp.audit_gazepoint_export_schema(dat, expected_roles=["PPG"], strict=True)
    sim = gp.simulate_gazepoint_multimodal_data(duration_s=4, sampling_rate_hz=10, seed=123)
    assert {"biometrics", "eye", "events", "fixations", "metadata"} <= sim.keys()
    assert {"GSR", "PPG", "HR", "IBI"} <= set(sim["biometrics"].columns)
    assert {"pupil_left", "gaze_x", "AOI"} <= set(sim["eye"].columns)
    irr = gp.assess_gazepoint_sampling_irregularity(pd.DataFrame({"time_s": [0, .1, .2, .3, 1, 1.1]}), time_col="time_s")
    assert irr.n_large_gaps.iloc[0] >= 1 and irr.effective_rate_hz.iloc[0] > 0
    ref = np.arange(11.); target = ref + .1 + .01 * ref
    drift = gp.diagnose_gazepoint_sync_drift(ref, target)
    assert drift["summary"].drift_slope_s_per_s.iloc[0] > 0 and len(drift["lag_table"]) == len(ref)


def test_aoi_dwell_scanpath():
    dwell_dat = pd.DataFrame({"participant": "P01", "trial": "T1", "time_s": np.arange(0, .6, .1), "AOI": ["left", "left", "center", "center", "left", "left"]})
    dwell = gp.summarize_gazepoint_aoi_dwell(dwell_dat, group_cols=["participant", "trial"])
    assert {"left", "center"} <= set(dwell.AOI)
    assert dwell.loc[dwell.AOI == "left", "dwell_time_s"].iloc[0] > dwell.loc[dwell.AOI == "center", "dwell_time_s"].iloc[0]
    assert dwell.loc[dwell.AOI == "left", "entry_count"].iloc[0] >= 2
    path = pd.DataFrame({"participant": "P01", "trial": "T1", "time_s": [1, 2, 3, 4], "gaze_x": [0, .2, .4, .1], "gaze_y": [0, .1, .2, .3], "AOI": ["A", "A", "B", "A"]})
    out = gp.summarize_gazepoint_scanpath_metrics(path, group_cols=["participant", "trial"])
    assert out.path_length.iloc[0] > 0 and out.saccade_count.iloc[0] > 0 and out.aoi_transition_count.iloc[0] >= 2


def test_manifest_wavelet_and_errors(tmp_path):
    inp = tmp_path / "x.csv"; inp.write_text("x,y\n1,2\n")
    manifest_path = tmp_path / "manifest.txt"
    m = gp.create_gazepoint_analysis_manifest(files=inp, settings={"window_s": 5, "threshold": .1}, outputs={"table": "features.csv"}, path=manifest_path, include_session=False)
    assert manifest_path.exists() and len(m["files"]) == 1 and m["package_version"] == "2.0.0"
    rr = 800 + 40 * np.sin(np.linspace(0, 8 * np.pi, 128))
    w = gp.compute_gazepoint_hrv_wavelet_psd(rr)
    assert len(w["psd"]) > 0 and {"vlf", "lf", "hf"} <= set(w["band_power"].band) and (w["psd"].wavelet_power >= 0).all()
    with pytest.raises(ValueError): gp.compute_gazepoint_hrv_wavelet_psd([800] * 7)
    with pytest.raises(ValueError): gp.diagnose_gazepoint_sync_drift([1], [1])
