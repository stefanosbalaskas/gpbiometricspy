# Studio windowed native release readiness

This checkpoint closes the Windows GUI-subsystem / console-free native presentation boundary for the `0.1.6` Studio development line while preserving the existing console-visible native build as the engineering and diagnostic baseline.

## Certified product/release-engineering identity

The immutable certified code checkpoint is:

`9153754dc36bd796d8871953287436614e172b75`

At that exact SHA, all thirteen pull-request workflow families completed successfully:

| Workflow | Run | Run ID | Result |
| --- | ---: | ---: | --- |
| `tests` | #463 | `34581859785` | success |
| `studio` | #248 | `34581859803` | success |
| `studio-e2e` | #219 | `34581859766` | success |
| `studio-production` | #220 | `34581859795` | success |
| `studio-packaging` | #27 | `34581859752` | success |
| `studio-signing-readiness` | #12 | `34581859891` | success |
| `studio-installer-readiness` | #6 | `34581859828` | success |
| `studio-windowed-readiness` | #1 | `34581859867` | success |
| `branch-coverage` | #261 | `34581859715` | success |
| `deep-parity` | #452 | `34581859812` | success |
| `interoperability` | #451 | `34581859732` | success |
| `docs` | #233 | `34581859845` | success |
| `CodeQL` | #454 | `34581859805` | success |

The ordinary packaging gate still validates PyInstaller onedir, onefile and console-visible native WebView2 builds on Python 3.11 and 3.14. Nuitka remains manual comparison-only through `workflow_dispatch`.

## Why a bootstrap is required

PyInstaller's Windows `windowed` / `noconsole` mode uses the Windows GUI bootloader and does not provide a console. PyInstaller documents that, in this mode, `sys.stdin`, `sys.stdout`, and `sys.stderr` can be `None`, which can break application or dependency code that assumes normal standard streams.

The release-window bootstrap therefore runs before importing the existing frozen native application:

1. if `sys.stdin` is absent, it is replaced with a text reader backed by `os.devnull`;
2. if stdout/stderr are absent, they are replaced with a shared line-buffered UTF-8 sink;
3. CI can point that sink at `GPBIOMETRICSPY_WINDOWED_LOG_PATH` to preserve startup evidence;
4. otherwise the sink is `os.devnull`, avoiding a hidden console dependency;
5. only after stream stabilization does the wrapper import `studio.native_frozen` and delegate to its unchanged `main()`.

The existing `tools/pyinstaller/gpbiometricspy_studio_native.spec` remains `console=True`. The separate `gpbiometricspy_studio_native_windowed.spec` is the release-window evaluation variant and sets `console=False`.

Authoritative PyInstaller references:

- https://pyinstaller.org/en/v6.22.2/common-issues-and-pitfalls.html#sys-stdin-sys-stdout-and-sys-stderr-in-noconsole-windowed-applications-windows-only
- https://pyinstaller.org/en/v6.22.2/usage.html

## Independent Windows proof

The dedicated Windows harness does not infer windowed behavior from the PyInstaller spec. It verifies the compiled PE directly:

- reads the PE header offset at `0x3c`;
- validates the `PE\0\0` signature;
- reads the Optional Header `Subsystem` field at PE offset + 92;
- requires subsystem value `2`, `IMAGE_SUBSYSTEM_WINDOWS_GUI`;
- launches the executable without redirecting stdout/stderr;
- requires the release bootstrap itself to report `console_attached=false` using `GetConsoleWindow()`;
- removes external Python from `PATH` and clears `PYTHONHOME` / `PYTHONPATH`;
- exercises both local and synthetic-only public-demo modes;
- requires HTTP 200, WebView2/`edgechromium`, the pywebview DOM-loaded event and clean native-window close;
- independently re-verifies Windows PE metadata and icon resources;
- deletes the built bundle, build tree and venv before evidence upload.

## Certified evidence

`studio-windowed-readiness` #1 produced artifact `studio-windowed-readiness-evidence`:

- artifact ID: `10192036938`;
- artifact digest: `sha256:11abda3317bd4cd785dc968f9d693ba0200e3ca0cacda32950f45857c14b6c6a`;
- evidence schema: `gpbiometricspy-studio-native-windowed-smoke`, version `1`;
- release artifact: `false`;
- bundle mode: `onedir-native-windowed-webview2`;
- renderer: `edgechromium`;
- console: `false`;
- PE subsystem: `2` (`IMAGE_SUBSYSTEM_WINDOWS_GUI`);
- console attached: `false`;
- external Python required: `false`;
- DOM loaded required: `true`;
- Windows identity verified: `true`;
- engineering console build preserved: `true`;
- product name: `gpbiometricspy Studio`;
- product version: `0.1.6.dev0`;
- Windows file version: `0.1.6.0`;
- local HTTP startup: `3.188 s`;
- public-demo HTTP startup: `2.974 s`;
- file count: `2,012`;
- bundle bytes: `249,803,733`;
- build time: `85.413 s`;
- Python: `3.14.7`;
- PyInstaller: `6.22.2`;
- pywebview: `6.2.1`.

Both retained mode logs begin with `Windowed release bootstrap: console_attached=false`, then show the unchanged frozen native app reaching Uvicorn HTTP service, requesting the `edgechromium` renderer, using pywebview WinForms/Chromium, opening the Shiny WebSocket, firing `_pywebviewready`, firing `Native DOM loaded.`, and closing cleanly.

No executable, PFX, P12, build tree or virtual environment is retained in the readiness artifact.

## Boundary retained

This checkpoint proves a console-free Windows-native presentation without altering the scientific/Shiny application and without removing the diagnosable console-visible engineering build.

It does not itself make the installer redistributable. Remaining release boundaries include a trusted production signing identity and timestamping, final brand/icon/application-metadata review, immutable release-build provenance/checksums/SBOM, update/upgrade policy, and human Windows installation/first-session UX validation.

The documentation commit containing this file is not itself the certified product identity. The immutable certified code checkpoint remains `9153754dc36bd796d8871953287436614e172b75`.
