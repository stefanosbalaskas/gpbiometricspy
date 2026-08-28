# Roadmap

## Completed: 0.1.0 parity and public release

- frozen `gpbiometrics 2.0.0` 406-export surface implemented: **406/406, 0 pending**;
- Python suite and ≥90% coverage gate;
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

## 0.1.2 release tranche — visual documentation and archival

- first-class Examples and package-generated Plot Gallery;
- all 26 curated executable article companions preserved through docs generation;
- Zenodo integration enabled with versioned `.zenodo.json` and explicit R-reference provenance;
- GitHub About/topics/language metadata and non-disruptive `main` protection;
- stable `v0.1.2` released to GitHub/PyPI and archived at Zenodo version DOI `10.5281/zenodo.22150873` under concept DOI `10.5281/zenodo.22150872`.

## Longer-term work

1. expand golden fixtures when a numerical edge case is discovered or a backend changes materially;
2. deepen branch coverage in complex modelling/reporting workflows toward 95%+ without gaming the metric;
3. validate on additional privately held real Gazepoint export profiles without committing participant data;
4. add archival DOI/provenance metadata if a Zenodo release archive is created;
5. adopt a later `gpbiometrics` release only through a new explicit semantic reference freeze.
