# Python ecosystem integrations

The core package remains dependency-light. Optional integrations are explicit.

- **HeartPy**: optional cross-check around native HeartPy-style PPG workflows.
- **BioSPPy**: preparation bridges plus native BioSPPy-style signal workflows.
- **pyHRV**: native pyHRV-style HRV calculations plus Python-ready exports.
- **NeuroKit2**: optional EDA cross-check execution.
- **MNE**: event matrices, RawArray specifications and optional FIF writing.
- **pylsl / pyxdf**: live LSL clock correction and XDF import/synchronization.
- **PyMC**: reserved optional Bayesian ecosystem dependency; core parity functions do not force it.

The package documents whether an operation is a native port, a toolbox-style implementation, a preparation bridge, or an optional direct external-library execution path.
