# Studio standalone packaging evaluation

This document records the **0.1.6 development-line packaging experiment** for gpbiometricspy Studio. It is not a release installer specification and it does not change the scientific engine.

## Status

**PyInstaller onedir baseline plus meaningful frozen Chromium interaction certified on Windows Python 3.11 and 3.14.**

The certified product-code checkpoint is:

```text
943e86c5f0f2a358e423ebf1abd32bebcfa15553
```

At that exact head, `studio-packaging` workflow run **#4** passed on both Windows Python 3.11 and 3.14. The other nine pull-request workflow families also passed at the same SHA, so the standalone proof did not replace or weaken the scientific, Studio, source-browser, distribution, interoperability, coverage, documentation or CodeQL gates.

The frozen executable now passes two browser contracts on each supported Windows build interpreter:

1. **Local research path** — Home teaching context → physiology guided start → bundled synthetic data → foundation QC → EDA/SCR → guided Continue → PPG/HR/HRV → guided Continue → Reporting → report build → `3/3` guided completion.
2. **Public-demo boundary** — the same frozen executable launched with `--public-demo` exposes the synthetic-only public identity, hides external upload controls, runs a synthetic gaze analysis, reaches Reporting, and keeps project-recipe upload/restore controls unavailable.

The browser harness connects only to the URL served by the frozen `.exe`; it does not use Shiny's source-app fixture. This proves real HTTP/WebSocket/reactive interaction with the standalone application rather than only process startup.

### Baseline size/startup measurements

The earlier certified onedir baseline measurements remain representative for this evaluation configuration:

| Build interpreter | Bundle files | Bundle bytes | Approx. MiB | Startup to HTTP 200 | External Python required |
| --- | ---: | ---: | ---: | ---: | --- |
| Python 3.11.9 | 1,892 | 235,369,466 | 224.5 | 3.563 s | No |
| Python 3.14.7 | 1,887 | 239,684,216 | 228.6 | 3.447 s | No |

Those measurements are CI evidence for the **diagnosable onedir baseline**, not size or startup guarantees for a future signed release installer.

## Decision for the first experiment

The standalone proof uses **PyInstaller 6.22.2** with **pyinstaller-hooks-contrib 2026.7** in **onedir** mode on Windows.

Why this remains the first candidate:

- PyInstaller supports the targeted Python 3.14 line;
- it produces self-contained OS-specific application bundles, so an end user does not need to install Python separately;
- onedir mode keeps the evaluation inspectable and easier to diagnose than onefile mode;
- the existing Studio application remains a Shiny application rather than being rewritten for a desktop toolkit;
- Shiny's in-process `run_app()` path avoids relying on `sys.executable -m shiny` inside a frozen executable.

PyInstaller is not a cross-compiler. Windows bundles are therefore built and tested on Windows. CI evaluates Python 3.11 and 3.14 independently.

## What is intentionally unchanged

The experiment does **not**:

- replace Shiny;
- duplicate or reimplement any gpbiometricspy scientific function;
- change analysis defaults, QC logic, reporting logic or project fingerprints;
- alter the public-demo upload boundary;
- modify the normal pip launchers (`gpbiometricspy-studio`, `gpbiometricspy-studio-public`, `gpbiometricspy-studio-desktop`);
- produce or publish a signed installer;
- publish the generated binary bundle as a release artifact;
- enable onefile mode or embed a webview.

The frozen entry point remains only a downstream packaging adapter.

## Frozen entry point

`studio/frozen.py` loads the requested Studio boundary lazily and invokes Shiny in-process. Local mode remains the default; `--public-demo` loads the existing synthetic-only public boundary before the full application is imported.

The launcher keeps the existing local port-selection policy and supports:

```text
--host
--port
--public-demo
--no-browser
```

Production-style frozen execution uses:

```text
reload=False
dev_mode=False
```

## Build and browser definitions

The evaluation files are:

```text
tools/pyinstaller/requirements.txt
tools/pyinstaller/gpbiometricspy_studio.spec
.github/scripts/test_studio_pyinstaller_windows.ps1
.github/scripts/test_studio_frozen_browser_windows.ps1
.github/workflows/studio-packaging.yml
studio/e2e/test_frozen_local_e2e.py
studio/e2e/test_frozen_public_e2e.py
```

The spec keeps the build diagnosable:

- onedir bundle;
- console enabled;
- UPX disabled;
- package data collected for Studio, gpbiometricspy and the Shiny runtime;
- Studio modules and the Shiny/Uvicorn runtime made explicit to the freezer;
- development-only tools excluded from the bundle where possible.

## Windows standalone smoke contract

The standalone PowerShell smoke:

1. creates a new isolated virtual environment;
2. installs the current repository with the existing `[studio]` optional dependency;
3. installs the pinned PyInstaller build tools;
4. builds the onedir bundle;
5. verifies the expected `.exe` exists;
6. removes external Python from `PATH` and clears `PYTHONHOME` / `PYTHONPATH`;
7. launches the frozen executable from outside the repository checkout;
8. requires the loopback Studio page to return successfully and contain the Studio identity;
9. records bundle size, file count, startup time, Python version and PyInstaller version;
10. stops the frozen process and preserves only small diagnostic logs/metrics in CI.

That contract proves the standalone app does not require an externally discoverable Python interpreter.

## Frozen Chromium contract

After the standalone startup smoke succeeds, CI installs a separate Playwright/Chromium **test harness** on the runner. The browser harness is not bundled into Studio.

The harness then:

1. launches the exact frozen `.exe` in normal local mode;
2. waits for the standalone server to become ready;
3. runs the frozen-local Chromium test against the served URL;
4. verifies teaching context, guided synthetic start, foundation QC, EDA/SCR, PPG/HR/HRV, Reporting and guided completion;
5. stops that process;
6. launches the same executable with `--public-demo`;
7. runs the frozen-public Chromium test against the served URL;
8. verifies synthetic-only messaging, absence of visible external file inputs, hidden AOI/project-recipe upload paths and a successful synthetic analysis/report path;
9. preserves JUnit plus bounded frozen server logs when useful for diagnosis.

The CI workflow deliberately does **not** upload the built virtual environment, PyInstaller work tree or binary bundle.

## Local evaluation commands

On Windows PowerShell from the repository root, the standalone build/start smoke is:

```powershell
./.github/scripts/test_studio_pyinstaller_windows.ps1 -Python python -ArtifactsDir "$PWD/.studio-pyinstaller-evaluation"
```

The generated executable can then be subjected to the frozen browser harness with:

```powershell
python -m pip install "pytest-playwright>=0.9,<1"
python -m playwright install chromium
./.github/scripts/test_studio_frozen_browser_windows.ps1 `
  -Python python `
  -Executable "$PWD/.studio-pyinstaller-evaluation/dist/gpbiometricspy-studio/gpbiometricspy-studio.exe" `
  -ArtifactsDir "$PWD/.studio-pyinstaller-evaluation"
```

The generated bundle remains an evaluation artifact only. Do not redistribute it as a gpbiometricspy release.

## Acceptance criteria

The PyInstaller onedir candidate has now satisfied these criteria on both Python 3.11 and 3.14 Windows builds:

- frozen launcher unit contract passes;
- PyInstaller build completes;
- standalone executable starts without an externally discoverable Python interpreter;
- Studio responds successfully on loopback;
- local frozen Chromium exercises meaningful guided scientific workflow and Reporting behavior;
- public frozen Chromium preserves the synthetic-only boundary and hides external upload/restore paths;
- the ordinary scientific, Studio, source-E2E, production, interoperability, branch-coverage, docs and CodeQL gates remain green;
- no public/private runtime or fingerprint safeguard is weakened.

This is enough to treat **PyInstaller onedir as the validated standalone baseline**, but not yet as a distributable release installer.

## Next packaging decisions

The remaining packaging questions are product/distribution questions rather than scientific-engine questions:

- whether onefile materially improves user experience enough to justify slower startup and extraction complexity;
- whether Nuitka offers a better size/startup/build-reproducibility tradeoff;
- whether a lightweight native webview adds meaningful usability over the default browser while preserving the same local Shiny service;
- application icon/version metadata and Windows file properties;
- signing strategy and certificate handling;
- installer technology, per-user vs machine install behavior, uninstall behavior and update policy;
- reproducible release-build provenance and checksum publication;
- human first-session testing of the standalone build on a normal Windows desktop.

## Nuitka status

Nuitka remains a credible secondary candidate. Any comparison should use the same frozen local/public browser contract and compare at least build reproducibility, build time, startup time, bundle size, diagnostic quality and Windows distribution ergonomics.

## Release boundary

Passing the frozen browser contract does **not** itself make `0.1.6` releasable. Human first-session usability, installer/update policy, signing strategy and reproducible release-build rules remain separate release decisions. Stable `0.1.5`, PyPI, Zenodo and the recovery branch are not modified by this evaluation.
