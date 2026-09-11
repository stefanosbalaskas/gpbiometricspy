# gpbiometricspy 0.1.6 — Studio product workflow and release simplification

Release candidate frozen **2026-09-11**.

`gpbiometricspy 0.1.6` preserves the frozen **406/406** `gpbiometrics 2.0.0` scientific API while promoting Studio into a substantially more complete end-user research workflow.

## Product and workflow layer

- guided researcher and teaching routes;
- project identity and fingerprint checks;
- module prerequisites and researcher-facing remediation;
- integrated QC, EDA/SCR, PPG/HR/HRV, pupil, gaze/AOI, event alignment, multimodal, statistics and reporting routes;
- project Timeline/provenance, recent-project handling and reproducible recipe lifecycle;
- browser end-to-end coverage of the first physiology session from guided synthetic start through reporting and project edit state.

## Scientific contract

- **406 / 406** frozen exports implemented;
- **0 pending** exports;
- package statement coverage remains **100%**;
- the release-preparation baseline carries **641 passing core tests** on the certified Studio product head before stable identity freeze;
- public demonstration mode remains synthetic-only.

## Python publication boundary

The normal Python release no longer depends on optional standalone Windows code signing or human installer validation. The Windows packaging/signing/handoff workflows remain available as engineering evidence for a future signed standalone installer, but they do not block the Python/GitHub/PyPI/Zenodo release.

Stable publication remains fail-closed: exact-current-main validation, immutable exact tag, reproducible wheel/sdist build, SHA-256 package manifest, canonical release metadata, byte-identical GitHub Release assets, and PyPI Trusted Publishing only from the successful canonical release workflow artifact.

## Archival boundary

- software concept DOI: **10.5281/zenodo.22150872**;
- previous 0.1.5 version DOI: **10.5281/zenodo.22672823**;
- frozen R-reference provenance DOI: **10.5281/zenodo.21434608**;
- 0.1.6 version DOI: **pending Zenodo ingestion**; no pre-ingestion DOI is fabricated.
