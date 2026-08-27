from __future__ import annotations
from _shared import *
d=pulse_frame(100,20); det=gp.detect_gazepoint_ppg_peaks(d,'pulse','time_s',['participant'],100,high_precision=False); rr=gp.reject_gazepoint_ppg_peaks(det['peaks']); measures=gp.compute_gazepoint_ppg_measures(rr); fig=gp.plot_gazepoint_ppg_peak_detection(det); finish('ppg-hrv-visual-diagnostics',peaks=det,rr=rr,measures=measures,figure=fig)
