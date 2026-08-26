from __future__ import annotations
import numpy as np, pandas as pd, pytest
import gpbiometricspy as gp


def test_biometric_validity_fixtures_and_conservative_hrv():
    df=pd.DataFrame({'USER':np.repeat(['P1','P2'],4),'GSR':[1,2,np.nan,4,2,3,4,5],'HR':[70,71,72,np.nan,80,81,82,83],'HRV':[1,1,0,1,1,1,1,1],'ENGAGEMENT':[50,51,52,53,50,50,50,50]})
    out=gp.summarise_gazepoint_biometric_validity(df,group_cols='USER')
    assert out['overview'].loc[0,'signal_column_count']==3 and out['overview'].loc[0,'validity_flag_column_count']==1
    assert out['overview'].loc[0,'active_signal_count']>=2 and out['overview'].loc[0,'status']=='biometric_signals_available'
    assert {'GSR','HR','ENGAGEMENT'}.issubset(out['signals']['column']) and 'HRV' in out['validity_flags']['column'].tolist()
    assert 'validity/vendor flag' in out['validity_flags'].loc[0,'interpretation_note']
    no=gp.summarise_gazepoint_biometric_validity(pd.DataFrame({'USER':['P1','P2'],'CONDITION':['A','B']}))
    assert no['overview'].loc[0,'status']=='no_biometric_signal_columns_detected' and len(no['signals'])==0
    const=gp.summarise_gazepoint_biometric_validity(pd.DataFrame({'GSR':[1]*4,'HR':[70]*4}))
    assert set(const['signals']['status'])=={'constant_or_low_variability_signal'} and const['overview'].loc[0,'status']=='no_active_biometric_signals_detected'


def test_epoch_scr_vector_and_metadata():
    time=np.arange(0,10.0001,.1); gsr=np.zeros(len(time)); gsr+=np.exp(-((time-5.8)**2)/.02)*.5; gsr+=np.exp(-((time-7.0)**2)/.03)*.3
    out=gp.epoch_gazepoint_scr(pd.DataFrame({'time_s':time,'GSR':gsr}),events=[5],pre=1,post=3,min_amplitude=.05,min_distance_s=.5)
    assert len(out)==1 and out.loc[0,'scr_count']>=1 and out.loc[0,'scr_max_amplitude']>.1 and out.loc[0,'n_samples']>0
    t=np.arange(0,8.0001,.1); eda=np.exp(-((t-3.5)**2)/.02); events=pd.DataFrame({'trial':['T1'],'condition':['A'],'onset':[3]})
    meta=gp.epoch_gazepoint_scr(pd.DataFrame({'time_s':t,'EDA':eda}),events=events,pre=1,post=2,signal_col='EDA',event_time_col='onset',event_id_col='trial',event_group_cols='condition',min_amplitude=.05)
    assert meta.loc[0,'event_id']=='T1' and meta.loc[0,'condition']=='A' and meta.loc[0,'scr_count']>=1


def test_scr_normalization_and_rr_flags():
    x=np.array([1.,2.,3.]); np.testing.assert_allclose(gp.normalize_gazepoint_scr(x,method='percent_max'),[100/3,200/3,100]);np.testing.assert_allclose(gp.normalize_gazepoint_scr(x,method='range'),[0,.5,1]);assert round(np.mean(gp.normalize_gazepoint_scr(x,method='z')),10)==0
    dat=pd.DataFrame({'participant':['P01','P01','P02','P02'],'scr_amplitude':[1,2,10,20]});out=gp.normalize_gazepoint_scr(dat,method='percent_max',group_cols='participant');np.testing.assert_allclose(out['scr_amplitude_normalized'],[50,100,50,100])
    rr=[800,810,790,2500,805,100];assert gp.flag_gazepoint_rr_outliers(rr,method='range',min_rr=300,max_rr=2000).tolist()==[False,False,False,True,False,True]
    filtered=gp.flag_gazepoint_rr_outliers([800,810,790,2500],method='range',return_='filtered');assert np.isnan(filtered[3])
    detail=gp.flag_gazepoint_rr_outliers([800,810,790,2500],method='range',return_='data');assert bool(detail.loc[3,'is_outlier']) and detail.loc[0,'rr_filtered']==800
    robust=gp.flag_gazepoint_rr_outliers([800,805,810,795,1600],method='mad',mad_threshold=3,min_rr=300,max_rr=2000);assert bool(robust[4])


def test_engagement_duration_weighting_scalar_and_groups():
    out=gp.compute_gazepoint_engagement_index([20,60,80,40],time=[0,1,2,3],threshold=50)
    assert out.loc[0,'n_valid']==4 and out.loc[0,'mean_engagement']==50 and out.loc[0,'duration_s']==3 and out.loc[0,'percent_time_above_threshold']>0
    scalar=gp.compute_gazepoint_engagement_index([20,60,80],time=[0,1,2],threshold=50,return_='scalar');assert isinstance(scalar,float)
    grouped=gp.compute_gazepoint_engagement_index([20,60,80,10,90,100],time=[0,1,2,0,1,2],threshold=50,group=['A','A','A','B','B','B']);assert len(grouped)==2 and set(grouped['group'])=={'A','B'} and (grouped['n_valid']==3).all()


def test_missingness_grouping_and_long_gaps():
    dat=pd.DataFrame({'time_s':np.arange(0,.6,.1),'GSR':[1,np.nan,np.nan,1.2,1.3,np.nan],'PPG':[1,1,1,np.nan,1,1]})
    out=gp.summarize_gazepoint_missingness(dat,signal_cols=['GSR','PPG'],time_col='time_s',long_gap_s=.15);gsr=out.query("signal == 'GSR'").iloc[0]
    assert gsr.n_missing==3 and gsr.n_missing_runs==2 and gsr.longest_missing_run_samples>=2 and gsr.n_long_gaps>=1
    grouped=pd.DataFrame({'participant':np.repeat(['P01','P02'],4),'time_s':np.tile(np.arange(0,.4,.1),2),'pupil_left':[1,np.nan,1,1,np.nan,np.nan,2,2]});go=gp.summarize_gazepoint_missingness(grouped,signal_cols='pupil_left',time_col='time_s',group_cols='participant');assert len(go)==2 and go.query("participant == 'P02'")['n_missing'].iloc[0]>go.query("participant == 'P01'")['n_missing'].iloc[0]


def test_detrend_linear_global_and_grouped():
    dat=pd.DataFrame({'time_s':np.arange(1,101),'GSR':2+.5*np.arange(1,101)});out=gp.detrend_gazepoint_signal(dat,signal_col='GSR',time_col='time_s',method='linear');assert abs(np.polyfit(out['time_s'],out['GSR_detrended'],1)[0])<1e-10 and {'GSR_trend','GSR_detrended'}.issubset(out.columns)
    d=pd.DataFrame({'participant':np.repeat(['P01','P02'],10),'time_s':np.tile(np.arange(1,11),2),'signal':np.r_[np.arange(1,11),10+2*np.arange(1,11)]});o=gp.detrend_gazepoint_signal(d,signal_col='signal',time_col='time_s',group_cols='participant',method='linear');
    for p in ['P01','P02']:z=o[o.participant==p];assert abs(np.polyfit(z.time_s,z.signal_detrended,1)[0])<1e-10


def test_frontdoor_audit_dataframe_and_csv(tmp_path):
    dat=pd.DataFrame({'TIME':[0,.1,.2,.3,.3],'GSR_US':[1,np.nan,1.2,1.3,1.3],'PPG':[0,1,0,1,1],'LPD':[3,np.nan,np.nan,3.2,3.2]});dat=pd.concat([dat,dat.iloc[[4]]],ignore_index=True)
    out=gp.audit_gazepoint_biometrics_file(data=dat,expected_modalities=['time','eda','ppg','pupil','gaze'],long_gap_s=.15)
    assert out['dimensions'].loc[0,'n_rows']==len(dat) and ((out['modalities'].modality=='eda')&out['modalities'].present).any() and any('Missing expected modalities' in w for w in out['warnings']) and out['duplicate_rows'].loc[0,'n_duplicate_rows']>=1
    path=tmp_path/'x.csv';pd.DataFrame({'TIME':[0,100,200],'GSR_US':[1,1.1,np.nan],'PPG':[0,1,0]}).to_csv(path,index=False);p=gp.audit_gazepoint_biometrics_file(path=path,expected_modalities=['time','eda','ppg']);assert p['dimensions'].loc[0,'n_rows']==3 and p['modalities'].present.any()


def test_new_family_validation_paths():
    with pytest.raises(ValueError,match='active_min_unique'):gp.summarise_gazepoint_biometric_validity(pd.DataFrame({'GSR':[1,2]}),active_min_unique=0)
    with pytest.raises(ValueError,match='time.*same length'):gp.compute_gazepoint_engagement_index([1,2],[0])
    with pytest.raises(ValueError,match='Supply either'):gp.audit_gazepoint_biometrics_file()
