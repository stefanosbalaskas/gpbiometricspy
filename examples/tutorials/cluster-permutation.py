from __future__ import annotations
from _shared import *
d=gp.simulate_gazepoint_cluster_timecourse_data(n_subjects=8,n_time=24,effect_start=8,effect_end=14,seed=7).rename(columns={'subject':'participant'})
res=gp.run_gazepoint_cluster_permutation(d,participant_col='participant',n_permutations=99,seed=7)
report=gp.report_gazepoint_cluster_permutation(res); finish('cluster-permutation',result=res,report=report)
