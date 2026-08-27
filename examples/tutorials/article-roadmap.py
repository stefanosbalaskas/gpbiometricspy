from __future__ import annotations
from _shared import *
d=demo(600)
inv=gp.create_gazepoint_biometrics_feature_inventory(); fmt=gp.format_gazepoint_biometrics_feature_inventory(inv); summ=gp.summarise_gazepoint_biometrics_feature_inventory(fmt)
interop=gp.gazepoint_interoperability_manifest(); readiness=gp.run_gazepoint_biometrics_real_data_readiness(d,min_rows=100)
finish('article-roadmap',inventory=fmt,summary=summ,interop=interop,readiness=readiness)
