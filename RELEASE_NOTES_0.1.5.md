# gpbiometricspy 0.1.5 release-readiness notes

**Status: development / unreleased (`0.1.5.dev0`).**

These notes describe the current candidate delta from stable `v0.1.4`. They are not evidence that `0.1.5` has been tagged, published to PyPI, or ingested by Zenodo. Stable citation remains `gpbiometricspy 0.1.4` with version DOI `10.5281/zenodo.22515782` until a future 0.1.5 release is actually completed.

## Frozen scientific contract

- **406 / 406** frozen `gpbiometrics 2.0.0` exports implemented; **0 pending**.
- Package/runtime development identity remains **`0.1.5.dev0`**.
- Current scientific regression evidence: **567 tests** and **10,456 / 10,456 statements = 100.00%**.
- Current raw branch evidence: **5,629 / 5,648 = 99.6636%**, above the persistent **99.6000%** raw branch floor.
- The structural-debt ledger still contains exactly **19** reviewed structural/caller-dominated arcs, with **0 unexpected**, **0 stale**, and **0 unaudited** missing branches; audited branch accounting is **5,648 / 5,648 = 100.0000%** without relabelling the honest raw coverage metric.

## Measurement accountability

The development line adds a focused physiology measurement-accountability layer without replacing or redefining the frozen R parity surface:

- `compare_hrv_prv_devices()` reports agreement for a named derived metric rather than treating ECG-HRV and PPG-PRV devices as globally interchangeable;
- `scr_responsivity_sensitivity()` retains low-reactive/nonresponder participants for explicit sensitivity analysis rather than automatically deleting them;
- `validation_ladder()` separates acquisition QC, analytical QC, construct checks, within-person evidence, and held-out-person generalization, and refuses a generalization claim when held-out-person evidence is absent;
- `ppg_topology_features()` provides explicitly **experimental structural descriptors** for PPG morphology and does not label them as direct physiological surrogates.

The corresponding documentation states the interpretation boundaries and validation expectations explicitly.

## Studio replay and production hardening

Since `v0.1.4`, Studio validation has expanded substantially beyond shell/browser smoke:

- installed wheel and sdist entrypoints are exercised in Chromium on Python 3.11 and 3.14;
- installed replay covers local and public CLI boundaries, physiology analysis, external event alignment, multimodal/model preparation, and cluster-permutation workflows;
- replay recipes bind external event logs and target streams to deterministic resource identities rather than embedding raw data paths;
- wrong event resources and wrong target streams are rejected before analysis, while exact resources replay successfully;
- generated replay recipes fail closed when required secondary resources are absent;
- installed upload synchronization now uses production-compatible rendered server state rather than Shiny test-mode snapshots or arbitrary fixed sleeps;
- package plotting adapters preserve public scientific return contracts while letting Studio render structured plot bundles safely;
- public-demo CSS and server-side upload boundaries remain independently guarded so usability fixes do not weaken the synthetic-only deployment policy.

## Coverage-gate integrity repair

Release-readiness auditing found and fixed a CI integrity defect in `branch-coverage.yml`: auditor commands were piped through `tee` without Bash `pipefail`, allowing the pipeline to look green when the Python auditor exited non-zero.

The repaired gate immediately exposed one genuine new missing branch in non-finite PPG-topology input handling. That path was covered with a regression test rather than added to structural debt. The structural ledger was then rebased from the 0.1.4 denominator of **5,594** branches to the observed 0.1.5.dev0 denominator of **5,648**, while keeping the reviewed structural debt unchanged at **19** arcs.

The resulting exact evidence is:

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

The successful development evidence artifact is GitHub Actions artifact **10066871104**, digest `sha256:4a42bad6b344a85a24d4c9bde75d926a9d51f635404c0fb67528c16df3e14a96`.

## What is not being claimed yet

- No stable `0.1.5` tag has been created.
- No `gpbiometricspy==0.1.5` PyPI release is claimed.
- No 0.1.5 version-specific Zenodo DOI is claimed before Zenodo ingestion.
- `CITATION.cff` remains pinned to the actual stable `0.1.4` release and DOI until a stable 0.1.5 freeze is intentionally performed.
- The measurement-accountability additions do not establish universal sensor interchangeability or direct latent-state inference.

## Remaining stable-release sequence

1. merge and qualify the release-readiness documentation/metadata tranche on exact `main`;
2. intentionally freeze `0.1.5.dev0` to stable `0.1.5` in a separate release commit only when development is closed;
3. synchronize package/runtime/CFF/Zenodo/generated metadata for the stable version without inventing a DOI;
4. require every exact-main stable-release gate to pass;
5. create immutable `v0.1.5` only from that exact qualified commit and let protected release automation build/check/publish artifacts;
6. verify GitHub Release/PyPI hashes and fresh-index installation;
7. wait for Zenodo ingestion, then record the actual 0.1.5 version DOI while retaining concept DOI `10.5281/zenodo.22150872` and R-reference provenance.
