# gpbiometricspy validation status

Frozen semantic reference: **gpbiometrics 2.0.0**.

## Frozen reference inventory

- 406 R exports
- 144 R source files
- 403 Rd help files
- 120 R test files, including `tests/testthat.R`
- 26 vignette/article sources
- 39 `inst/extdata` files

## Stable 0.1.0 release evidence

`gpbiometricspy 0.1.0` is a completed public release, not a release candidate.

- **406 / 406** frozen R exports implemented
- **0** pending exports
- exact export-set audit: **PASS**
- **204 / 204** Python tests at the stable freeze: **PASS**
- every frozen export explicitly referenced by Python tests: **406 / 406**
- exports explicitly referenced by the frozen R tests: **378 / 406**
- exports documented in frozen Rd help: **406 / 406**
- whole-package statement coverage at the stable freeze: **90.45%**
- required coverage threshold: **90% — PASS**
- Python 3.11–3.14 on Linux, Windows and macOS: **PASS**
- Ruff, `compileall`, MkDocs strict build, wheel build, sdist build and Twine metadata check: **PASS**
- synthetic kiosk demo: **69,120 rows / 36 participants — PASS**
- stable GitHub release `v0.1.0`: **PASS**
- PyPI Trusted Publishing through GitHub OIDC: **PASS**
- PyPI wheel/sdist SHA-256 identity with GitHub Release assets: **PASS**
- fresh public-PyPI install/import/export smoke: **PASS**
- GitHub Pages documentation deployment over HTTPS: **PASS**

Stable distribution digests:

- `gpbiometricspy-0.1.0-py3-none-any.whl`: `3370c646825603d96165e890b36491acd07148ffbe992ad00ba3ab79044a31e6`
- `gpbiometricspy-0.1.0.tar.gz`: `0e7cd9badeb64dae7f46690746fe9a7eca5f7b3eb61cd10f70af0e04f5f83970`

## Stable 0.1.1 deep-validation release

The 0.1.1 release adds evidence and release hardening rather than silently changing the frozen R contract:

1. paired R/Python golden fixtures for deterministic numerical families;
2. optional-backend floor/current CI for HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf;
3. executable Python companions for all 26 frozen R articles/vignettes;
4. a repository-safe real-data validation CLI and manual workflow;
5. CodeQL, Dependabot and contribution/issue templates.

Validated `0.1.1` regression evidence before the stable tag:

- **211 / 211** Python tests: **PASS**
- whole-package statement coverage: **90.75%**
- exact export audit: **406 / 406 implemented, 0 pending — PASS**
- Python 3.11 grammar audit: **PASS**
- `compileall` across `src/`, `tests/`, `scripts/` and `examples/`: **PASS**
- executable article companions: **26 / 26 — PASS**
- development wheel build + isolated import/export smoke: **PASS**
- documentation relative-link/nav audit: **PASS, 0 broken/missing targets**
- R/Python golden comparison: **PASS on GitHub Actions**
- optional-backend floor/current matrix: **14 / 14 PASS on GitHub Actions**
- strict docs + GitHub Pages: **PASS on GitHub Actions**
- CodeQL: **PASS on GitHub Actions**
- privacy-safe real-data harness workflow: **PASS on GitHub Actions**
- private participant-data validation: **not claimed without a user-supplied private dataset**

The golden-fixture harness writes independent R and Python result JSON files at full numerical precision and compares recursively with explicit absolute/relative tolerances. It is intentionally separate from ordinary Python unit tests so cross-runtime disagreements cannot be hidden by shared implementation code.

The real-data workflow is opt-in. Private Gazepoint exports remain outside Git and are supplied only at execution time. The workflow/reporting code checks paths and output locations to reduce accidental repository disclosure.

## Meaning of parity

The 406-function freeze means the complete frozen R export surface has a Python implementation and direct Python-test evidence. It does **not** claim that every optional external-library call is bit-identical across every operating system, library release or numerical backend. Cross-runtime fixtures and optional-backend CI are maintained as additional evidence layers.

- Optional-backend compatibility metadata now explicitly supplies BioSPPy/pyHRV `peakutils` and HeartPy `setuptools<82` requirements required by the upstream releases tested in CI.

- pyHRV compatibility constrains `nolds<0.6.3` because nolds 0.6.3 breaks imports via an `importlib.resources` regression; compatible earlier nolds releases still use `pkg_resources`, so pyHRV also inherits the `setuptools>=77,<82` compatibility boundary on current Python runtimes.


## 0.1.1 release-gate policy

The stable tag must point at the exact validated `main` commit. Before creating or publishing the GitHub Release, `release.yml` verifies successful `main` runs for the 12-job core matrix, strict documentation build, CodeQL, R/Python golden parity, 14-job optional-backend interoperability matrix, and the privacy-safe real-data harness. After the GitHub Release is created, the workflow explicitly dispatches the protected `pypi.yml` Trusted Publisher workflow. Public participant data are never required or uploaded.

## 0.1.2 visual-documentation and Zenodo-backed release candidate

The 0.1.2 tranche adds documentation, archival metadata and repository hardening without changing the frozen 406-function R semantic contract. Before tagging, the release source is required to retain:

- **406 / 406** frozen R exports implemented and **0 pending**;
- the complete Python regression suite and **>=90%** whole-package coverage gate;
- all **26 / 26** executable article companions;
- all **13 / 13** package-generated documentation figures;
- R/Python golden parity, 14-job optional-backend interoperability, CodeQL, strict docs/Pages and the privacy-safe real-data harness as exact-commit GitHub gates;
- `CITATION.cff` and `.zenodo.json` synchronized to **0.1.2**;
- the R `gpbiometrics 2.0.0` DOI `10.5281/zenodo.21434608` preserved only as `isDerivedFrom` provenance;
- no Python DOI claimed until Zenodo actually ingests the published `v0.1.2` GitHub release.

## Stable 0.1.3 public release and archival evidence

- immutable GitHub tag: `v0.1.3`;
- public PyPI release: `gpbiometricspy 0.1.3`;
- Zenodo version DOI: `10.5281/zenodo.22313884`;
- previous 0.1.2 version DOI: `10.5281/zenodo.22150873`;
- Zenodo concept DOI: `10.5281/zenodo.22150872`;
- frozen R reference DOI remains separate: `10.5281/zenodo.21434608` with `isDerivedFrom` provenance;
- public release artifacts, exact-commit CI, documentation, PyPI installation and Zenodo ingestion were verified before returning `main` to development.

## 0.1.3 stable-release freeze

The 0.1.3 release source freezes the completed Studio application and the literal whole-package coverage closure without changing the frozen 406-function scientific contract.

- whole-package statement coverage: **100.00%**, enforced with `--cov-fail-under=100`;
- frozen R export contract: **406 / 406 implemented; 0 pending**;
- completion uses executable behavioral/error-path tests and small dead-path cleanups; no `pragma: no cover`, coverage exclusion, or measurement-scope reduction is used;
- Studio is included as a separate distributable application package, with full and synthetic-only installed launchers;
- Studio smoke, Chromium E2E, production/distribution, strict docs, CodeQL, deep parity, optional-backend interoperability, and the 12-cell scientific matrix were all green on the pre-freeze launch-hardening PR before merge;
- release identity is synchronized to **0.1.3** across package metadata, `gpbiometricspy.__version__`, `.zenodo.json`, `CITATION.cff`, generated documentation metadata, governance/reproducibility outputs, and release-facing tests;
- the 0.1.3 version-specific Zenodo DOI is **not claimed before Zenodo ingestion**; the software concept DOI remains `10.5281/zenodo.22150872`, while `10.5281/zenodo.22150873` remains explicitly the previous 0.1.2 version DOI;
- the stable tag cutter requires all nine release-gate workflow families to succeed on the exact current `main` commit before creating `v0.1.3`, then explicitly dispatches `release.yml` to avoid `GITHUB_TOKEN` tag-push recursion suppression;
- a public `v0.1.3` GitHub Release, PyPI publication, release-asset digests, and Zenodo version DOI are recorded only after those downstream release steps actually complete.

## 0.1.4 development branch-path validation

The first 0.1.4 validation tranche adds control-flow coverage as a separate quality signal while preserving the existing **100% statement-coverage** contract.

- empirical pre-tranche branch baseline: **4,815 / 5,594 branches = 86.0744%**;
- post-tranche measurement: **4,869 / 5,594 branches = 87.0397%**;
- missing branch paths reduced from **779 to 725** (**54 newly validated paths**);
- `cluster_permutation.py`: **82 / 110 (74.545%) → 101 / 110 (91.818%)**;
- `governance_core.py`: **112 / 160 (70.000%) → 143 / 160 (89.375%)**;
- `reports.py`: **62 / 70 (88.571%) → 66 / 70 (94.286%)**;
- the added tests exercise public modelling, guardrail, provenance, audit and reporting behavior; they do not call private helpers and do not alter production scientific algorithms;
- a dedicated Python 3.13 branch-coverage workflow now measures the full suite with `--cov-branch` and enforces a pure branch-coverage floor using `covered_branches / num_branches` from coverage JSON;
- the branch floor is intentionally separate from pytest-cov's combined statement/branch percentage and from the 12-cell **100% statement** gate;
- the branch workflow runs for matching pull requests and matching pushes to `main`, so the measured improvement becomes a persistent regression gate rather than a one-off audit.

### Scientific QC branch tranche

The second 0.1.4 branch/path tranche closes deterministic alternatives and guardrails in scientific QC, standardization, and signal-quality reporting without changing production scientific implementations.

- pre-tranche measurement inherited from the first 0.1.4 tranche: **4,869 / 5,594 branches = 87.0397%**;
- post-tranche measurement: **4,928 / 5,594 branches = 88.0944%**;
- missing branch paths reduced from **725 to 666** (**59 newly validated paths** in this tranche; **113 cumulatively** since the 0.1.4 baseline);
- `scientific_qc.py`: **116 / 116 branches = 100.000%**;
- `qc_windows_standardization.py`: **66 / 66 branches = 100.000%**;
- `signal_quality.py`: **60 / 60 branches = 100.000%**;
- the tranche exercises public IBI/RR, SCR interval, EDA artifact, GSR conversion/decomposition, standardization, GSR/HR/dial QC-window, and signal-quality APIs; no file under `src/gpbiometricspy/` is changed;
- branch-coverage CI now retains both `coverage-branch.json` and a human-readable branch-debt audit as a **30-day GitHub Actions artifact** for exact-head evidence and next-tranche planning;
- the persistent pure branch-coverage regression floor is raised conservatively from **86.8% to 87.8%**, retaining headroom below the measured **88.0944%** while preventing regression to the previous tranche level.

### Final remaining branch tranche

The third 0.1.4 branch/path tranche targets the largest remaining deterministic source-file debt while keeping the production scientific tree unchanged.

- pre-tranche measurement inherited from the scientific-QC tranche: **4,928 / 5,594 branches = 88.0944%**;
- post-tranche exact-head measurement: **4,981 / 5,594 branches = 89.0418%**;
- missing branch paths reduced from **666 to 613** (**53 newly validated paths** in this tranche; **166 cumulatively** since the original 0.1.4 baseline);
- `final_remaining.py`: **279 / 332 branches = 84.036% → 332 / 332 branches = 100.000%**;
- the added tests exercise exported AOI assignment, BIDS export, eyetrackingR/gazeR/pupillometryR adapters, data-quality/dashboard reporting, artifact-SVM features, autoencoder guardrails, point-process alternatives, preregistration/trial-regressor paths, and smoke/privacy behavior;
- helper-level branches are reached through exported `gpbiometricspy` front doors rather than by directly testing private helpers;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact branch evidence remains retained as the 30-day `branch-coverage-python-3.13` GitHub Actions artifact;
- the persistent pure branch-coverage regression floor is raised conservatively from **87.8% to 88.7%**, retaining headroom below the measured **89.0418%** while preventing regression to the previous 88.0944% tranche level.

### Endgame science branch tranche

The fourth 0.1.4 branch/path tranche targets deterministic EDA/SCR, nonlinear-HRV, respiration, drift, changepoint, and recovery control flow while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the final-remaining tranche: **4,981 / 5,594 branches = 89.0418%**;
- post-tranche measurement: **5,027 / 5,594 branches = 89.8641%**;
- missing branch paths reduced from **613 to 567** (**46 newly validated paths** in this tranche; **212 cumulatively** since the original 0.1.4 baseline);
- `endgame_science.py`: **205 / 252 branches = 81.349% → 251 / 252 branches = 99.603%**;
- the added tests exercise only exported `gpbiometricspy` APIs for EDA artifact/SCR validation, event-window alternatives, nonresponder/hurdle/sensitivity guardrails, spectral/wavelet/TVSymp failure and partial paths, nonlinear-HRV alternatives, respiration fusion, MAD wall artifacts, distributional drift, changepoint fallbacks, and SCR recovery behavior;
- the sole residual `endgame_science.py` branch is the defensive short-input guard in private `_match_count()`: repository search confirms its only production caller first requires coarse-grained length `>= m + 2`, which necessarily satisfies both subsequent `_match_count(..., m, ...)` and `_match_count(..., m + 1, ...)` minimum-length conditions; the guard is therefore structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing production solely for a coverage number;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact branch evidence remains retained as the 30-day `branch-coverage-python-3.13` GitHub Actions artifact;
- the persistent pure branch-coverage regression floor is raised conservatively from **88.7% to 89.5%**, retaining headroom below the measured **89.8641%** while preventing regression to the prior **89.0418%** tranche level.

### Deterministic extensions branch tranche

The fifth 0.1.4 branch/path tranche closes the largest remaining deterministic source-file debt across plotting contracts, within-unit standardization, interoperability preparation, synchronization diagnostics, PPG/EDA utilities, and conservative reporting behavior.

- pre-tranche measurement inherited from the endgame-science tranche: **5,027 / 5,594 branches = 89.8641%**;
- post-tranche exact-head measurement: **5,072 / 5,594 branches = 90.6686%**;
- missing branch paths reduced from **567 to 522** (**45 newly validated paths** in this tranche; **257 cumulatively** since the original 0.1.4 baseline);
- `deterministic_extensions.py`: **179 / 224 branches = 79.911% → 224 / 224 branches = 100.000%**;
- public-API tests cover plot-contract validation and metadata fallback, within-unit standardization guardrails/reference subsets/zero-SD and no-transform behavior, RHRV export and IBI-unit alternatives, NeuroKit EDA input preparation, lag and synchronization-drift alternatives, pyPPG preparation and waveform-quality statuses, EDA decomposition/SCR detection, and checklist/methods-text behavior;
- branch testing exposed one genuine pandas 3 compatibility defect in the existing `center=False, scale=False` standardization path: `Series.to_numpy()` could return a read-only view before the existing finite-mask assignment; the implementation now requests `to_numpy(dtype=float, copy=True)`, preserving the same numerical transformation and scientific semantics while guaranteeing the intended writable working array;
- repository search found this exact mutable-array pattern only at that standardization location; no broader production refactor was made;
- the frozen 406-export semantic contract, 100% statement-coverage gate, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating artifact for the measured head is bound by digest `sha256:40538f12fef16597d68dfd8785c5d8d2dbc8600e7abba0b0e69e040bbe406886`;
- the persistent pure branch-coverage regression floor is raised conservatively from **89.5% to 90.3%**, retaining headroom below the measured **90.6686%** while preventing regression to the prior **89.8641%** tranche level.

### pyHRV-style branch tranche

The sixth 0.1.4 branch/path tranche targets the largest remaining HRV-style control-flow debt through exported pyHRV-compatible front doors while preserving the production scientific implementation unchanged.

- pre-tranche measurement inherited from the deterministic-extensions tranche: **5,072 / 5,594 branches = 90.6686%**;
- post-tranche exact measured coverage: **5,111 / 5,594 branches = 91.3657%**;
- missing branch paths reduced from **522 to 483** (**39 newly validated paths** in this tranche; **296 cumulatively** since the original 0.1.4 baseline);
- `pyhrv_style.py`: **154 / 194 branches = 79.381% → 193 / 194 branches = 99.485%**;
- public-API tests cover short/degenerate Welch, Lomb and autoregressive PSD behavior; NN-interval extraction and segmentation guardrails; empty time-domain, triangular-index and TINN alternatives; PSD waterfall and nonlinear short/invalid-scale behavior; plotting/radar validation; JSON conversion/export behavior; and `prepare_gazepoint_pyhrv_input()` validation, explicit/automatic unit resolution, missing/non-numeric columns, and multi-column grouping;
- the sole residual `pyhrv_style.py` branch is arc `76 → exit`, the defensive `n < 4` guard in private `_fft_psd()`; repository search confirms the only pyHRV production caller is `_welch_psd()`, which returns before invoking `_fft_psd()` whenever `n < 8`, so the `n < 4` guard is structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing scientific code solely for a coverage number;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:2a818fd7c33b0a62fbeba0140b0e4b17c6910c763e6a8a51f46ffbbc084de331`;
- the persistent pure branch-coverage regression floor is raised conservatively from **90.3% to 91.0%**, retaining headroom below the measured **91.3657%** while preventing regression to the prior **90.6686%** tranche level.

### HeartPy-style branch tranche

The seventh 0.1.4 branch/path tranche targets the largest remaining HeartPy-style PPG/HRV control-flow debt through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the pyHRV-style tranche: **5,111 / 5,594 branches = 91.3657%**;
- post-tranche exact measured coverage: **5,145 / 5,594 branches = 91.9735%**;
- missing branch paths reduced from **483 to 449** (**34 newly validated paths** in this tranche; **330 cumulatively** since the original 0.1.4 baseline);
- `heartpy_style.py`: **227 / 264 branches = 85.985% → 261 / 264 branches = 98.864%**;
- public-API tests cover time-column inference and group validation, short/nonfinite/constant clipping inputs, enhancement/Butterworth/Hampel sampling guardrails, detector shape/sampling/high-precision fallback behavior, peak rejection and RR-from-peaks alternatives, empty/tiny RR resampling and frequency inputs, empty measures and plotting/report validation, unsectioned scaling, RR-cleaning invalid/short/zero-dispersion alternatives, and segmentwise input/plot guardrails;
- the three residual `heartpy_style.py` branches are structural defensive paths rather than missing exported behavior: arc `134 → exit` checks for an empty `output_dir` only after `Path(output_dir)` construction, while `Path("")` normalizes to `.`; arc `154 → 156` is the false branch of `if n > 1` after an earlier unconditional return for every `n < 4`, so reaching that line implies `n >= 4`; and arc `399 → exit` checks for an empty positive datetime-difference vector only after timestamps have been de-duplicated, sorted, and required to have length at least two, which necessarily yields positive adjacent differences;
- those defensive guards are retained rather than manufacturing private-helper tests or changing valid production code solely for nominal branch closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:e0437027b2000309f25aeae2e3852f24c5858839da8cb7a72449c017c2bf44ae`;
- the persistent pure branch-coverage regression floor is raised conservatively from **91.0% to 91.6%**, retaining headroom below the measured **91.9735%** while preventing regression to the prior **91.3657%** tranche level.

### BioSPPy-style branch tranche

The eighth 0.1.4 branch/path tranche targets BioSPPy-style EDA/PPG, RRI, spectral, and correlation control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the HeartPy-style tranche: **5,145 / 5,594 branches = 91.9735%**;
- post-tranche exact measured coverage: **5,174 / 5,594 branches = 92.4920%**;
- missing branch paths reduced from **449 to 420** (**29 newly validated paths** in this tranche; **359 cumulatively** since the original 0.1.4 baseline);
- `biosppy_style.py`: **155 / 186 branches = 83.333% → 184 / 186 branches = 98.925%**;
- public-API tests cover preparation/settings validation, explicit signal/time/group errors, nonfinite and nonincreasing time, invalid inferred rates, sparse interpolation and segment handling, overwrite/manifest behavior, exported EDA preparation failures, short PPG filtering and empty onset/template behavior, EDA recovery without a recovery point, RRI detrending/artifact-correction alternatives, short/invalid spectra, absolute/zero-total band power, phase locking, and correlation validation/lag insufficiency;
- the two residual `biosppy_style.py` branches are caller-dominated defensive guards rather than missing exported behavior: arc `20 → exit` is private `_running_mean()`'s `k <= 1` return, while repository search confirms its sole BioSPPy production caller invokes it as `_running_mean(..., max(3, round(.25 * fs)))`; arc `85 → exit` is private `_peak_indices(peaks=None)`, while both exported PPG callers replace `peaks=None` with `_detect_ppg(...)` before invoking `_peak_indices()`;
- those defensive guards are retained rather than manufacturing private-helper tests or changing valid production code solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:7c7ea93b9d555170135a5135c77d2dc6782651b504ea6ca61cfe5241291fa0c4`;
- the persistent pure branch-coverage regression floor is raised conservatively from **91.6% to 92.1%**, retaining headroom below the measured **92.4920%** while preventing regression to the prior **91.9735%** tranche level.

### MNE/EEG/LSL branch tranche

The ninth 0.1.4 branch/path tranche closes the complete remaining MNE event, EEG alignment, MNE input, and LSL synchronization control-flow debt through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the BioSPPy-style tranche: **5,174 / 5,594 branches = 92.4920%**;
- post-tranche exact measured coverage: **5,205 / 5,594 branches = 93.0461%**;
- missing branch paths reduced from **420 to 389** (**31 newly validated paths** in this tranche; **390 cumulatively** since the original 0.1.4 baseline);
- `mne_eeg_lsl.py`: **115 / 146 branches = 78.767% → 146 / 146 branches = 100.000%**;
- public-API tests cover MNE event option/rate validation, empty and marker/no-marker time-resolution failures, marker-column and active-marker guardrails, sample-unit conversion, embedded event codes and incomplete mappings; MNE input type/option/time/rate/channel/metadata validation and EEG/ECG type inference; EEG alignment option/type/sample-rate/no-match/linear-minimum/residual-policy guardrails; and LSL stream/time/option/dejitter validation plus one-dimensional XDF-style stream normalization;
- all 31 pre-tranche residual MNE/EEG/LSL branch paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:5909731d9feaead01ef06da5dee776a5ec0e72fb2f8abdceabf46660e07f7737`;
- the frozen 406-export semantic contract, 100% statement-coverage gate, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **92.1% to 92.7%**, retaining headroom below the measured **93.0461%** while preventing regression to the prior **92.4920%** tranche level.

### Final deterministic branch tranche

The tenth 0.1.4 branch/path tranche closes the complete remaining control-flow debt in the final deterministic utilities through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the MNE/EEG/LSL tranche: **5,205 / 5,594 branches = 93.0461%**;
- post-tranche exact measured coverage: **5,235 / 5,594 branches = 93.5824%**;
- missing branch paths reduced from **389 to 359** (**30 newly validated paths** in this tranche; **420 cumulatively** since the original 0.1.4 baseline);
- `final_deterministic.py`: **206 / 236 branches = 87.288% → 236 / 236 branches = 100.000%**;
- public-API tests cover adaptive EMA operation without an explicit time column; downsampling group/signal-selection validation; sampling-audit option/column/group validation and estimated-rate behavior; HRV feature validation, explicit IBI selection, validity-column omission and sparse-input alternatives; row-level/window-summary exclusion validation and no-participant aggregation; insufficient pupil-baseline reference rows; eye-simulator type/range/bounds guardrails and explicit zero invalid-gaze proportion; and biometric-simulator sampling/no-pulse/TTL-disabled behavior;
- all 30 pre-tranche residual `final_deterministic.py` branch paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:33b2dc01ed01c4b1ee8a599e980ab6034fa1922239d7ea6d6a6b447a6cbeda15`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **92.7% to 93.2%**, retaining headroom below the measured **93.5824%** while preventing regression to the prior **93.0461%** tranche level.

### PsPM-style branch tranche

The eleventh 0.1.4 branch/path tranche targets the remaining PsPM-style marker, SCR preprocessing, event/design, GLM, and export control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the final-deterministic tranche: **5,235 / 5,594 branches = 93.5824%**;
- post-tranche exact measured coverage: **5,263 / 5,594 branches = 94.0829%**;
- missing branch paths reduced from **359 to 331** (**28 newly validated paths** in this tranche; **448 cumulatively** since the original 0.1.4 baseline);
- `pspm_style.py`: **121 / 150 branches = 80.667% → 149 / 150 branches = 99.333%**;
- public-API tests cover SCR preprocessing helper guardrails through the exported preprocessor; marker extraction and empty-marker combination; empty and non-reset session splitting; explicit SCR signal and sampling validation; event-segment validation and no-overlap behavior; short/degenerate design timing and non-finite onset behavior; GLM signal/design/interpolation/regressor/complete-row guardrails; and export model/format/no-prediction/JSON-array alternatives;
- the sole residual `pspm_style.py` branch is arc `116 → exit`, the defensive invalid/non-positive sampling-interval guard in private `_kernel()`; repository search confirms its only production caller is `create_gazepoint_pspm_glm_design()`, which first derives differences from unique sorted time points, retains only finite positive intervals, raises if none remain, and then passes their positive median to `_kernel()`; the guard is therefore structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing scientific code solely for nominal branch closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:c8dc94fde8c02a224edad26328de26133bd44bd1d0fd4f578bd6294887df1557`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **93.2% to 93.7%**, retaining headroom below the measured **94.0829%** while preventing regression to the prior **93.5824%** tranche level.

### Roadmap helpers branch tranche

The twelfth 0.1.4 branch/path tranche targets the remaining roadmap helper control-flow debt across event normalization, recovery and pupil-event summaries, tracking, PPG morphology/quality, event import/matching, synchronization, scanpaths, manifests, and template similarity while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the PsPM-style tranche: **5,263 / 5,594 branches = 94.0829%**;
- post-tranche exact measured coverage: **5,291 / 5,594 branches = 94.5835%**;
- missing branch paths reduced from **331 to 303** (**28 newly validated paths** in this tranche; **476 cumulatively** since the original 0.1.4 baseline);
- `roadmap_helpers.py`: **187 / 216 branches = 86.574% → 215 / 216 branches = 99.537%**;
- public-API tests cover SCR recovery and pupil-event windows without recoverable/response samples; pupil-only and combined tracking validity; sparse/invalid-method luminance auditing and automatic close-peak suppression through PPG morphology; PPG-quality empty-window handling; event-log DataFrame/missing-file/explicit-separator paths; event matching invalid-return and no-overlap behavior; invalid column-assertion mode; synchronization vector/DataFrame/target/finite-pair guardrails; scanpath behavior without AOIs, with empty AOIs, and without transitions; manifest validation/no-path/no-output behavior; and template-similarity integer-index peaks plus short-window rejection.
- the sole residual `roadmap_helpers.py` branch is arc `124 → 126`, the explicit `event_label_col` alternative inside private `_standardize_events()`; repository search confirms the exported production callers `summarize_gazepoint_scr_recovery()`, `summarize_gazepoint_pupil_events()`, and `match_gazepoint_events_to_biometrics()` expose/pass event-time and event-id overrides only and never supply the helper's fourth `event_label_col` argument, so this branch is structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:614014e7562b603e490a715b888ef37a3b158cde8e6e9e134f5e7286929dabc6`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **93.7% to 94.2%**, retaining headroom below the measured **94.5835%** while preventing regression to the prior **94.0829%** tranche level.

### QC audits and design branch tranche

The thirteenth 0.1.4 branch/path tranche closes the complete remaining control-flow debt in the QC-audit and experimental-design utilities through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the roadmap-helpers tranche: **5,291 / 5,594 branches = 94.5835%**;
- post-tranche exact measured coverage: **5,319 / 5,594 branches = 95.0840%**;
- missing branch paths reduced from **303 to 275** (**28 newly validated paths** in this tranche; **504 cumulatively** since the original 0.1.4 baseline);
- `qc_audits_design.py`: **136 / 164 branches = 82.927% → 164 / 164 branches = 100.000%**;
- public-API tests cover quality-index metric/type/mapping/weight/collision/all-nonfinite alternatives; beat-audit column/type/range/duplicate/relative-change guardrails; correction-summary input/schema/grouping validation; beat-correction audit/action/output-collision plus local- and group-reference fallback behavior; session-comparability validation; QC-overview quality-index and flag-column validation; condition-free experiment-design behavior and expected-condition validation; and design-coverage plot input validation;
- all 28 pre-tranche residual `qc_audits_design.py` branch paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:199c8ac7c253855d455625bee5307eb821902af4fba291a9537fb47c3fac6ef5`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **94.2% to 94.7%**, retaining headroom below the measured **95.0840%** while preventing regression to the prior **94.5835%** tranche level.

### QC dropouts branch tranche

The fourteenth 0.1.4 branch/path tranche closes the complete remaining control-flow debt in time-reset, dropout/nonwear, filtering, and upsampling utilities through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the QC-audits/design tranche: **5,319 / 5,594 branches = 95.0840%**;
- post-tranche exact measured coverage: **5,347 / 5,594 branches = 95.5846%**;
- missing branch paths reduced from **275 to 247** (**28 newly validated paths** in this tranche; **532 cumulatively** since the original 0.1.4 baseline);
- `qc_dropouts.py`: **216 / 244 branches = 88.525% → 244 / 244 branches = 100.000%**;
- public-API tests cover exact time-column autodetection and nonfinite reindex behavior; short missing and low-variance nonwear runs; nonwear-summary validation; filter signal/method/group/time/window/suffix guardrails, rolling missingness and sparse detrending; and upsampling empty/missing/group/signal/interval/method guardrails, insufficient/duplicate time groups, and sparse-signal interpolation fallback;
- all 28 pre-tranche residual `qc_dropouts.py` branch paths are closed through exported production behavior; private run, rolling, low-variance and interpolation helpers are reached only through exported front doors, so no private-helper-only test or structural residual remains;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:aebdbcc35957bba2d3432dbc4cba32031b0f615069ceda2b182f8df22fc9708d`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **94.7% to 95.2%**, retaining headroom below the measured **95.5846%** while preventing regression to the prior **95.0840%** tranche level.

### Final science bridges branch tranche

The fifteenth 0.1.4 branch/path tranche closes the complete remaining control-flow debt in the final scientific bridge utilities through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the QC-dropouts tranche: **5,347 / 5,594 branches = 95.5846%**;
- post-tranche exact measured coverage: **5,374 / 5,594 branches = 96.0672%**;
- missing branch paths reduced from **247 to 220** (**27 newly validated paths** in this tranche; **559 cumulatively** since the original 0.1.4 baseline);
- `final_science_bridges.py`: **133 / 160 branches = 83.125% → 160 / 160 branches = 100.000%**;
- public-API tests cover automated-statistics validation, mixed-completion and non-Holm paths; cardiorespiratory missing-column, non-standardized and partial-group behavior; bootstrap empty/missing/paired/configuration validation, median contrasts and no-valid-bootstrap behavior; CTSI no-event/no-output alternatives; cvxEDA tau validation and failed/partial optimization; EDA pipeline blueprint/runner guardrails; non-flattened XDF import; online-design validation and previous-assignment/cost alternatives; PsPM DCM default/no-event behavior; and SCR multiverse failed/partial/model-callback paths;
- all 27 pre-tranche residual `final_science_bridges.py` branch paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:1b0888fbe9feb9ce53c87c5cccbe505ad98777231e5e24696a42e413870c838c`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **95.2% to 95.7%**, retaining headroom below the measured **96.0672%** while preventing regression to the prior **95.5846%** tranche level.

### Event frontdoor branch tranche

The sixteenth 0.1.4 branch/path tranche targets the remaining event-frontdoor control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the final-science-bridges tranche: **5,374 / 5,594 branches = 96.0672%**;
- post-tranche exact measured coverage: **5,393 / 5,594 branches = 96.4069%**;
- missing branch paths reduced from **220 to 201** (**19 newly validated paths** in this tranche; **578 cumulatively** since the original 0.1.4 baseline);
- `event_frontdoor.py`: **92 / 112 branches = 82.143% → 111 / 112 branches = 99.107%**;
- public-API tests cover grouping and event-group validation; invalid epoch input; close-peak suppression, sub-threshold SCR rejection and sparse-response AUC behavior; `none`/`center` normalization plus invalid-method validation; engagement group-length/all-nonfinite/scalar alternatives; missingness validation; detrending missing-signal/all-nonfinite and `none`/`mean`/`median` alternatives; and biometrics-file audit validation;
- the sole residual `event_frontdoor.py` branch is arc `61 → 58`, the `if len(before) == 0: continue` defensive path in private `_scr_peaks()`: local maxima are constructed only from `y[1:-1]` and shifted by `+1`, so every candidate index satisfies `ii >= 1` and `before = np.arange(ii)` necessarily has at least one element; the branch is therefore structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing valid scientific code solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:fb2ef4a7c6bf296aeded590c11cd62c9ca37977df5973dab73a3fed780e50d21`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **95.7% to 96.1%**, retaining headroom below the measured **96.4069%** while preventing regression to the prior **96.0672%** tranche level.

### User workflows branch tranche

The seventeenth 0.1.4 branch/path tranche targets the remaining user-workflow plotting, readiness, workflow orchestration, and reporting control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the event-frontdoor tranche: **5,393 / 5,594 branches = 96.4069%**;
- post-tranche exact measured coverage: **5,410 / 5,594 branches = 96.7108%**;
- missing branch paths reduced from **201 to 184** (**17 newly validated paths** in this tranche; **595 cumulatively** since the original 0.1.4 baseline);
- `user_workflows.py`: **346 / 366 branches = 94.536% → 363 / 366 branches = 99.180%**;
- public-API tests cover points-only/no-legend biometric signal plots; ungrouped and empty explicit quality summaries; dashboard omission of time-reset plots; empty SCR peak overlays; hidden multimodal event markers; specification curves without a zero line; readiness without a detected time column; explicit sampling groups with exclusion recommendations disabled; existing recommendation columns in report tables; report-bundle non-Figure entries with README/session files disabled; and report creation without an output file;
- the three residual `user_workflows.py` branches are structural defensive paths rather than missing exported behavior: arc `278 → 282` cannot follow the earlier non-empty audit requirement plus `max_groups >= 1` group selection; arc `582 → 584` cannot occur for normal produced HRV feature rows because `extract_gazepoint_hrv_features()` always includes `mean_ibi_ms` and does not emit `mean_ibi_sec`; and arc `673 → 672` cannot occur because all requested/inferred factor and random-effect columns are guaranteed present before the loop;
- those guards are retained rather than manufacturing private-helper tests or changing valid production code solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:a04e6ab2e58e08fdf4100635022e7d993ce7d5eaa083626f3a3cf55c2640449d`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **96.1% to 96.5%**, retaining headroom below the measured **96.7108%** while preventing regression to the prior **96.4069%** tranche level.

### Governance core branch tranche

The eighteenth 0.1.4 branch/path tranche closes the complete remaining control-flow debt in governance, audit-trail, export-inventory, dataset-structure, and sidecar-template utilities through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the user-workflows tranche: **5,410 / 5,594 branches = 96.7108%**;
- post-tranche exact measured coverage: **5,427 / 5,594 branches = 97.0147%**;
- missing branch paths reduced from **184 to 167** (**17 newly validated paths** in this tranche; **612 cumulatively** since the original 0.1.4 baseline);
- `governance_core.py`: **143 / 160 branches = 89.375% → 160 / 160 branches = 100.000%**;
- public-API tests cover audit-index inclusion of check and summary tables; empty-summary Markdown rendering; export-inventory recursion/path validation and event, biometrics, JSON-sidecar and unknown-file classification; dataset-structure root/boolean/expected-directory/expected-file validation plus no-pattern/no-extension/no-sidecar-check behavior; and sidecar-template scalar/boolean/custom-field validation plus the no-custom-fields path;
- all 17 pre-tranche residual `governance_core.py` branch paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating corrected measured-head artifact is bound by digest `sha256:4e3bbb76d40ff7867a5288c52b201cf9619710d62c0faa2c9957137fefbd520c`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **96.5% to 96.8%**, retaining headroom below the measured **97.0147%** while preventing regression to the prior **96.7108%** tranche level.

### Remaining core branch tranche

The nineteenth 0.1.4 branch/path tranche targets the remaining preprocessing, smoothing, IBI-filtering, HR↔IBI consistency, and HRV feature-extraction control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the governance-core tranche: **5,427 / 5,594 branches = 97.0147%**;
- post-tranche exact measured coverage: **5,443 / 5,594 branches = 97.3007%**;
- missing branch paths reduced from **167 to 151** (**16 newly validated paths** in this tranche; **628 cumulatively** since the original 0.1.4 baseline);
- `remaining_core.py`: **191 / 208 branches = 91.827% → 207 / 208 branches = 99.519%**;
- public-API tests cover explicit baseline-signal selection with zero inclusion and no validity column; smoothing without NA removal; IBI-filter missing time/validity and invalid-bound guardrails, singleton groups and ungrouped summaries; HR↔IBI missing-column/time guardrails and ungrouped summaries; and HRV missing-column handling plus singleton repeated-interval collapse and ungrouped output;
- the sole residual `remaining_core.py` branch is arc `126 → 128`, the false branch of the final `elif artifact_type == "drift"` in `simulate_gazepoint_artifact()`: the exported front door first validates `artifact` against the exhaustive set `missing_run`, `flatline`, `spike`, `noise`, and `drift`, so once execution reaches that final `elif`, a false branch would require an already-rejected unsupported artifact type; the branch is therefore structurally unreachable through valid exported behavior and is retained rather than manufacturing a private-helper test or changing production solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:03b0acda0e232b8a303071d1ae47461192588d10d51964f356cd828adcbb0858`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **96.8% to 97.1%**, retaining headroom below the measured **97.3007%** while preventing regression to the prior **97.0147%** tranche level.

### Compatibility branch tranche

The twentieth 0.1.4 branch/path tranche targets compatibility-layer column standardization, pupil interpolation, and mixed-model preparation control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the remaining-core tranche: **5,443 / 5,594 branches = 97.3007%**;
- post-tranche exact measured coverage: **5,458 / 5,594 branches = 97.5688%**;
- missing branch paths reduced from **151 to 136** (**15 newly validated paths** in this tranche; **643 cumulatively** since the original 0.1.4 baseline);
- `compatibility.py`: **56 / 72 branches = 77.778% → 71 / 72 branches = 98.611%**;
- public-API tests cover non-data-frame and empty inputs, invalid conflict mode and conflict=`keep` standardization; short/degenerate time vectors, complete pupil data, too-sparse pupil data and edge gaps; interpolation method/pupil/time/blink validation; and mixed-model missing requested columns, disabled outcome dropping and disabled numeric scaling;
- the sole residual `compatibility.py` branch is arc `36 → exit`, private `_unique_name()`'s early return when `target` is absent from `existing`: its only production caller invokes `_unique_name()` only inside a preceding `if target in ...` branch and passes that same competing-name list, so the target-absent path is structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing production solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:11a4cb2973fc86c58d634701230d006829e21589ead108ca9d2ed221a49ef3f2`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **97.1% to 97.4%**, retaining headroom below the measured **97.5688%** while preventing regression to the prior **97.3007%** tranche level.

### Advanced physiology branch tranche

The twenty-first 0.1.4 branch/path tranche targets the remaining advanced physiology control flow through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the compatibility tranche: **5,458 / 5,594 branches = 97.5688%**;
- post-tranche exact measured coverage: **5,470 / 5,594 branches = 97.7833%**;
- missing branch paths reduced from **136 to 124** (**12 newly validated paths** in this tranche; **655 cumulatively** since the original 0.1.4 baseline);
- `advanced_physiology.py`: **111 / 124 branches = 89.516% → 123 / 124 branches = 99.194%**;
- public-API tests cover insufficient-beat IPFM behavior; explicit millisecond and second external-EDA time units; response-pattern failure when no EDA response column can be inferred; bilateral EDA asymmetry without a time column; quantization-noise output-collision protection; insufficient-complete and unscaled EDR-PCA paths; and skin-potential non-finite/zero threshold plus positive and negative response-direction alternatives;
- the sole residual `advanced_physiology.py` branch is arc `60 → 65`, the zero-iteration exit of private `_simple_kmeans_1d()`'s fixed iteration loop: the helper's `iters` argument is not exposed by the exported beat-extraction front door, and its sole production caller uses the helper default `iters=50`, so a zero-iteration path is structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper test or changing production solely for nominal closure;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:3accd5d6c1d4daaf9974211b19f615debccc5956bd1bb4b0a0b7bf4052025131`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **97.4% to 97.6%**, retaining headroom below the measured **97.7833%** while preventing regression to the prior **97.5688%** tranche level.

### Alignment and AOI branch tranche

The twenty-second 0.1.4 branch/path tranche closes the complete remaining control-flow debt in stream alignment, AOI timecourses, event-locked multimodal summaries, and quality-dashboard validation through exported APIs while retaining the production scientific implementation unchanged.

- pre-tranche measurement inherited from the advanced-physiology tranche: **5,470 / 5,594 branches = 97.7833%**;
- post-tranche exact measured coverage: **5,483 / 5,594 branches = 98.0157%**;
- missing branch paths reduced from **124 to 111** (**13 newly validated paths** in this tranche; **668 cumulatively** since the original 0.1.4 baseline);
- `alignment_aoi.py`: **61 / 74 branches = 82.432% → 74 / 74 branches = 100.000%**;
- public-API tests cover nonnumeric event-vector fallback and invalid alignment method; zero-pair and all-nonfinite-pair alignment failures; AOI-definition, grouping-column, bin-width and explicit AOI-column validation; all-nonfinite AOI time groups and `include_empty=False`; event-locked group mismatch and no-window-overlap paths; and quality-dashboard title validation;
- all 13 pre-tranche residual `alignment_aoi.py` paths are closed through exported production behavior; no private-helper-only test is needed and no structural residual remains in this module;
- no file under `src/gpbiometricspy/` is changed by this tranche;
- whole-package statement coverage remains **10,316 / 10,316 = 100.000%**;
- exact evidence is retained as the 30-day `branch-coverage-python-3.13` artifact; the validating measured-head artifact is bound by digest `sha256:6d8f635e83b2274a832051484fa7b2f82711f1de890bb3a768e4029fe592da09`;
- the frozen 406-export semantic contract, deep R↔Python parity, optional-backend interoperability, and CodeQL requirements remain unchanged;
- the persistent pure branch-coverage regression floor is raised conservatively from **97.6% to 97.8%**, retaining headroom below the measured **98.0157%** while preventing regression to the prior **97.7833%** tranche level.
