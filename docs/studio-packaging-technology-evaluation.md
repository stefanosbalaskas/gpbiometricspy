# Studio packaging technology evaluation

This note records the completed Windows packaging and presentation comparison for the gpbiometricspy Studio `0.1.6` development line.

## Packaging technology checkpoint

The completed PyInstaller-versus-Nuitka **product-code** checkpoint is:

`f41bbf6763434321a42491bf9be2b37a78a6c5dd`

At that exact commit, all ten pull-request workflow families completed successfully. `studio-packaging` run **#9** (`34535686926`) passed PyInstaller onedir, PyInstaller onefile, and Nuitka standalone on Python 3.11 and 3.14. Every mode proved external-Python independence and passed the same frozen local and `--public-demo` Chromium contracts.

### Same-run packaging measurements

| Build interpreter | Technology / mode | Footprint | Files | Startup to HTTP 200 | Build time recorded |
| --- | --- | ---: | ---: | ---: | ---: |
| Python 3.11.9 | PyInstaller 6.22.2 onedir | 224.5 MiB | 1,892 | 3.780 s | legacy metric did not record build time |
| Python 3.11.9 | PyInstaller 6.22.2 onefile | 93.8 MiB executable | 1 executable | 8.649 s | legacy metric did not record build time |
| Python 3.11.9 | Nuitka 4.2.1 standalone / MSVC | 369.2 MiB | 1,765 | 13.020 s | 4,152.368 s (69.21 min) |
| Python 3.14.7 | PyInstaller 6.22.2 onedir | 228.6 MiB | 1,887 | 3.784 s | legacy metric did not record build time |
| Python 3.14.7 | PyInstaller 6.22.2 onefile | 97.0 MiB executable | 1 executable | 8.999 s | legacy metric did not record build time |
| Python 3.14.7 | Nuitka 4.2.1 standalone / MSVC | 398.7 MiB | 1,764 | 20.162 s | 4,041.341 s (67.36 min) |

The result is unchanged: **PyInstaller remains the packaging baseline**. Onedir is the engineering/reference form, onefile is a validated convenience option with a roughly twofold cold-start penalty, and Nuitka is compatible but not preferred at this checkpoint because it is larger, slower to start, and dramatically slower to build.

Routine pull-request packaging CI therefore keeps PyInstaller onedir and onefile. The reproducible Nuitka comparison remains available through manual workflow dispatch instead of adding roughly 67–69 minutes to normal packaging validation.

## Certified native-window checkpoint

The completed native-window **product-code** checkpoint is:

`3245eef9eb3c141a957384ef7deecb0ed75ee3a6`

At that exact SHA, **all ten pull-request workflow families completed successfully**:

- `tests` #448;
- `studio` #233;
- `studio-e2e` #204;
- `studio-production` #205;
- `studio-packaging` #12;
- `branch-coverage` #246;
- `deep-parity` #437;
- `interoperability` #436;
- `docs` #218;
- CodeQL #439.

`studio-packaging` run **#12** (`34545721787`) passed all six required PyInstaller jobs: onedir, onefile, and native WebView2 on Python 3.11 and 3.14. Nuitka was intentionally skipped on this pull-request run because its separate technology comparison was already certified and remains manually dispatchable.

The native wrapper does not create another scientific or Shiny implementation. It starts the existing Studio application on loopback and presents that same service in pywebview using the Windows `edgechromium` / WebView2 renderer. The normal browser launchers remain available as fallback paths.

### Strengthened native runtime contract

The final native validation is deliberately stronger than an HTTP-only smoke test. For both the full local application and the synthetic-only public boundary, on both Python 3.11 and 3.14, the frozen executable must:

1. run with external Python removed from `PATH` and `PYTHONHOME` / `PYTHONPATH` cleared;
2. bind only to loopback;
3. reach HTTP 200 with the expected Studio identity;
4. initialize the requested `edgechromium` renderer;
5. open the Shiny connection inside the WebView2 host;
6. emit pywebview readiness and the actual DOM-loaded event;
7. remain alive briefly after DOM load; and
8. close the native window and process cleanly.

The diagnostic metric schema is version 2 and records `dom_loaded_required=true`. The local and public logs on both interpreters contain the expected renderer, DOM-loaded, and clean-close evidence, while pywebview diagnostics identify WinForms / Chromium and the Shiny connection opening.

### Same-run presentation measurements

All rows below come from `studio-packaging` #12 at the same certified product-code SHA.

| Interpreter | Presentation / package | Footprint | Files | HTTP readiness | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| Python 3.11.9 | PyInstaller onedir + browser | 224.5 MiB | 1,892 | 3.553 s | existing reference bundle |
| Python 3.11.9 | PyInstaller onefile + browser | 93.8 MiB executable | 1 | 8.455 s | single-file convenience |
| Python 3.11.9 | PyInstaller onedir + WebView2 | 235.8 MiB | 2,018 | local 3.684 s; public 3.422 s | DOM-loaded gate passed; build 75.084 s |
| Python 3.14.7 | PyInstaller onedir + browser | 228.6 MiB | 1,887 | 6.068 s | existing reference bundle |
| Python 3.14.7 | PyInstaller onefile + browser | 97.0 MiB executable | 1 | 8.779 s | single-file convenience |
| Python 3.14.7 | PyInstaller onedir + WebView2 | 238.3 MiB | 2,012 | local 3.344 s; public 2.418 s | DOM-loaded gate passed; build 77.856 s |

The WebView2 onedir bundle is approximately **5.1% larger on Python 3.11** and **4.2% larger on Python 3.14** than the same-run browser onedir bundle. Its HTTP readiness remains in the same practical startup class as onedir and materially below onefile in this run. Startup measurements on shared CI runners are treated as comparative diagnostics rather than hard performance guarantees.

## Decision

For the `0.1.6` development line:

- **Retain PyInstaller as the Windows packaging baseline.**
- **Retain onedir as the engineering/reference bundle.**
- **Retain onefile as an optional validated distribution form**, not the default.
- **Retain the native WebView2 wrapper as the preferred desktop-presentation candidate** for a polished Windows application experience, while preserving browser launch as a fallback and diagnostic route.
- **Keep Nuitka as an evaluated, manually reproducible alternative**, not a routine PR gate or preferred freezer at the current measurements.
- Do not fork or rewrite the scientific engine, Shiny application, public-demo restrictions, provenance/fingerprint guards, or normal pip launchers for desktop presentation.

The native-window candidate should not become a release executable merely because it passed this engineering checkpoint. User-facing release packaging still requires explicit release metadata and installer/security work.

## Next release-readiness boundary

The next tranche is **Windows application identity and binary metadata** before installer/signing work:

- application icon resources and consistent product naming;
- executable/file/product version resources derived from the package version rather than handwritten divergent values;
- company/product/description/copyright metadata where appropriate;
- deterministic build-time validation that the frozen executable carries the expected version identity;
- preservation of console-enabled diagnosable evaluation builds until the metadata path is certified.

After that boundary, the remaining release-readiness work is code signing, installer/uninstaller behavior, update policy, checksums/SBOM as appropriate, and reproducible release-build provenance. None of those should weaken the already-certified local/public browser or native WebView2 contracts.