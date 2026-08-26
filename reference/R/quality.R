#' Audit Gazepoint GSR/EDA signal quality
#'
#' Audits Gazepoint GSR/EDA columns for missingness, inactive zero rows,
#' validity flags, plausible value ranges, flatlining, and usable sample
#' coverage. When available, `GSR_US` is used by default because it represents
#' skin conductance in microsiemens in Gazepoint exports.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param value_column Optional GSR/EDA value column. If `NULL`, `GSR_US` is
#'   used when present, otherwise `GSR`.
#' @param validity_column Optional validity column. Defaults to `"GSRV"`.
#' @param min_value Minimum plausible value.
#' @param max_value Maximum plausible value.
#' @param jump_threshold Optional threshold for detecting large sample-to-sample
#'   jumps.
#'
#' @return A one-row data frame summarising signal quality.
#'
#' @export
audit_gazepoint_gsr_quality <- function(data,
                                        value_column = NULL,
                                        validity_column = "GSRV",
                                        min_value = 0,
                                        max_value = 100,
                                        jump_threshold = NULL) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (is.null(value_column)) {
    value_column <- choose_first_present(dat, c("GSR_US", "GSR"))
  }

  audit_gazepoint_signal_quality(
    data = dat,
    signal = "gsr_eda",
    value_column = value_column,
    validity_column = validity_column,
    min_value = min_value,
    max_value = max_value,
    jump_threshold = jump_threshold
  )
}


#' Audit Gazepoint heart-rate signal quality
#'
#' Audits Gazepoint heart-rate values for missingness, inactive zero rows,
#' validity flags, plausible value ranges, sudden jumps, flatlining, and usable
#' sample coverage. `HRV` is treated as the heart-rate validity flag, not as a
#' heart-rate-variability metric.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param value_column Heart-rate value column. Defaults to `"HR"`.
#' @param validity_column Heart-rate validity column. Defaults to `"HRV"`.
#' @param min_value Minimum plausible heart rate.
#' @param max_value Maximum plausible heart rate.
#' @param jump_threshold Threshold for detecting large sample-to-sample jumps.
#'
#' @return A one-row data frame summarising signal quality.
#'
#' @export
audit_gazepoint_hr_quality <- function(data,
                                       value_column = "HR",
                                       validity_column = "HRV",
                                       min_value = 30,
                                       max_value = 220,
                                       jump_threshold = 25) {
  dat <- coerce_gazepoint_biometrics_data(data)

  audit_gazepoint_signal_quality(
    data = dat,
    signal = "heart_rate",
    value_column = value_column,
    validity_column = validity_column,
    min_value = min_value,
    max_value = max_value,
    jump_threshold = jump_threshold
  )
}


#' Audit Gazepoint engagement-dial signal quality
#'
#' Audits Gazepoint engagement-dial values for missingness, inactive rows,
#' validity flags, plausible range, flatlining, and usable sample coverage.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param value_column Engagement-dial value column. Defaults to `"DIAL"`.
#' @param validity_column Engagement-dial validity column. Defaults to
#'   `"DIALV"`.
#' @param min_value Minimum plausible dial value.
#' @param max_value Maximum plausible dial value.
#' @param jump_threshold Optional threshold for detecting large sample-to-sample
#'   jumps.
#'
#' @return A one-row data frame summarising signal quality.
#'
#' @export
audit_gazepoint_engagement_dial <- function(data,
                                            value_column = "DIAL",
                                            validity_column = "DIALV",
                                            min_value = 0,
                                            max_value = 1,
                                            jump_threshold = NULL) {
  dat <- coerce_gazepoint_biometrics_data(data)

  audit_gazepoint_signal_quality(
    data = dat,
    signal = "engagement_dial",
    value_column = value_column,
    validity_column = validity_column,
    min_value = min_value,
    max_value = max_value,
    jump_threshold = jump_threshold
  )
}


audit_gazepoint_signal_quality <- function(data,
                                           signal,
                                           value_column,
                                           validity_column = NULL,
                                           min_value = -Inf,
                                           max_value = Inf,
                                           jump_threshold = NULL) {
  if (is.null(value_column) || length(value_column) != 1L || is.na(value_column)) {
    return(empty_signal_quality(signal, value_column, validity_column, nrow(data)))
  }

  if (!value_column %in% names(data)) {
    return(empty_signal_quality(signal, value_column, validity_column, nrow(data)))
  }

  x <- as_numeric_safe(data[[value_column]])

  missing_rows <- sum(is.na(x))
  zero_rows <- sum(!is.na(x) & x == 0)
  nonzero_rows <- sum(!is.na(x) & x != 0)

  valid <- !is.na(x)

  if (!is.null(validity_column) && validity_column %in% names(data)) {
    v <- as_numeric_safe(data[[validity_column]])
    valid <- valid & !is.na(v) & v > 0
  }

  low <- !is.na(x) & x < min_value
  high <- !is.na(x) & x > max_value

  usable <- valid & !low & !high

  usable_values <- x[usable]

  large_jump_rows <- NA_integer_

  if (!is.null(jump_threshold) && length(usable_values) > 1L) {
    large_jump_rows <- sum(abs(diff(usable_values)) > jump_threshold, na.rm = TRUE)
  }

  flatline <- FALSE

  if (length(usable_values) > 1L) {
    flatline <- length(unique(usable_values)) == 1L
  }

  data.frame(
    signal = signal,
    issue = NA_character_,
    value_column = value_column,
    validity_column = ifelse(
      !is.null(validity_column) && validity_column %in% names(data),
      validity_column,
      NA_character_
    ),
    n_rows = length(x),
    missing_rows = missing_rows,
    missing_pct = safe_pct(missing_rows, length(x)),
    zero_rows = zero_rows,
    zero_pct = safe_pct(zero_rows, length(x)),
    nonzero_rows = nonzero_rows,
    valid_rows = sum(valid),
    invalid_rows = length(x) - sum(valid),
    low_rows = sum(low),
    high_rows = sum(high),
    large_jump_rows = large_jump_rows,
    flatline = flatline,
    usable_rows = length(usable_values),
    usable_pct = safe_pct(length(usable_values), length(x)),
    min_value = ifelse(length(usable_values) > 0L, min(usable_values), NA_real_),
    max_value = ifelse(length(usable_values) > 0L, max(usable_values), NA_real_),
    mean_value = ifelse(length(usable_values) > 0L, mean(usable_values), NA_real_),
    stringsAsFactors = FALSE
  )
}


empty_signal_quality <- function(signal,
                                 value_column,
                                 validity_column,
                                 n_rows) {
  data.frame(
    signal = signal,
    issue = "value_column_missing",
    value_column = ifelse(is.null(value_column), NA_character_, value_column),
    validity_column = ifelse(is.null(validity_column), NA_character_, validity_column),
    n_rows = n_rows,
    missing_rows = NA_integer_,
    missing_pct = NA_real_,
    zero_rows = NA_integer_,
    zero_pct = NA_real_,
    nonzero_rows = NA_integer_,
    valid_rows = NA_integer_,
    invalid_rows = NA_integer_,
    low_rows = NA_integer_,
    high_rows = NA_integer_,
    large_jump_rows = NA_integer_,
    flatline = NA,
    usable_rows = 0L,
    usable_pct = 0,
    min_value = NA_real_,
    max_value = NA_real_,
    mean_value = NA_real_,
    stringsAsFactors = FALSE
  )
}


choose_first_present <- function(data, columns) {
  present <- intersect(columns, names(data))

  if (length(present) == 0L) {
    return(NA_character_)
  }

  present[1]
}
