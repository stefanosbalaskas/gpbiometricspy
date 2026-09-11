# Studio PyInstaller onefile evaluation

This note records the measured **PyInstaller onedir vs onefile** comparison for the gpbiometricspy Studio `0.1.6` development line. It is packaging evidence only: the Shiny application, scientific implementation, public/private runtime policy, project fingerprints, normal pip launchers, stable `v0.1.5`, PyPI and Zenodo are unchanged.

## Certified code checkpoint

The comparison is certified at exact product-code SHA:

```text
b733900d7616bf4788312a1dd6c362cee8c257bf
```

At that exact head, all ten pull-request workflow families passed:

- `tests` #443;
- `studio` #228;
- `studio-e2e` #199;
- `studio-production` #200;
- `studio-packaging` #7;
- `branch-coverage` #241;
- `deep-parity` #432;
- `interoperability` #431;
- `docs` #213;
- `CodeQL` #434.

`studio-packaging` #7 contained four independent Windows jobs: PyInstaller onedir on Python 3.11 and 3.14, plus PyInstaller onefile on Python 3.11 and 3.14. All four completed successfully.

## Measured comparison

The measurements below come from the workflow's machine-readable smoke artifacts produced after building and launching the frozen application with external Python removed from `PATH` and `PYTHONHOME` / `PYTHONPATH` cleared.

| Build interpreter | Mode | Files | Bundle/executable bytes | Approx. MiB | Startup to HTTP 200 | External Python |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Python 3.11.9 | onedir | 1,892 | 235,369,466 | 224.5 | 4.049 s | Not required |
| Python 3.11.9 | onefile | 1 | 98,311,420 | 93.8 | 8.841 s | Not required |
| Python 3.14.7 | onedir | 1,887 | 239,684,216 | 228.6 | 3.779 s | Not required |
| Python 3.14.7 | onefile | 1 | 101,663,178 | 97.0 | 7.579 s | Not required |

Relative to the same-run onedir builds, onefile reduced the packaged footprint by about **58.2% on Python 3.11** and **57.6% on Python 3.14**. Cold startup to HTTP 200 was about **2.18× slower on Python 3.11** and **2.01× slower on Python 3.14**.

These shared-run timings supersede earlier onedir timing observations for purposes of this direct comparison. They are CI measurements, not end-user performance guarantees.

## Browser parity

Both onefile builds passed the same frozen Chromium contracts already required of onedir:

1. **Local research path** — Home teaching context → guided physiology start → foundation QC → EDA/SCR → PPG/HR/HRV → Reporting → report build → `3/3` guided completion.
2. **Public-demo boundary** — synthetic-only identity, no visible external file inputs, successful synthetic gaze analysis, Reporting access, and unavailable project-recipe upload/restore controls.

The browser connects to the application served directly by the frozen executable. It does not substitute the source Shiny fixture.

## Decision

PyInstaller onefile is now a **validated distribution option**, not an automatic replacement for onedir.

- **onefile advantage:** one user-facing executable and roughly 58% smaller packaged footprint in the certified Windows matrix;
- **onefile cost:** approximately doubled cold-start latency plus the normal self-extraction/runtime-temp complexity of onefile packaging;
- **onedir advantage:** materially faster startup and easier inspection/diagnosis;
- **scientific/runtime parity:** no observed difference under the certified local and public frozen-browser contracts.

Therefore the release decision remains open until the same user-facing contracts are compared against a second freezer/compiler and, if warranted, a native-window presentation. The next isolated engineering tranche is **Nuitka standalone evaluation** using the same external-Python independence test and frozen local/public Chromium contract.

No native binary is published from PR CI, and this evidence does not constitute a signed or redistributable installer decision.
