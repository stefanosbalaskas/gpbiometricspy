from __future__ import annotations
from _shared import *
d=demo(900); ev=gp.extract_gazepoint_ttl_events(d,ttl_columns=['TTL0'],group_columns=['participant_id']); summary=gp.summarize_gazepoint_eventlocked_multimodal(d,events=ev,time_col='TIME',event_time_col='TIME',signal_cols=['GSR_US','HR','LPMM'],group_cols=['participant_id']); fig=gp.plot_gazepoint_multimodal_timeline(d,time_col='TIME',signal_cols=['GSR_US','HR','LPMM'],group_cols=['participant_id']); finish('multimodal-event-dashboard',events=ev,summary=summary,figure=fig)
