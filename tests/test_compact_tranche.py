import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.figure
import pytest

import gpbiometricspy as gp


def test_contract_and_pending():
    assert len(gp.R_EXPORTS) == 406
    assert len(gp.IMPLEMENTED_EXPORTS) == 406
    assert gp.PENDING_EXPORTS == []
    assert set(gp.IMPLEMENTED_EXPORTS) == set(gp.R_EXPORTS)
    assert len(set(gp.IMPLEMENTED_EXPORTS)) == 406


def test_detect_blinks_r_fixture():
    d=pd.DataFrame({'participant':['P01']*8,'time':range(1,9),'pupil_left':[3.1,3.2,0,3.2,8.5,3.1,np.nan,3.0]})
    x=gp.detect_gazepoint_blinks(d,pupil_cols='pupil_left',id_cols='participant',min_pupil=0,max_pupil=8,mask=True)
    assert x['summary'].iloc[0].n_flagged==3
    assert x['data']['pupil_left_blink_flag'].tolist()==[False,False,True,False,True,False,True,False]
    assert x['data'].loc[[2,4,6],'pupil_left_blink_clean'].isna().all()


def test_detect_blinks_change_and_extend():
    d=pd.DataFrame({'participant':['P01']*5+['P02']*5,'time':list(range(1,6))*2,'pupil_left':[3,3.1,6.5,3.2,3.1,3,3.1,3.2,3.3,3.4]})
    x=gp.detect_gazepoint_blinks(d,pupil_cols='pupil_left',id_cols='participant',max_pupil=np.inf,change_threshold=2,extend_samples=1,mask=False)
    assert x['data'].loc[1:3,'pupil_left_blink_flag'].all()
    assert not x['data'].loc[5:9,'pupil_left_blink_flag'].any()


def test_smooth_pupil_r_fixtures():
    d=pd.DataFrame({'participant':['P01']*5,'pupil_left':[1,2,3,4,5]})
    x=gp.smooth_gazepoint_pupil(d,pupil_cols='pupil_left',id_cols='participant',window=3)
    np.testing.assert_allclose(x['data']['pupil_left_smooth'],[1.5,2,3,4,4.5])
    d2=pd.DataFrame({'participant':['P01','P01','P02','P02'],'pupil_left':[1,3,10,20]})
    x2=gp.smooth_gazepoint_pupil(d2,pupil_cols='pupil_left',id_cols='participant',window=3)
    np.testing.assert_allclose(x2['data']['pupil_left_smooth'],[2,2,15,15])
    with pytest.raises(ValueError): gp.smooth_gazepoint_pupil(d,pupil_cols='pupil_left',window=2)


def test_metadata_validation_fixtures():
    clean=pd.DataFrame({'participant':['P01','P01','P02','P02'],'trial':[1,2,1,2],'time':[1,2,1,2],'pupil_left':[3.1,3.2,3,3.1]})
    x=gp.validate_gazepoint_metadata(clean,required_cols=['participant','trial','time'],expected_cols=['pupil_left'],id_cols='participant',time_col='time',unique_cols=['participant','trial'])
    assert x['status']=='pass' and x['summary'].iloc[0].n_rows==4
    bad=pd.DataFrame({'participant':['P01','P01','','P02'],'trial':[1,1,1,2],'time':[1,0,1,2]})
    y=gp.validate_gazepoint_metadata(bad,required_cols=['participant','trial','time'],id_cols='participant',time_col='time',unique_cols=['participant','trial'])
    assert y['status']=='review'
    assert any('Missing values detected' in p for p in y['problems'])
    assert any('not monotonically increasing' in p for p in y['problems'])
    assert any('Duplicate rows detected' in p for p in y['problems'])


def test_missingness_plot():
    d=pd.DataFrame({'time':[1,2,3],'pupil_left':[3,np.nan,3.2]})
    fig=gp.plot_gazepoint_missingness(d,cols='pupil_left',time_col='time')
    assert isinstance(fig,matplotlib.figure.Figure)
    with pytest.raises(ValueError): gp.plot_gazepoint_missingness(d,cols='missing')


def test_detect_pupil_blinks_intervals_onsets_flags():
    dat=pd.DataFrame({'participant':['P01']*10,'time_s':range(10),'LPD':[3,3.1,np.nan,np.nan,3.2,3.1,3,0,3.1,3.2],'RPD':[3,3.1,np.nan,np.nan,3.2,3.1,3,0,3.1,3.2]})
    bl=gp.detect_gazepoint_pupil_blinks(dat,pupil_cols=['LPD','RPD'],time_col='time_s')
    assert len(bl)==2
    np.testing.assert_allclose(bl.onset_time,[2,7]); assert bl.n_samples.tolist()==[2,1]
    d=pd.DataFrame({'time_s':range(1,6),'LPD':[3,np.nan,np.nan,3.1,3.2]})
    np.testing.assert_allclose(gp.detect_gazepoint_pupil_blinks(d,pupil_cols='LPD',time_col='time_s',return_='onsets'),[2])
    assert gp.detect_gazepoint_pupil_blinks(d,pupil_cols='LPD',time_col='time_s',return_='flags').tolist()==[False,True,True,False,False]


def test_clean_pupil_signal_and_grouping():
    dat=pd.DataFrame({'time_s':range(1,8),'LPD':[3.0,3.1,np.nan,np.nan,3.2,30,3.3]})
    out=gp.clean_gazepoint_pupil_signal(dat,pupil_cols='LPD',time_col='time_s',spike_mad=3)
    assert out.LPD_clean.notna().all(); assert out.LPD_was_blink.any(); assert out.LPD_was_spike.any(); assert out.attrs['pupil_cleaning_summary'].iloc[0]['column']=='LPD'
    dat2=pd.DataFrame({'participant':['P01']*3+['P02']*3,'time_s':[1,2,3,1,2,3],'LPD':[3,np.nan,5,10,np.nan,14]})
    out2=gp.clean_gazepoint_pupil_signal(dat2,pupil_cols='LPD',time_col='time_s',group_cols='participant')
    np.testing.assert_allclose(out2.LPD_clean,[3,4,5,10,12,14])


def test_fixation_summary_r_fixture():
    fix=pd.DataFrame({'participant':['P01']*4,'trial':['T1','T1','T1','T2'],'AOI':['A','A','B','A'],'FPOGD':[.2,.3,.4,.5],'FPOGX':[.1,.2,.7,.3],'FPOGY':[.2,.4,.8,.3]})
    out=gp.summarize_gazepoint_fixations(fix)
    assert len(out)==3
    row=out[(out.trial=='T1')&(out.AOI=='A')].iloc[0]
    assert row.n_fixations==2 and row.total_duration_s==pytest.approx(.5)
    fix2=pd.DataFrame({'trial':['T1','T1'],'AOI':['A','A'],'duration_ms':[200,300],'x':[10,20],'y':[5,15]})
    out2=gp.summarize_gazepoint_fixations(fix2,duration_col='duration_ms',x_col='x',y_col='y',group_cols=['trial','AOI'])
    assert out2.iloc[0].total_duration_s==pytest.approx(.5) and out2.iloc[0].x_dispersion==10


def test_gaze_filter_r_fixtures():
    gaze=pd.DataFrame({'time_s':range(1,6),'BPOGX':[.1,.2,1.5,.3,.4],'BPOGY':[.1,.2,.3,-.2,.4]})
    out=gp.filter_gazepoint_gaze(gaze,screen_bounds=(0,1,0,1))
    assert out.gaze_valid.tolist()==[True,True,False,False,True]
    assert np.isnan(out.loc[2,'BPOGX_filtered']) and np.isnan(out.loc[3,'BPOGY_filtered'])
    g2=pd.DataFrame({'participant':['P01']*4,'time_s':[1,2,3,4],'BPOGX':[.1,.2,.95,.96],'BPOGY':[.1,.2,.95,.96]})
    o2=gp.filter_gazepoint_gaze(g2,group_cols='participant',max_velocity=.5)
    assert o2.gaze_valid.iloc[0] and o2.gaze_valid.iloc[1] and not o2.gaze_valid.iloc[2] and o2.gaze_filter_reason.iloc[2]=='high_velocity'


def test_hrv_segment_flags():
    rr=np.r_[np.repeat(800,30),250,np.repeat(820,10),3000,np.repeat(810,20)]
    out=gp.flag_gazepoint_hrv_segments(rr,window_s=None,min_beats=20,min_duration_s=20,max_artifact_prop=.01)
    assert len(out)==1 and not bool(out.quality_ok.iloc[0]) and 'implausible_rr' in out.reasons.iloc[0]
    dat=pd.DataFrame({'participant':np.repeat(['P01','P02'],40),'rr_ms':np.r_[np.repeat(800,40),np.repeat(850,39),250]})
    o2=gp.flag_gazepoint_hrv_segments(dat,rr_col='rr_ms',group_cols='participant',window_s=None,min_beats=20,min_duration_s=20)
    assert bool(o2.loc[o2.participant=='P01','quality_ok'].iloc[0]); assert not bool(o2.loc[o2.participant=='P02','quality_ok'].iloc[0])


def test_scr_latency_response_and_none():
    t=np.arange(0,8.0001,.1); response=np.where((t>=2)&(t<=5),np.exp(-((t-3)**2)/.3),0); dat=pd.DataFrame({'time_s':t,'GSR':1+response}); ev=pd.DataFrame({'event_id':['E1'],'event_time':[2]})
    out=gp.compute_gazepoint_scr_latency(dat,ev,baseline_window_s=(-1,0),response_window_s=(0,4),onset_threshold=.05)
    assert bool(out.response_detected.iloc[0]); assert abs(out.peak_latency_s.iloc[0]-1)<.15; assert out.peak_amplitude.iloc[0]>.9
    flat=pd.DataFrame({'time_s':np.arange(0,5.0001,.1),'GSR':1.0}); no=gp.compute_gazepoint_scr_latency(flat,ev,onset_threshold=.05)
    assert not bool(no.response_detected.iloc[0]) and no.peak_amplitude.iloc[0]<.05


def test_signal_lag_matrix_known_lag_and_groups():
    t=np.arange(0,20.0001,.05); dat=pd.DataFrame({'time_s':t,'x':np.sin(2*np.pi*.2*t),'y':np.sin(2*np.pi*.2*(t-.5))})
    out=gp.compute_gazepoint_signal_lag_matrix(dat,signal_cols=['x','y'],max_lag_s=1,lag_step_s=.05,min_overlap=50)
    assert len(out)==1 and abs(abs(out.best_lag_s.iloc[0])-.5)<.1 and abs(out.best_correlation.iloc[0])>.9
    t2=np.arange(0,5.0001,.1); d2=pd.concat([pd.DataFrame({'participant':'P01','time_s':t2,'a':np.sin(t2),'b':np.sin(t2)}),pd.DataFrame({'participant':'P02','time_s':t2,'a':np.cos(t2),'b':np.cos(t2)})],ignore_index=True)
    o2=gp.compute_gazepoint_signal_lag_matrix(d2,signal_cols=['a','b'],group_cols='participant',max_lag_s=.5,lag_step_s=.1)
    assert len(o2)==2 and (o2.abs_best_correlation>.9).all()


def test_respiration_ppg_vector_and_df():
    fs=50; t=np.arange(0,120+1/fs,1/fs); ppg=.8*np.sin(2*np.pi*.25*t)+.2*np.sin(2*np.pi*1.2*t)
    out=gp.estimate_gazepoint_respiration_from_ppg(pd.DataFrame({'time_s':t,'PPG':ppg}))
    assert abs(out['summary'].iloc[0].respiration_rate_bpm-15)<1 and len(out['spectrum'])>0
    fs2=20;t2=np.arange(0,90+1/fs2,1/fs2); o2=gp.estimate_gazepoint_respiration_from_ppg(np.sin(2*np.pi*.2*t2),sampling_rate_hz=fs2)
    assert abs(o2['summary'].iloc[0].respiration_rate_bpm-12)<1


def _quality_fixture():
    return pd.DataFrame({'participant':np.repeat(['P01','P02'],20),'trial':np.tile(np.repeat([1,2],10),2),'condition':np.tile(np.repeat(['A','B'],10),2),'pupil':np.r_[np.linspace(3,3.09,10),[np.nan]*5,np.linspace(3.10,3.14,5),np.repeat(2.9,10),np.linspace(3,3.07,8),8,-1],'gsr':np.r_[np.linspace(.7,.79,10),np.linspace(.8,.89,10),[np.nan]*6,np.linspace(.9,.93,4),np.repeat(.75,10)]})


def test_signal_quality_compute_and_classify():
    q=gp.compute_gazepoint_signal_quality(_quality_fixture(),signal_cols=['pupil','gsr'],group_cols=['participant','trial','condition'],long_missing_run_threshold=5,long_constant_run_threshold=5)
    assert len(q)==8
    r=q[(q.participant=='P01')&(q.trial==2)&(q.signal=='pupil')].iloc[0]; assert r.n_missing==5 and r.prop_missing==pytest.approx(.5) and r.long_missing_run==5 and bool(r.contains_long_missing_run)
    r2=q[(q.participant=='P02')&(q.trial==1)&(q.signal=='pupil')].iloc[0]; assert r2.long_constant_run==10 and bool(r2.contains_long_constant_run)
    base=pd.DataFrame({'participant':['P01','P02','P03'],'signal':['pupil','pupil','gsr'],'n_samples':[100]*3,'prop_missing':[0,.3,.7],'finite_prop':[1,.7,.3],'flatline_prop':[0,.1,.1],'long_missing_run':[0,12,60],'long_constant_run':[0,0,0],'spike_count':[0,0,0],'extreme_z_count':[0,0,0]})
    c=gp.classify_gazepoint_signal_quality(base); assert c.quality_label.tolist()==['pass','review','exclude_candidate'] and c.attrs['rules']


def test_signal_quality_summary_and_plot():
    q=pd.DataFrame({'signal':['pupil','pupil','gsr'],'condition':['A','B','A'],'n_samples':[10,20,30],'prop_missing':[0,.2,.5],'finite_prop':[1,.8,.5],'flatline_prop':[0,.1,.2],'long_missing_run':[0,3,6],'long_constant_run':[0,4,8],'spike_count':[0,1,2],'extreme_z_count':[0,1,2],'quality_label':['pass','review','exclude_candidate']})
    s=gp.summarize_gazepoint_signal_quality(q,by='signal'); assert len(s)==2 and {'pass_n','review_n','exclude_candidate_n'}.issubset(s.columns)
    fig=gp.plot_gazepoint_signal_quality(q,metric='prop_missing',x='signal'); assert isinstance(fig,matplotlib.figure.Figure)


def _audit(overview, warnings=None): return {'overview':pd.DataFrame([overview]),'warnings':[] if warnings is None else warnings}
def _log(): return {'decisions':pd.DataFrame([{'stage':'quality_control','decision':'retained'}])}


def test_report_templates():
    design=_audit({'n_participants':2,'n_trials':4,'n_conditions':2})
    event=_audit({'n_units':4,'n_expected_events':2,'n_complete_units':4,'complete_unit_prop':1.0})
    condition=_audit({'n_participants':2,'n_conditions':2,'n_trials':4,'trial_imbalance_ratio':1.0,'complete_participant_condition_grid':True})
    methods=gp.create_gazepoint_methods_section(design_audit=design,event_audit=event,condition_audit=condition,decision_log=_log(),validation={'test':'PASS 2322','check':'0 errors, 0 warnings, 0 notes'})
    text=str(methods); assert methods.template=='methods_section' and 'gpbiometrics' in text and 'experiment-design audit' in text and 'Event coverage' in text and 'structured analysis decision log' in text and 'not interpreted as direct measures' in text
    qc=gp.create_gazepoint_qc_supplement(design_audit=design,event_audit=event,condition_audit=condition,decision_log=_log()); assert qc.template=='qc_supplement' and 'Experiment-design audit' in str(qc) and 'Analysis decision log' in str(qc)
    repro=gp.create_gazepoint_reproducibility_statement(decision_log=_log(),repository_url='https://example.org/repo',validation={'test':'PASS'},data_statement='Synthetic demonstration data were used.'); assert repro.template=='reproducibility_statement' and 'not as automatic labels' in str(repro)
    audit=gp.create_gazepoint_audit_report_section(design_audit=design,event_audit=event,condition_audit=condition,decision_log=_log()); assert audit.template=='audit_report_section' and 'No audit warnings' in str(audit)


def test_report_template_validation_and_empty():
    assert 'No audit objects were supplied' in str(gp.create_gazepoint_qc_supplement())
    assert 'No audit objects were supplied' in str(gp.create_gazepoint_audit_report_section())
    with pytest.raises(ValueError): gp.create_gazepoint_methods_section(export_profile=pd.DataFrame())
    with pytest.raises(ValueError): gp.create_gazepoint_qc_supplement(title='')
    with pytest.raises(ValueError): gp.create_gazepoint_reproducibility_statement(validation=['PASS'])
