from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
import gpbiometricspy as gp


def pulse_data(fs=100, seconds=20, hz=1.2):
    t=np.arange(0,seconds+1/fs/2,1/fs)
    x=np.sin(2*np.pi*hz*t)**8 + .02*np.sin(2*np.pi*6*t)
    return t,x


def test_input_peak_detection_measures_and_report(tmp_path):
    fs=100;t,x=pulse_data(fs,20)
    d=pd.DataFrame({'participant':'P01','trial':'T01','time_s':t,'pulse':x})
    prep=gp.prepare_gazepoint_heartpy_input(d,'pulse','time_s',['participant','trial'])
    assert len(prep['signal_table'])==len(d) and np.isfinite(prep['sampling_rate_hz'])
    exp=gp.export_gazepoint_heartpy_input(d,'pulse','time_s',['participant'],output_dir=tmp_path)
    assert len(exp['path'])==2 and all(Path(p).exists() for p in exp['path'])
    det=gp.detect_gazepoint_ppg_peaks(d,'pulse','time_s',['participant'],fs,bpm_min=40,bpm_max=140,enhance_peaks=False,lowpass_hz=None,hampel=False,high_precision=False)
    assert isinstance(det['peaks'],pd.DataFrame) and len(det['peaks'])>10
    assert det['peaks']['peak_index'].min()>=1
    rej=gp.reject_gazepoint_ppg_peaks(det['peaks']); assert 'rr_ms' in rej and 'accepted' in rej
    m=gp.compute_gazepoint_ppg_measures(rej);assert {'bpm','ibi_ms','rmssd_ms','lf','hf'}<=set(m)
    rep=gp.create_gazepoint_heartpy_report(det,output_dir=tmp_path,prefix='hp');assert len(rep['path'])==4 and not rep['measures'].empty
    fig=gp.plot_gazepoint_ppg_peak_detection(det);assert hasattr(fig,'savefig');plt.close(fig)


def test_clipping_filter_enhance_hampel_and_scaling():
    fs=100;t,x=pulse_data(fs,5);x=x.copy();x[99:103]=x.max()
    c=gp.reconstruct_gazepoint_ppg_clipping(x);assert len(c['signal'])==len(x) and len(c['clipped'])==len(x)
    assert len(gp.enhance_gazepoint_ppg_peaks(x,fs,1))==len(x)
    assert len(gp.filter_gazepoint_ppg_butterworth(x,5,fs))==len(x)
    assert len(gp.correct_gazepoint_ppg_hampel(x,fs))==len(x)
    for meth in ['zscore','minmax','robust','center','none']:
        assert len(gp.scale_gazepoint_ppg_signal(x,meth))==len(x)
    d=pd.DataFrame({'g':['a']*(len(x)//2)+['b']*(len(x)-len(x)//2),'pulse':x})
    ss=gp.scale_gazepoint_ppg_sections(d,'pulse','g');assert 'ppg_scaled' in ss
    assert np.allclose(gp.flip_gazepoint_ppg_signal([1,2],method='negative'),[-1,-2])
    assert np.allclose(gp.flip_gazepoint_ppg_signal([1,2],method='max_minus'),[1,0])
    assert len(gp.remove_gazepoint_ppg_baseline_wander(x,fs))==len(x)
    assert len(gp.smooth_gazepoint_ppg_signal(x,fs))==len(x)
    for typ,kw in [('lowpass',{'high_hz':5}),('highpass',{'low_hz':.5}),('bandpass',{'low_hz':.5,'high_hz':5}),('notch',{'low_hz':5,'high_hz':7})]:
        assert len(gp.filter_gazepoint_ppg_signal(x,fs,type=typ,**kw))==len(x)


def test_sampling_rr_clean_frequency_breathing_and_quality():
    est=gp.estimate_gazepoint_samplerate_mstimer(np.arange(0,1001,10));assert round(est['sampling_rate_hz'])==100
    dt=pd.date_range('2026-01-01',periods=101,freq='10ms',tz='UTC');est2=gp.estimate_gazepoint_samplerate_datetime(dt);assert round(est2['sampling_rate_hz'])==100
    rr=np.array([800,810,790,805,2000,795,805,800,790,810],float)
    for meth in ['quotient','iqr','modified_z','zscore','none']:
        c=gp.clean_gazepoint_rr_intervals(rr,meth);assert isinstance(c,pd.DataFrame) and 'accepted' in c
    # Preserve strict R IQR semantics when the IQR collapses around a repeated center.
    strict=gp.clean_gazepoint_rr_intervals([833.333333,833.333333,816.666667,833.333333,850.0,833.333333],method='iqr')
    assert (~strict['accepted']).any()
    f=gp.compute_gazepoint_ppg_frequency_measures(rr_ms=np.tile([800,820,790,810],20),method='welch');assert {'lf','hf','total_power'}<=set(f)
    br=gp.estimate_gazepoint_breathing_rate_from_ibi(800+50*np.sin(np.linspace(0,20,40)));assert 'breathing_rate_hz' in br
    q=gp.check_gazepoint_ppg_binary_quality(pd.DataFrame({'group':['all'],'n_peaks':[20],'bpm':[72]}));assert bool(q.loc[0,'quality_pass'])


def test_full_process_segmentwise_plots_and_crosscheck():
    fs=100;t,x=pulse_data(fs,30);d=pd.DataFrame({'participant':'P01','time_s':t,'pulse':x})
    out=gp.process_gazepoint_ppg_heartpy_style(d,'pulse','time_s','participant',fs,high_precision=False)
    for key in ['peaks','measures','frequency','quality']: assert isinstance(out[key],pd.DataFrame)
    # Numeric-vector route is part of the R API.
    det=gp.detect_gazepoint_ppg_peaks(x,sampling_rate_hz=fs,high_precision=False);assert len(det['peaks'])>10
    t2,x2=pulse_data(fs,70);d2=pd.DataFrame({'participant':'P01','time_s':t2,'pulse':x2})
    seg=gp.process_gazepoint_ppg_segmentwise(d2,'pulse','time_s','participant',fs,window_seconds=20,overlap=.5,min_segment_seconds=10,high_precision=False)
    assert len(seg['segments'])>1 and isinstance(seg['measures'],pd.DataFrame)
    figs=[gp.plot_gazepoint_ppg_segmentwise(seg),gp.plot_gazepoint_ppg_poincare(rr_ms=np.tile([800,820,790,810],10)),gp.plot_gazepoint_ppg_breathing(np.tile([800,820,790,810],30))]
    assert all(hasattr(f,'savefig') for f in figs);plt.close('all')
    cc=gp.run_gazepoint_heartpy_crosscheck(d,'pulse','time_s','participant',fs,high_precision=False);assert 'heartpy_available' in cc and 'native' in cc


def test_heartpy_validation_edges(tmp_path):
    with pytest.raises(ValueError): gp.export_gazepoint_heartpy_input(pd.DataFrame({'pulse':[1,2]}),signal_col='pulse',sampling_rate_hz=10)
    with pytest.raises(ValueError): gp.filter_gazepoint_ppg_butterworth([1,2,3],cutoff_hz=6,sampling_rate_hz=10)
    with pytest.raises(ValueError): gp.filter_gazepoint_ppg_signal([1,2,3,4],10,type='bandpass',low_hz=.5)
    with pytest.raises(ValueError): gp.process_gazepoint_ppg_segmentwise(np.arange(100),sampling_rate_hz=10,overlap=1)
    with pytest.raises(ValueError): gp.plot_gazepoint_ppg_poincare(rr_ms=[800,810])
    with pytest.raises(ValueError): gp.plot_gazepoint_ppg_breathing([800,810,820])
    with pytest.raises(ValueError): gp.check_gazepoint_ppg_binary_quality()
    assert gp.check_gazepoint_ppg_binary_quality(pd.DataFrame()).empty
