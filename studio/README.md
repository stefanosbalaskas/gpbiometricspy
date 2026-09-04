# gpbiometricspy Studio

`gpbiometricspy Studio` is the first-party Shiny for Python application layer for `gpbiometricspy`.
The scientific package remains the computational engine; Studio calls the public package API instead of reimplementing scientific algorithms.

## Current application

Studio now provides eleven workflow areas:

- **Home** — bundled synthetic demo or single CSV/TXT intake, schema validation, detected channels, preview, foundation missingness/activity QC, and package-native signal-activity plotting;
- **Quality Control** — configurable time-reset/segment diagnostics, EDA and heart-rate quality audits, gaze validation, group-level gaze diagnostics, and package-native QC plots;
- **Annotation** — native Python EDA review with plot-click manual peaks, brushed artifact intervals, notes, editable session annotation state, and CSV export;
- **EDA / SCR Analysis** — Guided and Expert workflows for EDA quality review, tonic/phasic decomposition, candidate SCR detection, group summaries, package-native decomposition/SCR plots, CSV exports, and an exportable Python reproduction script;
- **PPG / HR / HRV Analysis** — Guided and Expert workflows for pulse-waveform QC, peak detection and rejection, heart-rate quality/windows, IBI/RR quality, time-domain HRV, Poincare diagnostics, optional HeartPy/BioSPPy/pyHRV-style cross-checks, CSV exports, and reproducible Python code;
- **Pupil Analysis** — Guided blink/invalid-sample auditing plus Expert opt-in interpolation, smoothing, baseline correction, event-locked pupil summaries, missingness/trace diagnostics, CSV exports, and reproducible Python code;
- **Gaze / Fixation / AOI Analysis** — gaze validation and screen filtering, fixation/saccade detection, rectangular AOI assignment or existing AOI use, dwell/fixation summaries, scanpath metrics, saccade diagnostics, CSV exports, and reproducible Python code;
- **Events & Alignment** — TTL/marker extraction, external event-log import, group-safe event windows, TTL-relative alignment, optional two-stream event-anchor synchronization, lag/drift diagnostics, CSV exports, and reproducible Python code;
- **Multimodal Analysis** — event-locked EDA/cardiac/pupil/gaze summaries on the validated event clock, reuse of prior processed Studio streams, AOI-linked biometrics, participant/trial windows, model-ready tables, package-native timeline diagnostics, exports, and reproducible code;
- **Statistics & Modelling** — auditable mixed-effects model-data preparation plus design-gated two-condition within-subject cluster permutation, package-native diagnostics/plots/reports, threshold sensitivity, guardrails, exports, and reproducible code;
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

On **Gaze / Fixation / AOI Analysis**:

1. select gaze X/Y, time, optional validity, participant, and trial/stimulus columns;
2. `validate_gazepoint_gaze()` audits missing/invalid gaze, timestamps, duplicate/non-monotonic time, gaps, coordinate range, and expected sampling rate;
3. screen-bound filtering is optional and uses `filter_gazepoint_gaze()`; normalized data use the 0–1 screen and pixel data use the supplied screen dimensions;
4. Guided mode can classify fixation/saccade events through `detect_gazepoint_fixations()` using operational duration/velocity starting points, while Expert mode exposes the event thresholds explicitly;
5. AOIs can come from an existing AOI column or an uploaded rectangular definition table (`aoi,xmin,xmax,ymin,ymax[,priority]`) delegated to `assign_gazepoint_aoi()` with explicit overlap and boundary rules;
6. detected fixation tables are summarized with `summarize_gazepoint_fixations()` and, when AOI geometry is available, `summarise_gazepoint_fixations_by_aoi()`;
7. AOI dwell/entry metrics use `summarize_gazepoint_aoi_dwell()`, while path length, step distance, saccade-like steps, regression-like movements, AOI transition count and transition entropy use `summarize_gazepoint_scanpath_metrics()`;
8. review the gaze trajectory, AOI geometry, package-native saccade main-sequence diagnostic, event/AOI tables and scanpath metrics, then export processed gaze, fixations, saccades, AOI dwell, scanpath metrics, or reproducible Python code.

Velocity-based event classification depends on sampling rate, coordinate units, calibration, preprocessing, and threshold definitions; Guided settings are starting points rather than universal classifiers. AOI results likewise depend on accurate geometry and stimulus alignment. Gaze measures describe oculomotor behaviour and should not be treated as direct evidence of attention, comprehension, preference, intent, emotion, trust, or diagnosis.

On **Events & Alignment**:

1. choose a reference time column and use either a TTL/marker column in the loaded recording or an external event-log CSV/TXT/TSV;
2. TTL audit rows are extracted with `extract_gazepoint_ttl_events()`, while TTL-relative windows and event identities come from `align_gazepoint_biometrics_to_ttl()`;
3. external logs are standardized with `import_gazepoint_event_log()` into `event_id`, `event_time`, and `event_label` while preserving extra design/grouping columns;
4. sample-level and event-level windows are generated through `match_gazepoint_events_to_biometrics()`; when a grouping column is selected, Studio calls that package matcher separately within each group to prevent cross-participant event leakage;
5. Guided mode uses a rising-edge TTL rule, a 1 s pre-event window, a 5 s post-event window, and no nearby-event collapse; Expert mode exposes TTL extraction mode, edge rule, collapse interval, and the event window explicitly;
6. a second Gazepoint stream can optionally be uploaded and aligned from shared TTL/event anchors using `align_gazepoint_streams_by_events()` with either a constant-offset or linear offset+drift model;
7. event-anchor lag and drift are diagnosed with `diagnose_gazepoint_sync_drift()`; cross-stream clock fitting is intentionally restricted to one participant/session at a time rather than pooling independent clocks;
8. review standardized events, TTL extraction/alignment tables, event-locked samples and summaries, clock-model residuals and lag/drift plots, then export reference events, matched windows, aligned target timestamps, lag tables, or a Python reproduction script.

Event synchronization is only as defensible as its anchors. Misordered, duplicated, sparse, or semantically mismatched events can create plausible-looking but incorrect clock fits. Event-locked measurement changes also do not establish causal responses without an appropriate experimental design.

On **Multimodal Analysis**:

1. complete **Events & Alignment** for the current dataset first; Multimodal Analysis deliberately refuses to invent or independently reinterpret the event clock;
2. select EDA/SCR, cardiac, pupil, and optional gaze X/Y channels. Guided mode automatically prefers compatible processed EDA, pupil, and gaze outputs from prior Studio analyses and reports the resolved source for every modality;
3. `summarize_gazepoint_eventlocked_multimodal()` creates event-relative samples and per-event/per-signal summaries, including baseline mean, summary mean, peak/minimum values, peak latency, AUC, and missingness;
4. when participant/trial identifiers are selected, `summarise_gazepoint_multimodal_windows()` and `prepare_gazepoint_multimodal_model_data()` create grouped descriptive windows and a model-ready table;
5. when a processed or native AOI column is available, Studio performs group-safe event-window matching and calls `summarise_gazepoint_aoi_biometrics()` so biometric values can be summarized within AOI membership for each event/group;
6. `plot_gazepoint_multimodal_timeline()` provides the package-native synchronized signal view. Standardized event times from Events & Alignment are overlaid as timing references rather than being inferred from signal shape;
7. Expert mode exposes the extraction window, baseline window, response-summary window, processed/raw preference, and timeline standardization;
8. export event-response summaries, sample-level event windows, an event × modality matrix, participant/trial windows, model-ready data, AOI-linked summaries, or a Python reproduction script.

A common event clock permits multimodal comparison but does not make physiological and oculomotor channels interchangeable. Their latency, smoothing, sampling, artifact, and valid response-window assumptions remain modality-specific. Cross-modal co-occurrence should not be interpreted as direct evidence of emotion, attention, trust, preference, cognition, or diagnosis.

On **Statistics & Modelling**:

1. Studio exposes curated statistical source tables from the loaded dataset and prior analyses, including multimodal event responses/samples, multimodal model data, modality-specific processed samples, and selected summary tables;
2. **Model Preparation** delegates to `prepare_gazepoint_biometrics_lme_data()` to define the numeric outcome, fixed effects, covariates, participant/trial random-effect identifiers, optional baseline correction, factor roles, continuous scaling, complete cases, and an auditable formula;
3. Model Preparation intentionally stops at a model-ready table and formula. Studio does not claim that a mixed model has been fitted because the current public package contract provides model-data preparation rather than a general mixed-model estimator;
4. **Cluster Permutation** first calls `prepare_gazepoint_timecourse_test_data()` to aggregate repeated participant × condition × time observations and optionally bin time;
5. the prepared grid must then pass `diagnose_gazepoint_cluster_design()`. Error-level failures such as a non-complete participant × two-condition × time grid block permutations rather than being silently ignored;
6. valid designs run `run_gazepoint_cluster_permutation()` using the package-supported within-subject sign-flip scheme, followed by `summarize_gazepoint_time_clusters()`, `report_gazepoint_cluster_permutation()`, package-native time-course plotting, and null-distribution plotting;
7. Expert mode can vary the time bin, mean/median aggregation, diagnostic participant target, permutation count, cluster-forming alpha, cluster alpha, tail, seed, and optional `run_gazepoint_cluster_threshold_sensitivity()` analysis;
8. Studio explicitly lists the package guardrails for unsupported ANOVA/>2-condition cluster inference, mixed-model cluster permutation, TFCE, multidimensional clusters, and precise cluster onset/offset estimation instead of presenting those exports as functioning methods;
9. model-ready data, variable audits, cluster results, timewise statistics, prepared grids, and exact Python reproduction scripts are downloadable and their parameters are stored in immutable Studio provenance.

A significant cluster is cluster-level evidence against the tested global null, not proof that every time point in the cluster differs and not a precise estimator of effect onset or offset. Model formulas likewise describe a proposed statistical design; they do not establish identifiability, convergence, distributional adequacy, causal interpretation, or substantive validity on their own.

## State and reproducibility

Studio uses immutable per-session project state. Loading a replacement dataset clears stale QC, annotations, and analyses. Completed analyses are stored by workflow name and append an operation to the provenance trail with the exact parameter set serialized for auditability.

## Architecture rule

Scientific transformations, QC, models, and scientific plots belong in `src/gpbiometricspy/`. Interactive orchestration, session state, presentation, modules, and workflow navigation belong in `studio/`.

Reusable Shiny modules live under `studio/modules/`. The Studio test suite remains separate from the package's frozen scientific-core coverage gate.
