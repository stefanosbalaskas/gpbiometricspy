# gpbiometricspy 0.1.8 release qualification checklist

Stable-freeze candidate date: **2026-10-04**.

## Qualified pre-freeze source

- [x] Exact qualified `main` source: `a75eb1d73791213e6e830ff94975f632455632e2`.
- [x] Frozen `gpbiometrics 2.0.0` semantic contract preserved at **406/406 implemented exports, 0 pending**.
- [x] **12/12** OS × Python 3.11–3.14 test lanes green.
- [x] **874/874** tests passed.
- [x] **15,612/15,612 statements = 100.00%**.
- [x] Raw branch coverage **7,315/7,334 = 99.7409%**.
- [x] Exactly **19** reviewed structural arcs.
- [x] **0 unexpected / 0 stale / 0 unaudited** branch debt.
- [x] Audited branch accounting **7,334/7,334 = 100.0000%**.
- [x] Docs/Pages, CodeQL, deep parity, interoperability, private real-data validation and release-handoff safety green.

## 0.1.8 scientific scope

- [x] PPG pigmentation / measurement-equity API included as Python-native methods outside the frozen R parity registry.
- [x] Deterministic synthetic evidence separates amplitude, quality, retention and accuracy.
- [x] Authorized BigIdeasLab_STEP v1.0 execution recorded against `dc2b539154f65061a90d360f01503108ad1fd39f`.
- [x] STEP Fitzpatrick retained as subjective categorical phototype only.
- [x] STEP row-level retention described as paired availability/reporting density, not generic device missingness or fairness.
- [x] STEP unlabeled/NA activity stratum remains explicitly unlabeled.
- [x] Restricted participant-level STEP rows are not committed or redistributed.
- [x] ENCoDE real-data execution explicitly deferred and not claimed.
- [x] Clinical SpO₂ validation explicitly outside scope.

## Stable identity

- [x] `pyproject.toml` version = `0.1.8`.
- [x] runtime `gpbiometricspy.__version__` = `0.1.8`.
- [x] governance/reproducibility version literals synchronized to `0.1.8`.
- [x] generated documentation manifest version = `0.1.8`.
- [x] `.zenodo.json` version = `0.1.8`.
- [x] `CITATION.cff` version/date = `0.1.8` / `2026-10-04`.
- [x] software concept DOI remains `10.5281/zenodo.22150872`.
- [x] no 0.1.7 or 0.1.8 version DOI invented before genuine independent verification.

## Protected release gates

- [ ] Exact-head 0.1.8 freeze PR passes every required workflow family.
- [ ] Release-identity audit passes on the exact PR head.
- [ ] Stable wheel and sdist build successfully and pass metadata checks.
- [ ] Exact PR head is pinned and unchanged immediately before merge.
- [ ] Stable-freeze PR is merged only after the exact-head gate set is green.
- [ ] Resulting exact `main` commit passes every package release gate.
- [ ] Automatic stable-release cutter verifies the exact current `main` commit.
- [ ] Immutable annotated `v0.1.8` is created only from the exact qualified stable commit.
- [ ] Canonical GitHub Release wheel, sdist, `SHA256SUMS.txt` and `RELEASE-METADATA.json` are verified.
- [ ] Protected PyPI Trusted Publishing publishes only the canonical successful release artifact.
- [ ] GitHub Release and PyPI wheel/sdist SHA-256 equality is verified.
- [ ] Fresh public-index installation checks pass.
- [ ] A genuine 0.1.8 Zenodo version DOI is recorded only after independent verification; otherwise it remains explicitly pending.
