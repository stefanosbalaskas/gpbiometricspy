import importlib.util
import sys
import types

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.heartpy_style as m


def pulse(fs=50, seconds=8):
    t=np.arange(0,seconds,1/fs); x=np.sin(2*np.pi*1.2*t)**8
    return t,x


def test_helpers_input_inference_and_validation(tmp_path):
    assert np.isnan(m._interp_na([np.nan,1])).sum()==1
    d=pd.DataFrame({'xx_PPG_signal':[1,2,3], 'myTimestamp':[0,.1,.2]})
    assert m._pick_col(d,['PPG'],'signal')=='xx_PPG_signal'
    with pytest.raises(ValueError,match='Could not infer'):
        m._pick_col(pd.DataFrame({'x':[1]}),['PPG'],'signal')
    assert np.allclose(m._running_mean([1,3],5),[2,2])
    with pytest.raises(ValueError,match='Missing group'):
        m._group_indices(pd.DataFrame({'x':[1]}),'g')
    g=m._group_indices(pd.DataFrame({'a':['x','x'],'b':[1,2]}),['a','b'])
    assert set(g)=={'x | 1','x | 2'}

    with pytest.raises(TypeError):m.prepare_gazepoint_heartpy_input([1,2])
    with pytest.raises(ValueError,match='at least one'):m.prepare_gazepoint_heartpy_input(pd.DataFrame())
    with pytest.raises(ValueError,match='signal_col'):m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1]}),signal_col='bad',sampling_rate_hz=10)
    with pytest.raises(ValueError,match='sampling_rate_hz'):
        m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1,2,3]}),signal_col='PPG')
    with pytest.raises(ValueError,match='time_col'):
        m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1,2]}),signal_col='PPG',time_col='bad')
    with pytest.raises(ValueError,match='numeric time'):
        m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1,2],'time':['x','y']}),signal_col='PPG',time_col='time')
    no_time=m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1,np.nan,3]}),signal_col='PPG',sampling_rate_hz=10)
    assert no_time['signal_table'].time_s.tolist()==[0,.1,.2]
    out=m.prepare_gazepoint_heartpy_input(pd.DataFrame({'PPG':[1,2,3],'other_time':[0,.1,.2],'g':['a']*3}),group_cols='g',output_dir=tmp_path)
    assert len(out['path'])==2


def test_peak_roi_replacement_and_high_precision_fallbacks(monkeypatch):
    x=np.array([0,2,3,0,0,4,5,0.],float)
    # nearby second ROI replaces the first when it has a higher maximum
    p=m._peak_rois(x,1,5)
    assert p.tolist()==[6]
    t=np.arange(5,dtype=float)
    assert m._high_precision(np.arange(5.),t,0)[0]==0

    class BadSpline:
        def __init__(self,*a,**k):raise RuntimeError('bad')
    monkeypatch.setattr(m.interpolate,'CubicSpline',BadSpline)
    pt,val=m._high_precision(np.array([0,1,2,1,0.]),np.array([0,.1,.2,.3,.4]),2,window_s=.3)
    assert pt==.2 and val==2


def test_measures_short_group_and_scaling_errors():
    p=pd.DataFrame({'peak_time_s':[0,1], 'group':['g','g']})
    out=m.compute_gazepoint_ppg_measures(p)
    assert out.n_peaks.iloc[0]==2 and np.isnan(out.bpm.iloc[0])
    with pytest.raises(ValueError,match='peak_time_s'):
        m.compute_gazepoint_ppg_measures(pd.DataFrame({'x':[1]}))

    assert np.isnan(m.scale_gazepoint_ppg_signal([1,1],'zscore')).all()
    assert np.isnan(m.scale_gazepoint_ppg_signal([1,1],'robust')).all()
    assert np.isnan(m.scale_gazepoint_ppg_signal([1,1],'minmax')).all()
    with pytest.raises(ValueError,match='Invalid scaling'):m.scale_gazepoint_ppg_signal([1,2],'bad')
    with pytest.raises(ValueError,match='signal_col'):m.scale_gazepoint_ppg_sections(pd.DataFrame({'x':[1]}),signal_col='bad')
    with pytest.raises(ValueError,match='Missing section'):m.scale_gazepoint_ppg_sections(pd.DataFrame({'PPG':[1,2]}),'PPG','g')
    assert len(m.scale_gazepoint_ppg_sections([1,2,3],method='center'))==3
    with pytest.raises(ValueError,match='Invalid flip'):m.flip_gazepoint_ppg_signal([1,2],'bad')


def test_crosscheck_available_success_and_error(monkeypatch):
    t,x=pulse()
    d=pd.DataFrame({'time_s':t,'PPG':x})
    monkeypatch.setattr(importlib.util,'find_spec',lambda name:object())
    fake=types.ModuleType('heartpy')
    fake.process=lambda sig,fs,report_time=False:({'peaklist':[1]}, {'bpm':70})
    monkeypatch.setitem(sys.modules,'heartpy',fake)
    o=m.run_gazepoint_heartpy_crosscheck(d,'PPG','time_s',sampling_rate_hz=50,high_precision=False)
    assert o['heartpy']['measures']['bpm']==70
    fake.process=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('boom'))
    o2=m.run_gazepoint_heartpy_crosscheck(d,'PPG','time_s',sampling_rate_hz=50,high_precision=False)
    assert 'boom' in o2['heartpy']['error']


def test_filter_baseline_smooth_and_quality_from_peaks():
    with pytest.raises(ValueError):m.remove_gazepoint_ppg_baseline_wander([1,2],0)
    with pytest.raises(ValueError):m.smooth_gazepoint_ppg_signal([1,2],0)
    assert len(m.remove_gazepoint_ppg_baseline_wander([1,2,3,4],10,method='mean'))==4
    assert len(m.smooth_gazepoint_ppg_signal([1,2,3,4],10,method='median'))==4
    with pytest.raises(ValueError,match='Invalid sampling'):m.filter_gazepoint_ppg_signal([1,2],0)
    with pytest.raises(ValueError,match='bandpass'):m.filter_gazepoint_ppg_signal([1,2,3,4],10,'bandpass',low_hz=1)
    with pytest.raises(ValueError,match='notch'):m.filter_gazepoint_ppg_signal([1,2,3,4],10,'notch',low_hz=1)
    with pytest.raises(ValueError,match='Invalid filter'):m.filter_gazepoint_ppg_signal([1,2,3,4],10,'bad')

    peaks=pd.DataFrame({'peak_time_s':[0,1,2,3,4,5]})
    q=m.check_gazepoint_ppg_binary_quality(peaks=peaks,min_peaks=3)
    assert 'quality_pass' in q


def test_samplerates_degenerate_and_segmentwise_numeric_error(monkeypatch):
    assert np.isnan(m.estimate_gazepoint_samplerate_mstimer([1])['sampling_rate_hz'])
    assert np.isnan(m.estimate_gazepoint_samplerate_mstimer([1,1])['sampling_rate_hz'])
    assert np.isnan(m.estimate_gazepoint_samplerate_datetime(['bad'])['sampling_rate_hz'])
    assert np.isnan(m.estimate_gazepoint_samplerate_datetime(['2026-01-01','2026-01-01'])['sampling_rate_hz'])

    arr=np.sin(np.linspace(0,20,300))
    out=m.process_gazepoint_ppg_segmentwise(arr,sampling_rate_hz=10,window_seconds=10,min_segment_seconds=100,high_precision=False)
    assert out['segments'].empty

    t,x=pulse(20,12);d=pd.DataFrame({'time_s':t,'PPG':x})
    monkeypatch.setattr(m,'detect_gazepoint_ppg_peaks',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('segment boom')))
    er=m.process_gazepoint_ppg_segmentwise(d,'PPG','time_s',sampling_rate_hz=20,window_seconds=10,min_segment_seconds=5)
    assert er['segments'].status.iloc[0]=='error'

def test_frequency_fft_branch():
    rr=800+40*np.sin(np.linspace(0,8*np.pi,80))
    out=m.compute_gazepoint_ppg_frequency_measures(rr_ms=rr,method='fft')
    assert out.method.iloc[0]=='fft'
