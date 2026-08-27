from __future__ import annotations
from _shared import *
bio=gp.simulate_gazepoint_biometrics(n_seconds=5,sampling_rate=20,seed=1); eye=gp.simulate_gazepoint_eye_data({'n_samples':100,'seed':2}); multi=gp.simulate_gazepoint_multimodal_data(duration_s=5,sampling_rate_hz=20,seed=3); artifact=gp.simulate_gazepoint_artifact(bio,signal_cols=['GSR_US'],artifact='spike',seed=4); finish('synthetic-data-showcase',biometrics=bio,eye=eye,multimodal=multi,artifact=artifact)
