# gpbiometricspy Studio — Windows installer readiness

This document records the certified Windows installer/uninstaller engineering proof for the `0.1.6` development line. It is evidence for release readiness only; it does not publish or authorize distribution of an installer.

## Certified product/release-engineering checkpoint

Exact certified SHA:

`d5f30872468e272944c90d93574d30b656a38f4f`

All twelve applicable pull-request workflow families completed successfully at that exact head:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| `tests` | #459 | `34576986162` | success |
| `studio` | #244 | `34576986190` | success |
| `studio-e2e` | #215 | `34576986222` | success |
| `studio-production` | #216 | `34576986156` | success |
| `studio-packaging` | #23 | `34576986198` | success |
| `studio-signing-readiness` | #8 | `34576986173` | success |
| `studio-installer-readiness` | #2 | `34576986161` | success |
| `branch-coverage` | #257 | `34576986183` | success |
| `deep-parity` | #448 | `34576986169` | success |
| `interoperability` | #447 | `34576986215` | success |
| `docs` | #229 | `34576986209` | success |
| `CodeQL` | #450 | `34576986178` | success |

The routine packaging workflow intentionally keeps Nuitka as manual `workflow_dispatch`; its skipped PR job is not a missing gate.

## Installer proof

`studio-installer-readiness` #2 built the already-certified PyInstaller native WebView2 bundle, exercised that source bundle, compiled an unsigned Inno Setup installer, installed it silently for the current user into an isolated runner location, exercised the installed native application, and silently uninstalled it.

The proof is deliberately non-elevating and current-user scoped:

- stable AppId: `fd3ca1af-0ebb-5061-9c59-f7ab1079252e`;
- `PrivilegesRequired=lowest`;
- x64-compatible install mode;
- no automatic post-install launch;
- Start Menu shortcut created;
- desktop shortcut remains opt-in and is not created by default;
- no environment-variable or file-association mutation;
- no production signing hook or signing secret in the installer definition or workflow.

The PEP 440 display/package version remains `0.1.6`. Windows PE numeric version metadata uses the derived numeric version `0.1.6.0`; a regression test prevents the non-numeric development version from being supplied to Inno Setup PE version directives.

## Certified installer evidence

Workflow artifact:

- name: `studio-installer-readiness-evidence`;
- artifact ID: `10190168121`;
- artifact digest: `sha256:f36469b7c140200650b1bcd83d0fd0fff17c59c7f36ba23d04c925e8a35b0949`.

Installer/readiness metrics:

- installer SHA-256: `08f27baea61cdaad4bc4101373f53cb81b4943cc18ecf8d1acc1f1faf0050b91`;
- installer bytes: `77,784,632`;
- installer signed: `false`;
- installer published: `false`;
- source native executable SHA-256: `3b496de6c0655be42fc121e905c04ce0d83b49f14b0ee49c08c27b7123718bfa`;
- installed native executable SHA-256: `3b496de6c0655be42fc121e905c04ce0d83b49f14b0ee49c08c27b7123718bfa`;
- installed executable identity match: `true`;
- installed local HTTP/DOM startup: `2.976 s`;
- installed public-demo HTTP/DOM startup: `2.920 s`;
- external Python required: `false`;
- uninstall exit code: `0`;
- uninstall registration removed: `true`;
- shortcuts removed: `true`;
- installed payload files removed: `true`.

The source native bundle used by the proof also retained the certified Windows identity and WebView2 behavior:

- renderer: `edgechromium`;
- native bundle files: `2,012`;
- native bundle bytes: `249,806,121`;
- native build time: `80.974 s`;
- source-bundle local startup: `3.711 s`;
- source-bundle public-demo startup: `2.931 s`;
- Windows identity verified: `true`;
- product version: `0.1.6`;
- file version: `0.1.6.0`.

## Failure closed during development

Installer-readiness #1 correctly failed before installation because Inno Setup rejected `VersionInfoProductVersion=0.1.6`: that directive requires numeric Windows version metadata. The candidate was not certified. The installer definition was corrected to use the existing numeric `0.1.6.0` Windows file-version resource for both PE numeric version directives while preserving `AppVersion=0.1.6` as the researcher-facing development version. Installer-readiness #2 then passed the complete install/exercise/uninstall proof.

## Evidence-retention boundary

Pull-request CI uploads diagnostics only. The workflow explicitly checks the evidence directory for `.exe`, `.pfx`, and `.p12` files before upload. The compiled installer, installed application tree, native bundle, and any signing material are not retained as workflow evidence.

The installer proof therefore establishes installation semantics and reproducibility without turning PR CI into a distribution channel.

## WebView2 boundary

The current installer proof records:

`webview2_runtime_strategy = host-provided-evaluation-only`

The hosted Windows runner already has a compatible WebView2 Runtime. This is sufficient for the engineering proof but is not yet the final deployment policy for end users. A release installer must explicitly define and validate how WebView2 availability is handled on supported Windows systems, including the failure/remediation path when the Evergreen Runtime is absent or unusable.

## Production release requirements still open

This certification does **not** make the current installer redistributable. A production release still requires, at minimum:

1. a trusted production code-signing identity or approved signing service with protected key custody;
2. SHA-256 Authenticode signing and trusted RFC 3161-compatible SHA-256 timestamping;
3. a final WebView2 Runtime deployment/detection/remediation strategy;
4. final windowed/console-free native release configuration and application branding review;
5. immutable release-build provenance, checksums and post-sign verification;
6. an explicit update policy;
7. human Windows install/upgrade/uninstall and first-session UX validation.

Stable `v0.1.5`, PyPI, Zenodo, `main`, and the recovery checkpoint are outside this tranche and remain untouched.
