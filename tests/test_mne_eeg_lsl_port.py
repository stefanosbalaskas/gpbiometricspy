import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_mne_events_table_dictionary_marker_and_export(tmp_path):
    e=pd.DataFrame({'event_time_s':[1,2,3],'event_label':['stimulus/A','stimulus/B','response']})
    out=gp.prepare_gazepoint_mne_events(e,sampling_rate_hz=100)
    assert out['events'].shape==(3,3) and out['events'][:,0].tolist()==[100,200,300] and out['events'][:,1].tolist()==[0,0,0] and list(out['event_id'].values())==[1,2,3]
    e2=pd.DataFrame({'event_time_s':[1,2],'event_label':['left','right']}); d=gp.prepare_gazepoint_mne_events(e2,sampling_rate_hz=1000,event_id={'left':11,'right':12}); assert d['events'][:,2].tolist()==[11,12]
    c=pd.DataFrame({'time_s':np.arange(0,.6,.1),'TTL0':[0,1,1,0,2,2]}); m=gp.prepare_gazepoint_mne_events(c,marker_cols='TTL0',sampling_rate_hz=10); assert m['table']['event_label'].tolist()==['TTL0','TTL0/2'] and m['events'][:,0].tolist()==[1,4]
    q=tmp_path/'events.txt';gp.prepare_gazepoint_mne_events(e2,sampling_rate_hz=100,export_csv=q); assert q.exists() and np.loadtxt(q).shape==(2,3)
    with pytest.raises(ValueError,match='Repeated'):gp.prepare_gazepoint_mne_events(pd.DataFrame({'event_time_s':[1,1],'event_label':['A','B']}),sampling_rate_hz=100)


def test_mne_input_channels_scaling_and_irregular():
    d=pd.DataFrame({'time_s':[0,.01,.02,.03],'gaze_x':[.2,.3,.4,.5],'pupil_left':[3,3.1,3.2,3.3],'GSR':[5,5.1,5.2,5.3],'TTL0':[0,1,0,0]})
    out=gp.prepare_gazepoint_mne_input(d); assert out['data'].shape==(4,4) and out['channel_info']['channel_type'].tolist()==['eyegaze','pupil','gsr','stim'] and out['info_spec']['sfreq']==pytest.approx(100)
    s=gp.prepare_gazepoint_mne_input(pd.DataFrame({'time_ms':[0,10,20],'PPG':[1,2,3]}),channel_cols='PPG',scale_factors=.001); np.testing.assert_allclose(s['data'][0],[.001,.002,.003])
    irr=pd.DataFrame({'time_ms':[0,10,20,50],'pupil':[3,3.1,3.2,3.3]})
    with pytest.raises(ValueError,match='Irregular'):gp.prepare_gazepoint_mne_input(irr)
    assert gp.prepare_gazepoint_mne_input(irr,irregular='allow')['sampling']['irregular_interval_count']>0
    miss=pd.DataFrame({'time_ms':[0,10,20],'pupil':[3,np.nan,3.2]})
    with pytest.raises(ValueError,match='Non-finite'):gp.prepare_gazepoint_mne_input(miss)
    assert np.isnan(gp.prepare_gazepoint_mne_input(miss,missing='allow')['data'][0,1])


def test_eeg_alignment_offset_linear_and_samples():
    gaze=pd.DataFrame({'time_s':[0,1,2,3],'pupil':[3,3.1,3.2,3.3]});gp_ev=pd.DataFrame({'event_id':['A','B','C'],'event_time_s':[.5,1.5,2.5]});ee=pd.DataFrame({'event_id':['A','B','C'],'event_time_s':[.7,1.7,2.7]})
    out=gp.align_gazepoint_to_eeg(gaze,gp_ev,ee,method='offset'); assert out['mapping']['intercept_s']==pytest.approx(.2) and np.allclose(out['data'].time_eeg_s,gaze.time_s+.2)
    g2=pd.DataFrame({'time_s':range(5)});a=pd.DataFrame({'event_id':list('ABCDE'),'event_time_s':range(5)});b=pd.DataFrame({'event_id':list('ABCDE'),'event_time_s':.1+1.001*np.arange(5)}); lin=gp.align_gazepoint_to_eeg(g2,a,b,method='linear'); assert lin['mapping']['intercept_s']==pytest.approx(.1) and lin['mapping']['slope']==pytest.approx(1.001) and lin['audit']['drift_ppm']==pytest.approx(1000)
    es=pd.DataFrame({'event_id':['A','B','C'],'sample':[10,110,210]});sm=gp.align_gazepoint_to_eeg(pd.DataFrame({'time_s':[0,1,2]}),pd.DataFrame({'event_id':['A','B','C'],'event_time_s':[0,1,2]}),es,eeg_event_sample_col='sample',eeg_sampling_rate_hz=100); assert sm['mapping']['intercept_s']==pytest.approx(.1) and 'time_eeg_s_sample' in sm['data']


def test_methods_and_session_info():
    text=gp.create_gazepoint_eye_methods_text(60,calibration_points=9,screen_resolution=(1920,1080),viewing_distance_cm=60,preprocessing=['blink flagging','short-gap interpolation'],synchronization='TTL markers'); assert '60 Hz' in text and '9-point calibration' in text and '1920 x 1080' in text and 'TTL markers' in text
    assert 'will be recorded' in gp.create_gazepoint_eye_methods_text(60,tense='future')
    info=gp.session_info_gazepoint(packages='pytest',include_loaded=False); assert 'gpbiometrics' in info['packages'].package.tolist() and 'r_version' in info['system'].field.tolist()


def test_lsl_sync_offsets_merge_pyxdf_and_dejitter():
    streams={'gaze':pd.DataFrame({'time_s':[0,1,2],'x':[.2,.3,.4]}),'eeg':pd.DataFrame({'time_s':[.1,1.1,2.1],'eeg':[1,2,3]})};out=gp.sync_gazepoint_signals_via_lsl(streams,reference='gaze',clock_offsets_s={'gaze':0,'eeg':-.1}); np.testing.assert_allclose(out['streams']['eeg']['.lsl_time_relative_s'],[0,1,2])
    streams2={'gaze':pd.DataFrame({'time_s':[0,1,2],'x':[.2,.3,.4]}),'marker':pd.DataFrame({'time_s':[.05,1.05,2.05],'marker':['A','B','C']})};m=gp.sync_gazepoint_signals_via_lsl(streams2,reference='gaze',merge='nearest',tolerance_s=.1); assert m['merged']['marker__marker'].tolist()==['A','B','C'];np.testing.assert_allclose(m['merged']['marker__time_difference_s'],.05)
    pyxdf={'gaze':{'time_stamps':[10,10.1,10.2],'time_series':pd.DataFrame({'x':[.2,.3,.4],'y':[.5,.5,.5]})}};p=gp.sync_gazepoint_signals_via_lsl(pyxdf); assert list(p['streams']['gaze'].columns[:2])==['x','y'];np.testing.assert_allclose(p['streams']['gaze']['.lsl_time_relative_s'],[0,.1,.2])
    dj=gp.sync_gazepoint_signals_via_lsl({'gaze':pd.DataFrame({'time_s':[0,.101,.199,.301],'x':range(4)})},dejitter='linear',nominal_rates_hz=10);np.testing.assert_allclose(np.diff(dj['streams']['gaze']['.lsl_time_corrected_s']),.1)
