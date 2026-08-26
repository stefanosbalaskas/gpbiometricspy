from __future__ import annotations
import numpy as np, pandas as pd, pytest
import gpbiometricspy as gp


def test_zscore_and_range_correction_fixtures():
    dat=pd.DataFrame({'source_participant':np.repeat(['p1','p2'],5),'SCR_Amplitude':[1,2,3,4,5,10,20,30,40,50]})
    out=gp.standardise_gazepoint_zscore(dat);assert 'SCR_Amplitude_Z' in out
    for p in ['p1','p2']:
        x=out.loc[out.source_participant==p,'SCR_Amplitude_Z'];assert abs(x.mean())<1e-10 and abs(x.std(ddof=1)-1)<1e-10
    dat2=pd.DataFrame({'source_participant':np.repeat(['p1','p2'],3),'SCR_Amplitude':[1,2,3,10,20,30]});r=gp.standardise_gazepoint_range_correction(dat2,signal_col='SCR_Amplitude');np.testing.assert_allclose(r.query("source_participant == 'p1'")['SCR_Amplitude_Range_Corrected'],[0,.5,1]);np.testing.assert_allclose(r.query("source_participant == 'p2'")['SCR_Amplitude_Range_Corrected'],[0,.5,1]);assert r.attrs['range_correction_summary'].loc[0,'status']=='range_correction_complete'
    zero=gp.standardise_gazepoint_range_correction(pd.DataFrame({'source_participant':['p1']*4,'SCR_Amplitude':[1]*4}),signal_col='SCR_Amplitude');assert zero['SCR_Amplitude_Range_Corrected'].isna().all() and zero.attrs['range_correction_summary'].loc[0,'status']=='range_correction_failed'
    np.testing.assert_allclose(gp.standardize_gazepoint_range_correction(dat2,signal_col='SCR_Amplitude')['SCR_Amplitude_Range_Corrected'],r['SCR_Amplitude_Range_Corrected'])


def test_quality_audits_exact_counts_ranges_and_fallback():
    g=gp.audit_gazepoint_gsr_quality(pd.DataFrame({'GSR_US':[2,2.1,2.2,np.nan,0],'GSRV':[1,1,1,0,0]})).iloc[0];assert g.signal=='gsr_eda' and g.value_column=='GSR_US' and g.n_rows==5 and g.missing_rows==1 and g.zero_rows==1 and g.usable_rows==3
    gf=gp.audit_gazepoint_gsr_quality(pd.DataFrame({'GSR':[500000,510000,520000],'GSRV':[1,1,1]}),min_value=1,max_value=1_000_000).iloc[0];assert gf.value_column=='GSR' and gf.usable_rows==3
    h=gp.audit_gazepoint_hr_quality(pd.DataFrame({'HR':[75,76,300,0,np.nan],'HRV':[1,1,1,0,0]})).iloc[0];assert h.signal=='heart_rate' and h.high_rows==1 and h.zero_rows==1 and h.missing_rows==1 and h.usable_rows==2
    hj=gp.audit_gazepoint_hr_quality(pd.DataFrame({'HR':[75,76,130,131],'HRV':[1,1,1,1]}),jump_threshold=25).iloc[0];assert hj.large_jump_rows==1
    d=gp.audit_gazepoint_engagement_dial(pd.DataFrame({'DIAL':[.1,.2,1.2,0,np.nan],'DIALV':[1,1,1,0,0]})).iloc[0];assert d.high_rows==1 and d.zero_rows==1 and d.missing_rows==1 and d.usable_rows==2
    empty=gp.audit_gazepoint_hr_quality(pd.DataFrame({'X':[1,2,3]})).iloc[0];assert empty.issue=='value_column_missing' and empty.usable_rows==0


def test_quality_usable_values_exclude_inactive_zero():
    dat=pd.DataFrame({'GSR_US':[0,2,4],'GSRV':[0,1,1],'HR':[0,70,80],'HRV':[0,1,1]});g=gp.audit_gazepoint_gsr_quality(dat).iloc[0];h=gp.audit_gazepoint_hr_quality(dat).iloc[0];assert g.usable_rows==2 and g.min_value==2 and g.max_value==4 and g.mean_value==3;assert h.usable_rows==2 and h.min_value==70 and h.max_value==80 and h.mean_value==75


def test_window_summaries_r_fixtures():
    dat=pd.DataFrame({'USER':['U1','U1','U2','U2'],'MEDIA_ID':[1,1,1,1],'GSR_US':[2,2.4,1,1.2],'GSRV':[1,1,1,1]});g=gp.summarise_gazepoint_gsr_windows(dat,group_columns=['USER','MEDIA_ID']);u=g[g.USER=='U1'].iloc[0];assert len(g)==2 and u.usable_rows==2 and abs(u.mean_value-2.2)<1e-8 and abs(u.change_value-.4)<1e-8
    h=gp.summarise_gazepoint_hr_windows(pd.DataFrame({'USER':['U1']*4,'HR':[70,72,0,90],'HRV':[1,1,0,0]}),group_columns='USER').iloc[0];assert h.usable_rows==2 and h.mean_value==71 and h.zero_rows==1
    d=gp.summarise_gazepoint_engagement_windows(pd.DataFrame({'USER':['U1']*3,'DIAL':[0,.5,1],'DIALV':[1,1,1]}),group_columns='USER').iloc[0];assert d.usable_rows==3 and d.mean_value==.5
    ug=gp.summarise_gazepoint_gsr_windows(pd.DataFrame({'GSR_US':[2,2.2,2.4],'GSRV':[1,1,1]}));assert len(ug)==1 and ug.loc[0,'window']=='all' and abs(ug.loc[0,'mean_value']-2.2)<1e-8


def test_multimodal_window_merge_and_validation():
    dat=pd.DataFrame({'USER':['U1','U1','U2','U2'],'MEDIA_ID':[1,1,1,1],'GSR_US':[2,2.4,1,1.2],'GSRV':[1,1,1,1],'HR':[70,72,80,82],'HRV':[1,1,1,1],'DIAL':[.1,.2,.3,.4],'DIALV':[1,1,1,1]});out=gp.summarise_gazepoint_multimodal_windows(dat,group_columns=['USER','MEDIA_ID']);assert len(out)==2 and {'gsr_mean_value','hr_mean_value','dial_mean_value'}.issubset(out.columns);u=out[out.USER=='U1'].iloc[0];assert abs(u.gsr_mean_value-2.2)<1e-8 and u.hr_mean_value==71 and abs(u.dial_mean_value-.15)<1e-8
    with pytest.raises(ValueError,match='group_columns'):gp.summarise_gazepoint_gsr_windows(pd.DataFrame({'GSR_US':[2,2.2],'GSRV':[1,1]}),group_columns='USER')
