from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
import gpbiometricspy.final_science_bridges as fsb
import gpbiometricspy.frontdoor as frontdoor
import gpbiometricspy.advanced_physiology as ap
import gpbiometricspy.deterministic_extensions as de


def test_final_science_private_and_ac_edges():
    with pytest.raises(TypeError): fsb._df([1])
    with pytest.raises(ValueError, match="group_cols"): fsb._groups(pd.DataFrame({"x":[1]}), ["g"])
    g=fsb._groups(pd.DataFrame({"x":[1,2]})); assert g[0][0]=="all_rows"
    assert np.isnan(fsb._sampling_rate([1,2]))
    assert np.isnan(fsb._sampling_rate([3,2,1]))
    with pytest.raises(ValueError, match="at least one"):
        gp.analyze_gazepoint_ac_susceptance(pd.DataFrame({"x":[1]}))
    with pytest.raises(ValueError, match="Missing required"):
        gp.analyze_gazepoint_ac_susceptance(pd.DataFrame({"x":[1]}), conductance_col="g")
    with pytest.raises(TypeError, match="not numeric"):
        gp.analyze_gazepoint_ac_susceptance(pd.DataFrame({"g":["x"]}), conductance_col="g")


def test_statistics_causality_and_bootstrap_remaining_modes():
    small=pd.DataFrame({"g":["a","b"],"y":[1.,2.]})
    out=gp.run_gazepoint_automated_statistics(small,["y"],"g",min_group_n=2)
    assert out["test_table"].iloc[0].status=="insufficient_group_data"
    caus=gp.analyze_gazepoint_cardiorespiratory_causality(pd.DataFrame({"r":[1,2,3],"c":[1,2,3]}),"r","c",min_rows=10)
    assert caus["causality_summary"].iloc[0].status=="insufficient_rows"

    # participant means without pairing hits the unpaired participant branch.
    dat=pd.DataFrame({"p":np.repeat(["p1","p2","p3"],2),"c":np.tile(["a","b"],3),"y":[1,2,2,4,3,6],"block":[1,1,2,2,3,3]})
    u=gp.compare_gazepoint_conditions_bootstrap(dat,"y","c",participant_col="p",condition_levels=["a","b"],paired=False,n_boot=5,seed=1,statistic="standardized_mean_difference")
    assert np.isfinite(u.iloc[0].estimate)
    p=gp.compare_gazepoint_conditions_bootstrap(dat,"y","c",participant_col="p",condition_levels=["a","b"],paired=True,n_boot=5,seed=2,statistic="standardized_mean_difference")
    assert np.isfinite(p.iloc[0].estimate)
    # one grouping column makes pandas yield a scalar key; code coerces it to tuple.
    b=gp.compare_gazepoint_conditions_bootstrap(dat,"y","c",condition_levels=["a","b"],by_cols="block",n_boot=3,seed=3)
    assert "block" in b


def test_pipeline_path_bridges_success_error_and_rethrow(monkeypatch):
    dat=pd.DataFrame({"CNT":np.arange(30),"GSR_US":1+np.sin(np.arange(30)/3)})
    monkeypatch.setattr(frontdoor,"import_gazepoint_biometrics",lambda path:dat.copy())
    with pytest.raises(ValueError,match="Supply `data` or `path`"): gp.run_gazepoint_eda_analysis_pipeline()

    # Make all external bridges cheap deterministic fakes; one raises to cover continue-on-error.
    monkeypatch.setattr(ap,"prepare_gazepoint_cvxeda_input",lambda *a,**k:{"ok":"cvx"})
    monkeypatch.setattr(ap,"prepare_gazepoint_ledalab_input",lambda *a,**k:(_ for _ in ()).throw(RuntimeError("ledalab fail")))
    monkeypatch.setattr(ap,"prepare_gazepoint_pspm_input",lambda *a,**k:{"ok":"pspm"})
    monkeypatch.setattr(de,"prepare_gazepoint_neurokit_eda_input",lambda *a,**k:{"ok":"nk"})
    run=gp.run_gazepoint_eda_analysis_pipeline(path="dummy",prepare_external_bridges=True,bridge_methods=["cvxeda","ledalab","pspm","neurokit","unknown"],continue_on_error=True)
    br=run["phases"]["phase_3_external_bridges"]
    assert br["cvxeda"]["ok"]=="cvx" and "error" in br["ledalab"] and "unknown" not in br
    with pytest.raises(RuntimeError,match="ledalab fail"):
        gp.run_gazepoint_eda_analysis_pipeline(data=dat,prepare_external_bridges=True,bridge_methods=["ledalab"],continue_on_error=False)


def test_xdf_direct_import_module_paths(monkeypatch,tmp_path):
    p=tmp_path/"x.xdf"; p.write_bytes(b"xdf")
    def fail(name): raise ModuleNotFoundError(name)
    monkeypatch.setattr(fsb.importlib,"import_module",fail)
    with pytest.raises(ImportError,match="required to read XDF"):
        gp.import_gazepoint_lsl_xdf(p,pyxdf_module="missing_pyxdf")

    streams=[
        {"info":{"name":["Gazepoint Gaze"]},"time_stamps":[1.,2.],"time_series":[10.,20.]},
        {"info":{"name":"Other"},"time_stamps":[3.],"time_series":[[1,2]]},
    ]
    fake=SimpleNamespace(load_xdf=lambda path:(streams,{"header":"ok"}))
    monkeypatch.setattr(fsb.importlib,"import_module",lambda name:fake)
    one=gp.import_gazepoint_lsl_xdf(p,include_all_streams=False,flatten=True)
    assert one["overview"].iloc[0].selected_stream_count==1 and len(one["data"])==2
    all_=gp.import_gazepoint_lsl_xdf(p,include_all_streams=True,flatten=True)
    assert all_["overview"].iloc[0].selected_stream_count==2 and {"value_1","value_2"}.issubset(all_["data"].columns)
