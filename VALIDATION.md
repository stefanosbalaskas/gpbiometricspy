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
- stable-candidate wheel PEP 517 build via pip with the installed setuptools backend: **PASS**
- stable-candidate wheel clean-install/import/export smoke: **PASS**
- stable sdist build and Twine validation: **release-workflow gate (not locally runnable because `build`/`twine` are absent in this sandbox)**
- prior `0.1.0.dev1` wheel + sdist build/Twine/GitHub Release/PyPI publication chain: **PASS**
- documentation relative-link audit: **PASS, 0 broken links**
- pandas 4 forward-warning audit for the previously identified single-column groupby sites: **PASS, 0 warnings in the full suite**

The wheel contains the complete Python runtime package and all 39 synthetic-demo files. The source distribution additionally retains the frozen R reference: 144 R source files, 403 Rd files, 120 R test files and 26 Rmd vignette/article sources.

## Tooling limitation in this sandbox

Ruff, MkDocs, Twine and the `build` frontend were not installed in this execution environment and package installation from the internet was blocked. The repository contains CI workflows that install and execute these release tools. For the stable `0.1.0` candidate, a wheel was built through pip using the installed setuptools PEP 517 backend with build isolation disabled, then installed into an isolated target and import/export-smoke-tested successfully. Stable sdist construction and Twine validation remain mandatory GitHub release-workflow gates. The preceding `0.1.0.dev1` release already passed GitHub `python -m build`, Twine, exact-hash PyPI publication and a fresh public-index install/import smoke test.

## Meaning of parity

The 406-function freeze means the complete frozen R export surface has a Python implementation and test evidence. It does **not** claim that every optional external-library call will be bit-identical across all versions, operating systems or numerical backends. The original R implementation/tests/documentation are retained under `reference/` specifically so continued deep-parity audits remain reproducible.

## Public distribution evidence

The `0.1.0.dev1` prerelease was published to PyPI through GitHub OIDC Trusted Publishing. The PyPI wheel and sdist SHA-256 digests matched the corresponding immutable GitHub Release assets exactly, and a fresh public-index installation/import smoke test passed on Windows with Python 3.11 and pandas 3.0.5. The stable `0.1.0` candidate retains that distribution path and is gated by the same cross-platform test, documentation, GitHub Release and PyPI environment controls.
