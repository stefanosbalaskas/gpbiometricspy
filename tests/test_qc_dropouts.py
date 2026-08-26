from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_time_reset_audit_monotonic_reset_ties_and_nonnumeric():
    dat = pd.DataFrame({"source_file": np.repeat(["a.csv", "b.csv"], 5), "CNT": list(range(1,6))*2, "GSR_US": np.linspace(1,2,10)})
    res = gp.audit_gazepoint_time_resets(dat, time_col="CNT", group_cols="source_file")
    assert res["overview"].loc[0,"status"] == "pass"
    assert res["overview"].loc[0,"negative_steps"] == 0
    assert res["overview"].loc[0,"segment_count"] == 2

    reset = pd.DataFrame({"source_file":"a.csv","CNT":[1,2,3,1,2,3],"GSR_US":np.linspace(1,2,6)})
    rr = gp.audit_gazepoint_time_resets(reset,time_col="CNT",group_cols="source_file",return_reindexed_time=True)
    assert rr["overview"].loc[0,"status"] == "warn_time_irregularities_detected"
    assert rr["overview"].loc[0,"negative_steps"] == 1
    assert rr["overview"].loc[0,"segment_count"] == 2
    np.testing.assert_allclose(rr["data_with_segments"]["time_reindexed_within_segment"],[0,1,2,0,1,2])

    ties = pd.DataFrame({"CNT":[1,2,2,3],"HR":[70,71,72,73]})
    yes = gp.audit_gazepoint_time_resets(ties,time_col="CNT",allow_ties=True)
    no = gp.audit_gazepoint_time_resets(ties,time_col="CNT",allow_ties=False)
    assert yes["overview"].loc[0,"status"] == "pass" and yes["overview"].loc[0,"duplicate_steps"] == 1
    assert no["overview"].loc[0,"status"] == "warn_time_irregularities_detected" and no["overview"].loc[0,"nonmonotonic_steps"] == 1

    bad = gp.audit_gazepoint_time_resets(pd.DataFrame({"time_label":["a","b","c"],"GSR_US":[1,2,3]}),time_col="time_label")
    assert bad["overview"].loc[0,"status"] == "fail_no_numeric_time"
    assert bad["overview"].loc[0,"nonfinite_time_rows"] == 3


def test_signal_activity_r_fixtures_and_auto_detection():
    dat=pd.DataFrame({"source_file":np.repeat(["inactive.csv","active.csv"],5),"GSR_US":[0]*5+list(np.linspace(1,2,5)),"HR":[0]*5+list(np.linspace(70,75,5))})
    res=gp.audit_gazepoint_signal_activity(dat,signal_cols=["GSR_US","HR"],group_cols="source_file")
    assert res["overview"].loc[0,"status"] == "warn_inactive_groups_detected"
    assert res["overview"].loc[0,"no_active_group_count"] == 1
    assert "inactive.csv" in res["inactive_groups"]["source_file"].tolist()
    assert "inactive_all_zero" in res["signal_by_group"]["status"].tolist()

    const=pd.DataFrame({"participant":np.repeat(["P1","P2"],5),"GSR_US":[1]*5+list(np.linspace(1,2,5)),"HR":[70]*5+list(np.linspace(70,75,5))})
    cr=gp.audit_gazepoint_signal_activity(const,signal_cols=["GSR_US","HR"],group_cols="participant")
    assert set(cr["signal_by_group"].query("participant == 'P1'")["status"]) == {"inactive_constant"}
    assert set(cr["signal_by_group"].query("participant == 'P2'")["status"]) == {"active"}

    low=pd.DataFrame({"source_file":"a.csv","GSR_US":[0,0,1,1,1,1],"HR":[70,71,72,73,74,75]})
    lr=gp.audit_gazepoint_signal_activity(low,signal_cols=["GSR_US","HR"],group_cols="source_file",min_unique_nonzero=2)
    assert ((lr["signal_by_group"]["signal"]=="GSR_US")&(lr["signal_by_group"]["status"]=="low_variation")).any()
    auto=gp.audit_gazepoint_signal_activity(pd.DataFrame({"source_file":"a.csv","GSR_US":np.linspace(1,2,10),"HR":np.linspace(70,80,10),"unrelated":list("abcdefghij")}),group_cols="source_file")
    assert {"GSR_US","HR"}.issubset(auto["settings"]["signal_cols"])
    assert "unrelated" not in auto["settings"]["signal_cols"] and auto["overview"].loc[0,"status"]=="pass"


def test_biometric_dropout_missing_flatline_grouping_and_time_order():
    df=pd.DataFrame({"CNT":range(1,9),"GSR":[1,np.nan,np.nan,np.nan,2,3,4,5],"HR":[70,71,72,73,74,75,76,77]})
    out=gp.flag_gazepoint_biometric_dropouts(df,signal_cols=["GSR","HR"],min_missing_run=3,min_flatline_run=3)
    assert out["biometric_dropout_GSR_missing"].iloc[1:4].all()
    assert not out["biometric_dropout_HR_missing"].any()
    assert out.attrs["dropout_summary"].query("column == 'GSR'")["n_missing_dropout"].iloc[0] == 3

    flat=pd.DataFrame({"CNT":range(1,9),"GSR":range(1,9),"HR":[70,70,70,71,72,72,72,72]})
    fo=gp.flag_gazepoint_biometric_dropouts(flat,signal_cols=["GSR","HR"],min_missing_run=3,min_flatline_run=3)
    assert fo["biometric_dropout_HR_flatline"].iloc[:3].all() and fo["biometric_dropout_HR_flatline"].iloc[4:].all()
    assert fo.attrs["dropout_summary"].query("column == 'HR'")["n_flatline_dropout"].iloc[0] == 7

    grouped=pd.DataFrame({"USER":np.repeat(["P1","P2"],3),"CNT":[1,2,3,1,2,3],"GSR":[1,np.nan,np.nan,2,np.nan,3]})
    go=gp.flag_gazepoint_biometric_dropouts(grouped,signal_cols="GSR",group_cols="USER",min_missing_run=2,min_flatline_run=3)
    assert go["biometric_dropout_GSR_missing"].iloc[1:3].all() and not bool(go["biometric_dropout_GSR_missing"].iloc[4])

    unsorted=pd.DataFrame({"USER":["P1"]*3,"TIME":[3,1,2],"GSR":[np.nan,1,np.nan]})
    uo=gp.flag_gazepoint_biometric_dropouts(unsorted,signal_cols="GSR",group_cols="USER",time_col="TIME",min_missing_run=2,min_flatline_run=3)
    assert bool(uo["biometric_dropout_GSR_missing"].iloc[0]) and bool(uo["biometric_dropout_GSR_missing"].iloc[2]) and not bool(uo["biometric_dropout_GSR_missing"].iloc[1])


def _nonwear_demo():
    return pd.DataFrame({
        "participant":np.repeat(["P01","P02"],20),
        "trial":np.tile(np.repeat([1,2],10),2),
        "time_ms":np.tile(np.arange(0,1000,100),4),
        "pupil":np.r_[np.linspace(3,3.9,10),[np.nan]*10,[2.8]*10,np.linspace(3.1,3.5,10)],
        "gsr":np.r_[np.linspace(.70,.79,10),[0]*10,np.linspace(.80,.89,10),[.75]*5,np.linspace(.76,.80,5)],
    })


def test_nonwear_detection_and_summary_exact_counts():
    out=gp.detect_gazepoint_nonwear(_nonwear_demo(),signal_cols=["pupil","gsr"],group_cols=["participant","trial"],time_col="time_ms",min_run_length=5,low_variance_threshold=.0001)
    assert len(out["summary"]) == 8
    assert {"missing_run","zero_run","constant_run","low_variance_run"}.issubset(set(out["intervals"]["run_type"]))
    pupil_missing=out["intervals"].query("participant == 'P01' and trial == 2 and signal == 'pupil' and run_type == 'missing_run'")
    assert len(pupil_missing)==1 and pupil_missing["n_samples"].iloc[0]==10 and pupil_missing["start_time"].iloc[0]==0 and pupil_missing["end_time"].iloc[0]==900
    summary=gp.summarize_gazepoint_nonwear(out,by="signal")
    assert summary.query("signal == 'pupil'")["n_samples_total"].iloc[0]==40
    assert summary.query("signal == 'gsr'")["n_samples_total"].iloc[0]==40
    assert summary.query("signal == 'pupil'")["n_flagged_samples_total"].iloc[0]==20
    assert summary.query("signal == 'gsr'")["n_flagged_samples_total"].iloc[0]==15

    clean=pd.DataFrame({"time_ms":np.arange(0,1000,100),"signal":np.linspace(1,2,10)})
    no=gp.detect_gazepoint_nonwear(clean,signal_cols="signal",time_col="time_ms",min_run_length=5)
    assert len(no["intervals"])==0 and no["summary"].loc[0,"n_intervals"]==0 and no["summary"].loc[0,"n_flagged_samples"]==0


def test_filter_signal_and_upsample_r_fixtures():
    demo=pd.DataFrame({"participant":np.repeat(["P01","P02"],5),"time_ms":np.tile(np.arange(0,500,100),2),"pupil":[1,2,3,4,5,10,10,10,10,10]})
    out=gp.filter_gazepoint_signal(demo,signal_cols="pupil",method="moving_average",group_cols="participant",time_col="time_ms",window=3,na_rm=False)
    np.testing.assert_allclose(out["pupil_moving_average"].iloc[:5],[1.5,2,3,4,4.5])
    np.testing.assert_allclose(out["pupil_moving_average"].iloc[5:],[10]*5)
    assert len(out.attrs["filter_log"])==2

    one=pd.DataFrame({"participant":["P01"]*5,"time_ms":np.arange(0,500,100),"signal":[1,100,3,4,5]})
    med=gp.filter_gazepoint_signal(one,signal_cols="signal",method="rolling_median",time_col="time_ms",window=3,na_rm=False)
    assert med["signal_rolling_median"].iloc[1]==3
    detr=gp.filter_gazepoint_signal(one,signal_cols="signal",method="detrend",time_col="time_ms")
    assert len(detr["signal_detrend"])==5

    irregular=pd.DataFrame({"participant":["P01"]*3+["P02"]*3,"time_ms":[0,110,250,0,100,310],"pupil":[3,3.1,3.3,2.9,3,3.2],"gsr":[.7,.72,.75,.8,.81,.84]})
    up=gp.upsample_gazepoint_data(irregular,time_col="time_ms",signal_cols=["pupil","gsr"],group_cols="participant",interval=50)
    assert len(up)==13
    np.testing.assert_allclose(up.query("participant == 'P01'")["time_ms"],[0,50,100,150,200,250])
    np.testing.assert_allclose(up.query("participant == 'P02'")["time_ms"],[0,50,100,150,200,250,300])
    log=up.attrs["upsample_log"]
    assert log.query("participant == 'P01'")["n_output_rows"].iloc[0]==6 and log.query("participant == 'P02'")["n_output_rows"].iloc[0]==7


def test_dropout_preprocessing_validation_and_empty_detection():
    demo=pd.DataFrame({"time_ms":range(1,6),"signal":range(1,6),"label":list("abcde")})
    with pytest.raises(ValueError,match="not found"): gp.detect_gazepoint_nonwear(demo,signal_cols="missing")
    with pytest.raises(TypeError,match="numeric"): gp.detect_gazepoint_nonwear(demo,signal_cols="label")
    with pytest.raises(TypeError,match="numeric"): gp.filter_gazepoint_signal(demo,signal_cols="label")
    existing=demo.copy(); existing["signal_moving_average"]=0
    with pytest.raises(ValueError,match="already exists"): gp.filter_gazepoint_signal(existing,signal_cols="signal",method="moving_average")
    with pytest.raises(TypeError,match="numeric"): gp.upsample_gazepoint_data(demo,time_col="label",signal_cols="signal")
    with pytest.raises(TypeError,match="numeric"): gp.upsample_gazepoint_data(demo,time_col="time_ms",signal_cols="label")

    empty=gp.flag_gazepoint_biometric_dropouts(pd.DataFrame({"USER":["P1","P2"]}))
    assert "biometric_dropout_any" in empty and not empty["biometric_dropout_any"].any() and len(empty.attrs["dropout_summary"])==0
    with pytest.raises(ValueError,match="positive integer"): gp.flag_gazepoint_biometric_dropouts(pd.DataFrame({"GSR":[1,2,3]}),min_missing_run=0)
