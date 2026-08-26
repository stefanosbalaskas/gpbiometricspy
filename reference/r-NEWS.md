# gpbiometrics 2.0.0

- Version 2.0.0 consolidates the expanded gpbiometrics workflow for Gazepoint import, validation, quality control, preprocessing, multimodal alignment, external interoperability, reporting, reproducibility, and privacy-safe validation.
- Added workflow articles for auditing interoperability across external package versions and for running privacy-safe smoke tests on genuine Gazepoint exports stored outside the repository.
- Added a privacy-safe real-data smoke-test harness with external-directory protection, anonymous dataset identifiers, sanitized conditions, aggregate workflow and diagnostic summaries, repository-safe CSV reporting, and local command-line tools for running and combining private-data audits.
- Added a machine-readable interoperability version-testing framework with declared bridge contracts, minimum-tested Python versions, dependency and runtime audits, privacy-safe CSV reports, and a dedicated GitHub Actions matrix covering R eye-tracking bridges and floor/current Python environments.
- Added four workflow articles covering MNE/EEG/LSL interoperability, BIDS export and data sharing, eyetrackingR/PupillometryR/gazeR bridges, and troubleshooting and real-data readiness.
- Added reciprocal gp3tools compatibility documentation describing the   cross-package biometric schema, time-unit requirements, synchronization   ownership boundary, audit expectations, and interpretation guardrails.

- Closed the remaining roadmap gaps with `validate_gazepoint_gaze()`, `summarise_gazepoint_fixations_by_aoi()` and its American-spelling alias, modality-specific BIDS convenience wrappers, optional native MNE FIF writing through a local Python/MNE installation, and optional live LSL clock-offset estimation through pylsl.
- Added an integrated MNE/EEG/LSL interoperability module with `prepare_gazepoint_mne_events()`, `prepare_gazepoint_mne_input()`, `align_gazepoint_to_eeg()`, `sync_gazepoint_signals_via_lsl()`, `create_gazepoint_eye_methods_text()`, and `session_info_gazepoint()` for auditable event conversion, channel-matrix preparation, offset and drift correction, post-import LSL/XDF synchronization, standardized eye-tracking methods reporting, and reproducibility metadata.
- Added `prepare_gazepoint_gazer_input()` for auditable conversion of long-form Gazepoint gaze and pupil samples into gazeR-compatible subject, trial, millisecond-time, monocular or binocular coordinate, pupil, validity, and blink columns, with optional runtime construction through a locally installed GitHub version of `gazer`.
- Added `prepare_gazepoint_pupillometryr_input()` for auditable conversion of long-form Gazepoint pupil samples into PupillometryR-compatible subject, trial, millisecond-time, condition, pupil, validity, and blink columns, with optional invalid-sample masking and construction of a `PupillometryR` object.
- Added `prepare_gazepoint_eyetrackingr_input()` for auditable conversion of sample-level Gazepoint gaze and AOI data into eyetrackingR-compatible participant, trial, millisecond-time, track-loss, and logical AOI columns, with optional construction of an `eyetrackingR_data` object.
- Added `export_gazepoint_to_bids()` for standards-oriented BIDS 1.11.1 eye-tracking export with headerless compressed physiological tables, JSON sidecars, screen-metadata enforcement, dry-run path previews, and overwrite protection.
- Added `prepare_gazepoint_biosppy_input()` for auditable preparation of grouped Gazepoint EDA/GSR and PPG/BVP waveform vectors with timebase validation, explicit missing-data handling, and optional Python-ready CSV export.
- Added `prepare_gazepoint_pyhrv_input()` for auditable conversion of Gazepoint IBI/RR data into grouped millisecond NN-interval vectors and optional Python-ready CSV files.
- Added `assign_gazepoint_aoi()` for auditable rectangular and polygonal AOI assignment with context matching, boundary control, and explicit overlap resolution.
- Added `detect_gazepoint_fixations()` and `detect_gazepoint_saccades()` for auditable I-VT-style classification of raw Gazepoint gaze samples and extraction of fixation and saccade event properties.
- Added `downsample_gazepoint_data()` for auditable fixed-width aggregation of grouped Gazepoint gaze and biometric time series.
* Polished the pkgdown home-page DOI badge and grouped article navigation into workflow categories.
* Added a plot-rich toolbox-crosscheck visuals article with executable synthetic native-versus-toolbox comparison, EDA event-count, PPG peak/IBI, HRV-feature, Bland-Altman-style, rank-sensitivity, decision-map, and dashboard figures.
* Added a plot-rich design-release visual audit article with executable synthetic condition-balance, coverage, schema, channel, sampling, timebase, readiness, and dashboard figures.
* Added a plot-rich multimodal event-dashboard article with executable synthetic event-timeline, alignment, event-locked, AOI-linked, synchronization-lag, coverage, and dashboard figures.
* Added a plot-rich PPG/HRV visual diagnostics article with executable synthetic filtering, peak-detection, IBI-audit, Poincare-style, HRV-feature, respiration-proxy, and dashboard figures.
* Added a plot-rich EDA/SCR visual diagnostics article with executable synthetic signal, decomposition, event-marker, latency, recovery, and threshold-sensitivity figures.
* Added a plot-rich visual QC dashboard workflow article with executable synthetic diagnostic figures.
* Expanded the plot gallery with additional QC, signal-processing, EDA/SCR, PPG/HRV, event-alignment, AOI, reporting, design-audit, and toolbox-bridge plotting examples.
* Added an external-toolbox bridges workflow article covering HeartPy, pyPPG, pyHRV, RHRV, LEDALAB, PSPM, cvxEDA, NeuroKit, and BioSPPy-style preparation, cross-checks, result import, export contracts, and reporting.
* Added a design-audit workflow article covering metadata validation, dataset structure, condition balance, session comparability, export-schema checks, event coverage, timing audits, pipeline readiness, design-coverage plots, and reporting outputs.
* Added a synthetic-data showcase article demonstrating validation, QC, event alignment, AOI-linked summaries, model-ready tables, reporting outputs, and reproducibility records without private data.
* Added a reporting and reproducibility workflow article covering decision logs, manifests, QC supplements, methods text, report-ready tables, audit trails, preregistration checks, and reproducibility statements.
* Added an event-alignment and AOI-linked biometric workflow article covering event extraction, timing audits, stream alignment, gaze-biometric synchronization, AOI time courses, event-locked summaries, model-ready tables, and reporting.
* Added a PPG, IBI, HRV, and respiration workflow article covering PPG quality, filtering, peak detection, IBI audits, beat correction, HRV summaries, respiration proxies, external-toolbox preparation, and reporting.
* Added an EDA, GSR, and SCR workflow article covering unit audits, signal quality, artifacts, baseline correction, tonic/phasic decomposition, SCR events, sensitivity checks, model-ready summaries, and reporting.
* Added a pupil and gaze quality-control workflow article covering missingness, blink detection, smoothing, interpolation, baseline correction, gaze filtering, QC summaries, and reporting.
* Added an article roadmap for planned workflow, showcase, plotting, reporting, and reproducibility articles.
* Added a quality-control workflow article linking dataset-layout checks, metadata validation, missingness summaries, signal-quality flags, exclusion recommendations, dashboard summaries, and reproducibility outputs.
* Added `pipeline_comparison_dashboard()` for static reviewer-facing summaries of QC, missingness, quality, rule-failure, exclusion, and audit indicators.

* Added `check_gazepoint_bids()` for conservative BIDS-like Gazepoint dataset layout audits.

# gpbiometrics 0.3.0

* Added advanced cluster-permutation guardrails and external export helpers. The guardrail functions explicitly prevent unsupported ANOVA, mixed-model, TFCE, multidimensional, covariate-adjusted, parallel, and onset/offset cluster claims while directing users back to the validated two-condition time-course workflow. Added export helpers for MNE-, permuco-, and permutes-style external workflows.

* Added cluster-permutation diagnostics, reporting, sensitivity, simulation, null-distribution plotting, and export helpers: `audit_gazepoint_timecourse_grid()`, `diagnose_gazepoint_cluster_design()`, `plot_gazepoint_cluster_null_distribution()`, `report_gazepoint_cluster_permutation()`, `run_gazepoint_cluster_threshold_sensitivity()`, `simulate_gazepoint_cluster_timecourse_data()`, and `export_gazepoint_cluster_results()`.

## Experimental statistical extensions

* Added an experimental within-subject, two-condition cluster-based permutation prototype for Gazepoint-derived time-course signals.
* Added `prepare_gazepoint_timecourse_test_data()`, `run_gazepoint_cluster_permutation()`, `summarize_gazepoint_time_clusters()`, and `plot_gazepoint_cluster_permutation()`.
* Added an experimental pkgdown article describing the prototype and emphasizing that cluster timing should be interpreted descriptively rather than as precise onset or offset evidence.

* Added release-preparation and auditability helpers for preregistration
  readiness, dataset-structure review, pipeline mapping, audit-trail
  summaries, and conservative release-readiness checks.
* Added pkgdown reference coverage for the new audit, checklist, pipeline,
  preregistration, dataset-inventory, and release-readiness helpers.

# gpbiometrics 0.2.0

* Added roadmap compatibility aliases and discoverability wrappers for
  column standardization, format validation, pupil cleaning/interpolation,
  PPG-derived respiration estimation, and mixed-model data preparation.
* Added `compare_gazepoint_conditions_bootstrap()` for lightweight
  percentile-bootstrap condition comparisons of Gazepoint-derived
  trial-level, event-locked, or participant-level outcomes.
* Added physiology/QC refinement helpers for HRV segment quality flags,
  SCR latency metrics, pairwise multimodal signal-lag screening, and
  exploratory PPG-derived respiration-rate estimation.
* Added alignment, AOI time-course, event-locked synthesis, and dashboard
  helpers for event-based stream alignment, binned AOI proportions,
  multimodal event-locked summaries, and compact quality-dashboard exports.
* Added front-door audit and missingness helpers: unified Gazepoint
  biometrics preflight audit, dedicated missingness/gap summaries, and
  generic signal detrending for slow drift in biometric or pupil signals.
* Added exact roadmap backlog helpers for schema standardization, export
  schema auditing, multimodal simulation, sampling-irregularity QC, sync-drift
  diagnostics, AOI dwell summaries, scanpath metrics, analysis manifests,
  PPG template-similarity QC, and Haar-style HRV wavelet PSD summaries.
* Added remaining roadmap helpers for SCR habituation/recovery, event-related
  pupil summaries, tracking ratios, pupil-luminance audits, PPG morphology,
  segment-level PPG quality, generic event-log import, event-to-biometric
  matching, column validation, and reproducibility metadata.
* Added `import_gazepoint_data()` as a single-entry helper for importing
  Gazepoint session folders into named lists of data frames.
* Added `impute_gazepoint_missing()` for CRAN-safe interpolation of short
  missing gaps in continuous Gazepoint signals.
* Added pupil and gaze helpers: `detect_gazepoint_pupil_blinks()`,
  `clean_gazepoint_pupil_signal()`, `filter_gazepoint_gaze()`, and
  `summarize_gazepoint_fixations()`.
* Added event-level physiology helpers: `epoch_gazepoint_scr()`,
  `normalize_gazepoint_scr()`, `flag_gazepoint_rr_outliers()`, and
  `compute_gazepoint_engagement_index()`.
* Added workflow helpers for modeling and reporting:
  `create_gazepoint_trial_regressors()`, `report_gazepoint_data_quality()`,
  and `preprocess_gazepoint_all()`.
* Added `simulate_gazepoint_eye_data()` for synthetic Gazepoint-style gaze,
  fixation, pupil, blink, and validity data for teaching, tests, vignettes,
  and smoke tests.
* Updated package metadata, README, and pkgdown configuration to reflect the
  expanded Gazepoint-native workflow surface.

# gpbiometrics 0.1.1

- Added Gazepoint-native pyHRV-style HRV workflows, including time-domain,
  frequency-domain, nonlinear, Poincare, sample-entropy, DFA, PSD, tachogram,
  radar-chart, export/import, and all-in-one HRV helpers.
- Added BioSPPy-style Gazepoint biosignal workflows for EDA event extraction,
  EDA recovery-time estimation, PPG/BVP processing, PPG pulse templates,
  PPG onset detection, local RRI artifact correction, RRI detrending, power
  spectra, band power, phase locking, and signal correlation.
- Added PsPM-style Gazepoint preprocessing and modelling workflows for marker
  extraction, marker-channel combination, trimming, session splitting,
  recording merging, SCR preprocessing/QC, event-centred segment extraction,
  convolution-GLM design creation, GLM fitting, and model-estimate export.
- Extended HeartPy-style PPG support with segmentwise processing, signal
  scaling, filtering, smoothing, clipping reconstruction, binary-quality
  checks, breathing-rate visualisation, Poincare plotting, and frequency
  measures.
- Updated package metadata and README to describe the new Gazepoint-native
  toolbox-style workflow layers without claiming exact external-toolbox
  equivalence.

# gpbiometrics 0.1.0

- Added HeartPy-style Gazepoint pulse/PPG workflows, including input preparation,
  clipping reconstruction, peak enhancement, Butterworth-style filtering, Hampel
  correction, adaptive peak detection, peak rejection, HR/IBI-style measures,
  breathing-rate estimation, plotting, report-table generation, and optional
  Python HeartPy cross-checking through `reticulate`.

## Overview

* Initial validated development release of `gpbiometrics`, an R package for importing, validating, quality-checking, preprocessing, synchronising, summarising, modelling, plotting, and reporting Gazepoint Biometrics and Gazepoint GP3 biometric exports.
* The package focuses on Gazepoint-specific biometric channels, including GSR/EDA, heart rate, interbeat intervals, pulse signal, engagement dial, TTL markers, pupil-related columns, AOI fields, and synchronisation variables.
* The current feature inventory contains 155 available user-facing helpers across 11 complete workflow domains.
* Interpretation is intentionally conservative: biometric features are treated as physiological descriptors, quality-control outputs, or analysis-ready signals, not direct labels for emotion, stress, cognition, preference, health status, or diagnosis.

## Import, schema, and workflow infrastructure

* Added import helpers for single files and export folders, including `import_gazepoint_biometrics()`, `import_gazepoint_biometric_folder()`, `import_gazepoint_data_summary()`, and `import_gazepoint_lsl_xdf()`.
* Added Gazepoint schema and channel-detection helpers, including `check_gazepoint_biometric_columns()`, `detect_gazepoint_biometric_schema()`, `detect_gazepoint_time_columns()`, `detect_active_biometric_channels()`, and `standardise_gazepoint_biometric_names()`.
* Added the main workflow wrapper `run_gazepoint_biometrics_workflow()` and summary/diagnostic helpers, including `summarise_gazepoint_biometrics_workflow()` and `diagnose_gazepoint_biometrics_workflow()`.
* Added synthetic data generation with `simulate_gazepoint_biometrics()` for examples, teaching, and controlled validation.

## Quality control and readiness

* Added validation, missingness, sampling, signal-activity, time-reset, dropout, distributional-drift, and real-data readiness checks.
* Added `run_gazepoint_biometrics_real_data_readiness()` as a final readiness gate for real Gazepoint exports.
* Added exclusion-recommendation helpers for participant-level and window-level biometric quality decisions.
* Added artifact-detection helpers, including MAD-based, Kleckner-style, and SVM-feature workflows.
* Added `audit_gazepoint_gsr_units()` to help distinguish conductance-like and resistance-like GSR columns before downstream EDA/SCR processing.
* Added `audit_gazepoint_stabilization_period()` for flagging or trimming the initial electrode-stabilisation period.

## Preprocessing and signal correction

* Added baseline correction, smoothing, within-unit standardisation, z-score/range correction, adaptive EMA smoothing, wavelet denoising, quantisation-noise handling, and optional autoencoder-denoising bridges.
* Added EDA/GSR unit auditing and conductance-conversion helpers.
* Added environmental and stimulus-confound controls, including `correct_gazepoint_eda_temperature()`, `audit_gazepoint_stabilization_period()`, and `regress_gazepoint_pupil_luminance()`.
* Added both British and American spelling aliases where useful, including standardise/standardize variants.

## EDA, GSR, and SCR analysis

* Added EDA/GSR quality audits, tonic/phasic summaries, SCR event and peak detection, SCR event-window summaries, nonresponder screening, threshold-sensitivity checks, and SCR multiverse workflows.
* Added SCR recovery-time extraction with `extract_gazepoint_scr_recovery_times()`, including half-recovery and 63 percent recovery-time summaries.
* Added advanced EDA helpers for spectral power, complexity, TVSymp-style analysis, bilateral EDA asymmetry, skin-potential analysis, AC admittance/susceptance, stochastic change-point screening, and EDA-gram-style visualisation.
* Added external EDA interoperability helpers for Ledalab, PsPM, cvxEDA, NeuroKit-style input, and DCM/CTSI-oriented bridges.
* Added `run_gazepoint_automated_statistics()` for exploratory group comparisons with normality screening, ANOVA/Kruskal-Wallis selection, post-hoc testing, and multiplicity correction.

## Pulse, IBI, HR, HRV, and respiration

* Added HR, IBI, and HRV quality and consistency checks.
* Added HR/IBI window summaries and IBI-derived HRV feature extraction.
* Added nonlinear and geometric HRV descriptors, including RQA, fragmentation, asymmetry, FuzzyEn/CSI, RCMSE, surrogate nonlinearity testing, and IPFM-style impulse-train modelling.
* Added Gazepoint pulse beat-candidate extraction with `extract_gazepoint_beats_kmeans()`.
* Added respiration-related helpers, including PPG-derived respiration, ECG-derived respiration PCA bridges, CEEMDAN-style respiration extraction, RSA proxy calculation, and Kalman fusion of respiration proxy streams.
* Added point-process and cardiorespiratory directionality helpers for advanced exploratory analysis.

## TTL, synchronisation, windows, and model-ready data

* Added TTL event extraction and TTL alignment helpers.
* Added signal-lag estimation and synchronisation-drift diagnostics.
* Added multimodal time-window summaries and model-ready table preparation helpers for biometric, AOI-linked, and LME-style analyses.
* Added chunking and online design-optimisation decision-support helpers for advanced experimental workflows.
* Added helpers for synchronising Gazepoint Biometrics outputs with Gazepoint eye-tracking master tables.

## AOI-linked biometrics and plotting

* Added AOI-linked biometric summaries, AOI-biometric model data preparation, and AOI-biometric plotting.
* Added biometric signal plots, quality plots, decomposition plots, SCR plots, multimodal timelines, activity/time-reset plots, report dashboards, SCR specification-curve plots, saccade main-sequence plots, and EDA-gram-style plots.
* Added plot-contract helpers to store plot data, settings, and interpretation metadata for reproducibility.

## Reporting, feature inventory, and documentation

* Added checklist, methods-text, report-table, report-bundle, preregistration-template, and Shiny/annotator helpers.
* Added `create_gazepoint_biometrics_feature_inventory()` for programmatic workflow coverage checks.
* Added formatted inventory helpers, `format_gazepoint_biometrics_feature_inventory()` and `summarise_gazepoint_biometrics_feature_inventory()`.
* Added a compact user-facing README and the first workflow vignette, `vignettes/gpbiometrics-workflow.Rmd`.
* Updated workflow documentation to use the current `run_gazepoint_biometrics_workflow(path = ...)` API and to export report bundles through `export_gazepoint_biometrics_report_bundle()`.
* Added a public, fully synthetic Gazepoint-like kiosk demo dataset under `inst/extdata/gazepoint_biometrics_kiosk_demo_exports/`.
* The demo dataset contains 36 synthetic participants, four kiosk tasks per participant, 69,120 rows, 36 all-gaze CSV exports, task metadata, gaze/AOI fields, pupil columns, GSR/EDA, HR, IBI, pulse waveform, engagement dial, and TTL markers.
* Added `data-raw/create_gazepoint_biometrics_kiosk_demo_exports.R` to regenerate the synthetic demo exports reproducibly.
* Added package tests to ensure the synthetic kiosk demo remains available, importable, and schema-valid.


## Interoperability and optional external methods

* Added RHRV, pyPPG, NeuroKit2, Ledalab, PsPM, cvxEDA, DCM, and CTSI-oriented preparation/export bridges.
* External-method bridges remain optional and do not make external software a hard dependency.
* Advanced bridge functions prepare or structure data for external workflows unless explicit cross-check execution is requested and available.

## Validation

* Current local validation passed with:

```r
devtools::test()
# FAIL 0 | WARN 0 | SKIP 0 | PASS 1662

devtools::check()
# 0 errors | 0 warnings | 0 notes
```

* The workflow vignette builds during `devtools::check()`.
* A private real-data smoke test on a local Gazepoint export folder passed import, readiness, workflow, summary, and report-bundle export checks.
* The private workflow used 6 source files, 7340 imported all-gaze rows, 70 columns, 1323 TTL events, 0 validation issues, and 3 active signal groups.
* The private report-bundle export wrote 81 files with 0 skipped items.
* Private data and private smoke-test outputs remain outside the package repository.

## Interpretation safeguards

* EDA/GSR/SCR features describe electrodermal dynamics and arousal-related physiology; they do not directly infer emotion, stress, cognition, health status, or diagnosis.
* HR, IBI, HRV, pulse, and respiration-proxy features describe cardiovascular or signal-derived dynamics; they are not clinical labels.
* Pupil outputs are affected by luminance and visual context; luminance-adjusted residuals are not proof of cognitive-load-only effects.
* AOI-linked biometric summaries describe signal values during AOI exposure and do not establish emotional valence, preference, or cognitive evaluation by themselves.
* Automated statistics and advanced models are exploratory/reporting aids unless matched to a preregistered design and reviewed analytically.
