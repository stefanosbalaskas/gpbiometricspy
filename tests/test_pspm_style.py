import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_pspm_marker_extraction_and_combination():
    fs=10; t=np.arange(0,10+1/fs/2,1/fs)
    a=np.zeros(len(t)); b=np.zeros(len(t)); a[(t>=2)&(t<2.3)]=1; b[(t>=5)&(t<5.2)]=9
    d=pd.DataFrame({'participant':'P01','time_s':t,'marker_a':a,'marker_b':b,'scr':np.sin(t)})
    m=gp.extract_gazepoint_markerinfo_pspm_style(d,['marker_a','marker_b'],'time_s',group_cols='participant')
    assert len(m)>=2 and {'marker_channel','time_s','marker_code'}<=set(m)
    assert m['sample_index'].min() >= 1
    c=gp.combine_gazepoint_marker_channels_pspm_style(d,['marker_a','marker_b'],'time_s',group_cols='participant')
    assert isinstance(c['data'],pd.DataFrame) and 'pspm_marker' in c['data'] and isinstance(c['markers'],pd.DataFrame)


def test_pspm_trim_split_merge():
    rng=np.random.default_rng(1)
    d=pd.DataFrame({'time_s':np.r_[np.arange(0,2.01,.1),np.arange(10,12.01,.1)],'scr':rng.normal(size=42)})
    trimmed=gp.trim_gazepoint_biometrics_pspm_style(d,.5,1.5,'time_s',True)
    assert trimmed.time_s.min()==pytest.approx(0)
    sp=gp.split_gazepoint_sessions_pspm_style(d,'time_s',2)
    assert len(sp['sessions'])==2 and len(sp['split_data'])==2
    assert sp['sessions'].iloc[0]['start_index']==1
    merged=gp.merge_gazepoint_recordings_pspm_style([trimmed,trimmed],'time_s',1)
    assert merged.pspm_recording.nunique()==2 and 'pspm_original_time_s' in merged


def test_pspm_scr_preprocessing_and_numeric_input():
    fs=50; t=np.arange(0,20+1/fs/2,1/fs); scr=1+.01*t+.2*np.exp(-((t-8)**2)/.8)
    scr[99:110]=100; scr[399:440]=scr[399]
    out=gp.preprocess_gazepoint_scr_pspm_style(pd.DataFrame({'time_s':t,'gsr':scr}),'gsr','time_s',fs,range=(0,20))
    assert {'scr_processed','pspm_artifact'}<=set(out['signal']) and out['signal'].pspm_artifact.any()
    assert len(out['summary'])==1
    v=gp.preprocess_gazepoint_scr_pspm_style(np.sin(np.arange(100)/10)+2,sampling_rate_hz=10)
    assert len(v['signal'])==100
    with pytest.raises(ValueError): gp.preprocess_gazepoint_scr_pspm_style(np.ones(10))


def test_pspm_segments():
    fs=20; t=np.arange(0,20+1/fs/2,1/fs)
    d=pd.DataFrame({'time_s':t,'scr':np.sin(t)})
    events=pd.DataFrame({'event_id':[1,2],'onset_time_s':[5,12],'condition':['A','B']})
    seg=gp.extract_gazepoint_segments_pspm_style(d,events,'scr','time_s',event_id_col='event_id',condition_col='condition',pre_s=1,post_s=2)
    assert {'event_id','relative_time_s','value_baseline_corrected'}<=set(seg)
    assert seg.event_id.nunique()==2 and seg.sample_index.min()>=1


def test_pspm_glm_and_export(tmp_path):
    rng=np.random.default_rng(123); fs=20; t=np.arange(0,60+1/fs/2,1/fs)
    ev=pd.DataFrame({'onset_time_s':[5,15,25,35,45],'condition':['A','B','A','B','A']})
    design=gp.create_gazepoint_pspm_glm_design(ev,t,response='scr',response_length_s=8)
    assert {'pspm_A','pspm_B','intercept'}<=set(design)
    y=.5*design.pspm_A-.2*design.pspm_B+rng.normal(0,.01,len(t))
    fit=gp.fit_gazepoint_convolution_glm(pd.DataFrame({'time_s':t,'scr':y}),design,'scr','time_s')
    assert fit['class']=='gazepoint_pspm_glm' and fit['summary'].iloc[0].r_squared>.5
    files=gp.export_gazepoint_pspm_model_estimates(fit,tmp_path/'fit.csv')
    assert len(files)==3 and (tmp_path/'fit.csv').exists()
    files2=gp.export_gazepoint_pspm_model_estimates(fit,tmp_path/'fit.rds')
    assert (tmp_path/'fit.rds').exists() and len(files2)==1


def test_pspm_design_edges_and_errors(tmp_path):
    ev=pd.DataFrame({'onset_time_s':[1,2],'condition':['A','A'],'duration':[.6,0]})
    t=np.arange(0,5,.1)
    d=gp.create_gazepoint_pspm_glm_design(ev,t,duration_col='duration',response='boxcar',include_derivative=True,add_intercept=False)
    assert 'pspm_A_derivative' in d and 'intercept' not in d
    with pytest.raises(ValueError): gp.extract_gazepoint_markerinfo_pspm_style(pd.DataFrame({'time_s':[0,1]}),marker_cols=[])
    with pytest.raises(ValueError): gp.create_gazepoint_pspm_glm_design(pd.DataFrame({'x':[1]}),t)
    with pytest.raises(ValueError): gp.merge_gazepoint_recordings_pspm_style([])
