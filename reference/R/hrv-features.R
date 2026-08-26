#' Summarise time-domain HRV features from Gazepoint IBI/RR intervals
#'
#' Computes conservative time-domain HRV-style features from genuine interbeat
#' interval or RR interval columns. The raw Gazepoint `HRV` column is not used
#' as an HRV metric because it is treated as a validity/vendor flag unless
#' independently documented otherwise.
#'
#' The helper computes descriptive features including mean IBI, mean heart rate
#' derived from IBI, SDNN, RMSSD, and pNN50. It does not compute frequency-domain
#' HRV and does not replace specialised ECG/PPG HRV software.
#'
#' @param data A data frame.
#' @param ibi_col Optional IBI/RR interval column. If `NULL`, a likely IBI/RR
#'   column is detected. The raw `HRV` column is never selected automatically.
#' @param group_cols Optional grouping columns, such as participant, stimulus,
#'   trial, or window.
#' @param time_col Optional time/order column used to order IBI values within
#'   each group before calculating successive-difference features.
#' @param ibi_unit Unit of the IBI/RR column. Use `"auto"`, `"seconds"`, or
#'   `"milliseconds"`.
#' @param min_ibi_ms Minimum plausible IBI in milliseconds.
#' @param max_ibi_ms Maximum plausible IBI in milliseconds.
#' @param min_valid_ibi Minimum number of valid IBI values required before a
#'   group is marked as having computed HRV features.
#'
#' @return A list with `overview`, `features`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   participant = "P1",
#'   IBI = c(0.9, 1.0, 1.1, 1.0, 0.95)
#' )
#' summarise_gazepoint_hrv_features(df, group_cols = "participant")
#'
#' @export
summarise_gazepoint_hrv_features <- function(data,
                                             ibi_col = NULL,
                                             group_cols = NULL,
                                             time_col = NULL,
                                             ibi_unit = c("auto", "seconds", "milliseconds"),
                                             min_ibi_ms = 300,
                                             max_ibi_ms = 2000,
                                             min_valid_ibi = 3L) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  ibi_unit <- match.arg(ibi_unit)

  if (!is.null(ibi_col)) {
    .gpbiom_hrv_assert_columns(data, ibi_col, "ibi_col")
    if (length(ibi_col) != 1L) {
      stop("`ibi_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(group_cols)) {
    .gpbiom_hrv_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_hrv_assert_columns(data, time_col, "time_col")
    if (length(time_col) != 1L) {
      stop("`time_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  .gpbiom_hrv_assert_positive_number(min_ibi_ms, "min_ibi_ms")
  .gpbiom_hrv_assert_positive_number(max_ibi_ms, "max_ibi_ms")
  .gpbiom_hrv_assert_positive_integer(min_valid_ibi, "min_valid_ibi")

  if (min_ibi_ms >= max_ibi_ms) {
    stop("`min_ibi_ms` must be smaller than `max_ibi_ms`.", call. = FALSE)
  }

  if (is.null(ibi_col)) {
    ibi_col <- .gpbiom_hrv_choose_ibi_column(data)
  }

  if (is.na(ibi_col) || !ibi_col %in% names(data)) {
    stop(
      "No IBI/RR interval column was detected. Provide `ibi_col` explicitly. ",
      "The raw `HRV` column is not treated as an HRV metric.",
      call. = FALSE
    )
  }

  if (identical(ibi_col, "HRV")) {
    stop(
      "`HRV` is treated as a validity/vendor flag, not as an HRV metric. ",
      "Use a genuine IBI/RR interval column.",
      call. = FALSE
    )
  }

  if (!is.numeric(data[[ibi_col]])) {
    stop("`ibi_col` must be numeric.", call. = FALSE)
  }

  groups <- .gpbiom_hrv_group_indices(data, group_cols)

  feature_rows <- lapply(names(groups), function(group_name) {
    idx <- groups[[group_name]]
    idx <- .gpbiom_hrv_order_index(data, idx, time_col)

    values <- data[[ibi_col]][idx]
    unit <- .gpbiom_hrv_resolve_unit(values, ibi_unit)
    values_ms <- .gpbiom_hrv_to_ms(values, unit)

    .gpbiom_hrv_feature_row(
      group_name = group_name,
      values_ms = values_ms,
      unit = unit,
      min_ibi_ms = min_ibi_ms,
      max_ibi_ms = max_ibi_ms,
      min_valid_ibi = min_valid_ibi
    )
  })

  features <- if (length(feature_rows) == 0L) {
    .gpbiom_hrv_empty_features()
  } else {
    do.call(rbind, feature_rows)
  }

  overview <- data.frame(
    n_rows = nrow(data),
    ibi_col = ibi_col,
    group_count = length(groups),
    feature_rows = nrow(features),
    groups_with_computed_features = sum(features$status == "hrv_features_computed"),
    groups_with_insufficient_ibi = sum(features$status == "insufficient_valid_ibi"),
    total_valid_ibi = sum(features$n_valid_ibi, na.rm = TRUE),
    status = if (any(features$status == "hrv_features_computed")) {
      "hrv_features_available"
    } else {
      "insufficient_valid_ibi"
    },
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    features = features,
    settings = list(
      ibi_col = ibi_col,
      group_cols = group_cols,
      time_col = time_col,
      ibi_unit = ibi_unit,
      min_ibi_ms = min_ibi_ms,
      max_ibi_ms = max_ibi_ms,
      min_valid_ibi = as.integer(min_valid_ibi),
      note = paste0(
        "Time-domain HRV features are derived from IBI/RR intervals only. ",
        "The raw Gazepoint HRV column is treated as a validity/vendor flag."
      )
    )
  )

  class(out) <- c("gazepoint_hrv_features", class(out))
  out
}


.gpbiom_hrv_choose_ibi_column <- function(data) {
  standard_names <- standardise_gazepoint_biometric_names(names(data))

  candidates <- names(data)[standard_names == "IBI"]

  numeric_candidates <- candidates[vapply(candidates, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(numeric_candidates) > 0L) {
    return(numeric_candidates[1L])
  }

  rr_like <- names(data)[grepl(
    "^(IBI|RR|RR_INTERVAL|RR_MS|INTERBEAT|INTER_BEAT)",
    toupper(names(data))
  )]

  rr_like <- rr_like[!toupper(rr_like) %in% "HRV"]

  numeric_rr_like <- rr_like[vapply(rr_like, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(numeric_rr_like) > 0L) {
    return(numeric_rr_like[1L])
  }

  NA_character_
}


.gpbiom_hrv_resolve_unit <- function(values, ibi_unit = "auto") {
  if (!identical(ibi_unit, "auto")) {
    return(ibi_unit)
  }

  finite <- values[is.finite(values)]

  if (length(finite) == 0L) {
    return("unknown")
  }

  median_value <- stats::median(finite)

  if (is.finite(median_value) && median_value > 10) {
    "milliseconds"
  } else {
    "seconds"
  }
}


.gpbiom_hrv_to_ms <- function(values, unit) {
  values <- as.numeric(values)

  if (identical(unit, "milliseconds")) {
    return(values)
  }

  if (identical(unit, "seconds")) {
    return(values * 1000)
  }

  values
}


.gpbiom_hrv_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || length(group_cols) == 0L) {
    return(list(all = seq_len(nrow(data))))
  }

  group_data <- data[group_cols]

  group_key <- apply(group_data, 1, function(row) {
    row <- as.character(row)
    row[is.na(row)] <- "<NA>"
    paste(row, collapse = " | ")
  })

  split(seq_len(nrow(data)), group_key, drop = TRUE)
}


.gpbiom_hrv_order_index <- function(data, idx, time_col = NULL) {
  if (is.null(time_col)) {
    return(idx)
  }

  idx[order(data[[time_col]][idx], na.last = TRUE)]
}


.gpbiom_hrv_feature_row <- function(group_name,
                                    values_ms,
                                    unit,
                                    min_ibi_ms,
                                    max_ibi_ms,
                                    min_valid_ibi) {
  n_total <- length(values_ms)
  missing <- is.na(values_ms) | !is.finite(values_ms)
  finite <- !missing

  out_of_range <- finite & (values_ms < min_ibi_ms | values_ms > max_ibi_ms)
  valid <- finite & !out_of_range

  valid_values <- values_ms[valid]

  n_valid <- length(valid_values)

  diffs <- if (n_valid >= 2L) {
    diff(valid_values)
  } else {
    numeric()
  }

  status <- if (n_valid >= min_valid_ibi) {
    "hrv_features_computed"
  } else {
    "insufficient_valid_ibi"
  }

  data.frame(
    group = group_name,
    n_total_ibi = n_total,
    n_missing_ibi = sum(missing),
    n_out_of_range_ibi = sum(out_of_range),
    n_valid_ibi = n_valid,
    valid_ibi_rate = if (n_total > 0L) n_valid / n_total else NA_real_,
    unit_detected = unit,
    mean_ibi_ms = if (n_valid > 0L) mean(valid_values) else NA_real_,
    median_ibi_ms = if (n_valid > 0L) stats::median(valid_values) else NA_real_,
    sdnn_ms = if (n_valid >= 2L) stats::sd(valid_values) else NA_real_,
    rmssd_ms = if (length(diffs) > 0L) sqrt(mean(diffs^2)) else NA_real_,
    pnn50_percent = if (length(diffs) > 0L) mean(abs(diffs) > 50) * 100 else NA_real_,
    mean_hr_bpm_from_ibi = if (n_valid > 0L) 60000 / mean(valid_values) else NA_real_,
    min_ibi_ms = if (n_valid > 0L) min(valid_values) else NA_real_,
    max_ibi_ms = if (n_valid > 0L) max(valid_values) else NA_real_,
    status = status,
    stringsAsFactors = FALSE
  )
}


.gpbiom_hrv_empty_features <- function() {
  data.frame(
    group = character(),
    n_total_ibi = integer(),
    n_missing_ibi = integer(),
    n_out_of_range_ibi = integer(),
    n_valid_ibi = integer(),
    valid_ibi_rate = numeric(),
    unit_detected = character(),
    mean_ibi_ms = numeric(),
    median_ibi_ms = numeric(),
    sdnn_ms = numeric(),
    rmssd_ms = numeric(),
    pnn50_percent = numeric(),
    mean_hr_bpm_from_ibi = numeric(),
    min_ibi_ms = numeric(),
    max_ibi_ms = numeric(),
    status = character(),
    stringsAsFactors = FALSE
  )
}


.gpbiom_hrv_assert_columns <- function(data, columns, argument) {
  missing <- setdiff(columns, names(data))

  if (length(missing) > 0L) {
    stop(
      "`", argument, "` contains columns not found in `data`: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  invisible(TRUE)
}


.gpbiom_hrv_assert_positive_number <- function(x, argument) {
  if (!is.numeric(x) ||
      length(x) != 1L ||
      is.na(x) ||
      !is.finite(x) ||
      x <= 0) {
    stop("`", argument, "` must be a positive number.", call. = FALSE)
  }

  invisible(TRUE)
}


.gpbiom_hrv_assert_positive_integer <- function(x, argument) {
  if (!is.numeric(x) ||
      length(x) != 1L ||
      is.na(x) ||
      !is.finite(x) ||
      x <= 0 ||
      x != as.integer(x)) {
    stop("`", argument, "` must be a positive integer.", call. = FALSE)
  }

  invisible(TRUE)
}
