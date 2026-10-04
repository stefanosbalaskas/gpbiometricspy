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
python -m pip install "gpbiometricspy[studio]==0.1.8"
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

Additive Python-native methods sit outside the frozen `gpbiometrics 2.0.0` parity surface. Current families include Gaussian and robust Student-t hierarchical location–scale models; one-factor location, log-scale, and joint random slopes; crossed participant–item intercept, location-slope, scale-slope, and **joint location + log-scale random-slope** models; grouped mixed and ordinal boosting; timebase/alignment certification; cardiac-source provenance; and a PPG pigmentation / measurement-equity audit that separates signal quality, paired availability, and reference agreement.

The PPG equity workflow supports objective CIELAB/ITA-style pigmentation metadata when available and preserves subjective scales such as Fitzpatrick as subjective provenance rather than converting them into objective pigmentation, race, ethnicity, melanin or ITA. It does not apply a universal pigmentation correction and does not provide clinical SpO₂ validation.

### New in 0.1.8 — PPG measurement equity

The 0.1.8 release now has a complete documentation path around this method:

- **[Explanation article: Auditing PPG measurement equity](https://stefanosbalaskas.github.io/gpbiometricspy/articles/python-native/ppg-measurement-equity/)** — why signal quality, paired availability and reference agreement must remain separate;
- **[Synthetic worked example](https://stefanosbalaskas.github.io/gpbiometricspy/examples/ppg-equity-synthetic/)** — deterministic known-truth figures and participant-cluster uncertainty;
- **[Method specification](https://stefanosbalaskas.github.io/gpbiometricspy/methods/ppg-pigmentation-equity/)** — public API, equations and interpretation guardrails;
- **[STEP external evidence](https://stefanosbalaskas.github.io/gpbiometricspy/ppg-equity-external-evidence/)** — authorized aggregate-only wearable–ECG evidence under the applicable PhysioNet DUA;
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — 20 showcased deterministic figures, including the three PPG measurement-equity SVGs.

The STEP evidence uses only derived aggregate outputs publicly; participant-level restricted rows are not redistributed. Fitzpatrick remains subjective categorical provenance, and row-level paired availability is not relabelled as generic device failure or fairness.

Use the **[model-selection guide](https://stefanosbalaskas.github.io/gpbiometricspy/guides/model-selection/)** to add complexity only when the design and scientific question require it.

## Current stable release — 0.1.8

`gpbiometricspy 0.1.8` was published on **4 October 2026**.

- immutable release source: **`32cafd5565bdf4a7575dcf5c5d6bb2bfbe101e5d`**;
- immutable tag: **[`v0.1.8`](https://github.com/stefanosbalaskas/gpbiometricspy/releases/tag/v0.1.8)**;
- public package: **[PyPI 0.1.8](https://pypi.org/project/gpbiometricspy/0.1.8/)**;
- frozen semantic reference: **`gpbiometrics 2.0.0`**;
- **406 / 406** frozen exports implemented, **0 pending**;
- exact-main tests: **12 / 12** OS × Python 3.11–3.14 lanes green;
- canonical scientific suite: **874 / 874 tests**, **15,612 / 15,612 statements = 100.00%**;
- raw branch coverage **7,315 / 7,334 = 99.7409%**;
- exactly **19** reviewed structural arcs with **0 unexpected / 0 stale / 0 unaudited** branch debt;
- audited branch accounting **7,334 / 7,334 = 100.0000%**;
- docs/Pages, CodeQL, deep R↔Python parity, optional-backend interoperability, private real-data validation, release-handoff safety, Studio packaging and Windows upgrade-policy validation all green;
- wheel SHA-256: **`b1a88c2306843df2cc324b8987335bba413d27715a81f451ba0a036afe0a39f0`**;
- sdist SHA-256: **`231c14bab9eeddb0e0e6e9dce0cc095451cf48d7dcd160c5c553005482d7c24d`**;
- PyPI Trusted Publishing completed with digital attestations for both distributions.

The scientific qualification baseline immediately before the stable freeze was commit `a75eb1d73791213e6e830ff94975f632455632e2`. The STEP evidence tranche was completed on an authorized local copy of BigIdeasLab_STEP v1.0 under the applicable PhysioNet DUA using exact scientific source `dc2b539154f65061a90d360f01503108ad1fd39f`. The public repository records only derived aggregate evidence and interpretation boundaries; participant-level restricted rows are not redistributed. ENCoDE remains deferred and is not claimed as empirically executed.

## Interpretation boundary

`gpbiometricspy` measures, processes, audits, aligns, summarizes, predicts and models recorded signals. Those operations do not by themselves establish emotion, stress, trust, preference, cognition, diagnosis, sensor validity or causal effects.

In particular, robust heavy-tailed modelling is not an artifact score; random effects/slopes are modelled heterogeneity rather than stable traits; log-scale effects are not measurement-quality scores by definition; permutation importance is predictive rather than causal; timing/cardiac certificates bind declared provenance evidence rather than proving sensor validity; and PPG pigmentation analyses must not be relabelled as generic device fairness or causal optical effects.

See **[Interpretation guardrails](https://stefanosbalaskas.github.io/gpbiometricspy/interpretation/)** and **[Measurement accountability](https://stefanosbalaskas.github.io/gpbiometricspy/measurement-accountability/)**.

## Documentation

- **[Start here](https://stefanosbalaskas.github.io/gpbiometricspy/start-here/)** — route by research task.
- **[Studio](https://stefanosbalaskas.github.io/gpbiometricspy/studio/)** — guided visual workflow and local/public boundaries.
- **[Workflows](https://stefanosbalaskas.github.io/gpbiometricspy/workflows/)** — EDA, cardiac, eye tracking, multimodal alignment, QC and interoperability.
- **[Methods](https://stefanosbalaskas.github.io/gpbiometricspy/methods/)** — Python-native modelling and provenance methods.
- **[Plot gallery](https://stefanosbalaskas.github.io/gpbiometricspy/plot-gallery/)** — 20 showcased deterministic figures: 17 CI-generated core figures plus 3 PPG measurement-equity SVGs.
- **[API](https://stefanosbalaskas.github.io/gpbiometricspy/api/)** — domain-organized 406-function frozen-parity reference.
- **[Validation & trust](https://stefanosbalaskas.github.io/gpbiometricspy/deep-validation/)** — parity, coverage, real-data and application validation.

## Citation and archival record

`gpbiometricspy 0.1.8` is the current public stable release.

- **0.1.8 version DOI:** pending genuine Zenodo ingestion of `v0.1.8`; no DOI is fabricated before minting
- **0.1.8 GitHub release:** [v0.1.8](https://github.com/stefanosbalaskas/gpbiometricspy/releases/tag/v0.1.8)
- **0.1.8 PyPI release:** [gpbiometricspy 0.1.8](https://pypi.org/project/gpbiometricspy/0.1.8/)
- **0.1.7 version DOI:** still pending independent Zenodo verification
- **0.1.6 version DOI:** still pending independent Zenodo verification
- **Software concept DOI:** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)
- **0.1.5 version DOI:** [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)
- **0.1.4 version DOI:** [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)
- **0.1.3 version DOI:** [10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)
- **0.1.2 version DOI:** [10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)
- **Frozen R semantic-reference DOI:** [10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)
- **gpbiometrics article:** [10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

Until Zenodo mints and exposes a genuine 0.1.8 version DOI, cite the immutable `v0.1.8` release together with version `0.1.8` and the software concept DOI.

The frozen R source/tests/docs/articles remain under `reference/` as the semantic reference used for parity work. See [`VALIDATION.md`](VALIDATION.md) and the documentation site for the complete evidence trail.