# gpbiometricspy 0.1.3

`0.1.3` is the first stable release that distributes **gpbiometricspy Studio** alongside the frozen scientific package.

## Studio application

- Complete Shiny for Python research interface covering intake/QC, annotation, EDA/SCR, PPG/HR/HRV, pupil, gaze/fixation/AOI, events/alignment, multimodal analysis, statistics/modelling, and reporting/reproducibility.
- Installed launchers: `gpbiometricspy-studio` for full local/authenticated use and `gpbiometricspy-studio-public` for the fail-closed synthetic-only public boundary.
- Studio is included in wheel and source distributions as a separate top-level application package; scientific implementations remain under `src/gpbiometricspy`.
- Python 3.11/3.14 Studio smoke, Chromium browser E2E, and production/distribution validation are stable release gates.

## Scientific package

- Frozen semantic contract remains **406/406** R exports implemented with **0 pending**.
- Whole-package statement coverage remains **100.00%** with no coverage exclusions introduced for the release.
- Linux, Windows, and macOS validation continues across Python 3.11–3.14.
- Deep R/Python parity and optional-backend interoperability remain independent release gates.

## Release and archival integrity

- Stable release identity is synchronized across package metadata, runtime `__version__`, Zenodo metadata, CFF citation metadata, generated documentation metadata, and reproducibility/governance outputs.
- A permanent release-identity audit rejects mismatched stable metadata or leftover 0.1.3 development literals.
- The immutable `v0.1.3` tag is cut only after all nine exact-main validation workflow families are green.
- The tag cutter explicitly dispatches the protected release workflow after tag creation, avoiding GitHub `GITHUB_TOKEN` recursive tag-push suppression.
- The release workflow verifies wheel/sdist Studio contents, smoke-installs both distributions, creates SHA-256 manifests and the GitHub Release, then dispatches PyPI Trusted Publishing.
- The 0.1.3 Zenodo version DOI is intentionally not predeclared; it will be recorded only after Zenodo ingests the published GitHub release. The software concept DOI remains `10.5281/zenodo.22150872`.

## Compatibility

This release does not intentionally alter the frozen scientific API or semantics. The core scientific changes in the stable-freeze diff are release-version/provenance literals only.
