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
  <a href="https://stefanosbalaskas.github.io/gpbiometricspy/methods/"><strong>Methods</strong></a> ·
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
| Development head | **0.1.7.dev0** |
| Release date | **2026-09-11** |
| Frozen semantic reference | **gpbiometrics 2.0.0** |
| API parity | **406 / 406 implemented · 0 pending** |
| Latest certified development baseline | **#125 · `1464e46cd75373eb634c3df12dedd5e7764af395`** |
| Exact-main tests | **733 / 733 passed** |
| Exact-main statement coverage | **13,028 / 13,028 = 100.00%** |
| Exact-main raw branch coverage | **6,403 / 6,422 = 99.7041%** |
| Crossed participant–item module coverage | **444 / 444 statements · 168 / 168 branches** |
| Timebase provenance module coverage | **377 / 377 statements · 150 / 150 branches** |
| PR #125 exact-head qualification | **14 / 14 workflow families successful** |
| PR #125 exact-main certification | **14 / 14 push workflow families successful** |
| Audited structural arcs | **19** |
| Unexpected / stale / unaudited branch debt | **0 / 0 / 0** |
| Supported Python | **3.11–3.14** |
| Studio | **11 research workflows + Chromium E2E + installed wheel/sdist production validation** |

The latest fully certified development baseline is PR #125 at `1464e46cd75373eb634c3df12dedd5e7764af395`, tree `2b4d4f532a2414179fe916fcae208ba20e063461`. Its tree exactly matches the qualified PR head tree `aafeab90e9b863746f60cd018accb1d336cc8a5d`, and its GitHub signature is verified/valid. The merge is transparently recorded as a **two-parent merge commit**—parents `eb8c737f93e952f7bec0e6d7958336f1ecf469f5` and `aafeab90e9b863746f60cd018accb1d336cc8a5d`—rather than being described as a squash. The candidate completed **14/14 exact-head workflow families successfully**, and the merge SHA completed **14/14 fresh exact-main push workflow families successfully** with **0 failures**, **0 cancellations**, **0 queued**, and **0 in-progress** runs. Exact-main software evidence passes **733/733 tests**, **13,028/13,028 statements = 100.00%**, and the frozen export audit remains **406/406 with 0 pending**. Exact-main raw branch coverage is **6,403/6,422 = 99.7041%**, with all **19** uncovered arcs explicitly audited as structural debt and **0 unexpected, stale or unaudited branch debt**; audited accounting is **6,422/6,422 = 100.0000%**. The crossed participant–item module passes **444/444 statements** and **168/168 branches**, while the timebase-provenance module passes **377/377 statements** and **150/150 branches**. The exact-main branch-coverage artifact is `10328745378` (`sha256:c0e767e4a9c6cad4ed87a3368e29ee778bf32a89e1809e1515c6581b29949108`). PR #124 remains the certified crossed-effects predecessor at `eb8c737f93e952f7bec0e6d7958336f1ecf469f5`.

Full exact-main certification is deliberately stricter than test and coverage success: it is declared only after every required post-merge push workflow for the exact merge SHA is terminal green. Pre-merge qualification is never substituted for post-merge evidence.

Stable **0.1.6** remains a separate frozen release line. Its release qualification preserves **641 core tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Development-line metrics above include post-release methods work and must not be read as retroactively changing the 0.1.6 artifacts.

### Scientific scope

`gpbiometricspy` supports Gazepoint-native and multimodal workflows spanning:

- CSV/TXT import, schema detection and validation;
- EDA/GSR/SCR preprocessing, artifacts, decomposition and response analysis;
- PPG/IBI/HRV processing and optional toolbox cross-checks;
- pupil, gaze, fixation, saccade and AOI workflows;
- TTL/event alignment, synchronization drift and secondary streams;
- multimodal summaries and model-ready tables;
- cluster permutation and statistical/design guardrails;
- Python-native Gaussian hierarchical location–scale modelling with correlated participant/group random intercepts in mean and log-scale equations;
- Python-native robust Student-t hierarchical location–scale modelling with jointly estimated finite-variance degrees of freedom;
- Python-native Gaussian random-slope location–scale modelling with one group-specific numeric slope in the location equation, a log-scale random intercept, full 3 × 3 latent covariance, and three-dimensional adaptive Gauss–Hermite quadrature;
- Python-native Gaussian random scale-slope location–scale modelling with one group-specific numeric slope in the log-scale equation, a location random intercept, full 3 × 3 latent covariance, and three-dimensional adaptive Gauss–Hermite quadrature;
- Python-native Gaussian joint random-slope location–scale modelling with one group-specific numeric slope in each equation, full 4 × 4 latent covariance, and bounded four-dimensional adaptive Gauss–Hermite quadrature;
- Python-native crossed participant–item Gaussian location–scale modelling with participant and item/stimulus random intercepts in both equations, separate correlated 2 × 2 covariance matrices, and joint Laplace integration;
- Python-native timebase provenance and multimodal alignment certification that separates nominal from timestamp-derived timing evidence, binds clock mappings and tolerances, and retains warning provenance;
- MNE, LSL/XDF, BIDS-oriented and external-toolbox interoperability;
- reproducibility, provenance, reporting and synthetic simulation.

The package preserves conservative interpretation boundaries: physiological and eye-tracking measurements are not direct proof of emotion, stress, trust, preference, cognition, health status, or diagnosis. The location–scale models estimate distributional heterogeneity. The Student-t extension provides heavy-tailed distributional robustness; a low fitted degrees-of-freedom parameter is **not** an artifact score. Location random slopes estimate association heterogeneity; log-scale random slopes estimate residual-heterogeneity association. Neither is a causal effect, artifact score, sensor-validity measure, or error-free participant trait. The joint model combines one slope in each equation under the same boundary. Crossed participant/item effects are modelled association heterogeneity, not participant traits or stimulus-quality scores. Timebase and alignment certificates bind recorded timing evidence and declared tolerances; they do **not** prove sensor validity, hardware synchronization beyond the supplied evidence, biological equivalence, reconstruction of unsampled information, or causal ordering. None of these methods by itself identifies artifacts, establishes sensor validity, performs sensor-validity weighting, or supports causal interpretation.

---

## Documentation

- **[Start here](https://stefanosbalaskas.github.io/gpbiometricspy/getting-started/)** — installation and first analysis.
- **[Studio](https://stefanosbalaskas.github.io/gpbiometricspy/studio/)** — application workflow, local/public boundaries and launch options.
- **[Workflow map](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** — choose a path from your recorded signals.
- **[Methods](https://stefanosbalaskas.github.io/gpbiometricspy/methods/)** — Python-native methodological extensions outside the frozen 406-export R parity surface.
- **[Timebase provenance and multimodal alignment](https://stefanosbalaskas.github.io/gpbiometricspy/methods/timebase-provenance/)** — observed timing audits, clock mappings, residual-tolerance gates and deterministic timing-lineage certificates.
- **[Hierarchical location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/hierarchical-location-scale/)** — Gaussian joint mean/log-scale modelling, adaptive Gauss–Hermite quadrature, empirical-Bayes group effects, prediction semantics and reproducibility certificates.
- **[Robust Student-t location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/robust-hierarchical-location-scale/)** — heavy-tailed conditional outcomes, estimated degrees of freedom, scale-vs-SD semantics, canonical empirical-Bayes certificate binding, defensive numerical validation and fail-closed certificates.
- **[Random-slope location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/random-slope-location-scale/)** — one group-specific numeric slope in the Gaussian location equation, full 3 × 3 latent covariance, three-dimensional adaptive quadrature, conditional/population prediction and reproducibility certificates.
- **[Random scale-slope location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/random-scale-slope-location-scale/)** — one group-specific numeric slope in the Gaussian log-scale equation, full 3 × 3 latent covariance, conditional/population prediction and reproducibility certificates.
- **[Joint random-slope location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/joint-random-slopes-location-scale/)** — one group-specific numeric slope in each Gaussian equation, full 4 × 4 latent covariance, bounded four-dimensional adaptive quadrature, conditional/population prediction and reproducibility certificates.
- **[Crossed participant–item location–scale modelling](https://stefanosbalaskas.github.io/gpbiometricspy/methods/crossed-location-scale/)** — crossed participant/item random intercepts in mean and log-scale equations, joint Laplace integration, fail-closed design checks and reproducibility certificates.
- **[Examples](https://stefanosbalaskas.github.io/gpbiometricspy/examples/)** — EDA, HRV, pupil/gaze, multimodal, QC/reporting and interoperability.
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — figures generated by the package.
- **[API by scientific domain](https://stefanosbalaskas.github.io/gpbiometricspy/api/)** — task-oriented navigation of all 406 frozen-parity functions plus separately documented Python-native methods.
- **[Validation](https://stefanosbalaskas.github.io/gpbiometricspy/deep-validation/)** — parity, coverage, real-data and application validation layers.

---

<a id="citation"></a>
## Citation and archival record

Stable `gpbiometricspy 0.1.6` was released on **2026-09-11** from the fully qualified stable-release line. The 0.1.6 Zenodo version DOI is intentionally left unset until Zenodo ingests the frozen GitHub release.

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

The R `gpbiometrics 2.0.0` source, tests, documentation and article material are retained under `reference/` as the frozen semantic reference used for parity work. Python-native methodological extensions are additive and documented separately under **Methods** so they do not alter the completed 406/406 semantic-parity contract. The current certified development line contains the Gaussian random-intercept location–scale model, robust Student-t extension, Gaussian location-random-slope extension, Gaussian scale-random-slope extension, Gaussian joint random-slope extension, crossed participant–item location–scale model, and timebase-provenance/multimodal-alignment certification layer, certified through PR #125. See [`VALIDATION.md`](VALIDATION.md), the documentation site, and the machine-readable export inventory for the deeper validation contract.