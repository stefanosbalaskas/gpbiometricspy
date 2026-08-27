from __future__ import annotations
from _shared import *
d=demo(900); active=gp.detect_active_biometric_channels(d); miss=gp.summarize_gazepoint_missingness(d,signal_cols=['GSR_US','HR','IBI','LPMM']); validity=gp.summarise_gazepoint_biometric_validity(d); quality=gp.audit_gazepoint_gsr_quality(d,value_column='GSR_US'); finish('qc-workflow',active=active,missingness=miss,validity=validity,quality=quality)
