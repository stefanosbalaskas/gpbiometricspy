from __future__ import annotations
from _shared import *
d=demo(300); e=gp.prepare_gazepoint_eyetrackingr_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',x_col='FPOGX',y_col='FPOGY',aoi_col='AOI',validity_col='FPOGV',irregular='allow')
p=gp.prepare_gazepoint_pupillometryr_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',pupil_col='LPMM',validity_cols=['LPMMV'],irregular='allow'); g=gp.prepare_gazepoint_gazer_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',x_col='FPOGX',y_col='FPOGY',pupil_col='LPMM',validity_col='FPOGV',irregular='allow'); finish('eye-tracking-ecosystem-bridges',eyetrackingr=e,pupillometryr=p,gazer=g)
