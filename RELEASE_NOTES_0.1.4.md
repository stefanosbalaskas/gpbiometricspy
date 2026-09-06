# gpbiometricspy 0.1.4 — branch-path validation and release hardening

`gpbiometricspy 0.1.4` preserves the frozen **gpbiometrics 2.0.0** scientific contract while substantially strengthening executable path validation and release governance.

## Scientific contract

- **406 / 406** frozen R exports implemented; **0 pending**.
- **557** scientific regression tests.
- **10,316 / 10,316 statements = 100.00%** with a 100% statement CI floor.
- No intended scientific API redesign in this release line.

## Branch/path validation

- Raw pure branch coverage increased from the original 0.1.4 baseline **4,815 / 5,594 = 86.0744%** to **5,575 / 5,594 = 99.6604%**.
- **760** additional branch paths were validated through exported/public behavior where genuinely reachable.
- The remaining **19** raw arcs are explicitly reviewed structural/caller-dominated or dominated defensive paths.
- CI enforces an exact machine-readable structural-debt contract: **0 unexpected**, **0 stale**, and **0 unaudited branch debt**.
- Audited accounting is **5,594 / 5,594**, while the release continues to report the literal raw Coverage.py branch metric as **99.6604%** rather than relabelling it as 100%.

## Release integrity

- Branch/structural coverage is now a first-class exact-commit stable-release gate alongside the OS×Python matrix, docs, CodeQL, deep parity, interoperability, private-data validation, and Studio gates.
- `pyproject.toml` changes trigger the branch audit so dependency/runtime metadata cannot bypass path validation.
- Release identity is synchronized across package metadata, runtime `__version__`, `.zenodo.json`, `CITATION.cff`, generated documentation metadata, README/site, changelog, and validation records.
- `CITATION.cff` deliberately contained no 0.1.4 version DOI before Zenodo ingestion; the minted DOI is recorded in the post-release archival record below.

## Studio and interoperability

The packaged Shiny for Python Studio, synthetic-only public boundary, Chromium E2E checks, production/distribution checks, deep R/Python parity, and optional-backend interoperability gates remain part of the stable release contract.

## Post-release archival record

- PyPI: `gpbiometricspy 0.1.4` published through protected Trusted Publishing with Sigstore attestations.
- GitHub/PyPI wheel SHA-256: `88f84908f91bedf9e9ebef1a144e593dfc623bd1f65db757ec91858c0c966add`.
- GitHub/PyPI sdist SHA-256: `78df06e7fd43c87b68351451e92368d9ccf6428cbb27bb09caaa0d253f66e1ab`.
- Zenodo version DOI: **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**.
- Zenodo software concept DOI: **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**.
- Previous 0.1.3 version DOI: **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**.
- The immutable `v0.1.4` tag and released distributions remain unchanged; live repository development advances separately.
