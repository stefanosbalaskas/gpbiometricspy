# gpbiometricspy Studio product roadmap

The `0.1.6` development line moves **gpbiometricspy Studio** from a scientifically complete Shiny application toward a polished standalone research product.

The scientific backend is not being replaced. Studio continues to call public `gpbiometricspy` functions so application polish, teaching, project continuity and packaging remain separate from the validated scientific contract.

## Recovery point

Before product-polish work began, the fully qualified post-0.1.5 application state was preserved on:

```text
backup/studio-0.1.5-pre-product-polish
```

That branch points to exact commit:

```text
98e6dcc23406986c8a89c2c5b35c772ca73c1fae
```

The immutable `v0.1.5` tag, GitHub Release, PyPI artifacts and Zenodo version DOI remain separate and untouched.

## Product principles

1. **Guide, do not guess.** The interface should tell users what the next defensible step is.
2. **One scientific engine.** Studio must keep calling package functions rather than duplicating methods.
3. **Quality before interpretation.** QC readiness should be visible before analysis is encouraged.
4. **Progressive disclosure.** Guided defaults should be approachable; expert controls should remain available.
5. **Actionable errors.** Error messages should tell the researcher what failed and what to do next.
6. **Projects should be reopenable.** Recipes, fingerprints, provenance and source-resource identity must support real project continuity.
7. **Public means synthetic.** Anonymous deployment remains fail-closed for participant-data uploads.
8. **Local/private means accountable.** Research-data deployments require explicit access, storage, logging and retention controls.
9. **Packaging is downstream.** Standalone executables and installers must wrap the same Shiny/scientific engine rather than fork it.

## Phase 1 — product shell and onboarding

Status: **delivered**

- product-first GitHub and documentation landing paths;
- end-user Studio installation and first-session guidance;
- PATH-independent Windows launch instructions;
- visible Project → Quality → Analyze → Align → Model → Report research path;
- project-readiness and next-step summaries;
- clearer sidebar hierarchy, session status, spacing, cards, controls and mobile behavior;
- improved empty-state language;
- clean Windows installed-launch smoke on Python 3.11 and 3.14.

## Phase 2 — navigation and workflow guidance

Status: **delivered**

- grouped Home → Quality → Analyze → Integrate → Model → Report navigation while preserving stable internal module IDs;
- guided synthetic multimodal, eye-tracking and physiology starts;
- stepwise guided continuation with live progress and a next-step Continue action;
- multimodal route: Events & Alignment → Multimodal → Reporting;
- eye-tracking route: Pupil → Gaze/AOI → Reporting;
- physiology route: EDA/SCR → PPG/HR/HRV → Reporting;
- replacing the dataset retires stale guided state;
- package-native channel/capability state drives advisory Home recommendations;
- signal workflows are recommended without auto-running or interpreting analyses;
- TTL/event alignment is deferred until appropriate;
- malformed or incomplete validation metadata fails closed;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment and Multimodal expose reactive readiness banners;
- readiness distinguishes absent data, pending QC, ready, complete and prerequisite-blocked states without disabling expert controls;
- Event Alignment readiness uses shared project/capability state rather than cross-module Shiny input leakage;
- browser regression tests navigate by stable Shiny module identifiers.

## Phase 3 — project management and reproducibility

Status: **delivered**

- first-class project identity propagated through recipes, manifests, reports and bundles;
- exact SHA-256 source-resource fingerprint validation remains mandatory on restore;
- explicit project-recipe `Unsaved` → `Saved` → `Unsaved changes` lifecycle;
- an exact-fingerprint restore establishes the restored metadata as the saved checkpoint;
- later project changes invalidate stale report artifacts;
- Reporting exposes a researcher-readable metadata-only Timeline while preserving the original full Provenance table;
- recipes exclude raw biometric rows and cached analysis-result tables;
- local/private Reporting offers an opt-in, default-off recent-project locator on recipe save;
- recent history stores only project name, save time, dataset fingerprint, row/column counts, analysis/annotation counts and suggested recipe filename;
- source paths, column names, annotation content, provenance payloads, parameters, cached results, raw rows and credentials are excluded;
- recent entries are strict-schema validated, deduplicated, bounded to 12 entries / 256 KB and atomically written;
- the UI shows only a shortened fingerprint and current-dataset Match indicator;
- recent history is a locator, not a restore source; reopening still requires explicit data + recipe and exact fingerprint validation;
- public-demo markup contains no recent-project controls and the service rejects public-demo disk access.

## Phase 4 — examples, presets and first-session guidance

Status: **delivered; human subjective validation still required**

- bundled synthetic multimodal, eye-tracking and EDA/cardiovascular walkthroughs;
- Home exposes four non-executing teaching narratives: physiology, eye tracking, event-linked multimodal work and modelling;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment, Multimodal and Statistics/Modelling expose documented teaching presets;
- each preset states the existing Guided starting point, prerequisites, checks before inference, interpretation guardrails and next step;
- preset guidance is presentation-only and does not mutate controls, run analyses, fit models or infer psychological states;
- EDA guidance documents the existing 31-sample tonic window, automatic SCR threshold and 10-sample minimum peak distance;
- cardiac guidance documents 40–180 bpm, 0.30 RR tolerance, 300–2000 ms IBI limits and 500 ms maximum jump;
- pupil guidance documents conservative blink-gap detection without automatic interpolation, smoothing, baseline correction or event summaries;
- gaze guidance documents screen-bound filtering, event detection, 100 ms minimum fixation, 10 ms minimum saccade and 100 ms maximum event gap;
- cluster-permutation guidance preserves the validated two-condition, within-subject, one-dimensional design and package-native diagnostics;
- Chromium verifies documented Guided defaults against live controls and proves that merely viewing guidance does not run analysis;
- a dedicated first-session Chromium contract follows Home teaching context → physiology guided start → automatic foundation QC → EDA/SCR → Continue → PPG/HR/HRV → Reporting → report build → 3/3 completion → Timeline → recipe save → dirty-state transition;
- the first-session contract passes on Python 3.11 and 3.14.

## Phase 5 — errors, diagnostics and supportability

Status: **delivered for the current product surface**

- privacy-safe Studio Doctor with human-readable and JSON output;
- diagnostics do not inspect raw biometric samples or transmit support information;
- installed wheel/sdist browser failures preserve bounded CI diagnostics;
- clean Windows CI installs Studio non-editably in a fresh virtual environment and verifies imports from outside the checkout;
- Windows CI exercises Studio Doctor, `gpbiometricspy-studio.exe` and `python -m studio.cli` on Python 3.11 and 3.14;
- installed upload retry guards match substantive missing-resource conditions rather than presentation punctuation;
- external-event, target-stream and dual-resource replay identity/fingerprint/count/path-nondisclosure assertions remain intact;
- shared `GP-STUDIO-*` support codes cover input, prerequisite, identity, external-resource, analysis and unknown failures with concrete next actions;
- local/private mode retains bounded technical detail;
- public-demo mode suppresses caught exception detail;
- recipe/resource identity failures remain fail-closed and never recommend bypassing fingerprint verification.

## Phase 6 — desktop-style local and standalone packaging

Status: **browser-backed launcher plus PyInstaller onedir standalone and frozen-browser baseline certified**

- Shiny for Python remains the single application engine;
- `gpbiometricspy-studio-desktop` chooses an available loopback port and opens Studio automatically;
- `--no-browser` supports manual/browser-managed startup and troubleshooting;
- clean Windows CI verifies the ordinary installed launch path on Python 3.11 and 3.14;
- a separate frozen adapter uses Shiny's in-process runner for standalone packaging and leaves the normal pip launchers unchanged;
- PyInstaller **6.22.2** with pyinstaller-hooks-contrib **2026.7** is pinned as the first standalone evaluation toolchain;
- the build is deliberately **onedir**, console-enabled and UPX-disabled for diagnosability;
- Windows Python 3.11 and 3.14 each build and launch frozen Studio successfully with external Python removed from `PATH` and `PYTHONHOME` / `PYTHONPATH` cleared;
- baseline measurement on Python 3.11: 1,892 files, 235,369,466 bytes (~224.5 MiB), 3.563 s to HTTP 200;
- baseline measurement on Python 3.14: 1,887 files, 239,684,216 bytes (~228.6 MiB), 3.447 s to HTTP 200;
- CI now drives **meaningful Chromium interaction against the frozen executable itself** on both supported Windows interpreters;
- frozen local-mode Chromium follows Home teaching context → physiology guided start → foundation QC → EDA/SCR → PPG/HR/HRV → Reporting → report build → 3/3 guided completion;
- frozen public-mode Chromium launches the same executable with `--public-demo`, verifies synthetic-only messaging, absence of visible external upload controls, a successful synthetic gaze workflow and unavailable project-recipe upload/restore controls;
- the frozen browser harness connects to the URL served by the `.exe` and does not use Shiny's source-app fixture;
- CI uploads only bounded metrics, JUnit and server logs, not the generated binary bundle, build tree or virtual environment;
- the frozen bundle remains an evaluation artifact, not a redistributable or signed release installer;
- remaining packaging decisions: onefile tradeoffs, Nuitka comparison, icon/version metadata, optional native-window/webview presentation, signing, installer/update technology and reproducible release-build provenance;
- a native-window wrapper, if adopted, remains packaging rather than a scientific-runtime rewrite.

See [Studio standalone packaging evaluation](studio-packaging-evaluation.md) for the frozen-build and browser contracts.

## Phase 7 — hosted deployment

Status: **deployment boundary documented; production hosting remains future work**

### Public demonstration

- synthetic-only;
- no participant-data upload controls;
- sanitized error details;
- clear demo/privacy boundary;
- representative guided workflows;
- production health checks, resource limits and browser regression tests remain deployment gates.

### Authenticated/private research deployment

- authentication and authorization are deployment-layer responsibilities, not implicit Studio features;
- storage, retention, encryption, logging/audit, upload limits, secrets and disaster recovery must be defined before research-data upload is enabled;
- an anonymous public deployment must not be presented as a participant-data service.

See [Studio deployment and support](studio-deployment.md) for the current operational boundary.

## Current validation checkpoint

The current certified **product-code** checkpoint is:

```text
943e86c5f0f2a358e423ebf1abd32bebcfa15553
```

At that exact head, **all ten pull-request workflow families passed**:

- `tests` run #440;
- `studio` run #225 on Python 3.11 and 3.14;
- `studio-e2e` run #196, Chromium on Python 3.11 and 3.14;
- `studio-production` run #197: Linux Python 3.11 and 3.14 installed wheel/source-distribution Chromium replay plus synthetic runtime smoke, and clean Windows local-install/Doctor/launch smoke on Python 3.11 and 3.14;
- `studio-packaging` run #4: Windows Python 3.11 and 3.14 frozen-launcher unit contract, PyInstaller onedir build, standalone launch without external Python, and local/public frozen Chromium interaction;
- `branch-coverage` run #238;
- `deep-parity` run #429;
- `interoperability` run #428;
- `docs` run #210;
- `CodeQL` run #431.

This checkpoint supersedes the previous standalone-startup checkpoint `a4e8e9ad1abfd2f6d47cba4039f411f5ce6f1c44`. The new tranche changes only frozen-browser tests, the Windows frozen-browser harness and packaging CI; it does not modify `src/gpbiometricspy`, scientific workflow implementations, normal pip launchers, runtime privacy policy, project fingerprints or replay rules.

The checkpoint additionally certifies:

- all previously certified first-session, project/reproducibility, guidance and measurement safeguards;
- clean Windows pip-style install → Doctor → launch on Python 3.11 and 3.14;
- Linux installed wheel/source-distribution Chromium replay on Python 3.11 and 3.14;
- Windows standalone PyInstaller launch without externally installed Python;
- real frozen local-mode Shiny/WebSocket/reactive interaction through guided physiology analysis and Reporting on Windows Python 3.11 and 3.14;
- real frozen public-mode interaction preserving the synthetic-only/no-upload boundary on both Windows interpreters;
- bounded frozen-browser diagnostics without publishing the binary bundle.

Further product-polish code commits must pass the same ten-family matrix before they supersede this checkpoint.

## 0.1.6 release criteria for Studio

Before calling Studio `0.1.6` product-polished, require at minimum:

- all scientific package gates remain green;
- Studio unit/smoke, source Chromium E2E, production/distribution and standalone-packaging gates remain green;
- no regression in public synthetic fail-closed behavior;
- clean Windows pip install → Studio Doctor → launch remains green on Python 3.11 and 3.14;
- standalone Windows build → launch without external Python remains green on Python 3.11 and 3.14;
- the researcher-facing launch → guided demo → QC → analysis → report/save path remains browser-certified;
- frozen standalone local and public browser interaction remains green on both supported Windows interpreters;
- the complete onboarding path is still tested by a human for comprehension, visual hierarchy, friction and install/launch usability;
- keyboard and narrow-viewport browser checks remain green;
- project/replay fingerprint guards remain fail-closed;
- documentation reflects actual installed and frozen behavior;
- signing, installer/update policy and reproducible release-build rules are defined before distributing a native installer;
- the 0.1.5 backup/release boundary remains untouched.

## Current human-testing target

Automated coverage now spans both the ordinary pip-installed launcher and a standalone Windows PyInstaller application with real browser interaction. Human validation should focus on **comprehension, visual hierarchy, perceived friction and install/launch experience** while replaying the research path:

```text
install or open the standalone evaluation build
  → run Studio Doctor when using the pip-installed path
  → launch
  → review the Home teaching routes
  → choose a guided synthetic walkthrough or load the synthetic demo only
  → inspect module readiness / foundation QC
  → review the teaching preset and Guided baseline
  → run a signal analysis
  → follow Continue into the next signal family
  → complete the guided route and build the report
  → verify a safe GP-STUDIO-* recovery message for an invalid action
  → review Timeline and full Provenance
  → export a privacy-preserving project recipe
  → verify Saved / Unsaved changes after project edits
  → optionally use the local metadata-only recent-project list
  → restore only against the exact source fingerprint
```

The next engineering decision should compare **distribution ergonomics rather than scientific behavior**: onefile vs onedir, PyInstaller vs Nuitka, optional native-window/webview presentation, signing, installer/uninstaller behavior and update policy. The next human tranche remains **subjective first-session validation**.
