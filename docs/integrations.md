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

## Compatibility dependencies

Two upstream packages currently need small packaging compatibility dependencies:

- **BioSPPy 2.2.4 / pyHRV 0.5.0**: BioSPPy imports `peakutils` without declaring it in its package metadata. The `biosppy`, `pyhrv`, and `interop` extras therefore include `peakutils>=1.3.4`.
- **HeartPy 1.2.7**: HeartPy imports the legacy `pkg_resources` API. Setuptools removed `pkg_resources` in version 82, so the `heartpy` and `interop` extras constrain Setuptools to `>=77,<82` until HeartPy migrates to `importlib.resources`.

These dependencies are compatibility scaffolding for the external backends; they do not alter gpbiometricspy's native numerical implementations.

### pyHRV / nolds compatibility

`pyHRV 0.5.0` depends on `nolds` without an upper bound. `nolds 0.6.3` has a known `importlib.resources` regression on Python 3.11 (`TypeError: 'nolds.datasets' is not a package`). The `gpbiometricspy[pyhrv]` and `gpbiometricspy[interop]` extras therefore constrain `nolds<0.6.3` while that upstream regression remains unresolved.
