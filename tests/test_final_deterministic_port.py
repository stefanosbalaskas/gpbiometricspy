import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt

import gpbiometricspy as gp


def test_gsr_units_and_adaptive_ema():
    c = gp.audit_gazepoint_gsr_units(pd.DataFrame({'GSR_US':[.8,1.2,2.5,4.]}), gsr_col='GSR_US')
    assert c['overview'].loc[0,'likely_unit'] == 'conductance_microSiemens'
    r = gp.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':[500000.,1000000.,1500000.,2000000.]}), gsr_col='GSR', convert=True)
    assert r['overview'].loc[0,'likely_unit'] == 'resistance_or_impedance_ohms'
    assert np.all(np.isfinite(r['data']['GSR_converted_us']))
    dat = pd.DataFrame({'participant':np.repeat(['p1','p2'],30),'time':np.tile(np.arange(1,31),2),'GSR_US':np.r_[np.linspace(1,2,30),np.linspace(2,4,30)]})
    out = gp.standardise_gazepoint_adaptive_ema(dat, group_cols='participant', time_col='time', alpha=.2)
    assert {'GSR_US_adaptive_ema','GSR_US_ema_center'} <= set(out.columns)
    assert out.attrs['adaptive_ema_overview']['status'] == 'adaptive_ema_normalization_complete'
    alias = gp.standardize_gazepoint_adaptive_ema(dat, group_cols='participant', time_col='time', alpha=.2)
    np.testing.assert_allclose(out.GSR_US_adaptive_ema, alias.GSR_US_adaptive_ema)


def test_downsample_exact_fixtures_and_methods():
    demo=pd.DataFrame({'participant':np.repeat(['P01','P02'],10),'time_ms':np.tile(np.arange(10),2),'pupil':np.arange(1,21),'gsr':np.arange(21,41)})
    out=gp.downsample_gazepoint_data(demo,time_col='time_ms',signal_cols=['pupil','gsr'],group_cols='participant',interval=5,method='mean')
    assert len(out)==4
    assert out.loc[out.participant=='P01','time_ms'].tolist()==[0.,5.]
    np.testing.assert_allclose(out.loc[out.participant=='P01','pupil'],[3,8])
    np.testing.assert_allclose(out.loc[out.participant=='P02','pupil'],[13,18])
    assert out.n_source_rows.tolist()==[5,5,5,5]
    d=pd.DataFrame({'time_s':[10,11,12,13],'pupil':[1,np.nan,3,5]})
    cent=gp.downsample_gazepoint_data(d,time_col='time_s',signal_cols='pupil',interval=2,time_value='center',origin=10)
    np.testing.assert_allclose(cent.time_s,[11,13]);np.testing.assert_allclose(cent.pupil,[1,4])
    keep=gp.downsample_gazepoint_data(d,time_col='time_s',signal_cols='pupil',interval=2,na_rm=False,origin=10)
    assert np.isnan(keep.pupil.iloc[0]) and keep.pupil.iloc[1]==4
    m=pd.DataFrame({'time_s':range(4),'signal':[1,100,3,5]})
    assert gp.downsample_gazepoint_data(m,'time_s','signal',interval=2,method='median').signal.tolist()==[50.5,4]
    assert gp.downsample_gazepoint_data(m,'time_s','signal',interval=2,method='first').signal.tolist()==[1,3]
    assert gp.downsample_gazepoint_data(m,'time_s','signal',interval=2,method='last').signal.tolist()==[100,5]


def test_sampling_audit_seconds_ms_duplicates_samples_and_groups():
    d=pd.DataFrame({'source_participant':['User 1']*4,'MEDIA_ID':[0]*4,'TIME':np.arange(4)/60})
    out=gp.audit_gazepoint_biometric_sampling(d,['source_participant','MEDIA_ID'],'TIME','seconds',60,1)
    assert out.loc[0,'estimated_rate_hz']==pytest.approx(60); assert out.loc[0,'rate_status']=='within_tolerance'; assert bool(out.loc[0,'strictly_increasing'])
    ms=gp.audit_gazepoint_biometric_sampling(pd.DataFrame({'TIME_TICK':[0,16.6667,33.3334,50.0001]}),time_column='TIME_TICK',time_unit='milliseconds',tolerance_hz=1)
    assert 59<ms.loc[0,'estimated_rate_hz']<61
    bad=gp.audit_gazepoint_biometric_sampling(pd.DataFrame({'TIME':[0,.1,.1,.05]}),time_column='TIME')
    assert bad.loc[0,'duplicate_time_rows']==1 and bad.loc[0,'zero_interval_rows']==1 and bad.loc[0,'negative_interval_rows']==1
    samp=gp.audit_gazepoint_biometric_sampling(pd.DataFrame({'CNT':[1,2,3,4]}),time_column='CNT',time_unit='samples')
    assert samp.loc[0,'rate_status']=='not_estimated' and np.isnan(samp.loc[0,'estimated_rate_hz'])


def test_hrv_feature_summary_matches_frozen_fixtures():
    df=pd.DataFrame({'participant':['P1']*4,'time':[1,2,3,4],'IBI':[1.,1.1,.9,1.]})
    out=gp.summarise_gazepoint_hrv_features(df,group_cols='participant',time_col='time')
    f=out['features'].iloc[0]
    assert out['overview'].loc[0,'status']=='hrv_features_available'; assert f.n_valid_ibi==4; assert f.unit_detected=='seconds'; assert f.mean_ibi_ms==pytest.approx(1000); assert f.mean_hr_bpm_from_ibi==pytest.approx(60); assert f.rmssd_ms==pytest.approx(np.sqrt(20000)); assert f.pnn50_percent==100
    auto=gp.summarise_gazepoint_hrv_features(pd.DataFrame({'HRV':[1]*4,'IBI':[900,1000,1100,1000]}))
    assert auto['settings']['ibi_col']=='IBI' and auto['features'].loc[0,'unit_detected']=='milliseconds'
    poor=gp.summarise_gazepoint_hrv_features(pd.DataFrame({'IBI':[.2,1.,3.,np.nan]}),min_valid_ibi=3)
    assert poor['features'].loc[0,'n_valid_ibi']==1 and poor['features'].loc[0,'n_out_of_range_ibi']==2 and poor['features'].loc[0,'n_missing_ibi']==1 and poor['overview'].loc[0,'status']=='insufficient_valid_ibi'


def test_ibi_hrv_window_summary():
    dat=pd.DataFrame({'p':['A']*4,'IBI':[1.,1.1,.9,1.],'HRV':[1,1,1,1]})
    out=gp.summarise_gazepoint_ibi_hrv_windows(dat,'p')
    assert out.loc[0,'mean_ibi_sec']==pytest.approx(1); assert out.loc[0,'mean_hr_from_ibi_bpm']==pytest.approx(np.mean(60/np.array([1.,1.1,.9,1.])))
    assert out.loc[0,'sdnn_ms']==pytest.approx(np.std([1.,1.1,.9,1.],ddof=1)*1000)


def test_exclusion_recommendations_frozen_cases():
    windows=pd.DataFrame({'source_participant':['User 0','User 0','User 1','User 1'],'MEDIA_ID':[0,1,0,1],'gsr_usable_pct':[0,0,100,100],'hr_usable_pct':[0,0,100,90],'dial_usable_pct':[0,0,100,100]})
    out=gp.recommend_gazepoint_biometric_exclusions(windows,data_is_window_summary=True,require_gsr=True,require_hr=True,require_dial=False)
    ov=out['overview'].iloc[0]; assert ov.n_windows==4 and ov.exclude_windows==2 and ov.keep_windows==2
    p=out['participant_recommendations'].set_index('participant'); assert p.loc['User 0','participant_recommendation']=='exclude'; assert p.loc['User 1','participant_recommendation']=='keep'
    review=gp.recommend_gazepoint_biometric_exclusions(pd.DataFrame({'source_participant':['User 1'],'MEDIA_ID':[0],'gsr_usable_pct':[100],'hr_usable_pct':[100],'dial_usable_pct':[0]}),data_is_window_summary=True)
    assert review['window_recommendations'].loc[0,'recommendation']=='review'; assert 'Engagement-dial' in review['window_recommendations'].loc[0,'recommendation_reason']
    raw=pd.DataFrame({'source_participant':['User 1']*3,'MEDIA_ID':[0]*3,'GSR_US':[1.1,1.2,1.3],'GSRV':[1,1,1],'HR':[70,72,74],'HRV':[1,1,1],'DIAL':[1,1,1],'DIALV':[1,1,1]})
    assert gp.recommend_gazepoint_biometric_exclusions(raw,group_columns=['source_participant','MEDIA_ID'])['window_recommendations'].loc[0,'recommendation']=='keep'


def test_pupil_baseline_and_main_sequence():
    dat=pd.DataFrame({'participant':['p1']*6,'trial':[1]*6,'time':[-240,-220,-200,0,100,200],'pupil':[3,3.2,3.4,4,4.2,4.4]})
    out=gp.baseline_correct_gazepoint_pupil(dat,pupil_col='pupil',time_col='time',trial_cols=['participant','trial'],baseline_window=[-240,-200])
    assert out.loc[3,'pupil_baseline_corrected']==pytest.approx(.8); assert out.attrs['pupil_baseline_summary']['status']=='pupil_baseline_correction_complete'
    p=gp.plot_gazepoint_saccade_main_sequence(pd.DataFrame({'amplitude_deg':[1,2,3,4,5],'peak_velocity_deg_s':[100,180,250,300,340]}),amplitude_col='amplitude_deg',peak_velocity_col='peak_velocity_deg_s',add_smoother=False)
    assert len(p['data'])==5; plt.close(p['figure'])


def test_eye_simulator_columns_seed_duration_blinks_invalid():
    a=gp.simulate_gazepoint_eye_data({'n':120,'seed':1})
    assert len(a)==120
    assert {'time_s','MSTIMER','BPOGX','BPOGY','FPOGX','FPOGY','LPD','RPD','LPV','RPV','fixation_id','in_blink'} <= set(a.columns)
    assert a.BPOGX.between(0,1).all() and a.BPOGY.between(0,1).all()
    b=gp.simulate_gazepoint_eye_data({'n':80,'seed':42}); c=gp.simulate_gazepoint_eye_data({'n':80,'seed':42})
    np.testing.assert_allclose(b.BPOGX,c.BPOGX); np.testing.assert_allclose(b.LPD,c.LPD,equal_nan=True); assert b.in_blink.equals(c.in_blink)
    d=gp.simulate_gazepoint_eye_data({'duration_s':2,'sampling_rate_hz':50,'seed':3}); assert len(d)==100 and d.attrs['sampling_rate_hz']==50 and d.MSTIMER.max()==1980
    blink=gp.simulate_gazepoint_eye_data({'n':600,'sampling_rate_hz':60,'blink_rate_per_min':120,'blink_duration_mean_s':.1,'blink_duration_sd_s':.01,'seed':10}); assert blink.in_blink.any() and blink.LPD.isna().any() and (blink.LPV==0).any()
    inv=gp.simulate_gazepoint_eye_data({'n':200,'seed':12,'include_invalid_gaze':True,'invalid_gaze_prop':.1}); assert (~inv.gaze_valid_simulated).any() and (inv.BPOGX>1).any()


def test_biometric_simulation_ground_truth():
    out=gp.simulate_gazepoint_biometrics(n_seconds=20,sampling_rate=20,scr_onsets=[5,12],seed=1)
    assert len(out['data'])>0 and {'GSR_US','HRP','HR','IBI','TTL0'} <= set(out['data'].columns)
    assert len(out['ground_truth']['scr_events'])==2 and out['overview'].loc[0,'status']=='synthetic_gazepoint_biometrics_created'


def test_new_tranche_validation_paths():
    with pytest.raises(ValueError): gp.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':[np.nan]}))
    with pytest.raises(ValueError): gp.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':[1]*6}),alpha=0)
    with pytest.raises(TypeError): gp.downsample_gazepoint_data(pd.DataFrame({'time':['a'],'x':[1]}),'time','x',interval=1)
    with pytest.raises(ValueError): gp.audit_gazepoint_biometric_sampling(pd.DataFrame({'GSR_US':[1]}))
    with pytest.raises(ValueError): gp.summarise_gazepoint_hrv_features(pd.DataFrame({'HRV':[1,1,1]}))
    with pytest.raises(ValueError): gp.summarise_gazepoint_hrv_features(pd.DataFrame({'IBI':[1,1,1]}),min_ibi_ms=2000,max_ibi_ms=300)
    with pytest.raises(ValueError): gp.summarise_gazepoint_ibi_hrv_windows(pd.DataFrame({'IBI':[1]}),[])
    with pytest.raises(ValueError): gp.recommend_gazepoint_biometric_exclusions(pd.DataFrame({'gsr_usable_pct':[100]}),data_is_window_summary=True)
    with pytest.raises(ValueError): gp.baseline_correct_gazepoint_pupil(pd.DataFrame({'time':[0],'pupil':[3]}),pupil_col='pupil',baseline_window=[0,0])
    with pytest.raises(ValueError): gp.plot_gazepoint_saccade_main_sequence(pd.DataFrame({'amplitude_deg':[0],'peak_velocity_deg_s':[0]}))
    with pytest.raises(ValueError): gp.simulate_gazepoint_biometrics(n_seconds=0)
