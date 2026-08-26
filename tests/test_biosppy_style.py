import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_biosppy_input_numeric_and_grouped():
    out=gp.prepare_gazepoint_biosppy_input([1,1.1,1.2,1.15],signal_type='eda',sampling_rate_hz=10)
    assert np.allclose(out['vectors']['all'],[1,1.1,1.2,1.15])
    assert out['sampling_rates_hz']['all']==pytest.approx(10)
    assert np.allclose(out['samples']['time_s'],[0,.1,.2,.3]) and out['settings']['signal_type']=='eda'
    d=pd.DataFrame({'participant':['P01']*4+['P02']*4,'time_s':[0,.02,.04,.06]*2,'HRP':[1,2,3,2,2,3,4,3]})
    p=gp.prepare_gazepoint_biosppy_input(d,signal_type='ppg',group_cols='participant')
    assert list(p['vectors'])==['P01','P02'] and np.allclose(list(p['sampling_rates_hz']),[50,50])
    assert p['manifest']['participant'].tolist()==['P01','P02']


def test_biosppy_input_missing_segments_irregular_and_files(tmp_path):
    d=pd.DataFrame({'time_s':[0,1,2,3],'EDA':[1,np.nan,3,4]})
    out=gp.prepare_gazepoint_biosppy_input(d,signal_type='eda',missing='interpolate')
    assert np.allclose(out['vectors']['all'],[1,2,3,4]) and out['samples']['interpolated'].tolist()==[False,True,False,False]
    with pytest.raises(ValueError,match='Non-finite signal'):gp.prepare_gazepoint_biosppy_input(d,signal_type='eda',missing='error')
    seg=gp.prepare_gazepoint_biosppy_input(pd.DataFrame({'time_s':range(9),'EDA':[1,2,3,np.nan,4,5,6,7,np.nan]}),signal_type='eda',missing='segments',min_segment_samples=3)
    assert list(seg['vectors'])==['all__segment_001','all__segment_002']
    irr=pd.DataFrame({'time_s':[0,.1,.2,.5],'EDA':[1,2,3,4]})
    with pytest.raises(ValueError,match='Irregular sampling'):gp.prepare_gazepoint_biosppy_input(irr,signal_type='eda')
    allow=gp.prepare_gazepoint_biosppy_input(irr,signal_type='eda',irregular='allow'); assert allow['manifest'].iloc[0].irregular_intervals_in_group==1
    g=pd.DataFrame({'participant':['P01']*3+['P02']*3,'time_s':[0,.1,.2]*2,'EDA':[1,1.1,1.2,2,2.1,2.2]})
    files=gp.prepare_gazepoint_biosppy_input(g,signal_type='eda',group_cols='participant',output_dir=tmp_path,prefix='study')['files']
    assert len(files)==3 and all(pd.Series(files.path).map(lambda x: __import__('pathlib').Path(x).exists()))


def test_biosppy_eda_family():
    fs=50;t=np.arange(0,30+1/fs/2,1/fs);eda=1+.01*t+.4*np.exp(-((t-8)**2)/.8)+.3*np.exp(-((t-18)**2))
    d=pd.DataFrame({'participant':'P01','time_s':t,'gsr':eda})
    ev=gp.extract_gazepoint_eda_events_biosppy_style(d,'gsr','time_s','participant',fs,min_amplitude=.02)
    assert isinstance(ev,pd.DataFrame) and {'onset_index','peak_index','amplitude'}<=set(ev)
    rec=gp.estimate_gazepoint_eda_recovery_times(d,ev,'gsr','time_s','participant',fs); assert isinstance(rec,pd.DataFrame)
    out=gp.run_gazepoint_biosppy_eda(d,'gsr','time_s','participant',fs); assert {'eda_tonic','eda_phasic'}<=set(out['signal']) and len(out['summary'])==1


def test_biosppy_ppg_family():
    fs=100;t=np.arange(0,20+1/fs/2,1/fs);ppg=np.sin(2*np.pi*1.2*t)**8+.02*np.sin(2*np.pi*6*t)
    d=pd.DataFrame({'participant':'P01','time_s':t,'ppg':ppg})
    out=gp.run_gazepoint_biosppy_ppg(d,'ppg','time_s','participant',fs)
    assert isinstance(out['peaks'],pd.DataFrame) and len(out['peaks'])>10 and out['peaks'].peak_index.min()>=1
    temp=gp.extract_gazepoint_ppg_templates(d,'ppg','time_s',out['peaks'],'participant',fs); assert temp['templates'].ndim==2
    on=gp.detect_gazepoint_ppg_onsets(d,'ppg','time_s',out['peaks'],'participant',fs); assert isinstance(on,pd.DataFrame)


def test_biosppy_rri_helpers():
    r=[800,810,790,805,2000,795,805,800,790,810]
    d=gp.detrend_gazepoint_rri_window(r,window_seconds=5); assert 'rri_detrended_ms' in d
    c=gp.correct_gazepoint_rri_artifacts_local(r,method='local_median'); assert c.artifact.any() and 'rri_corrected_ms' in c
    q=gp.correct_gazepoint_rri_artifacts_local(r,method='quotient',replacement='interpolate'); assert len(q)==len(r)


def test_biosppy_generic_signal_helpers():
    fs=100;t=np.arange(0,10+1/fs/2,1/fs);x=np.sin(2*np.pi*1.5*t);y=np.sin(2*np.pi*1.5*t+np.pi/6)
    psd=gp.compute_gazepoint_signal_power_spectrum(x,fs); assert {'frequency_hz','power'}<=set(psd)
    bp=gp.compute_gazepoint_signal_band_power(psd,bands={'alpha':(1,2)}); assert bp.iloc[0].power>0
    plv=gp.compute_gazepoint_signal_phase_locking(x,y,fs,band=(1,2)); assert np.isfinite(plv.iloc[0].phase_locking_value)
    cc=gp.compute_gazepoint_signal_correlation(x,y,lag_max=20); assert 'correlation' in cc and np.isfinite(cc.iloc[0].best_lag_correlation)


def test_biosppy_input_validation_and_short_psd():
    with pytest.raises(ValueError):gp.prepare_gazepoint_biosppy_input([],signal_type='eda',sampling_rate_hz=10)
    with pytest.raises(ValueError):gp.prepare_gazepoint_biosppy_input([1,2,3],sampling_rate_hz=10)
    with pytest.raises(ValueError):gp.prepare_gazepoint_biosppy_input([1,2,3],signal_type='eda')
    with pytest.raises(TypeError):gp.prepare_gazepoint_biosppy_input(pd.DataFrame({'time_s':[0,1,2],'EDA':['1','2','3']}),signal_type='eda')
    assert gp.compute_gazepoint_signal_power_spectrum([1,2,3],10).empty
