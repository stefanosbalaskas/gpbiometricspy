from __future__ import annotations
from _shared import *
d=demo(900); active=gp.detect_active_biometric_channels(d); schema=gp.detect_gazepoint_biometric_schema(d); readiness=gp.run_gazepoint_biometrics_real_data_readiness(d,min_rows=100); inv=gp.create_gazepoint_biometrics_feature_inventory(); finish('gpbiometrics-workflow',active=active,schema=schema,readiness=readiness,inventory=inv)
