import matplotlib.figure
import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def _summary_data():
    return pd.DataFrame({'participant':['P1','P1','P1','P1','P2','P2'],'MEDIA_ID':[1]*6,'AOI':['claim','claim','logo','logo','claim','logo'],'GSR_US':[1,2,3,4,5,6],'HR':[70,72,74,76,78,80]})


def test_aoi_biometric_summary_and_filter_low_rows_empty():
    r=gp.summarise_gazepoint_aoi_biometrics(_summary_data(),signal_cols=['GSR_US','HR'],group_cols=['participant','MEDIA_ID'],min_rows=1)
    assert r['overview'].iloc[0].signal_count==2 and len(r['summary'])>0 and {'mean_value','median_value','signal','aoi_label'}.issubset(r['summary'].columns)
    dat=pd.DataFrame({'participant':'P1','AOI':['claim','claim','logo'],'GSR_US':[1,2,3]})
    f=gp.summarise_gazepoint_aoi_biometrics(dat,signal_cols='GSR_US',group_cols='participant',valid_aoi_values='claim')
    assert set(f['summary'].aoi_label)=={'claim'} and f['overview'].iloc[0].aoi_count==1
    low=gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({'participant':'P1','AOI':['claim','logo'],'GSR_US':[1,2]}),signal_cols='GSR_US',group_cols='participant',min_rows=2)
    assert low['overview'].iloc[0].status=='warn_low_rows_in_some_summaries' and (low['summary'].summary_status=='warn_low_rows').any()
    empty=gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({'participant':'P1','AOI':[np.nan,''],'GSR_US':[1,2]}),signal_cols='GSR_US',group_cols='participant')
    assert empty['overview'].iloc[0].status=='fail_no_aoi_rows' and empty['summary'].empty


def test_model_data_standardization_modes_and_filter():
    dat=pd.DataFrame({'participant':['P1','P1','P2','P2'],'AOI':['claim','logo','claim','logo'],'GSR_US':[1,2,3,4],'HR':[70,72,74,76]})
    s=gp.summarise_gazepoint_aoi_biometrics(dat,signal_cols=['GSR_US','HR'],group_cols='participant')
    m=gp.prepare_gazepoint_aoi_biometrics_model_data(s,outcome_col='mean_value',predictor_cols=['aoi_label','signal'],factor_cols=['aoi_label','signal'],group_cols='participant',standardise_outcome=True,standardise_within='signal')
    assert m['overview'].iloc[0].status=='aoi_biometrics_model_data_prepared' and m['overview'].iloc[0].standardise_within=='signal'
    assert 'mean_value_z' in m['model_data'] and str(m['model_data'].aoi_label.dtype)=='category'
    means=m['model_data'].groupby('signal',observed=False).mean_value_z.mean(); assert (np.abs(means)<1e-10).all()
    allm=gp.prepare_gazepoint_aoi_biometrics_model_data(s,standardise_outcome=True,standardise_within='all')
    assert abs(allm['model_data'].mean_value_z.mean())<1e-10
    s2=gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({'participant':'P1','AOI':['claim','claim','logo'],'GSR_US':[1,2,3]}),signal_cols='GSR_US',group_cols='participant')
    filt=gp.prepare_gazepoint_aoi_biometrics_model_data(s2,predictor_cols='aoi_label',min_rows=2)
    assert (filt['model_data'].n_rows>=2).all()


def test_aoi_plot_and_validation():
    dat=pd.DataFrame({'participant':['P1','P1','P2','P2'],'AOI':['claim','logo','claim','logo'],'GSR_US':[1,2,3,4],'HR':[70,72,74,76]})
    s=gp.summarise_gazepoint_aoi_biometrics(dat,signal_cols=['GSR_US','HR'],group_cols='participant')
    fig=gp.plot_gazepoint_aoi_biometrics(s,value_col='mean_value',plot_type='point',group_col='participant')
    assert isinstance(fig,matplotlib.figure.Figure) and isinstance(fig.plot_data,pd.DataFrame)
    m=gp.prepare_gazepoint_aoi_biometrics_model_data(s,standardise_outcome=True,standardise_within='signal')
    fig2=gp.plot_gazepoint_aoi_biometrics(m,value_col='mean_value_z',plot_type='boxplot'); assert isinstance(fig2,matplotlib.figure.Figure)
    with pytest.raises(ValueError,match='aoi_col'): gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({'AOI':['claim'],'GSR_US':[1]}),aoi_col='missing')
    with pytest.raises(ValueError,match='signal_cols'): gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({'AOI':['claim'],'GSR_US':[1]}),signal_cols='missing')
    with pytest.raises(ValueError,match='outcome_col'): gp.prepare_gazepoint_aoi_biometrics_model_data(pd.DataFrame({'mean_value':[1]}),outcome_col='missing')
    with pytest.raises(ValueError,match='requires a `signal` column'): gp.prepare_gazepoint_aoi_biometrics_model_data(pd.DataFrame({'aoi_label':['claim'],'mean_value':[1]}),standardise_outcome=True,standardise_within='signal')
    with pytest.raises(ValueError,match='Required plotting columns'): gp.plot_gazepoint_aoi_biometrics(pd.DataFrame({'AOI':['claim'],'GSR_US':[1]}),value_col='missing')
