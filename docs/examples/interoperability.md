# Interoperability examples

Optional integrations are isolated from the core install. The public CI matrix tests both floor and current versions for the supported external backends.

```bash
python -m pip install "gpbiometricspy[interop]"
```

Then use the package bridge that matches the workflow you need:

```python
import gpbiometricspy as gp

# HeartPy / BioSPPy / pyHRV / NeuroKit2 style workflows
# MNE event structures and RawArray handoff
# LSL/XDF synchronization
# BIDS-oriented export helpers
```

The matrix currently covers HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf. See the [Interoperability version-testing article](../articles/interoperability-version-testing.md), [MNE/EEG/LSL workflow](../articles/mne-eeg-lsl-workflow.md), and [External toolbox bridges](../articles/toolbox-bridges-workflow.md).
