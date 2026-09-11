# Studio release provenance readiness

This document records the release-provenance, checksums, and SBOM readiness checkpoint for the `0.1.6` Studio development line. It is evidence for release engineering only. It does not publish, sign, timestamp, or attest a redistributable artifact.

## Certified product/release-engineering identity

Certified product-code SHA:

`2c1d88ea4c12a0f123728b15ab46e6a89abbd484`

The pull-request merge checkout used by GitHub Actions for this checkpoint was:

`7a0321c9f84d869559d7ca2f5b37a01365f865a3`

These identities are intentionally distinct. The certified source identity is the pull-request head SHA; the merge-checkout SHA records the exact GitHub Actions test checkout used for this PR run.

At the certified source SHA, all fifteen pull-request workflow families completed successfully:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| `tests` | #469 | `34587475256` | success |
| `studio` | #254 | `34587475226` | success |
| `studio-e2e` | #225 | `34587475240` | success |
| `studio-production` | #226 | `34587475234` | success |
| `studio-packaging` | #33 | `34587475248` | success |
| `studio-signing-readiness` | #18 | `34587475209` | success |
| `studio-installer-readiness` | #12 | `34587475288` | success |
| `studio-windowed-readiness` | #7 | `34587475260` | success |
| `studio-windowed-installer-readiness` | #5 | `34587475281` | success |
| `studio-release-provenance-readiness` | #1 | `34587475261` | success |
| `branch-coverage` | #267 | `34587475305` | success |
| `deep-parity` | #458 | `34587475299` | success |
| `interoperability` | #457 | `34587475143` | success |
| `docs` | #239 | `34587475138` | success |
| `CodeQL` | #460 | `34587475196` | success |

The ordinary packaging workflow intentionally keeps Nuitka as a manual comparison path; the required PyInstaller packaging jobs passed.

## Release-provenance evidence

`studio-release-provenance-readiness` #1 produced the diagnostics-only artifact `studio-release-provenance-readiness-evidence`:

- artifact ID: `10194319536`;
- GitHub artifact digest: `sha256:23252f6f9e6256791181a3de1612df536fd61d40350ec4b553252d10c8d037e6`;
- independently downloaded ZIP SHA-256: `23252f6f9e6256791181a3de1612df536fd61d40350ec4b553252d10c8d037e6`;
- provenance schema: `gpbiometricspy-studio-release-provenance-readiness`, version `1`;
- readiness-only: `true`;
- release artifact: `false`;
- published: `false`;
- signed: `false`;
- attested: `false`;
- SLSA claimed: `false`;
- readiness OIDC used: `false`;
- readiness attestation permissions used: `false`.

No executable, DLL, PFX, P12, PEM, or private-key material is retained in the uploaded evidence.

## Transient artifact and executable bindings

The readiness workflow built a transient GUI-subsystem installer and source executable, recorded their hashes, and then deleted the binaries before evidence upload.

- transient installer name: `gpbiometricspy-studio-setup.exe`;
- transient installer bytes: `75,011,910`;
- transient installer SHA-256: `25717e591b4f5babc82f1d87b2e4a39502b9a99458a5095cf1acde51832e854a`;
- transient source executable SHA-256: `a92f701f98d629219cf0f9dcabfba2322088116334046bed0f37c9dd73307922`;
- source PE subsystem: `2` / `IMAGE_SUBSYSTEM_WINDOWS_GUI`;
- identity manifest SHA-256: `e3f198e13bb5f4de1b99a2ea171bfcdb5e2eb0f679885b59b76dd9f1a535fbb3`;
- product version: `0.1.6`;
- Windows file version: `0.1.6.0`.

`SHA256SUMS.txt` intentionally contains entries for both transient binaries even though the binaries themselves are not retained. The checksum file itself has SHA-256:

`309ca9e0a4934e0294c9a73efabcea628786c27bad3ef7b5f6959806518a8e6d`

Every retained entry in that checksum manifest was independently re-hashed after artifact download and matched exactly.

## CycloneDX SBOM

The workflow inventories the actual isolated Python build environment before cleanup and emits a validated, reproducible CycloneDX JSON SBOM.

- CycloneDX tool: `cyclonedx-bom 7.3.1`;
- CycloneDX spec: `1.6`;
- format: JSON;
- validation enabled: `true`;
- reproducible-output mode: `true`;
- target: actual build virtual environment;
- environment component count: `58`;
- metadata root component: `gpbiometricspy 0.1.6`, type `application`;
- dependency nodes: `59`;
- SBOM SHA-256: `9491264e0b7c2a01d9988c0e8ea8552a9a4bdee485a545f15dbd328f1348c9c2`.

The validated inventory includes the expected frozen-build stack, including:

- `pyinstaller 6.22.2`;
- `pywebview 6.2.1`;
- `shiny 1.7.0`;
- `numpy 2.5.3`;
- `pandas 3.0.5`;
- `scipy 1.18.1`;
- `matplotlib 3.11.1`.

To prevent the separately installed CycloneDX tooling environment from contaminating target discovery, the workflow clears `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` while inspecting the build virtual environment.

Additional environment evidence:

- `studio-build-environment.freeze.txt` SHA-256: `bfe8d571cbff6b3d1a24fe48bc21d764d25aff46f7246bddcdaa09514d0b86ae`;
- `studio-build-environment.pip-list.json` SHA-256: `cd14e4dae19c8ad0e99b1b6add871336b86b4d4fec3939d60a8277cd5e18979e`;
- Python: `3.14.7`;
- PyInstaller: `6.22.2`;
- pywebview: `6.2.1`.

## Installer compiler provenance

The transient installer was compiled with:

- tool: Inno Setup;
- version: `6.7.1`;
- version source: Inno Setup uninstall-registry metadata;
- compiler binary SHA-256: `bca711de277c540181fb846d9d4dbf46e3f034ab89c38bbd3c17a709f5ef3edc`.

The readiness policy does not trust the previously observed `ISCC.exe` `FileVersionInfo=0.0.0.0` path as authoritative version provenance.

## Material build-input hashes

The provenance record cryptographically binds the material release-build inputs used by this readiness proof:

| Input | SHA-256 |
| --- | --- |
| `.github/scripts/assert_studio_windows_identity.ps1` | `e3ed17539d0a0306f10289b813b50d0cd077286baed20cb9758eb579df0b20b0` |
| `.github/scripts/test_studio_release_provenance_windows.ps1` | `ac9d8492235cde88a980047803f2b311dbe7cbc2151f1cace2c741535fc7dbb1` |
| `pyproject.toml` | `97734aef4b31114e1d585744e646c38167c4326b9ec7a7cf35987c0dfffc9346` |
| `tools/installer/gpbiometricspy_studio.iss` | `f18b9b243e5edac1a92c20c26628dbff24589a7e955898acb2f14f8ac5f4612e` |
| `tools/pyinstaller/generate_windows_identity.py` | `5e4bc55d3c460c6142d6554c6fea11b5a045b18b7b626206cf6c0dd21890f41e` |
| `tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec` | `6a0cd48ffcfec1bb01611a68ec90f3e33e502bb5c32615c7bb3244875709b157` |
| `tools/pyinstaller/requirements.txt` | `e8ca173c9645c546d3048200c1c3f4c6749cc56fe61d021e99473723472cd4f4` |
| `tools/release/requirements.txt` | `d9cd9f7e0497149cc29bc2fe41b434a000f7e4b6a28188f5a561fcdeed1f1d78` |

## Production release boundary

This readiness proof deliberately does not create a redistributable release artifact. A real production release must bind provenance to the actual artifact that is ultimately published, after production signing and timestamping.

The production release policy remains fail-closed:

1. build the actual windowed installer from the selected immutable release source/tag;
2. retain exact source identity and material build-input hashes;
3. generate and validate the release SBOM from the actual build environment;
4. record pre-sign artifact SHA-256;
5. sign with the authorized trusted production code-signing identity/service using SHA-256;
6. obtain an RFC 3161-compatible SHA-256 timestamp;
7. verify the signed artifact with the platform verification path;
8. record the post-sign artifact SHA-256, signer identity/certificate metadata, and timestamp evidence;
9. generate the public checksum manifest for the actual distributable artifact;
10. create release attestation/provenance for that actual published artifact, not for this readiness-only CI build;
11. publish only after those checks pass.

The PR readiness workflow intentionally has only `contents: read` permission, uses no repository signing secret, requests no OIDC token, and performs no GitHub artifact attestation.

## Guardrails retained

- stable `v0.1.5`, its GitHub Release, PyPI artifacts, and Zenodo DOI chain remain untouched;
- no scientific implementation is duplicated or changed by this tranche;
- the 406-function scientific parity boundary remains unchanged;
- current PR evidence remains diagnostics-only;
- no installer or executable is distributed from readiness CI;
- production signing credentials remain outside the repository;
- production timestamping, checksums, SBOM, and release attestation remain mandatory release-time operations;
- the current generated icon remains an evaluation/reproducibility asset pending final branding review;
- PR #107 remains draft pending the remaining production-distribution and human-validation boundaries.

This file is a post-certification documentation record. Its documentation commit does not replace certified product-code identity `2c1d88ea4c12a0f123728b15ab46e6a89abbd484`.
