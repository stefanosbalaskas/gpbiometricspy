# gpbiometricspy Studio product roadmap

The `0.1.6` development line moves **gpbiometricspy Studio** from a scientifically complete Shiny application toward a polished standalone research product.

The scientific backend is not being replaced. Studio continues to call public `gpbiometricspy` functions so application polish remains separate from the validated scientific contract.

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

Studio should become easier to use without becoming scientifically opaque.

1. **Guide, do not guess.** The interface should tell users what the next defensible step is.
2. **One scientific engine.** Studio must keep calling package functions rather than duplicating methods.
3. **Quality before interpretation.** QC readiness should be visible before analysis is encouraged.
4. **Progressive disclosure.** Guided defaults should be approachable; expert controls should remain available.
5. **Actionable errors.** Error messages should tell the researcher what failed and what to do next.
6. **Projects should be reopenable.** Recipes, fingerprints, provenance and source-resource identity must support real project continuity.
7. **Public means synthetic.** Anonymous deployment remains fail-closed for participant-data uploads.
8. **Local/private means accountable.** Research-data deployments require explicit access, storage, logging and retention controls.

## Phase 1 — product shell and onboarding

Status: **delivered in the current 0.1.6 development branch**

- product-first GitHub landing page;
- product-first documentation home;
- end-user Studio installation and first-session guide;
- PATH-independent Windows launch instructions;
- clean Windows installed-launch smoke is now CI-certified on Python 3.11 and 3.14;
- guided Home screen with a visible Project → Quality → Analyze → Align → Model → Report path;
- project-readiness and next-step summaries;
- clearer sidebar hierarchy and session status;
- more consistent spacing, cards, controls and mobile behavior;
- improved empty-state language.

## Phase 2 — navigation and workflow guidance

Status: **guided starts, channel-aware Home recommendations and module-level prerequisite guidance delivered**

- top navigation is grouped as Home → Quality → Analyze → Integrate → Model → Report;
- established module identifiers remain unchanged underneath the grouped navigation;
- a workflow-progress table exposes required, ready, optional and completed stages;
- guided synthetic starts open multimodal, eye-tracking or physiology workflows after foundation QC;
- guided starts now advance stepwise rather than jumping directly to a downstream module;
- multimodal guidance begins at Events & Alignment before Multimodal and Reporting;
- eye-tracking guidance advances Pupil → Gaze/AOI → Reporting;
- physiology guidance advances EDA/SCR → PPG/HR/HRV → Reporting;
- Home exposes live guided progress and a next-step Continue action;
- replacing the dataset retires a stale guided walkthrough so guidance cannot leak across projects;
- outside an active guided walkthrough, Home derives advisory next-step recommendations from package-native foundation-QC channel validation plus the existing pupil/gaze capability helpers;
- active EDA, heart-rate, pupil and gaze capabilities are surfaced as defensible signal-level next steps without auto-running or interpreting analyses;
- active TTL markers are deferred until signal-level work is recorded, then Events & Alignment is recommended before Multimodal integration;
- malformed or incomplete channel-validation metadata fails closed rather than manufacturing biosignal recommendations;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment and Multimodal expose a compact reactive readiness banner before their normal scientific controls;
- readiness states explain whether data are absent, foundation QC is still pending, the workflow is ready, the corresponding result is already stored, or a prerequisite such as Events & Alignment remains incomplete;
- readiness remains advisory: foundation-QC pending does not newly disable expert controls, and no scientific analysis is auto-run or interpreted;
- readiness reuses the modules' established signal/capability helpers rather than introducing a second raw-column inference system;
- Events & Alignment cross-module readiness uses shared project/capability state rather than attempting to read another Shiny module's namespaced inputs; TTL-capable datasets can be identified as ready through the normal bundled/default path, while no-TTL datasets explicitly point to an external event log as the alternative;
- module readiness is attached through separate sibling Shiny modules so scientific module sessions and namespaces remain unchanged;
- the session summary exposes first-session readiness as a percentage;
- browser regression tests navigate by stable Shiny `data-value` module identifiers rather than mutable display labels;
- grouped Analyze / Integrate navigation and the EDA → QC → analysis → alignment → multimodal prerequisite progression are covered through the same stable E2E contract;
- remaining work: deeper contextual interpretation/help examples where they preserve the measurement guardrails.

## Phase 3 — project management

Status: **project identity, restore integrity, saved/dirty state, readable provenance timeline and privacy-safe recent history delivered**

- first-class project name and project metadata;
- project names persist in privacy-preserving project recipes, manifests, reports and report bundles;
- exact SHA-256 source-resource fingerprint validation remains mandatory on restore;
- the sidebar provides a direct Save / reopen / report action;
- Reporting exposes the restored project identity and suggests a project-derived recipe filename;
- project recipes expose explicit `Unsaved`, `Saved`, and `Unsaved changes` state;
- a successful recipe download records the current metadata checkpoint through the normal Shiny websocket event path, while the download handler remains pure file generation;
- any later project-state mutation marks that checkpoint dirty;
- replacing the dataset clears the prior save checkpoint;
- an exact-fingerprint recipe restore establishes the restored metadata as the current saved checkpoint;
- stale report artifacts are invalidated after report-relevant project changes rather than being served with outdated project identity;
- Reporting exposes a researcher-readable metadata-only Timeline derived from the existing provenance log;
- timeline entries group actions into Project, Quality, Analyze, Integrate, Model and Report stages and use human-facing action/detail labels;
- the timeline intentionally does not repeat source filenames, raw samples or recorded parameter payloads; the original full provenance table remains available unchanged for auditability;
- raw biometric rows and cached analysis tables remain outside project recipes;
- local/private Reporting now offers an **opt-in** “Remember this project” choice at recipe-save time; it is off by default and does not alter the existing Saved/dirty lifecycle;
- the recent-project index stores only project name, save timestamp, full dataset fingerprint, row/column counts, analysis/annotation counts and the suggested recipe filename;
- source filenames/paths, directory paths, column names, annotation content, provenance payloads, analysis parameters/parameter keys, cached result tables, raw biometric rows and credentials are explicitly excluded;
- recent entries are strict-schema validated, deduplicated by project name plus dataset fingerprint, bounded to 12 entries and a 256 KB file, and written through an atomic local replace with restrictive permissions where supported;
- the researcher-facing recent-project table shows only a shortened fingerprint and whether the current loaded dataset matches; recent history remains a locator rather than a restore source;
- reopening still requires explicit source dataset and project-recipe selection and the existing exact fingerprint gate;
- local users can clear the metadata index without changing the in-memory project or recipe Saved state;
- public-demo markup contains no recent-project opt-in/history controls, while the persistence service independently rejects public-demo disk access;
- browser validation uses a process-specific temporary recent-project store so tests cannot modify a developer's real local history.

## Phase 4 — examples and presets

Status: **guided starts, documented analysis presets, teaching routes and an end-to-end first-session browser contract delivered**

- bundled synthetic multimodal walkthrough;
- bundled synthetic eye-tracking walkthrough;
- bundled synthetic EDA/cardiovascular walkthrough;
- guided starts load synthetic data, run foundation QC, record provenance and open the relevant analysis family;
- Home exposes four non-executing teaching narratives: physiology foundations, eye-tracking foundations, event-linked multimodal workflow, and modelling;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment, Multimodal and Statistics/Modelling expose researcher-facing preset guidance documenting the current Guided-mode baseline, prerequisites, checks before inference, interpretation guardrails and next step;
- preset guidance is attached at the Studio package boundary and does not modify scientific module implementation, mutate controls, run analyses, fit models or create psychological interpretations;
- EDA guidance documents the existing 31-sample tonic window, automatic SCR threshold and 10-sample minimum peak distance;
- cardiac guidance documents the existing 40–180 bpm bounds, 0.30 RR rejection tolerance, 300–2000 ms IBI limits and 500 ms maximum jump;
- pupil guidance documents the existing conservative default of blink-gap detection without automatic interpolation, smoothing, baseline correction or event summaries;
- gaze guidance documents screen-bound filtering, event detection, 100 ms minimum fixation, 10 ms minimum saccade and 100 ms maximum event gap as the current Guided starting point;
- event-alignment and multimodal guidance document their existing event/baseline/summary windows and require event-clock review before integration;
- the Model guidance distinguishes auditable model-data preparation from model fitting;
- the cluster-permutation teaching preset explicitly preserves the validated two-condition, within-subject, one-dimensional time-course boundary, package-native design diagnostics, 1000-permutation Guided starting point and descriptive interpretation of cluster boundaries;
- Chromium coverage verifies the Home teaching routes, EDA and modelling preset cards, matching live Guided controls, and that merely viewing the guidance leaves the analysis count at zero;
- a dedicated first-session golden-path Chromium contract now follows the actual physiology journey from Home teaching context through the guided synthetic start, automatic foundation QC, EDA/SCR, guided Continue to PPG/HR/HRV, Reporting, report build, 3/3 guided completion, Timeline review, recipe save and visible dirty-state transition after a project-name edit;
- the first-session contract uses the same live controls and stable navigation identifiers as the product, does not add a parallel tutorial engine, and passed on Python 3.11 and 3.14;
- remaining work: human subjective usability review, richer teaching/demo examples and optional one-click reproducibility conveniences only where they reuse the existing scientific/reporting contracts rather than create a second analysis engine.

## Phase 5 — errors, diagnostics and supportability

Status: **structured remediation, production-browser evidence and clean Windows installed-launch diagnostics delivered**

- a privacy-safe Studio Doctor checks the Shiny dependency, packaged application/CSS assets, runtime mode and loopback binding;
- `gpbiometricspy-studio-doctor` provides concise human-readable diagnostics;
- `gpbiometricspy-studio-doctor --json` provides machine-readable support output;
- diagnostics do not inspect raw biometric samples or transmit support information;
- installed wheel/sdist production-browser failures preserve JUnit and Studio server diagnostics for both supported CI interpreters;
- clean Windows CI creates a fresh isolated virtual environment, installs Studio non-editably, then verifies imports from outside the repository so the checkout cannot mask packaging defects;
- Windows CI exercises Studio Doctor plus both the installed `gpbiometricspy-studio.exe` launcher and the PATH-independent `python -m studio.cli` launch path on Python 3.11 and 3.14;
- installed upload retries match substantive missing-resource conditions rather than presentation punctuation for the main Gazepoint upload, external event log and target stream;
- the external-event replay retry matcher is case-insensitive and uses resource-specific message fragments rather than exact complete status strings;
- all existing external-event and target-stream replay identity checks, resource-fingerprint failures, pair/event counts, path non-disclosure assertions and exact-resource replay assertions remain unchanged;
- a shared researcher-facing presentation taxonomy now classifies caught failures as input, prerequisite, identity, external-resource, analysis or unknown and assigns stable `GP-STUDIO-*` support codes plus a concrete next action;
- app-level and module-level caught failures use the same formatter without changing or swallowing scientific backend exceptions;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment, Multimodal, QC, Annotation, Statistics/Modelling and Reporting catch boundaries now expose consistent recovery guidance;
- local/private Studio retains bounded diagnostic detail alongside the stable recovery code;
- public-demo Studio suppresses caught exception detail and exposes only the operation prefix, stable support code and safe recovery guidance;
- deferred QC diagnostic strings and caught plot-rendering exceptions also pass through the sanitizer before being shown to the researcher;
- project-recipe validation and restore continue to fail closed on fingerprint/identity mismatches and explicitly instruct researchers not to bypass fingerprint validation;
- classifier precedence distinguishes genuine selection/numeric validation from incidental parameter names embedded in internal diagnostic payloads;
- Chromium regression coverage deliberately triggers a public-demo project-name validation failure and verifies that the `GP-STUDIO-INPUT` recovery code is shown while the underlying exception detail remains hidden;
- public-demo error sanitization remains fail-closed at both the Shiny application boundary and the manual-catch presentation layer;
- remaining work: optional local/private technical-detail affordances and broader support documentation only where they improve recovery without exposing research data.

## Phase 6 — desktop-style local experience

Status: **browser-backed local launcher and clean Windows installed-launch certification delivered as the intermediate product surface**

- Shiny for Python remains the single application engine;
- `gpbiometricspy-studio-desktop` chooses an available loopback port and opens Studio automatically;
- `--no-browser` supports manual/browser-managed startup and troubleshooting;
- clean Windows CI verifies installed launch behavior on Python 3.11 and 3.14 from outside the repository;
- the PATH-independent `python -m studio.cli` route is now an executable CI contract rather than documentation-only guidance;
- next packaging evaluation: PyInstaller/Nuitka and, only if justified, a lightweight local webview;
- a native-window wrapper remains packaging rather than a scientific-runtime rewrite;
- signed installers wait until reproducible build/update policies are defined.

## Phase 7 — hosted deployment

Status: **deployment boundary documented; production hosting remains future work**

### Public demonstration

- synthetic-only;
- no participant-data upload controls;
- sanitized error details;
- clear demo/privacy boundary;
- representative guided workflows;
- production health checks, resource limits and browser regression tests remain release/deployment gates.

### Authenticated/private research deployment

- authentication and authorization are deployment-layer responsibilities, not implicit Studio features;
- storage, retention, encryption, logging/audit, upload limits, secrets and disaster recovery must be defined before research-data upload is enabled;
- the documentation explicitly warns against presenting an anonymous public deployment as a participant-data service.

See [Studio deployment and support](studio-deployment.md) for the current operational boundary.

## Current validation checkpoint

The current certified product-code checkpoint is:

```text
299e3beb0a0545ed59270bbdff2359454a77582e
```

At that exact head, the complete pull-request workflow set passed:

- `tests` run #435;
- `studio` run #220 on Python 3.11 and 3.14;
- `studio-e2e` run #191, Chromium on Python 3.11 and 3.14;
- `studio-production` run #192: Linux Python 3.11 and 3.14 installed wheel/source-distribution Chromium replay plus synthetic runtime smoke, and clean Windows local-install/Doctor/launch smoke on Python 3.11 and 3.14;
- `branch-coverage` run #233;
- `deep-parity` run #424;
- `interoperability` run #423;
- `docs` run #205;
- `CodeQL` run #426.

The candidate first exposed a deterministic test-contract error in the newly added first-session journey: the EDA Guided-mode control is a Shiny radio-group container, so the first version incorrectly asserted a value on the group node. The correction changed only that E2E selector to target the existing `input[value="guided"]`, matching the already-certified analysis-preset test. No application or scientific implementation changed, and the corrected exact head passed the complete nine-family matrix.

The checkpoint additionally certifies:

- a cohesive first-session Chromium journey from Home teaching routes through physiology guided start, automatic foundation QC, EDA/SCR, PPG/HR/HRV, Reporting, report build, 3/3 completion, project Timeline, recipe Saved state and `Unsaved changes` after a metadata edit;
- the first-session journey on source Chromium for Python 3.11 and 3.14;
- stepwise guided walkthrough continuation and dynamic Continue-label updates;
- dataset-boundary retirement of stale guided state;
- channel-aware Home recommendations based on existing validated channel/capability state, including fail-closed behavior for malformed validation tables;
- reactive module-level readiness guidance for EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment and Multimodal;
- advisory QC-pending guidance that preserves expert controls instead of silently changing scientific access rules;
- Shiny-safe sibling readiness namespaces that do not modify the scientific modules' own sessions;
- shared-state Event Alignment readiness that avoids cross-module input leakage and distinguishes TTL/default-path readiness from the external-event-log alternative;
- browser-certified progression from EDA QC pending → ready → completed, Events & Alignment ready on the bundled TTL-capable demo, and Multimodal blocked until alignment is stored;
- project identity propagation through recipes, manifests, reports and bundles;
- report-cache invalidation after report-relevant project changes;
- explicit recipe `Unsaved` → `Saved` → `Unsaved changes` lifecycle in Chromium;
- exact-fingerprint restore returning the restored project to a saved metadata checkpoint;
- a readable metadata-only project timeline while preserving the original provenance audit table;
- privacy-preserving recipes that exclude raw biometric rows and cached analysis-result tables;
- installed-browser diagnostics and semantic upload-race retry guards across main, event-log and target-stream uploads;
- installed external-event, target-stream and dual-resource replay identity checks on both supported CI interpreters;
- stable researcher-facing `GP-STUDIO-*` error/remediation codes across the major Studio catch boundaries;
- public-demo caught-exception detail suppression in both unit and Chromium browser contracts;
- local/private bounded technical detail retained for troubleshooting;
- fail-closed recipe/resource identity guidance that never recommends bypassing fingerprint verification;
- opt-in local recent-project metadata recording on the existing recipe-save checkpoint without changing Saved/dirty semantics;
- strict recent-history field minimization, bounds, deduplication, atomic persistence and clear-history behavior;
- browser-verified current-dataset fingerprint matching while source identity, full fingerprints and research-detail fields remain absent from the recent-project table;
- complete public-demo exclusion of recent-project controls plus server-side public-demo disk-access rejection;
- installed wheel/sdist operation with the recent-project service/module present on both supported CI interpreters;
- immutable, presentation-only analysis-preset definitions for EDA/SCR, cardiac, pupil, gaze, event alignment, multimodal, model preparation and cluster permutation;
- Home teaching routes for physiology, eye tracking, event-linked multimodal work and modelling;
- browser-verified agreement between documented Guided defaults and the corresponding live EDA/model/cluster controls;
- browser-verified non-execution: navigating through preset guidance does not run an analysis or increment the project analysis count;
- preservation of the validated cluster-permutation design boundary and measurement/interpretation guardrails;
- a clean Windows virtual-environment install on Python 3.11 and 3.14 with import resolution verified from outside the repository checkout;
- successful Windows Studio Doctor execution through the installed diagnostic entry point and module route;
- successful loopback startup through both `gpbiometricspy-studio.exe` and `python -m studio.cli` on both Windows interpreters.

Further product-polish commits must pass the same normal pull-request gates before they supersede this checkpoint.

## 0.1.6 release criteria for Studio

Before calling Studio `0.1.6` product-polished, require at minimum:

- all existing scientific package gates remain green;
- Studio smoke, Chromium E2E and production/distribution gates remain green;
- no regression in public synthetic fail-closed behavior;
- clean Windows install → Studio Doctor → launch remains CI-green on Python 3.11 and 3.14;
- the researcher-facing launch → guided demo → QC → analysis → report/save path remains browser-certified on Python 3.11 and 3.14;
- the full onboarding path is still tested by a human for comprehension, friction and visual usability rather than scientific correctness alone;
- keyboard and narrow-viewport browser checks remain green;
- project/replay fingerprint guards remain fail-closed;
- documentation reflects the actual installed behavior;
- the 0.1.5 backup/release boundary remains untouched.

## Current human-testing target

The automated browser contract now covers the central researcher-facing physiology first session after launch. Human validation should therefore focus on **comprehension, visual hierarchy, perceived friction and packaging/install experience**, while still replaying the complete path:

```text
install
  → run Studio Doctor
  → launch
  → review the Home teaching routes
  → choose a guided synthetic walkthrough or load the synthetic demo only
  → inspect module readiness before QC
  → run foundation QC
  → see affected modules become ready
  → review the teaching preset and its Guided baseline before analysis
  → run a signal analysis and see its readiness state become complete
  → follow the guided Continue action into the next signal family
  → complete the guided route and build the report
  → verify a safe `GP-STUDIO-*` recovery message for an invalid action
  → Save / reopen / report
  → review the readable project Timeline and full Provenance audit table
  → export a privacy-preserving project recipe
  → verify Saved / Unsaved changes state after project edits
  → optionally remember the project in the local metadata-only recent-project list
  → verify the current dataset match indicator and clear recent history independently
  → restore against the exact source fingerprint
```

The next product work should prioritize **human subjective first-session validation and packaging evaluation**, with PyInstaller/Nuitka or a lightweight webview treated as optional downstream packaging experiments. Any additional one-click convenience must remain constrained to existing reporting/replay contracts and the same privacy/fingerprint guardrails.