from __future__ import annotations

import types
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
from gpbiometricspy import advanced_physiology as ap
from gpbiometricspy import alignment_aoi as aa
from gpbiometricspy import aoi_biometrics as ab
from gpbiometricspy import cluster_permutation as cp
from gpbiometricspy import demo
from gpbiometricspy import deterministic_extensions as de
from gpbiometricspy import endgame_science as es
from gpbiometricspy import event_frontdoor as ef
from gpbiometricspy import frontdoor as fd
from gpbiometricspy import governance_core as gc
from gpbiometricspy import governance_extra as ge
from gpbiometricspy import mne_eeg_lsl as me
from gpbiometricspy import pspm_style as ps
from gpbiometricspy import pupil_gaze as pg
from gpbiometricspy import pupil_qc as pq
from gpbiometricspy import pyhrv_style as ph
from gpbiometricspy import qc_audits_design as qa
from gpbiometricspy import qc_dropouts as qd
from gpbiometricspy import release_profile as rr
from gpbiometricspy import schema_io as sio


def test_placeholder_cluster_schema_release_and_demo(tmp_path, monkeypatch):
    f=gp._placeholder('future_export')
    assert f.__name__=='future_export'
    with pytest.raises(gp.ParityNotImplementedError): f()

    d=pd.DataFrame({'v':[1.,2.,3.,4.],'t':[0.,.1,.2,.3],'c':['A','A','B','B'],'p':['1','1','2','2']})
    with pytest.raises(ValueError): cp.prepare_gazepoint_timecourse_test_data(d,'v','t','c','p',time_bin_width=0)
    b=cp.prepare_gazepoint_timecourse_test_data(d,'v','t','c','p',condition_a='A',condition_b='B',time_bin_width=.1,require_complete=False)
    assert not b.empty
    diag=cp.diagnose_gazepoint_cluster_design(pd.DataFrame({'s':['1','2'],'c':['A','B'],'t':[0,0],'v':[1.,2.]}),'s','c','t','v',design='between',min_subjects=1)
    assert 'supported_by_current_runner' in set(diag['checks']['check'])

    with pytest.raises(ValueError): sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'CNT':[0,1]}),counter_col='missing')
    tb=sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'TIME':[0.,.1,.2],'CNT':[0,1,2]}),time_col='TIME',counter_col='CNT')
    assert tb['overview'].iloc[0].counter_column=='CNT'
    assert sio._schema_group('TTLV_2')=='ttl_validity_flag'
    assert sio._schema_group('SOMETHING_ELSE')=='other'

    pkg=tmp_path/'pkg'; pkg.mkdir(); (pkg/'NAMESPACE').write_text('export(foo_hrv)\nexport(read_data)\n')
    cov=rr.summarize_gazepoint_feature_coverage(pkg)
    assert cov.n_exports.sum()>0
    with pytest.raises(ValueError): rr.plot_gazepoint_export_profile({'files':pd.DataFrame(),'columns':pd.DataFrame()},type='bad')

    noid=tmp_path/'noid.csv'; pd.DataFrame({'x':[1]}).to_csv(noid,index=False)
    yes=tmp_path/'yes.csv'; pd.DataFrame({'participant_id':['wanted'],'x':[2]}).to_csv(yes,index=False)
    monkeypatch.setattr(demo,'kiosk_demo_files',lambda:[noid,yes])
    got=demo.load_kiosk_demo(participants=['wanted'])
    assert len(got)==1


def test_advanced_physiology_final_branches(monkeypatch):
    pulse=np.array([0.,2.,0.,3.,0.,0.,0.,0.,0.,0.,0.,0.])
    labels=np.zeros(len(pulse),dtype=int); labels[[1,3]]=1
    monkeypatch.setattr(ap,'_simple_kmeans_1d',lambda x,k,seed=None:(labels.copy(),np.array([0.,1.])))
    z=ap.extract_gazepoint_beats_kmeans(pd.DataFrame({'CNT':np.arange(len(pulse))*.1,'HRP':pulse}),k=2,min_distance_s=.5)
    assert z['beat_table'].iloc[0].pulse==3

    samples=pd.DataFrame({'EDA':[1.,2.,3.],'sample':[10.,11.,12.]})
    with pytest.raises(ValueError): ap._external_eda(samples,'pspm',eda_col='EDA',time_col='sample',time_unit='samples')
    ext=ap._external_eda(samples,'pspm',eda_col='EDA',time_col='sample',time_unit='samples',sampling_rate=10)
    assert ext['signal_table'].iloc[-1].time_s==pytest.approx(.2)
    with pytest.raises(ValueError): ap.denoise_gazepoint_quantization_noise(pd.DataFrame({'a':[1.],'b':[2.]}),['a','b'],[.1,.2])


def test_alignment_and_aoi_final_branches():
    stream=pd.DataFrame({'time_s':[0.,.5,1.,1.5,2.], 'grp':['a']*5, 'sig':[1.,2.,3.,2.,1.]})
    events=pd.DataFrame({'event_time_s':[1.], 'event_id':['e'], 'grp':['a']})
    out=aa.summarize_gazepoint_eventlocked_multimodal(stream,events,time_col='time_s',group_cols='grp',signal_cols=['sig'])
    assert len(out['summary'])==1
    align={'diagnostics':pd.DataFrame([{'n_event_pairs':3,'residual_sd_s':.01}])}
    dash=aa.create_gazepoint_quality_dashboard(alignment=align)
    assert dash['overview'].iloc[0].n_alignment_pairs==3

    md=pd.DataFrame({'mean_value':[1.,2.], 'aoi_label':['a','b'], 'signal':['x','x'], 'n_rows':['2','3']})
    model=ab.prepare_gazepoint_aoi_biometrics_model_data(md,numeric_cols=['n_rows'])
    assert pd.api.types.is_numeric_dtype(model['model_data']['n_rows'])
    with pytest.raises(TypeError): ab.plot_gazepoint_aoi_biometrics(3)
    line=ab.plot_gazepoint_aoi_biometrics(md,plot_type='line')
    plt.close(line)
    grouped=ab.plot_gazepoint_aoi_biometrics(md.assign(g=['u','v']),group_col='g',plot_type='line')
    plt.close(grouped)


def test_deterministic_and_endgame_final_branches():
    nk=de.prepare_gazepoint_neurokit_eda_input(pd.DataFrame({'GSR_US':[1.,2.,3.]}))
    assert nk['eda_table'].time_s.isna().all()
    ev=de.detect_gazepoint_scr_events(pd.DataFrame({'EDA':[0.,2.,0.,3.,0.]}),phasic_col='EDA',threshold=1,min_peak_distance=4)
    assert ev['events'].iloc[0].peak_value==3
    txt=de.create_gazepoint_biometrics_methods_text(data=pd.DataFrame({'GSR_US':[1.,2.]}))
    assert isinstance(txt,str) and 'GSR/EDA' in txt

    pk=es.detect_gazepoint_scr_peaks(pd.DataFrame({'EDA':[0.,1.,0.,2.,0.]}),prefer_vendor_phasic=False,amplitude_min=.01)
    assert pk['overview'].iloc[0].source_signal=='EDA'
    basepeaks=pd.DataFrame({'peak_time':[1.], 'onset_time':[.8], 'amplitude':[1.], 'rise_time':[.2], 'recovery_time_after_peak':[1.], 'status':['ok']})
    with pytest.raises(ValueError): es.summarise_gazepoint_scr_event_windows(scr_peaks=basepeaks,events=pd.DataFrame({'event_time':[1.]}),collapse_simultaneous_events='x')
    w=es.summarise_gazepoint_scr_event_windows(scr_peaks=basepeaks,events=pd.DataFrame({'event_time':[1.]}),analysis_window=(0,2),response_window=(0,2))
    assert w['events'].iloc[0].event_group_id=='all'
    empty=es.summarise_gazepoint_scr_event_windows(scr_peaks=basepeaks,events=pd.DataFrame(columns=['event_time']))
    assert empty['overview'].iloc[0].status=='fail_no_events'
    h=es.prepare_gazepoint_scr_hurdle_model_data(pd.DataFrame({'response_flag':[1],'scr_amplitude':[2.]}),amplitude_transform='none')
    assert h['amplitude_model_data'].iloc[0].scr_amplitude_model==2
    sens=es.run_gazepoint_scr_threshold_sensitivity(pd.DataFrame({'EDA':[0.,1.,0.,2.,0.]}),signal_col='EDA',amplitude_min_values=[.1],min_peak_distance_values=[1],events=pd.DataFrame({'event_time':[1.]}),event_time_col='event_time',analysis_window=(0,2),response_window=(0,2),include_event_windows=True)
    assert len(sens['event_window_summary'])>=0
    nl=es.test_gazepoint_hrv_nonlinearity(pd.DataFrame({'IBI':np.linspace(700,900,30)}),metric='sd1_sd2',n_surrogates=1,seed=1)
    assert len(nl['results'])==1


def test_event_frontdoor_and_frontdoor_final_branches(tmp_path):
    far=ef.epoch_gazepoint_scr(pd.DataFrame({'time_s':[0.,1.],'EDA':[1.,2.]}),pd.DataFrame({'event_time':[10.]}),pre=1,post=1,time_col='time_s',signal_col='EDA')
    assert far.iloc[0].n_samples==0
    flags=ef.flag_gazepoint_rr_outliers([1000.,1000.,1000.],method='z',return_='flags')
    assert not flags.any()
    same=ef.compute_gazepoint_engagement_index([1.,2.],time=[0.,0.])
    assert np.isnan(same.iloc[0].auc_engagement)
    one=ef.compute_gazepoint_engagement_index([2.],time=[0.])
    assert one.iloc[0].auc_engagement==0
    det=ef.detrend_gazepoint_signal(pd.DataFrame({'time':[0.,1.,2.],'x':[1.,2.,3.]}),time_col='time')
    assert 'x_detrended' in det

    (tmp_path/'random.csv').write_text('x\n1\n')
    with pytest.raises(ValueError): fd.import_gazepoint_biometric_folder(tmp_path,include_fixations=False,include_all_gaze=False,include_other_csv=False)
    empty=pd.DataFrame(columns=['CNT','GSR_US'])
    v=fd.validate_gazepoint_biometrics(empty)
    assert 'empty_data' in set(v['issues']['issue'])
    weird=pd.DataFrame([[0,1]],columns=['CNT',''])
    v2=fd.validate_gazepoint_biometrics(weird)
    assert 'empty_column_names' in set(v2['issues']['issue'])
    m=fd.audit_gazepoint_biometric_missingness(pd.DataFrame({'CNT':[0.,1.],'GSR_US':[1.,np.nan]}),columns='GSR_US')
    assert len(m)==1


def test_governance_mne_pspm_pupil_qc_and_maps(tmp_path, monkeypatch):
    assert gc._audit_rows(3,'x')==[]
    one=gc.create_gazepoint_audit_index({'checks':pd.DataFrame([{'status':'ok'}])},audit_ids=['named'])
    assert one.iloc[0].audit_id=='named'
    with pytest.raises(TypeError): gc.create_gazepoint_audit_index(3)
    f=tmp_path/'single.csv'; f.write_text('x\n1\n')
    inv=gc.summarize_gazepoint_export_inventory(f)
    assert len(inv)==1

    checklist=pd.DataFrame([{'required':False,'evidence_key':'opt','required_fields':'','item_id':'x','domain':'d'}])
    pr=ge.audit_gazepoint_preregistration_consistency(checklist=checklist,evidence={})
    assert pr['item_results'].iloc[0].audit_status=='missing_optional'

    markers=pd.DataFrame({'time_s':[0.,1.,2.],'M':[0,2,3]})
    mevents=me.prepare_gazepoint_mne_events(markers,event_time_col='time_s',marker_cols='M',marker_onset='nonzero',sampling_rate_hz=10)
    assert len(mevents['events'])==2
    gpdat=pd.DataFrame({'time_s':[0.,1.,2.]})
    gpev=pd.DataFrame({'event_time_s':[0.,1.]})
    eev=pd.DataFrame({'event_time_s':[.1,1.1]})
    al=me.align_gazepoint_to_eeg(gpdat,gpev,eev,match_by='row')
    assert al['audit']['n_matched_events']==2

    nonzero=ps.extract_gazepoint_markerinfo_pspm_style(pd.DataFrame({'time_s':[0.,1.],'TTL':[0,1]}),edge='nonzero')
    assert len(nonzero)==1
    design=ps.create_gazepoint_pspm_glm_design(pd.DataFrame({'onset_time_s':[.2]}),pd.DataFrame({'time_s':np.arange(0,1,.1)}),time_col='time_s')
    data=pd.DataFrame({'time_s':[0.,.4,.9],'sig':[0.,1.,0.]})
    fit=ps.fit_gazepoint_convolution_glm(data,design,signal_col='sig',time_col='time_s')
    assert len(fit['predictions'])==len(design)

    df=pd.DataFrame({'LPD':[3.,3.],'RPD':[3.,3.]})
    with pytest.raises(TypeError): pg.detect_gazepoint_pupil_blinks(df,return_='flags',**{'return':'onsets'})
    assert pg.detect_gazepoint_pupil_blinks(df,**{'return':'flags'}).shape==(2,)
    no=pg.detect_gazepoint_pupil_blinks(df)
    assert no.empty
    clean=pg.clean_gazepoint_pupil_signal(pd.DataFrame({'LPD':[3.,3.,3.],'RPD':[3.,3.,3.]}))
    assert 'LPD_clean' in clean
    with pytest.raises(ValueError): pq.detect_gazepoint_blinks(pd.DataFrame({'left_pupil':[1.,2.]}),change_threshold=-1)

    def bad_lstsq(*args,**kwargs): raise np.linalg.LinAlgError('forced')
    monkeypatch.setattr(ph.np.linalg,'lstsq',bad_lstsq)
    assert ph._ar_psd(np.arange(20,dtype=float),4,order=1).empty

    assert qa._prep_map(2,['a','b'],1)=={'a':2,'b':2}
    assert qa._prep_map([2],['a','b'],1)=={'a':2,'b':2}
    assert qa._prep_map([2,3],['a','b'],1)=={'a':2,'b':3}
    with pytest.raises(ValueError): qa._prep_map([1,2,3],['a','b'],1)
    comp=qa.audit_gazepoint_session_comparability(pd.DataFrame({'x':[1.,2.,3.]}),metric_cols='x')
    assert 'segment_id' in comp['data']
    q=qa.summarize_gazepoint_qc_overview(pd.DataFrame({'x':[1.,2.]}))
    assert q.n_flagged_rows.isna().all()

    base=pd.DataFrame({'signal':['a'],'n_samples':[1],'n_intervals':[0],'n_flagged_samples':[0],'n_missing_run':[0],'n_zero_run':[0],'n_constant_run':[0],'n_low_variance_run':[0],'g':['x'],'h':['y']})
    sm=qd.summarize_gazepoint_nonwear(base,by=['g','h'])
    assert len(sm)==1
