from __future__ import annotations
from _shared import *
t=np.arange(-.5,1.01,.05); d=pd.DataFrame({'participant':'P01','trial':'T01','time':t,'pupil':3+.1*np.sin(4*t)}); base=gp.baseline_correct_gazepoint_pupil(d,pupil_col='pupil',time_col='time',trial_cols=['participant','trial'],baseline_window=(-.5,-.1)); smooth=gp.smooth_gazepoint_pupil(base,pupil_cols='pupil',id_cols=['participant','trial'],window=5); clean=gp.clean_gazepoint_pupil_signal(d,pupil_cols=['pupil'],time_col='time',group_cols=['participant','trial']); finish('pupil-qc-workflow',baseline=base,smooth=smooth,clean=clean)
