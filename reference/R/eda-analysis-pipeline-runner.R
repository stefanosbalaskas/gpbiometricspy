#' Run a six-phase Gazepoint EDA/GSR analysis pipeline
#'
#' Runs a conservative six-phase Gazepoint EDA/GSR workflow using native
#' `gpbiometrics` helpers where possible. The function imports or accepts data,
#' audits signal quality, prepares preprocessing outputs, creates optional
#' external-method bridge inputs, prepares synchronization/model-formatting
#' outputs, attaches model templates, and generates reporting outputs.
#'
#' The function does not fit `brms` or `lme4` models, does not run external
#' software, and does not infer emotion, valence, stress, trust, preference,
#' cognition, or diagnosis.
#'
#' @param data Optional Gazepoint biometric data frame or imported object.
#' @param path Optional file or folder path. Used only when `data` is `NULL`.
#' @param eda_col Optional EDA/conductance column. If omitted, the runner
#'   prefers `GSR_US` when available.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param signal_cols Optional biometric signal columns for activity plots and
#'   signal audits.
#' @param sampling_rate Optional sampling rate in Hz, used when `time_col` is a
#'   sample counter.
#' @param baseline_window Optional baseline window object passed to baseline
#'   correction helpers when supported.
#' @param event_windows Optional event-window table used for SCR event-window
#'   summaries when available.
#' @param event_data Optional event table used for TTL/event alignment when
#'   available.
#' @param lag_signal_pair Optional character vector of length two giving signals
#'   for lag estimation.
#' @param convert_resistance_to_us Logical. If `TRUE`, allow conservative
#'   resistance-to-conductance conversion when the selected EDA column is `GSR`.
#' @param prepare_external_bridges Logical. If `TRUE`, prepare selected external
#'   EDA bridge inputs.
#' @param bridge_methods Character vector containing any of `"neurokit"`,
#'   `"cvxeda"`, `"ledalab"`, and `"pspm"`.
#' @param prepare_model_data Logical. If `TRUE`, attempt to create SCR hurdle
#'   and biometric LME-ready data objects.
#' @param create_reports Logical. If `TRUE`, attempt to create report outputs.
#' @param output_dir Optional output directory for report bundles or bridge
#'   files where supported.
#' @param prefix File prefix used by output-producing helpers where supported.
#' @param continue_on_error Logical. If `TRUE`, failed steps are stored in
#'   `errors` and the pipeline continues.
#'
#' @return A list with `overview`, `phases`, `errors`, `pipeline_guide`,
#'   `model_templates`, `reporting_guidance`, `interpretation_guardrails`, and
#'   `settings`.
#' @export
run_gazepoint_eda_analysis_pipeline <- function(data = NULL,
                                                path = NULL,
                                                eda_col = NULL,
                                                time_col = NULL,
                                                group_cols = NULL,
                                                signal_cols = NULL,
                                                sampling_rate = NULL,
                                                baseline_window = NULL,
                                                event_windows = NULL,
                                                event_data = NULL,
                                                lag_signal_pair = NULL,
                                                convert_resistance_to_us = FALSE,
                                                prepare_external_bridges = TRUE,
                                                bridge_methods = c("neurokit", "cvxeda", "ledalab", "pspm"),
                                                prepare_model_data = TRUE,
                                                create_reports = TRUE,
                                                output_dir = NULL,
                                                prefix = "gazepoint_eda_pipeline",
                                                continue_on_error = TRUE) {
  gpbiometrics_eda_runner_validate_logical(
    prepare_external_bridges,
    "prepare_external_bridges"
  )
  gpbiometrics_eda_runner_validate_logical(
    prepare_model_data,
    "prepare_model_data"
  )
  gpbiometrics_eda_runner_validate_logical(
    create_reports,
    "create_reports"
  )
  gpbiometrics_eda_runner_validate_logical(
    convert_resistance_to_us,
    "convert_resistance_to_us"
  )
  gpbiometrics_eda_runner_validate_logical(
    continue_on_error,
    "continue_on_error"
  )

  bridge_methods <- match.arg(
    bridge_methods,
    choices = c("neurokit", "cvxeda", "ledalab", "pspm"),
    several.ok = TRUE
  )

  if (!is.null(lag_signal_pair) &&
      (!is.character(lag_signal_pair) || length(lag_signal_pair) != 2)) {
    stop("`lag_signal_pair` must be NULL or a character vector of length two.", call. = FALSE)
  }

  errors <- data.frame(
    phase = integer(),
    step = character(),
    function_name = character(),
    message = character(),
    stringsAsFactors = FALSE
  )

  add_error <- function(phase, step, function_name, message) {
    errors <<- rbind(
      errors,
      data.frame(
        phase = phase,
        step = step,
        function_name = function_name,
        message = message,
        stringsAsFactors = FALSE
      )
    )
  }

  run_step <- function(phase, step, function_name, args = list()) {
    result <- gpbiometrics_eda_runner_call(
      function_name = function_name,
      args = args,
      continue_on_error = continue_on_error
    )

    if (inherits(result, "gazepoint_eda_pipeline_error")) {
      add_error(
        phase = phase,
        step = step,
        function_name = function_name,
        message = result$message
      )
    }

    result
  }

  skip_step <- function(reason) {
    gpbiometrics_eda_runner_skip(reason)
  }

  imported <- NULL

  if (is.null(data)) {
    if (is.null(path)) {
      stop("Supply either `data` or `path`.", call. = FALSE)
    }

    if (dir.exists(path)) {
      imported <- run_step(
        phase = 1,
        step = "folder_import",
        function_name = "import_gazepoint_biometric_folder",
        args = list(
          path = path
        )
      )
    } else {
      imported <- run_step(
        phase = 1,
        step = "file_import",
        function_name = "import_gazepoint_biometrics",
        args = list(
          file = path,
          path = path
        )
      )
    }
  } else {
    imported <- data
  }

  dat <- gpbiometrics_eda_runner_extract_data(imported)

  if (!is.data.frame(dat)) {
    stop("Could not extract a data frame from `data` or imported object.", call. = FALSE)
  }

  resolved_eda_col <- gpbiometrics_eda_runner_resolve_col(
    dat = dat,
    supplied = eda_col,
    candidates = c(
      "GSR_US",
      "GSR_US_PHASIC",
      "GSR_US_TONIC",
      "EDA_US",
      "conductance_us",
      "GSR",
      "EDA"
    ),
    label = "EDA/GSR"
  )

  resolved_time_col <- gpbiometrics_eda_runner_resolve_col(
    dat = dat,
    supplied = time_col,
    candidates = c(
      "time_s",
      "time_sec",
      "time_seconds",
      "time_ms",
      "timestamp_ms",
      "timestamp",
      "TIME",
      "Time",
      "time",
      "CNT",
      "cnt"
    ),
    label = "time/counter",
    allow_null = TRUE
  )

  resolved_group_cols <- gpbiometrics_eda_runner_resolve_group_cols(dat, group_cols)

  resolved_signal_cols <- gpbiometrics_eda_runner_resolve_signal_cols(
    dat = dat,
    signal_cols = signal_cols,
    eda_col = resolved_eda_col
  )

  phase1 <- list(
    imported = imported,
    data = dat,
    schema = run_step(
      1,
      "schema_detection",
      "detect_gazepoint_biometric_schema",
      list(data = dat)
    ),
    time_columns = run_step(
      1,
      "time_column_detection",
      "detect_gazepoint_time_columns",
      list(data = dat)
    ),
    timebase = run_step(
      1,
      "timebase_detection",
      "detect_gazepoint_biometric_timebase",
      list(data = dat, time_col = resolved_time_col, time_column = resolved_time_col)
    ),
    active_channels = run_step(
      1,
      "active_channel_detection",
      "detect_active_biometric_channels",
      list(data = dat)
    ),
    validation = run_step(
      1,
      "validation",
      "validate_gazepoint_biometrics",
      list(data = dat)
    ),
    missingness = run_step(
      1,
      "missingness_audit",
      "audit_gazepoint_biometric_missingness",
      list(data = dat, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    ),
    time_resets = run_step(
      1,
      "time_reset_audit",
      "audit_gazepoint_time_resets",
      list(data = dat, time_col = resolved_time_col, time_column = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    ),
    signal_activity = run_step(
      1,
      "signal_activity_audit",
      "audit_gazepoint_signal_activity",
      list(data = dat, signal_cols = resolved_signal_cols, signal_columns = resolved_signal_cols, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    ),
    eda_artifacts = run_step(
      1,
      "eda_artifact_audit",
      "audit_gazepoint_eda_artifacts",
      list(data = dat, eda_col = resolved_eda_col, gsr_col = resolved_eda_col, time_col = resolved_time_col, time_column = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    ),
    dashboard = run_step(
      1,
      "qc_dashboard",
      "plot_gazepoint_biometric_report_dashboard",
      list(data = dat, signal_cols = resolved_signal_cols, time_col = resolved_time_col, group_cols = resolved_group_cols, max_groups = 12)
    )
  )

  working_data <- dat

  conversion <- if (isTRUE(convert_resistance_to_us)) {
    run_step(
      2,
      "conservative_conductance_conversion",
      "convert_gazepoint_gsr_to_conductance",
      list(data = working_data, gsr_col = resolved_eda_col, eda_col = resolved_eda_col)
    )
  } else {
    skip_step("Skipped because `convert_resistance_to_us = FALSE`; no blind GSR resistance assumption was made.")
  }

  if (is.data.frame(conversion)) {
    working_data <- conversion
  } else if (is.list(conversion) && is.data.frame(conversion$data)) {
    working_data <- conversion$data
  }

  smoothed <- run_step(
    2,
    "smoothing",
    "smooth_gazepoint_biometrics",
    list(data = working_data, signal_cols = resolved_signal_cols, signal_columns = resolved_signal_cols, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
  )

  if (is.data.frame(smoothed)) {
    working_data <- smoothed
  } else if (is.list(smoothed) && is.data.frame(smoothed$data)) {
    working_data <- smoothed$data
  }

  baseline_corrected <- if (!is.null(baseline_window)) {
    run_step(
      2,
      "baseline_correction",
      "baseline_correct_gazepoint_gsr",
      list(data = working_data, eda_col = resolved_eda_col, gsr_col = resolved_eda_col, baseline_window = baseline_window, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because `baseline_window` was not supplied.")
  }

  if (is.data.frame(baseline_corrected)) {
    working_data <- baseline_corrected
  } else if (is.list(baseline_corrected) && is.data.frame(baseline_corrected$data)) {
    working_data <- baseline_corrected$data
  }

  scr_peaks <- run_step(
    2,
    "scr_peak_detection",
    "detect_gazepoint_scr_peaks",
    list(data = working_data, eda_col = resolved_eda_col, gsr_col = resolved_eda_col, time_col = resolved_time_col, time_column = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols, sampling_rate = sampling_rate)
  )

  scr_event_windows <- if (!is.null(event_windows)) {
    run_step(
      2,
      "scr_event_window_summary",
      "summarise_gazepoint_scr_event_windows",
      list(data = working_data, peaks = scr_peaks, event_windows = event_windows, eda_col = resolved_eda_col, time_col = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because `event_windows` was not supplied.")
  }

  response_patterns <- run_step(
    2,
    "eda_response_pattern_classification",
    "classify_gazepoint_eda_response_pattern",
    list(data = working_data, response_col = resolved_eda_col, group_cols = resolved_group_cols)
  )

  phase2 <- list(
    conversion = conversion,
    smoothed = smoothed,
    baseline_corrected = baseline_corrected,
    scr_peaks = scr_peaks,
    scr_event_windows = scr_event_windows,
    response_patterns = response_patterns,
    working_data = working_data
  )

  phase3 <- list()

  if (isTRUE(prepare_external_bridges)) {
    if ("neurokit" %in% bridge_methods) {
      phase3$neurokit <- run_step(
        3,
        "neurokit_bridge",
        "prepare_gazepoint_neurokit_eda_input",
        list(data = working_data, eda_col = resolved_eda_col, gsr_col = resolved_eda_col, time_col = resolved_time_col, group_cols = resolved_group_cols, sampling_rate = sampling_rate)
      )
    }

    if ("cvxeda" %in% bridge_methods) {
      phase3$cvxeda <- run_step(
        3,
        "cvxeda_bridge",
        "prepare_gazepoint_cvxeda_input",
        list(data = working_data, eda_col = resolved_eda_col, time_col = resolved_time_col, group_cols = resolved_group_cols, sampling_rate = sampling_rate, output_dir = NULL)
      )
    }

    if ("ledalab" %in% bridge_methods) {
      phase3$ledalab <- run_step(
        3,
        "ledalab_bridge",
        "prepare_gazepoint_ledalab_input",
        list(data = working_data, eda_col = resolved_eda_col, time_col = resolved_time_col, group_cols = resolved_group_cols, sampling_rate = sampling_rate, output_dir = NULL)
      )
    }

    if ("pspm" %in% bridge_methods) {
      phase3$pspm <- run_step(
        3,
        "pspm_bridge",
        "prepare_gazepoint_pspm_input",
        list(data = working_data, eda_col = resolved_eda_col, time_col = resolved_time_col, group_cols = resolved_group_cols, sampling_rate = sampling_rate, output_dir = NULL)
      )
    }
  } else {
    phase3$bridges <- skip_step("Skipped because `prepare_external_bridges = FALSE`.")
  }

  ttl_events <- run_step(
    4,
    "ttl_event_extraction",
    "extract_gazepoint_ttl_events",
    list(data = working_data, group_cols = resolved_group_cols, group_columns = resolved_group_cols, time_col = resolved_time_col, time_column = resolved_time_col)
  )

  ttl_alignment <- if (!is.null(event_data) || !inherits(ttl_events, "gazepoint_eda_pipeline_error")) {
    run_step(
      4,
      "ttl_alignment",
      "align_gazepoint_biometrics_to_ttl",
      list(data = working_data, ttl_events = ttl_events, events = event_data, event_data = event_data, time_col = resolved_time_col, time_column = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because no usable TTL/event data were available.")
  }

  resolved_lag_pair <- gpbiometrics_eda_runner_lag_pair(
    dat = working_data,
    lag_signal_pair = lag_signal_pair,
    eda_col = resolved_eda_col,
    signal_cols = resolved_signal_cols
  )

  signal_lag <- if (length(resolved_lag_pair) == 2) {
    run_step(
      4,
      "signal_lag_estimation",
      "estimate_gazepoint_signal_lag",
      list(data = working_data, signal_x_col = resolved_lag_pair[1], signal_y_col = resolved_lag_pair[2], time_col = resolved_time_col, group_cols = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because fewer than two numeric signal columns were available for lag estimation.")
  }

  sync_drift <- run_step(
    4,
    "sync_drift_audit",
    "audit_gazepoint_biometric_sync_drift",
    list(data = working_data, time_col = resolved_time_col, group_cols = resolved_group_cols, signal_cols = resolved_signal_cols)
  )

  scr_hurdle_data <- if (isTRUE(prepare_model_data)) {
    run_step(
      4,
      "scr_hurdle_model_data",
      "prepare_gazepoint_scr_hurdle_model_data",
      list(data = working_data, scr_events = scr_event_windows, peaks = scr_peaks, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because `prepare_model_data = FALSE`.")
  }

  lme_data <- if (isTRUE(prepare_model_data)) {
    run_step(
      4,
      "biometrics_lme_data",
      "prepare_gazepoint_biometrics_lme_data",
      list(data = working_data, outcome_cols = resolved_signal_cols, signal_cols = resolved_signal_cols, time_col = resolved_time_col, group_cols = resolved_group_cols, group_columns = resolved_group_cols)
    )
  } else {
    skip_step("Skipped because `prepare_model_data = FALSE`.")
  }

  phase4 <- list(
    ttl_events = ttl_events,
    ttl_alignment = ttl_alignment,
    signal_lag = signal_lag,
    sync_drift = sync_drift,
    scr_hurdle_data = scr_hurdle_data,
    lme_data = lme_data
  )

  pipeline_guide <- run_step(
    5,
    "pipeline_guide",
    "create_gazepoint_eda_analysis_pipeline",
    list(include_external_bridges = prepare_external_bridges, include_model_templates = TRUE, include_reporting_guidance = TRUE, style = "detailed")
  )

  model_templates <- if (is.list(pipeline_guide) && is.data.frame(pipeline_guide$model_templates)) {
    pipeline_guide$model_templates
  } else {
    data.frame()
  }

  phase5 <- list(
    model_templates = model_templates,
    note = paste(
      "Model fitting is intentionally external to gpbiometrics.",
      "Use the prepared SCR hurdle and LME-ready tables with brms, lme4, or another appropriate modelling package."
    )
  )

  report_bundle <- if (isTRUE(create_reports) && !is.null(output_dir)) {
    run_step(
      6,
      "report_bundle",
      "export_gazepoint_biometrics_report_bundle",
      list(data = working_data, output_dir = output_dir, prefix = prefix)
    )
  } else if (isTRUE(create_reports)) {
    skip_step("Skipped report-bundle file export because `output_dir` was not supplied.")
  } else {
    skip_step("Skipped because `create_reports = FALSE`.")
  }

  report_tables <- if (isTRUE(create_reports)) {
    run_step(
      6,
      "report_tables",
      "create_gazepoint_biometrics_report_tables",
      list(data = working_data, workflow = list(data = working_data, quality = phase1, windows = phase2))
    )
  } else {
    skip_step("Skipped because `create_reports = FALSE`.")
  }

  methods_text <- if (isTRUE(create_reports)) {
    run_step(
      6,
      "methods_text",
      "create_gazepoint_biometrics_methods_text",
      list(data = working_data)
    )
  } else {
    skip_step("Skipped because `create_reports = FALSE`.")
  }

  phase6 <- list(
    report_bundle = report_bundle,
    report_tables = report_tables,
    methods_text = methods_text
  )

  phases <- list(
    phase_1_ingestion_qc = phase1,
    phase_2_preprocessing_peaks = phase2,
    phase_3_external_bridges = phase3,
    phase_4_sync_model_formatting = phase4,
    phase_5_model_templates = phase5,
    phase_6_reporting = phase6
  )

  skipped_count <- gpbiometrics_eda_runner_count_class(
    phases,
    "gazepoint_eda_pipeline_skip"
  )

  error_count <- nrow(errors)

  status <- if (error_count == 0) {
    "eda_analysis_pipeline_completed"
  } else if (isTRUE(continue_on_error)) {
    "eda_analysis_pipeline_completed_with_errors"
  } else {
    "eda_analysis_pipeline_failed"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    input_columns = ncol(dat),
    phase_count = length(phases),
    error_count = error_count,
    skipped_count = skipped_count,
    eda_col = if (is.null(resolved_eda_col)) NA_character_ else resolved_eda_col,
    time_col = if (is.null(resolved_time_col)) NA_character_ else resolved_time_col,
    group_cols = paste(resolved_group_cols, collapse = ", "),
    signal_cols = paste(resolved_signal_cols, collapse = ", "),
    external_bridges_prepared = isTRUE(prepare_external_bridges),
    model_data_requested = isTRUE(prepare_model_data),
    reports_requested = isTRUE(create_reports),
    status = status,
    interpretation = paste(
      "The pipeline organizes Gazepoint EDA/GSR preprocessing, QC, bridge preparation, model formatting, and reporting.",
      "It does not fit statistical models, run external software, or infer emotion, valence, stress, trust, preference, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      phases = phases,
      errors = errors,
      pipeline_guide = pipeline_guide,
      model_templates = model_templates,
      reporting_guidance = if (is.list(pipeline_guide)) pipeline_guide$reporting_guidance else data.frame(),
      interpretation_guardrails = if (is.list(pipeline_guide)) pipeline_guide$interpretation_guardrails else data.frame(),
      settings = list(
        path = path,
        eda_col = eda_col,
        resolved_eda_col = resolved_eda_col,
        time_col = time_col,
        resolved_time_col = resolved_time_col,
        group_cols = group_cols,
        resolved_group_cols = resolved_group_cols,
        signal_cols = signal_cols,
        resolved_signal_cols = resolved_signal_cols,
        sampling_rate = sampling_rate,
        baseline_window_supplied = !is.null(baseline_window),
        event_windows_supplied = !is.null(event_windows),
        event_data_supplied = !is.null(event_data),
        lag_signal_pair = lag_signal_pair,
        convert_resistance_to_us = convert_resistance_to_us,
        prepare_external_bridges = prepare_external_bridges,
        bridge_methods = bridge_methods,
        prepare_model_data = prepare_model_data,
        create_reports = create_reports,
        output_dir = output_dir,
        prefix = prefix,
        continue_on_error = continue_on_error
      )
    ),
    class = c("gazepoint_eda_analysis_pipeline_run", "list")
  )
}

gpbiometrics_eda_runner_call <- function(function_name,
                                         args = list(),
                                         continue_on_error = TRUE) {
  fn <- gpbiometrics_eda_runner_get_function(function_name)

  if (is.null(fn)) {
    msg <- paste0("Function `", function_name, "` is not available.")
    if (!isTRUE(continue_on_error)) {
      stop(msg, call. = FALSE)
    }
    return(gpbiometrics_eda_runner_error(msg))
  }

  args <- gpbiometrics_eda_runner_filter_args(fn, args)

  out <- tryCatch(
    do.call(fn, args),
    error = function(e) e
  )

  if (inherits(out, "error")) {
    if (!isTRUE(continue_on_error)) {
      stop(conditionMessage(out), call. = FALSE)
    }
    return(gpbiometrics_eda_runner_error(conditionMessage(out)))
  }

  out
}

gpbiometrics_eda_runner_get_function <- function(function_name) {
  if (exists(function_name, mode = "function", envir = asNamespace("gpbiometrics"), inherits = FALSE)) {
    return(get(function_name, mode = "function", envir = asNamespace("gpbiometrics"), inherits = FALSE))
  }

  if (exists(function_name, mode = "function", inherits = TRUE)) {
    return(get(function_name, mode = "function", inherits = TRUE))
  }

  NULL
}

gpbiometrics_eda_runner_filter_args <- function(fn, args) {
  args <- args[!vapply(args, function(x) length(x) == 0, logical(1))]

  formal_names <- names(formals(fn))

  if ("..." %in% formal_names) {
    return(args)
  }

  args[names(args) %in% formal_names]
}

gpbiometrics_eda_runner_extract_data <- function(x) {
  if (is.data.frame(x)) {
    return(x)
  }

  if (is.list(x)) {
    candidates <- c(
      "data",
      "biometrics",
      "merged_data",
      "all_data",
      "imported_data",
      "raw_data"
    )

    for (nm in candidates) {
      if (!is.null(x[[nm]]) && is.data.frame(x[[nm]])) {
        return(x[[nm]])
      }
    }

    is_df <- vapply(x, is.data.frame, logical(1))

    if (any(is_df)) {
      return(x[[which(is_df)[1]]])
    }
  }

  NULL
}

gpbiometrics_eda_runner_resolve_col <- function(dat,
                                                supplied,
                                                candidates,
                                                label,
                                                allow_null = FALSE) {
  if (!is.null(supplied)) {
    if (!is.character(supplied) || length(supplied) != 1 || is.na(supplied)) {
      stop("`", label, "` column must be a single column name.", call. = FALSE)
    }

    if (!supplied %in% names(dat)) {
      stop("Column `", supplied, "` was not found in `data`.", call. = FALSE)
    }

    return(supplied)
  }

  found <- intersect(candidates, names(dat))

  if (length(found) > 0) {
    return(found[1])
  }

  if (isTRUE(allow_null)) {
    return(NULL)
  }

  stop("No ", label, " column was detected. Supply it explicitly.", call. = FALSE)
}

gpbiometrics_eda_runner_resolve_group_cols <- function(dat, group_cols = NULL) {
  if (!is.null(group_cols)) {
    if (!is.character(group_cols)) {
      stop("`group_cols` must be NULL or a character vector.", call. = FALSE)
    }

    missing_cols <- setdiff(group_cols, names(dat))

    if (length(missing_cols) > 0) {
      stop(
        "The following `group_cols` were not found in `data`: ",
        paste(missing_cols, collapse = ", "),
        call. = FALSE
      )
    }

    return(group_cols)
  }

  candidates <- c(
    "source_file",
    "source_participant",
    "USER_FILE",
    "participant",
    "participant_id",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "stimulus",
    "trial",
    "trial_id",
    "trial_global"
  )

  intersect(candidates, names(dat))
}

gpbiometrics_eda_runner_resolve_signal_cols <- function(dat,
                                                        signal_cols = NULL,
                                                        eda_col = NULL) {
  if (!is.null(signal_cols)) {
    if (!is.character(signal_cols)) {
      stop("`signal_cols` must be NULL or a character vector.", call. = FALSE)
    }

    missing_cols <- setdiff(signal_cols, names(dat))

    if (length(missing_cols) > 0) {
      stop(
        "The following `signal_cols` were not found in `data`: ",
        paste(missing_cols, collapse = ", "),
        call. = FALSE
      )
    }

    return(signal_cols)
  }

  candidates <- c(
    eda_col,
    "GSR_US",
    "GSR_US_PHASIC",
    "GSR_US_TONIC",
    "GSR",
    "EDA",
    "HR",
    "HRP",
    "IBI",
    "DIAL"
  )

  unique(intersect(candidates[!is.na(candidates)], names(dat)))
}

gpbiometrics_eda_runner_lag_pair <- function(dat,
                                             lag_signal_pair = NULL,
                                             eda_col = NULL,
                                             signal_cols = NULL) {
  if (!is.null(lag_signal_pair)) {
    if (all(lag_signal_pair %in% names(dat))) {
      return(lag_signal_pair)
    }

    return(character())
  }

  candidates <- unique(c(
    eda_col,
    intersect(c("HR", "IBI", "DIAL", "GSR_US_PHASIC", "GSR_US_TONIC"), names(dat)),
    signal_cols
  ))

  candidates <- candidates[!is.na(candidates)]
  candidates <- candidates[candidates %in% names(dat)]
  candidates <- candidates[vapply(dat[candidates], is.numeric, logical(1))]

  if (length(candidates) >= 2) {
    return(candidates[1:2])
  }

  character()
}

gpbiometrics_eda_runner_error <- function(message) {
  structure(
    list(
      message = message,
      status = "error"
    ),
    class = c("gazepoint_eda_pipeline_error", "list")
  )
}

gpbiometrics_eda_runner_skip <- function(reason) {
  structure(
    list(
      reason = reason,
      status = "skipped"
    ),
    class = c("gazepoint_eda_pipeline_skip", "list")
  )
}

gpbiometrics_eda_runner_count_class <- function(x, class_name) {
  count <- 0L

  walk <- function(obj) {
    if (inherits(obj, class_name)) {
      count <<- count + 1L
    }

    if (is.list(obj) && !is.data.frame(obj)) {
      for (item in obj) {
        walk(item)
      }
    }

    invisible(NULL)
  }

  walk(x)

  count
}

gpbiometrics_eda_runner_validate_logical <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
