# Getting started

Install from PyPI:

```bash
python -m pip install gpbiometricspy
```

```python
import gpbiometricspy as gp

data = gp.load_kiosk_demo()
print(data.shape)
```

The packaged kiosk dataset contains 36 synthetic participants, four tasks per participant and 69,120 Gazepoint-like rows at 60 Hz.

## Inspect and validate

```python
active = gp.detect_gazepoint_active_channels(data)
validity = gp.summarise_gazepoint_biometric_validity(data)
events = gp.extract_gazepoint_ttl_events(data)
```

## Physiological workflows

```python
# A pyHRV-style example from IBI in seconds.
nni_ms = data.loc[data["IBI"].notna(), "IBI"].head(500).to_numpy() * 1000
hrv = gp.run_gazepoint_pyhrv_style(nni_ms=nni_ms)

# HeartPy-style PPG processing.
ppg = gp.process_gazepoint_ppg_heartpy_style(data, signal_col="HRP", time_col="TIME")
```

## Optional integrations

Install only what you need, for example:

```bash
pip install "gpbiometricspy[mne,lsl]"
pip install "gpbiometricspy[heartpy,neurokit]"
```
