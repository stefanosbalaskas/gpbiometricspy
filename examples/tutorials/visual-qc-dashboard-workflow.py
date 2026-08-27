from __future__ import annotations
from _shared import *
d=demo(600); activity=gp.audit_gazepoint_signal_activity(d,signal_cols=['GSR_US','HR','IBI','LPMM'],group_cols=['participant_id']); resets=gp.audit_gazepoint_time_resets(d,time_col='TIME',group_cols=['participant_id']); dashboard=gp.plot_gazepoint_biometric_report_dashboard(d,signal_activity=activity,time_resets=resets,signal_cols=['GSR_US','HR','LPMM'],group_cols=['participant_id'],time_col='TIME'); finish('visual-qc-dashboard-workflow',activity=activity,resets=resets,dashboard=dashboard)
