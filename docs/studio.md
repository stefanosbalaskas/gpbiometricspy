# gpbiometricspy Studio

**gpbiometricspy Studio** is the Shiny for Python application layer for the `gpbiometricspy` scientific package. It exposes the package's quality-control, annotation, physiology, eye-tracking, alignment, multimodal, modelling, and reporting workflows through one stateful research interface.

The architectural rule is strict: **Studio calls public `gpbiometricspy` functions; it does not reimplement the scientific package.** The frozen 406-function R-parity surface therefore remains independent from the application layer.

## Two runtime boundaries

| Runtime | Entry point | External files | Intended use |
|---|---|---:|---|
| Full Studio | `gpbiometricspy-studio` / `studio/app.py` | Yes | Local Positron use or an authenticated/private deployment with research data |
| Public demonstration | `gpbiometricspy-studio-public` / repository-root `app.py` | **No** | Anonymous demonstration with the bundled synthetic kiosk dataset only |

The public boundary is fail-closed. It removes file-input affordances **and** rejects server-side attempts to feed external biometric datasets, AOI files, event logs, secondary streams, or project recipes. Error details are sanitized in this mode.

!!! warning "Do not submit participant data to the public demo"
    The public deployment is intentionally synthetic-only. Use the full Studio locally or behind an authenticated/private deployment when working with research data.

## Install and launch

The Studio application is included in the `0.1.3.dev0` development distribution and requires the optional Shiny dependencies.

=== "Installed package / editable checkout"

    ```bash
    python -m pip install -e ".[studio]"
    gpbiometricspy-studio
    ```

=== "Public synthetic boundary"

    ```bash
    python -m pip install -e ".[studio]"
    gpbiometricspy-studio-public
    ```

=== "Direct Shiny development"

    ```bash
    shiny run --reload studio/app.py
    ```

In Positron, open `studio/app.py` and use **Run Shiny App** for the full local application.

The launchers pass additional arguments through to `shiny run`, so normal Shiny CLI controls remain available. For example:

```bash
gpbiometricspy-studio --host 127.0.0.1 --port 8765
```

## Application map

Studio currently provides the following primary workflows:

1. **Home / project intake** — synthetic demo or research-data import, schema inspection, channel detection, missingness, validation issues, and foundation signal-activity QC.
2. **Quality Control** — timing resets/segments, EDA/GSR quality, HR/IBI quality, gaze validation, and package-native diagnostics.
3. **Annotation** — plot click/brush annotations, manual EDA peaks, artifact intervals, notes, provenance, and CSV export.
4. **EDA / SCR Analysis** — guided/expert decomposition, response detection, summaries, package-native plots, exports, and reproducible Python code.
5. **PPG / HR / HRV Analysis** — waveform/interval QC, HRV summaries, diagnostics, optional scientific-backend paths, and reproducibility outputs.
6. **Pupil Analysis** — pupil quality/preprocessing and analysis workflows with explicit interpretation guardrails.
7. **Gaze / Fixation / AOI Analysis** — gaze/fixation/AOI workflows, including AOI-definition support in the full Studio.
8. **Events & Alignment** — event-log and secondary-stream alignment workflows with provenance.
9. **Multimodal Analysis** — aligned cross-signal summaries and diagnostics.
10. **Statistics & Modelling** — package-backed statistical/design workflows and guardrails.
11. **Reporting & Reproducibility** — privacy-preserving project recipes, reporting artifacts, provenance summaries, fingerprints, and downloads.

## Guided versus expert operation

Where a workflow exposes both modes, **Guided** selects conservative package defaults and keeps the number of decisions small. **Expert** exposes additional parameters needed for sensitivity analysis or domain-specific protocols.

Neither mode changes the interpretation policy: physiological and eye-tracking measurements do not directly establish emotion, stress, trust, preference, cognition, health status, or diagnosis.

## Reproducibility model

Studio holds project state in the running Shiny session. Dataset loading resets downstream analyses as appropriate; analyses and annotations append provenance operations. Reporting/project-recipe outputs intentionally exclude raw participant rows and cached analysis-result tables.

For a reproducible workflow, retain:

- the original data outside the repository;
- the exact `gpbiometricspy` version;
- exported Studio parameters/results as appropriate;
- the project recipe/fingerprint;
- generated Python reproduction scripts;
- any study-specific exclusion, artifact, or interpretation decisions.

## Deployment

The repository root is prepared as a public Connect-style content root:

```text
app.py
requirements.txt
studio/
src/gpbiometricspy/
```

`app.py` imports the synthetic-only public boundary. The full `studio/app.py` should be deployed only in an environment whose authentication, access-control, storage, logging, retention, and data-governance configuration is suitable for the research data being processed.

See **[Deployment and production hardening](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/DEPLOYMENT.md)** for Posit Connect Cloud, self-hosted Posit Connect/`rsconnect`, runtime diagnostics, security boundaries, and accessibility notes.

## Validation

Studio has three independent CI layers on Python 3.11 and 3.14:

- **Studio smoke** — install, Ruff, compilation, and Studio unit/service tests;
- **Chromium E2E** — real browser loading, synthetic workflow/reporting interactions, public upload suppression, keyboard skip-link behavior, and narrow-viewport overflow checks;
- **Production smoke** — deployment-style dependency reconstruction, fail-closed runtime policy, installed-distribution content checks, source-distribution deployment-asset checks, and synthetic runtime metrics.

The scientific package continues to run its separate Ubuntu/Windows/macOS × Python 3.11–3.14 matrix, deep R↔Python parity workflow, optional-backend interoperability tests, and CodeQL analysis.

Automated accessibility checks are regression guards, **not a claim of formal WCAG certification**.
