# Synthetic kiosk demo

The package ships the unchanged synthetic kiosk exports from `gpbiometrics 2.0.0`.

```python
import gpbiometricspy as gp

path = gp.kiosk_demo_path()
overview = gp.kiosk_demo_overview()
design = gp.kiosk_demo_trial_design()
data = gp.load_kiosk_demo()
```

Expected complete-demo invariants:

- 36 participants
- 4 tasks per participant
- 60 Hz
- 69,120 rows
- gaze, AOI, pupil, EDA/GSR, HR, IBI, pulse waveform, engagement dial and TTL channels

The dataset is synthetic and must not be interpreted as real human physiology.
