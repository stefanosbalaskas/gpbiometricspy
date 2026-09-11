# Studio Windows signing readiness

This document records the Windows Authenticode signing-readiness proof for the gpbiometricspy Studio `0.1.6` development line. It is an engineering-readiness checkpoint, not a release-signing policy and not a published binary.

## Certified product-code identity

The certified product-code SHA is:

`28637dbc6a8abb87f0f6acf2b7f728eceacacd77`

At that exact SHA, all 11 pull-request workflow families completed successfully:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| tests | #456 | `34574876698` | success |
| studio | #241 | `34574876693` | success |
| studio-e2e | #212 | `34574876704` | success |
| studio-production | #213 | `34574876699` | success |
| studio-packaging | #20 | `34574876665` | success |
| studio-signing-readiness | #5 | `34574876675` | success |
| branch-coverage | #254 | `34574876670` | success |
| deep-parity | #445 | `34574876674` | success |
| interoperability | #444 | `34574876752` | success |
| docs | #226 | `34574876721` | success |
| CodeQL | #447 | `34574876662` | success |

The normal pull-request packaging gate intentionally skips the manually dispatched Nuitka comparison. That comparison had already been certified separately; PyInstaller remains the Windows freezer baseline.

## What the signing gate proves

`studio-signing-readiness` builds the same PyInstaller native WebView2 Studio candidate exercised by the packaging gate and then performs a test-only Authenticode proof on Windows Python 3.14.

The gate:

1. builds and exercises the unsigned native Studio candidate with external Python removed from `PATH`;
2. verifies the generated Windows product identity before signing;
3. requires the input executable to be unsigned;
4. creates a one-day RSA/SHA-256 code-signing certificate entirely in memory;
5. validates that certificate using an in-memory `.NET` `CustomRootTrust` chain;
6. does **not** install the certificate into `CurrentUser/Root`, `TrustedPublisher`, or any other Windows certificate store;
7. exports an ephemeral password-protected PFX only to runner-local temporary storage;
8. signs the executable with the Windows SDK `signtool.exe` using `/fd SHA256`;
9. verifies that the executable SHA-256 changes and that the embedded signer thumbprint matches the ephemeral certificate;
10. re-verifies the pre-existing PE identity/icon resources after signing;
11. asks SignTool to verify the signature under the Windows Authenticode policy and records the expected trust failure of the deliberately self-signed test certificate;
12. deletes the ephemeral PFX and uploads evidence only—never the signed executable or PFX.

All potentially blocking SignTool processes are bounded to 60 seconds and PowerShell Authenticode inspection is bounded to 30 seconds. The workflow itself has a 15-minute ceiling.

## Exact evidence from run #5

Artifact:

- name: `studio-signing-readiness-evidence`
- artifact ID: `10189301564`
- artifact digest: `sha256:0aaefa4c75b3a298bfc57b97c0555433982ecd9e6e3180c5a69da1bf676899aa`

The schema-v4 signing provenance reports:

- `test_only = true`
- `release_artifact = false`
- `certificate_ephemeral = true`
- `certificate_persisted = false`
- `trust_store_mutated = false`
- `test_certificate_trusted = false`
- `production_trusted_certificate_required = true`
- `timestamped = false`
- `production_timestamp_required = true`
- production file digest algorithm: `SHA256`
- production timestamp digest algorithm: `SHA256`
- signing tool: `signtool`
- unsigned SHA-256: `dfc004a1427f2632e2c3fb315cf55c2e5c7f40ed8ea313498f874c8ec8afb867`
- signed SHA-256: `7eb8ed39e6909aa25a9666304b4a151d8a8e8cdd6bf6366e39e0e615b77dd955`
- signer subject: `CN=gpbiometricspy Studio CI Test Signing`
- signer thumbprint: `649ABAD5572598F2D56CE4B1470FBF6886ECA2C6`
- signer identity match: `true`
- PowerShell signature state: `UnknownError`, specifically because the self-signed root is intentionally not trusted by the runner
- SignTool verification exit code: `1`, with the same explicit untrusted-root reason
- SignTool signing itself: successful

SignTool identified the embedded primary signature, SHA-256 file hash, signer certificate chain, and absence of a timestamp before stopping at the expected untrusted-root boundary. There was no hash-mismatch condition.

## Same-run native build evidence

The signing run rebuilt the native bundle rather than signing an unrelated artifact. Its native metrics were:

- Python `3.14.7`
- PyInstaller `6.22.2`
- pywebview `6.2.1`
- renderer `edgechromium`
- 2,012 files
- 249,806,121 bytes (about 238.2 MiB)
- build time 86.871 s
- local HTTP startup 3.182 s
- public-demo HTTP startup 3.448 s
- external Python required: `false`
- DOM-loaded proof required: `true`
- Windows identity verified: `true`

The identity remained `gpbiometricspy Studio`, product version `0.1.6.dev0`, file version `0.1.6.0`, original filename `gpbiometricspy-studio-native.exe`.

## Trust boundary and production interpretation

A self-signed CI certificate must not be made globally trusted merely to turn a test result green. Earlier experimentation showed that mutating `CurrentUser/Root` on the hosted Windows image could block indefinitely. The certified design therefore keeps CI trust-store-free and treats the untrusted-root result as the expected final boundary of the test certificate.

This is sufficient to prove that the application can be Authenticode-signed through the intended Windows SDK toolchain, that the signature is attached to the expected executable and signer identity, and that signing preserves the already-certified Windows application resources. It deliberately does **not** claim that the CI test certificate is suitable for redistribution.

A production release remains fail-closed on all of the following:

- a real trusted code-signing identity/certificate or approved signing service;
- protected key custody with no private key committed to the repository;
- SHA-256 Authenticode signing;
- trusted RFC 3161-compatible timestamping with SHA-256;
- post-signing verification of signer identity, timestamp, executable digest/provenance, and Windows application resources;
- installer/uninstaller design and validation;
- signing of the final distribution surface as appropriate;
- release checksums and immutable build provenance;
- update-policy definition;
- human Windows installation/launch UX validation.

No signed executable is uploaded by pull-request CI, and this checkpoint does not alter `main`, stable `v0.1.5`, PyPI, Zenodo, or the pre-product-polish recovery branch.
