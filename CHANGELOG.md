# Changelog

## 0.1.0.dev1 — Python 3.11 compatibility and release hardening

- fixed `export_gazepoint_pipeline_dot()` so the frozen implementation parses correctly under the declared Python 3.11 minimum without changing generated DOT output;
- retained the exact 406/406 `gpbiometrics 2.0.0` export parity contract and 204-test scientific regression suite;
- narrowed the Ruff release gate to high-signal correctness checks compatible with the intentionally compact parity-port source style;
- made GitHub Release creation idempotent and able to rebuild an existing immutable tag via manual dispatch;
- added compatibility with pandas 3 copy-on-write, datetime-unit, object-dtype, and DataFrame-attrs behavior while retaining the same public semantics.
- retained `v0.1.0.dev0` unchanged as the historical initial parity-freeze prerelease.

## 0.1.0.dev0 — gpbiometrics 2.0.0 parity freeze

- froze `gpbiometrics 2.0.0` as the initial R semantic reference;
- mapped and implemented all 406 exported R functions;
- added translated semantic, error-path and Python-native regression tests;
- added Gazepoint import, schema, QC, timing, TTL and workflow infrastructure;
- added EDA/SCR, HR/IBI/HRV, PPG, pupil, gaze, fixation, AOI and multimodal workflows;
- added native PsPM-style, BioSPPy-style, pyHRV-style and HeartPy-style families;
- added cluster permutation, diagnostics and intentional guardrails;
- added MNE, EEG, LSL/XDF and BIDS-oriented interoperability;
- added audit trails, preregistration/readiness, reporting and reproducibility helpers;
- packaged the 36-participant / 69,120-row synthetic kiosk demonstration dataset;
- retained frozen R source, tests, Rd help and 26 vignette/article sources in the sdist;
- added 26 Python article migration companions and a generated 406-function API reference;
- established CI, documentation and release workflows.
