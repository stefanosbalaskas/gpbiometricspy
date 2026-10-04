# gpbiometricspy 0.1.8 — PPG measurement equity and STEP evidence

Stable-freeze candidate prepared **2026-10-04**.

`gpbiometricspy 0.1.8` preserves the frozen **406/406** `gpbiometrics 2.0.0` semantic contract with **0 pending exports** while promoting the post-0.1.7 PPG pigmentation / measurement-equity programme into the stable release scope.

## Exact qualification baseline

The candidate is frozen from exact qualified `main` source:

```text
a75eb1d73791213e6e830ff94975f632455632e2
```

- **12/12** OS × Python 3.11–3.14 test lanes green;
- **874/874** tests;
- **15,612/15,612 statements = 100.00%**;
- **7,315/7,334 raw branches = 99.7409%**;
- exactly **19** reviewed structural arcs;
- **0 unexpected / 0 stale / 0 unaudited** branch debt;
- **7,334/7,334 = 100.0000%** audited branch accounting;
- docs/Pages, CodeQL, deep parity, interoperability, private real-data validation and release-handoff safety green.

The stable-freeze PR and merged stable source still require their own exact-head/exact-main qualification before publication.

## PPG measurement-equity surface

Version 0.1.8 includes the Python-native functions `compute_skin_ita()`, `validate_skin_pigmentation_metadata()`, `summarize_ppg_quality_by_pigmentation()`, `compare_ppg_reference_by_pigmentation()` and `ppg_pigmentation_audit()`.

The method separates pigmentation provenance, acquisition quality, retention/paired availability, and reference agreement. Objective CIELAB/ITA-style measures can support continuous descriptive associations. Subjective Fitzpatrick/Monk-style scales remain subjective provenance; demographic race/ethnicity proxies are not treated as pigmentation.

The package does not apply a universal pigmentation correction, does not automatically exclude observations because of pigmentation, and does not label a device “fair” or “unfair”.

See [PPG pigmentation & measurement-equity audit](methods/ppg-pigmentation-equity.md) and the [synthetic worked example](examples/ppg-equity-synthetic.md).

## STEP external evidence

BigIdeasLab_STEP v1.0 was executed on an authorized local copy under the applicable PhysioNet DUA against exact scientific source `dc2b539154f65061a90d360f01503108ad1fd39f`.

The retained aggregate record includes:

- DOI `10.13026/cqfy-d860`;
- 53 participants;
- 1,431,570 long-format wearable rows;
- 1,328,850 rows with ECG reference available;
- 361,675 paired wearable/ECG measurements;
- six wearable devices;
- participant-cluster bootstrap with 1,000 replicates and seed `20261003`;
- derived-only bundle SHA256 `65EF1DE84CF711F9E6753DB771E3E2386FD6926A104E0D4DC1618EE88E8744B1`.

Restricted participant-level rows were not committed or redistributed.

Fitzpatrick 1–6 is retained as **subjective categorical phototype**, not objective pigmentation. STEP row-level retention is interpreted as **paired availability/reporting density** because device reporting cadence differs materially. The observed unlabeled/NA activity stratum remains unlabeled. Agreement results are observational and device/activity-specific.

See the [external-evidence record](ppg-equity-external-evidence.md).

## Explicit exclusions

0.1.8 does not claim:

- causal effects of pigmentation or melanin on PPG performance;
- race or ethnicity as a substitute for measured pigmentation;
- generic device fairness from paired error statistics;
- a universal pigmentation correction;
- real ENCoDE execution;
- clinical SpO₂/pulse-oximeter validation.

ENCoDE remains deferred future evidence infrastructure.

## Archival state

The software concept DOI remains **10.5281/zenodo.22150872** and the frozen R reference DOI remains **10.5281/zenodo.21434608**. No 0.1.7 or 0.1.8 version DOI is fabricated before genuine independent Zenodo verification.

## Publication state

This page documents the stable-freeze candidate. `v0.1.8`, GitHub Release artifacts and PyPI publication are not considered complete until the protected release pipeline succeeds on the exact merged stable `main` commit.