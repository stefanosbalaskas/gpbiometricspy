# gpbiometricspy

[![PyPI](https://img.shields.io/pypi/v/gpbiometricspy.svg)](https://pypi.org/project/gpbiometricspy/)
[![Python](https://img.shields.io/pypi/pyversions/gpbiometricspy.svg)](https://pypi.org/project/gpbiometricspy/)
[![GitHub release](https://img.shields.io/github/v/release/stefanosbalaskas/gpbiometricspy)](https://github.com/stefanosbalaskas/gpbiometricspy/releases/latest)
[![Tests](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/tests.yml)
[![Docs](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/docs.yml)
[![CodeQL](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/stefanosbalaskas/gpbiometricspy/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22150872.svg)](https://doi.org/10.5281/zenodo.22150872)

`gpbiometricspy` is the Python counterpart of **gpbiometrics**, with the supplied
**gpbiometrics 2.0.0** source release frozen as its initial semantic reference.
It provides Gazepoint-native tools for importing, validating, preprocessing,
analysing, plotting, modelling, synchronising, and reporting biometric and
multimodal eye-tracking data.

| Channel | Current state |
|---|---|
| Stable PyPI / GitHub release | **0.1.2** |
| Development branch | **0.1.3.dev0** |
| Frozen R semantic reference | **gpbiometrics 2.0.0** |
| Export parity | **406 / 406 implemented; 0 pending** |
| Zenodo concept DOI | **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)** |
| Zenodo 0.1.2 version DOI | **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)** |

## Parity status

The current development tree has reached the frozen R API contract:

- **406 / 406 R exports implemented and registered**
- **0 pending exports**
- **200+ Python parity/edge tests**
- **whole-package statement coverage ≥ 90%**
- packaged synthetic kiosk demo: **36 participants, 69,120 rows**
- frozen R reference retained: 144 R sources, 403 Rd files, 120 R test files,
  and 26 vignette/article sources

The project deliberately distinguishes **API completion** from an absolute
claim that independent R and Python runtimes are numerically identical in every
external-library/version combination. The frozen R tests and implementation
are retained in `reference/` so parity can continue to be audited.

## Install

Install the public release from PyPI:

```bash
python -m pip install gpbiometricspy
```

For optional integrations:

```bash
python -m pip install "gpbiometricspy[interop]"
```

For a source checkout used in package development:

```bash
python -m pip install -e ".[dev]"
```

Individual extras are available for `heartpy`, `biosppy`, `pyhrv`,
`neurokit`, `mne`, `lsl`, `bayes`, `stats`, `docs`, and `dev`.

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

The demo is **fully synthetic** and is intended only for examples, testing,
and reproducible workflow demonstrations.

## Documentation, examples and plots

The documentation site now exposes the package as a complete scientific workflow rather than only an API catalog:

- [Examples](https://stefanosbalaskas.github.io/gpbiometricspy/examples/) — EDA/SCR, PPG/HRV, pupil/gaze/AOI, multimodal, QC/reporting and interoperability;
- [Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/) — figures generated directly by the Python plotting API from bundled synthetic/public data;
- [Articles and tutorials](https://stefanosbalaskas.github.io/gpbiometricspy/articles/) — all 26 frozen R vignette/article companions, each backed by executable Python code;
- [API reference](https://stefanosbalaskas.github.io/gpbiometricspy/api/reference/) — all 406 exported functions.


## Deep validation layers

Beyond the 406/406 export freeze, development on `main` includes independent R↔Python golden fixtures, floor/current optional-backend interoperability CI, 26 executable Python article companions, and a privacy-preserving real-data validation CLI. See the documentation site for the distinction between API parity and deeper cross-runtime/backend evidence.

## Scientific scope

The 2.0.0 parity surface covers, among other areas:

- Gazepoint biometric file/folder import, schema detection, validation and QC;
- EDA/GSR/SCR preprocessing, artifacts, response detection, windows,
  habituation/recovery, spectral/nonlinear descriptors and external bridges;
- HR/IBI/HRV/PPG processing, pyHRV-style, HeartPy-style and BioSPPy-style
  workflows, nonlinear HRV, RQA/geometric metrics and respiratory proxies;
- pupil, gaze, fixation, saccade, AOI and event-locked multimodal workflows;
- TTL alignment, synchronization drift, LSL/XDF, MNE and BIDS-oriented bridges;
- cluster permutation testing plus explicit guardrails for designs that the R
  package intentionally refuses;
- reproducibility, preregistration, audit trails, readiness checks, reporting,
  plots, workflow summaries, simulation and synthetic smoke testing.

## Interpretation guardrails

`gpbiometricspy` preserves the conservative interpretation policy of the R
package. Physiological and eye-tracking signals are measurements and derived
features; they do **not** directly establish emotion, stress, cognition,
preference, health status, or diagnosis. Pupil measurements remain sensitive
to luminance and visual context, and respiration estimates derived from PPG or
other surrogate channels are proxies unless independently validated.

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

See the documentation site source in `docs/`, the machine-readable export
inventory in `reference/r-export-inventory.csv`, and `VALIDATION.md` for the
current release gates.
