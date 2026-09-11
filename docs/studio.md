# gpbiometricspy Studio

**gpbiometricspy Studio** is the visual research application built on top of the `gpbiometricspy` scientific package. It is designed for researchers who want a guided, stateful workflow without giving up the reproducibility and provenance of the Python API.

The architectural rule remains strict: **Studio calls public `gpbiometricspy` functions; it does not reimplement the scientific package.** The frozen 406-function R-parity surface therefore remains independent from the application layer.

## What Studio is for

Studio organizes the research process into six practical stages:

1. **Project** — load a dataset, inspect schema and channels, and establish the analysis context.
2. **Quality** — run foundation and signal-specific QC before interpreting results.
3. **Analyze** — work with EDA/SCR, PPG/HRV, pupil, gaze, fixation and AOIs.
4. **Align** — connect events, TTL markers, AOIs and secondary streams.
5. **Model** — prepare summaries and run guarded statistical/modelling workflows.
6. **Report** — export results, provenance, project recipes and reproducible replay code.

## Full Studio versus public demonstration

| Runtime | Entry point | External files | Intended use |
|---|---|---:|---|
| Full Studio | `gpbiometricspy-studio` / `python -m studio.cli` | Yes | Local use or authenticated/private deployment with research data |
| Public demonstration | `gpbiometricspy-studio-public` | **No** | Anonymous demonstration using the bundled synthetic kiosk dataset only |

The public boundary is fail-closed. It removes file-input affordances **and** rejects server-side attempts to feed external biometric datasets, AOI files, event logs, secondary streams, or project recipes. Error details are sanitized in this mode.

!!! warning "Do not submit participant data to the public demo"
    Use the full Studio locally or behind an authenticated/private deployment when working with research data.

## Install the stable application

Studio is included in the stable `0.1.5` distribution and requires the optional Shiny dependencies.

```bash
python -m pip install "gpbiometricspy[studio]==0.1.5"
```

Verify the installed package:

```bash
python -c "import gpbiometricspy; print(gpbiometricspy.__version__)"
```

Expected output:

```text
0.1.5
```

## Launch Studio

### Normal installed launcher

```bash
gpbiometricspy-studio
```

### PATH-independent launcher

This is the most robust launch form when Python's Scripts directory is not on your shell `PATH`:

```bash
python -m studio.cli --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

### Windows Store Python note

Microsoft Store Python installations may install console scripts under a user-local Scripts directory that PowerShell does not automatically search. In that case, installation can succeed while `gpbiometricspy-studio` is reported as “not recognized”.

Use the PATH-independent launcher above instead of changing your system configuration just to test Studio.

A clean virtual environment can also be created with the Python executable itself:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "gpbiometricspy[studio]==0.1.5"
.\.venv\Scripts\python.exe -m studio.cli --host 127.0.0.1 --port 8765
```

No activation step is required when you call the environment's Python executable directly.

### Development checkout

```bash
git clone https://github.com/stefanosbalaskas/gpbiometricspy.git
cd gpbiometricspy
python -m pip install -e ".[studio]"
python -m studio.cli --host 127.0.0.1 --port 8765
```

In Positron, open `studio/app.py` and use **Run Shiny App**.

## Your first Studio session

For the first human test, do **not** start with participant data. Use the bundled synthetic kiosk dataset.

### 1. Load the demo

On the Home screen, choose **Load synthetic demo**.

You should see:

- a dataset name;
- row and column counts;
- detected biometric channels;
- a data preview;
- validation information.

### 2. Run foundation QC

Choose **Run foundation QC**.

This establishes the first quality-control layer before signal-specific analysis. The Home screen then exposes signal-activity diagnostics and directs you toward the deeper Quality Control workflow.

### 3. Walk through the analysis modules

Recommended order for the first test:

1. Quality Control
2. EDA / SCR Analysis
3. PPG / HR / HRV Analysis
4. Pupil Analysis
5. Gaze / Fixation / AOI Analysis
6. Events & Alignment
7. Multimodal Analysis
8. Statistics & Modelling
9. Reporting & Reproducibility

Annotation can be used whenever manual peaks, artifact intervals, notes, or provenance decisions are needed.

### 4. Test reproducibility

In Reporting & Reproducibility, inspect the available project-recipe, provenance, fingerprint and replay outputs. Studio intentionally does not hide the assumptions needed to reproduce an analysis.

## Application map

| Area | What it does |
|---|---|
| Home / project intake | Demo or research-data import, schema inspection, channel detection, missingness and foundation QC |
| Quality Control | Timing resets/segments, EDA/GSR quality, HR/IBI quality, gaze validation and package-native diagnostics |
| Annotation | Manual EDA peaks, artifact intervals, notes, provenance and CSV export |
| EDA / SCR Analysis | Guided/expert decomposition, response detection, summaries, plots, exports and reproducible Python code |
| PPG / HR / HRV Analysis | Waveform/interval QC, HRV summaries, diagnostics, optional scientific backends and reproducibility outputs |
| Pupil Analysis | Pupil QC, preprocessing and analysis with explicit interpretation guardrails |
| Gaze / Fixation / AOI Analysis | Gaze/fixation/AOI workflows and AOI-definition support in the full Studio |
| Events & Alignment | Event-log and secondary-stream alignment with provenance |
| Multimodal Analysis | Aligned cross-signal summaries and diagnostics |
| Statistics & Modelling | Package-backed statistical/design workflows and guardrails |
| Reporting & Reproducibility | Project recipes, provenance, fingerprints, reports, downloads and replay code |

## Guided versus expert operation

Where a workflow exposes both modes, **Guided** selects conservative package defaults and minimizes the number of decisions required to get started. **Expert** exposes additional parameters for sensitivity analysis or domain-specific protocols.

Neither mode changes the interpretation policy: physiological and eye-tracking measurements do not directly establish emotion, stress, trust, preference, cognition, health status, or diagnosis.

## Project and reproducibility model

Studio holds project state in the running Shiny session. Loading a new dataset resets downstream analyses as appropriate; analyses and annotations append provenance operations.

For a defensible project, retain:

- the original data outside the repository;
- the exact `gpbiometricspy` version;
- exported Studio parameters/results as appropriate;
- the project recipe/fingerprint;
- generated Python reproduction scripts;
- study-specific exclusion, artifact and interpretation decisions.

Project recipes intentionally exclude raw participant rows and cached analysis-result tables.

## What to report during product testing

Human testing should focus on usability as well as correctness. Useful feedback includes:

- “I do not know what to click next.”
- “This label is too technical.”
- “I expected this result to appear somewhere else.”
- “The graph is too small or crowded.”
- “The error message does not tell me how to fix the problem.”
- “This workflow needs another option.”
- “I cannot tell whether QC has been completed.”
- “I need to save or reopen this project more easily.”

Screenshots and the exact status/error text are especially useful when reporting problems.

## Deployment

The repository root is prepared as a public Connect-style content root:

```text
app.py
requirements.txt
studio/
src/gpbiometricspy/
```

The repository-root `app.py` imports the synthetic-only public boundary. The full `studio/app.py` should be deployed only where authentication, access control, storage, logging, retention and data-governance controls are suitable for the research data being processed.

See [`DEPLOYMENT.md`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/DEPLOYMENT.md) for current production-hardening details.

## Product direction for 0.1.6

The `0.1.6` development line is moving Studio from a scientifically complete application toward a more polished standalone research product. Current priorities are:

- clearer onboarding and “next step” guidance;
- stronger information hierarchy and visual consistency;
- improved navigation across the analysis lifecycle;
- more actionable errors and empty states;
- easier project/session management;
- richer examples and guided presets;
- a smoother local launch experience, including desktop-style packaging options;
- a polished synthetic public demonstration and a documented authenticated/private deployment path.

Scientific methods remain package-backed throughout this work.

## Validation

Studio has independent validation layers on Python 3.11 and 3.14:

- **Studio smoke** — install, Ruff, compilation, and Studio unit/service tests;
- **Chromium E2E** — browser loading, synthetic workflow interactions, public upload suppression, accessibility and viewport checks;
- **Production smoke** — deployment-style dependency reconstruction, fail-closed runtime policy, installed-distribution checks, source-distribution deployment assets and synthetic runtime metrics;
- **Installed replay** — wheel/sdist replay paths for physiology, gaze/pupil, alignment, multimodal/modelling and cluster-permutation workflows with fingerprint guards.

The scientific package continues to run its separate platform/Python matrix, deep R↔Python parity, optional-backend interoperability, private real-data validation and CodeQL layers.

Automated accessibility checks are regression guards, not a claim of formal WCAG certification.

## Guided walkthroughs and project continuity

    Studio now offers guided synthetic starts for multimodal, eye-tracking and EDA/cardiovascular workflows. A guided start loads the bundled synthetic dataset, runs foundation QC, records the action in provenance and opens the relevant analysis family. It is a teaching/onboarding shortcut, not a different scientific engine.

    The top navigation is grouped into **Home → Quality → Analyze → Integrate → Model → Report** while the established module identifiers remain unchanged underneath.

    Project names persist in privacy-preserving project recipes. Use **Save / reopen / report** in the sidebar to move directly to the project recipe and reporting tools.

    For installation or startup problems, run:

    ```bash
    gpbiometricspy-studio-doctor
    ```

    See [Studio deployment and support](studio-deployment.md) for local, desktop-style, public-demo and authenticated/private deployment boundaries.
