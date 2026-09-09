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

Status: **in progress**

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

- reduce cognitive load from the large analysis navigation surface;
- add clearer workflow grouping while preserving stable module identifiers;
- expose channel-aware recommendations after dataset inspection;
- show which prerequisites are complete or missing for each analysis family;
- add contextual “why this matters” and “what to do next” help;
- make Guided versus Expert mode visually consistent across modules.

## Phase 3 — project management

- first-class project name and project metadata;
- explicit save/export project action;
- reopen project recipe with source-resource fingerprint validation;
- visible dirty/saved state;
- recent-project convenience for local desktop-style use without embedding raw research data in repository artifacts;
- clearer separation between raw source files, derived results, recipes and report bundles;
- project-level provenance timeline.

## Phase 4 — examples and presets

- guided synthetic walkthroughs for EDA/SCR, PPG/HRV, pupil/gaze/AOI and multimodal workflows;
- analysis presets tied to documented assumptions rather than opaque “magic” settings;
- example result interpretation that stays inside the package's conservative guardrails;
- reusable teaching/demo projects;
- downloadable reproducibility bundles.

## Phase 5 — errors, diagnostics and supportability

- consistent user-facing error taxonomy;
- concise primary message plus optional technical detail for local/private use;
- actionable remediation suggestions for missing channels, bad schemas, unavailable optional backends and fingerprint mismatches;
- runtime diagnostics page suitable for support requests;
- version/environment copy button;
- safer reset/new-project flow.

## Phase 6 — desktop-style local experience

Candidate path:

- retain Shiny for Python as the application engine;
- provide a launcher that starts the local server, chooses an available loopback port and opens the application automatically;
- evaluate packaging approaches such as PyInstaller/Nuitka plus a lightweight local webview only after installed-wheel behavior is stable;
- avoid introducing a second scientific runtime;
- sign/package desktop installers only after reproducible build and update policies are defined.

A browser-backed local launcher is acceptable as an intermediate product step; a native-window wrapper should be treated as packaging, not as a rewrite of the application.

## Phase 7 — hosted deployment

### Public demonstration

- synthetic-only;
- no participant-data upload controls;
- sanitized error details;
- clear demo banner and privacy boundary;
- representative guided workflows;
- production health checks and browser regression tests.

### Authenticated/private research deployment

- authentication and authorization;
- explicit storage and retention policy;
- logging/audit controls;
- upload-size and file-type controls;
- secrets/configuration management;
- backup and disaster-recovery policy;
- institution-appropriate data governance.

## 0.1.6 release criteria for Studio

Before calling Studio `0.1.6` product-polished, require at minimum:

- all existing scientific package gates remain green;
- Studio smoke, Chromium E2E and production/distribution gates remain green;
- no regression in public synthetic fail-closed behavior;
- Windows local launch instructions tested on a clean environment;
- onboarding path tested by a human from install → demo → QC → analysis → report;
- keyboard and narrow-viewport browser checks remain green;
- project/replay fingerprint guards remain fail-closed;
- documentation reflects the actual installed behavior;
- the 0.1.5 backup/release boundary remains untouched.

## Current human-testing target

The immediate target is the **first-session experience**:

```text
install
  → launch
  → load synthetic demo
  → understand project readiness
  → run foundation QC
  → choose a signal workflow
  → inspect a result
  → reach Reporting & Reproducibility
```

Usability findings from that path should drive the next tranche before desktop packaging or broader deployment work expands further.
