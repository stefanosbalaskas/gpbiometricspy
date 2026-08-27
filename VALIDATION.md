# gpbiometricspy validation status

Frozen semantic reference: **gpbiometrics 2.0.0**.

## Frozen reference inventory

- 406 R exports
- 144 R source files
- 403 Rd help files
- 120 R test files, including `tests/testthat.R`
- 26 vignette/article sources
- 39 `inst/extdata` files

## Python parity freeze

- **406 / 406** frozen R exports implemented
- **0** pending exports
- exact export-set audit: **PASS**
- **204 / 204** Python tests: **PASS**
- every frozen export explicitly referenced by Python tests: **406 / 406**
- exports explicitly referenced by the frozen R tests: **378 / 406**
- exports documented in frozen Rd help: **406 / 406**
- whole-package statement coverage: **90.45%**
- required coverage threshold: **90% — PASS**
- `compileall`: **PASS**
- synthetic kiosk demo: **69,120 rows / 36 participants — PASS**
- wheel clean-install smoke: **PASS**
- sdist clean-install smoke: **PASS**
- documentation relative-link audit: **PASS, 0 broken links**

The wheel contains the complete Python runtime package and all 39 synthetic-demo files. The source distribution additionally retains the frozen R reference: 144 R source files, 403 Rd files, 120 R test files and 26 Rmd vignette/article sources.

## Tooling limitation in this sandbox

Ruff, MkDocs, Twine and the `build` frontend were not installed in this execution environment and package installation from the internet was blocked. The repository contains CI workflows that install and execute these release tools. Local wheel/sdist creation was performed directly through the installed setuptools PEP 517 backend and both artifacts were subsequently installed and smoke-tested in isolated targets.

## Meaning of parity

The 406-function freeze means the complete frozen R export surface has a Python implementation and test evidence. It does **not** claim that every optional external-library call will be bit-identical across all versions, operating systems or numerical backends. The original R implementation/tests/documentation are retained under `reference/` specifically so continued deep-parity audits remain reproducible.
