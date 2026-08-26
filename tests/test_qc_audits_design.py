import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
import gpbiometricspy as gp


def beats():
    return pd.DataFrame({'participant':np.repeat(['P01','P02'],8),'beat_time_ms':[0,800,1600,1850,2700,5200,6000,6800,0,780,1560,2340,3120,3900,3900,4680]})

def test_beat_audit_and_corrections():
    a=gp.audit_gazepoint_beats(beats(),beat_time_col='beat_time_ms',group_cols='participant',min_ibi=300,max_ibi=2000,duplicate_tolerance=0,max_relative_change=1.0)
    assert len(a['beats'])==16 and len(a['summary'])==2
    p1=a['summary'].query("participant=='P01'").iloc[0];p2=a['summary'].query("participant=='P02'").iloc[0]
    assert (p1.n_flagged_beats,p1.n_short_ibi,p1.n_long_ibi,p1.n_abrupt_change)==(3,1,1,2)
    assert (p2.n_flagged_beats,p2.n_short_ibi,p2.n_duplicate_time)==(1,1,1)
    m=gp.correct_gazepoint_beats(a,action='mask');assert len(m['correction_log'])==4;assert m['summary'].n_corrections.tolist()==[3,1]
    lm=gp.correct_gazepoint_beats(a,action='local_median',local_window=2)
    assert lm['correction_log'].query("participant=='P01'").corrected_ibi.tolist()==[800,800,800]
    assert lm['correction_log'].query("participant=='P02'").corrected_ibi.tolist()==[780]

def test_beat_explicit_and_summary_validation():
    d=pd.DataFrame({'participant':'P03','ibi_ms':[np.nan,800,790,250,810,2600,805]})
    a=gp.audit_gazepoint_beats(d,ibi_col='ibi_ms',group_cols='participant')
    s=a['summary'].iloc[0];assert (s.n_intervals,s.n_nonfinite_ibi,s.n_short_ibi,s.n_long_ibi,s.n_flagged_beats)==(7,1,1,1,3)
    log=pd.DataFrame({'participant':['P01','P01','P02'],'action':['mask','local_median','local_median'],'correction_note':['masked_flagged_interval','replaced_with_local_median','replaced_with_group_median'],'flag_reason':['short_ibi','long_ibi','short_ibi'],'original_ibi':[250,2500,0],'corrected_ibi':[np.nan,800,780]})
    out=gp.summarize_gazepoint_beat_corrections(log,by='participant');assert out.query("participant=='P01'").iloc[0].n_corrections==2;assert out.query("participant=='P02'").iloc[0].n_group_median==1
    with pytest.raises(ValueError):gp.audit_gazepoint_beats(d)
    with pytest.raises(ValueError):gp.audit_gazepoint_beats(d,ibi_col='ibi_ms',min_ibi=2000,max_ibi=300)
    with pytest.raises(ValueError):gp.correct_gazepoint_beats(a,local_window=0)

def test_quality_index_session_and_overview():
    qc=pd.DataFrame({'participant':['P01','P02','P03'],'missing_prop':[0,5,10],'signal_quality':[10,20,30],'constant_metric':[4,4,4]})
    q=gp.compute_gazepoint_quality_index(qc,['missing_prop','signal_quality'],directions={'signal_quality':'higher','missing_prop':'lower'},weights={'signal_quality':2,'missing_prop':1},index_col='q')
    assert np.allclose(q.q,[1/3,1/2,2/3]);assert np.allclose(gp.compute_gazepoint_quality_index(qc,['constant_metric']).quality_index,.5)
    d=pd.DataFrame({'participant':np.repeat(['P01','P02','P03','P04'],2),'session':['S1','S2']*4,'prop_missing':[.02,.04,.03,.05,.25,.28,.01,.02],'n_flags':[1,2,1,3,12,14,0,1],'signal_quality':[.95,.92,.90,.88,.45,.40,.98,.96]})
    qi=gp.compute_gazepoint_quality_index(d,['prop_missing','n_flags','signal_quality'],directions={'prop_missing':'lower','n_flags':'lower','signal_quality':'higher'},weights={'prop_missing':2,'n_flags':1,'signal_quality':2})
    a=gp.audit_gazepoint_session_comparability(qi,['prop_missing','n_flags','quality_index'],['participant','session'],method='both',z_threshold=1.5)
    assert len(a['flags'])==24
    assert a['summary'].query("participant=='P03'").n_flagged_metrics.tolist()==[3,3]
    assert (a['summary'].query("participant!='P03'").n_flagged_metrics==0).all()
    x=pd.DataFrame({'participant':['P01','P01','P02','P02'],'any_flag':[True,False,True,True],'missing_flag':[False,False,True,False],'quality_index':[.9,.8,.4,.5],'prop_missing':[.02,.03,.20,.25]})
    o=gp.summarize_gazepoint_qc_overview(x,'participant','quality_index',['any_flag','missing_flag'],['prop_missing']);p1=o.query("participant=='P01'").iloc[0]
    assert p1.n_any_flag==1 and p1.n_flagged_rows==1 and np.isclose(p1.quality_index_mean,.85) and np.isclose(p1.prop_missing_mean,.025)

def test_session_missing_and_validation():
    d=pd.DataFrame({'participant':['P01','P02','P03'],'session':'S1','prop_missing':[.01,np.nan,.03]})
    a=gp.audit_gazepoint_session_comparability(d,'prop_missing',['participant','session']);f=a['flags'].query("participant=='P02'").iloc[0]
    assert f.metric_missing and f.any_flag and f.flag_reason=='metric_missing'
    with pytest.raises(ValueError):gp.audit_gazepoint_session_comparability(d,'prop_missing','missing')
    with pytest.raises(ValueError):gp.audit_gazepoint_session_comparability(d,'prop_missing',z_threshold=0)

def test_design_event_condition_and_plots():
    dat=pd.DataFrame([(f'P{i}',t,'A' if t%2 else 'B','S1' if i<3 else 'S2') for i in range(1,5) for t in range(1,5)],columns=['participant','trial','condition','session'])
    a=gp.audit_gazepoint_experiment_design(dat,'participant','trial','condition','session',['A','B'],1);assert a['overview'].iloc[0].n_participants==4 and len(a['warnings'])==0
    bad=pd.DataFrame({'participant':['P1','P1','P2'],'trial':[1,2,1],'condition':['A']*3});b=gp.audit_gazepoint_experiment_design(bad,'participant','trial','condition',expected_conditions=['A','B']);assert {'missing_expected_conditions','low_participant_condition_cells'}<=set(b['warnings'].issue)
    ev=pd.DataFrame([(f'P{i}',t,e) for i in range(1,4) for t in [1,2] for e in ['stimulus','response']],columns=['participant','trial','event']);e=gp.audit_gazepoint_event_coverage(ev,'event','participant','trial',expected_events=['stimulus','response']);assert e['overview'].iloc[0].complete_unit_prop==1
    bal=pd.DataFrame([(f'P{i}',c,t) for i in range(1,5) for c in ['A','B'] for t in [1,2,3]],columns=['participant','condition','trial']);c=gp.audit_gazepoint_condition_balance(bal,'participant','condition','trial',['A','B']);assert c['overview'].iloc[0].trial_imbalance_ratio==1 and c['overview'].iloc[0].complete_participant_condition_grid
    for obj,typ in [(a,'condition_counts'),(a,'participant_trials'),(e,'event_coverage'),(c,'warnings')]:
        fig=gp.plot_gazepoint_design_coverage(obj,typ);assert hasattr(fig,'savefig');plt.close(fig)

def test_incomplete_event_condition_and_validation():
    dat=pd.DataFrame({'participant':['P1','P1','P2'],'trial':[1,1,1],'event':['stimulus','response','stimulus']});a=gp.audit_gazepoint_event_coverage(dat,'event','participant','trial',expected_events=['stimulus','response','feedback']);assert {'events_never_observed','partial_event_coverage','incomplete_event_units'}<=set(a['warnings'].issue)
    x=pd.DataFrame({'participant':['P1']*10+['P2']*2+['P3']*2,'condition':['A']*12+['B']*2,'trial':range(1,15)});b=gp.audit_gazepoint_condition_balance(x,'participant','condition','trial',['A','B']);assert {'missing_participant_condition_cells','condition_trial_imbalance','incomplete_participant_condition_grid'}<=set(b['warnings'].issue)
    with pytest.raises(ValueError):gp.audit_gazepoint_event_coverage(dat,'missing')
    with pytest.raises(ValueError):gp.audit_gazepoint_event_coverage(dat,'event',unit_cols='missing')
