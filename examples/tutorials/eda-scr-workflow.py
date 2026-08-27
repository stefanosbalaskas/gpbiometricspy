from __future__ import annotations
from _shared import *
d=demo(900); units=gp.audit_gazepoint_gsr_units(d,gsr_col='GSR_US'); quality=gp.audit_gazepoint_gsr_quality(d,value_column='GSR_US'); artifacts=gp.audit_gazepoint_eda_artifacts(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'])
dec=gp.decompose_gazepoint_eda(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'],window_size=31); events=gp.detect_gazepoint_scr_events(dec,phasic_col='eda_phasic',time_col='TIME',group_cols=['participant_id'],min_peak_distance=10)
finish('eda-scr-workflow',units=units,quality=quality,artifacts=artifacts,decomposition=dec,events=events)
