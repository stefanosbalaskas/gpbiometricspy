# gpbiometricspy 0.1.5 — measurement accountability and installed-replay hardening

Released **2026-09-08** from the fully qualified stable-release line.

`gpbiometricspy 0.1.5` preserves the frozen **gpbiometrics 2.0.0** scientific contract while strengthening measurement accountability, installed Studio replay validation, and CI release integrity.

## Frozen scientific contract

- **406 / 406** frozen `gpbiometrics 2.0.0` exports implemented; **0 pending**.
- Package/runtime stable identity: **`0.1.5`**.
- Scientific regression evidence: **567 tests** and **10,456 / 10,456 statements = 100.00%**.
- Raw branch evidence: **5,629 / 5,648 = 99.6636%**, above the persistent **99.6000%** raw branch floor.
- The structural-debt ledger contains exactly **19** reviewed structural/caller-dominated arcs, with **0 unexpected**, **0 stale**, and **0 unaudited** missing branches; audited branch accounting is **5,648 / 5,648 = 100.0000%** without relabelling the honest raw coverage metric.

## Measurement accountability

The release adds a focused physiology measurement-accountability layer without replacing or redefining the frozen R parity surface:

- `compare_hrv_prv_devices()` reports agreement for a named derived metric rather than treating ECG-HRV and PPG-PRV devices as globally interchangeable;
- `scr_responsivity_sensitivity()` retains low-reactive/nonresponder participants for explicit sensitivity analysis rather than automatically deleting them;
- `validation_ladder()` separates acquisition QC, analytical QC, construct checks, within-person evidence, and held-out-person generalization, and refuses a generalization claim when held-out-person evidence is absent;
- `ppg_topology_features()` provides explicitly **experimental structural descriptors** for PPG morphology and does not label them as direct physiological surrogates.

The corresponding documentation states the interpretation boundaries and validation expectations explicitly.

## Studio replay and production hardening

Since `v0.1.4`, Studio validation has expanded substantially beyond shell/browser smoke:

- installed wheel and sdist entrypoints are exercised in Chromium on Python 3.11 and 3.14;
- installed replay covers local and public CLI boundaries, gaze/pupil, physiology analysis, external event alignment, multimodal/model preparation, and cluster-permutation workflows;
- replay recipes bind external event logs and target streams to deterministic resource identities rather than embedding raw data paths;
- wrong event resources and wrong target streams are rejected before analysis, while exact resources replay successfully;
- generated replay recipes fail closed when required secondary resources are absent;
- installed upload synchronization uses production-compatible rendered server state rather than Shiny test-mode snapshots or arbitrary fixed sleeps;
- package plotting adapters preserve public scientific return contracts while letting Studio render structured plot bundles safely;
- public-demo CSS and server-side upload boundaries remain independently guarded so usability fixes do not weaken the synthetic-only deployment policy.

## Coverage-gate integrity repair

Release-readiness auditing found and fixed a CI integrity defect in `branch-coverage.yml`: auditor commands were piped through `tee` without Bash `pipefail`, allowing the pipeline to look green when the Python auditor exited non-zero.

The repaired gate immediately exposed one genuine new missing branch in non-finite PPG-topology input handling. That path was covered with a regression test rather than added to structural debt. The structural ledger was then rebased from the 0.1.4 denominator of **5,594** branches to the 0.1.5 denominator of **5,648**, while keeping the reviewed structural debt unchanged at **19** arcs.

The release validation target is:

```text
R exports:                  406
Implemented exports:        406
Explicit pending:             0
Tests:                      567
Statements:              10,456
Missed statements:            0
Statement coverage:      100.00%
Statement CI floor:      100.00%
Branches:             5,629/5,648
Raw branch coverage:    99.6636%
Raw branch CI floor:    99.6000%
Audited structural arcs:       19
Unexpected missing arcs:        0
Stale structural entries:       0
Unaudited branch debt:           0
Audited branch accounting: 100.0000%
```

The development evidence artifact used to prepare the stable freeze is GitHub Actions artifact **10066871104**, digest `sha256:4a42bad6b344a85a24d4c9bde75d926a9d51f635404c0fb67528c16df3e14a96`. Stable release qualification is independently rerun on the exact stable commit before tagging.

## Archival boundary

- The software concept DOI remains **10.5281/zenodo.22150872**.
- The previous 0.1.4 version DOI is **10.5281/zenodo.22515782**.
- The frozen R reference remains separate `isDerivedFrom` provenance at **10.5281/zenodo.21434608**.
- `CITATION.cff` records stable `0.1.5` and the release date but intentionally contains **no 0.1.5 version DOI before Zenodo ingestion**.
- The actual 0.1.5 version DOI is recorded only after Zenodo ingests the immutable GitHub release; it is not invented or inferred in the release freeze.


## Post-release distribution record

- Immutable annotated tag `v0.1.5` resolves to exact qualified commit `294a9b6349aef93abae84bda6f2c89afce1001de`.
- GitHub Release and PyPI wheel SHA-256: `eb2474a7d3156b305c573a5327040038f6ec08ba7e5cf244952712b3d239c607`.
- GitHub Release and PyPI sdist SHA-256: `b8605ad8d402a948d0610dd40ff98985dedf6351b681b7e43294df38d10dc47e`.
- Protected PyPI Trusted Publishing completed with HTTP 200 uploads and Sigstore/Rekor attestations (wheel Rekor `2762034607`; sdist Rekor `2762034601`).
- The 0.1.5 Zenodo version DOI remains pending ingestion and is deliberately not inferred.
- Live repository development is prepared as `0.1.6.dev0`; the stable `CITATION.cff` record remains 0.1.5 / 2026-09-08 until the actual Zenodo version DOI exists.

## Release integrity

The stable tag may be created only from the exact current `main` commit after all ten configured release-gate workflow families have succeeded on that same SHA: tests, docs, CodeQL, deep parity, interoperability, branch coverage/structural audit, private real-data validation, Studio smoke, Studio Chromium E2E, and Studio production/distribution validation. The release workflow independently rechecks those exact-commit gates before building or publishing artifacts.
