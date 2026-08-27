# Python ecosystem integrations

The core package remains dependency-light. Optional integrations are explicit.

- **HeartPy**: optional direct cross-check around native HeartPy-style PPG workflows.
- **BioSPPy**: preparation bridges, native BioSPPy-style workflows, and external BioSPPy smoke execution.
- **pyHRV**: native pyHRV-style calculations plus external pyHRV smoke execution.
- **NeuroKit2**: direct EDA cross-check execution.
- **MNE**: event matrices, RawArray specifications and optional FIF writing.
- **pylsl / pyxdf**: LSL clock/synchronization support and XDF import pathways.
- **PyMC**: reserved optional Bayesian ecosystem dependency; core parity functions do not force it.

The `interoperability` GitHub Actions workflow tests declared floor versions and current versions of HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf. The smoke script imports and exercises each installed backend rather than testing only graceful behavior when it is absent.

The package documents whether an operation is a native port, a toolbox-style implementation, a preparation bridge, or an optional direct external-library execution path.
