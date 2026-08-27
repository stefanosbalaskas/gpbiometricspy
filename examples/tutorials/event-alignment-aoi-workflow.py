from __future__ import annotations
from _shared import *
d=demo(900); ttl=gp.extract_gazepoint_ttl_events(d,ttl_columns=['TTL0'],group_columns=['participant_id']); aligned=gp.align_gazepoint_biometrics_to_ttl(d,ttl_cols=['TTL0'],time_col='TIME',group_cols=['participant_id'],pre_window_ms=250,post_window_ms=500)
aoi=gp.summarize_gazepoint_aoi_dwell(d,aoi_col='AOI',group_cols=['participant_id']); finish('event-alignment-aoi-workflow',ttl=ttl,aligned=aligned,aoi=aoi)
