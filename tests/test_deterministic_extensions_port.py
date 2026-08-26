import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt

import gpbiometricspy as gp


def test_plot_contracts_and_aliases():
    dat = pd.DataFrame({"x": [1,2,3], "y": [2,3,4]})
    fig, _ = plt.subplots()
    p = gp.standardise_gazepoint_plot_contract(fig, dat, {"plot_type":"point"}, "Complete contract.", "point")
    chk = gp.check_gazepoint_plot_contract(p)
    assert chk["overview"].loc[0,"status"] == "pass_plot_contract"
    assert chk["overview"].loc[0,"plot_data_rows"] == 3
    pd.testing.assert_frame_equal(gp.get_gazepoint_plot_data(p), dat)
    assert gp.get_gazepoint_plot_settings(p)["plot_type"] == "point"

    bare, _ = plt.subplots()
    assert gp.check_gazepoint_plot_contract(bare, False, False)["overview"].loc[0,"status"] == "warn_partial_plot_contract"
    assert gp.check_gazepoint_plot_contract(bare)["overview"].loc[0,"status"] == "fail_plot_contract"
    f1,_=plt.subplots();f2,_=plt.subplots()
    out=gp.standardize_gazepoint_plot_contracts({"first":f1,"second":f2},[dat,dat],[{"plot_type":"a"},{"plot_type":"b"}],["n1","n2"],["a","b"])
    assert list(out)==["first","second"] and gp.get_gazepoint_plot_settings(out["second"])["plot_type"]=="b"
    with pytest.raises(TypeError): gp.standardise_gazepoint_plot_contract("bad")
    with pytest.raises(ValueError): gp.get_gazepoint_plot_data(bare)
    plt.close("all")


def test_within_unit_standardization_and_reference_zero_sd():
    dat=pd.DataFrame({"participant":np.repeat(["p1","p2"],5),"GSR_US":[1,2,3,4,5,10,20,30,40,50],"HR":[70,71,72,73,74,80,82,84,86,88]})
    out=gp.standardize_gazepoint_biometrics_within_unit(dat,["GSR_US","HR"],["participant"])
    assert np.isclose(out[out.participant.eq("p1")].GSR_US_z_within.mean(),0)
    assert np.isclose(out[out.participant.eq("p2")].GSR_US_z_within.std(ddof=1),1)
    assert out.attrs["standardization_summary"].loc[0,"status"]=="within_unit_standardization_complete"
    alias=gp.standardise_gazepoint_biometrics_within_unit(dat,["GSR_US"],["participant"])
    assert "GSR_US_z_within" in alias

    ref=pd.DataFrame({"participant":["p1"]*4,"baseline":[True,True,False,False],"GSR_US":[1,1,3,4]})
    z=gp.standardize_gazepoint_biometrics_within_unit(ref,["GSR_US"],["participant"],"baseline",True,zero_sd_action="zero")
    assert np.allclose(z.GSR_US_z_within,0,equal_nan=False)
    with pytest.raises(ValueError,match="output columns"):
        gp.standardize_gazepoint_biometrics_within_unit(out,["GSR_US"],["participant"])


def test_external_interoperability_rhrv_neurokit(tmp_path):
    dat=pd.DataFrame({"participant":"P1","IBI_clean_ms":[1000,1000,1020,1020,980]})
    r=gp.export_gazepoint_rhrv_input(dat,group_cols=["participant"])
    assert r["overview"].loc[0,"status"]=="rhrv_input_prepared"
    assert r["beat_table"].ibi_ms.tolist()==[1000,1020,980]
    alias=gp.prepare_gazepoint_rhrv_input(dat,group_cols=["participant"])
    pd.testing.assert_frame_equal(alias["beat_table"],r["beat_table"])
    rf=gp.export_gazepoint_rhrv_input(pd.DataFrame({"participant":["P1","P1","P2","P2"],"IBI_clean_ms":[1000,1020,900,910]}),group_cols=["participant"],output_dir=tmp_path/"rhrv")
    assert rf["manifest"].file_path.map(lambda p: __import__('pathlib').Path(p).exists()).all()

    eda=pd.DataFrame({"participant":"P1","CNT":range(5),"GSR_US":[1,1.1,1.2,1.1,1]})
    n=gp.prepare_gazepoint_neurokit_eda_input(eda,time_col="CNT",group_cols=["participant"],sampling_rate=10)
    assert np.allclose(n["eda_table"].time_s,[0,.1,.2,.3,.4])
    skip=gp.run_gazepoint_neurokit_eda_crosscheck(n,sampling_rate=10,execute=False)
    assert skip["overview"].loc[0,"status"]=="skipped_execute_false" and not skip["overview"].loc[0,"executed"]
    with pytest.raises(ValueError,match="ibi_col"):gp.export_gazepoint_rhrv_input(dat,ibi_col="missing")


def test_signal_lag_and_sync_drift_fixtures():
    n=120;x=np.zeros(n);y=np.zeros(n);x[29:50]=1;y[34:55]=1
    dat=pd.DataFrame({"participant":"p1","time_ms":np.arange(1,n+1),"x":x,"y":y})
    out=gp.estimate_gazepoint_signal_lag(dat,"x","y","time_ms",["participant"],10,1,min_complete_pairs=20)
    assert out["overview"].loc[0,"status"]=="estimated"
    assert out["lag_by_group"].loc[0,"estimated_lag"]==5
    poor=gp.estimate_gazepoint_signal_lag(pd.DataFrame({"x":range(5),"y":range(5)}),"x","y",max_lag=2,lag_step=1,min_complete_pairs=20)
    assert poor["lag_by_group"].loc[0,"status"]=="insufficient_data"

    def group(pid,delay):
        n=140;x=np.zeros(n);y=np.zeros(n);x[39:60]=1;y[39+delay:60+delay]=1
        return pd.DataFrame({"participant":pid,"time_ms":np.arange(1,n+1),"x":x,"y":y})
    both=pd.concat([group("p1",2),group("p2",6)],ignore_index=True)
    aud=gp.audit_gazepoint_biometric_sync_drift(both,time_col="time_ms",group_cols=["participant"],signal_pairs=pd.DataFrame({"signal_x":["x"],"signal_y":["y"]}),max_lag=8,lag_step=1,drift_tolerance=2,min_complete_pairs=20,include_reset_segments=False)
    assert len(aud["lag_by_group"])==2 and aud["drift_summary"].loc[0,"status"]=="drift_exceeds_tolerance"
    none=gp.audit_gazepoint_biometric_sync_drift(pd.DataFrame({"x":range(20)}),signal_cols=["x"])
    assert none["overview"].loc[0,"status"]=="no_signal_pairs"


def test_pyppg_preparation_and_quality(tmp_path):
    dat=pd.DataFrame({"participant":np.repeat(["p1","p2"],30),"CNT":np.tile(np.arange(1,31),2),"HRP":np.r_[np.sin(np.linspace(0,2*np.pi,30)),np.cos(np.linspace(0,2*np.pi,30))]})
    out=gp.prepare_gazepoint_pyppg_input(dat,time_col="CNT",group_cols=["participant"],sampling_rate=60)
    assert out["overview"].loc[0,"status"]=="pyppg_input_prepared" and len(out["waveform_table"])==len(dat)
    assert set(out["group_summary"].status)=={"ready_for_pyppg_input"}
    sample=gp.prepare_gazepoint_pyppg_input(pd.DataFrame({"participant":"p1","HRP":np.sin(np.linspace(0,2*np.pi,20))}),group_cols=["participant"])
    assert sample["group_summary"].loc[0,"status"]=="prepared_with_sample_index_only"
    written=gp.prepare_gazepoint_pyppg_input(dat.iloc[:20],time_col="CNT",group_cols=["participant"],sampling_rate=60,output_dir=tmp_path)
    assert len(written["manifest"])==2

    qdat=pd.DataFrame({"participant":"p1","time_ms":np.arange(0,800,10),"HRP":np.sin(np.linspace(0,6*np.pi,80))})
    q=gp.assess_gazepoint_hrp_waveform_quality(qdat,hrp_col="HRP",time_col="time_ms",group_cols=["participant"],min_rows=20)
    assert q["overview"].loc[0,"status"]=="pass"
    flat=gp.assess_gazepoint_hrp_waveform_quality(pd.DataFrame({"participant":"p1","time_ms":np.arange(0,500,10),"HRP":1.0}),time_col="time_ms",group_cols=["participant"])
    assert flat["group_quality"].loc[0,"status"]=="review_flat_signal"
    missing=pd.DataFrame({"participant":"p1","time_ms":np.arange(0,500,10),"HRP":[np.nan]*30+list(np.sin(np.linspace(0,2*np.pi,20)))})
    assert gp.assess_gazepoint_hrp_waveform_quality(missing,time_col="time_ms",group_cols=["participant"])["overview"].loc[0,"status"]=="fail_review_required"


def test_eda_decomposition_scr_and_reporting():
    existing=pd.DataFrame({"CNT":range(1,6),"GSR_US":[1,1.1,1.2,1.1,1],"GSR_US_TONIC":[1]*5,"GSR_US_PHASIC":[0,.1,.2,.1,0]})
    dec=gp.decompose_gazepoint_eda(existing,signal_col="GSR_US")
    assert np.allclose(dec.eda_phasic,existing.GSR_US_PHASIC)
    assert dec.attrs["overview"].loc[0,"method"]=="existing_tonic_phasic_columns"
    raw=pd.DataFrame({"CNT":range(1,8),"GSR_US":[1,1,1,2,1,1,1]})
    r=gp.decompose_gazepoint_eda(raw,signal_col="GSR_US",time_col="CNT",window_size=3,output_prefix="test_eda")
    assert (np.abs(r.test_eda_phasic)>0).any()
    ph=pd.DataFrame({"CNT":range(1,21),"GSR_US_PHASIC":[0]*5+[.2,.8,.2]+[0]*4+[.3,.9,.2]+[0]*5})
    ev=gp.detect_gazepoint_scr_events(ph,phasic_col="GSR_US_PHASIC",time_col="CNT",threshold=.5,min_peak_distance=3)
    assert ev["overview"].loc[0,"n_events"]==2 and ev["overview"].loc[0,"status"]=="scr_events_detected"
    no=gp.detect_gazepoint_scr_events(pd.DataFrame({"GSR_US_PHASIC":[0]*10}),phasic_col="GSR_US_PHASIC",threshold=.5)
    assert no["overview"].loc[0,"status"]=="no_scr_events_detected"

    report_data=pd.DataFrame({"TIME":[.01,.02,.03],"GSR_US":[2,2.1,2.2],"GSRV":[1]*3,"HR":[75,76,77],"HRV":[1]*3,"DIAL":[.1,.2,.3],"DIALV":[1]*3,"TTL0":[1]*3,"TTLV":[1]*3})
    checklist=gp.create_gazepoint_biometrics_checklist(report_data)
    assert checklist["overview"].loc[0,"active_gsr_eda"] and checklist["overview"].loc[0,"active_heart_rate"] and checklist["overview"].loc[0,"active_engagement_dial"]
    text=gp.create_gazepoint_biometrics_methods_text(checklist)
    assert "Gazepoint Biometrics" in text and "GSR/EDA" in text and "heart rate" in text and "engagement dial" in text and "conservatively" in text
    with pytest.raises(ValueError):gp.create_gazepoint_biometrics_methods_text()
