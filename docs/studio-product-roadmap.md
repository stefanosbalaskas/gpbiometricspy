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

Status: **core tranche delivered; contextual module-level guidance remains**

- top navigation is grouped as Home → Quality → Analyze → Integrate → Model → Report;
- established module identifiers remain unchanged underneath the grouped navigation;
- a workflow-progress table exposes required, ready, optional and completed stages;
- guided synthetic starts can open multimodal, eye-tracking or physiology workflows after foundation QC;
- the session summary exposes first-session readiness as a percentage;
- browser regression tests navigate by stable Shiny `data-value` module identifiers rather than mutable display labels;
- grouped Analyze / Integrate navigation is covered through the same stable E2E contract;
- remaining work: channel-aware recommendations, module-specific prerequisites and deeper contextual help.

## Phase 3 — project management

Status: **substantial foundation delivered**

- first-class project name and project metadata;
- project names persist in privacy-preserving project recipes and manifests;
- exact SHA-256 source-resource fingerprint validation remains mandatory on restore;
- the sidebar provides a direct Save / reopen / report action;
- Reporting exposes the restored project identity and suggests a project-derived recipe filename;
- raw biometric rows and cached analysis tables remain outside project recipes;
- remaining work: explicit dirty/saved state, local recent-project convenience and a richer project-level provenance timeline.

## Phase 4 — examples and presets

Status: **guided-start foundation delivered**

- bundled synthetic multimodal walkthrough;
- bundled synthetic eye-tracking walkthrough;
- bundled synthetic EDA/cardiovascular walkthrough;
- guided starts load synthetic data, run foundation QC, record provenance and open the relevant analysis family;
- remaining work: documented analysis presets, teaching/demo project narratives, interpretation examples and one-click reproducibility bundles.

## Phase 5 — errors, diagnostics and supportability

Status: **diagnostic foundation delivered**

- a privacy-safe Studio Doctor checks the Shiny dependency, packaged application/CSS assets, runtime mode and loopback binding;
- `gpbiometricspy-studio-doctor` provides concise human-readable diagnostics;
- `gpbiometricspy-studio-doctor --json` provides machine-readable support output;
- diagnostics do not inspect raw biometric samples or transmit support information;
- public-demo error sanitization remains fail-closed;
- remaining work: module-level remediation suggestions, a richer error taxonomy and optional local/private technical-detail disclosure.

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

The guided-product tranche was applied through fail-closed helpers that committed only after their focused validation succeeded. The navigation-contract helper additionally migrated the Chromium suite from mutable display-label clicks to stable Shiny module IDs and removed itself after validation.

The checkpoint therefore includes:

- Studio source compilation;
- focused product-services and Studio Doctor tests;
- reporting/reproducibility regression tests;
- desktop-launcher and CLI regression tests;
- production-hardening regression tests;
- `studio.app` import validation;
- strict MkDocs build;
- static validation of the migrated E2E sources with Ruff, Python compilation and helper import checks;
- zero stale label-based navigation calls after migration.

Full pull-request CI is required on the normal user-authored checkpoint above the helper-produced commit before the tranche is considered merge-ready.

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

## Current human-testing target

The immediate target is now the **guided first-session experience**:

```text
install
  → run Studio Doctor
  → launch
  → choose a guided synthetic walkthrough
  → see foundation QC complete
  → continue in the relevant analysis family
  → inspect a result
  → Save / reopen / report
  → export a privacy-preserving project recipe
```

Usability findings from that path should drive the remaining presets, project-state polish and packaging work before a non-development `0.1.6` release.
