# Studio standalone packaging evaluation

This document records the **0.1.6 development-line packaging experiment** for gpbiometricspy Studio. It is not a release installer specification and it does not change the scientific engine.

## Decision for the first experiment

The first standalone proof uses **PyInstaller 6.22.2** with **pyinstaller-hooks-contrib 2026.7** in **onedir** mode on Windows.

Why this is the first candidate:

- PyInstaller currently supports Python 3.14;
- it produces self-contained OS-specific application bundles, so a user does not need to install Python separately;
- onedir mode keeps the first evaluation inspectable and easier to diagnose than onefile mode;
- the existing Studio application can remain a Shiny application rather than being rewritten for a desktop toolkit;
- current Shiny exposes an in-process `run_app()` API, which avoids relying on `sys.executable -m shiny` inside a frozen executable.

PyInstaller is not a cross-compiler. Windows bundles must therefore be built and tested on Windows. The CI evaluation runs independently on Python 3.11 and 3.14.

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

The frozen entry point exists only as a downstream packaging adapter.

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

## Build definition

The evaluation files are:

```text
tools/pyinstaller/requirements.txt
tools/pyinstaller/gpbiometricspy_studio.spec
.github/scripts/test_studio_pyinstaller_windows.ps1
.github/workflows/studio-packaging.yml
```

The spec keeps the first build diagnosable:

- onedir bundle;
- console enabled;
- UPX disabled;
- package data collected for Studio, gpbiometricspy and the Shiny runtime;
- Studio modules and the Shiny/Uvicorn runtime made explicit to the freezer;
- development-only tools excluded from the bundle where possible.

## Windows smoke contract

The PowerShell smoke performs a clean standalone evaluation:

1. create a new isolated virtual environment;
2. install the current repository with the existing `[studio]` optional dependency;
3. install the pinned PyInstaller build tools;
4. build the onedir bundle;
5. verify the expected `.exe` exists;
6. remove external Python from `PATH` and clear `PYTHONHOME` / `PYTHONPATH`;
7. launch the frozen executable from outside the repository checkout;
8. require the loopback Studio page to return successfully and contain the Studio identity;
9. record bundle size, file count, startup time, Python version and PyInstaller version;
10. stop the frozen process and preserve only small diagnostic logs/metrics in CI.

The CI workflow deliberately does **not** upload the built virtual environment, PyInstaller work tree, or binary bundle.

## Local evaluation command

On Windows PowerShell from the repository root:

```powershell
./.github/scripts/test_studio_pyinstaller_windows.ps1 -Python python -ArtifactsDir "$PWD/.studio-pyinstaller-evaluation"
```

The generated bundle is an evaluation artifact only. Do not redistribute it as a gpbiometricspy release.

## Acceptance criteria

The PyInstaller candidate is acceptable for the next packaging stage only if all of the following hold on both Python 3.11 and 3.14 Windows builds:

- frozen launcher unit contract passes;
- PyInstaller build completes;
- standalone executable starts without an externally discoverable Python interpreter;
- Studio responds successfully on loopback;
- the visible application identity is correct;
- the ordinary scientific, Studio, E2E, production, interoperability, branch-coverage, docs and CodeQL gates remain green;
- no public/private runtime or fingerprint safeguard is weakened.

Only after that baseline is stable should we evaluate Chromium interaction against the frozen bundle, onefile mode, icon/native-window presentation, code signing and installer technology.

## Nuitka status

Nuitka 4.2 also officially supports Python 3.14 and remains a credible secondary candidate. It is deferred until the PyInstaller onedir baseline is measured because Nuitka introduces a different compilation/toolchain cost profile. A later comparison should use the same acceptance contract and compare at least build reproducibility, build time, startup time, bundle size, diagnostic quality and Windows distribution ergonomics.

## Release boundary

A successful packaging evaluation does not itself make `0.1.6` releasable. Human first-session usability, installer/update policy, signing strategy and reproducible release-build rules remain separate release decisions.
