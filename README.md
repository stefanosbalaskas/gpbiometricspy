<p align="center">
  <img src="https://raw.githubusercontent.com/stefanosbalaskas/gpbiometricspy/main/docs/assets/python-suite-logo.png" width="260" alt="Python Suite research packages logo">
</p>

<h1 align="center">gpbiometricspy</h1>

<p align="center">
  <strong>Scientific Python infrastructure for EDA/SCR, PPG/HRV, pupil, gaze, AOI, synchronization, QC, and multimodal Gazepoint research.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="PyPI" src="https://img.shields.io/pypi/v/gpbiometricspy.svg"></a>
  <a href="https://pypi.org/project/gpbiometricspy/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/gpbiometricspy.svg"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/releases/latest"><img alt="GitHub release" src="https://img.shields.io/github/v/release/stefanosbalaskas/gpbiometricspy"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml"><img alt="Docs" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/codeql.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a href="https://doi.org/10.5281/zenodo.22150872"><img alt="DOI" src="https://zenodo.org/badge/DOI/10.5281/zenodo.22150872.svg"></a>
</p>

<p align="center">
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/"><strong>Documentation</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/workflows/"><strong>Workflow map</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/api/"><strong>Browse API</strong></a> ·
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/"><strong>Plot gallery</strong></a> ·
  <a href="#citation"><strong>Citation</strong></a>
</p>

`gpbiometricspy` is scientific Python infrastructure for Gazepoint and multimodal psychophysiology workflows spanning EDA/SCR, PPG/HRV, pupil, gaze/AOI, event alignment, quality control, statistics, interoperability, and reproducible reporting. It is the Python counterpart of **gpbiometrics**, using the supplied **gpbiometrics 2.0.0** source release as a frozen semantic reference.

| Status | Current state |
|---|---|
| Stable release | **0.1.2** |
| Development | **0.1.3.dev0** |
| Frozen semantic reference | **gpbiometrics 2.0.0** |
| API parity | **406 / 406 implemented · 0 pending** |
| Validation | **317 tests · 100.00% statement coverage** |
| Supported Python | **3.11–3.14** |

## What you get

- **Complete frozen API contract:** all **406 / 406** exported R functions are implemented and registered, with **0 pending exports**.
- **Literal whole-package coverage:** **317 tests**, **10,316 statements**, **0 missed**, and a CI floor of **100%**.
- **Scientific-domain navigation:** the documentation groups the API into **8 research domains** while preserving the complete alphabetical 406-function reference.
- **Executable learning material:** **26** frozen-R article/vignette companions are paired with Python workflows, examples, and generated figures.
- **Reproducible public demo data:** a fully synthetic kiosk dataset with **36 participants and 69,120 rows** ships with the package.
- **Deep validation layers:** independent R↔Python golden fixtures, optional-backend interoperability CI, privacy-preserving real-data validation, and frozen upstream provenance.

The project deliberately distinguishes **API completion** from an absolute claim that independent R and Python runtimes are numerically identical in every external-library/version combination. The frozen R implementation, tests, documentation, and article sources are retained in `reference/` so deeper parity can continue to be audited.

## Install

Install the current public release from PyPI:

```bash
python -m pip install gpbiometricspy
```

For optional scientific integrations:

```bash
python -m pip install "gpbiometricspy[interop]"
```

For a source checkout used in package development:

```bash
python -m pip install -e ".[dev]"
```

Individual extras are available for `heartpy`, `biosppy`, `pyhrv`, `neurokit`, `mne`, `lsl`, `bayes`, `stats`, `docs`, and `dev`.

## Quick start

```python
import gpbiometricspy as gp

# Load the public synthetic kiosk demo distributed with the package.
data = gp.load_kiosk_demo()
print(data.shape)  # (69120, ...)

# Inspect biometric signal validity / availability.
validity = gp.summarise_gazepoint_biometric_validity(data)

# Extract TTL transitions.
events = gp.extract_gazepoint_ttl_events(data)

# Example native pyHRV-style workflow from IBI values.
hrv = gp.run_gazepoint_pyhrv_style(
    nni_ms=data.loc[data["IBI"].notna(), "IBI"].head(500).to_numpy() * 1000
)
```

The bundled kiosk demo is **fully synthetic** and is intended only for examples, testing, and reproducible workflow demonstrations.

## Explore the documentation

Start with the route that matches what you want to do:

- **[Documentation home](https://stefanosbalaskas.github.io/gpbiometricspy/)** — package overview, status, entry points, and validation story.
- **[Workflow map](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** — choose a path based on the signals and events you recorded.
- **[Browse API by scientific domain](https://stefanosbalaskas.github.io/gpbiometricspy/api/)** — navigate the 406-function surface by research task rather than alphabetically.
- **[Complete 406-function reference](https://stefanosbalaskas.github.io/gpbiometricspy/api/reference/)** — exhaustive frozen export reference.
- **[Examples](https://stefanosbalaskas.github.io/gpbiometricspy/examples/)** — EDA/SCR, PPG/HRV, pupil/gaze/AOI, multimodal, QC/reporting, and interoperability examples.
- **[Articles and tutorials](https://stefanosbalaskas.github.io/gpbiometricspy/articles/)** — all 26 frozen R vignette/article companions, organized by scientific topic and backed by executable Python code.
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — figures generated directly by the Python plotting API from bundled synthetic/public data.

## Scientific scope

The frozen `gpbiometrics 2.0.0` parity surface covers, among other areas:

- Gazepoint biometric file/folder import, schema detection, validation, and QC;
- EDA/GSR/SCR preprocessing, artifacts, response detection, windows, habituation/recovery, spectral and nonlinear descriptors, and external bridges;
- HR/IBI/HRV/PPG processing, pyHRV-style, HeartPy-style and BioSPPy-style workflows, nonlinear HRV, RQA/geometric metrics, and respiratory proxies;
- pupil, gaze, fixation, saccade, AOI, and event-locked multimodal workflows;
- TTL alignment, synchronization drift, LSL/XDF, MNE, and BIDS-oriented bridges;
- cluster permutation testing plus explicit guardrails for designs the frozen R package intentionally refuses;
- reproducibility, preregistration, audit trails, readiness checks, reporting, plots, workflow summaries, simulation, and synthetic smoke testing.

## Validation and parity

Development on `main` goes beyond the 406/406 export freeze. The repository includes independent R↔Python golden fixtures, floor/current optional-backend interoperability CI, executable article companions, platform/Python matrix testing, and a privacy-preserving real-data validation CLI.

The current development validation baseline is:

```text
R exports:             406
Implemented exports:   406
Explicit pending:        0
Tests:                 317
Statements:         10,316
Missed:                   0
Statement coverage: 100.00%
CI coverage floor:      100%
```

See [`VALIDATION.md`](VALIDATION.md) and the documentation site's validation material for the distinction between API parity, executable contract coverage, and deeper cross-runtime/backend evidence.

## Interpretation guardrails

`gpbiometricspy` preserves the conservative interpretation policy of the R package. Physiological and eye-tracking signals are measurements and derived features; they do **not** directly establish emotion, stress, cognition, preference, health status, or diagnosis. Pupil measurements remain sensitive to luminance and visual context, and respiration estimates derived from PPG or other surrogate channels are proxies unless independently validated.

<a id="citation"></a>
## Archival and citation

`gpbiometricspy 0.1.2` is the first Python release archived automatically through the Zenodo GitHub integration.

- **Version DOI (0.1.2):** [10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)
- **Concept DOI (all gpbiometricspy versions):** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)
- **Frozen R reference DOI:** [10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)

For reproducible citation of analyses, cite the **version DOI** corresponding to the software release used. Use the **concept DOI** when referring to the evolving `gpbiometricspy` software family.

The R DOI remains separate provenance and is recorded in `.zenodo.json` as `isDerivedFrom`; it is not the Python package DOI. GitHub citation metadata are maintained in [`CITATION.cff`](CITATION.cff).

## Reference precedence

When Python and explanatory prose disagree, parity work follows:

1. frozen `gpbiometrics 2.0.0` implementation;
2. frozen R tests;
3. formal Rd documentation;
4. vignettes/examples;
5. repository/site explanatory material.

See the documentation site source in `docs/`, the machine-readable export inventory in `reference/r-export-inventory.csv`, and [`VALIDATION.md`](VALIDATION.md) for the current release gates.
