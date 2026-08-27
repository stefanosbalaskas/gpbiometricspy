from __future__ import annotations
from _shared import *
d=demo(600); schema=gp.detect_gazepoint_biometric_schema(d); timebase=gp.detect_gazepoint_biometric_timebase(d,time_col='TIME',counter_col='CNT'); readiness=gp.run_gazepoint_biometrics_real_data_readiness(d,min_rows=100); missing=gp.summarize_gazepoint_missingness(d,signal_cols=['GSR_US','HR','IBI','LPMM']); finish('troubleshooting-readiness',schema=schema,timebase=timebase,readiness=readiness,missingness=missing)
