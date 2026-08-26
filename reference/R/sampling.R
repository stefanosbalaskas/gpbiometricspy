#' Audit Gazepoint biometric sampling and timing
#'
#' Audits timing or row-order information in Gazepoint Biometrics exports. The
#' function checks monotonicity, duplicate timestamps, nonpositive intervals,
#' and estimated sampling rate when the selected time column has a real time
#' unit. If only `CNT` is available, the function can still check ordering but
#' does not estimate a sampling rate unless `time_unit` is explicitly meaningful.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Optional grouping columns within which timing should be
#'   audited, such as `c("source_participant", "MEDIA_ID")`.
#' @param time_column Optional time/order column. If `NULL`, the function uses
#'   the first available column among `TIME`, `TIME_TICK`, and `CNT`.
#' @param time_unit Unit of the selected time column. Use `"seconds"`,
#'   `"milliseconds"`, `"microseconds"`, or `"samples"`. When `"samples"` is
#'   used, sampling-rate estimates are returned as `NA`.
#' @param expected_rate_hz Optional expected sampling rate in Hz.
#' @param tolerance_hz Acceptable absolute deviation from `expected_rate_hz`.
#'
#' @return A data frame with one row per group.
#'
#' @export
audit_gazepoint_biometric_sampling <- function(data,
                                               group_columns = NULL,
                                               time_column = NULL,
                                               time_unit = c(
                                                 "seconds",
                                                 "milliseconds",
                                                 "microseconds",
                                                 "samples"
                                               ),
                                               expected_rate_hz = 60,
                                               tolerance_hz = 5) {
  dat <- coerce_gazepoint_biometrics_data(data)
  time_unit <- match.arg(time_unit)

  if (is.null(time_column)) {
    time_column <- choose_first_present(dat, c("TIME", "TIME_TICK", "CNT"))
  }

  if (is.null(time_column) || length(time_column) != 1L || is.na(time_column)) {
    stop("No timing/order column was found in `data`.", call. = FALSE)
  }

  if (!time_column %in% names(dat)) {
    stop("`time_column` was not found in `data`: ", time_column, call. = FALSE)
  }

  if (!is.null(group_columns)) {
    missing_groups <- setdiff(group_columns, names(dat))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_columns` were not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }

    group_key <- make_group_key(dat, group_columns)
  } else {
    group_key <- rep("all", nrow(dat))
  }

  rows <- lapply(unique(group_key), function(key) {
    in_group <- group_key == key
    source_rows <- which(in_group)

    group_values <- if (!is.null(group_columns)) {
      dat[source_rows[1], group_columns, drop = FALSE]
    } else {
      data.frame(group = "all", stringsAsFactors = FALSE)
    }

    time_values <- as_numeric_safe(dat[[time_column]][in_group])

    summary <- summarise_sampling_vector(
      time_values = time_values,
      time_column = time_column,
      time_unit = time_unit,
      expected_rate_hz = expected_rate_hz,
      tolerance_hz = tolerance_hz
    )

    cbind(group_values, summary, stringsAsFactors = FALSE)
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}


summarise_sampling_vector <- function(time_values,
                                      time_column,
                                      time_unit,
                                      expected_rate_hz,
                                      tolerance_hz) {
  non_missing <- !is.na(time_values)
  usable_time <- time_values[non_missing]

  intervals <- diff(usable_time)

  positive_intervals <- intervals[!is.na(intervals) & intervals > 0]

  estimated_rate_hz <- NA_real_
  median_interval_seconds <- NA_real_

  if (length(positive_intervals) > 0L && time_unit != "samples") {
    interval_seconds <- convert_interval_to_seconds(
      positive_intervals,
      time_unit = time_unit
    )

    median_interval_seconds <- stats::median(interval_seconds)

    if (!is.na(median_interval_seconds) && median_interval_seconds > 0) {
      estimated_rate_hz <- 1 / median_interval_seconds
    }
  }

  rate_deviation_hz <- ifelse(
    !is.na(estimated_rate_hz) && !is.null(expected_rate_hz) && !is.na(expected_rate_hz),
    estimated_rate_hz - expected_rate_hz,
    NA_real_
  )

  rate_status <- classify_sampling_rate(
    estimated_rate_hz = estimated_rate_hz,
    expected_rate_hz = expected_rate_hz,
    tolerance_hz = tolerance_hz
  )

  data.frame(
    time_column = time_column,
    time_unit = time_unit,
    n_rows = length(time_values),
    non_missing_time_rows = sum(non_missing),
    missing_time_rows = sum(!non_missing),
    missing_time_pct = safe_pct(sum(!non_missing), length(time_values)),
    duplicate_time_rows = sum(duplicated(usable_time)),
    interval_rows = length(intervals),
    positive_interval_rows = length(positive_intervals),
    zero_interval_rows = sum(!is.na(intervals) & intervals == 0),
    negative_interval_rows = sum(!is.na(intervals) & intervals < 0),
    monotonic_non_decreasing = all(intervals >= 0, na.rm = TRUE),
    strictly_increasing = all(intervals > 0, na.rm = TRUE),
    median_interval_seconds = median_interval_seconds,
    estimated_rate_hz = estimated_rate_hz,
    expected_rate_hz = expected_rate_hz,
    rate_deviation_hz = rate_deviation_hz,
    rate_status = rate_status,
    stringsAsFactors = FALSE
  )
}


convert_interval_to_seconds <- function(intervals,
                                        time_unit) {
  if (time_unit == "seconds") {
    return(intervals)
  }

  if (time_unit == "milliseconds") {
    return(intervals / 1000)
  }

  if (time_unit == "microseconds") {
    return(intervals / 1000000)
  }

  rep(NA_real_, length(intervals))
}


classify_sampling_rate <- function(estimated_rate_hz,
                                   expected_rate_hz,
                                   tolerance_hz) {
  if (is.na(estimated_rate_hz)) {
    return("not_estimated")
  }

  if (is.null(expected_rate_hz) || is.na(expected_rate_hz)) {
    return("estimated")
  }

  if (abs(estimated_rate_hz - expected_rate_hz) <= tolerance_hz) {
    return("within_tolerance")
  }

  "outside_tolerance"
}
