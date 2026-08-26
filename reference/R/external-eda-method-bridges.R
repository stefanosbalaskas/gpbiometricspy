#' Prepare Gazepoint EDA input for external Ledalab-style workflows
#'
#' Prepares a clean Gazepoint EDA/conductance time-series table that can be
#' exported for external Ledalab-style workflows. This function does not run
#' Ledalab and does not attempt to reproduce Ledalab internally.
#'
#' @param data A Gazepoint biometric data frame, or a list containing one.
#' @param eda_col Optional EDA/conductance column. If omitted, the function
#'   prefers `GSR_US` when available.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz, used when the time column
#'   is a sample counter.
#' @param time_unit Unit of `time_col`.
#' @param convert_resistance_to_us If `TRUE`, convert a selected resistance-like
#'   `GSR` column to microsiemens as `1,000,000 / GSR`. The default is `FALSE`
#'   because this conversion should be used only when the user has verified that
#'   `GSR` is resistance-like and `GSR_US` is unavailable.
#' @param min_finite_prop Minimum finite proportion required for a group to be
#'   labelled ready.
#' @param output_dir Optional folder where CSV files should be written.
#' @param prefix File prefix used when `output_dir` is supplied.
#'
#' @return A list with `overview`, `signal_table`, `group_summary`, `manifest`,
#'   and `settings`.
#' @export
prepare_gazepoint_ledalab_input <- function(data,
                                            eda_col = NULL,
                                            time_col = NULL,
                                            group_cols = NULL,
                                            sampling_rate = NULL,
                                            time_unit = c("auto", "ms", "seconds", "samples"),
                                            convert_resistance_to_us = FALSE,
                                            min_finite_prop = 0.50,
                                            output_dir = NULL,
                                            prefix = "gazepoint_ledalab") {
  gpbiometrics_prepare_external_eda_input(
    data = data,
    method = "ledalab",
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate = sampling_rate,
    time_unit = match.arg(time_unit),
    convert_resistance_to_us = convert_resistance_to_us,
    min_finite_prop = min_finite_prop,
    output_dir = output_dir,
    prefix = prefix
  )
}

#' Prepare Gazepoint EDA input for external PsPM-style workflows
#'
#' Prepares a clean Gazepoint EDA/conductance time-series table that can be
#' exported for external PsPM-style workflows. This function does not run PsPM
#' and does not attempt to reproduce PsPM internally.
#'
#' @inheritParams prepare_gazepoint_ledalab_input
#'
#' @return A list with `overview`, `signal_table`, `group_summary`, `manifest`,
#'   and `settings`.
#' @export
prepare_gazepoint_pspm_input <- function(data,
                                         eda_col = NULL,
                                         time_col = NULL,
                                         group_cols = NULL,
                                         sampling_rate = NULL,
                                         time_unit = c("auto", "ms", "seconds", "samples"),
                                         convert_resistance_to_us = FALSE,
                                         min_finite_prop = 0.50,
                                         output_dir = NULL,
                                         prefix = "gazepoint_pspm") {
  gpbiometrics_prepare_external_eda_input(
    data = data,
    method = "pspm",
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate = sampling_rate,
    time_unit = match.arg(time_unit),
    convert_resistance_to_us = convert_resistance_to_us,
    min_finite_prop = min_finite_prop,
    output_dir = output_dir,
    prefix = prefix
  )
}

#' Prepare Gazepoint EDA input for external cvxEDA-style workflows
#'
#' Prepares a clean Gazepoint EDA/conductance time-series table that can be
#' exported for external cvxEDA-style workflows. This function does not run a
#' native cvxEDA solver and does not attempt to reproduce cvxEDA internally.
#'
#' @inheritParams prepare_gazepoint_ledalab_input
#'
#' @return A list with `overview`, `signal_table`, `group_summary`, `manifest`,
#'   and `settings`.
#' @export
prepare_gazepoint_cvxeda_input <- function(data,
                                           eda_col = NULL,
                                           time_col = NULL,
                                           group_cols = NULL,
                                           sampling_rate = NULL,
                                           time_unit = c("auto", "ms", "seconds", "samples"),
                                           convert_resistance_to_us = FALSE,
                                           min_finite_prop = 0.50,
                                           output_dir = NULL,
                                           prefix = "gazepoint_cvxeda") {
  gpbiometrics_prepare_external_eda_input(
    data = data,
    method = "cvxeda",
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate = sampling_rate,
    time_unit = match.arg(time_unit),
    convert_resistance_to_us = convert_resistance_to_us,
    min_finite_prop = min_finite_prop,
    output_dir = output_dir,
    prefix = prefix
  )
}

#' Classify descriptive Gazepoint EDA response patterns
#'
#' Classifies descriptive EDA response patterns from an EDA/SCR feature column.
#' The labels are intended for quality-control and descriptive reporting only.
#' They do not infer emotion, valence, stress, trust, preference, cognition, or
#' diagnosis.
#'
#' @param data A data frame containing EDA/SCR values.
#' @param response_col Optional response feature column. If omitted, the helper
#'   searches for common SCR/EDA response columns and then `GSR_US_PHASIC` or
#'   `GSR_US`.
#' @param group_cols Optional grouping columns.
#' @param summary_function Summary used within each group.
#' @param no_response_threshold Absolute response threshold for
#'   `no_detectable_response`.
#' @param low_response_threshold Upper threshold for `low_response`.
#' @param moderate_response_threshold Upper threshold for `moderate_response`.
#'
#' @return A list with `overview`, `classifications`, and `settings`.
#' @export
classify_gazepoint_eda_response_pattern <- function(data,
                                                    response_col = NULL,
                                                    group_cols = NULL,
                                                    summary_function = c("max_abs", "mean_abs", "median_abs"),
                                                    no_response_threshold = 0.01,
                                                    low_response_threshold = 0.05,
                                                    moderate_response_threshold = 0.20) {
  dat <- gpbiometrics_eda_bridge_extract_data(data)

  summary_function <- match.arg(summary_function)

  response_col <- gpbiometrics_eda_bridge_resolve_response_col(
    dat = dat,
    response_col = response_col
  )

  group_cols <- gpbiometrics_eda_bridge_resolve_group_cols(dat, group_cols)

  gpbiometrics_eda_bridge_validate_thresholds(
    no_response_threshold = no_response_threshold,
    low_response_threshold = low_response_threshold,
    moderate_response_threshold = moderate_response_threshold
  )

  split_info <- gpbiometrics_eda_bridge_split_data(dat, group_cols)

  classifications <- lapply(split_info$groups, function(group_dat) {
    response <- suppressWarnings(as.numeric(group_dat[[response_col]]))
    finite_response <- response[is.finite(response)]

    abs_response <- abs(finite_response)

    response_value <- if (length(abs_response) == 0) {
      NA_real_
    } else if (identical(summary_function, "max_abs")) {
      max(abs_response, na.rm = TRUE)
    } else if (identical(summary_function, "mean_abs")) {
      mean(abs_response, na.rm = TRUE)
    } else {
      stats::median(abs_response, na.rm = TRUE)
    }

    pattern <- gpbiometrics_eda_bridge_response_label(
      response_value = response_value,
      no_response_threshold = no_response_threshold,
      low_response_threshold = low_response_threshold,
      moderate_response_threshold = moderate_response_threshold
    )

    group_values <- gpbiometrics_eda_bridge_group_values(group_dat, group_cols)

    data.frame(
      group_values,
      group_id = gpbiometrics_eda_bridge_group_id(group_dat, group_cols),
      response_col = response_col,
      n_rows = nrow(group_dat),
      n_finite = length(finite_response),
      finite_prop = if (nrow(group_dat) > 0) length(finite_response) / nrow(group_dat) else NA_real_,
      summary_function = summary_function,
      response_value = response_value,
      response_pattern = pattern,
      status = if (length(finite_response) == 0) "fail_no_finite_response_values" else "response_pattern_classified",
      interpretation = paste(
        "This is a descriptive EDA response-pattern label only.",
        "It does not infer emotion, valence, stress, trust, preference, cognition, or diagnosis."
      ),
      stringsAsFactors = FALSE
    )
  })

  classifications <- gpbiometrics_eda_bridge_rbind(classifications)

  status <- if (nrow(classifications) == 0) {
    "no_groups_classified"
  } else if (all(classifications$status == "response_pattern_classified")) {
    "eda_response_patterns_classified"
  } else if (any(classifications$status == "response_pattern_classified")) {
    "partial_eda_response_patterns_classified"
  } else {
    "eda_response_patterns_not_classified"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = nrow(classifications),
    classified_group_count = sum(classifications$status == "response_pattern_classified"),
    response_col = response_col,
    summary_function = summary_function,
    status = status,
    interpretation = paste(
      "EDA response-pattern labels are descriptive QC/reporting aids.",
      "They do not infer emotion, valence, stress, trust, preference, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      classifications = classifications,
      settings = list(
        response_col = response_col,
        group_cols = group_cols,
        summary_function = summary_function,
        no_response_threshold = no_response_threshold,
        low_response_threshold = low_response_threshold,
        moderate_response_threshold = moderate_response_threshold
      )
    ),
    class = c("gazepoint_eda_response_pattern", "list")
  )
}

gpbiometrics_prepare_external_eda_input <- function(data,
                                                    method,
                                                    eda_col,
                                                    time_col,
                                                    group_cols,
                                                    sampling_rate,
                                                    time_unit,
                                                    convert_resistance_to_us,
                                                    min_finite_prop,
                                                    output_dir,
                                                    prefix) {
  dat <- gpbiometrics_eda_bridge_extract_data(data)

  eda_col <- gpbiometrics_eda_bridge_resolve_eda_col(dat, eda_col)
  time_col <- gpbiometrics_eda_bridge_resolve_time_col(dat, time_col)
  group_cols <- gpbiometrics_eda_bridge_resolve_group_cols(dat, group_cols)

  gpbiometrics_eda_bridge_validate_sampling_rate(sampling_rate)
  gpbiometrics_eda_bridge_validate_min_finite_prop(min_finite_prop)

  split_info <- gpbiometrics_eda_bridge_split_data(dat, group_cols)

  prepared <- lapply(split_info$groups, function(group_dat) {
    gpbiometrics_eda_bridge_prepare_group(
      group_dat = group_dat,
      method = method,
      eda_col = eda_col,
      time_col = time_col,
      group_cols = group_cols,
      sampling_rate = sampling_rate,
      time_unit = time_unit,
      convert_resistance_to_us = convert_resistance_to_us,
      min_finite_prop = min_finite_prop
    )
  })

  signal_table <- gpbiometrics_eda_bridge_rbind(lapply(prepared, `[[`, "signal_table"))
  group_summary <- gpbiometrics_eda_bridge_rbind(lapply(prepared, `[[`, "group_summary"))

  manifest <- gpbiometrics_eda_bridge_write_outputs(
    signal_table = signal_table,
    group_summary = group_summary,
    output_dir = output_dir,
    prefix = prefix,
    method = method
  )

  ready_group_count <- if (nrow(group_summary) == 0) {
    0L
  } else {
    sum(group_summary$status == paste0("ready_for_", method, "_input"))
  }

  status <- if (nrow(group_summary) == 0) {
    paste0(method, "_input_not_prepared")
  } else if (ready_group_count == nrow(group_summary)) {
    paste0(method, "_input_prepared")
  } else if (ready_group_count > 0) {
    paste0(method, "_input_prepared_with_review_flags")
  } else {
    paste0(method, "_input_requires_review")
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = nrow(group_summary),
    ready_group_count = ready_group_count,
    method = method,
    eda_col = eda_col,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    conductance_unit = unique(signal_table$conductance_unit)[1],
    output_file_count = nrow(manifest),
    status = status,
    interpretation = paste(
      "Output is prepared for optional external EDA workflows.",
      "No external toolbox is invoked and no emotion, valence, stress, trust, preference, cognition, or diagnosis is inferred."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      signal_table = signal_table,
      group_summary = group_summary,
      manifest = manifest,
      settings = list(
        method = method,
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        time_unit = time_unit,
        convert_resistance_to_us = convert_resistance_to_us,
        min_finite_prop = min_finite_prop,
        output_dir = output_dir,
        prefix = prefix
      )
    ),
    class = c(paste0("gazepoint_", method, "_input"), "gazepoint_external_eda_input", "list")
  )
}

gpbiometrics_eda_bridge_prepare_group <- function(group_dat,
                                                  method,
                                                  eda_col,
                                                  time_col,
                                                  group_cols,
                                                  sampling_rate,
                                                  time_unit,
                                                  convert_resistance_to_us,
                                                  min_finite_prop) {
  group_id <- gpbiometrics_eda_bridge_group_id(group_dat, group_cols)
  group_values <- gpbiometrics_eda_bridge_group_values(group_dat, group_cols)

  eda_raw <- suppressWarnings(as.numeric(group_dat[[eda_col]]))

  used_conversion <- FALSE
  conductance_unit <- "as_supplied"

  if (isTRUE(convert_resistance_to_us) &&
      identical(toupper(eda_col), "GSR")) {
    eda_raw <- ifelse(is.finite(eda_raw) & eda_raw > 0, 1000000 / eda_raw, NA_real_)
    used_conversion <- TRUE
    conductance_unit <- "microsiemens_converted_from_resistance"
  } else if (toupper(eda_col) %in% c("GSR_US", "EDA_US", "CONDUCTANCE_US")) {
    conductance_unit <- "microsiemens"
  }

  timing <- gpbiometrics_eda_bridge_time_seconds(
    group_dat = group_dat,
    time_col = time_col,
    sampling_rate = sampling_rate,
    time_unit = time_unit
  )

  signal_table <- data.frame(
    group_values,
    group_id = rep(group_id, nrow(group_dat)),
    sample_index = seq_len(nrow(group_dat)),
    time_s = timing$time_s,
    conductance_us = eda_raw,
    eda_raw = suppressWarnings(as.numeric(group_dat[[eda_col]])),
    method = method,
    eda_col = eda_col,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    detected_time_unit = timing$detected_time_unit,
    conductance_unit = conductance_unit,
    used_resistance_conversion = used_conversion,
    stringsAsFactors = FALSE
  )

  if (identical(method, "cvxeda")) {
    signal_table$y <- signal_table$conductance_us
  }

  n_finite <- sum(is.finite(signal_table$conductance_us))
  finite_prop <- if (nrow(signal_table) > 0) n_finite / nrow(signal_table) else NA_real_

  status <- if (nrow(signal_table) == 0) {
    paste0("review_no_rows_for_", method)
  } else if (!is.finite(finite_prop) || finite_prop < min_finite_prop) {
    paste0("review_low_finite_signal_for_", method)
  } else if (all(is.na(signal_table$time_s))) {
    paste0("prepared_with_sample_index_only_for_", method)
  } else {
    paste0("ready_for_", method, "_input")
  }

  interpretation <- paste(
    "Prepared signal is an external-method input table only.",
    "External decomposition/model fitting remains outside gpbiometrics.",
    "No emotion, valence, stress, trust, preference, cognition, or diagnosis is inferred."
  )

  group_summary <- data.frame(
    group_values,
    group_id = group_id,
    method = method,
    eda_col = eda_col,
    n_rows = nrow(signal_table),
    n_finite = n_finite,
    finite_prop = finite_prop,
    conductance_min = suppressWarnings(min(signal_table$conductance_us, na.rm = TRUE)),
    conductance_median = suppressWarnings(stats::median(signal_table$conductance_us, na.rm = TRUE)),
    conductance_max = suppressWarnings(max(signal_table$conductance_us, na.rm = TRUE)),
    conductance_sd = suppressWarnings(stats::sd(signal_table$conductance_us, na.rm = TRUE)),
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    detected_time_unit = timing$detected_time_unit,
    time_span_s = timing$time_span_s,
    median_time_step_s = timing$median_time_step_s,
    estimated_sampling_rate_hz = timing$estimated_sampling_rate_hz,
    conductance_unit = conductance_unit,
    used_resistance_conversion = used_conversion,
    status = status,
    interpretation = interpretation,
    stringsAsFactors = FALSE
  )

  finite_numeric_cols <- c(
    "conductance_min",
    "conductance_median",
    "conductance_max",
    "conductance_sd"
  )

  for (nm in finite_numeric_cols) {
    if (!is.finite(group_summary[[nm]])) {
      group_summary[[nm]] <- NA_real_
    }
  }

  list(
    signal_table = signal_table,
    group_summary = group_summary
  )
}

gpbiometrics_eda_bridge_extract_data <- function(data) {
  if (is.data.frame(data)) {
    return(data)
  }

  if (is.list(data)) {
    candidates <- c("data", "biometrics", "merged_data", "all_data", "imported_data")

    for (nm in candidates) {
      if (!is.null(data[[nm]]) && is.data.frame(data[[nm]])) {
        return(data[[nm]])
      }
    }

    is_df <- vapply(data, is.data.frame, logical(1))

    if (any(is_df)) {
      return(data[[which(is_df)[1]]])
    }
  }

  stop("`data` must be a data frame or a list containing a data frame.", call. = FALSE)
}

gpbiometrics_eda_bridge_resolve_eda_col <- function(dat, eda_col = NULL) {
  if (!is.null(eda_col)) {
    if (!is.character(eda_col) || length(eda_col) != 1 || is.na(eda_col)) {
      stop("`eda_col` must be a single column name.", call. = FALSE)
    }

    if (!eda_col %in% names(dat)) {
      stop("Column `", eda_col, "` was not found in `data`.", call. = FALSE)
    }

    return(eda_col)
  }

  candidates <- c(
    "GSR_US",
    "gsr_us",
    "EDA_US",
    "eda_us",
    "conductance_us",
    "GSR_US_PHASIC",
    "GSR_US_TONIC",
    "EDA",
    "eda",
    "GSR"
  )

  found <- intersect(candidates, names(dat))

  if (length(found) == 0) {
    stop(
      "No EDA/conductance column was detected. Supply `eda_col` explicitly.",
      call. = FALSE
    )
  }

  found[1]
}

gpbiometrics_eda_bridge_resolve_response_col <- function(dat, response_col = NULL) {
  if (!is.null(response_col)) {
    if (!is.character(response_col) || length(response_col) != 1 || is.na(response_col)) {
      stop("`response_col` must be a single column name.", call. = FALSE)
    }

    if (!response_col %in% names(dat)) {
      stop("Column `", response_col, "` was not found in `data`.", call. = FALSE)
    }

    return(response_col)
  }

  candidates <- c(
    "scr_amplitude_us",
    "SCR_amplitude_us",
    "peak_amplitude_us",
    "amplitude_us",
    "response_amplitude_us",
    "GSR_US_PHASIC",
    "GSR_US",
    "EDA",
    "eda"
  )

  found <- intersect(candidates, names(dat))

  if (length(found) == 0) {
    stop(
      "No EDA/SCR response column was detected. Supply `response_col` explicitly.",
      call. = FALSE
    )
  }

  found[1]
}

gpbiometrics_eda_bridge_resolve_time_col <- function(dat, time_col = NULL) {
  if (!is.null(time_col)) {
    if (!is.character(time_col) || length(time_col) != 1 || is.na(time_col)) {
      stop("`time_col` must be a single column name.", call. = FALSE)
    }

    if (!time_col %in% names(dat)) {
      stop("Column `", time_col, "` was not found in `data`.", call. = FALSE)
    }

    return(time_col)
  }

  candidates <- c(
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
  )

  found <- intersect(candidates, names(dat))

  if (length(found) == 0) {
    return(NULL)
  }

  found[1]
}

gpbiometrics_eda_bridge_resolve_group_cols <- function(dat, group_cols = NULL) {
  if (is.null(group_cols)) {
    candidates <- c(
      "source_file",
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

    return(intersect(candidates, names(dat)))
  }

  if (!is.character(group_cols)) {
    stop("`group_cols` must be NULL or a character vector of column names.", call. = FALSE)
  }

  missing_cols <- setdiff(group_cols, names(dat))

  if (length(missing_cols) > 0) {
    stop(
      "The following `group_cols` were not found in `data`: ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  group_cols
}

gpbiometrics_eda_bridge_split_data <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(list(groups = list(dat)))
  }

  split_key <- interaction(dat[group_cols], drop = TRUE, lex.order = TRUE)
  groups <- split(dat, split_key, drop = TRUE)

  list(groups = groups)
}

gpbiometrics_eda_bridge_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return("all")
  }

  vals <- vapply(group_cols, function(nm) {
    value <- dat[[nm]][1]
    if (is.na(value)) "<NA>" else as.character(value)
  }, character(1))

  paste(vals, collapse = "||")
}

gpbiometrics_eda_bridge_group_values <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(data.frame(stringsAsFactors = FALSE))
  }

  values <- lapply(group_cols, function(nm) {
    dat[[nm]][1]
  })

  names(values) <- group_cols

  as.data.frame(
    values,
    stringsAsFactors = FALSE,
    optional = TRUE
  )
}

gpbiometrics_eda_bridge_time_seconds <- function(group_dat,
                                                 time_col,
                                                 sampling_rate,
                                                 time_unit) {
  if (is.null(time_col)) {
    time_s <- if (!is.null(sampling_rate)) {
      (seq_len(nrow(group_dat)) - 1) / sampling_rate
    } else {
      rep(NA_real_, nrow(group_dat))
    }

    return(list(
      time_s = time_s,
      detected_time_unit = if (!is.null(sampling_rate)) "sample_index" else "missing_time",
      time_span_s = if (length(time_s) > 1 && any(is.finite(time_s))) {
        max(time_s, na.rm = TRUE) - min(time_s, na.rm = TRUE)
      } else {
        NA_real_
      },
      median_time_step_s = if (length(time_s) > 1) {
        stats::median(diff(time_s), na.rm = TRUE)
      } else {
        NA_real_
      },
      estimated_sampling_rate_hz = if (!is.null(sampling_rate)) sampling_rate else NA_real_
    ))
  }

  time_raw <- suppressWarnings(as.numeric(group_dat[[time_col]]))

  detected_time_unit <- gpbiometrics_eda_bridge_detect_time_unit(
    time_raw = time_raw,
    time_col = time_col,
    time_unit = time_unit,
    sampling_rate = sampling_rate
  )

  finite_time <- time_raw[is.finite(time_raw)]
  time_origin <- if (length(finite_time) > 0) min(finite_time, na.rm = TRUE) else NA_real_

  time_s <- if (identical(detected_time_unit, "ms")) {
    (time_raw - time_origin) / 1000
  } else if (identical(detected_time_unit, "seconds")) {
    time_raw - time_origin
  } else if (identical(detected_time_unit, "samples") && !is.null(sampling_rate)) {
    (time_raw - time_origin) / sampling_rate
  } else {
    rep(NA_real_, length(time_raw))
  }

  finite_time_s <- time_s[is.finite(time_s)]
  time_step <- diff(finite_time_s)

  median_time_step_s <- if (length(time_step) > 0) {
    stats::median(time_step[time_step > 0], na.rm = TRUE)
  } else {
    NA_real_
  }

  estimated_sampling_rate_hz <- if (is.finite(median_time_step_s) && median_time_step_s > 0) {
    1 / median_time_step_s
  } else if (!is.null(sampling_rate)) {
    sampling_rate
  } else {
    NA_real_
  }

  list(
    time_s = time_s,
    detected_time_unit = detected_time_unit,
    time_span_s = if (length(finite_time_s) > 0) {
      max(finite_time_s, na.rm = TRUE) - min(finite_time_s, na.rm = TRUE)
    } else {
      NA_real_
    },
    median_time_step_s = median_time_step_s,
    estimated_sampling_rate_hz = estimated_sampling_rate_hz
  )
}

gpbiometrics_eda_bridge_detect_time_unit <- function(time_raw,
                                                     time_col,
                                                     time_unit,
                                                     sampling_rate) {
  if (!identical(time_unit, "auto")) {
    return(time_unit)
  }

  lower_name <- tolower(time_col)

  if (lower_name %in% c("cnt", "sample", "sample_index")) {
    return("samples")
  }

  if (grepl("ms|millisecond", lower_name)) {
    return("ms")
  }

  if (grepl("sec|second", lower_name)) {
    return("seconds")
  }

  finite_time <- time_raw[is.finite(time_raw)]

  if (length(finite_time) == 0) {
    return(if (!is.null(sampling_rate)) "samples" else "seconds")
  }

  range_time <- diff(range(finite_time, na.rm = TRUE))

  if (is.finite(range_time) && range_time > 1000) {
    "ms"
  } else {
    "seconds"
  }
}

gpbiometrics_eda_bridge_validate_sampling_rate <- function(sampling_rate) {
  if (is.null(sampling_rate)) {
    return(invisible(TRUE))
  }

  if (!is.numeric(sampling_rate) || length(sampling_rate) != 1 ||
      is.na(sampling_rate) || sampling_rate <= 0) {
    stop("`sampling_rate` must be NULL or a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_eda_bridge_validate_min_finite_prop <- function(min_finite_prop) {
  if (!is.numeric(min_finite_prop) || length(min_finite_prop) != 1 ||
      is.na(min_finite_prop) || min_finite_prop < 0 || min_finite_prop > 1) {
    stop("`min_finite_prop` must be a single number between 0 and 1.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_eda_bridge_validate_thresholds <- function(no_response_threshold,
                                                        low_response_threshold,
                                                        moderate_response_threshold) {
  values <- c(no_response_threshold, low_response_threshold, moderate_response_threshold)

  if (!is.numeric(values) || any(!is.finite(values)) || any(values < 0)) {
    stop("Response thresholds must be finite non-negative numbers.", call. = FALSE)
  }

  if (!(no_response_threshold <= low_response_threshold &&
        low_response_threshold <= moderate_response_threshold)) {
    stop(
      "Thresholds must satisfy: no_response_threshold <= low_response_threshold <= moderate_response_threshold.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}

gpbiometrics_eda_bridge_response_label <- function(response_value,
                                                   no_response_threshold,
                                                   low_response_threshold,
                                                   moderate_response_threshold) {
  if (!is.finite(response_value)) {
    return("unclassified_no_finite_response")
  }

  if (response_value <= no_response_threshold) {
    "no_detectable_response"
  } else if (response_value <= low_response_threshold) {
    "low_response"
  } else if (response_value <= moderate_response_threshold) {
    "moderate_response"
  } else {
    "high_response"
  }
}

gpbiometrics_eda_bridge_write_outputs <- function(signal_table,
                                                  group_summary,
                                                  output_dir,
                                                  prefix,
                                                  method) {
  manifest <- data.frame(
    file_role = character(),
    path = character(),
    stringsAsFactors = FALSE
  )

  if (is.null(output_dir)) {
    return(manifest)
  }

  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }

  if (!dir.exists(output_dir)) {
    stop("Could not create `output_dir`: ", output_dir, call. = FALSE)
  }

  signal_path <- file.path(output_dir, paste0(prefix, "_", method, "_signal_table.csv"))
  summary_path <- file.path(output_dir, paste0(prefix, "_", method, "_group_summary.csv"))

  utils::write.csv(signal_table, signal_path, row.names = FALSE)
  utils::write.csv(group_summary, summary_path, row.names = FALSE)

  data.frame(
    file_role = c("signal_table", "group_summary"),
    path = normalizePath(c(signal_path, summary_path), winslash = "/", mustWork = FALSE),
    stringsAsFactors = FALSE
  )
}

gpbiometrics_eda_bridge_rbind <- function(x) {
  x <- x[!vapply(x, is.null, logical(1))]

  if (length(x) == 0) {
    return(data.frame())
  }

  all_names <- unique(unlist(lapply(x, names), use.names = FALSE))

  x <- lapply(x, function(dat) {
    missing_names <- setdiff(all_names, names(dat))

    for (nm in missing_names) {
      dat[[nm]] <- NA
    }

    dat[all_names]
  })

  do.call(rbind, x)
}
