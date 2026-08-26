#' Baseline-correct Gazepoint GSR/EDA
#'
#' Adds a baseline-corrected GSR/EDA column to a Gazepoint Biometrics table.
#' When available, `GSR_US` is used by default because it represents skin
#' conductance in microsiemens in Gazepoint exports. The baseline is estimated
#' from rows selected by `baseline_rows`, optionally within groups.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param baseline_rows Logical vector identifying baseline rows.
#' @param value_column Optional GSR/EDA value column. If `NULL`, `GSR_US` is
#'   used when present, otherwise `GSR`.
#' @param validity_column Optional validity column. Defaults to `"GSRV"`.
#' @param group_columns Optional grouping columns. When supplied, baselines are
#'   estimated separately within each group.
#' @param output_column Name of the corrected output column.
#' @param summary Baseline summary, either `"mean"` or `"median"`.
#' @param exclude_zero Should zero values be excluded from baseline estimation?
#'
#' @return A data frame with the added baseline-corrected column and a
#'   baseline-summary attribute named `"baseline_summary"`.
#'
#' @export
baseline_correct_gazepoint_gsr <- function(data,
                                           baseline_rows,
                                           value_column = NULL,
                                           validity_column = "GSRV",
                                           group_columns = NULL,
                                           output_column = NULL,
                                           summary = c("mean", "median"),
                                           exclude_zero = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (is.null(value_column)) {
    value_column <- choose_first_present(dat, c("GSR_US", "GSR"))
  }

  if (is.null(output_column)) {
    output_column <- paste0(value_column, "_baseline_corrected")
  }

  baseline_correct_gazepoint_signal(
    data = dat,
    baseline_rows = baseline_rows,
    value_column = value_column,
    validity_column = validity_column,
    group_columns = group_columns,
    output_column = output_column,
    summary = summary,
    exclude_zero = exclude_zero
  )
}


#' Baseline-correct Gazepoint heart rate
#'
#' Adds a baseline-corrected heart-rate column to a Gazepoint Biometrics table.
#' `HRV` is treated as the heart-rate validity flag, not as a heart-rate
#' variability metric.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param baseline_rows Logical vector identifying baseline rows.
#' @param value_column Heart-rate value column. Defaults to `"HR"`.
#' @param validity_column Heart-rate validity column. Defaults to `"HRV"`.
#' @param group_columns Optional grouping columns. When supplied, baselines are
#'   estimated separately within each group.
#' @param output_column Name of the corrected output column.
#' @param summary Baseline summary, either `"mean"` or `"median"`.
#' @param exclude_zero Should zero values be excluded from baseline estimation?
#'
#' @return A data frame with the added baseline-corrected column and a
#'   baseline-summary attribute named `"baseline_summary"`.
#'
#' @export
baseline_correct_gazepoint_hr <- function(data,
                                          baseline_rows,
                                          value_column = "HR",
                                          validity_column = "HRV",
                                          group_columns = NULL,
                                          output_column = NULL,
                                          summary = c("mean", "median"),
                                          exclude_zero = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (is.null(output_column)) {
    output_column <- paste0(value_column, "_baseline_corrected")
  }

  baseline_correct_gazepoint_signal(
    data = dat,
    baseline_rows = baseline_rows,
    value_column = value_column,
    validity_column = validity_column,
    group_columns = group_columns,
    output_column = output_column,
    summary = summary,
    exclude_zero = exclude_zero
  )
}


#' Smooth a Gazepoint biometric signal
#'
#' Adds a simple centered moving-average smoothing column to a Gazepoint
#' Biometrics table. This is intentionally conservative and dependency-free.
#' It does not replace specialised biosignal preprocessing libraries.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param value_column Column to smooth.
#' @param window Number of samples in the moving window. Must be a positive odd
#'   integer.
#' @param output_column Name of the smoothed output column.
#' @param na_rm Should missing values be ignored within the moving window?
#'
#' @return A data frame with the added smoothed column.
#'
#' @export
smooth_gazepoint_biometrics <- function(data,
                                        value_column,
                                        window = 5L,
                                        output_column = NULL,
                                        na_rm = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (missing(value_column) || length(value_column) != 1L || !nzchar(value_column)) {
    stop("`value_column` must be a single non-empty column name.", call. = FALSE)
  }

  if (!value_column %in% names(dat)) {
    stop("`value_column` was not found in `data`: ", value_column, call. = FALSE)
  }

  if (length(window) != 1L || is.na(window) || window < 1L || window %% 2L == 0L) {
    stop("`window` must be a positive odd integer.", call. = FALSE)
  }

  if (is.null(output_column)) {
    output_column <- paste0(value_column, "_smoothed")
  }

  x <- as_numeric_safe(dat[[value_column]])

  dat[[output_column]] <- centered_moving_average(
    x = x,
    window = as.integer(window),
    na_rm = na_rm
  )

  dat
}


baseline_correct_gazepoint_signal <- function(data,
                                              baseline_rows,
                                              value_column,
                                              validity_column = NULL,
                                              group_columns = NULL,
                                              output_column,
                                              summary = c("mean", "median"),
                                              exclude_zero = TRUE) {
  summary <- match.arg(summary)

  if (is.null(value_column) || length(value_column) != 1L || is.na(value_column)) {
    stop("`value_column` could not be determined.", call. = FALSE)
  }

  if (!value_column %in% names(data)) {
    stop("`value_column` was not found in `data`: ", value_column, call. = FALSE)
  }

  if (!is.logical(baseline_rows) || length(baseline_rows) != nrow(data)) {
    stop(
      "`baseline_rows` must be a logical vector with length equal to nrow(data).",
      call. = FALSE
    )
  }

  if (!is.null(group_columns)) {
    missing_groups <- setdiff(group_columns, names(data))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_columns` were not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }
  }

  x <- as_numeric_safe(data[[value_column]])

  valid <- !is.na(x)

  if (isTRUE(exclude_zero)) {
    valid <- valid & x != 0
  }

  if (!is.null(validity_column) && validity_column %in% names(data)) {
    v <- as_numeric_safe(data[[validity_column]])
    valid <- valid & !is.na(v) & v > 0
  }

  baseline_eligible <- baseline_rows & valid

  if (is.null(group_columns)) {
    baseline_value <- compute_baseline_value(x[baseline_eligible], summary)

    corrected <- x - baseline_value

    baseline_summary <- data.frame(
      group = "all",
      value_column = value_column,
      validity_column = ifelse(
        !is.null(validity_column) && validity_column %in% names(data),
        validity_column,
        NA_character_
      ),
      baseline_rows = sum(baseline_rows),
      baseline_usable_rows = sum(baseline_eligible),
      baseline_value = baseline_value,
      summary = summary,
      stringsAsFactors = FALSE
    )
  } else {
    group_key <- make_group_key(data, group_columns)
    corrected <- rep(NA_real_, length(x))

    baseline_summary <- lapply(unique(group_key), function(key) {
      in_group <- group_key == key
      eligible <- baseline_eligible & in_group
      baseline_value <- compute_baseline_value(x[eligible], summary)

      corrected[in_group] <<- x[in_group] - baseline_value

      data.frame(
        group = key,
        value_column = value_column,
        validity_column = ifelse(
          !is.null(validity_column) && validity_column %in% names(data),
          validity_column,
          NA_character_
        ),
        baseline_rows = sum(baseline_rows & in_group),
        baseline_usable_rows = sum(eligible),
        baseline_value = baseline_value,
        summary = summary,
        stringsAsFactors = FALSE
      )
    })

    baseline_summary <- do.call(rbind, baseline_summary)
    rownames(baseline_summary) <- NULL
  }

  data[[output_column]] <- corrected

  attr(data, "baseline_summary") <- baseline_summary

  data
}


compute_baseline_value <- function(x, summary) {
  x <- x[!is.na(x)]

  if (length(x) == 0L) {
    return(NA_real_)
  }

  if (identical(summary, "median")) {
    return(stats::median(x))
  }

  mean(x)
}


make_group_key <- function(data, group_columns) {
  if (length(group_columns) == 1L) {
    return(as.character(data[[group_columns]]))
  }

  do.call(
    paste,
    c(data[group_columns], sep = "\r")
  )
}


centered_moving_average <- function(x, window, na_rm = TRUE) {
  n <- length(x)
  half_window <- floor(window / 2L)
  out <- rep(NA_real_, n)

  for (i in seq_len(n)) {
    from <- max(1L, i - half_window)
    to <- min(n, i + half_window)

    values <- x[from:to]

    if (isTRUE(na_rm)) {
      values <- values[!is.na(values)]
    }

    if (length(values) == 0L || any(is.na(values))) {
      out[i] <- NA_real_
    } else {
      out[i] <- mean(values)
    }
  }

  out
}
