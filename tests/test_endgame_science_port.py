import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import gpbiometricspy as gp


def test_eda_artifacts_and_scr_peaks():
    clean=pd.DataFrame({'source_file':'clean.csv','CNT':np.arange(1,61),'GSR_US':np.linspace(1,2,60)})
    a=gp.audit_gazepoint_eda_artifacts(clean,signal_col='GSR_US',time_col='CNT',group_cols='source_file',flat_run_length=10,zero_run_length=10)
    assert a['overview'].loc[0,'status']=='pass' and a['overview'].loc[0,'artifact_rows']==0
    flat=pd.DataFrame({'CNT':np.arange(1,31),'GSR_US':np.r_[np.zeros(10),np.linspace(1,2,20)]})
    af=gp.audit_gazepoint_eda_artifacts(flat,signal_col='GSR_US',time_col='CNT',flat_run_length=5,zero_run_length=5)
    assert af['overview'].loc[0,'flatline_run_rows']>=10 and af['overview'].loc[0,'zero_run_rows']>=10
    dat=pd.DataFrame({'source_file':'simple.csv','CNT':np.arange(1,22),'GSR_US_PHASIC':np.r_[np.zeros(5),.02,.05,.10,.06,.02,0,np.zeros(10)]})
    p=gp.detect_gazepoint_scr_peaks(dat,phasic_col='GSR_US_PHASIC',time_col='CNT',group_cols='source_file',amplitude_min=.03)
    assert p['overview'].loc[0,'status']=='peaks_detected' and p['overview'].loc[0,'detected_peaks']==1
    assert np.isclose(p['peaks'].loc[0,'amplitude'],.10)
    low=gp.detect_gazepoint_scr_peaks(pd.DataFrame({'CNT':np.arange(1,13),'GSR_US_PHASIC':[0,0,.005,.01,.005,0,0,0,0,0,0,0]}),phasic_col='GSR_US_PHASIC',time_col='CNT',amplitude_min=.05)
    assert low['overview'].loc[0,'status']=='candidate_peaks_below_threshold'


def test_scr_event_windows_collapse_nonresponders_hurdle_sensitivity():
    events=pd.DataFrame({'participant':['P1'],'event_time':[10.],'condition':['stimulus']})
    peaks=pd.DataFrame({'participant':['P1'],'peak_id':[1],'peak_time':[12.],'onset_time':[11.],'amplitude':[.05],'rise_time':[1.],'recovery_time_after_peak':[3.],'status':['detected']})
    w=gp.summarise_gazepoint_scr_event_windows(scr_peaks=peaks,events=events,event_time_col='event_time',event_label_col='condition',group_cols='participant',analysis_window=(0,6),response_window=(1,4))
    assert w['overview'].loc[0,'status']=='scr_event_windows_summarised'
    assert w['event_table'].loc[0,'response_flag']==1 and np.isclose(w['event_table'].loc[0,'scr_latency'],2)
    ttl=pd.DataFrame({'participant':['P1']*10,'CNT':np.arange(1,11),'TTL0':[0,1,1,0,0,1,0,0,0,0],'TTL1':[0,1,1,0,0,1,0,0,0,0]})
    pk=pd.DataFrame({'participant':['P1','P1'],'peak_id':[1,2],'peak_time':[4,8],'onset_time':[3,7],'amplitude':[.05,.07],'rise_time':[1,1],'recovery_time_after_peak':[2,2],'status':['detected','detected']})
    wc=gp.summarise_gazepoint_scr_event_windows(data=ttl,scr_peaks=pk,time_col='CNT',group_cols='participant',ttl_cols=['TTL0','TTL1'],analysis_window=(0,4),response_window=(1,3),collapse_simultaneous_events=True)
    assert wc['overview'].loc[0,'event_count']==2 and (wc['events']['collapsed_event_count']==2).all()
    assert (wc['events']['event_label']=='TTL0+TTL1').all()
    nr=gp.screen_gazepoint_eda_nonresponders(pd.DataFrame({'participant':['P1','P1','P2','P2'],'response_flag':[1,0,0,0],'scr_amplitude':[.05,np.nan,np.nan,np.nan]}),group_cols='participant',min_events=2,min_response_events=1,min_response_rate=.1)
    assert nr['overview'].loc[0,'candidate_nonresponder_count']==1 and nr['candidate_nonresponders'].iloc[0]['participant']=='P2'
    h=gp.prepare_gazepoint_scr_hurdle_model_data(pd.DataFrame({'participant':['P1','P1','P2','P2'],'condition':['A','B','A','B'],'event_id':['e1','e2','e3','e4'],'response_flag':[1,0,1,0],'scr_amplitude':[.05,np.nan,.08,np.nan]}),predictor_cols='condition',factor_cols=['participant','condition'],group_cols='participant',amplitude_transform='log')
    assert len(h['response_model_data'])==4 and len(h['amplitude_model_data'])==2
    assert 'scr_amplitude_raw' in h['amplitude_model_data']
    sd=pd.DataFrame({'participant':['P1']*20,'CNT':np.arange(1,21),'GSR_US_PHASIC':np.r_[np.zeros(5),.02,.08,.02,np.zeros(12)]})
    sens=gp.run_gazepoint_scr_threshold_sensitivity(sd,phasic_col='GSR_US_PHASIC',time_col='CNT',group_cols='participant',amplitude_min_values=[.01,.05],min_peak_distance_values=[1,5],include_event_windows=False)
    assert len(sens['sensitivity_grid'])==4 and sens['overview'].loc[0,'status']=='scr_threshold_sensitivity_completed'


def test_eda_spectral_wavelet_tvsymp_gram_drift_mad():
    rng=np.random.default_rng(1);t=np.arange(128.);x=np.sin(2*np.pi*.1*t)+rng.normal(0,.01,len(t));dat=pd.DataFrame({'participant':'p1','time':t,'GSR_US':x})
    sp=gp.extract_gazepoint_eda_spectral_power(dat,time_col='time',group_cols='participant',sampling_rate=1)
    assert sp['overview'].loc[0,'status']=='eda_spectral_power_extracted' and np.isfinite(sp['spectral_summary'].loc[0,'band_power'])
    wav=gp.denoise_gazepoint_eda_wavelet(dat,group_cols='participant')
    assert 'GSR_US_wavelet_denoised' in wav and wav.attrs['wavelet_denoising_overview']['status']=='eda_wavelet_denoising_complete'
    long_t=np.arange(181.);long=pd.DataFrame({'participant':'p1','time':long_t,'GSR_US':np.sin(2*np.pi*.12*long_t)+rng.normal(0,.05,len(long_t))})
    tv=gp.extract_gazepoint_eda_tvsymp(long,time_col='time',group_cols='participant',sampling_rate=1,window_seconds=60,step_seconds=30)
    assert len(tv['tvsymp_timeseries'])>0 and 'edasympn' in tv['tvsymp_timeseries']
    gram=gp.plot_gazepoint_eda_gram(pd.DataFrame({'participant':'p1','time':np.arange(121.),'GSR_US':np.sin(2*np.pi*.1*np.arange(121.))}),time_col='time',group_cols='participant',sampling_rate=1,window_seconds=30,step_seconds=15,frequency_bins=16,plot=False)
    assert len(gram['gram_table'])>0 and 'power' in gram['gram_table']
    drift=gp.audit_gazepoint_distributional_drift(pd.DataFrame({'participant':['p1']*100,'session':[1]*50+[2]*50,'GSR_US':np.r_[rng.normal(1,.1,50),rng.normal(2,.1,50)]}),signal_cols='GSR_US',participant_col='participant')
    assert 'psi' in drift['drift_summary'] and (drift['drift_summary']['comparison_session']=='2').any()
    arr=np.r_[np.linspace(1,1.2,10),np.repeat(1.2,8),5,1.3,1.31,8,8.1,8.2]
    mad=gp.flag_gazepoint_mad_artifacts(pd.DataFrame({'participant':'p1','time':np.arange(len(arr)),'GSR_US':arr}),time_col='time',group_cols='participant',mad_multiplier=4,flatline_tolerance=1e-8,flatline_min_run=4)
    assert mad['mad_artifact'].any() and set(mad.loc[mad.mad_artifact,'mad_artifact_type']) & {'flatline','needle','step','wall','multiple'}


def test_nonlinear_and_surrogate():
    rng=np.random.default_rng(4);ibi=.8+.04*np.sin(np.linspace(0,8*np.pi,80))+rng.normal(0,.005,80);dat=pd.DataFrame({'participant':'p1','IBI':ibi})
    f=gp.extract_gazepoint_hrv_fuzzy_csi(dat,group_cols='participant')
    assert 'fuzzy_entropy' in f['features'] and np.isfinite(f['features'].loc[0,'csi'])
    rc=gp.extract_gazepoint_hrv_rcmse(pd.DataFrame({'participant':'p1','IBI':.8+.04*np.sin(np.linspace(0,10*np.pi,100))+rng.normal(0,.005,100)}),group_cols='participant',scales=[1,2,3,4],min_intervals=20)
    assert len(rc['rcmse_by_scale'])==4 and 'mean_rcmse' in rc['summary']
    sur=gp.test_gazepoint_hrv_nonlinearity(dat,group_cols='participant',n_surrogates=9,seed=1)
    assert len(sur['surrogate_statistics'])==9 and 'p_two_sided' in sur['results']


def test_respiration_change_recovery():
    t=np.arange(0,120.1,.1);sig=np.sin(2*np.pi*.25*t)+.2*np.sin(2*np.pi*1.2*t);dat=pd.DataFrame({'participant':'p1','time':t,'signal':sig})
    ce=gp.extract_gazepoint_respiration_ceemdan(dat,signal_col='signal',time_col='time',group_cols='participant',sampling_rate=10,respiration_band=(.1,.5))
    assert len(ce['respiration_timeseries'])>0 and 'proxy_respiration_rate_hz' in ce['summary']
    t2=np.arange(0,60.5,.5);truth=np.sin(2*np.pi*.25*t2);kf=gp.fuse_gazepoint_respiration_kalman(pd.DataFrame({'participant':'p1','time':t2,'pdr':truth+.05,'edr':truth-.05}),primary_col='pdr',secondary_col='edr',time_col='time',group_cols='participant')
    assert 'respiration_kalman_fused' in kf and kf.attrs['kalman_respiration_overview']['status']=='kalman_respiration_fusion_complete'
    rng=np.random.default_rng(3);tc=np.arange(121.);xs=np.r_[rng.normal(0,.1,61),rng.normal(2,.1,60)];cp=gp.detect_gazepoint_doubly_stochastic_changepoints(pd.DataFrame({'participant':'p1','time':tc,'signal':xs}),signal_col='signal',time_col='time',group_cols='participant',window_seconds=10,step_seconds=5,threshold_mad_multiplier=3)
    assert len(cp['score_table'])>0 and 'change_score' in cp['score_table']
    tr=np.arange(0,40.5,.5);rt=np.maximum(0,tr-5);eda=1+np.where(tr>=5,np.exp(-rt/8)-np.exp(-rt/.8),0);eda=eda/eda.max();rec=gp.extract_gazepoint_scr_recovery_times(pd.DataFrame({'participant':'p1','time':tr,'GSR_US':eda,'onset':[5]+[np.nan]*(len(tr)-1)}),eda_col='GSR_US',time_col='time',event_onset_col='onset',group_cols='participant',peak_window_s=10,recovery_window_s=30)
    assert {'rec_t2','rec_tc'} <= set(rec['recovery_table'])


def test_endgame_validation_edges():
    import pytest
    with pytest.raises(ValueError,match='response_window'):
        gp.summarise_gazepoint_scr_event_windows(scr_peaks=pd.DataFrame({'peak_time':[2],'amplitude':[.1]}),events=pd.DataFrame({'event_time':[1]}),event_time_col='event_time',analysis_window=(0,4),response_window=(-1,5))
    with pytest.raises(ValueError,match='amplitude_min_values'):
        gp.run_gazepoint_scr_threshold_sensitivity(pd.DataFrame({'CNT':[1,2,3],'GSR_US_PHASIC':[0,0,0]}),amplitude_min_values=[-1])
    with pytest.raises(ValueError,match='amplitude_col'):
        gp.prepare_gazepoint_scr_hurdle_model_data(pd.DataFrame({'response_flag':[1]}))
