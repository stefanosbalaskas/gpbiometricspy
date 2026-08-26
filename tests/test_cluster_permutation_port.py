import numpy as np
import pandas as pd
import pytest
import matplotlib.figure
import gpbiometricspy as gp


def test_cluster_prepare_and_run_structure():
    rng=np.random.default_rng(102)
    raw=pd.MultiIndex.from_product([[f'P{i:02d}' for i in range(1,7)],['A','B'],range(1,11),[1,2]],names=['participant_id','condition_name','time_ms','trial']).to_frame(index=False)
    raw['signal']=rng.normal(size=len(raw))
    prep=gp.prepare_gazepoint_timecourse_test_data(raw,'signal','time_ms','condition_name','participant_id','A','B')
    assert len(prep)==6*2*10 and {'participant','condition','time','value'}<=set(prep)
    result=gp.run_gazepoint_cluster_permutation(prep,n_permutations=49,seed=202)
    assert {'timewise','clusters','null_distribution','settings'}<=set(result) and len(result['null_distribution'])==49 and result['settings']['design']=='within'


def test_cluster_detects_strong_effect_and_plots():
    rng=np.random.default_rng(103); subs=[f'P{i:02d}' for i in range(1,13)]
    dat=pd.MultiIndex.from_product([subs,['A','B'],range(1,61)],names=['participant','condition','time']).to_frame(index=False)
    shift=dict(zip(subs,rng.normal(0,.15,len(subs)))); dat['value']=[shift[s]+rng.normal(0,.18)+(1.2 if c=='A' and 25<=t<=38 else 0) for s,c,t in dat[['participant','condition','time']].itertuples(index=False,name=None)]
    r=gp.run_gazepoint_cluster_permutation(dat,n_permutations=199,seed=303)
    c=gp.summarize_gazepoint_time_clusters(r)
    assert len(c)>=1 and c.significant.any() and ((c.start_time<=30)&(c.end_time>=33)).any()
    assert isinstance(gp.plot_gazepoint_cluster_permutation(r),matplotlib.figure.Figure)
    assert isinstance(gp.plot_gazepoint_cluster_null_distribution(r),matplotlib.figure.Figure)
    rep=gp.report_gazepoint_cluster_permutation(r); assert 'global null' in rep['text'] and 'descript' in rep['text']


def test_cluster_diagnostics_sensitivity_and_export(tmp_path):
    dat=gp.simulate_gazepoint_cluster_timecourse_data(n_subjects=10,n_time=20,effect_start=8,effect_end=12,effect_size=.9,noise_sd=.25,seed=123)
    aud=gp.audit_gazepoint_timecourse_grid(dat,'subject','condition','time','value'); assert bool(aud['summary'].iloc[0].complete_grid)
    bad=gp.audit_gazepoint_timecourse_grid(dat.iloc[1:],'subject','condition','time','value'); assert not bool(bad['summary'].iloc[0].complete_grid)
    diag=gp.diagnose_gazepoint_cluster_design(dat,'subject','condition','time','value'); assert diag['passed'] and {'two_conditions','complete_grid'}<=set(diag['checks']['check'])
    sens=gp.run_gazepoint_cluster_threshold_sensitivity(dat,'value','time','condition','subject',thresholds=(.025,.05),n_permutations=19,seed=123); assert sens['summary']['threshold'].tolist()==[.025,.05]
    res=gp.run_gazepoint_cluster_permutation(dat,outcome_col='value',time_col='time',condition_col='condition',participant_col='subject',n_permutations=19,seed=123); files=gp.export_gazepoint_cluster_results(res,tmp_path,prefix='test_cluster',overwrite=True); assert len(files)==5 and (tmp_path/'test_cluster_report.txt').exists()


def test_cluster_guardrails():
    fns=[gp.run_gazepoint_cluster_permutation_anova,gp.run_gazepoint_cluster_permutation_lmer,gp.run_gazepoint_tfce,gp.run_gazepoint_multidimensional_cluster_permutation,gp.estimate_gazepoint_cluster_onset,gp.estimate_gazepoint_cluster_offset,gp.run_gazepoint_cluster_permutation_covariate_adjusted,gp.run_gazepoint_cluster_permutation_parallel]
    for fn in fns:
        with pytest.raises(NotImplementedError,match='not implemented'):fn()


def test_cluster_external_exports(tmp_path):
    dat=gp.simulate_gazepoint_cluster_timecourse_data(n_subjects=5,n_time=10,seed=123)
    m=gp.export_gazepoint_mne_cluster_input(dat,'value','time','condition','subject'); assert {'long','difference_matrix','metadata'}<=set(m) and len(m['difference_matrix'])==5
    p=gp.export_gazepoint_permuco_cluster_input(dat,'value','time','condition','subject'); q=gp.export_gazepoint_permutes_cluster_input(dat,'value','time','condition','subject'); assert len(p['long'])==100 and len(q['long'])==100
    w=gp.export_gazepoint_mne_cluster_input(dat,'value','time','condition','subject',path=tmp_path,overwrite=True); assert len(w)==3 and (tmp_path/'gazepoint_mne_cluster_long.csv').exists()
