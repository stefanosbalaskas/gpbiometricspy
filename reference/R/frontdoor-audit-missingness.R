
# Front-door audit and missingness helpers for Gazepoint biometric workflows.

.gp_front_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_front_detect_sep <- function(path) {
  first <- readLines(path, n = 1L, warn = FALSE)

  if (!length(first)) {
    return(",")
  }

  counts <- c(
    comma = lengths(regmatches(first, gregexpr(",", first, fixed = TRUE))),
    semicolon = lengths(regmatches(first, gregexpr(";", first, fixed = TRUE))),
    tab = lengths(regmatches(first, gregexpr("\t", first, fixed = TRUE)))
  )

  switch(
    names(which.max(counts)),
    comma = ",",
    semicolon = ";",
    tab = "\t",
    ","
  )
}

.gp_front_read_table <- function(path) {
  if (!is.character(path) || length(path) != 1L || !file.exists(path)) {
    stop("`path` must be an existing file path.", call. = FALSE)
  }

  utils::read.table(
    path,
    sep = .gp_front_detect_sep(path),
    header = TRUE,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    comment.char = ""
  )
}

.gp_front_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(time)
  }

  d <- diff(time[is.finite(time)])
  d <- d[is.finite(d) & d > 0]

  if (!length(d)) {
    return(time)
  }

  med_d <- stats::median(d, na.rm = TRUE)

  if (is.finite(med_d) && med_d > 5) {
    time / 1000
  } else {
    time
  }
}

.gp_front_guess_time_col <- function(data, required = FALSE) {
  candidates <- c("time_s", "time", "timestamp", "TIME", "TIME_TICK", "MSTIMER", "CNT")
  idx <- match(tolower(candidates), tolower(names(data)))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(names(data)[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify a time column. Supply `time_col` explicitly.", call. = FALSE)
  }

  NULL
}

.gp_front_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_front_missing_runs <- function(missing, time = NULL) {
  missing[is.na(missing)] <- FALSE

  if (!any(missing)) {
    return(data.frame(
      run_id = integer(),
      start_index = integer(),
      end_index = integer(),
      length_samples = integer(),
      duration_s = numeric()
    ))
  }

  r <- rle(missing)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L
  keep <- which(r$values)

  duration <- rep(NA_real_, length(keep))

  if (!is.null(time)) {
    time <- .gp_front_time_seconds(time)
    finite_time <- time[is.finite(time)]
    d <- diff(finite_time)
    d <- d[is.finite(d) & d > 0]
    med_d <- if (length(d)) stats::median(d, na.rm = TRUE) else NA_real_

    for (i in seq_along(keep)) {
      s <- starts[keep[i]]
      e <- ends[keep[i]]

      if (is.finite(time[s]) && is.finite(time[e]) && is.finite(med_d)) {
        duration[i] <- max(0, time[e] - time[s]) + med_d
      }
    }
  }

  data.frame(
    run_id = seq_along(keep),
    start_index = starts[keep],
    end_index = ends[keep],
    length_samples = r$lengths[keep],
    duration_s = duration,
    stringsAsFactors = FALSE
  )
}

.gp_front_modality_map <- function() {
  list(
    time = c("time_s", "time", "timestamp", "MSTIMER", "TIME", "CNT"),
    eda = c("GSR", "EDA", "skin_conductance", "conductance", "GSR_US"),
    ppg = c("PPG", "BVP", "HRP", "pulse", "bvp", "ppg"),
    hr = c("HR", "heart_rate", "heartrate", "bpm"),
    ibi = c("IBI", "RRI", "RR", "NN", "ibi_ms", "rr_ms"),
    pupil = c("pupil_left", "pupil_right", "LPD", "RPD", "LPMM", "RPMM"),
    gaze = c("gaze_x", "gaze_y", "BPOGX", "BPOGY", "FPOGX", "FPOGY", "GPOGX", "GPOGY"),
    aoi = c("AOI", "aoi", "AOI_NAME", "aoi_name", "area_of_interest"),
    fixation = c("fixation_id", "fix_id", "FPOGID", "fixation"),
    events = c("TTL", "TTL0", "TTL1", "marker", "event_marker", "event_id", "event_time", "USER", "USER_DATA"),
    dial = c("DIAL", "dial", "engagement", "engagement_dial"),
    temperature = c("EDT", "temperature", "temp", "TEMP", "hand_temperature")
  )
}

.gp_front_detect_modalities <- function(data) {
  nms <- names(data)
  nms_lower <- tolower(nms)
  map <- .gp_front_modality_map()

  rows <- vector("list", length(map))

  for (i in seq_along(map)) {
    aliases <- unique(map[[i]])
    hits <- nms[nms_lower %in% tolower(aliases)]

    rows[[i]] <- data.frame(
      modality = names(map)[i],
      present = length(hits) > 0L,
      n_columns = length(hits),
      columns = paste(hits, collapse = ", "),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

.gp_front_as_warning_vector <- function(x) {
  x <- x[!is.na(x) & nzchar(x)]
  unique(as.character(x))
}

#' Summarize missingness and gap structure in Gazepoint data
#'
#' Computes missingness rates, missing-run counts, longest missing run, longest
#' missing duration, and optional long-gap counts for one or more columns. This
#' is intended as a reviewer-friendly audit helper before interpolation,
#' exclusion, or event-locked analysis.
#'
#' @param data Data frame containing signal columns.
#' @param signal_cols Optional character vector of columns to audit. If omitted,
#'   all columns except `time_col` and `group_cols` are audited.
#' @param time_col Optional time column. If supplied or detected, missing-run
#'   durations are reported in seconds.
#' @param group_cols Optional grouping columns such as participant, session, or
#'   trial.
#' @param long_gap_s Optional threshold in seconds used to count long missing
#'   gaps.
#' @param count_nonfinite If TRUE, non-finite numeric values are counted as
#'   missing.
#'
#' @return Data frame with one row per group and signal column.
#' @export
summarize_gazepoint_missingness <- function(data,
                                            signal_cols = NULL,
                                            time_col = NULL,
                                            group_cols = NULL,
                                            long_gap_s = NULL,
                                            count_nonfinite = TRUE) {
  .gp_front_check_df(data)

  if (is.null(time_col)) {
    time_col <- .gp_front_guess_time_col(data, required = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(data)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    exclude <- unique(c(time_col, group_cols))
    signal_cols <- setdiff(names(data), exclude)
  }

  if (!length(signal_cols)) {
    stop("No `signal_cols` were supplied or detected.", call. = FALSE)
  }

  missing_cols <- setdiff(signal_cols, names(data))
  if (length(missing_cols)) {
    stop("Missing signal columns: ", paste(missing_cols, collapse = ", "), call. = FALSE)
  }

  groups <- .gp_front_group_indices(data, group_cols)
  rows <- list()
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- data[idx, , drop = FALSE]
    time <- if (!is.null(time_col)) .gp_front_time_seconds(z[[time_col]]) else NULL

    for (sig in signal_cols) {
      x <- z[[sig]]
      missing <- is.na(x)

      if (isTRUE(count_nonfinite) && is.numeric(x)) {
        missing <- missing | !is.finite(x)
      }

      runs <- .gp_front_missing_runs(missing, time = time)
      n_missing <- sum(missing, na.rm = TRUE)
      longest_samples <- if (nrow(runs)) max(runs$length_samples, na.rm = TRUE) else 0L
      longest_duration <- if (nrow(runs) && any(is.finite(runs$duration_s))) {
        max(runs$duration_s, na.rm = TRUE)
      } else {
        NA_real_
      }

      n_long_gaps <- if (!is.null(long_gap_s) && nrow(runs) && any(is.finite(runs$duration_s))) {
        sum(runs$duration_s >= long_gap_s, na.rm = TRUE)
      } else if (!is.null(long_gap_s)) {
        0L
      } else {
        NA_integer_
      }

      k <- k + 1L
      row <- data.frame(
        group = g,
        signal = sig,
        n_samples = length(x),
        n_missing = n_missing,
        missing_prop = if (length(x)) n_missing / length(x) else NA_real_,
        n_missing_runs = nrow(runs),
        longest_missing_run_samples = longest_samples,
        longest_missing_gap_s = longest_duration,
        n_long_gaps = n_long_gaps,
        first_missing_index = if (any(missing)) which(missing)[1L] else NA_integer_,
        last_missing_index = if (any(missing)) rev(which(missing))[1L] else NA_integer_,
        missing_burst_prop = if (n_missing > 0) longest_samples / n_missing else 0,
        stringsAsFactors = FALSE
      )

      if (!is.null(group_cols) && length(group_cols)) {
        row <- cbind(z[1L, group_cols, drop = FALSE], row[setdiff(names(row), "group")])
      }

      rows[[k]] <- row
    }
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Detrend a Gazepoint signal
#'
#' Applies a lightweight generic detrending step to any numeric Gazepoint signal,
#' either globally or within participant/trial groups. This is useful for slow
#' drift in channels such as EDA, pupil size, PPG baseline, or temperature.
#'
#' @param data Data frame or numeric vector.
#' @param signal_col Signal column for data-frame input.
#' @param time_col Optional time column. If omitted, sample index is used.
#' @param group_cols Optional grouping columns for within-group detrending.
#' @param method Detrending method: `"linear"`, `"mean"`, `"median"`,
#'   `"loess"`, or `"none"`.
#' @param span Span for LOESS detrending.
#' @param preserve_mean If TRUE, add the mean trend back after removing drift.
#' @param suffix Suffix for the detrended signal column.
#'
#' @return Data frame with added trend and detrended columns.
#' @export
detrend_gazepoint_signal <- function(data,
                                     signal_col = NULL,
                                     time_col = NULL,
                                     group_cols = NULL,
                                     method = c("linear", "mean", "median", "loess", "none"),
                                     span = 0.30,
                                     preserve_mean = FALSE,
                                     suffix = "_detrended") {
  method <- match.arg(method)

  vector_input <- is.numeric(data) && is.null(dim(data))

  if (isTRUE(vector_input)) {
    data <- data.frame(
      sample_index = seq_along(data),
      signal = as.numeric(data)
    )
    signal_col <- "signal"
    time_col <- "sample_index"
  }

  .gp_front_check_df(data)

  if (is.null(signal_col)) {
    numeric_cols <- names(data)[vapply(data, is.numeric, logical(1))]
    numeric_cols <- setdiff(numeric_cols, c(time_col, group_cols))

    if (!length(numeric_cols)) {
      stop("Could not identify a numeric signal column. Supply `signal_col`.", call. = FALSE)
    }

    signal_col <- numeric_cols[1L]
  }

  if (!signal_col %in% names(data)) {
    stop("`signal_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(time_col)) {
    time_col <- .gp_front_guess_time_col(data, required = FALSE)
  }

  y_all <- suppressWarnings(as.numeric(data[[signal_col]]))
  tt_all <- if (!is.null(time_col) && time_col %in% names(data)) {
    .gp_front_time_seconds(data[[time_col]])
  } else {
    seq_along(y_all)
  }

  trend <- rep(NA_real_, length(y_all))
  detrended <- rep(NA_real_, length(y_all))

  groups <- .gp_front_group_indices(data, group_cols)

  for (g in names(groups)) {
    idx <- groups[[g]]
    y <- y_all[idx]
    tt <- tt_all[idx]
    ok <- is.finite(y) & is.finite(tt)

    group_trend <- rep(NA_real_, length(y))

    if (!any(ok)) {
      trend[idx] <- group_trend
      detrended[idx] <- NA_real_
      next
    }

    if (method == "none") {
      group_trend[ok] <- 0
    } else if (method == "mean") {
      group_trend[ok] <- mean(y[ok], na.rm = TRUE)
    } else if (method == "median") {
      group_trend[ok] <- stats::median(y[ok], na.rm = TRUE)
    } else if (method == "linear") {
      if (sum(ok) >= 2L && length(unique(tt[ok])) >= 2L) {
        fit <- stats::lm(y[ok] ~ tt[ok])
        group_trend[ok] <- stats::fitted(fit)
      } else {
        group_trend[ok] <- mean(y[ok], na.rm = TRUE)
      }
    } else if (method == "loess") {
      if (sum(ok) >= 5L && length(unique(tt[ok])) >= 4L) {
        df <- data.frame(y = y[ok], tt = tt[ok])
        fit <- tryCatch(
          stats::loess(
            y ~ tt,
            data = df,
            span = span,
            degree = 1,
            control = stats::loess.control(surface = "direct")
          ),
          error = function(e) NULL
        )

        if (!is.null(fit)) {
          pred <- tryCatch(
            as.numeric(stats::predict(fit, newdata = data.frame(tt = tt[ok]))),
            error = function(e) rep(NA_real_, sum(ok))
          )

          if (any(is.finite(pred))) {
            group_trend[ok] <- pred
          } else {
            group_trend[ok] <- mean(y[ok], na.rm = TRUE)
          }
        } else {
          group_trend[ok] <- mean(y[ok], na.rm = TRUE)
        }
      } else {
        group_trend[ok] <- mean(y[ok], na.rm = TRUE)
      }
    }

    center <- if (isTRUE(preserve_mean)) mean(group_trend[ok], na.rm = TRUE) else 0
    group_detrended <- y - group_trend + center

    trend[idx] <- group_trend
    detrended[idx] <- group_detrended
  }

  trend_col <- paste0(signal_col, "_trend")
  detrended_col <- paste0(signal_col, suffix)

  data[[trend_col]] <- trend
  data[[detrended_col]] <- detrended

  attr(data, "gazepoint_detrend") <- list(
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    method = method,
    span = span,
    preserve_mean = preserve_mean,
    trend_col = trend_col,
    detrended_col = detrended_col
  )

  data
}

#' Audit a Gazepoint biometrics file before analysis
#'
#' Provides a single front-door preflight audit for a Gazepoint-style biometric
#' export. The audit standardizes column names when requested, reports likely
#' modality availability, schema status, timestamp irregularity, missingness,
#' duplicate rows, and reviewer-facing warnings.
#'
#' @param path Optional CSV/TSV file path.
#' @param data Optional data frame. If supplied, it is used instead of `path`.
#' @param expected_modalities Modalities expected in the export.
#' @param time_col Optional time column. If omitted, a common Gazepoint time
#'   column is guessed after optional standardization.
#' @param standardize If TRUE, apply `standardize_gazepoint_column_names()`
#'   before auditing.
#' @param include_data If TRUE, include the standardized data in the returned
#'   audit object.
#' @param long_gap_s Optional missing-gap threshold passed to
#'   `summarize_gazepoint_missingness()`.
#'
#' @return An object of class `gazepoint_biometrics_audit`.
#' @export
audit_gazepoint_biometrics_file <- function(path = NULL,
                                            data = NULL,
                                            expected_modalities = c("time", "eda", "ppg", "hr", "ibi", "pupil", "gaze", "events"),
                                            time_col = NULL,
                                            standardize = TRUE,
                                            include_data = FALSE,
                                            long_gap_s = NULL) {
  if (is.null(data)) {
    if (is.null(path)) {
      stop("Supply either `path` or `data`.", call. = FALSE)
    }
    data <- .gp_front_read_table(path)
  }

  .gp_front_check_df(data)

  original_names <- names(data)
  standardized <- FALSE
  column_standardization <- data.frame()

  if (isTRUE(standardize) && exists("standardize_gazepoint_column_names", mode = "function")) {
    data <- standardize_gazepoint_column_names(data)
    standardized <- TRUE
    column_standardization <- attr(data, "gazepoint_column_standardization")
  }

  if (is.null(time_col)) {
    time_col <- .gp_front_guess_time_col(data, required = FALSE)
  }

  modalities <- .gp_front_detect_modalities(data)

  if (exists("audit_gazepoint_export_schema", mode = "function")) {
    schema <- tryCatch(
      audit_gazepoint_export_schema(data),
      error = function(e) data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
    )
  } else {
    schema <- modalities
  }

  missingness <- tryCatch(
    summarize_gazepoint_missingness(
      data,
      time_col = time_col,
      long_gap_s = long_gap_s
    ),
    error = function(e) data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
  )

  timestamp_diagnostics <- if (!is.null(time_col) && time_col %in% names(data) &&
    exists("assess_gazepoint_sampling_irregularity", mode = "function")) {
    tryCatch(
      assess_gazepoint_sampling_irregularity(data, time_col = time_col),
      error = function(e) data.frame(error = conditionMessage(e), stringsAsFactors = FALSE)
    )
  } else {
    data.frame(
      available = FALSE,
      reason = "No time column detected.",
      stringsAsFactors = FALSE
    )
  }

  duplicate_mask <- duplicated(data)
  duplicate_rows <- data.frame(
    n_rows = nrow(data),
    n_duplicate_rows = sum(duplicate_mask, na.rm = TRUE),
    duplicate_prop = mean(duplicate_mask, na.rm = TRUE),
    first_duplicate_index = if (any(duplicate_mask)) which(duplicate_mask)[1L] else NA_integer_,
    stringsAsFactors = FALSE
  )

  expected_missing <- setdiff(
    expected_modalities,
    modalities$modality[modalities$present]
  )

  warnings <- character()

  if (length(expected_missing)) {
    warnings <- c(
      warnings,
      paste0("Missing expected modalities: ", paste(expected_missing, collapse = ", "), ".")
    )
  }

  if (duplicate_rows$n_duplicate_rows > 0) {
    warnings <- c(
      warnings,
      paste0("Detected ", duplicate_rows$n_duplicate_rows, " duplicated rows.")
    )
  }

  if (NROW(timestamp_diagnostics) && "n_negative_steps" %in% names(timestamp_diagnostics) &&
    any(timestamp_diagnostics$n_negative_steps > 0, na.rm = TRUE)) {
    warnings <- c(warnings, "Detected negative timestamp steps.")
  }

  if (NROW(timestamp_diagnostics) && "n_zero_steps" %in% names(timestamp_diagnostics) &&
    any(timestamp_diagnostics$n_zero_steps > 0, na.rm = TRUE)) {
    warnings <- c(warnings, "Detected repeated timestamps.")
  }

  if (NROW(missingness) && "missing_prop" %in% names(missingness) &&
    any(missingness$missing_prop > 0.20, na.rm = TRUE)) {
    warnings <- c(warnings, "At least one column has more than 20% missing values.")
  }

  audit <- list(
    input = list(
      path = path,
      source = if (is.null(path)) "data" else "path",
      standardized = standardized,
      time_col = time_col
    ),
    dimensions = data.frame(
      n_rows = nrow(data),
      n_cols = ncol(data),
      stringsAsFactors = FALSE
    ),
    original_columns = original_names,
    current_columns = names(data),
    modalities = modalities,
    schema = schema,
    missingness = missingness,
    timestamp_diagnostics = timestamp_diagnostics,
    duplicate_rows = duplicate_rows,
    column_standardization = column_standardization,
    warnings = .gp_front_as_warning_vector(warnings)
  )

  if (isTRUE(include_data)) {
    audit$data <- data
  }

  class(audit) <- c("gazepoint_biometrics_audit", "list")
  audit
}

#' @param x Object of class `gazepoint_biometrics_audit` for the print method.
#' @param object Object of class `gazepoint_biometrics_audit` for the summary method.
#' @param ... Additional arguments currently ignored.
#' @rdname audit_gazepoint_biometrics_file
#' @export
print.gazepoint_biometrics_audit <- function(x, ...) {
  cat("Gazepoint biometrics preflight audit\n")
  cat("Rows:", x$dimensions$n_rows, "| Columns:", x$dimensions$n_cols, "\n")

  present <- x$modalities$modality[x$modalities$present]
  missing <- x$modalities$modality[!x$modalities$present]

  cat("Detected modalities:", if (length(present)) paste(present, collapse = ", ") else "none", "\n")
  cat("Missing modalities:", if (length(missing)) paste(missing, collapse = ", ") else "none", "\n")

  if (length(x$warnings)) {
    cat("Warnings:\n")
    for (w in x$warnings) {
      cat(" - ", w, "\n", sep = "")
    }
  } else {
    cat("Warnings: none\n")
  }

  invisible(x)
}

#' @rdname audit_gazepoint_biometrics_file
#' @export
summary.gazepoint_biometrics_audit <- function(object, ...) {
  data.frame(
    n_rows = object$dimensions$n_rows,
    n_cols = object$dimensions$n_cols,
    n_modalities_detected = sum(object$modalities$present, na.rm = TRUE),
    n_duplicate_rows = object$duplicate_rows$n_duplicate_rows,
    n_warnings = length(object$warnings),
    stringsAsFactors = FALSE
  )
}

