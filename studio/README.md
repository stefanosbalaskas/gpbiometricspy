# gpbiometricspy Studio

`gpbiometricspy Studio` is the first-party Shiny for Python application layer for `gpbiometricspy`.
The scientific package remains the computational engine; Studio calls the public package API instead of reimplementing scientific algorithms.

## Current application

Studio now provides seven workflow areas:

- **Home** — bundled synthetic demo or single CSV/TXT intake, schema validation, detected channels, preview, foundation missingness/activity QC, and package-native signal-activity plotting;
- **Quality Control** — configurable time-reset/segment diagnostics, EDA and heart-rate quality audits, gaze validation, group-level gaze diagnostics, and package-native QC plots;
- **Annotation** — native Python EDA review with plot-click manual peaks, brushed artifact intervals, notes, editable session annotation state, and CSV export;
- **EDA / SCR Analysis** — Guided and Expert workflows for EDA quality review, tonic/phasic decomposition, candidate SCR detection, group summaries, package-native decomposition/SCR plots, CSV exports, and an exportable Python reproduction script;
- **PPG / HR / HRV Analysis** — Guided and Expert workflows for pulse-waveform QC, peak detection and rejection, heart-rate quality/windows, IBI/RR quality, time-domain HRV, Poincare diagnostics, optional HeartPy/BioSPPy/pyHRV-style cross-checks, CSV exports, and reproducible Python code;
- **Pupil Analysis** — Guided blink/invalid-sample auditing plus Expert opt-in interpolation, smoothing, baseline correction, event-locked pupil summaries, missingness/trace diagnostics, CSV exports, and reproducible Python code;
- **Reproducibility** — package version, dataset/session summary, operation provenance, analysis count, and interpretation guardrails.

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

On **EDA / SCR Analysis**:

1. select the EDA signal, time column, and optional grouping column;
2. use **Guided** mode for the conservative Studio defaults (31-sample tonic window, automatic threshold, 10-sample minimum peak distance), or switch to **Expert** and set the parameters explicitly;
3. run the workflow to call `audit_gazepoint_gsr_quality()`, `decompose_gazepoint_eda()`, `detect_gazepoint_scr_events()`, and `summarise_gazepoint_gsr_tonic_phasic()`;
4. review package-native decomposition and SCR-event plots, event/group tables, and recorded parameters;
5. export SCR events, tonic/phasic summaries, the decomposed dataset, or a Python script containing the equivalent public package calls.

The default rolling-median residual decomposition is descriptive. Confirmatory SCR/EDA research may require specialised decomposition, event-timing definitions, preregistered thresholds, and sensitivity analyses. EDA/SCR outputs quantify electrodermal signal characteristics and do not infer emotion, stress, cognition, trust, preference, or diagnosis.

On **PPG / HR / HRV Analysis**:

1. Studio detects eligible pulse/PPG, HR, and IBI/RR columns independently, so a file does not need to contain all three signal families;
2. select the time and optional grouping columns and confirm the acquisition sampling rate;
3. use **Guided** mode for the Studio defaults (40–180 bpm, RR tolerance 0.30, 300–2000 ms IBI range, 500 ms maximum jump, no spline refinement, and no optional backend cross-checks), or switch to **Expert** to set these choices explicitly;
4. the waveform path calls `assess_gazepoint_hrp_waveform_quality()`, `detect_gazepoint_ppg_peaks()`, `reject_gazepoint_ppg_peaks()`, and `compute_gazepoint_ppg_measures()`;
5. the HR path calls `audit_gazepoint_hr_quality()` and `summarise_gazepoint_hr_windows()`;
6. the interval path calls `audit_gazepoint_ibi_quality()`, `summarise_gazepoint_ibi_windows()`, and `summarise_gazepoint_hrv_features()`; accepted PPG-derived RR intervals are also summarised when available;
7. Expert mode can additionally request HeartPy, BioSPPy, and pyHRV-style cross-checks through the package bridge APIs;
8. review peak-detection, HR, IBI/HRV, Poincare, and cross-check diagnostics, then export peaks, measures, HR windows, HRV features, or a Python reproduction script.

HRV estimates require genuine beat-to-beat intervals or intervals derived from accepted pulse peaks. Vendor HRV validity fields are not treated as RR intervals. Frequency-domain values from short or sparse recordings are exploratory and should not be interpreted without appropriate segment duration, stationarity, artifact control, and protocol-specific validation. Cardiac outputs do not by themselves establish emotion, stress, trust, preference, cognition, health status, or diagnosis.

On **Pupil Analysis**:

1. select a pupil channel such as Gazepoint `LPD`/`RPD`, its optional validity channel (`LPV`/`RPV`), a time column, and optional participant/trial identifiers;
2. **Guided** mode runs only transparent blink/invalid-sample auditing using `detect_gazepoint_pupil_blinks()` and `detect_gazepoint_blinks()`; it never repairs samples automatically;
3. **Expert** mode can explicitly enable short-gap interpolation through `interpolate_gazepoint_pupil_blinks()` and centered smoothing through `smooth_gazepoint_pupil()`; interpolation receives the validity-aware blink mask and retains `_was_interpolated` flags;
4. task-locked workflows can optionally call `baseline_correct_gazepoint_pupil()` using an explicit stimulus-onset column and trial identifiers;
5. an explicit event-onset column or TTL/marker source can be used with `summarize_gazepoint_pupil_events()` for baseline-relative response amplitude, latency, mean response, and AUC summaries;
6. review blink intervals, sample-level QC, package-native missingness diagnostics, raw/processed traces, repair flags, and event summaries;
7. export blink intervals, the processed pupil dataset, event-response summaries, or an equivalent Python workflow script.

Blink/dropout repair changes the measured time series and should be justified, bounded, flagged, and reported. Pupil responses also depend on event timing, baseline definition, usable-sample coverage, luminance and display conditions where relevant, and protocol-specific exclusions. Pupil diameter is not a direct measure of attention, effort, emotion, trust, preference, or diagnosis.

## State and reproducibility

Studio uses immutable per-session project state. Loading a replacement dataset clears stale QC, annotations, and analyses. Completed analyses are stored by workflow name and append an operation to the provenance trail with the exact parameter set serialized for auditability.

## Architecture rule

Scientific transformations, QC, models, and scientific plots belong in `src/gpbiometricspy/`. Interactive orchestration, session state, presentation, modules, and workflow navigation belong in `studio/`.

Reusable Shiny modules live under `studio/modules/`. The Studio test suite remains separate from the package's frozen scientific-core coverage gate.
