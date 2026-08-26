#' gpbiometrics: Process, Audit, Plot, and Report Gazepoint Biometrics Data
#'
#' `gpbiometrics` provides helper functions for importing, checking,
#' preprocessing, summarising, diagnosing, plotting, and reporting Gazepoint
#' Biometrics exports. It is designed for reproducible offline workflows
#' involving physiological, response-channel, event-marker, and timing data
#' exported alongside Gazepoint eye-tracking recordings.
#'
#' @details
#' The package supports common Gazepoint biometric channels, including GSR/EDA,
#' heart rate, interbeat interval or RR-style intervals, engagement dial, and
#' TTL markers. It provides functions for folder-level import, data-summary
#' import, schema and timebase detection, active-channel detection, column
#' validation, missingness audits, signal-quality audits, sampling and timing
#' audits, dropout and flatline flagging, baseline correction, smoothing, window
#' summaries, TTL event extraction, biometric-to-gaze synchronisation, exclusion
#' recommendations, workflow diagnostics, report-ready tables, cautious methods
#' text, lightweight report generation, and base-R diagnostic plotting.
#'
#' Schema and timing helpers include
#' `standardise_gazepoint_biometric_names()`,
#' `detect_gazepoint_biometric_schema()`,
#' `detect_gazepoint_time_columns()`, and
#' `detect_gazepoint_biometric_timebase()`. Signal-availability and quality
#' helpers include `summarise_gazepoint_biometric_validity()`,
#' `flag_gazepoint_biometric_dropouts()`, `audit_gazepoint_gsr_quality()`,
#' `audit_gazepoint_hr_quality()`, `audit_gazepoint_engagement_dial()`, and
#' `audit_gazepoint_ibi_quality()`.
#'
#' Preprocessing and summary helpers include
#' `baseline_correct_gazepoint_gsr()`,
#' `baseline_correct_gazepoint_hr()`, `smooth_gazepoint_biometrics()`,
#' `convert_gazepoint_gsr_to_conductance()`,
#' `summarise_gazepoint_gsr_windows()`,
#' `summarise_gazepoint_hr_windows()`,
#' `summarise_gazepoint_engagement_windows()`,
#' `summarise_gazepoint_dial_windows()`,
#' `summarise_gazepoint_ibi_windows()`,
#' `summarise_gazepoint_gsr_tonic_phasic()`,
#' `summarise_gazepoint_multimodal_windows()`,
#' `summarise_gazepoint_ibi_hrv_windows()`, and
#' `summarise_gazepoint_full_biometric_windows()`.
#'
#' Synchronisation, modelling, workflow, and reporting helpers include
#' `sync_gazepoint_biometrics_with_gaze()`,
#' `join_gazepoint_biometrics_to_master()`,
#' `join_gazepoint_biometrics_to_gp3tools()`,
#' `prepare_gazepoint_multimodal_model_data()`,
#' `run_gazepoint_biometrics_workflow()`,
#' `summarise_gazepoint_biometrics_workflow()`,
#' `diagnose_gazepoint_biometrics_workflow()`,
#' `create_gazepoint_biometrics_checklist()`,
#' `create_gazepoint_biometrics_methods_text()`,
#' `create_gazepoint_biometrics_report_tables()`,
#' `write_gazepoint_biometrics_report_tables()`, and
#' `create_gazepoint_biometrics_report()`. Diagnostic plotting helpers include
#' `plot_gazepoint_biometric_signals()` and
#' `plot_gazepoint_biometric_quality()`.
#'
#' The package treats biometric signals conservatively. GSR/EDA is handled as an
#' electrodermal activity or arousal-related signal rather than emotional
#' valence. Heart-rate summaries should be interpreted relative to baseline,
#' artefact handling, and task context. Raw Gazepoint `HRV` columns should be
#' treated as validity or vendor flags unless independent documentation proves
#' otherwise. IBI-derived HRV-style summaries should be computed only from
#' genuine interbeat interval or RR-style interval columns. Eye-tracking
#' measures, when combined with biometric data, should be interpreted as
#' indicators of visual attention rather than direct evidence of cognition,
#' scrutiny, or evaluation.
#'
#' @section Main workflow:
#'
#' The main workflow function is:
#'
#' `run_gazepoint_biometrics_workflow()`
#'
#' Useful follow-up helpers include:
#'
#' `summarise_gazepoint_biometrics_workflow()`,
#' `diagnose_gazepoint_biometrics_workflow()`,
#' `create_gazepoint_biometrics_report_tables()`,
#' `write_gazepoint_biometrics_report_tables()`, and
#' `create_gazepoint_biometrics_report()`.
#'
#' @section Interpretation caution:
#'
#' `gpbiometrics` is a preprocessing, quality-control, visualisation, and
#' reporting toolkit. It does not classify emotions, mental states, or cognitive
#' processes directly. Researchers should interpret biometric signals in
#' relation to experimental design, baseline periods, stimulus timing, task
#' demands, artefact handling, and complementary behavioural or self-report
#' measures.
#'
#' @docType package
#' @name gpbiometrics-package
#' @aliases gpbiometrics
#' @keywords internal
"_PACKAGE"
