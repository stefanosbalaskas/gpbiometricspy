from __future__ import annotations
from _shared import *
d=demo(600); q=gp.audit_gazepoint_gsr_quality(d,value_column='GSR_US'); figs=[gp.plot_gazepoint_missingness(d,cols=['GSR_US','HR','IBI'],time_col='TIME'),gp.plot_gazepoint_biometric_signals(d,signal_cols=['GSR_US','HR'],time_col='TIME'),gp.plot_gazepoint_multimodal_timeline(d,time_col='TIME',signal_cols=['GSR_US','HR','LPMM'],group_cols=['participant_id'])]; finish('plot-gallery',quality=q,figures=figs)
