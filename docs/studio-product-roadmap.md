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
- Events & Alignment cross-module readiness uses shared project state rather than another Shiny module's namespaced inputs;
- browser regression tests navigate by stable Shiny `data-value` module identifiers rather than mutable display labels.

## Phase 3 — project management

Status: **project identity, restore integrity, saved/dirty state, readable provenance timeline and privacy-safe recent-project convenience delivered**

- first-class project name and project metadata;
- project names persist in privacy-preserving project recipes, manifests, reports and report bundles;
- exact SHA-256 source-resource fingerprint validation remains mandatory on restore;
- project recipes expose explicit `Unsaved`, `Saved`, and `Unsaved changes` state;
- any later project-state mutation marks that checkpoint dirty;
- replacing the dataset clears the prior save checkpoint;
- an exact-fingerprint recipe restore establishes the restored metadata as the current saved checkpoint;
- Reporting exposes a researcher-readable metadata-only Timeline derived from the existing provenance log;
- raw biometric rows and cached analysis tables remain outside project recipes;
- local/private Reporting provides an opt-in, default-off recent-project locator tied to successful recipe saves;
- the recent-project index stores only project name, save timestamp, dataset SHA-256, row/column counts, analysis/annotation counts and suggested recipe filename;
- source filenames/paths, column names, raw rows, annotation content, provenance payloads, parameters, cached results and credentials are excluded;
- public-demo markup contains no recent-project controls and the service rejects public-demo disk access;
- recent history is only a locator: reopen still requires explicit source data + recipe and exact fingerprint validation.

## Phase 4 — examples and presets

Status: **guided-start foundation delivered; documented analysis presets and teaching routes staged for certification**

- bundled synthetic multimodal walkthrough;
- bundled synthetic eye-tracking walkthrough;
- bundled synthetic EDA/cardiovascular walkthrough;
- guided starts load synthetic data, run foundation QC, record provenance and open the relevant analysis family;
- Home now stages four non-executing teaching narratives: physiology foundations, eye-tracking foundations, event-linked multimodal workflow, and modelling;
- EDA/SCR, PPG/HR/HRV, Pupil, Gaze/AOI, Events & Alignment, Multimodal and Statistics/Modelling stage researcher-facing preset guidance documenting the current Guided-mode baseline, prerequisites, checks before inference, interpretation guardrails and next step;
- preset guidance is attached at the Studio package boundary and does not modify scientific module implementation, mutate controls, run analyses, fit models or create psychological interpretations;
- the cluster-permutation teaching preset explicitly preserves the validated two-condition, within-subject, one-dimensional time-course boundary and package-native design diagnostics;
- Chromium coverage is staged to verify that preset cards match live Guided controls while merely viewing them leaves the project analysis count unchanged;
- remaining work after certification: richer teaching/demo narratives, interpretation examples that preserve measurement guardrails, and one-click reproducibility bundles where scientifically justified.

## Phase 5 — errors, diagnostics and supportability

Status: **structured remediation taxonomy, semantic retry hardening and production-browser evidence delivered**

- a privacy-safe Studio Doctor checks the Shiny dependency, packaged application/CSS assets, runtime mode and loopback binding;
- `gpbiometricspy-studio-doctor` provides concise human-readable diagnostics;
- `gpbiometricspy-studio-doctor --json` provides machine-readable support output;
- diagnostics do not inspect raw biometric samples or transmit support information;
- installed wheel/sdist production-browser failures preserve JUnit and Studio server diagnostics for both supported CI interpreters;
- installed upload retries match substantive missing-resource conditions rather than presentation punctuation;
- a shared researcher-facing presentation taxonomy classifies caught failures as input, prerequisite, identity, external-resource, analysis or unknown and assigns stable `GP-STUDIO-*` support codes plus a concrete next action;
- local/private Studio retains bounded diagnostic detail alongside the stable recovery code;
- public-demo Studio suppresses caught exception detail and exposes only the operation prefix, stable support code and safe recovery guidance;
- project-recipe validation and restore continue to fail closed on fingerprint/identity mismatches and explicitly instruct researchers not to bypass fingerprint validation.

## Phase 6 — desktop-style local experience

Status: **browser-backed local launcher delivered as the intermediate product surface**

- Shiny for Python remains the single application engine;
- `gpbiometricspy-studio-desktop` chooses an available loopback port and opens Studio automatically;
- `--no-browser` supports manual/browser-managed startup and troubleshooting;
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

The current certified product-code checkpoint remains:

```text
3fee5aed2c263846b4daac0e69cc07253754747c
```

At that exact head, the complete pull-request workflow set passed:

- `tests` run #428;
- `studio` run #213 on Python 3.11 and 3.14;
- `studio-e2e` run #184, Chromium on Python 3.11 and 3.14;
- `studio-production` run #185 on Python 3.11 and 3.14, including installed wheel and source-distribution Chromium replay plus synthetic runtime smoke;
- `branch-coverage` run #226;
- `deep-parity` run #417;
- `interoperability` run #416;
- `docs` run #198;
- `CodeQL` run #419.

The preset/teaching tranche is staged on a separate branch and must pass the same nine normal pull-request gates before it supersedes this certified checkpoint.

## 0.1.6 release criteria for Studio

Before calling Studio `0.1.6` product-polished, require at minimum:

- all existing scientific package gates remain green;
- Studio smoke, Chromium E2E and production/distribution gates remain green;
- no regression in public synthetic fail-closed behavior;
- Windows local launch instructions tested on a clean environment;
- onboarding path tested by a human from install → guided demo → QC → analysis → report;
- keyboard and narrow-viewport browser checks remain green;
- project/replay fingerprint guards remain fail-closed;
- documentation reflects the actual installed behavior;
- the 0.1.5 backup/release boundary remains untouched.
