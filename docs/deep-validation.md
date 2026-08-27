# Deep parity and interoperability validation

`gpbiometricspy` uses several independent evidence layers beyond ordinary unit tests.

## R ↔ Python golden fixtures

`reference/golden/` contains deterministic numerical cases spanning EDA/GSR conversion, SCR normalization, HRV metrics, pupil smoothing, TTL changes, within-participant standardization and baseline correction. The `deep-parity` workflow runs the frozen R implementation and Python implementation independently and compares JSON results with explicit tolerances.

## Optional backend CI

The `interoperability` workflow tests both declared floor versions and current releases for HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf. Smoke cases import and actually exercise each backend rather than testing only absence/error paths.

## Why this is separate from 406/406 API parity

The exact export audit proves surface completeness. Golden fixtures and backend CI address numerical/back-end behavior, which is a different question and can change with dependency versions.
