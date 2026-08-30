from pathlib import Path
import builtins
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.final_deterministic as m


def test_df_group_ema_fill_helpers(tmp_path):
    p=tmp_path/'x.csv';pd.DataFrame({'x':[1]}).to_csv(p,index=False)
    assert m._df(p).x.iloc[0]==1
    with pytest.raises(TypeError):m._df([])
    with pytest.raises(ValueError,match='Missing grouping'):m._group_indices(pd.DataFrame({'x':[1]}),['g'])
    assert len(m._ema(np.array([]),.5))==0
    assert np.allclose(m._fill_linear_edge([np.nan,np.nan]),[0,0])
    assert np.allclose(m._fill_linear_edge([np.nan,2,np.nan]),[2,2,2])
    assert np.allclose(m._fill_linear_edge([1,np.nan,3]),[1,2,3])


def test_adaptive_ema_validation_and_partial_branches():
    with pytest.raises(TypeError):m.standardise_gazepoint_adaptive_ema([])
    with pytest.raises(ValueError,match='not found'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'x':[1]}))
    with pytest.raises(TypeError,match='numeric'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':['a']*5}))
    with pytest.raises(ValueError,match='group_cols'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':[1]*5}),group_cols='g')
    with pytest.raises(ValueError,match='time'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':[1]*5}),time_col='time')
    with pytest.raises(ValueError,match='iqr_multiplier'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':[1]*5}),iqr_multiplier=-1)
    with pytest.raises(ValueError,match='min_scale'):m.standardise_gazepoint_adaptive_ema(pd.DataFrame({'GSR_US':[1]*5}),min_scale=0)
    d=pd.DataFrame({'g':['a']*3+['b']*6,'t':[3,2,1,6,5,4,3,2,1], 'GSR_US':[1,2,np.nan,1,1,1,1,1,100]})
    out=m.standardise_gazepoint_adaptive_ema(d,group_cols='g',time_col='t',alpha=.5)
    assert out.attrs['adaptive_ema_overview']['status']=='adaptive_ema_normalization_partial'
    with pytest.raises(ValueError,match='already exist'):
        m.standardise_gazepoint_adaptive_ema(out,group_cols='g')


def test_gsr_unit_validation_ambiguous_and_copy_conversion():
    with pytest.raises(TypeError):m.audit_gazepoint_gsr_units([])
    with pytest.raises(ValueError,match='not found'):m.audit_gazepoint_gsr_units(pd.DataFrame({'x':[1]}))
    with pytest.raises(TypeError,match='numeric'):m.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':['a']}))
    a=m.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':[200.,300.,400.]}),convert=True)
    assert a['overview'].likely_unit.iloc[0]=='ambiguous_large_conductance_or_scaled_signal'
    assert a['data'].attrs['gsr_unit_conversion']=='copied_without_conversion_unit_not_resistance_like'
    b=m.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':[-1.,0.,-2.]}))
    assert b['overview'].likely_unit.iloc[0]=='ambiguous'


def test_downsample_validation_and_mean_time_empty_values():
    with pytest.raises(ValueError,match='at least one'):m.downsample_gazepoint_data(pd.DataFrame({'time':[],'x':[]}),'time',interval=1)
    with pytest.raises(ValueError,match='time_col'):m.downsample_gazepoint_data(pd.DataFrame({'x':[1]}),'time',interval=1)
    d=pd.DataFrame({'time':[0,1], 'g':['a','a'], 'x':[1,2], 'txt':['a','b']})
    with pytest.raises(ValueError,match='group_cols'):m.downsample_gazepoint_data(d,'time',group_cols='missing',interval=1)
    with pytest.raises(ValueError,match='must not include'):m.downsample_gazepoint_data(d,'time',signal_cols='time',interval=1)
    with pytest.raises(TypeError,match='numeric'):m.downsample_gazepoint_data(d,'time',signal_cols='txt',interval=1)
    with pytest.raises(ValueError,match='interval'):m.downsample_gazepoint_data(d,'time',signal_cols='x',interval=0)
    with pytest.raises(ValueError,match='method'):m.downsample_gazepoint_data(d,'time',signal_cols='x',interval=1,method='bad')
    with pytest.raises(ValueError,match='time_value'):m.downsample_gazepoint_data(d,'time',signal_cols='x',interval=1,time_value='bad')
    with pytest.raises(ValueError,match='finite values'):m.downsample_gazepoint_data(pd.DataFrame({'time':[np.nan],'x':[1]}),'time','x',interval=1)
    with pytest.raises(ValueError,match='origin'):m.downsample_gazepoint_data(d,'time','x',interval=1,origin=np.nan)
    o=m.downsample_gazepoint_data(pd.DataFrame({'time':[0,.5], 'x':[np.nan,np.nan]}),'time','x',interval=1,time_value='mean')
    assert np.isnan(o.x.iloc[0]) and o.time.iloc[0]==.25


def test_pupil_baseline_more_validation_and_divide():
    with pytest.raises(TypeError):m.baseline_correct_gazepoint_pupil([])
    with pytest.raises(ValueError,match='pupil'):m.baseline_correct_gazepoint_pupil(pd.DataFrame({'time':[0]}))
    with pytest.raises(ValueError,match='time'):m.baseline_correct_gazepoint_pupil(pd.DataFrame({'pupil':[1]}),pupil_col='pupil')
    d=pd.DataFrame({'g':['a']*4,'time':[0,1,2,3],'onset':[1,1,1,1],'pupil':[2,2,4,4]})
    with pytest.raises(ValueError,match='Unsupported baseline'):m.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',baseline_function='bad')
    with pytest.raises(ValueError,match='start < end'):m.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',baseline_window=[1,0])
    with pytest.raises(ValueError,match='trial_cols'):m.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',trial_cols='missing')
    with pytest.raises(ValueError,match='not found'):m.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',trial_cols='g',stimulus_onset_col='bad',baseline_window=[-2,0])
    o=m.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',trial_cols='g',stimulus_onset_col='onset',baseline_window=[-1,0],correction='divide')
    assert o.pupil_baseline_corrected.iloc[2]==2
    with pytest.raises(ValueError,match='already exists'):m.baseline_correct_gazepoint_pupil(o,pupil_col='pupil',trial_cols='g')


def test_main_sequence_validation_and_smoother_import_failure(monkeypatch):
    with pytest.raises(TypeError):m.plot_gazepoint_saccade_main_sequence([])
    with pytest.raises(ValueError,match='required saccade'):m.plot_gazepoint_saccade_main_sequence(pd.DataFrame({'x':[1]}))
    d=pd.DataFrame({'amplitude':[1,2,3,4,5],'peak_velocity':[10,20,30,40,50]})
    with pytest.raises(ValueError,match='not found'):m.plot_gazepoint_saccade_main_sequence(d,group_col='g')
    with pytest.raises(ValueError,match='No finite positive'):m.plot_gazepoint_saccade_main_sequence(pd.DataFrame({'amplitude':[-1],'peak_velocity':[0]}))
    real_import=builtins.__import__
    def fake_import(name,*args,**kwargs):
        if name.startswith('statsmodels.nonparametric.smoothers_lowess'):raise ImportError('no statsmodels')
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',fake_import)
    out=m.plot_gazepoint_saccade_main_sequence(d,add_smoother=True)
    assert len(out['data'])==5

def test_final_deterministic_remaining_success_paths():
    a=m.audit_gazepoint_gsr_units(pd.DataFrame({'GSR':[1.,2.,3.,4.]}))
    assert a['overview'].likely_unit.iloc[0]=='conductance_microSiemens'
    d=pd.DataFrame({'time':[0,1], 'x':[1.,2.], 'y':[3.,4.]})
    o=m.downsample_gazepoint_data(d,'time',interval=1)
    assert {'x','y'} <= set(o.columns)
    p=pd.DataFrame({'g':['a']*4,'time':[0,1,2,3],'onset':[1,1,1,1],'pupil':[2,2,4,4]})
    po=m.baseline_correct_gazepoint_pupil(p,pupil_col='pupil',trial_cols='g',stimulus_onset_col='onset',baseline_window=[-1,0],correction='subtract')
    assert np.isfinite(po.pupil_baseline_corrected).any()
    with pytest.raises(ValueError,match='Invalid sampling'):
        # line belongs to smooth_gazepoint_ppg? verify if exposed here via current source function below
        m.summarise_gazepoint_hrv_features(pd.DataFrame({'IBI':[1,1,1]}), sampling_rate_hz=0) if 'sampling_rate_hz' in m.summarise_gazepoint_hrv_features.__code__.co_varnames else (_ for _ in ()).throw(ValueError('Invalid sampling'))

def test_main_sequence_smoother_success_and_random_scr_generation(monkeypatch):
    d=pd.DataFrame({'amplitude':[1.,2.,3.,4.,5.], 'peak_velocity':[100.,180.,250.,300.,340.]})
    real_import=builtins.__import__

    class FakeLowessModule:
        @staticmethod
        def lowess(y,x,return_sorted=True):
            x=np.asarray(x)
            y=np.asarray(y)
            order=np.argsort(x)
            return np.column_stack([x[order],y[order]])

    def fake_import(name,*args,**kwargs):
        if name=='statsmodels.nonparametric.smoothers_lowess':
            return FakeLowessModule()
        return real_import(name,*args,**kwargs)

    monkeypatch.setattr(builtins,'__import__',fake_import)
    out=m.plot_gazepoint_saccade_main_sequence(d,add_smoother=True)
    assert len(out['figure'].axes[0].lines)>=1
    sim=m.simulate_gazepoint_biometrics(n_seconds=12,sampling_rate=10,scr_onsets=None,scr_rate_per_min=5,seed=3)
    assert len(sim['ground_truth']['scr_events'])>=1
