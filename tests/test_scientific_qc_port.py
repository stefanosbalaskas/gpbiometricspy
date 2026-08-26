import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_ibi_audit_and_windows():
    d=pd.DataFrame({'USER':['P1']*4+['P2']*4,'IBI':[800,810,790,805,900,910,905,920]})
    a=gp.audit_gazepoint_ibi_quality(d,group_cols='USER')
    assert a['overview'].loc[0,'unit']=='milliseconds' and a['overview'].loc[0,'n_valid_ibi']==8
    assert a['overview'].loc[0,'status']=='ibi_quality_ok' and len(a['group_summary'])==2 and a['samples'].valid_ibi.all()
    s=gp.audit_gazepoint_ibi_quality(pd.DataFrame({'IBI':[.8,.81,.79,.805]}));assert s['overview'].loc[0,'unit']=='seconds' and np.allclose(s['samples'].ibi_ms,[800,810,790,805])
    bad=gp.audit_gazepoint_ibi_quality(pd.DataFrame({'IBI':[800,np.nan,0,250,2500,np.inf,810]}));o=bad['overview'].iloc[0]
    assert [o.n_missing_ibi,o.n_nonpositive_ibi,o.n_below_min_ibi,o.n_above_max_ibi,o.n_nonfinite_ibi]==[1,1,1,1,1]
    jump=gp.audit_gazepoint_ibi_quality(pd.DataFrame({'USER':['P1']*4,'TIME':[1,2,3,4],'IBI':[800,810,1500,1510]}),group_cols='USER',time_col='TIME',max_jump_ms=500)
    assert bool(jump['samples'].loc[2,'large_jump_ibi']) and not bool(jump['samples'].loc[3,'large_jump_ibi'])
    w=gp.summarise_gazepoint_ibi_windows(d,group_cols='USER');assert w['overview'].loc[0,'window_count']==2 and (w['windows'].status=='sufficient_ibi_window').all()
    w2=gp.summarise_gazepoint_ibi_windows(pd.DataFrame({'IBI':[800,810,1500,1510]}),max_jump_ms=500,min_valid_ibi=2);assert w2['windows'].loc[0,'n_valid_ibi']==3
    with pytest.raises(ValueError,match='No IBI'):gp.audit_gazepoint_ibi_quality(pd.DataFrame({'HRV':[1,1],'HR':[70,71]}))


def test_scr_intervals_and_kleckner():
    d=pd.DataFrame({'stimulus_onset':0,'peak_time':[1.5,5,8,12,np.nan]})
    out=gp.classify_gazepoint_scr_intervals(d,response_time_col='peak_time',stimulus_onset_col='stimulus_onset')
    assert list(out.scr_interval)==['FIR','SIR','TIR','outside_defined_intervals','missing_latency']
    sm=out.attrs['scr_interval_summary'].iloc[0];assert (sm.fir_rows,sm.sir_rows,sm.tir_rows)==(1,1,1)
    k=gp.flag_kleckner_eda_artifacts(pd.DataFrame({'participant':'p1','time':range(1,7),'GSR_US':[1,1.1,1.2,200,1.3,np.nan]}),time_col='time',group_cols='participant',transition_padding=0)
    assert bool(k.loc[3,'kleckner_range_artifact']) and bool(k.loc[5,'kleckner_nonfinite']) and k.kleckner_artifact.any()
    assert k.attrs['kleckner_artifact_summary'].loc[0,'status']=='kleckner_style_artifacts_flagged'


def test_gsr_conversion_and_tonic_phasic():
    d=pd.DataFrame({'GSR_OHMS':[1_000_000,500_000,np.nan,0,-1,np.inf]});o=gp.convert_gazepoint_gsr_to_conductance(d)
    assert np.allclose(o.GSR_US.iloc[:2],[1,2]) and o.GSR_US.iloc[2:].isna().all();s=o.attrs['gsr_conversion_summary'].iloc[0];assert s.status=='conductance_created' and s.n_converted==2 and s.n_invalid==3
    k=gp.convert_gazepoint_gsr_to_conductance(pd.DataFrame({'GSR':[1000,500,np.nan]}),gsr_col='GSR',input_unit='kohms');assert np.allclose(k.GSR_US.iloc[:2],[1,2])
    generic=gp.convert_gazepoint_gsr_to_conductance(pd.DataFrame({'GSR':[1_000_000,500_000]}),gsr_col='GSR');assert 'GSR_US' not in generic and generic.attrs['gsr_conversion_summary'].loc[0,'status']=='unit_not_confirmed'
    existing=gp.convert_gazepoint_gsr_to_conductance(pd.DataFrame({'GSR_US':[1,2,3],'GSR_OHMS':[1e6,5e5,333333]}));assert list(existing.GSR_US)==[1,2,3]
    tp=gp.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({'CNT':range(1,11),'GSR_US':[1,1.1,1,1.2,2,1.3,1.2,1.1,1,1.1]}),window_n=3,peak_threshold=.4)
    assert {'gsr_tonic','gsr_phasic','gsr_phasic_peak','gsr_phasic_peak_threshold'}<=set(tp['data']) and tp['data'].gsr_phasic_peak.any() and tp['summary'].loc[0,'group']=='all'
    grp=gp.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({'USER':['P1']*5+['P2']*5,'CNT':list(range(1,6))*2,'GSR_US':[1,1,2,1,1,2,2,3,2,2]}),group_cols='USER',time_col='CNT',window_n=3,peak_threshold=.4);assert len(grp['summary'])==2
    with pytest.raises(ValueError,match='No GSR/EDA'):gp.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({'HR':[70,71]}))
