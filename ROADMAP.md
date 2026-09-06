# Roadmap

## Completed: 0.1.0 parity and public release

- frozen `gpbiometrics 2.0.0` 406-export surface implemented: **406/406, 0 pending**;
- Python suite and >=90% coverage gate;
- Linux / Windows / macOS CI across Python 3.11–3.14;
- Python 3.11 grammar and pandas 3 compatibility hardening;
- MkDocs documentation and 406-function generated API reference;
- GitHub `v0.1.0` stable release;
- PyPI Trusted Publishing with exact GitHub/PyPI artifact hashes;
- fresh public-index install smoke;
- GitHub Pages publication over HTTPS.

## Completed: 0.1.1 deep validation and release hardening

- paired R/Python numerical golden fixtures with tolerance comparison;
- floor/current optional-backend interoperability CI;
- executable Python companions for all 26 frozen R articles/vignettes;
- privacy-preserving real-data validation tooling;
- CodeQL, Dependabot and repository contribution templates;
- release-to-PyPI handoff hardening with exact-commit gate verification and explicit protected workflow dispatch.

## Completed: 0.1.2 visual documentation and archival

- first-class Examples and package-generated Plot Gallery;
- all 26 curated executable article companions preserved through docs generation;
- Zenodo integration enabled with versioned `.zenodo.json` and explicit R-reference provenance;
- GitHub About/topics/language metadata and non-disruptive `main` protection;
- stable `v0.1.2` released to GitHub/PyPI and archived at Zenodo version DOI `10.5281/zenodo.22150873` under concept DOI `10.5281/zenodo.22150872`.

## Completed: 0.1.3 gpbiometricspy Studio

- **gpbiometricspy Studio**, a Shiny for Python application layer over public package APIs;
- project intake/foundation QC, advanced QC, annotation, EDA/SCR, PPG/HR/HRV, pupil, gaze/fixation/AOI, events/alignment, multimodal analysis, statistics/modelling, and reporting/reproducibility workflows;
- Guided/Expert modes, provenance-aware state, exports, reproducible Python scripts, privacy-preserving project recipes, and interpretation guardrails;
- a synthetic-only fail-closed public deployment boundary plus full local/authenticated research-data mode;
- Chromium browser E2E, production/deployment smoke metrics, responsive/accessibility regression guards, and Connect-style deployment files;
- distributable `studio` package content and installed Studio launch commands while keeping application code separate from `src/gpbiometricspy`;
- README/MkDocs Studio launch surface and exact-commit Studio release gates.

## Completed: 0.1.4 branch-path validation and release hardening

- **557 scientific regression tests** with literal **10,316 / 10,316 = 100.00% statement coverage**;
- raw branch coverage raised to **5,575 / 5,594 = 99.6604%** without changing scientific semantics solely to manufacture coverage;
- the remaining **19** structural/caller-dominated arcs frozen in a machine-readable audit ledger;
- **0 unaudited branch debt** and **5,594 / 5,594 = 100.0000% audited branch accounting**;
- exact-main branch-coverage release gating alongside tests, docs, deep parity, interoperability, CodeQL, private real-data validation and Studio gates;
- stable `v0.1.4` released to GitHub/PyPI and archived at Zenodo version DOI `10.5281/zenodo.22515782` under concept DOI `10.5281/zenodo.22150872`.

## Active: 0.1.5.dev0 reliability and high-value workflow validation

Development continues from the frozen 406-export scientific contract. Current priorities are application reliability and evidence expansion rather than API churn:

1. extend Studio browser coverage from shell/reporting smoke into high-value scientific analysis paths, beginning with Gaze fixation/saccade execution, package-native diagnostic rendering and downloadable outputs;
2. retain the Studio render-boundary adapter for package APIs that intentionally return structured plot bundles while preserving those public scientific return contracts;
3. expand golden fixtures when a numerical edge case is discovered or an optional backend changes materially;
4. deepen branch-path validation in complex modelling/reporting workflows without gaming coverage metrics;
5. validate on additional privately held real Gazepoint export profiles without committing participant data;
6. extend authenticated/deployment browser validation where suitable infrastructure is available;
7. adopt a later `gpbiometrics` release only through a new explicit semantic reference freeze.
