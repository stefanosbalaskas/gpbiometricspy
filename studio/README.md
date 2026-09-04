# gpbiometricspy Studio

`gpbiometricspy Studio` is the first-party Shiny for Python application layer for `gpbiometricspy`.
The scientific package remains the computational engine; Studio calls the public package API instead of reimplementing scientific algorithms.

## Current application

Studio now provides four workflow areas:

- **Home** — bundled synthetic demo or single CSV/TXT intake, schema validation, detected channels, preview, foundation missingness/activity QC, and package-native signal-activity plotting;
- **Quality Control** — configurable time-reset/segment diagnostics, EDA and heart-rate quality audits, gaze validation, group-level gaze diagnostics, and package-native QC plots;
- **Annotation** — native Python EDA review with plot-click manual peaks, brushed artifact intervals, notes, editable session annotation state, and CSV export;
- **Reproducibility** — package version, dataset/session summary, operation provenance, and interpretation guardrails.

The Studio application is local-first. Uploaded files use Shiny's temporary upload location and are imported by `gpbiometricspy`; Studio does not intentionally persist raw uploads.

## Positron setup

From the repository root, create or activate a project-local Python environment and install Studio:

```bash
python -m pip install -e ".[studio]"
```

Then open `studio/app.py` in Positron and use **Run Shiny App**, or run from the terminal:

```bash
shiny run --reload studio/app.py
```

## Interaction model

Foundation QC is available from the global project sidebar. The **Quality Control** page exposes thresholds and timing parameters explicitly and uses a Shiny task button for the deeper QC pass.

On **Annotation**:

1. select an EDA signal and time column;
2. click the plot and choose **Add clicked peak** to record a manual peak;
3. brush an x-axis interval and choose **Add brushed artifact interval** to record an artifact;
4. add optional notes, remove rows, clear session annotations, or download the annotation table as CSV.

Annotations are expert-review metadata; they do not replace automated scoring and do not infer emotion, stress, cognition, trust, preference, or diagnosis.

## Architecture rule

Scientific transformations, QC, models, and scientific plots belong in `src/gpbiometricspy/`. Interactive orchestration, session state, presentation, modules, and workflow navigation belong in `studio/`.

Reusable Shiny modules live under `studio/modules/`. The Studio test suite remains separate from the package's frozen scientific-core coverage gate.
