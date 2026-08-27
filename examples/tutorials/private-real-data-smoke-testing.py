from __future__ import annotations
from _shared import *
with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as od:
    p=Path(td)/'synthetic_gazepoint.csv'; demo(300).to_csv(p,index=False); smoke=gp.run_gazepoint_real_data_smoke(td,output_dir=od,write_results=True,overwrite=True,protect_repository=True); privacy=gp.audit_gazepoint_smoke_privacy(smoke)
finish('private-real-data-smoke-testing',smoke=smoke,privacy=privacy)
