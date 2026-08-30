from __future__ import annotations

import sys
import types
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import advanced_physiology as ap
from gpbiometricspy import alignment_aoi as aa
from gpbiometricspy import aoi_biometrics as ab
from gpbiometricspy import cluster_permutation as cp
from gpbiometricspy import compatibility as co
from gpbiometricspy import demo
from gpbiometricspy import mne_eeg_lsl as me
from gpbiometricspy import physiology_qc as pq
from gpbiometricspy import pyhrv_style as ph
from gpbiometricspy import release_profile as rr
from gpbiometricspy import reports as rp
from gpbiometricspy import schema_io as sio
from gpbiometricspy import scientific_qc as sq
from gpbiometricspy import pupil_gaze as pg
from gpbiometricspy import governance_core as gc
from gpbiometricspy import governance_extra as ge
from gpbiometricspy import event_frontdoor as ef
from gpbiometricspy import frontdoor as fd


def test_advanced_physiology_remaining_paths():
    tiny=pd.DataFrame({'GSR_US':[1.,2.,3.], 'temp':[20.,21.,22.]})
    out=ap.correct_gazepoint_eda_temperature(tiny,temperature_cols='temp')
    assert out.attrs['eda_temperature_model_summary'].iloc[0].status=='insufficient_complete_cases'

    t=np.arange(12,dtype=float)*.1
    const=pd.DataFrame({'CNT':t,'HRP':np.ones(12)})
    z=ap.extract_gazepoint_beats_kmeans(const,k=2)
    assert z['summary'].iloc[0].status=='insufficient_pulse_variability'
    # Force closely spaced local maxima so refractory replacement executes.
    pulse=np.array([0,1,4,5,0,0,0,0,0,0,0,0],float)
    z=ap.extract_gazepoint_beats_kmeans(pd.DataFrame({'CNT':t,'HRP':pulse}),k=2,min_distance_s=.5,seed=1)
    assert isinstance(z['beat_table'],pd.DataFrame)

    ip=ap.model_gazepoint_hrv_ipfm(pd.DataFrame({'beat':[0.,1.,2.,3.,4.,5.]}),ibi_col=None,beat_time_col='beat',output_sampling_rate=2)
    assert 'overview' in ip

    for bad in [None, {'x':1}]:
        with pytest.raises((TypeError,ValueError)):
            ap._extract_df(bad)
    assert ap._extract_df({'data':pd.DataFrame({'x':[1]})}).shape==(1,1)
    with pytest.raises(ValueError): ap._external_eda({'data':pd.DataFrame({'EDA':[1.,2.]})},'cvxeda')
    ext=ap._external_eda({'data':pd.DataFrame({'EDA':[1.,2.]})},'cvxeda',sampling_rate=10)
    assert 'overview' in ext

    with pytest.raises(ValueError): ap.denoise_gazepoint_quantization_noise(pd.DataFrame({'GSR_US':[1.,2.]}),signal_cols='GSR_US',resolution='bad')
    scalar=ap.denoise_gazepoint_quantization_noise(pd.DataFrame({'GSR_US':[1.,1.1,1.2]}),signal_cols='GSR_US',resolution=.1)
    assert len(scalar)==3
    mapping=ap.denoise_gazepoint_quantization_noise(pd.DataFrame({'GSR_US':[1.,1.1,1.2]}),signal_cols='GSR_US',resolution={'GSR_US':.1})
    assert len(mapping)==3

    skin=ap.analyze_gazepoint_skin_potential(pd.DataFrame({'time':[0.,1.,2.,3.,4.],'skin_potential':[1.,1.,1.,2.,3.]}),sp_col='skin_potential',time_col='time',response_threshold=None)
    assert 'overview' in skin


def test_alignment_and_aoi_remaining_paths(tmp_path):
    with pytest.raises(TypeError): aa._check_df('x')
    with pytest.raises(ValueError): aa._check_df(pd.DataFrame())
    dat=pd.DataFrame({'time':[0.,.1,.2], 'AOI':['a','a','b'], 'valid':[True,False,True]})
    tc=aa.build_gazepoint_aoi_timecourse(dat,time_col='time',aoi_col='AOI',valid_col='valid')
    assert not tc.empty
    dat2=dat.assign(valid=[1,0,1])
    tc2=aa.build_gazepoint_aoi_timecourse(dat2,time_col='time',aoi_col='AOI',valid_col='valid')
    assert not tc2.empty
    s=aa._signal_summary([0,1],[np.nan,np.nan],(-1,0),(0,1))
    assert np.isnan(s['peak_latency_s'])
    # Dashboard warning/manifest paths.
    dash=aa.create_gazepoint_quality_dashboard(pd.DataFrame({'participant':['p'], 'prop_missing':[.1]}), output_dir=tmp_path)
    assert isinstance(dash,dict)

    df=pd.DataFrame({'AOI':['a','b'],'metric':[1.,2.]})
    assert ab._extract_summary({'summary':df}).equals(df)
    assert ab._extract_summary(df).equals(df)
    with pytest.raises(TypeError): ab._extract_summary(1)
    std=ab._standardise(pd.Series([1.,1.]))
    assert np.allclose(std,0)
    summary=pd.DataFrame({'aoi_label':['a','b'],'signal':['GSR','GSR'],'mean_value':[1.,2.]})
    prep=ab.prepare_gazepoint_aoi_biometrics_model_data(summary)
    assert not prep['model_data'].empty
    fig=ab.plot_gazepoint_aoi_biometrics(prep); plt.close(fig)


def test_cluster_compatibility_and_demo_paths(tmp_path):
    with pytest.raises(TypeError): cp.prepare_gazepoint_timecourse_test_data('bad')
    with pytest.raises(ValueError): cp.prepare_gazepoint_timecourse_test_data(pd.DataFrame({'time':[1]}),outcome_col='missing',time_col='time',condition_col='condition',participant_col='participant')
    diag=cp.diagnose_gazepoint_cluster_design(pd.DataFrame({'participant':['p1'],'condition':['a'],'time':[0.],'value':[1.]}),subject='participant',condition='condition',time='time',value='value')
    assert 'checks' in diag
    rep=cp.report_gazepoint_cluster_permutation({'clusters':pd.DataFrame()})
    assert rep is not None

    d={'a':pd.DataFrame({'GSR':[1]}),'b':pd.DataFrame({'HR':[60]})}
    std=co.standardize_gazepoint_column_names(d)
    assert isinstance(std,dict) and set(std)=={'a','b'}
    x=np.array([1.,np.nan,3.]); t=np.arange(3.)
    assert np.isfinite(co._interpolate_one(x,t,None,np.inf,'constant')[0][1])
    pupil=pd.DataFrame({'LPD':[1.,np.nan,2.]})
    y=co.interpolate_gazepoint_pupil_blinks(pupil,pupil_cols='LPD',method='linear')
    assert 'LPD' in y
    mix=co.prepare_gazepoint_mixed_model_data(pd.DataFrame({'participant':['a','b'],'outcome':['1',None]}),outcome_cols='outcome',participant_col='participant')
    assert len(mix)==1

    # Demo participants filtering and design generation.
    dd=demo.load_kiosk_demo(participants=['synthetic_kiosk_p001'])
    assert dd['participant_id'].nunique()==1
    empty=demo.load_kiosk_demo(participants=['does-not-exist'])
    assert empty.empty
    design=demo.kiosk_demo_trial_design()
    assert not design.empty


def test_mne_eeg_lsl_remaining_paths(monkeypatch,tmp_path):
    with pytest.raises(ValueError): me._time_unit([1,2],unit='hours')
    labels=['a','b']
    assert me._event_id(labels,pd.Series({'a':4,'b':5}))=={'a':4,'b':5}
    tab=pd.DataFrame({'event_label':['a','b'],'event_code':[8,9]})
    assert me._event_id(labels,tab)=={'a':8,'b':9}
    with pytest.raises(TypeError): me._event_id(labels,['x'])

    v=me.prepare_gazepoint_mne_events([0.,1.],sampling_rate_hz=100)
    assert v['events'].shape==(2,3)
    markers=pd.DataFrame({'TIME':[0.,1.,2.],'TTL1':[0,1,1]})
    mm=me.prepare_gazepoint_mne_events(markers,event_time_col='TIME',marker_cols='TTL1',sampling_rate_hz=10,marker_onset='change')
    assert len(mm['events'])==1
    with pytest.raises(TypeError): me.prepare_gazepoint_mne_events('bad',sampling_rate_hz=10)

    no_time=pd.DataFrame({'GSR':[1.,2.,3.]})
    mi=me.prepare_gazepoint_mne_input(no_time,channel_cols='GSR',sampling_rate_hz=10)
    assert mi['data'].shape==(1,3)
    one=me.prepare_gazepoint_mne_input(pd.DataFrame({'TIME':[0.],'GSR':[1.]}),channel_cols='GSR',sampling_rate_hz=10)
    assert one['sampling']['irregular_interval_count']==0

    assert me._infer_time(pd.DataFrame({'x':[1,2]}),None,['x'],unit='samples',fs=20)[0].shape==(2,)
    with pytest.raises(ValueError): me._infer_time(pd.DataFrame({'x':[1,2]}),None,['missing'])
    gp=pd.DataFrame({'time_s':[0.,1.,2.],'GSR':[1.,2.,3.]})
    gevents=pd.DataFrame({'event_time_s':[0.,1.],'event_id':['a','b']})
    eevents=pd.DataFrame({'event_time_s':[10.,11.],'event_id':['a','b']})
    aligned=me.align_gazepoint_to_eeg(gp,gevents,eevents,gazepoint_time_col='time_s')
    assert 'time_eeg_s' in aligned['data']

    with pytest.raises(TypeError): me._stream_df(3,'bad')
    sf=me._stream_df({'time_stamps':[1.,2.],'time_series':[[3.],[4.]],'info':{'name':['x']}},'x')
    assert len(sf)==2
    # Relative global/none and nearest merge branches.
    streams={'a':pd.DataFrame({'time_s':[1.,2.],'x':[1.,2.]}),'b':pd.DataFrame({'time_s':[1.1,2.1],'y':[3.,4.]})}
    synced=me.sync_gazepoint_signals_via_lsl(streams,reference='a',relative_zero='global',merge='nearest')
    assert synced['merged'] is not None
    synced2=me.sync_gazepoint_signals_via_lsl(streams,reference='a',relative_zero='none')
    assert synced2['streams']['a']['.lsl_time_relative_s'].iloc[0]==1.0


def test_physiology_qc_remaining_paths():
    ev=pq._event_table([1.,2.]); assert list(ev.event_id)==['E1','E2']
    d=pd.DataFrame({'time':[0.,1.,2.,3.], 'GSR_US':[1.,1.,1.,1.], 'group':['a']*4})
    e=pd.DataFrame({'event_time':[1.], 'event_id':['x'], 'group':['a']})
    out=pq.compute_gazepoint_scr_latency(d,e,time_col='time',eda_col='GSR_US',event_time_col='event_time',group_cols='group',baseline_window_s=(-2,0),response_window_s=(10,11))
    assert not out.response_detected.iloc[0]
    short=pq.estimate_gazepoint_respiration_from_ppg([1.,2.,3.],sampling_rate_hz=10)
    assert np.isnan(short['summary'].iloc[0].respiration_rate_bpm)
    tiny=pq.estimate_gazepoint_respiration_from_ppg(pd.DataFrame({'PPG':[1.,2.,3.,4.]}),ppg_col='PPG',sampling_rate_hz=10)
    assert 'summary' in tiny
    noband=pq.estimate_gazepoint_respiration_from_ppg(np.sin(np.linspace(0,4*np.pi,100)),sampling_rate_hz=10,respiratory_band_hz=(20,30))
    assert np.isnan(noband['summary'].iloc[0].respiration_frequency_hz)


def test_pyhrv_and_release_profile_remaining(monkeypatch,tmp_path):
    nni=np.array([800.,810.,790.,805.,795.,815.,785.,800.,810.,790.,805.,795.,815.,785.,800.,810.,790.,805.,795.,815.])
    # AR branch can fail gracefully if optional statsmodels path is unavailable; inject a small fake result.
    class FakeAR:
        sigma2=1.0
        arparams=np.array([.2])
    class FakeAutoReg:
        def __init__(self,*a,**k): pass
        def fit(self): return FakeAR()
    fake_ar=types.ModuleType('statsmodels.tsa.ar_model'); fake_ar.AutoReg=FakeAutoReg
    monkeypatch.setitem(sys.modules,'statsmodels.tsa.ar_model',fake_ar)
    fr=ph.compute_gazepoint_pyhrv_frequency_domain(nni,method='ar')
    assert 'measures' in fr
    with pytest.raises(ValueError): ph.compute_gazepoint_pyhrv_frequency_domain(nni,method='bad')
    cmp=ph.compare_gazepoint_pyhrv_psd_methods(nni,plot=True); plt.close('all'); assert not cmp['measures'].empty
    wf=ph.compute_gazepoint_pyhrv_psd_waterfall(np.tile(nni,5),segment_seconds=5,plot=True); plt.close('all'); assert not wf['psd'].empty
    pc=ph.compute_gazepoint_pyhrv_poincare(nni,plot=True); plt.close('all'); assert np.isfinite(pc.iloc[0].sd1)
    for measures in [pd.Series({'sdnn':1.,'rmssd':2.}), {'sdnn':1.,'rmssd':2.}]:
        f=ph.plot_gazepoint_pyhrv_radar_chart(measures,columns=('sdnn','rmssd')); plt.close(f)
    with pytest.raises(TypeError): ph.plot_gazepoint_pyhrv_radar_chart([1,2])
    peaks=pd.DataFrame({'peak_time_s':[0.,.8,1.6,2.4,3.2,4.]})
    run=ph.run_gazepoint_pyhrv_style(peaks=peaks)
    assert 'time_domain' in run

    assert rr._role('not_a_signal')=='other'
    folder=tmp_path/'profile'; folder.mkdir()
    (folder/'bad.csv').write_text('"unterminated\n',encoding='utf-8')
    p=rr.profile_gazepoint_export_folder(folder)
    assert p['overview'].iloc[0].n_read_errors==1
    f=rr.plot_gazepoint_export_profile(p,type='files'); plt.close(f)
    with pytest.raises(ValueError): rr.plot_gazepoint_export_profile(p,top_n=0)


def test_small_remaining_branches_after_sweep_a(tmp_path):
    assert pg._guess_pupil_cols(pd.DataFrame({'foo_pupil':[1.,2.]}))==['foo_pupil']
    with pytest.raises(ValueError): pg.detect_gazepoint_pupil_blinks(pd.DataFrame({'LPD':[1.]}),return_=1)
    with pytest.raises(ValueError): pg.clean_gazepoint_pupil_signal(pd.DataFrame({'LPD':[1.]}),pupil_cols='LPD',time_col='missing')
    with pytest.raises(TypeError): pg.detect_gazepoint_pupil_blinks(pd.DataFrame({'LPD':[1.]}),return_='data',return_type='flags')

    assert rp._warning_lines('x')==['x']
    assert rp._collect_warnings(a={'warnings':'w'})==['a: w']
    txt=rp.create_gazepoint_methods_section(export_profile={'overview':pd.DataFrame([{'n_files':1}])})
    assert txt is not None
    txt=rp.create_gazepoint_audit_report_section(export_profile={'overview':pd.DataFrame([{'n_files':1}]),'warnings':['w']})
    assert txt is not None

    # Unique name collision and tick/counter timebase branches.
    assert sio._make_unique(['a','a_1','a'])==['a','a_1','a_2']
    with pytest.raises(ValueError): sio.standardise_gazepoint_biometric_names(pd.DataFrame({'x':[1]}),style='bad')
    tick=sio.detect_gazepoint_time_columns(pd.DataFrame({'TIME_TICK':[0,10]})); assert len(tick)==1 and tick.iloc[0].standard_name=='TIME_TICK'
    counter=sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'CNT':[1,2,3]}),time_col='CNT')
    assert counter['overview'].iloc[0].unit in {'samples','seconds','milliseconds'}

    tonic=sq.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({'GSR_US':[1.,1.,1.,2.,1.,1.]}),window_n=3)
    assert 'summary' in tonic

    # Remaining governance paths.
    assert gc.create_gazepoint_audit_index(audits={}).empty
    with pytest.raises(ValueError): gc.summarize_gazepoint_export_inventory(tmp_path/'missing')
    assert ge._evidence_info(3)[2] is True
    with pytest.raises(ValueError): ge.audit_gazepoint_preregistration_consistency(pd.DataFrame())
    # front/event strict validation branches
    with pytest.raises(TypeError): fd.check_gazepoint_biometric_columns('x')
    with pytest.raises(TypeError): fd.detect_active_biometric_channels('x')
    with pytest.raises(ValueError): fd.import_gazepoint_biometric_folder('')
    with pytest.raises(ValueError): ef.epoch_gazepoint_scr(pd.DataFrame({'TIME':[0.],'GSR_US':[1.]}),[],pre=-1,post=1,time_col='TIME',signal_col='GSR_US')
