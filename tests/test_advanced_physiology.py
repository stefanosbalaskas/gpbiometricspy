import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_temperature_luminance_and_stabilization():
    rng=np.random.default_rng(1)
    n=60
    dat=pd.DataFrame({'participant':['p1']*n,'time':np.arange(1,n+1),'GSR_US':1+.05*np.arange(1,n+1)+rng.normal(0,.01,n),'ambient_temp':20+.1*np.arange(1,n+1)})
    out=gp.correct_gazepoint_eda_temperature(dat,eda_col='GSR_US',temperature_cols='ambient_temp',group_cols='participant',time_col='time')
    assert 'eda_temperature_adjusted' in out
    assert out.attrs['eda_temperature_overview']['status']=='eda_temperature_correction_complete'
    lum=np.linspace(-1,1,80); pupil=3+.4*lum+rng.normal(0,.05,80)
    po=gp.regress_gazepoint_pupil_luminance(pd.DataFrame({'participant':['p1']*80,'time':np.arange(80),'pupil':pupil,'luminance':lum}),pupil_col='pupil',luminance_col='luminance',group_cols='participant',time_col='time')
    assert 'pupil_luminance_adjusted' in po
    assert po.attrs['pupil_luminance_overview']['status']=='pupil_luminance_regression_complete'
    st=gp.audit_gazepoint_stabilization_period(pd.DataFrame({'participant':['p1']*121,'CNT':np.arange(0,1201,10),'GSR_US':rng.normal(size=121)}),group_cols='participant',stabilization_minutes=10)
    assert st.in_stabilization_period.any() and (~st.in_stabilization_period).any()


def test_kmeans_beats_and_ipfm():
    rng=np.random.default_rng(2); time=np.arange(0,20.0001,.02); pulse=np.zeros(len(time))
    for bt in np.arange(1,20): pulse+=np.exp(-.5*((time-bt)/.03)**2)
    out=gp.extract_gazepoint_beats_kmeans(pd.DataFrame({'participant':['p1']*len(time),'time':time,'HRP':pulse+rng.normal(0,.02,len(time))}),pulse_col='HRP',time_col='time',group_cols='participant',min_distance_s=.5,seed=1)
    assert len(out['beat_table'])>5
    assert 'ibi_s' in out['interval_table']
    ip=gp.model_gazepoint_hrv_ipfm(pd.DataFrame({'participant':['p1']*60,'IBI':.8+rng.normal(0,.02,60)}),ibi_col='IBI',group_cols='participant',output_sampling_rate=4,max_frequency=.5)
    assert len(ip['impulse_table'])>0 and 'frequency_hz' in ip['spectrum_table']
    assert ip['overview'].iloc[0].status=='ipfm_model_created'


def test_external_eda_bridges_and_files(tmp_path):
    dat=pd.DataFrame({'participant':np.repeat(['p1','p2'],20),'CNT':np.tile(np.arange(1,21),2),'GSR_US':np.r_[np.linspace(1,2,20),np.linspace(2,3,20)]})
    out=gp.prepare_gazepoint_ledalab_input(dat,eda_col='GSR_US',time_col='CNT',group_cols='participant',sampling_rate=60,output_dir=tmp_path,prefix='test_bridge')
    assert out['overview'].iloc[0].status=='ledalab_input_prepared'
    assert out['overview'].iloc[0].group_count==2 and out['overview'].iloc[0].ready_group_count==2
    assert {'time_s','conductance_us','group_id'} <= set(out['signal_table'])
    assert len(out['manifest'])==2 and all((tmp_path / p.split('/')[-1]).exists() for p in out['manifest'].path)
    no_time=gp.prepare_gazepoint_pspm_input(pd.DataFrame({'participant':np.repeat(['p1','p2'],10),'GSR_US':np.r_[np.linspace(1,2,10),np.linspace(2,3,10)]}),eda_col='GSR_US',group_cols='participant',sampling_rate=10)
    assert set(no_time['signal_table'].detected_time_unit)=={'sample_index'}
    cvx=gp.prepare_gazepoint_cvxeda_input(pd.DataFrame({'participant':['p1']*20,'time_s':np.arange(20)/10,'GSR_US':np.linspace(1,2,20)}),eda_col='GSR_US',time_col='time_s',group_cols='participant')
    np.testing.assert_allclose(cvx['signal_table'].y,cvx['signal_table'].conductance_us)
    res=gp.prepare_gazepoint_ledalab_input(pd.DataFrame({'participant':['p1']*3,'CNT':[1,2,3],'GSR':[1_000_000,500_000,250_000]}),eda_col='GSR',time_col='CNT',group_cols='participant',sampling_rate=60,convert_resistance_to_us=True)
    np.testing.assert_allclose(res['signal_table'].conductance_us,[1,2,4])


def test_eda_response_patterns_and_no_finite():
    dat=pd.DataFrame({'participant':np.repeat(['none','low','moderate','high'],4),'scr_amplitude_us':[0,.002,.003,.004,.02,.03,.04,.04,.08,.10,.15,.18,.25,.30,.40,.50]})
    out=gp.classify_gazepoint_eda_response_pattern(dat,response_col='scr_amplitude_us',group_cols='participant',summary_function='max_abs',no_response_threshold=.01,low_response_threshold=.05,moderate_response_threshold=.20)
    got=dict(zip(out['classifications'].participant,out['classifications'].response_pattern))
    assert got=={'none':'no_detectable_response','low':'low_response','moderate':'moderate_response','high':'high_response'}
    assert out['classifications'].interpretation.str.contains('does not infer emotion').all()
    nf=gp.classify_gazepoint_eda_response_pattern(pd.DataFrame({'participant':['p1','p1'],'scr_amplitude_us':[np.nan,np.nan]}),response_col='scr_amplitude_us',group_cols='participant')
    assert nf['overview'].iloc[0].status=='eda_response_patterns_not_classified'
    with pytest.raises(ValueError,match='No EDA'):
        gp.prepare_gazepoint_ledalab_input(pd.DataFrame({'CNT':[1,2],'HR':[60,61]}),time_col='CNT',sampling_rate=60)


def test_advanced_modality_bridges():
    t=np.arange(0,10.5,.5); dat=pd.DataFrame({'participant':['p1']*len(t),'time':t,'EDA_left':1+np.sin(t)*.05,'EDA_right':1+np.cos(t)*.04})
    out=gp.extract_gazepoint_bilateral_eda_asymmetry(dat,left_col='EDA_left',right_col='EDA_right',time_col='time',group_cols='participant')
    assert 'beda_left_minus_right' in out['asymmetry_timeseries']
    assert 'mean_left_minus_right' in out['summary'] and out['overview'].iloc[0].status=='bilateral_eda_asymmetry_complete'
    q=gp.denoise_gazepoint_quantization_noise(pd.DataFrame({'participant':['p1']*30,'IBI':np.resize([.80,.81,.82],30),'GSR_US':np.resize([1.,1.01,1.02],30)}),signal_cols=['IBI','GSR_US'],resolution={'IBI':.001,'GSR_US':.01},seed=1)
    assert 'IBI_quantization_jittered' in q and 'GSR_US_quantization_jittered' in q
    assert q.attrs['quantization_noise_overview']['status']=='quantization_noise_reduction_complete'


def test_edr_pca_and_skin_potential():
    time=np.arange(0,20.5,.5); resp=np.sin(2*np.pi*.2*time); dat=pd.DataFrame({'participant':['p1']*len(time),'time':time,'qrs_amp':1+.1*resp,'qrs_width':.08+.01*resp,'qrs_area':.5+.05*resp})
    pca=gp.extract_gazepoint_edr_pca(dat,ecg_cols=['qrs_amp','qrs_width','qrs_area'],time_col='time',group_cols='participant',n_components=1)
    assert 'edr_pca_pc1' in pca['edr_timeseries'] and 'variance_explained' in pca['component_summary']
    assert pca['overview'].iloc[0].status=='edr_pca_extracted'
    time=np.arange(0,60.5,.5); sp=2+.01*np.sin(time); sp[np.argmin(abs(time-10))]+=.5; sp[np.argmin(abs(time-30))]-=.6
    sk=gp.analyze_gazepoint_skin_potential(pd.DataFrame({'participant':['p1']*len(time),'time':time,'SP_mV':sp}),sp_col='SP_mV',time_col='time',group_cols='participant',response_direction='both',response_threshold=.5,min_response_distance_s=2)
    assert 'mean_spl' in sk['level_summary'] and 'skin_potential_response' in sk['timeseries']
    assert sk['overview'].iloc[0].status=='skin_potential_analysis_complete'


def test_advanced_edge_paths():
    with pytest.raises(ValueError,match='temperature_cols'):
        gp.correct_gazepoint_eda_temperature(pd.DataFrame({'GSR_US':[1,2,3,4,5]}),temperature_cols=None)
    with pytest.raises(ValueError,match='ecg_cols'):
        gp.extract_gazepoint_edr_pca(pd.DataFrame({'x':[1,2,3]}),ecg_cols=['x'])
    with pytest.raises(ValueError,match='Thresholds'):
        gp.classify_gazepoint_eda_response_pattern(pd.DataFrame({'GSR_US':[1]}),no_response_threshold=.2,low_response_threshold=.1)
