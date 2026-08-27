from __future__ import annotations
from _shared import *
d=demo(900); dec=gp.decompose_gazepoint_eda(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'],window_size=31)
ev=gp.detect_gazepoint_scr_events(dec,phasic_col='eda_phasic',time_col='TIME',group_cols=['participant_id'],min_peak_distance=10)
fig1=gp.plot_gazepoint_eda_decomposition(dec,time_col='TIME',signal_cols=['GSR_US','eda_tonic','eda_phasic'],group_cols=['participant_id']); finish('eda-scr-visual-diagnostics',decomposition=dec,events=ev,figure=fig1)
