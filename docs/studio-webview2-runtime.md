# Studio WebView2 Runtime deployment policy

This checkpoint closes the Windows WebView2 Runtime prerequisite boundary for the `0.1.6` Studio development line without changing the scientific application or publishing a Windows release artifact.

## Certified product/release-engineering identity

The certified code checkpoint is:

`6a72c593e1dbd310d528ba7d1c66777a78583263`

At that exact SHA, all twelve pull-request workflow families completed successfully:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| `tests` | #461 | `34578284449` | success |
| `studio` | #246 | `34578284646` | success |
| `studio-e2e` | #217 | `34578284486` | success |
| `studio-production` | #218 | `34578284443` | success |
| `studio-packaging` | #25 | `34578284460` | success |
| `studio-signing-readiness` | #10 | `34578284438` | success |
| `studio-installer-readiness` | #4 | `34578284488` | success |
| `branch-coverage` | #259 | `34578284445` | success |
| `deep-parity` | #450 | `34578284356` | success |
| `interoperability` | #449 | `34578284348` | success |
| `docs` | #231 | `34578284398` | success |
| `CodeQL` | #452 | `34578284335` | success |

The ordinary packaging gate continues to require PyInstaller onedir, onefile and native WebView2 jobs on Python 3.11 and 3.14. Nuitka remains manual comparison-only through `workflow_dispatch`.

### Packaging rerun provenance

Packaging #25 initially had one isolated failure in `pyinstaller-onefile-windows (3.14)`, job `103195694360`. The executable built successfully, passed Windows identity verification, passed the standalone onefile smoke, and passed the local Chromium contract. Its public Chromium process then failed to become ready with empty stdout/stderr while every other required packaging job passed.

The exact failed job was rerun without changing the candidate SHA. The replacement job `103203625020` passed the build/smoke and both local and public Chromium contracts. Workflow #25 then concluded `success` at the same certified SHA. No product, packaging or timeout code was changed to obtain the successful rerun.

## Distribution decision

Studio uses the Microsoft Edge WebView2 **Evergreen Runtime** as a prerequisite. The installer does not bundle a Fixed Version Runtime and pull-request CI does not download or retain a WebView2 Runtime payload.

Microsoft documents that WebView2 applications should detect the Runtime before creating a WebView2 and recommends checking at install/update time. On 64-bit Windows, detection can inspect the `pv` value under the WebView2 product ID `{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` in both machine and current-user EdgeUpdate registry locations. A missing, empty or `0.0.0.0` value means the Runtime is unavailable.

Authoritative references:

- Microsoft Learn, **Distribute your app and the WebView2 Runtime**: https://learn.microsoft.com/microsoft-edge/webview2/concepts/deployment-distribution
- Microsoft Edge Developer, **Microsoft Edge WebView2 / Runtime downloads**: https://developer.microsoft.com/microsoft-edge/webview2/

## Installer behavior

The Inno Setup installer now performs a fail-closed prerequisite check before installation:

- machine-wide registry location on 64-bit Windows: `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`;
- current-user registry location: `HKCU\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`;
- the `pv` value must be non-empty and greater than `0.0.0.0`;
- if no valid Runtime is detected, `PrepareToInstall` blocks installation and tells the user to install the Microsoft Evergreen WebView2 Runtime before rerunning setup;
- the remediation destination is the official Microsoft WebView2 page;
- no application payload is installed when the prerequisite check fails;
- there is no CI or installer bypass that can force the Runtime to be treated as present.

A CI-only switch can force the **missing** state so the failure path itself is testable. It cannot force the installed state.

## Certified installer evidence

`studio-installer-readiness` #4 produced artifact `studio-installer-readiness-evidence`:

- artifact ID: `10190691003`;
- artifact digest: `sha256:94cceeedd04f96767bbab7d42365697d025bd990715f5e7aa829265f871b3289`;
- evidence schema: `gpbiometricspy-studio-installer-readiness`, version `2`;
- installer SHA-256: `be506fdbf54b50498d9c77c8551095fdc87f3496dd56779ff7df8e8e09341248`;
- installer size: `77,782,018` bytes;
- source and installed native executable SHA-256: `d0d9fee525c884385455ba11c805cf07ce31bb545626fbe692c8952ac06bbb16`;
- installed executable identity match: `true`;
- install scope: `current-user`;
- elevation required: `false`;
- WebView2 strategy: `evergreen-prerequisite-detect-and-remediate`;
- WebView2 Runtime required: `true`;
- detected Runtime version: `152.0.4191.66`;
- detected scope: `machine`;
- detected registry path: `HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`;
- forced-missing setup exit code: `7`;
- forced-missing installation blocked: `true`;
- WebView2 Runtime payload bundled: `false`;
- WebView2 Runtime downloaded in CI: `false`;
- Evergreen policy: `true`;
- installed local DOM smoke: `true`, HTTP startup `3.462 s`;
- installed public-demo DOM smoke: `true`, HTTP startup `2.952 s`;
- external Python required: `false`;
- uninstall exit code: `0`;
- uninstall registration removed: `true`;
- shortcuts removed: `true`;
- payload files removed: `true`;
- installer signed: `false`;
- installer published: `false`.

The forced-missing Inno log records `WebView2 Runtime forced missing by CI validation hook`, `WebView2 Runtime missing; setup cannot continue`, and the official Microsoft WebView2 remediation destination. The missing-runtime test installs no Studio payload.

## Boundary retained

This checkpoint proves Runtime detection and remediation behavior. It does **not** turn the pull-request installer into a redistributable release. Production release still requires the separately tracked trusted signing/timestamping boundary, final release-window configuration and branding review, immutable release-build/checksum provenance, update policy, and human Windows installation/UX validation.

The later documentation commit containing this file is not itself the certified product identity. The immutable certified code checkpoint remains `6a72c593e1dbd310d528ba7d1c66777a78583263`.
