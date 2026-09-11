# Studio windowed installer integration checkpoint

This checkpoint records the first exact-head certification in which the console-free native WebView2 bundle is exercised through the Windows installer path without replacing the retained console-visible engineering build.

## Certified product-code identity

- Certified product-code SHA: `449a0abc84788ed31c9dc3ccf292e72721a9414d`
- Previous certified windowed SHA: `9153754dc36bd796d8871953287436614e172b75`
- Product version under test: `0.1.6`
- File version under test: `0.1.6.0`
- PR: `#107`
- Certification rule: every expected pull-request workflow family must be workflow-level `completed/success` on the exact product-code SHA.

A reproducible Python 3.14 browser synchronization issue was discovered before certification: after the EDA/SCR workflow completed, Home guidance could remain in Shiny's `recalculating` state for longer than Playwright's default five-second negative assertion. The product requirement was not weakened. The E2E assertion still requires `EDA / SCR` to disappear from Home guidance; it now uses the same 60-second reactive-settling budget already used by surrounding Shiny assertions. Both Python 3.11 and Python 3.14 then passed on the certified head.

## Exact-head workflow certification

All fourteen expected workflow families completed successfully on `449a0abc84788ed31c9dc3ccf292e72721a9414d`:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| `CodeQL` | #458 | `34585977493` | success |
| `deep-parity` | #456 | `34585977560` | success |
| `branch-coverage` | #265 | `34585977480` | success |
| `studio` | #252 | `34585977515` | success |
| `studio-signing-readiness` | #16 | `34585977494` | success |
| `tests` | #467 | `34585977516` | success |
| `studio-production` | #224 | `34585977475` | success |
| `studio-packaging` | #31 | `34585977532` | success |
| `docs` | #237 | `34585977433` | success |
| `studio-e2e` | #223 | `34585977417` | success |
| `studio-windowed-readiness` | #5 | `34585977397` | success |
| `studio-windowed-installer-readiness` | #3 | `34585977385` | success |
| `interoperability` | #455 | `34585977457` | success |
| `studio-installer-readiness` | #10 | `34585977430` | success |

The `studio-e2e` #223 jobs both passed:

- Python 3.11 job `103220179051`: success.
- Python 3.14 job `103220179185`: success.

## Windowed installer evidence

The exact-head `studio-windowed-installer-readiness` #3 evidence artifact is:

- Artifact name: `studio-windowed-installer-readiness-evidence`
- Artifact ID: `10193733620`
- Artifact ZIP SHA-256: `41b44d87fd458a7d95a441930343cc766129f4f5576bffa7cbcf3de6e758d1aa`
- Evidence retention: diagnostics only; no `.exe`, `.pfx`, or `.p12` is retained.

The integration proof records:

- Installer technology: Inno Setup.
- Install scope: current user; elevation not required.
- Stable AppId: `fd3ca1af-0ebb-5061-9c59-f7ab1079252e`.
- Source bundle: `onedir-native-windowed-webview2`.
- Source PE subsystem: `2` (`IMAGE_SUBSYSTEM_WINDOWS_GUI`).
- Installed PE subsystem: `2` (`IMAGE_SUBSYSTEM_WINDOWS_GUI`).
- Console: `false`; attached console: `false`.
- Console-visible engineering build remains preserved as a separate diagnostic target.
- Source executable SHA-256: `d3654fcccc8439f1706bd0f0668e8f611575d84c280e75933ba9a6ab02402e18`.
- Installed executable SHA-256: `d3654fcccc8439f1706bd0f0668e8f611575d84c280e75933ba9a6ab02402e18`.
- Installed executable byte identity: exact match.
- Unsigned integration-proof installer SHA-256: `76c8f5706bd7fe91b23c45c9c1dc9db29f1ac14d5e50131fb496dde9e7072b56`.
- Installer size: `77,783,039` bytes.
- Windowed source bundle: `2,012` files; `249,803,733` bytes.
- Windowed source build time: `87.467` seconds.
- Installed local-mode HTTP readiness: `3.109` seconds.
- Installed public-demo HTTP readiness: `2.938` seconds.
- Local DOM smoke: pass.
- Public-demo DOM smoke: pass.
- External Python required: `false`.
- WebView2 strategy: Evergreen prerequisite detect-and-remediate.
- Detected WebView2 runtime: `152.0.4191.66`, machine scope.
- Forced missing-WebView2 installation exit code: `7`; payload installation blocked.
- WebView2 runtime is neither bundled nor downloaded during CI.
- Uninstaller exit code: `0`.
- Uninstall registration removed: `true`.
- Shortcuts removed: `true`.
- Payload files removed: `true`.
- Production signing remains required, including a production timestamp.

The runner's file-version metadata for `ISCC.exe` reports `0.0.0.0`. This is not a product or installer failure; it is a provenance-quality limitation in the current evidence field and should be replaced in a later release-provenance tranche with a reliable Inno Setup version source rather than inferred from the executable's FileVersionInfo.

## Release boundary

This checkpoint does **not** publish or sign a release installer. The integration installer is intentionally unsigned and is not retained as workflow evidence. Production distribution still requires an authorized code-signing identity outside the repository, SHA-256 signing, an RFC3161 timestamp, release checksums/provenance, and a final human UX/branding review.

`main`, the stable `v0.1.5` tag/release, PyPI, Zenodo, and the recovery checkpoint remain unchanged by this certification.
