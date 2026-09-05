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
- missing branch paths reduced from **666 to 613** (**53 newly validated paths** in this tranche; **166 cumulatively** since the 0.1.4 baseline);
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
- the sole residual `endgame_science.py` branch is the defensive short-input guard in private `_match_count()`: repository search confirms its only production caller first requires coarse-grained length `>= m + 2`, which necessarily satisfies both subsequent `_match_count(..., m, ...)` and `_match_count(..., m + 1, ...)` minimum-length conditions; the guard is therefore structurally unreachable through exported production behavior and is retained rather than manufacturing a private-helper coverage test or changing production solely for a coverage number;
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
