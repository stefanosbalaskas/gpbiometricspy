# gpbiometricspy 0.1.7 — exact-main scientific validation and cross-platform release hardening

Stable source frozen **2026-09-21**.

`gpbiometricspy 0.1.7` preserves the frozen **406/406** `gpbiometrics 2.0.0` scientific API with **0 pending exports** while freezing the substantially expanded post-0.1.6 Python scientific, provenance, modelling, documentation and workflow surface.

## Scientific and validation contract

- **406 / 406** frozen exports implemented;
- **0 pending** exports;
- **855 / 855** exact-main tests pass;
- **15,171 / 15,171 statements = 100.00%**;
- **7,159 / 7,178 raw branches = 99.7353%**;
- exactly **19** reviewed residual structural/caller-dominated arcs;
- **0 unexpected / 0 stale / 0 unaudited** branch debt;
- **7,178 / 7,178 = 100.0000% audited branch accounting**;
- Python **3.11–3.14** cross-platform test matrix remains green.

## Release hardening

The structural branch-debt auditor now normalizes Windows and POSIX path separators before exact arc comparison. This fixes a Windows-only audit mismatch without altering package scientific behavior or changing the frozen 19-arc structural-debt ledger.

## Scientific and workflow surface

The release retains the post-0.1.6 development-line additions, including expanded hierarchical location–scale modelling, grouped predictive methods, timing/provenance and cardiac-source evidence, research workflow guidance, reviewer-facing documentation, and Studio-backed reproducibility routes. These additions remain subject to the package's explicit measurement, provenance and interpretation boundaries.

## Publication boundary

Stable publication remains fail-closed:

1. exact stable candidate pull-request workflows must pass;
2. the candidate is merged with pinned-head protection;
3. all stable release gates must pass on the exact merged `main` commit;
4. immutable `v0.1.7` is cut from that exact commit;
5. canonical wheel/sdist artifacts and SHA-256 evidence are produced once;
6. PyPI Trusted Publishing uses those canonical artifacts.

## Archival boundary

- software concept DOI: **10.5281/zenodo.22150872**;
- previous verified archived Python version DOI: **10.5281/zenodo.22672823** (`0.1.5`);
- `0.1.6` version DOI remains pending independent verification;
- frozen R-reference provenance DOI: **10.5281/zenodo.21434608**;
- `0.1.7` version DOI: **pending genuine Zenodo ingestion**; no pre-ingestion DOI is fabricated.
