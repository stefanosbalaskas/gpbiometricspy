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

## 0.1.1.dev0 deep-validation tranche

Development after the stable freeze adds evidence rather than silently changing the frozen R contract:

1. paired R/Python golden fixtures for deterministic numerical families;
2. optional-backend floor/current CI for HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf;
3. executable Python companions for all 26 frozen R articles/vignettes;
4. a repository-safe real-data validation CLI and manual workflow;
5. CodeQL, Dependabot and contribution/issue templates.

Latest local `0.1.1.dev0` regression evidence after adding these layers:

- **209 / 209** Python tests: **PASS**
- whole-package statement coverage: **90.75%**
- exact export audit: **406 / 406 implemented, 0 pending — PASS**
- Python 3.11 grammar audit: **PASS**
- `compileall` across `src/`, `tests/`, `scripts/` and `examples/`: **PASS**
- executable article companions: **26 / 26 — PASS**
- development wheel build + isolated import/export smoke: **PASS**
- documentation relative-link/nav audit: **PASS, 0 broken/missing targets**
- R golden comparison and optional-backend floor/current matrix: **live GitHub CI gates after push**
- private participant-data validation: **not claimed without a user-supplied private dataset**

The golden-fixture harness writes independent R and Python result JSON files and compares recursively with explicit absolute/relative tolerances. It is intentionally separate from ordinary Python unit tests so cross-runtime disagreements cannot be hidden by shared implementation code.

The real-data workflow is opt-in. Private Gazepoint exports remain outside Git and are supplied only at execution time. The workflow/reporting code checks paths and output locations to reduce accidental repository disclosure.

## Meaning of parity

The 406-function freeze means the complete frozen R export surface has a Python implementation and direct Python-test evidence. It does **not** claim that every optional external-library call is bit-identical across every operating system, library release or numerical backend. Cross-runtime fixtures and optional-backend CI are maintained as additional evidence layers.
