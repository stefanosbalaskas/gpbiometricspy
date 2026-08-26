import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_exact_standardizer_and_short_alias():
    dat=pd.DataFrame({'TIME':[1,2,3],'LPD':[3,3.1,3.2],'BPOGX':[.1,.2,.3],'BPOGY':[.4,.5,.6],'GSR_US':[1,2,3]})
    out=gp.standardize_gazepoint_column_names(dat)
    assert {'time_s','pupil_left','gaze_x','gaze_y','GSR'}.issubset(out.columns)
    assert isinstance(out.attrs['gazepoint_column_standardization'],pd.DataFrame)
    short=gp.standardize_gazepoint_columns(pd.DataFrame({'TIME':[0,1],'GSR_US':[1,2]}))
    assert len(short)==2
    conflict=pd.DataFrame({'GSR':[1,2],'GSR_US':[3,4]})
    suff=gp.standardize_gazepoint_column_names(conflict)
    assert len(set(suff.columns))==2 and 'GSR' in suff.columns
    with pytest.raises(ValueError,match='conflict'):
        gp.standardize_gazepoint_column_names(conflict,conflict='error')


def test_format_validation_required_optional():
    dat=pd.DataFrame({'time_s':[0,1,2],'GSR':[1,1.1,1.2]})
    out=gp.validate_gazepoint_format(dat,required_cols=['time_s','GSR'],optional_cols=['PPG','pupil_left'])
    assert out['valid'] and not out['missing_required'] and 'PPG' in out['missing_optional'] and out['class'][0]=='gazepoint_format_validation'
    fail=gp.validate_gazepoint_format(dat,required_cols=['time_s','PPG'])
    assert not fail['valid'] and 'PPG' in fail['missing_required']


def test_pupil_interpolation_short_cleaner_gap_threshold_and_errors():
    dat=pd.DataFrame({'time_s':np.arange(0,.6,.1),'pupil_left':[3,np.nan,np.nan,3.3,3.4,3.5],'blink':[False,True,True,False,False,False]})
    out=gp.interpolate_gazepoint_pupil_blinks(dat,pupil_cols='pupil_left',time_col='time_s',blink_col='blink',max_gap_s=.25)
    assert np.isfinite(out.loc[1:2,'pupil_left_interp']).all() and out.loc[1:2,'pupil_left_was_interpolated'].all()
    long=pd.DataFrame({'time_s':np.arange(0,1.1,.1),'pupil_left':[3,*([np.nan]*5),3.6,3.7,3.8,3.9,4.]})
    no=gp.interpolate_gazepoint_pupil_blinks(long,pupil_cols='pupil_left',time_col='time_s',max_gap_s=.20)
    assert no.loc[1:5,'pupil_left_interp'].isna().all() and not no.loc[1:5,'pupil_left_was_interpolated'].any()
    clean=gp.clean_gazepoint_pupil(pd.DataFrame({'time_s':np.arange(0,.5,.1),'pupil_left':[3,np.nan,3.2,3.3,3.4]}),pupil_cols='pupil_left',time_col='time_s',max_gap_s=.20)
    assert np.isfinite(clean.loc[1,'pupil_left_clean'])
    with pytest.raises(ValueError,match='No pupil'):
        gp.interpolate_gazepoint_pupil_blinks(pd.DataFrame({'time_s':[0,1],'x':[1,2]}))


def test_respiration_alias_and_mixed_model_preparation():
    fs=20; time=np.arange(0,90+1/fs,1/fs); ppg=np.sin(2*np.pi*.20*time)
    out=gp.respiration_from_ppg(ppg,sampling_rate_hz=fs)
    assert abs(out['summary'].iloc[0].respiration_rate_bpm-12)<1
    dat=pd.DataFrame({'participant':np.repeat(['P01','P02'],3),'trial':np.tile([1,2,3],2),'condition':np.tile(['A','B','A'],2),
                      'outcome':[1,2,3,2,np.nan,4],'pupil':[3.1,3.2,3.3,3.0,3.1,3.4]})
    mm=gp.prepare_gazepoint_mixed_model_data(dat,outcome_cols='outcome',participant_col='participant',trial_col='trial',condition_cols='condition',numeric_cols='pupil',center_numeric=True,scale_numeric=True)
    assert len(mm)==5 and isinstance(mm.participant.dtype,pd.CategoricalDtype) and isinstance(mm.condition.dtype,pd.CategoricalDtype)
    assert {'pupil_c','pupil_z'}.issubset(mm.columns) and mm.attrs['class'][0]=='gazepoint_mixed_model_data'
