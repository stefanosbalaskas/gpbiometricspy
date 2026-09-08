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

## Stable freeze: 0.1.5 measurement accountability, replay reliability, and release readiness

Version 0.1.5 freezes the completed validation/reliability line while preserving the **406/406, 0 pending** `gpbiometrics 2.0.0` scientific contract.

### Frozen in 0.1.5

- metric-specific ECG-HRV/PPG-PRV agreement, SCR responsivity sensitivity, a five-stage validation ladder, and experimental topology-aware PPG structural descriptors with conservative interpretation boundaries;
- **567 tests** and **10,456 / 10,456 = 100.00% statement coverage**;
- **5,629 / 5,648 = 99.6636% raw branch coverage**, a **99.6000%** raw floor, exactly **19** reviewed structural arcs, and **0 unexpected / 0 stale / 0 unaudited** debt;
- fail-closed branch-auditor pipeline behavior through Bash `pipefail`;
- installed Studio wheel/sdist Chromium validation on Python 3.11 and 3.14 across local/public CLI entrypoints, physiology, external event alignment, multimodal/model preparation, and cluster-permutation replay;
- deterministic replay identity checks for primary data, event logs, and target streams, including wrong/missing-resource rejection without serializing raw secondary paths;
- production-compatible upload synchronization and preservation of the synthetic-only public deployment boundary;
- independent R↔Python golden parity, optional-backend interoperability, private real-data validation, CodeQL, docs, and Studio release gates.

### Remaining release completion

1. qualify the exact stable-freeze PR head and merge only that pinned SHA;
2. require all ten exact-main stable-release gate families to succeed on the merged stable commit;
3. allow the protected tag cutter to create immutable `v0.1.5` only from that exact qualified commit;
4. verify GitHub Release assets, SHA-256 manifest, protected PyPI Trusted Publishing, and clean public-index installation;
5. wait for Zenodo ingestion before recording any 0.1.5 version DOI;
6. retain concept DOI `10.5281/zenodo.22150872`, previous 0.1.4 DOI `10.5281/zenodo.22515782`, and R-reference `isDerivedFrom` provenance;
7. return `main` to a new development version only after public-release and archival closeout.
