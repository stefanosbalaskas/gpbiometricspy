#' Audit IBI/RR interval quality
#'
#' Audits inter-beat interval (IBI) or RR-interval values in Gazepoint
#' Biometrics-style exports. This helper deliberately does not use raw `HRV`
#' columns as HRV metrics. HRV-style summaries should be derived only from
#' genuine IBI/RR interval columns.
#'
#' @param data A data frame.
#' @param ibi_col Optional IBI/RR interval column. If `NULL`, the function
#'   detects recognised IBI/RR-style column names.
#' @param group_cols Optional grouping columns, such as participant, trial,
#'   stimulus, condition, or window labels.
#' @param time_col Optional time/order column used to order samples before
#'   successive-difference checks.
#' @param unit Unit of the IBI values. `"auto"` treats median values below 10 as
#'   seconds and larger values as milliseconds.
#' @param min_ibi_ms Minimum plausible IBI in milliseconds.
#' @param max_ibi_ms Maximum plausible IBI in milliseconds.
#' @param max_jump_ms Maximum plausible absolute change between successive IBI
#'   values within a group.
#'
#' @return A list with `overview`, `samples`, `group_summary`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   USER = rep(c("P1", "P2"), each = 4),
#'   IBI = c(800, 810, 790, 805, 900, 910, 905, 920)
#' )
#' audit_gazepoint_ibi_quality(df, group_cols = "USER")
#'
#' @export
audit_gazepoint_ibi_quality <- function(data,
                                        ibi_col = NULL,
                                        group_cols = NULL,
                                        time_col = NULL,
                                        unit = c("auto", "milliseconds", "seconds"),
                                        min_ibi_ms = 300,
                                        max_ibi_ms = 2000,
                                        max_jump_ms = 500) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  unit <- match.arg(unit)

  if (!is.null(ibi_col)) {
    .gpbiom_assert_columns(data, ibi_col, "ibi_col")
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
  }

  .gpbiom_assert_positive_number(min_ibi_ms, "min_ibi_ms")
  .gpbiom_assert_positive_number(max_ibi_ms, "max_ibi_ms")
  .gpbiom_assert_positive_number(max_jump_ms, "max_jump_ms")

  if (min_ibi_ms >= max_ibi_ms) {
    stop("`min_ibi_ms` must be smaller than `max_ibi_ms`.", call. = FALSE)
  }

  source_col <- if (is.null(ibi_col)) {
    .gpbiom_choose_ibi_column(data)
  } else {
    ibi_col
  }

  if (is.na(source_col)) {
    stop(
      "No IBI/RR interval column was detected. Provide `ibi_col` explicitly.",
      call. = FALSE
    )
  }

  if (!is.numeric(data[[source_col]])) {
    stop("The selected IBI/RR interval column must be numeric.", call. = FALSE)
  }

  resolved_unit <- .gpbiom_resolve_ibi_unit(data[[source_col]], unit)
  ibi_ms <- .gpbiom_ibi_to_ms(data[[source_col]], resolved_unit)

  sample_table <- data.frame(
    row_id = seq_len(nrow(data)),
    group = .gpbiom_group_labels(data, group_cols),
    ibi_raw = data[[source_col]],
    ibi_ms = ibi_ms,
    missing_ibi = is.na(data[[source_col]]),
    nonfinite_ibi = !is.na(data[[source_col]]) & !is.finite(data[[source_col]]),
    nonpositive_ibi = !is.na(ibi_ms) & is.finite(ibi_ms) & ibi_ms <= 0,
    below_min_ibi = !is.na(ibi_ms) & is.finite(ibi_ms) & ibi_ms > 0 &
      ibi_ms < min_ibi_ms,
    above_max_ibi = !is.na(ibi_ms) & is.finite(ibi_ms) &
      ibi_ms > max_ibi_ms,
    large_jump_ibi = FALSE,
    stringsAsFactors = FALSE
  )

  groups <- .gpbiom_group_indices(data, group_cols)

  for (indices in groups) {
    ordered_indices <- .gpbiom_order_indices(data, indices, time_col)
    ordered_ibi <- sample_table$ibi_ms[ordered_indices]

    jump_flags <- .gpbiom_ibi_large_jump_flags(
      values = ordered_ibi,
      max_jump_ms = max_jump_ms
    )

    sample_table$large_jump_ibi[ordered_indices] <- jump_flags
  }

  sample_table$valid_ibi <- !sample_table$missing_ibi &
    !sample_table$nonfinite_ibi &
    !sample_table$nonpositive_ibi &
    !sample_table$below_min_ibi &
    !sample_table$above_max_ibi

  sample_table$any_quality_flag <- sample_table$missing_ibi |
    sample_table$nonfinite_ibi |
    sample_table$nonpositive_ibi |
    sample_table$below_min_ibi |
    sample_table$above_max_ibi |
    sample_table$large_jump_ibi

  sample_table$status <- ifelse(
    sample_table$missing_ibi,
    "missing_ibi",
    ifelse(
      sample_table$nonfinite_ibi,
      "nonfinite_ibi",
      ifelse(
        sample_table$nonpositive_ibi,
        "nonpositive_ibi",
        ifelse(
          sample_table$below_min_ibi,
          "below_min_ibi",
          ifelse(
            sample_table$above_max_ibi,
            "above_max_ibi",
            ifelse(
              sample_table$large_jump_ibi,
              "large_jump_ibi",
              "valid_ibi"
            )
          )
        )
      )
    )
  )

  group_summary <- .gpbiom_ibi_group_summary(
    sample_table = sample_table,
    group_cols = group_cols,
    min_valid_ibi = 2L
  )

  n_valid <- sum(sample_table$valid_ibi, na.rm = TRUE)
  n_quality_flagged <- sum(sample_table$any_quality_flag, na.rm = TRUE)

  overview <- data.frame(
    n_rows = nrow(data),
    ibi_column = source_col,
    unit = resolved_unit,
    group_column_count = length(group_cols),
    n_missing_ibi = sum(sample_table$missing_ibi, na.rm = TRUE),
    n_nonfinite_ibi = sum(sample_table$nonfinite_ibi, na.rm = TRUE),
    n_nonpositive_ibi = sum(sample_table$nonpositive_ibi, na.rm = TRUE),
    n_below_min_ibi = sum(sample_table$below_min_ibi, na.rm = TRUE),
    n_above_max_ibi = sum(sample_table$above_max_ibi, na.rm = TRUE),
    n_large_jump_ibi = sum(sample_table$large_jump_ibi, na.rm = TRUE),
    n_valid_ibi = n_valid,
    valid_ibi_rate = if (nrow(data) > 0L) n_valid / nrow(data) else NA_real_,
    n_quality_flagged = n_quality_flagged,
    quality_flag_rate = if (nrow(data) > 0L) {
      n_quality_flagged / nrow(data)
    } else {
      NA_real_
    },
    status = if (n_valid == 0L) {
      "no_valid_ibi_intervals"
    } else if (n_quality_flagged > 0L) {
      "ibi_quality_issues_detected"
    } else {
      "ibi_quality_ok"
    },
    stringsAsFactors = FALSE
  )

  settings <- list(
    ibi_col = source_col,
    group_cols = group_cols,
    time_col = time_col,
    unit = unit,
    resolved_unit = resolved_unit,
    min_ibi_ms = min_ibi_ms,
    max_ibi_ms = max_ibi_ms,
    max_jump_ms = max_jump_ms,
    note = paste0(
      "IBI quality and HRV-style summaries are based only on the selected ",
      "IBI/RR interval column, not on raw HRV validity/vendor columns."
    )
  )

  list(
    overview = overview,
    samples = sample_table,
    group_summary = group_summary,
    settings = settings
  )
}


#' Summarise IBI/RR windows
#'
#' Computes descriptive IBI/RR interval and simple HRV-style window summaries
#' from genuine inter-beat interval data. The function does not use raw `HRV`
#' columns as HRV metrics. It calculates metrics such as mean IBI, mean
#' instantaneous heart rate, SDNN, RMSSD, pNN20, and pNN50 only from valid IBI/RR
#' intervals.
#'
#' @param data A data frame.
#' @param ibi_col Optional IBI/RR interval column. If `NULL`, the function
#'   detects recognised IBI/RR-style column names.
#' @param group_cols Optional grouping columns defining windows, such as
#'   participant, trial, stimulus, condition, or window labels.
#' @param time_col Optional time/order column used to order IBI values before
#'   successive-difference metrics are computed.
#' @param unit Unit of the IBI values. `"auto"` treats median values below 10 as
#'   seconds and larger values as milliseconds.
#' @param min_ibi_ms Minimum plausible IBI in milliseconds.
#' @param max_ibi_ms Maximum plausible IBI in milliseconds.
#' @param max_jump_ms Maximum plausible absolute change between successive IBI
#'   values within a group.
#' @param exclude_large_jumps Logical. Should intervals flagged as large jumps be
#'   excluded from the window summaries?
#' @param min_valid_ibi Minimum valid IBI count required for a window to be marked
#'   as sufficient.
#'
#' @return A list with `overview`, `windows`, `samples`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   USER = rep(c("P1", "P2"), each = 4),
#'   IBI = c(800, 810, 790, 805, 900, 910, 905, 920)
#' )
#' summarise_gazepoint_ibi_windows(df, group_cols = "USER")
#'
#' @export
summarise_gazepoint_ibi_windows <- function(data,
                                            ibi_col = NULL,
                                            group_cols = NULL,
                                            time_col = NULL,
                                            unit = c("auto", "milliseconds", "seconds"),
                                            min_ibi_ms = 300,
                                            max_ibi_ms = 2000,
                                            max_jump_ms = 500,
                                            exclude_large_jumps = TRUE,
                                            min_valid_ibi = 2L) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  unit <- match.arg(unit)

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
  }

  if (!is.logical(exclude_large_jumps) ||
      length(exclude_large_jumps) != 1L ||
      is.na(exclude_large_jumps)) {
    stop("`exclude_large_jumps` must be TRUE or FALSE.", call. = FALSE)
  }

  .gpbiom_assert_positive_integer(min_valid_ibi, "min_valid_ibi")

  audit <- audit_gazepoint_ibi_quality(
    data = data,
    ibi_col = ibi_col,
    group_cols = group_cols,
    time_col = time_col,
    unit = unit,
    min_ibi_ms = min_ibi_ms,
    max_ibi_ms = max_ibi_ms,
    max_jump_ms = max_jump_ms
  )

  samples <- audit$samples
  samples$analysis_valid_ibi <- samples$valid_ibi

  if (isTRUE(exclude_large_jumps)) {
    samples$analysis_valid_ibi <- samples$analysis_valid_ibi &
      !samples$large_jump_ibi
  }

  windows <- .gpbiom_ibi_window_summary(
    sample_table = samples,
    group_cols = group_cols,
    min_valid_ibi = as.integer(min_valid_ibi)
  )

  n_sufficient <- sum(windows$status == "sufficient_ibi_window", na.rm = TRUE)

  overview <- data.frame(
    n_rows = nrow(data),
    ibi_column = audit$overview$ibi_column,
    unit = audit$overview$unit,
    window_count = nrow(windows),
    sufficient_window_count = n_sufficient,
    insufficient_window_count = nrow(windows) - n_sufficient,
    exclude_large_jumps = exclude_large_jumps,
    min_valid_ibi = as.integer(min_valid_ibi),
    status = if (nrow(windows) == 0L) {
      "no_ibi_windows"
    } else if (n_sufficient == 0L) {
      "no_sufficient_ibi_windows"
    } else if (n_sufficient < nrow(windows)) {
      "some_ibi_windows_insufficient"
    } else {
      "ibi_windows_summarised"
    },
    stringsAsFactors = FALSE
  )

  settings <- list(
    ibi_col = audit$overview$ibi_column,
    group_cols = group_cols,
    time_col = time_col,
    unit = unit,
    resolved_unit = audit$overview$unit,
    min_ibi_ms = min_ibi_ms,
    max_ibi_ms = max_ibi_ms,
    max_jump_ms = max_jump_ms,
    exclude_large_jumps = exclude_large_jumps,
    min_valid_ibi = as.integer(min_valid_ibi),
    note = paste0(
      "Window summaries are derived from genuine IBI/RR intervals only. ",
      "They are not calculated from raw HRV validity/vendor columns."
    )
  )

  list(
    overview = overview,
    windows = windows,
    samples = samples,
    settings = settings
  )
}


.gpbiom_assert_positive_number <- function(x, argument_name) {
  if (!is.numeric(x) ||
      length(x) != 1L ||
      is.na(x) ||
      !is.finite(x) ||
      x <= 0) {
    stop("`", argument_name, "` must be a positive number.", call. = FALSE)
  }

  invisible(TRUE)
}


.gpbiom_choose_ibi_column <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)
  candidates <- mapping$original_name[mapping$standard_name == "IBI"]

  if (length(candidates) == 0L) {
    return(NA_character_)
  }

  numeric_candidates <- candidates[vapply(candidates, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(numeric_candidates) > 0L) {
    return(numeric_candidates[1L])
  }

  candidates[1L]
}


.gpbiom_resolve_ibi_unit <- function(values, unit) {
  if (identical(unit, "milliseconds")) {
    return("milliseconds")
  }

  if (identical(unit, "seconds")) {
    return("seconds")
  }

  finite <- values[!is.na(values) & is.finite(values) & values > 0]

  if (length(finite) == 0L) {
    return("milliseconds")
  }

  if (stats::median(finite) < 10) {
    "seconds"
  } else {
    "milliseconds"
  }
}


.gpbiom_ibi_to_ms <- function(values, unit) {
  if (identical(unit, "seconds")) {
    return(values * 1000)
  }

  values
}


.gpbiom_group_labels <- function(data, group_cols) {
  if (length(group_cols) == 0L) {
    return(rep("all", nrow(data)))
  }

  as.character(interaction(data[group_cols], drop = TRUE, lex.order = TRUE))
}


.gpbiom_ibi_large_jump_flags <- function(values, max_jump_ms) {
  flags <- rep(FALSE, length(values))

  if (length(values) < 2L) {
    return(flags)
  }

  valid <- !is.na(values) & is.finite(values) & values > 0

  for (i in 2:length(values)) {
    if (valid[i] && valid[i - 1L]) {
      flags[i] <- abs(values[i] - values[i - 1L]) > max_jump_ms
    }
  }

  flags
}


.gpbiom_ibi_group_summary <- function(sample_table,
                                      group_cols,
                                      min_valid_ibi) {
  groups <- split(seq_len(nrow(sample_table)), sample_table$group)

  rows <- lapply(names(groups), function(group_name) {
    rows <- sample_table[groups[[group_name]], , drop = FALSE]
    valid <- rows$ibi_ms[rows$valid_ibi]

    metrics <- .gpbiom_ibi_metrics(valid)

    data.frame(
      group = group_name,
      n_rows = nrow(rows),
      n_valid_ibi = length(valid),
      valid_ibi_rate = if (nrow(rows) > 0L) length(valid) / nrow(rows) else NA_real_,
      n_quality_flagged = sum(rows$any_quality_flag, na.rm = TRUE),
      quality_flag_rate = if (nrow(rows) > 0L) {
        mean(rows$any_quality_flag, na.rm = TRUE)
      } else {
        NA_real_
      },
      mean_ibi_ms = metrics$mean_ibi_ms,
      median_ibi_ms = metrics$median_ibi_ms,
      mean_hr_bpm = metrics$mean_hr_bpm,
      sdnn_ms = metrics$sdnn_ms,
      rmssd_ms = metrics$rmssd_ms,
      pnn50 = metrics$pnn50,
      status = if (length(valid) >= min_valid_ibi) {
        "sufficient_ibi"
      } else {
        "insufficient_ibi"
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_ibi_window_summary <- function(sample_table,
                                       group_cols,
                                       min_valid_ibi) {
  groups <- split(seq_len(nrow(sample_table)), sample_table$group)

  rows <- lapply(names(groups), function(group_name) {
    rows <- sample_table[groups[[group_name]], , drop = FALSE]
    valid <- rows$ibi_ms[rows$analysis_valid_ibi]

    metrics <- .gpbiom_ibi_metrics(valid)

    data.frame(
      group = group_name,
      n_rows = nrow(rows),
      n_ibi = sum(!rows$missing_ibi, na.rm = TRUE),
      n_valid_ibi = length(valid),
      valid_ibi_rate = if (nrow(rows) > 0L) length(valid) / nrow(rows) else NA_real_,
      n_excluded_for_quality = sum(!rows$analysis_valid_ibi, na.rm = TRUE),
      duration_s = if (length(valid) > 0L) sum(valid) / 1000 else NA_real_,
      mean_ibi_ms = metrics$mean_ibi_ms,
      median_ibi_ms = metrics$median_ibi_ms,
      min_ibi_ms = metrics$min_ibi_ms,
      max_ibi_ms = metrics$max_ibi_ms,
      mean_hr_bpm = metrics$mean_hr_bpm,
      median_hr_bpm = metrics$median_hr_bpm,
      min_hr_bpm = metrics$min_hr_bpm,
      max_hr_bpm = metrics$max_hr_bpm,
      sdnn_ms = metrics$sdnn_ms,
      rmssd_ms = metrics$rmssd_ms,
      pnn20 = metrics$pnn20,
      pnn50 = metrics$pnn50,
      status = if (length(valid) >= min_valid_ibi) {
        "sufficient_ibi_window"
      } else {
        "insufficient_ibi_window"
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_ibi_metrics <- function(ibi_ms) {
  ibi_ms <- ibi_ms[!is.na(ibi_ms) & is.finite(ibi_ms) & ibi_ms > 0]

  hr <- 60000 / ibi_ms
  diffs <- diff(ibi_ms)

  list(
    mean_ibi_ms = if (length(ibi_ms) > 0L) mean(ibi_ms) else NA_real_,
    median_ibi_ms = if (length(ibi_ms) > 0L) stats::median(ibi_ms) else NA_real_,
    min_ibi_ms = if (length(ibi_ms) > 0L) min(ibi_ms) else NA_real_,
    max_ibi_ms = if (length(ibi_ms) > 0L) max(ibi_ms) else NA_real_,
    mean_hr_bpm = if (length(hr) > 0L) mean(hr) else NA_real_,
    median_hr_bpm = if (length(hr) > 0L) stats::median(hr) else NA_real_,
    min_hr_bpm = if (length(hr) > 0L) min(hr) else NA_real_,
    max_hr_bpm = if (length(hr) > 0L) max(hr) else NA_real_,
    sdnn_ms = if (length(ibi_ms) > 1L) stats::sd(ibi_ms) else NA_real_,
    rmssd_ms = if (length(diffs) > 0L) sqrt(mean(diffs^2)) else NA_real_,
    pnn20 = if (length(diffs) > 0L) mean(abs(diffs) > 20) else NA_real_,
    pnn50 = if (length(diffs) > 0L) mean(abs(diffs) > 50) else NA_real_
  )
}
