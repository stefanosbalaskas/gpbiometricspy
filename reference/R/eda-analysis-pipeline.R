#' Create a Gazepoint EDA analysis pipeline guide
#'
#' Creates a structured six-phase analysis pipeline for Gazepoint
#' Biometrics EDA/GSR workflows. The helper maps each phase to native
#' `gpbiometrics` functions, optional external-method bridges, and optional
#' downstream model templates for `brms` and `lme4`.
#'
#' This function does not fit statistical models, does not run external
#' software, and does not infer emotion, valence, stress, trust, preference,
#' cognition, or diagnosis. It is a reproducible planning and reporting aid.
#'
#' @param include_external_bridges Logical. If `TRUE`, include NeuroKit2,
#'   Ledalab-style, PsPM-style, cvxEDA-style, RHRV, and pyPPG bridge helpers.
#' @param include_model_templates Logical. If `TRUE`, include text templates
#'   for downstream `brms` hurdle models and `lme4` mixed-effects models.
#' @param include_reporting_guidance Logical. If `TRUE`, include reporting and
#'   interpretation guardrails.
#' @param style Output style. `"compact"` returns concise phase descriptions;
#'   `"detailed"` returns fuller phase notes.
#'
#' @return A list with `overview`, `phases`, `function_map`,
#'   `model_templates`, `reporting_guidance`, `interpretation_guardrails`, and
#'   `settings`.
#' @export
create_gazepoint_eda_analysis_pipeline <- function(include_external_bridges = TRUE,
                                                   include_model_templates = TRUE,
                                                   include_reporting_guidance = TRUE,
                                                   style = c("compact", "detailed")) {
  style <- match.arg(style)

  gpbiometrics_eda_pipeline_validate_logical(
    include_external_bridges,
    "include_external_bridges"
  )
  gpbiometrics_eda_pipeline_validate_logical(
    include_model_templates,
    "include_model_templates"
  )
  gpbiometrics_eda_pipeline_validate_logical(
    include_reporting_guidance,
    "include_reporting_guidance"
  )

  phases <- gpbiometrics_eda_pipeline_phases(style = style)
  function_map <- gpbiometrics_eda_pipeline_function_map(
    include_external_bridges = include_external_bridges
  )

  model_templates <- if (isTRUE(include_model_templates)) {
    gpbiometrics_eda_pipeline_model_templates()
  } else {
    data.frame(
      model_family = character(),
      package = character(),
      target_outcome = character(),
      template = character(),
      notes = character(),
      stringsAsFactors = FALSE
    )
  }

  reporting_guidance <- if (isTRUE(include_reporting_guidance)) {
    gpbiometrics_eda_pipeline_reporting_guidance()
  } else {
    data.frame(
      topic = character(),
      guidance = character(),
      stringsAsFactors = FALSE
    )
  }

  interpretation_guardrails <- gpbiometrics_eda_pipeline_guardrails()

  overview <- data.frame(
    phase_count = nrow(phases),
    function_rows = nrow(function_map),
    model_template_count = nrow(model_templates),
    reporting_guidance_rows = nrow(reporting_guidance),
    external_bridges_included = include_external_bridges,
    model_templates_included = include_model_templates,
    status = "eda_analysis_pipeline_created",
    interpretation = paste(
      "This object is a planning and reporting aid for Gazepoint EDA/GSR workflows.",
      "It does not fit models, run external software, or infer emotion, valence, stress, trust, preference, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      phases = phases,
      function_map = function_map,
      model_templates = model_templates,
      reporting_guidance = reporting_guidance,
      interpretation_guardrails = interpretation_guardrails,
      settings = list(
        include_external_bridges = include_external_bridges,
        include_model_templates = include_model_templates,
        include_reporting_guidance = include_reporting_guidance,
        style = style
      )
    ),
    class = c("gazepoint_eda_analysis_pipeline", "list")
  )
}

gpbiometrics_eda_pipeline_phases <- function(style = "compact") {
  compact <- data.frame(
    phase = 1:6,
    phase_name = c(
      "Data ingestion, auditing, and quality control",
      "Baseline preprocessing and peak detection",
      "Advanced signal decomposition through external-method bridges",
      "Synchronization and model formatting",
      "Statistical modelling outside gpbiometrics",
      "Reproducible reporting"
    ),
    purpose = c(
      "Import Gazepoint exports, detect schemas and active channels, and audit missingness, time resets, inactive signals, and signal quality.",
      "Apply conservative unit conversion, smoothing, baseline correction, descriptive SCR peak extraction, event-window summaries, and response-pattern classification.",
      "Prepare cleaned EDA data for established external tools when SCR overlap or close stimulus spacing requires deconvolution or external decomposition.",
      "Align physiological signals to TTL/event markers, audit lag and drift, and prepare model-ready repeated-measures tables.",
      "Use prepared data with external statistical packages such as brms or lme4 for zero-heavy SCR amplitude and repeated-measures SCL/EDA models.",
      "Create report bundles, report-ready tables, cautious methods text, dashboards, and reproducible analysis documentation."
    ),
    native_gpbiometrics = c(TRUE, TRUE, FALSE, TRUE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )

  if (identical(style, "compact")) {
    return(compact)
  }

  compact$details <- c(
    paste(
      "Raw Gazepoint biometric exports should be audited before substantive analysis.",
      "The package supports file and folder import, Data Summary parsing, schema detection, active-channel detection, missingness checks, time-reset diagnostics, and signal-activity auditing."
    ),
    paste(
      "Preprocessing is deliberately conservative.",
      "Raw GSR conversion is user-confirmed, baseline correction and smoothing are transparent, and peak/event summaries describe physical EDA responses without psychological labels."
    ),
    paste(
      "Complex EDA decomposition is not reimplemented natively.",
      "Instead, gpbiometrics prepares clean input tables for established external workflows such as NeuroKit2, Ledalab-style, PsPM-style, and cvxEDA-style analysis."
    ),
    paste(
      "Multimodal modelling requires reliable alignment between physiology and events.",
      "The package supports TTL extraction/alignment, lag estimation, drift audits, SCR hurdle-model data preparation, and LME-ready biometric data preparation."
    ),
    paste(
      "Model fitting remains outside gpbiometrics to avoid heavy dependencies.",
      "Templates show how prepared outputs can be used with brms for hurdle-style SCR models and lme4 for mixed-effects SCL/EDA models."
    ),
    paste(
      "Reporting helpers document data quality, preprocessing, exclusions, transformations, and analysis-readiness decisions.",
      "Generated text remains cautious and avoids direct emotion, cognition, valence, stress, trust, or preference inference."
    )
  )

  compact
}

gpbiometrics_eda_pipeline_function_map <- function(include_external_bridges = TRUE) {
  native_rows <- data.frame(
    phase = c(
      rep(1L, 9),
      rep(2L, 7),
      rep(4L, 6),
      rep(6L, 6)
    ),
    function_name = c(
      "import_gazepoint_biometrics",
      "import_gazepoint_biometric_folder",
      "import_gazepoint_data_summary",
      "detect_gazepoint_biometric_schema",
      "detect_gazepoint_time_columns",
      "detect_gazepoint_biometric_timebase",
      "audit_gazepoint_time_resets",
      "audit_gazepoint_signal_activity",
      "audit_gazepoint_biometric_missingness",
      "convert_gazepoint_gsr_to_conductance",
      "smooth_gazepoint_biometrics",
      "baseline_correct_gazepoint_gsr",
      "audit_gazepoint_eda_artifacts",
      "detect_gazepoint_scr_peaks",
      "summarise_gazepoint_scr_event_windows",
      "classify_gazepoint_eda_response_pattern",
      "extract_gazepoint_ttl_events",
      "align_gazepoint_biometrics_to_ttl",
      "estimate_gazepoint_signal_lag",
      "audit_gazepoint_biometric_sync_drift",
      "prepare_gazepoint_scr_hurdle_model_data",
      "prepare_gazepoint_biometrics_lme_data",
      "export_gazepoint_biometrics_report_bundle",
      "create_gazepoint_biometrics_report_tables",
      "create_gazepoint_biometrics_methods_text",
      "plot_gazepoint_biometric_report_dashboard",
      "run_gazepoint_biometrics_real_data_readiness",
      "create_gazepoint_biometrics_feature_inventory"
    ),
    role = c(
      "Import single Gazepoint biometric export.",
      "Import a folder of Gazepoint biometric exports.",
      "Parse Gazepoint Data Summary exports.",
      "Detect Gazepoint biometric schema.",
      "Detect candidate time or counter columns.",
      "Detect biometric timebase.",
      "Audit grouped time/counter resets.",
      "Audit inactive, all-zero, or low-variance channels.",
      "Audit biometric missingness.",
      "Conservatively convert verified resistance-like GSR to conductance.",
      "Smooth selected biometric time-series columns.",
      "Apply GSR/EDA baseline correction.",
      "Flag EDA artefacts and corrupted segments.",
      "Detect descriptive SCR peaks.",
      "Summarise SCR responses in event windows.",
      "Classify descriptive EDA response patterns without psychological labels.",
      "Extract TTL/event marker rows.",
      "Align biometric data to TTL events.",
      "Estimate descriptive lag between two recorded signals.",
      "Audit synchronization drift descriptively.",
      "Prepare zero-heavy SCR response data for hurdle-style models.",
      "Prepare repeated-measures biometric data for mixed-effects models.",
      "Export report bundle outputs.",
      "Create report-ready tables.",
      "Generate cautious methods text.",
      "Create lightweight QC dashboard.",
      "Run real-data readiness checks.",
      "Summarise package feature availability."
    ),
    native_gpbiometrics = TRUE,
    external_dependency_required = FALSE,
    stringsAsFactors = FALSE
  )

  if (!isTRUE(include_external_bridges)) {
    native_rows$available <- gpbiometrics_eda_pipeline_available(native_rows$function_name)
    return(native_rows)
  }

  bridge_rows <- data.frame(
    phase = rep(3L, 5),
    function_name = c(
      "prepare_gazepoint_neurokit_eda_input",
      "prepare_gazepoint_cvxeda_input",
      "prepare_gazepoint_ledalab_input",
      "prepare_gazepoint_pspm_input",
      "run_gazepoint_neurokit_eda_crosscheck"
    ),
    role = c(
      "Prepare cleaned EDA input for optional NeuroKit2-style workflows.",
      "Prepare cleaned EDA input for optional cvxEDA-style workflows.",
      "Prepare cleaned EDA input for optional Ledalab-style workflows.",
      "Prepare cleaned EDA input for optional PsPM-style workflows.",
      "Optionally cross-check EDA processing with NeuroKit2 when available."
    ),
    native_gpbiometrics = TRUE,
    external_dependency_required = c(FALSE, FALSE, FALSE, FALSE, TRUE),
    stringsAsFactors = FALSE
  )

  out <- rbind(native_rows, bridge_rows)
  out <- out[order(out$phase, out$function_name), , drop = FALSE]
  rownames(out) <- NULL
  out$available <- gpbiometrics_eda_pipeline_available(out$function_name)

  out
}

gpbiometrics_eda_pipeline_model_templates <- function() {
  data.frame(
    model_family = c(
      "SCR occurrence and amplitude",
      "SCL or mean EDA level",
      "EDA response pattern"
    ),
    package = c("brms", "lme4", "lme4 or brms"),
    target_outcome = c(
      "Zero-heavy SCR amplitude or response magnitude",
      "Continuous skin conductance level or baseline-corrected EDA",
      "Descriptive response-pattern categories"
    ),
    template = c(
      paste(
        "brms::brm(",
        "  bf(scr_amplitude ~ condition + trial_order + (1 | participant),",
        "     hu ~ condition + trial_order + (1 | participant)),",
        "  data = scr_hurdle_data,",
        "  family = hurdle_lognormal()",
        ")",
        sep = "\n"
      ),
      paste(
        "lme4::lmer(",
        "  scl_mean ~ condition + trial_order + baseline_scl + (1 | participant),",
        "  data = lme_data",
        ")",
        sep = "\n"
      ),
      paste(
        "lme4::glmer(",
        "  response_detected ~ condition + trial_order + (1 | participant),",
        "  data = response_pattern_data,",
        "  family = binomial()",
        ")",
        sep = "\n"
      )
    ),
    notes = c(
      paste(
        "Template only. Use when zero responses are substantively meaningful.",
        "Check distributional assumptions, priors, convergence, posterior predictive checks, and trial/participant nesting."
      ),
      paste(
        "Template only. Use for continuous background arousal/SCL-style summaries.",
        "Interpret with baseline, artefact, task, and participant-level context."
      ),
      paste(
        "Template only. Response-pattern labels are descriptive and should not be interpreted as emotion, valence, stress, trust, preference, cognition, or diagnosis."
      )
    ),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_eda_pipeline_reporting_guidance <- function() {
  data.frame(
    topic = c(
      "Data source",
      "Quality control",
      "Preprocessing",
      "EDA/SCR extraction",
      "External methods",
      "Synchronization",
      "Statistical modelling",
      "Interpretation"
    ),
    guidance = c(
      "Report Gazepoint export type, software/export context when known, imported files, detected channels, time columns, and timebase.",
      "Report missingness, inactive channels, all-zero or flat channels, time resets, sampling issues, artefact flags, and exclusion/review thresholds.",
      "Report conductance conversion only when unit assumptions are explicit; report smoothing and baseline-correction settings.",
      "Report SCR peak/event-window rules, thresholds, response windows, and whether zero responses were retained as informative outcomes.",
      "Report external tools as optional post-export workflows; do not imply that gpbiometrics reimplemented Ledalab, PsPM, cvxEDA, NeuroKit2, RHRV, or pyPPG.",
      "Report TTL/event alignment, lag checks, drift checks, and how timing windows were defined.",
      "Report model family, link/distribution, random effects, participant/trial nesting, covariates, convergence checks, and treatment of zero responses.",
      "Avoid direct inference from EDA to emotion, valence, trust, preference, cognition, or diagnosis without converging task, behavioural, and self-report evidence."
    ),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_eda_pipeline_guardrails <- function() {
  data.frame(
    signal_or_method = c(
      "GSR/EDA",
      "SCR peaks",
      "Response patterns",
      "External decomposition",
      "Heart rate",
      "IBI-derived HRV",
      "Eye-tracking measures",
      "Timing diagnostics"
    ),
    conservative_interpretation = c(
      "Electrodermal or arousal-related signal; not emotional valence.",
      "Discrete conductance responses under specified detection thresholds; not direct evidence of emotion.",
      "Descriptive QC/reporting labels only.",
      "External method input or cross-check; not a native clone or replacement.",
      "Requires baseline, artefact, and task context.",
      "Compute only from genuine IBI/RR intervals, not raw Gazepoint HRV validity/vendor columns.",
      "Visual attention and timing indicators, not direct cognition, scrutiny, or evaluation.",
      "Synchronization QC only; not causal timing or true physiological latency."
    ),
    avoid_claiming = c(
      "Emotion, valence, stress, trust, preference, cognition, diagnosis.",
      "Emotion, valence, stress, trust, preference, cognition, diagnosis.",
      "Emotion class, valence class, trust state, diagnostic state.",
      "That gpbiometrics reimplemented Ledalab, PsPM, cvxEDA, NeuroKit2, RHRV, or pyPPG.",
      "Task engagement or affect without context.",
      "HRV from raw Gazepoint HRV columns unless independently documented.",
      "Deep cognition or evaluative processing from gaze alone.",
      "Physiological latency or causal ordering without design support."
    ),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_eda_pipeline_available <- function(function_name) {
  vapply(function_name, function(fn) {
    exists(fn, mode = "function", envir = parent.frame(2), inherits = TRUE) ||
      exists(fn, mode = "function", envir = asNamespace("gpbiometrics"), inherits = FALSE)
  }, logical(1))
}

gpbiometrics_eda_pipeline_validate_logical <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
