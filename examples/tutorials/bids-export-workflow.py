from __future__ import annotations
from _shared import *
d=demo(240)[['TIME','FPOGX','FPOGY','LPMM','participant_id']].rename(columns={'TIME':'timestamp','FPOGX':'x','FPOGY':'y','LPMM':'pupil'})
with tempfile.TemporaryDirectory() as td:
    plan=gp.export_gazepoint_to_bids(d,td,subject='01',task='kiosk',timestamp_col='timestamp',x_col='x',y_col='y',pupil_col='pupil',dry_run=True)
finish('bids-export-workflow',plan=plan)
