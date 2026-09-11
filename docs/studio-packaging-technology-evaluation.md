# Studio packaging technology evaluation

This note records the completed Windows packaging comparison for the gpbiometricspy Studio `0.1.6` development line.

## Certified comparison checkpoint

The evaluated **product-code** checkpoint is:

`f41bbf6763434321a42491bf9be2b37a78a6c5dd`

At that exact commit, all ten pull-request workflow families completed successfully. `studio-packaging` run **#9** (`34535686926`) passed six Windows jobs:

- PyInstaller onedir on Python 3.11 and 3.14;
- PyInstaller onefile on Python 3.11 and 3.14;
- Nuitka standalone on Python 3.11 and 3.14.

Every packaging mode proved that Studio starts with external Python removed from `PATH`, and every build then passed the same frozen local and `--public-demo` Chromium contracts. The browser JUnit evidence contains one passing local test and one passing public test for every interpreter/mode combination, with zero failures or errors.

## Same-run measurements

| Build interpreter | Technology / mode | Footprint | Files | Startup to HTTP 200 | Build time recorded |
| --- | --- | ---: | ---: | ---: | ---: |
| Python 3.11.9 | PyInstaller 6.22.2 onedir | 224.5 MiB | 1,892 | 3.780 s | not recorded by the legacy onedir metric |
| Python 3.11.9 | PyInstaller 6.22.2 onefile | 93.8 MiB executable | 1 executable | 8.649 s | not recorded by the legacy onefile metric |
| Python 3.11.9 | Nuitka 4.2.1 standalone / MSVC | 369.2 MiB | 1,765 | 13.020 s | 4,152.368 s (69.21 min) |
| Python 3.14.7 | PyInstaller 6.22.2 onedir | 228.6 MiB | 1,887 | 3.784 s | not recorded by the legacy onedir metric |
| Python 3.14.7 | PyInstaller 6.22.2 onefile | 97.0 MiB executable | 1 executable | 8.999 s | not recorded by the legacy onefile metric |
| Python 3.14.7 | Nuitka 4.2.1 standalone / MSVC | 398.7 MiB | 1,764 | 20.162 s | 4,041.341 s (67.36 min) |

The comparison is deliberately same-run and same-head. The Nuitka build therefore did not receive a different Studio/scientific implementation or a weaker runtime contract.

## Interpretation

Relative to PyInstaller onedir, Nuitka standalone was about **64.5% larger on Python 3.11** and **74.4% larger on Python 3.14**. Its startup was about **3.44x slower on Python 3.11** and **5.33x slower on Python 3.14**.

Relative to PyInstaller onefile, Nuitka standalone also started more slowly: about **1.51x** on Python 3.11 and **2.24x** on Python 3.14, while retaining a multi-file distribution footprint.

PyInstaller onefile remained about **58.2% smaller than onedir on Python 3.11** and **57.6% smaller on Python 3.14**, but its cold startup was about 2.29x and 2.38x slower than onedir respectively. That tradeoff remains a distribution choice rather than an automatic replacement for onedir.

The Nuitka compile itself required roughly **67–69 minutes** on clean GitHub-hosted Windows runners before the frozen browser replay, whereas the PyInstaller jobs completed their full build plus browser validation in only a few minutes. That release/CI cost is material even though the final Nuitka executables were functionally correct.

## Decision

**Retain PyInstaller as the Studio Windows packaging baseline.**

- Keep **onedir** as the conservative engineering/reference bundle because it has the fastest startup and the simplest diagnosability.
- Keep **onefile** as a validated optional distribution form when a single executable is materially more convenient and its approximately twofold cold-start penalty is acceptable.
- Treat **Nuitka 4.2.1 standalone as evaluated and compatible, but not preferred** for this application at this checkpoint. It did not provide a footprint or startup advantage that offsets its substantially longer build cost.
- Do not change the scientific engine, Shiny application, public-demo restrictions, provenance/fingerprint guards, or normal pip launchers because of packaging technology.

Nuitka can be reconsidered if a future version or a materially different build configuration changes these measurements, but any such comparison must again preserve the same frozen browser and external-Python-independence contracts.

## Next boundary

The next product experiment is presentation ergonomics: compare the current default-browser desktop launcher with a lightweight Windows native-window/WebView2 wrapper around the **same loopback Shiny service**. That experiment must remain downstream of the existing scientific application and must not become a second UI/scientific implementation.

Code signing, installer/uninstaller behavior, application icon/version resources, update policy, checksums, and reproducible release-build provenance remain later release-readiness gates.