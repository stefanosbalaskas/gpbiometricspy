<p align="center">
  <img src="https://raw.githubusercontent.com/stefanosbalaskas/gpbiometricspy/main/docs/assets/python-suite-logo.png" width="240" alt="Python Suite research packages logo">
</p>

<h1 align="center">gpbiometricspy</h1>

<p align="center">
  <strong>Analyze Gazepoint eye-tracking and biometric data in Python — or use gpbiometricspy Studio for a guided research workflow.</strong>
</p>

<p align="center">
  EDA / SCR · PPG / HRV · pupil · gaze · fixation · AOI · events · synchronization · multimodal QC · statistics · reproducible reporting
</p>

<p align="center">
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="PyPI" src="https://img.shields.io/pypi/v/gpbiometricspy.svg"></a>
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/gpbiometricspy.svg"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/studio-e2e.yml"><img alt="Studio browser E2E" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/studio-e2e.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/studio-production.yml"><img alt="Studio production" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/studio-production.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a href="https://doi.org/10.5281/zenodo.22150872"><img alt="Concept DOI" src="https://zenodo.org/badge/DOI/10.5281/zenodo.22150872.svg"></a>
</p>

<p align="center">
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/"><strong>Website</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/studio/"><strong>Studio guide</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/workflows/"><strong>Workflow map</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/api/"><strong>Python API</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/"><strong>Plots</strong></a>
</p>

---

## Start with Studio

**gpbiometricspy Studio** is the end-user application layer over the validated `gpbiometricspy` scientific API. It gives researchers one stateful interface for importing data, checking quality, running signal-specific analyses, aligning streams, modelling results, and exporting reproducible outputs.

### Install the stable app

```bash
python -m pip install "gpbiometricspy[studio]==0.1.6"
```

### Launch it

The normal installed launcher is:

```bash
gpbiometricspy-studio
```

On Windows, if Python's Scripts directory is not on `PATH`, use the PATH-independent form:

```bash
python -m studio.cli --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`.

> Use the **full local Studio** for research files. The public-demo runtime is intentionally synthetic-only and blocks external uploads.

### Studio workflow

```text
Project intake
  → foundation QC
  → signal-specific analysis
  → events / AOIs / multimodal alignment
  → statistics & modelling
  → reporting / project recipe / reproducibility
```

Studio currently covers:

- project intake, schema inspection and channel detection;
- quality control and annotation;
- EDA / GSR / SCR;
- PPG / HR / HRV;
- pupil analysis;
- gaze / fixation / AOI analysis;
- event and secondary-stream alignment;
- multimodal analysis;
- statistics and modelling;
- reporting, provenance, recipes and reproducible replay.

Read the **[Studio guide](https://stefanosbalaskas.github.io/gpbiometricspy/studio/)** for the full application map and runtime boundaries.

---

## Prefer Python code?

Install the scientific package:

```bash
python -m pip install gpbiometricspy
```

Quick example:

```python
import gpbiometricspy as gp

# Fully synthetic bundled demonstration data.
data = gp.load_kiosk_demo()

# Inspect signal validity and availability.
validity = gp.summarise_gazepoint_biometric_validity(data)

# Extract TTL transitions.
events = gp.extract_gazepoint_ttl_events(data)
```

Optional interoperability stack:

```bash
python -m pip install "gpbiometricspy[interop]"
```

Extras are also available for `heartpy`, `biosppy`, `pyhrv`, `neurokit`, `mne`, `lsl`, `bayes`, `stats`, `studio`, `studio-test`, `docs`, and `dev`.

---

## Why gpbiometricspy?

| Area | Current state |
|---|---|
| Stable release | **0.1.6** |
| Release date | **2026-09-11** |
| Frozen semantic reference | **gpbiometrics 2.0.0** |
| API parity | **406 / 406 implemented · 0 pending** |
| Tests | **641** |
| Statement coverage | **10,456 / 10,456 = 100.00%** |
| Raw branch coverage | **5,629 / 5,648 = 99.6636%** |
| Audited structural arcs | **19** |
| Unexpected / stale / unaudited branch debt | **0 / 0 / 0** |
| Supported Python | **3.11–3.14** |
| Studio | **11 research workflows + Chromium E2E + installed wheel/sdist production validation** |

The raw branch metric remains **99.6636%**. The 19 remaining arcs are explicitly reviewed structural/caller-dominated paths; audited accounting is separate and does not relabel the raw coverage percentage as 100%.

### Scientific scope

`gpbiometricspy` supports Gazepoint-native and multimodal workflows spanning:

- CSV/TXT import, schema detection and validation;
- EDA/GSR/SCR preprocessing, artifacts, decomposition and response analysis;
- PPG/IBI/HRV processing and optional toolbox cross-checks;
- pupil, gaze, fixation, saccade and AOI workflows;
- TTL/event alignment, synchronization drift and secondary streams;
- multimodal summaries and model-ready tables;
- cluster permutation and statistical/design guardrails;
- MNE, LSL/XDF, BIDS-oriented and external-toolbox interoperability;
- reproducibility, provenance, reporting and synthetic simulation.

The package preserves conservative interpretation boundaries: physiological and eye-tracking measurements do **not** directly establish emotion, stress, trust, preference, cognition, health status, or diagnosis.

---

## Documentation

- **[Start here](https://stefanosbalaskas.github.io/gpbiometricspy/getting-started/)** — installation and first analysis.
- **[Studio](https://stefanosbalaskas.github.io/gpbiometricspy/studio/)** — application workflow, local/public boundaries and launch options.
- **[Workflow map](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** — choose a path from your recorded signals.
- **[Examples](https://stefanosbalaskas.github.io/gpbiometricspy/examples/)** — EDA, HRV, pupil/gaze, multimodal, QC/reporting and interoperability.
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — figures generated by the package.
- **[API by scientific domain](https://stefanosbalaskas.github.io/gpbiometricspy/api/)** — task-oriented navigation of all 406 functions.
- **[Validation](https://stefanosbalaskas.github.io/gpbiometricspy/deep-validation/)** — parity, coverage, real-data and application validation layers.

---

<a id="citation"></a>
## Citation and archival record

Stable `gpbiometricspy 0.1.6` was released on **2026-09-11** from the fully qualified stable-release line. The 0.1.6 Zenodo version DOI is intentionally left unset until Zenodo ingests the immutable GitHub release.

- **0.1.6 version DOI:** pending Zenodo ingestion of `v0.1.6` — no DOI is fabricated before minting
- **Software concept DOI:** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)
- **Previous 0.1.5 DOI:** [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)
- **Earlier 0.1.4 DOI:** [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)
- **Earlier 0.1.3 DOI:** [10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)
- **Earlier 0.1.2 DOI:** [10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)
- **Frozen R semantic-reference DOI:** [10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)
- **gpbiometrics article:** [10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

Recommended citation:

> Balaskas, S. (2026). *gpbiometricspy: Python tools for Gazepoint biometric workflows* (Version 0.1.6) [Computer software]. GitHub. https://github.com/stefanosbalaskas/gpbiometricspy/releases/tag/v0.1.6

## Development and provenance

The R `gpbiometrics 2.0.0` source, tests, documentation and article material are retained under `reference/` as the frozen semantic reference used for parity work. See [`VALIDATION.md`](VALIDATION.md), the documentation site, and the machine-readable export inventory for the deeper validation contract.
