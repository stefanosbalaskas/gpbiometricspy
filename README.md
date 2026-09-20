<p align="center">
  <img src="https://raw.githubusercontent.com/stefanosbalaskas/gpbiometricspy/main/docs/assets/python-suite-logo.png" width="240" alt="gpbiometricspy Python research package logo">
</p>

<h1 align="center">gpbiometricspy</h1>

<p align="center"><strong>Scientific Python workflows and a guided application for Gazepoint eye-tracking and multimodal psychophysiology.</strong></p>
<p align="center">EDA / SCR · PPG / HRV · pupil · gaze · fixation · AOI · events · synchronization · multimodal QC · modelling · reproducible reporting</p>

<p align="center">
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="PyPI" src="https://img.shields.io/pypi/v/gpbiometricspy.svg"></a>
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/gpbiometricspy.svg"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml"><img alt="Documentation" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a href="https://doi.org/10.5281/zenodo.22150872"><img alt="Concept DOI" src="https://zenodo.org/badge/DOI/10.5281/zenodo.22150872.svg"></a>
</p>

<p align="center">
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/"><strong>Website</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/start-here/"><strong>Start here</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/studio/"><strong>Studio</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/workflows/"><strong>Workflows</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/methods/"><strong>Methods</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/"><strong>Plots</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/api/"><strong>API</strong></a>
</p>

---

## Start with the interface you need

**Studio** is the guided application over the same scientific package functions used by the Python API:

```bash
python -m pip install "gpbiometricspy[studio]==0.1.7"
gpbiometricspy-studio
```

Use the full local/private Studio for participant files. The anonymous public demonstration is synthetic-only and blocks external uploads.

**Python API**:

```bash
python -m pip install gpbiometricspy
```

```python
import gpbiometricspy as gp

data = gp.load_kiosk_demo()
validity = gp.summarise_gazepoint_biometric_validity(data)
events = gp.extract_gazepoint_ttl_events(data)
```

Optional extras cover interoperability, HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, LSL/XDF, Bayesian/statistical tooling, Studio, docs, and development.

## Research path

```text
Project intake
  → measurement + provenance checks
  → signal-specific QC and processing
  → events / AOIs / multimodal alignment
  → summaries and guarded modelling
  → reporting / certificates / reproducible replay
```

The package supports Gazepoint import/schema/validity, EDA/SCR, PPG and interval variability, pupil/gaze/fixation/saccade/AOI workflows, TTL/events, clock alignment and timebase provenance, multimodal summaries, design audits, cluster permutation, reporting/certificates, simulation, and MNE/LSL/XDF/external-toolbox interoperability.

For a task-first entry point use the **[Start here](https://stefanosbalaskas.github.io/gpbiometricspy/start-here/)** or **[Workflow map](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** rather than beginning with the raw function index.

## Python-native methods

Additive Python-native methods sit outside the frozen `gpbiometrics 2.0.0` parity surface. Current families include Gaussian and robust Student-t hierarchical location–scale models; one-factor location, log-scale, and joint random slopes; crossed participant–item intercept, location-slope, scale-slope, and **joint location + log-scale random-slope** models; grouped mixed and ordinal boosting; timebase/alignment certification; and cardiac-source provenance.

Use the **[model-selection guide](https://stefanosbalaskas.github.io/gpbiometricspy/guides/model-selection/)** to add complexity only when the design and scientific question require it.

## Certified release-preparation baseline

The exact current-main source qualified immediately before the stable freeze is:

- commit **`4c52b7c5fa20ab4e9981c9770baa79481f46c39f`**;
- frozen semantic reference **`gpbiometrics 2.0.0`**;
- **406 / 406** frozen exports implemented, **0 pending**;
- Tests #724: **12 / 12** OS/Python matrix lanes green;
- canonical Ubuntu / CPython 3.12.14: **855 / 855 tests**, **15,171 / 15,171 statements = 100.00%**;
- Branch Coverage #414: **7,159 / 7,178 = 99.7353%** raw branch coverage;
- exactly **19** reviewed residual arcs with **0 unexpected / 0 stale / 0 unaudited** branch debt;
- audited branch accounting **7,178 / 7,178 = 100.0000%**;
- Docs #485, CodeQL #703, Deep Parity #713, Interoperability #712 and Private Real Data Validation #175 all green.

The Windows structural-debt auditor now normalizes Windows and POSIX path separators before exact arc comparison. The audited 19-arc ledger and scientific implementation remain unchanged.

### Stable release record

Stable **0.1.7** is frozen from this release source on **20 September 2026**. Public GitHub/PyPI publication remains fail-closed: the stable source must first pass the protected pull-request and exact-main release gates before immutable `v0.1.7` creation and Trusted Publishing.

## Interpretation boundary

`gpbiometricspy` measures, processes, audits, aligns, summarizes, predicts and models recorded signals. Those operations do not by themselves establish emotion, stress, trust, preference, cognition, diagnosis, sensor validity or causal effects.

In particular, robust heavy-tailed modelling is not an artifact score; random effects/slopes are modelled heterogeneity rather than stable traits; log-scale effects are not measurement-quality scores by definition; permutation importance is predictive rather than causal; and timing/cardiac certificates bind declared provenance evidence rather than proving sensor validity.

See **[Interpretation guardrails](https://stefanosbalaskas.github.io/gpbiometricspy/interpretation/)** and **[Measurement accountability](https://stefanosbalaskas.github.io/gpbiometricspy/measurement-accountability/)**.

## Documentation

- **[Start here](https://stefanosbalaskas.github.io/gpbiometricspy/start-here/)** — route by research task.
- **[Studio](https://stefanosbalaskas.github.io/gpbiometricspy/studio/)** — guided visual workflow and local/public boundaries.
- **[Workflows](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** — EDA, cardiac, eye tracking, multimodal alignment, QC and interoperability.
- **[Methods](https://stefanosbalaskas.github.io/gpbiometricspy/methods/)** — Python-native modelling and provenance methods.
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — 17 deterministic figures generated in docs CI.
- **[API](https://stefanosbalaskas.github.io/gpbiometricspy/api/)** — domain-organized 406-function frozen-parity reference.
- **[Validation & trust](https://stefanosbalaskas.github.io/gpbiometricspy/deep-validation/)** — parity, coverage, real-data and application validation.

## Citation and archival record

Stable `gpbiometricspy 0.1.7` is frozen on **20 September 2026**.

- **0.1.7 version DOI:** pending genuine Zenodo ingestion of `v0.1.7`; no DOI is fabricated before minting
- **0.1.6 version DOI:** still pending independent Zenodo verification
- **Software concept DOI:** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)
- **0.1.5 version DOI:** [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)
- **0.1.4 version DOI:** [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)
- **0.1.3 version DOI:** [10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)
- **0.1.2 version DOI:** [10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)
- **Frozen R semantic-reference DOI:** [10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)
- **gpbiometrics article:** [10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

Until Zenodo mints the genuine 0.1.7 version DOI, cite the immutable GitHub release:

> Balaskas, S. (2026). *gpbiometricspy: Python tools for Gazepoint biometric workflows* (Version 0.1.7) [Computer software]. GitHub. https://github.com/stefanosbalaskas/gpbiometricspy/releases/tag/v0.1.7

The frozen R source/tests/docs/articles remain under `reference/` as the semantic reference used for parity work. See [`VALIDATION.md`](VALIDATION.md) and the documentation site for the complete evidence trail.