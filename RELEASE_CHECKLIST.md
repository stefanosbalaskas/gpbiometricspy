# Release checklist

## 0.1.0 — completed

- [x] Exact R export audit reports 406/406 implemented and 0 pending.
- [x] `compileall` passes.
- [x] Full pytest suite passes with coverage ≥90%.
- [x] Every frozen export remains directly referenced by a Python test.
- [x] Synthetic kiosk demo loads 69,120 rows / 36 participants.
- [x] Generated API reference contains 406 function entries.
- [x] Article migration catalog contains 26 companions.
- [x] Ruff passes in CI.
- [x] MkDocs strict build passes in CI.
- [x] Wheel and sdist build successfully.
- [x] Twine metadata check passes in CI.
- [x] Fresh wheel/public-PyPI install smoke passes.
- [x] Stable wheel/sdist hashes match between GitHub Release and PyPI.
- [x] Changelog, citation and version metadata were synchronized for the stable release.
- [x] Annotated `v0.1.0` tag and non-prerelease GitHub release were created from the validated commit.
- [x] PyPI publication occurred only after release gates passed.
- [x] GitHub Pages is enabled from `gh-pages` `/` with HTTPS.

## 0.1.1 — stable release gates

- [x] Core tests, exact export audit and coverage remain green (211 tests; 406/406 exports; 0 pending; coverage >=90%).
- [x] R/Python golden-fixture workflow passes.
- [x] Optional-backend floor/current interoperability workflow passes 14/14.
- [x] All 26 executable tutorial companions pass.
- [x] Privacy-safe representative real-data harness passes without committing participant data.
- [x] CodeQL, Dependabot configuration and repository security automation are present/green.
- [x] Stable release notes distinguish validation/documentation changes from semantic API changes.
- [x] Release workflow verifies the exact validated commit before creating the GitHub Release.
- [x] Release workflow explicitly dispatches protected PyPI Trusted Publishing after GitHub Release creation.
- [ ] Optional additional evidence: validate against an approved genuine participant Gazepoint export locally or on an approved private runner. This is not a public-release blocker and is not claimed by the package.

## 0.1.2 — Zenodo-backed release preparation

- [x] Zenodo GitHub integration is enabled for `stefanosbalaskas/gpbiometricspy`.
- [x] `CITATION.cff` contains ORCID, affiliation, abstract and software keywords.
- [x] `.zenodo.json` declares software/open/MIT metadata and links the frozen R reference DOI `10.5281/zenodo.21434608` as `isDerivedFrom`.
- [x] README/site clearly distinguished stable `0.1.1` from development `0.1.2.dev0` during preparation; the stable freeze now identifies `0.1.2` as the release source.
- [x] Release workflow validates archival metadata before building a stable release.
- [x] Promote `0.1.2.dev0` to stable `0.1.2` only after the development tranche is intentionally frozen.
- [x] Create annotated `v0.1.2` only from the exact fully validated stable commit.
- [x] Wait for Zenodo to ingest the GitHub release and confirm the software record is published.
- [x] Record the Zenodo **version DOI** `10.5281/zenodo.22150873` for `v0.1.2` and software **concept DOI** `10.5281/zenodo.22150872`.
- [x] Add the Python concept DOI badge/link to README and documentation; add the release DOI to release-specific citation metadata where appropriate.
- [x] Verify the Zenodo record preserves the R-reference `isDerivedFrom` relation without presenting the R DOI as the Python DOI.
- [ ] Verify Software Heritage archival status once Zenodo reports it under external resources.

## 0.1.3 — Studio release gates

- [x] Scientific core remains frozen at 406/406 implemented exports and 0 pending exports.
- [x] Scientific package validation remains at literal 100% statement coverage across Ubuntu/Windows/macOS and Python 3.11–3.14.
- [x] gpbiometricspy Studio provides the complete planned application navigation: intake/QC, annotation, EDA/SCR, PPG/HR/HRV, pupil, gaze/fixation/AOI, events/alignment, multimodal, statistics/modelling, and reporting/reproducibility.
- [x] Studio smoke validation runs on Python 3.11 and 3.14.
- [x] Chromium Studio E2E validation runs on Python 3.11 and 3.14.
- [x] Public synthetic-demo mode removes upload affordances and independently fails closed for external biometric/AOI/event/secondary-stream/project-recipe inputs.
- [x] Production/deployment smoke validation reconstructs dependencies from root `requirements.txt` and records synthetic runtime metrics.
- [x] Studio is included in wheel/sdist packaging as a separate top-level application package with installed `gpbiometricspy-studio` and `gpbiometricspy-studio-public` launchers.
- [x] README/MkDocs expose a first-class Studio guide and distinguish public synthetic use from full local/authenticated research-data use.
- [x] Stable release workflow requires exact-main Studio smoke, browser E2E, and production/distribution success in addition to the existing scientific/docs/security/parity/interoperability/private-data gates.
- [x] Merge the Studio launch/release-hardening tranche and confirm all pull-request gates are green.
- [x] Freeze package, `__version__`, Zenodo, citation, README/site and changelog metadata to stable `0.1.3` without inventing a pre-ingestion Zenodo version DOI.
- [ ] Require every stable-release gate to succeed on the exact stable `main` commit.
- [ ] Create immutable `v0.1.3` from that exact commit and let the protected release workflow build/check/publish artifacts.
- [ ] Confirm GitHub Release assets and SHA-256 manifest.
- [ ] Confirm PyPI `gpbiometricspy==0.1.3` is public and fresh-index installable.
- [ ] Wait for Zenodo ingestion; record the new `0.1.3` version DOI while retaining concept DOI `10.5281/zenodo.22150872` and R-reference `isDerivedFrom` provenance.

### 0.1.3 post-release closeout

- [x] Protected PyPI Trusted Publishing completed successfully.
- [x] Public PyPI JSON hashes match the GitHub Release wheel and sdist.
- [x] Clean public-index installs passed on Python 3.11 and 3.14, including Studio launchers.
- [x] Zenodo ingested `v0.1.3`; version DOI: `10.5281/zenodo.22313884`.
- [x] Concept DOI remains `10.5281/zenodo.22150872`.
- [x] Move repository development identity to `0.1.4` after the immutable 0.1.3 release.

## 0.1.4 — branch validation and stable-release preparation

- [x] Preserve the frozen `gpbiometrics 2.0.0` semantic contract at **406/406 implemented exports, 0 pending**.
- [x] Preserve literal statement coverage at **10,316/10,316 = 100.00%** with the statement CI floor remaining **100%**.
- [x] Expand the scientific regression suite to **557 passing tests**.
- [x] Complete the branch/path validation campaign from **4,815/5,594 = 86.0744%** to **5,575/5,594 = 99.6604%**, validating **760** additional paths through public behavior where reachable.
- [x] Freeze the exact remaining **19** structural/caller-dominated arcs in a machine-readable contract rather than manufacturing private-helper tests or altering scientific semantics for nominal coverage.
- [x] Enforce **0 unexpected**, **0 stale**, and **0 unaudited** missing branch debt in CI, with **5,594/5,594 = 100.0000% audited branch accounting** while retaining the honest raw metric.
- [x] Keep the persistent pure branch regression floor at **99.6%**.
- [x] Add `branch-coverage.yml` and its structural-debt audit as an exact-commit prerequisite in both the automatic stable tag cutter and the exact-tag release workflow.
- [x] Refresh README/changelog/release-facing development validation status without changing the current public stable identity before the separate stable freeze.
- [x] Promote the qualified 0.1.4 development identity to stable `0.1.4` only after the release-hardening tranche merged green.
- [x] Synchronize stable package, runtime `__version__`, Zenodo metadata, CFF citation metadata, generated documentation metadata, README/site, changelog, release notes and checklist without inventing a pre-ingestion 0.1.4 Zenodo version DOI.
- [x] Require every stable-release gate—including the new branch/structural audit—to succeed on the exact stable `main` commit.
- [x] Create immutable annotated `v0.1.4` only from that exact fully validated stable commit.
- [x] Confirm release workflow builds/checks wheel and sdist, validates Studio inclusion, smoke-installs both distributions, and publishes SHA-256 manifest/GitHub Release assets.
- [x] Confirm protected PyPI Trusted Publishing publishes `gpbiometricspy==0.1.4`; both distributions returned HTTP 200 and Sigstore attestations were logged.
- [x] Wait for Zenodo ingestion and record the actual 0.1.4 version DOI while retaining concept DOI `10.5281/zenodo.22150872` and R-reference `isDerivedFrom` provenance.

### 0.1.4 post-release closeout

- [x] Immutable annotated `v0.1.4` resolves to exact qualified commit `3b45a4698d8c3accd989ced0513058ef5d11d3fb`.
- [x] Protected PyPI Trusted Publishing completed successfully for `gpbiometricspy 0.1.4` with Sigstore/Rekor attestations.
- [x] GitHub Release and PyPI wheel SHA-256 match: `88f84908f91bedf9e9ebef1a144e593dfc623bd1f65db757ec91858c0c966add`.
- [x] GitHub Release and PyPI sdist SHA-256 match: `78df06e7fd43c87b68351451e92368d9ccf6428cbb27bb09caaa0d253f66e1ab`.
- [x] Zenodo ingested `v0.1.4`; version DOI: `10.5281/zenodo.22515782`.
- [x] Concept DOI remains `10.5281/zenodo.22150872`; previous 0.1.3 DOI remains `10.5281/zenodo.22313884`.
- [x] Return live repository identity to development as `0.1.5.dev0` while keeping `CITATION.cff` pinned to stable `0.1.4` + DOI `10.5281/zenodo.22515782`.

## 0.1.5.dev0 — reliability, measurement accountability, and release readiness

- [x] Preserve the frozen `gpbiometrics 2.0.0` semantic contract at **406/406 implemented exports, 0 pending**.
- [x] Add measurement-accountability methods for derived-metric HRV/PRV agreement, SCR responsivity sensitivity, validation-ladder evidence, and experimental topology-aware PPG morphology without changing the frozen export contract.
- [x] Extend Studio browser validation into installed wheel/sdist scientific replay paths, including primary/secondary resource fingerprint guards and deterministic exact-status upload synchronization.
- [x] Validate installed scientific replay across the high-value physiology, gaze/pupil, events/alignment, multimodal/modelling, and cluster-permutation paths on Python 3.11 and 3.14 production boundaries.
- [x] Make branch-coverage enforcement fail closed through `tee` rather than allowing a non-zero auditor exit to be masked by the pipeline.
- [x] Cover the newly reachable non-finite `ppg_topology_features()` branch rather than adding it to structural debt.
- [x] Rebase current development branch evidence to **567 passing tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**.
- [x] Preserve exactly **19** reviewed structural/caller-dominated arcs with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt; audited accounting remains **5,648/5,648 = 100.0000%** while raw branch coverage remains explicitly 99.6636%.
- [x] Add unreleased `0.1.5.dev0` release notes/changelog material and keep stable citation metadata pinned to **0.1.4 / 10.5281/zenodo.22515782** until an intentional stable freeze and actual Zenodo ingestion occur.
- [ ] Merge the 0.1.5.dev0 release-readiness documentation tranche and require its exact merged `main` SHA to pass every workflow actually triggered by the documentation-only change.
- [ ] Intentionally promote `0.1.5.dev0` to stable `0.1.5` only in a separate stable-freeze tranche that synchronizes package/runtime/archival/generated metadata without inventing a pre-ingestion Zenodo version DOI.
- [ ] Require every stable-release gate to succeed on the exact stable `main` commit before creating `v0.1.5`.
- [ ] Create immutable annotated `v0.1.5`, let the protected release workflow build/check GitHub assets, and verify the SHA-256 manifest.
- [ ] Confirm protected PyPI Trusted Publishing publishes `gpbiometricspy==0.1.5` and fresh public-index installs succeed.
- [ ] Wait for Zenodo to ingest the immutable GitHub release; record the actual 0.1.5 version DOI while retaining concept DOI `10.5281/zenodo.22150872` and R-reference `isDerivedFrom` provenance.
