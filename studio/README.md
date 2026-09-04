# gpbiometricspy Studio

`gpbiometricspy Studio` is the first-party Shiny for Python application layer for `gpbiometricspy`.
The scientific package remains the computational engine; Studio calls the public package API instead of reimplementing scientific algorithms.

## Current MVP

- load the bundled, fully synthetic kiosk demonstration dataset;
- upload one Gazepoint CSV/TXT file (100 MB MVP limit);
- validate the imported schema with `validate_gazepoint_biometrics()`;
- inspect detected/active biometric channels;
- run missingness and signal-activity QC with public package functions;
- render the package-native signal-activity plot;
- retain a per-session provenance trail;
- preserve the package interpretation guardrails in the UI.

## Positron setup

From the repository root, create or activate a project-local Python environment and install Studio:

```bash
python -m pip install -e ".[studio]"
```

Then open `studio/app.py` in Positron and use **Run Shiny App**, or run from the terminal:

```bash
shiny run --reload studio/app.py
```

The app runs locally by default. Uploaded files use Shiny's temporary upload location and are imported by `gpbiometricspy`; Studio does not intentionally persist raw uploads.

## Architecture rule

Scientific transformations, QC, models, and scientific plots belong in `src/gpbiometricspy/`. Interactive orchestration, session state, presentation, and workflow navigation belong in `studio/`.

The Studio test suite is intentionally separate from the package's frozen 100% scientific-core coverage gate.
