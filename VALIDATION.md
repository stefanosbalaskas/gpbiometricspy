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

## Stable 0.1.2 public release and archival evidence

- immutable GitHub tag: `v0.1.2`;
- public PyPI release: `gpbiometricspy 0.1.2`;
- Zenodo version DOI: `10.5281/zenodo.22150873`;
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
