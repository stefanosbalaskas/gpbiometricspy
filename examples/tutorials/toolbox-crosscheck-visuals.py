from __future__ import annotations
from _shared import *
d=pulse_frame(100,20); det=gp.detect_gazepoint_ppg_peaks(d,'pulse','time_s',['participant'],100,high_precision=False); heart=gp.run_gazepoint_heartpy_crosscheck(d,'pulse','time_s','participant',100,high_precision=False); bio=gp.run_gazepoint_biosppy_ppg(d.rename(columns={'pulse':'ppg'}),'ppg','time_s','participant',100); fig1=gp.plot_gazepoint_ppg_peak_detection(det); finish('toolbox-crosscheck-visuals',heartpy=heart,biosppy=bio,figure=fig1)
