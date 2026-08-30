from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import deterministic_extensions as de
from gpbiometricspy import endgame_science as es
from gpbiometricspy import pspm_style as ps
from gpbiometricspy import qc_audits_design as qa
from gpbiometricspy import qc_dropouts as qd


def test_deterministic_extensions_deep_remaining(monkeypatch,tmp_path):
    with pytest.raises(TypeError): de._df('x')

    # pick() fallback path for scalar metadata shared across multiple figures.
    f1, f2 = plt.figure(), plt.figure()
    out=de.standardize_gazepoint_plot_contracts([f1,f2],plot_data=pd.DataFrame({'x':[1]}),settings={'a':1},interpretation_notes='n',plot_type='p')
    assert len(out)==2
    plt.close(f1); plt.close(f2)

    auto=pd.DataFrame({'participant':['p','p'],'GSR_US':[1.,2.]})
    z=de.standardize_gazepoint_biometrics_within_unit(auto)
    assert 'GSR_US_z_within' in z
    with pytest.raises(ValueError): de.standardize_gazepoint_biometrics_within_unit(pd.DataFrame({'x':[1,2]}))

    ibi=pd.DataFrame({'participant':['p']*3,'IBI_clean_ms':[800.,810.,820.]})
    rr=de.export_gazepoint_rhrv_input(ibi,output_dir=tmp_path/'rhrv')
    assert not rr['group_summary'].empty

    eda=pd.DataFrame({'participant':['p']*4,'time':[0.,10.,20.,30.],'GSR_US':[1.,2.,3.,4.]})
    nk=de.prepare_gazepoint_neurokit_eda_input(eda,time_col='time',output_dir=tmp_path/'nk')
    assert nk['overview'].iloc[0].files_written==1

    original_find=importlib.util.find_spec
    monkeypatch.setattr(importlib.util,'find_spec',lambda name: None if name=='neurokit2' else original_find(name))
    no=de.run_gazepoint_neurokit_eda_crosscheck(nk,execute=True)
    assert no['overview'].iloc[0].status=='neurokit2_not_available'

    fake=types.ModuleType('neurokit2')
    def good_process(x,sampling_rate): return pd.DataFrame({'EDA_Clean':x}), {'SCR_Peaks':[1]}
    fake.eda_process=good_process
    monkeypatch.setitem(sys.modules,'neurokit2',fake)
    monkeypatch.setattr(importlib.util,'find_spec',lambda name: object() if name=='neurokit2' else original_find(name))
    yes=de.run_gazepoint_neurokit_eda_crosscheck(nk,execute=True,sampling_rate=10)
    assert yes['results'].iloc[0].status=='neurokit_crosscheck_complete'
    def bad_process(x,sampling_rate): raise RuntimeError('boom')
    fake.eda_process=bad_process
    bad=de.run_gazepoint_neurokit_eda_crosscheck(nk,execute=True,sampling_rate=10)
    assert bad['results'].iloc[0].status=='neurokit_crosscheck_failed'

    drift=de.audit_gazepoint_biometric_sync_drift(pd.DataFrame({'a':np.arange(30.),'b':np.arange(30.)}),signal_pairs=[('a','b')],min_complete_pairs=5,max_lag=2)
    assert 'overview' in drift
    with pytest.raises(ValueError): de._resolve_ppg(pd.DataFrame({'x':[1.,2.]}),None)
    ppg=de.prepare_gazepoint_pyppg_input(pd.DataFrame({'PPG':[1.,2.,3.],'time':[0.,20.,40.]}),time_col='time')
    assert np.isfinite(ppg['waveform_table'].time_s).all()

    dec=de.decompose_gazepoint_eda(pd.DataFrame({'GSR_US':[1.,2.,1.,2.,1.]}))
    assert 'eda_phasic' in dec
    events=de.detect_gazepoint_scr_events(pd.DataFrame({'GSR_US':[0.,0.,1.,0.,2.,0.,0.]}),signal_col='GSR_US',threshold=None,min_peak_distance=1,window_size=3)
    assert 'overview' in events


def test_endgame_science_deep_remaining():
    assert np.allclose(es._fill([np.nan,np.nan]),0)
    assert np.allclose(es._fill([np.nan,2,np.nan]),2)
    assert np.isfinite(es._fill([1,np.nan,3])).all()

    art=es.audit_gazepoint_eda_artifacts(pd.DataFrame({'GSR':[1.,2.,3.,4.]}),prefer_gsr_us=False)
    assert art['settings']['signal_col']=='GSR'
    assert len(es._smooth_center([1.,2.,3.,4.,5.],3))==5
    got=es._filter_peaks(np.array([0.,3.,0.,2.,0.]),np.array([1,3]),3)
    assert got.tolist()==[1]

    peaks=es.detect_gazepoint_scr_peaks(pd.DataFrame({'EDA':[0.,1.,0.,2.,1.,.5]}),signal_col='EDA',prefer_vendor_phasic=False,amplitude_min=.1,min_peak_distance=2)
    assert 'peaks' in peaks
    windows=pd.DataFrame({'event_id':['e1','e2'],'response_flag':[1,0],'scr_amplitude':[1.,np.nan],'scr_latency':[1.,np.nan],'scr_rise_time':[.2,np.nan],'scr_recovery_time':[1.,np.nan]})
    non=es.screen_gazepoint_eda_nonresponders({'peaks':pd.DataFrame({'amplitude':[1.]})},min_detected_peaks=2)
    assert non['group_summary'].iloc[0].candidate_nonresponder
    h1=es.prepare_gazepoint_scr_hurdle_model_data(windows,amplitude_transform='log')
    h2=es.prepare_gazepoint_scr_hurdle_model_data(windows,amplitude_transform='log1p')
    assert len(h1['response_model_data'])==2 and len(h2['response_model_data'])==2

    sens=es.run_gazepoint_scr_threshold_sensitivity(pd.DataFrame({'EDA':[0.,1.,0.,2.,0.]}),signal_col='EDA',amplitude_min_values=[.1],min_peak_distance_values=[1],include_event_windows=False,keep_objects=True)
    assert len(sens['objects'])==1
    rcm=es.extract_gazepoint_hrv_rcmse(pd.DataFrame({'IBI':[800.,800.,800.]}),scales=[1,2],min_intervals=2)
    assert (rcm['summary'].status=='insufficient_intervals').all()
    nl=es.test_gazepoint_hrv_nonlinearity(pd.DataFrame({'IBI':np.linspace(750,850,20)}),metric='approximate_entropy',n_surrogates=2,seed=1)
    assert not nl['results'].empty
    resp1=es.extract_gazepoint_respiration_ceemdan(pd.DataFrame({'CNT':np.arange(20.),'sig':np.sin(np.arange(20.))}),signal_col='sig',sampling_rate=1,respiration_band=(.1,.8))
    assert 'summary' in resp1
    resp2=es.extract_gazepoint_respiration_ceemdan(pd.DataFrame({'CNT':[0.,1.],'sig':[1.,2.]}),signal_col='sig')
    assert resp2['summary'].iloc[0].status=='insufficient_signal_or_sampling_rate'


def test_pspm_style_deep_remaining(tmp_path):
    with pytest.raises(ValueError): ps._pick_col(pd.DataFrame({'x':[1]}),['y'],'thing')
    with pytest.raises(TypeError): ps._prepare_time_data('x')
    created,tc=ps._prepare_time_data(pd.DataFrame({'x':[1,2,3]}),sampling_rate_hz=10)
    assert tc=='time_s'
    with pytest.raises(ValueError): ps._prepare_time_data(pd.DataFrame({'x':[1]}),time_col='no')
    assert ps._group_positions(pd.DataFrame({'x':[1]}),None)[0][0]=='all'
    with pytest.raises(ValueError): ps._group_positions(pd.DataFrame({'x':[1]}),'missing')
    assert len(ps._kernel(.1,'canonical'))>0

    markers=pd.DataFrame({'time_s':[0.,1.,2.,3.],'TTL':[0,1,2,0]})
    m=ps.extract_gazepoint_markerinfo_pspm_style(markers,edge='change')
    assert len(m)>=1
    scr=ps.preprocess_gazepoint_scr_pspm_style(pd.DataFrame({'time_s':[0.,.1,.2,.3,.4],'GSR':[1.,2.,1.,2.,1.]}),signal_col='GSR')
    assert 'scr_processed' in scr['signal'].columns

    ev=pd.DataFrame({'onset_time_s':[1.,2.],'condition':['a','b']})
    des=ps.create_gazepoint_pspm_glm_design(ev,np.arange(0,4,.1),include_derivative=True)
    assert isinstance(des,pd.DataFrame) and 'time_s' in des
    data=pd.DataFrame({'time_s':des.time_s,'sig':np.linspace(0,1,len(des))})
    model=ps.fit_gazepoint_convolution_glm(data,des,signal_col='sig',time_col='time_s')
    assert 'coefficients' in model
    out=ps.export_gazepoint_pspm_model_estimates(model,tmp_path/'m.json')
    assert Path(out.iloc[0]['file']).exists()
    out2=ps.export_gazepoint_pspm_model_estimates(model,tmp_path/'m.rds')
    assert Path(out2.iloc[0]['file']).exists()


def test_qc_audits_design_deep_remaining(tmp_path):
    with pytest.raises(TypeError): qa._df('x')
    with pytest.raises(ValueError): qa._df(pd.DataFrame())
    emptylog=pd.DataFrame(columns=['action','correction_note','flag_reason','original_ibi','corrected_ibi'])
    assert qa.summarize_gazepoint_beat_corrections(emptylog).empty
    log=pd.DataFrame({'action':['x'],'correction_note':['masked_flagged_interval'],'flag_reason':['short'],'original_ibi':[1.],'corrected_ibi':[np.nan]})
    s=qa.summarize_gazepoint_beat_corrections(log)
    assert s.iloc[0].segment_id=='all'

    audit=qa.audit_gazepoint_beats(pd.DataFrame({'IBI':[100.,100.,100.]}),ibi_col='IBI')
    corr=qa.correct_gazepoint_beats(audit,action='local_median')
    assert len(corr['correction_log'])>=1

    assert qa._prep_map(None,['a','b'],1)=={'a':1,'b':1}
    assert qa._prep_map({'a':1},['a','b'],1)=={'a':1,'b':1}
    comp=qa.audit_gazepoint_session_comparability(pd.DataFrame({'session':['a','a','b','b'],'x':[1.,2.,100.,101.]}),metric_cols='x',group_cols='session')
    assert 'summary' in comp
    qcov=qa.summarize_gazepoint_qc_overview(pd.DataFrame({'group':['a','a'],'quality_index':[.2,.3],'flag':[True,False]}),group_cols='group',quality_index_col='quality_index',flag_cols='flag')
    assert len(qcov)==1
    ev=qa.audit_gazepoint_event_coverage(pd.DataFrame({'event':['a','b']}),event_col='event',expected_events=['a','b'])
    assert ev['unit_summary'].iloc[0].complete
    design=qa.audit_gazepoint_experiment_design(pd.DataFrame({'participant':['p','p'],'condition':['a','b']}),condition_col='condition')
    for typ in ['condition_counts','participant_trials','warnings']:
        f=qa.plot_gazepoint_design_coverage(design,type=typ); plt.close(f)
    f=qa.plot_gazepoint_design_coverage(ev,type='event_coverage'); plt.close(f)
    with pytest.raises(ValueError): qa.plot_gazepoint_design_coverage(design,type='bad')


def test_qc_dropouts_deep_remaining():
    with pytest.raises(TypeError): qd._check_df('x')
    with pytest.raises(ValueError): qd._resolve_groups(['x'],'missing')
    d=pd.DataFrame({'time':[0.,1.,.5,2.],'sig':[1.,2.,3.,4.]})
    for kw,val in [('allow_ties','x'),('split_on_negative_step','x'),('return_reindexed_time','x')]:
        with pytest.raises(TypeError): qd.audit_gazepoint_time_resets(d,time_col='time',**{kw:val})
    with pytest.raises(ValueError): qd.audit_gazepoint_time_resets(d,time_col='time',min_segment_rows=0)

    with pytest.raises(TypeError): qd.audit_gazepoint_signal_activity(d,signal_cols='sig',zero_is_inactive='x')
    with pytest.raises(ValueError): qd.audit_gazepoint_signal_activity(d,signal_cols='sig',min_unique_nonzero=0)
    with pytest.raises(TypeError): qd.audit_gazepoint_signal_activity(d,signal_cols='sig',missing_as_inactive='x')
    nonnum=qd.audit_gazepoint_signal_activity(pd.DataFrame({'x':['a','b']}),signal_cols='x')
    assert nonnum['signal_by_group'].iloc[0].status=='nonnumeric'
    missing=qd.audit_gazepoint_signal_activity(pd.DataFrame({'x':[np.nan,np.nan]}),signal_cols='x')
    assert missing['signal_by_group'].iloc[0].status=='insufficient_data'

    assert qd._flatline_flags([1.,1.,np.nan],2,0).any()
    assert qd._safe_col('1 a').startswith('X')
    with pytest.raises(ValueError): qd.flag_gazepoint_biometric_dropouts(d,signal_cols='missing')
    with pytest.raises(ValueError): qd.flag_gazepoint_biometric_dropouts(d,signal_cols='sig',constant_tolerance=-1)
    with pytest.raises(ValueError): qd.flag_gazepoint_biometric_dropouts(d,signal_cols='sig',prefix='')
    assert qd._constant_intervals([1.],2,0)==[]

    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame(),['x'])
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),[])
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['missing'])
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['x'],group_cols='g')
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['x'],time_col='t')
    with pytest.raises(TypeError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.],'t':['a']}),['x'],time_col='t')
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['x'],min_run_length=0)
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['x'],zero_tolerance=-1)
    with pytest.raises(ValueError): qd.detect_gazepoint_nonwear(pd.DataFrame({'x':[1.]}),['x'],low_variance_threshold=-1)
    with pytest.raises(TypeError): qd.summarize_gazepoint_nonwear(3)

    nw=qd.detect_gazepoint_nonwear(pd.DataFrame({'g':['a','b'],'x':[0.,0.]}),['x'],group_cols='g',min_run_length=1)
    # Exercise multi-column grouping key normalization.
    multi=nw['summary'].assign(h=['u','v'])
    sm=qd.summarize_gazepoint_nonwear(multi,by=['g','h'])
    assert len(sm)==2
    assert np.isfinite(qd._approx_signal([0,1],[1,2],[.5],'previous')[0])
