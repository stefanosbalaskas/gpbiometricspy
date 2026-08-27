from __future__ import annotations
from _shared import *
d=demo(240)[['TIME','GSR_US','LPMM','TTL0']].rename(columns={'TIME':'time_s','LPMM':'pupil'}); mne_in=gp.prepare_gazepoint_mne_input(d,channel_cols=['GSR_US','pupil','TTL0'],time_col='time_s',sampling_rate_hz=60,missing='allow',irregular='allow')
events=gp.prepare_gazepoint_mne_events(pd.DataFrame({'event_time_s':[1.,2.],'event_label':['stimulus','response']}),sampling_rate_hz=60); synced=gp.sync_gazepoint_signals_via_lsl({'gaze':pd.DataFrame({'time_s':[0,1,2],'x':[.2,.3,.4]}),'bio':pd.DataFrame({'time_s':[.1,1.1,2.1],'gsr':[1,2,3]})},reference='gaze',clock_offsets_s={'gaze':0,'bio':-.1}); finish('mne-eeg-lsl-workflow',mne=mne_in,events=events,synced=synced)
