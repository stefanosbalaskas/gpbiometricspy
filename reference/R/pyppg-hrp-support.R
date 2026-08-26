#' Prepare Gazepoint HRP/PPG waveform input for pyPPG
#'
#' Prepares a Gazepoint heart-rate pulse waveform column, usually `HRP`, as a
#' lightweight input table for optional pyPPG workflows. This helper does not
#' call Python, does not require pyPPG, and does not derive HRV features. It only
#' prepares waveform values, timing information when available, and conservative
#' group-level summaries for interoperability review.
#'
#' @param data A Gazepoint biometric data frame or a list containing one.
#' @param ppg_col Optional HRP/PPG waveform column. If `NULL`, common Gazepoint
#'   HRP/PPG column names are detected.
#' @param time_col Optional time, timestamp, or sample-counter column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz. Useful when `time_col`
#'   is a sample counter such as `CNT`.
#' @param time_unit Unit of `time_col`: `"auto"`, `"ms"`, `"seconds"`, or
#'   `"samples"`.
#' @param min_finite_prop Minimum finite waveform proportion used for group
#'   readiness summaries.
#' @param output_dir Optional directory for CSV export. If `NULL`, no files are
#'   written.
#' @param prefix File prefix used when `output_dir` is supplied.
#'
#' @return A list with `overview`, `waveform_table`, `group_summary`,
#'   `manifest`, and `settings`.
#' @export
prepare_gazepoint_pyppg_input <- function(data,
                                          ppg_col = NULL,
                                          time_col = NULL,
                                          group_cols = NULL,
                                          sampling_rate = NULL,
                                          time_unit = c("auto", "ms", "seconds", "samples"),
                                          min_finite_prop = 0.50,
                                          output_dir = NULL,
                                          prefix = "gazepoint_pyppg") {
  time_unit <- match.arg(time_unit)

  dat <- gpbiometrics_pyppg_extract_data(data)
  names_dat <- names(dat)

  if (!is.null(sampling_rate)) {
    gpbiometrics_pyppg_validate_positive_scalar(sampling_rate, "sampling_rate")
  }

  if (!is.numeric(min_finite_prop) ||
      length(min_finite_prop) != 1 ||
      is.na(min_finite_prop) ||
      min_finite_prop < 0 ||
      min_finite_prop > 1) {
    stop("`min_finite_prop` must be a single number between 0 and 1.", call. = FALSE)
  }

  if (is.null(ppg_col)) {
    ppg_col <- gpbiometrics_pyppg_first_existing(
      names_dat,
      c("HRP", "hrp", "PPG", "ppg", "pulse", "pulse_wave", "ppg_signal")
    )
  }

  if (is.null(ppg_col) || !ppg_col %in% names_dat) {
    stop("No usable HRP/PPG waveform column was found. Supply `ppg_col`.", call. = FALSE)
  }

  if (is.null(time_col)) {
    time_col <- gpbiometrics_pyppg_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (!is.null(time_col) && !time_col %in% names_dat) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_pyppg_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  dat$.gpbiometrics_group_id <- gpbiometrics_pyppg_group_id(dat, group_cols)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  group_indices <- split(seq_len(nrow(dat)), dat$.gpbiometrics_group_id, drop = TRUE)

  waveform_parts <- list()
  summary_parts <- list()

  for (group_id in names(group_indices)) {
    idx <- group_indices[[group_id]]
    d <- dat[idx, , drop = FALSE]
    group_values <- gpbiometrics_pyppg_group_values(d, group_cols)

    ppg_value <- suppressWarnings(as.numeric(d[[ppg_col]]))

    timing <- gpbiometrics_pyppg_resolve_timing(
      d = d,
      time_col = time_col,
      sampling_rate = sampling_rate,
      time_unit = time_unit
    )

    waveform <- data.frame(
      group_id = group_id,
      sample_index = seq_len(nrow(d)),
      source_row = d$.gpbiometrics_row_id,
      time_raw = timing$time_raw,
      time_s = timing$time_s,
      ppg_signal = ppg_value,
      ppg_col = ppg_col,
      detected_time_unit = timing$detected_time_unit,
      stringsAsFactors = FALSE
    )

    waveform <- gpbiometrics_pyppg_prepend_group_values(group_values, waveform)
    waveform_parts[[length(waveform_parts) + 1L]] <- waveform

    finite_ppg <- ppg_value[is.finite(ppg_value)]
    finite_prop <- if (length(ppg_value) > 0) {
      length(finite_ppg) / length(ppg_value)
    } else {
      NA_real_
    }

    status <- if (length(ppg_value) == 0) {
      "empty_group"
    } else if (!is.finite(finite_prop) || finite_prop < min_finite_prop) {
      "insufficient_finite_waveform"
    } else if (all(is.na(timing$time_s))) {
      "prepared_with_sample_index_only"
    } else {
      "ready_for_pyppg_input"
    }

    summary_row <- data.frame(
      group_id = group_id,
      ppg_col = ppg_col,
      n_rows = nrow(d),
      n_finite = length(finite_ppg),
      finite_prop = finite_prop,
      ppg_min = if (length(finite_ppg)) min(finite_ppg) else NA_real_,
      ppg_median = if (length(finite_ppg)) stats::median(finite_ppg) else NA_real_,
      ppg_max = if (length(finite_ppg)) max(finite_ppg) else NA_real_,
      ppg_sd = if (length(finite_ppg) > 1) stats::sd(finite_ppg) else NA_real_,
      time_col = if (is.null(time_col)) NA_character_ else time_col,
      detected_time_unit = timing$detected_time_unit,
      time_span_s = timing$time_span_s,
      median_time_step_s = timing$median_time_step_s,
      estimated_sampling_rate_hz = timing$estimated_sampling_rate_hz,
      status = status,
      interpretation = gpbiometrics_pyppg_status_interpretation(status),
      stringsAsFactors = FALSE
    )

    summary_parts[[length(summary_parts) + 1L]] <-
      gpbiometrics_pyppg_prepend_group_values(group_values, summary_row)
  }

  waveform_table <- gpbiometrics_pyppg_rbind(waveform_parts)
  group_summary <- gpbiometrics_pyppg_rbind(summary_parts)

  manifest <- gpbiometrics_pyppg_write_outputs(
    waveform_table = waveform_table,
    group_summary = group_summary,
    output_dir = output_dir,
    prefix = prefix
  )

  ready_groups <- sum(group_summary$status %in% c(
    "ready_for_pyppg_input",
    "prepared_with_sample_index_only"
  ), na.rm = TRUE)

  overview_status <- if (nrow(dat) == 0) {
    "empty_input"
  } else if (ready_groups == nrow(group_summary)) {
    "pyppg_input_prepared"
  } else if (ready_groups > 0) {
    "partial_pyppg_input_prepared"
  } else {
    "pyppg_input_not_ready"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = nrow(group_summary),
    ready_group_count = as.integer(ready_groups),
    ppg_col = ppg_col,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    output_file_count = nrow(manifest),
    status = overview_status,
    interpretation = paste(
      "Output is prepared waveform input for optional pyPPG-style workflows.",
      "No Python dependency is invoked and no HRV or physiological diagnosis is inferred."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      waveform_table = waveform_table,
      group_summary = group_summary,
      manifest = manifest,
      settings = list(
        ppg_col = ppg_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        time_unit = time_unit,
        min_finite_prop = min_finite_prop,
        output_dir = output_dir,
        prefix = prefix
      )
    ),
    class = c("gazepoint_pyppg_input", "list")
  )
}

#' Assess Gazepoint HRP waveform quality
#'
#' Computes descriptive quality-control summaries for a Gazepoint HRP/PPG
#' waveform column. The output is intended for waveform availability,
#' missingness, flatness, and timing-gap review. It does not infer diagnosis,
#' emotion, valence, cognition, preference, or true physiological state.
#'
#' @param data A Gazepoint biometric data frame or a list containing one.
#' @param hrp_col Optional HRP/PPG waveform column. If `NULL`, common column
#'   names are detected.
#' @param time_col Optional time, timestamp, or sample-counter column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz.
#' @param time_unit Unit of `time_col`: `"auto"`, `"ms"`, `"seconds"`, or
#'   `"samples"`.
#' @param min_rows Minimum rows required per group.
#' @param min_finite_prop Minimum finite waveform proportion required per group.
#' @param max_flat_prop Maximum allowed proportion of near-zero consecutive
#'   differences among finite waveform values.
#' @param flat_tolerance Absolute difference threshold used to identify near-flat
#'   consecutive waveform changes.
#' @param max_gap_multiplier Time gaps larger than this multiple of the median
#'   positive time step are flagged.
#'
#' @return A list with `overview`, `group_quality`, `row_flags`, and `settings`.
#' @export
assess_gazepoint_hrp_waveform_quality <- function(data,
                                                  hrp_col = NULL,
                                                  time_col = NULL,
                                                  group_cols = NULL,
                                                  sampling_rate = NULL,
                                                  time_unit = c("auto", "ms", "seconds", "samples"),
                                                  min_rows = 20,
                                                  min_finite_prop = 0.80,
                                                  max_flat_prop = 0.95,
                                                  flat_tolerance = 1e-8,
                                                  max_gap_multiplier = 3) {
  time_unit <- match.arg(time_unit)

  dat <- gpbiometrics_pyppg_extract_data(data)
  names_dat <- names(dat)

  gpbiometrics_pyppg_validate_positive_scalar(min_rows, "min_rows")
  gpbiometrics_pyppg_validate_proportion(min_finite_prop, "min_finite_prop")
  gpbiometrics_pyppg_validate_proportion(max_flat_prop, "max_flat_prop")
  gpbiometrics_pyppg_validate_nonnegative_scalar(flat_tolerance, "flat_tolerance")
  gpbiometrics_pyppg_validate_positive_scalar(max_gap_multiplier, "max_gap_multiplier")

  if (!is.null(sampling_rate)) {
    gpbiometrics_pyppg_validate_positive_scalar(sampling_rate, "sampling_rate")
  }

  if (is.null(hrp_col)) {
    hrp_col <- gpbiometrics_pyppg_first_existing(
      names_dat,
      c("HRP", "hrp", "PPG", "ppg", "pulse", "pulse_wave", "ppg_signal")
    )
  }

  if (is.null(hrp_col) || !hrp_col %in% names_dat) {
    stop("No usable HRP/PPG waveform column was found. Supply `hrp_col`.", call. = FALSE)
  }

  if (is.null(time_col)) {
    time_col <- gpbiometrics_pyppg_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (!is.null(time_col) && !time_col %in% names_dat) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_pyppg_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  dat$.gpbiometrics_group_id <- gpbiometrics_pyppg_group_id(dat, group_cols)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  group_indices <- split(seq_len(nrow(dat)), dat$.gpbiometrics_group_id, drop = TRUE)

  quality_parts <- list()
  flag_parts <- list()

  for (group_id in names(group_indices)) {
    idx <- group_indices[[group_id]]
    d <- dat[idx, , drop = FALSE]
    group_values <- gpbiometrics_pyppg_group_values(d, group_cols)

    hrp_value <- suppressWarnings(as.numeric(d[[hrp_col]]))

    timing <- gpbiometrics_pyppg_resolve_timing(
      d = d,
      time_col = time_col,
      sampling_rate = sampling_rate,
      time_unit = time_unit
    )

    finite_hrp <- hrp_value[is.finite(hrp_value)]
    finite_prop <- if (length(hrp_value) > 0) {
      length(finite_hrp) / length(hrp_value)
    } else {
      NA_real_
    }

    diffs <- diff(finite_hrp)
    zero_diff_prop <- if (length(diffs) > 0) {
      mean(abs(diffs) <= flat_tolerance)
    } else {
      NA_real_
    }

    missing_flags <- !is.finite(hrp_value)

    time_gap_flags <- gpbiometrics_pyppg_large_gap_flags(
      time_s = timing$time_s,
      max_gap_multiplier = max_gap_multiplier
    )

    longest_missing_run <- gpbiometrics_pyppg_longest_true_run(missing_flags)

    status <- gpbiometrics_pyppg_quality_status(
      n_rows = nrow(d),
      finite_prop = finite_prop,
      n_unique_finite = length(unique(finite_hrp)),
      zero_diff_prop = zero_diff_prop,
      n_large_time_gaps = sum(time_gap_flags, na.rm = TRUE),
      min_rows = min_rows,
      min_finite_prop = min_finite_prop,
      max_flat_prop = max_flat_prop
    )

    quality_row <- data.frame(
      group_id = group_id,
      hrp_col = hrp_col,
      n_rows = nrow(d),
      n_finite = length(finite_hrp),
      finite_prop = finite_prop,
      missing_prop = if (length(hrp_value) > 0) mean(!is.finite(hrp_value)) else NA_real_,
      n_unique_finite = length(unique(finite_hrp)),
      hrp_min = if (length(finite_hrp)) min(finite_hrp) else NA_real_,
      hrp_median = if (length(finite_hrp)) stats::median(finite_hrp) else NA_real_,
      hrp_max = if (length(finite_hrp)) max(finite_hrp) else NA_real_,
      hrp_sd = if (length(finite_hrp) > 1) stats::sd(finite_hrp) else NA_real_,
      hrp_iqr = if (length(finite_hrp) > 1) stats::IQR(finite_hrp) else NA_real_,
      median_abs_diff = if (length(diffs) > 0) stats::median(abs(diffs)) else NA_real_,
      zero_diff_prop = zero_diff_prop,
      longest_missing_run = as.integer(longest_missing_run),
      n_large_time_gaps = as.integer(sum(time_gap_flags, na.rm = TRUE)),
      time_col = if (is.null(time_col)) NA_character_ else time_col,
      detected_time_unit = timing$detected_time_unit,
      median_time_step_s = timing$median_time_step_s,
      estimated_sampling_rate_hz = timing$estimated_sampling_rate_hz,
      status = status,
      interpretation = gpbiometrics_pyppg_quality_interpretation(status),
      stringsAsFactors = FALSE
    )

    quality_parts[[length(quality_parts) + 1L]] <-
      gpbiometrics_pyppg_prepend_group_values(group_values, quality_row)

    row_flags <- data.frame(
      group_id = group_id,
      source_row = d$.gpbiometrics_row_id,
      sample_index = seq_len(nrow(d)),
      hrp_value = hrp_value,
      time_s = timing$time_s,
      flag_missing_or_nonfinite_hrp = missing_flags,
      flag_large_time_gap = time_gap_flags,
      stringsAsFactors = FALSE
    )

    flag_parts[[length(flag_parts) + 1L]] <-
      gpbiometrics_pyppg_prepend_group_values(group_values, row_flags)
  }

  group_quality <- gpbiometrics_pyppg_rbind(quality_parts)
  row_flags <- gpbiometrics_pyppg_rbind(flag_parts)

  fail_count <- sum(grepl("^fail_", group_quality$status), na.rm = TRUE)
  review_count <- sum(grepl("^review_", group_quality$status), na.rm = TRUE)
  pass_count <- sum(group_quality$status == "descriptive_quality_pass", na.rm = TRUE)

  final_status <- if (nrow(dat) == 0) {
    "empty_input"
  } else if (fail_count > 0) {
    "fail_review_required"
  } else if (review_count > 0) {
    "review_recommended"
  } else {
    "pass"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = nrow(group_quality),
    pass_group_count = as.integer(pass_count),
    review_group_count = as.integer(review_count),
    fail_group_count = as.integer(fail_count),
    hrp_col = hrp_col,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    status = final_status,
    interpretation = paste(
      "HRP waveform quality is summarized descriptively for QC.",
      "The helper does not infer diagnosis, emotion, valence, cognition, trust, preference, or true physiological state."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      group_quality = group_quality,
      row_flags = row_flags,
      settings = list(
        hrp_col = hrp_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        time_unit = time_unit,
        min_rows = min_rows,
        min_finite_prop = min_finite_prop,
        max_flat_prop = max_flat_prop,
        flat_tolerance = flat_tolerance,
        max_gap_multiplier = max_gap_multiplier
      )
    ),
    class = c("gazepoint_hrp_waveform_quality", "list")
  )
}

gpbiometrics_pyppg_extract_data <- function(data) {
  if (is.data.frame(data)) {
    return(as.data.frame(data, stringsAsFactors = FALSE))
  }

  if (is.list(data)) {
    candidates <- c(
      "data",
      "biometrics",
      "merged_data",
      "all_data",
      "imported_data",
      "raw_data",
      "combined_data"
    )

    for (nm in candidates) {
      if (!is.null(data[[nm]]) && is.data.frame(data[[nm]])) {
        return(as.data.frame(data[[nm]], stringsAsFactors = FALSE))
      }
    }

    data_frame_items <- vapply(data, is.data.frame, logical(1))

    if (any(data_frame_items)) {
      return(as.data.frame(data[[which(data_frame_items)[1]]], stringsAsFactors = FALSE))
    }
  }

  stop("`data` must be a data frame or a list containing a data frame.", call. = FALSE)
}

gpbiometrics_pyppg_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]

  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

gpbiometrics_pyppg_resolve_group_cols <- function(names_dat, group_cols) {
  if (!is.null(group_cols)) {
    group_cols <- as.character(group_cols)
    group_cols <- group_cols[!is.na(group_cols) & nzchar(group_cols)]
    return(unique(group_cols))
  }

  candidates <- c(
    "source_file",
    "source_participant",
    "participant",
    "subject",
    "subject_id",
    "USER",
    "USER_FILE",
    "MEDIA_ID",
    "MEDIA_NAME",
    "stimulus",
    "stimulus_id",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_pyppg_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_pyppg_group_values <- function(dat, group_cols) {
  if (length(group_cols) == 0 || nrow(dat) == 0) {
    return(NULL)
  }

  out <- as.data.frame(dat[1, group_cols, drop = FALSE], stringsAsFactors = FALSE)
  rownames(out) <- NULL
  out
}

gpbiometrics_pyppg_prepend_group_values <- function(group_values, row) {
  row <- as.data.frame(row, stringsAsFactors = FALSE)
  rownames(row) <- NULL

  if (is.null(group_values) || ncol(group_values) == 0) {
    return(row)
  }

  group_values <- as.data.frame(group_values, stringsAsFactors = FALSE)
  rownames(group_values) <- NULL

  group_values <- group_values[rep(1, nrow(row)), , drop = FALSE]
  rownames(group_values) <- NULL

  cbind(group_values, row, stringsAsFactors = FALSE)
}

gpbiometrics_pyppg_rbind <- function(x) {
  x <- x[!vapply(x, is.null, logical(1))]

  if (length(x) == 0) {
    return(data.frame(stringsAsFactors = FALSE))
  }

  out <- do.call(rbind, x)
  rownames(out) <- NULL
  out
}

gpbiometrics_pyppg_resolve_timing <- function(d,
                                              time_col = NULL,
                                              sampling_rate = NULL,
                                              time_unit = "auto") {
  if (is.null(time_col)) {
    time_raw <- seq_len(nrow(d))
    detected_time_unit <- if (is.null(sampling_rate)) {
      "sample_index"
    } else {
      "samples"
    }
  } else {
    time_raw <- suppressWarnings(as.numeric(d[[time_col]]))
    detected_time_unit <- gpbiometrics_pyppg_detect_time_unit(
      time_raw = time_raw,
      time_col = time_col,
      sampling_rate = sampling_rate,
      time_unit = time_unit
    )
  }

  finite_time <- time_raw[is.finite(time_raw)]

  time_s <- rep(NA_real_, length(time_raw))

  if (length(finite_time) > 0) {
    time_origin <- min(finite_time)

    if (identical(detected_time_unit, "ms")) {
      time_s <- (time_raw - time_origin) / 1000
    } else if (identical(detected_time_unit, "seconds")) {
      time_s <- time_raw - time_origin
    } else if (identical(detected_time_unit, "samples") && !is.null(sampling_rate)) {
      time_s <- (time_raw - time_origin) / sampling_rate
    }
  }

  finite_time_s <- time_s[is.finite(time_s)]
  time_span_s <- if (length(finite_time_s) > 1) {
    max(finite_time_s) - min(finite_time_s)
  } else {
    NA_real_
  }

  positive_steps <- diff(sort(unique(finite_time_s)))
  positive_steps <- positive_steps[is.finite(positive_steps) & positive_steps > 0]

  median_time_step_s <- if (length(positive_steps) > 0) {
    stats::median(positive_steps)
  } else {
    NA_real_
  }

  estimated_sampling_rate_hz <- if (!is.null(sampling_rate)) {
    sampling_rate
  } else if (is.finite(median_time_step_s) && median_time_step_s > 0) {
    1 / median_time_step_s
  } else {
    NA_real_
  }

  list(
    time_raw = time_raw,
    time_s = time_s,
    detected_time_unit = detected_time_unit,
    time_span_s = time_span_s,
    median_time_step_s = median_time_step_s,
    estimated_sampling_rate_hz = estimated_sampling_rate_hz
  )
}

gpbiometrics_pyppg_detect_time_unit <- function(time_raw,
                                                time_col = NULL,
                                                sampling_rate = NULL,
                                                time_unit = "auto") {
  if (!identical(time_unit, "auto")) {
    return(time_unit)
  }

  lower_col <- tolower(if (is.null(time_col)) "" else time_col)

  if (grepl("cnt|sample", lower_col)) {
    return("samples")
  }

  if (grepl("ms|millisecond", lower_col)) {
    return("ms")
  }

  if (grepl("sec|second", lower_col)) {
    return("seconds")
  }

  finite_time <- sort(unique(time_raw[is.finite(time_raw)]))

  if (length(finite_time) < 2) {
    return(if (is.null(sampling_rate)) "seconds" else "samples")
  }

  positive_steps <- diff(finite_time)
  positive_steps <- positive_steps[is.finite(positive_steps) & positive_steps > 0]

  if (length(positive_steps) == 0) {
    return(if (is.null(sampling_rate)) "seconds" else "samples")
  }

  median_step <- stats::median(positive_steps)

  if (median_step > 10) {
    "ms"
  } else {
    "seconds"
  }
}

gpbiometrics_pyppg_status_interpretation <- function(status) {
  switch(
    status,
    empty_group = "No rows were available for this group.",
    insufficient_finite_waveform = "The waveform has too few finite values for reliable pyPPG input preparation.",
    prepared_with_sample_index_only = paste(
      "A waveform table was prepared, but time in seconds could not be derived.",
      "Supply `sampling_rate` for sample-counter based pyPPG workflows."
    ),
    ready_for_pyppg_input = paste(
      "Waveform and timing columns were prepared for optional pyPPG-style input.",
      "External pyPPG processing remains optional and is not run by gpbiometrics."
    ),
    "Waveform input status was not recognized."
  )
}

gpbiometrics_pyppg_write_outputs <- function(waveform_table,
                                             group_summary,
                                             output_dir = NULL,
                                             prefix = "gazepoint_pyppg") {
  manifest <- data.frame(
    item = character(),
    path = character(),
    rows = integer(),
    status = character(),
    stringsAsFactors = FALSE
  )

  if (is.null(output_dir)) {
    return(manifest)
  }

  if (!is.character(output_dir) || length(output_dir) != 1 || is.na(output_dir) || !nzchar(output_dir)) {
    stop("`output_dir` must be NULL or a single non-empty character value.", call. = FALSE)
  }

  if (!is.character(prefix) || length(prefix) != 1 || is.na(prefix) || !nzchar(prefix)) {
    stop("`prefix` must be a single non-empty character value.", call. = FALSE)
  }

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  waveform_path <- file.path(output_dir, paste0(prefix, "_waveform_table.csv"))
  summary_path <- file.path(output_dir, paste0(prefix, "_group_summary.csv"))

  utils::write.csv(waveform_table, waveform_path, row.names = FALSE)
  utils::write.csv(group_summary, summary_path, row.names = FALSE)

  manifest <- rbind(
    manifest,
    data.frame(
      item = "waveform_table",
      path = normalizePath(waveform_path, winslash = "/", mustWork = FALSE),
      rows = nrow(waveform_table),
      status = "written",
      stringsAsFactors = FALSE
    ),
    data.frame(
      item = "group_summary",
      path = normalizePath(summary_path, winslash = "/", mustWork = FALSE),
      rows = nrow(group_summary),
      status = "written",
      stringsAsFactors = FALSE
    )
  )

  rownames(manifest) <- NULL
  manifest
}

gpbiometrics_pyppg_large_gap_flags <- function(time_s, max_gap_multiplier = 3) {
  out <- rep(FALSE, length(time_s))

  finite_time <- time_s[is.finite(time_s)]

  if (length(finite_time) < 3) {
    return(out)
  }

  steps <- diff(time_s)
  positive_steps <- steps[is.finite(steps) & steps > 0]

  if (length(positive_steps) == 0) {
    return(out)
  }

  median_step <- stats::median(positive_steps)

  if (!is.finite(median_step) || median_step <= 0) {
    return(out)
  }

  gap <- c(FALSE, steps > max_gap_multiplier * median_step)
  gap[is.na(gap)] <- FALSE
  gap
}

gpbiometrics_pyppg_longest_true_run <- function(x) {
  x <- as.logical(x)
  x[is.na(x)] <- FALSE

  if (length(x) == 0 || !any(x)) {
    return(0L)
  }

  r <- rle(x)
  as.integer(max(r$lengths[r$values]))
}

gpbiometrics_pyppg_quality_status <- function(n_rows,
                                              finite_prop,
                                              n_unique_finite,
                                              zero_diff_prop,
                                              n_large_time_gaps,
                                              min_rows,
                                              min_finite_prop,
                                              max_flat_prop) {
  if (n_rows < min_rows) {
    return("fail_insufficient_rows")
  }

  if (!is.finite(finite_prop) || finite_prop < min_finite_prop) {
    return("fail_low_finite_signal")
  }

  if (n_unique_finite < 3) {
    return("review_flat_signal")
  }

  if (is.finite(zero_diff_prop) && zero_diff_prop > max_flat_prop) {
    return("review_low_variability")
  }

  if (n_large_time_gaps > 0) {
    return("review_time_gaps")
  }

  "descriptive_quality_pass"
}

gpbiometrics_pyppg_quality_interpretation <- function(status) {
  switch(
    status,
    fail_insufficient_rows = "Too few rows were available for descriptive HRP waveform QC.",
    fail_low_finite_signal = "The HRP waveform has too many missing or nonfinite values for descriptive QC.",
    review_flat_signal = "The HRP waveform has very low uniqueness and should be manually reviewed.",
    review_low_variability = "The HRP waveform has a high proportion of near-flat consecutive changes.",
    review_time_gaps = "The timing trace contains large gaps relative to the local sampling interval.",
    descriptive_quality_pass = paste(
      "Basic descriptive HRP waveform checks passed.",
      "This is a QC summary only and does not establish physiological validity."
    ),
    "HRP waveform quality status was not recognized."
  )
}

gpbiometrics_pyppg_validate_positive_scalar <- function(x, arg) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x <= 0) {
    stop("`", arg, "` must be a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_pyppg_validate_nonnegative_scalar <- function(x, arg) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x < 0) {
    stop("`", arg, "` must be a single non-negative number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_pyppg_validate_proportion <- function(x, arg) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x < 0 || x > 1) {
    stop("`", arg, "` must be a single number between 0 and 1.", call. = FALSE)
  }

  invisible(TRUE)
}
