from __future__ import annotations
from _shared import *
d=pulse_frame(100,30); process=gp.process_gazepoint_ppg_heartpy_style(d,'pulse','time_s','participant',100,high_precision=False); nni=800+30*np.sin(np.linspace(0,12*np.pi,300)); pyhrv=gp.run_gazepoint_pyhrv_style(nni_ms=nni); freq=gp.compute_gazepoint_pyhrv_frequency_domain(nni,method='welch'); finish('ppg-hrv-workflow',process=process,pyhrv=pyhrv,frequency=freq)
