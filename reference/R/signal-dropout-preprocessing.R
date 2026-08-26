#' Detect long signal-dropout intervals
#'
#' Flags long missing, zero, constant, or low-variance runs in selected signal
#' columns. The function is intended for quality control and audit reporting
#' only. It does not remove samples and does not make physiological,
#' psychological, diagnostic, or clinical claims.
#'
#' @param data A data frame.
#' @param signal_cols Character vector of numeric signal columns to inspect.
#' @param group_cols Optional character vector of grouping columns, such as
#'   participant, trial, session, or condition.
#' @param time_col Optional numeric time column used to report interval start
#'   and end times.
#' @param min_run_length Minimum number of consecutive samples required for a
#'   run to be reported.
#' @param zero_tolerance Absolute tolerance used when detecting zero-valued
#'   runs.
#' @param constant_tolerance Absolute adjacent-difference tolerance used when
#'   detecting constant runs.
#' @param low_variance_threshold Optional standard-deviation threshold for
#'   low-variance windows. If \code{NULL}, low-variance detection is skipped.
#' @param detect_missing Logical. If \code{TRUE}, detect non-finite runs.
#' @param detect_zero Logical. If \code{TRUE}, detect near-zero runs.
#' @param detect_constant Logical. If \code{TRUE}, detect constant runs.
#' @param detect_low_variance Logical. If \code{TRUE}, detect low-variance
#'   windows when \code{low_variance_threshold} is supplied.
#'
#' @return A list with class \code{gazepoint_nonwear_detection}, containing
#'   interval and summary tables.
#' @export
detect_gazepoint_nonwear <- function(data,
                                     signal_cols,
                                     group_cols = NULL,
                                     time_col = NULL,
                                     min_run_length = 10,
                                     zero_tolerance = 0,
                                     constant_tolerance = 0,
                                     low_variance_threshold = NULL,
                                     detect_missing = TRUE,
                                     detect_zero = TRUE,
                                     detect_constant = TRUE,
                                     detect_low_variance = TRUE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  if (missing(signal_cols) || length(signal_cols) == 0) {
    stop("`signal_cols` must contain at least one column name.", call. = FALSE)
  }

  signal_cols <- as.character(signal_cols)
  missing_signal_cols <- setdiff(signal_cols, names(data))
  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(group_cols)) {
    group_cols <- as.character(group_cols)
    missing_group_cols <- setdiff(group_cols, names(data))
    if (length(missing_group_cols) > 0) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_group_cols, collapse = ", "),
        call. = FALSE
      )
    }
  }

  if (!is.null(time_col)) {
    time_col <- as.character(time_col)[1]
    if (!time_col %in% names(data)) {
      stop("`time_col` was not found in `data`.", call. = FALSE)
    }
    if (!is.numeric(data[[time_col]])) {
      stop("`time_col` must be numeric.", call. = FALSE)
    }
  }

  gazepoint_check_positive_integer(min_run_length, "min_run_length")
  gazepoint_check_nonnegative_number(zero_tolerance, "zero_tolerance")
  gazepoint_check_nonnegative_number(constant_tolerance, "constant_tolerance")

  if (!is.null(low_variance_threshold)) {
    gazepoint_check_nonnegative_number(
      low_variance_threshold,
      "low_variance_threshold"
    )
  }

  gazepoint_check_logical_one(detect_missing, "detect_missing")
  gazepoint_check_logical_one(detect_zero, "detect_zero")
  gazepoint_check_logical_one(detect_constant, "detect_constant")
  gazepoint_check_logical_one(detect_low_variance, "detect_low_variance")

  working <- data
  working$.gp_row_index <- seq_len(nrow(working))

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(working)))
  } else {
    interaction(working[group_cols], drop = TRUE, lex.order = TRUE)
  }

  pieces <- split(working, split_index, drop = TRUE)

  interval_rows <- list()
  summary_rows <- list()
  interval_i <- 0L
  summary_i <- 0L

  for (piece_name in names(pieces)) {
    piece <- pieces[[piece_name]]

    if (!is.null(time_col)) {
      ord <- order(piece[[time_col]], na.last = TRUE)
      piece <- piece[ord, , drop = FALSE]
    }

    group_values <- if (is.null(group_cols) || length(group_cols) == 0) {
      data.frame(segment_id = piece_name, stringsAsFactors = FALSE)
    } else {
      piece[1, group_cols, drop = FALSE]
    }

    for (signal in signal_cols) {
      x <- piece[[signal]]
      n_samples <- length(x)
      any_flag <- rep(FALSE, n_samples)
      type_counts <- c(
        missing_run = 0L,
        zero_run = 0L,
        constant_run = 0L,
        low_variance_run = 0L
      )

      run_specs <- list()

      if (detect_missing) {
        run_specs$missing_run <- gazepoint_flag_runs(!is.finite(x), min_run_length)
      }

      if (detect_zero) {
        run_specs$zero_run <- gazepoint_flag_runs(
          is.finite(x) & abs(x) <= zero_tolerance,
          min_run_length
        )
      }

      if (detect_constant) {
        run_specs$constant_run <- gazepoint_constant_runs(
          x,
          min_run_length = min_run_length,
          tolerance = constant_tolerance
        )
      }

      if (detect_low_variance && !is.null(low_variance_threshold)) {
        run_specs$low_variance_run <- gazepoint_low_variance_runs(
          x,
          min_run_length = min_run_length,
          threshold = low_variance_threshold
        )
      }

      for (run_type in names(run_specs)) {
        intervals <- run_specs[[run_type]]

        if (nrow(intervals) == 0) {
          next
        }

        type_counts[[run_type]] <- nrow(intervals)

        for (j in seq_len(nrow(intervals))) {
          pos <- seq.int(intervals$start_pos[j], intervals$end_pos[j])
          any_flag[pos] <- TRUE

          interval_i <- interval_i + 1L

          time_start <- if (!is.null(time_col)) {
            piece[[time_col]][intervals$start_pos[j]]
          } else {
            NA_real_
          }

          time_end <- if (!is.null(time_col)) {
            piece[[time_col]][intervals$end_pos[j]]
          } else {
            NA_real_
          }

          interval_rows[[interval_i]] <- cbind(
            group_values,
            data.frame(
              signal = signal,
              run_type = run_type,
              start_row = piece$.gp_row_index[intervals$start_pos[j]],
              end_row = piece$.gp_row_index[intervals$end_pos[j]],
              start_position = intervals$start_pos[j],
              end_position = intervals$end_pos[j],
              n_samples = intervals$n_samples[j],
              start_time = time_start,
              end_time = time_end,
              stringsAsFactors = FALSE
            ),
            stringsAsFactors = FALSE
          )
        }
      }

      summary_i <- summary_i + 1L
      summary_rows[[summary_i]] <- cbind(
        group_values,
        data.frame(
          signal = signal,
          n_samples = n_samples,
          n_intervals = sum(type_counts),
          n_flagged_samples = sum(any_flag),
          prop_flagged_samples = if (n_samples > 0) sum(any_flag) / n_samples else NA_real_,
          n_missing_run = type_counts[["missing_run"]],
          n_zero_run = type_counts[["zero_run"]],
          n_constant_run = type_counts[["constant_run"]],
          n_low_variance_run = type_counts[["low_variance_run"]],
          stringsAsFactors = FALSE
        ),
        stringsAsFactors = FALSE
      )
    }
  }

  intervals <- if (length(interval_rows) == 0) {
    gazepoint_empty_nonwear_intervals(group_cols)
  } else {
    do.call(rbind, interval_rows)
  }

  summary <- do.call(rbind, summary_rows)

  rownames(intervals) <- NULL
  rownames(summary) <- NULL

  result <- list(
    intervals = intervals,
    summary = summary,
    parameters = list(
      signal_cols = signal_cols,
      group_cols = group_cols,
      time_col = time_col,
      min_run_length = min_run_length,
      zero_tolerance = zero_tolerance,
      constant_tolerance = constant_tolerance,
      low_variance_threshold = low_variance_threshold,
      detect_missing = detect_missing,
      detect_zero = detect_zero,
      detect_constant = detect_constant,
      detect_low_variance = detect_low_variance
    )
  )

  class(result) <- c("gazepoint_nonwear_detection", "list")
  result
}

gazepoint_empty_nonwear_intervals <- function(group_cols) {
  groups <- if (is.null(group_cols) || length(group_cols) == 0) {
    data.frame(segment_id = character(0), stringsAsFactors = FALSE)
  } else {
    as.data.frame(
      stats::setNames(
        rep(list(character(0)), length(group_cols)),
        group_cols
      ),
      stringsAsFactors = FALSE
    )
  }

  cbind(
    groups,
    data.frame(
      signal = character(0),
      run_type = character(0),
      start_row = integer(0),
      end_row = integer(0),
      start_position = integer(0),
      end_position = integer(0),
      n_samples = integer(0),
      start_time = numeric(0),
      end_time = numeric(0),
      stringsAsFactors = FALSE
    ),
    stringsAsFactors = FALSE
  )
}

gazepoint_flag_runs <- function(flag, min_run_length) {
  if (length(flag) == 0) {
    return(data.frame(
      start_pos = integer(0),
      end_pos = integer(0),
      n_samples = integer(0)
    ))
  }

  flag[is.na(flag)] <- FALSE
  runs <- rle(flag)
  ends <- cumsum(runs$lengths)
  starts <- ends - runs$lengths + 1L

  keep <- runs$values & runs$lengths >= min_run_length

  data.frame(
    start_pos = starts[keep],
    end_pos = ends[keep],
    n_samples = runs$lengths[keep],
    stringsAsFactors = FALSE
  )
}

gazepoint_constant_runs <- function(x, min_run_length, tolerance) {
  n <- length(x)

  if (n == 0) {
    return(gazepoint_flag_runs(logical(0), min_run_length))
  }

  finite <- is.finite(x)

  if (n == 1) {
    return(gazepoint_flag_runs(FALSE, min_run_length))
  }

  new_run <- rep(TRUE, n)

  for (i in 2:n) {
    same_as_previous <- finite[i] &&
      finite[i - 1L] &&
      abs(x[i] - x[i - 1L]) <= tolerance

    new_run[i] <- !same_as_previous
  }

  run_id <- cumsum(new_run)
  run_lengths <- tabulate(run_id, nbins = max(run_id))
  constant_flag <- finite & run_lengths[run_id] >= min_run_length

  gazepoint_flag_runs(constant_flag, min_run_length)
}

gazepoint_low_variance_runs <- function(x, min_run_length, threshold) {
  n <- length(x)
  flag <- rep(FALSE, n)

  if (n < min_run_length) {
    return(gazepoint_flag_runs(flag, min_run_length))
  }

  for (i in seq_len(n - min_run_length + 1L)) {
    idx <- seq.int(i, i + min_run_length - 1L)
    values <- x[idx]

    if (all(is.finite(values)) && stats::sd(values) <= threshold) {
      flag[idx] <- TRUE
    }
  }

  gazepoint_flag_runs(flag, min_run_length)
}

#' Summarize signal-dropout detections
#'
#' Aggregates the summary table returned by \code{detect_gazepoint_nonwear()}.
#' The result is intended for QC reporting and does not imply automatic
#' exclusion.
#'
#' @param nonwear A \code{gazepoint_nonwear_detection} object or a compatible
#'   summary data frame.
#' @param by Character vector of columns used for aggregation.
#'
#' @return A data frame.
#' @export
summarize_gazepoint_nonwear <- function(nonwear, by = "signal") {
  summary <- if (inherits(nonwear, "gazepoint_nonwear_detection")) {
    nonwear$summary
  } else if (is.data.frame(nonwear)) {
    nonwear
  } else {
    stop(
      "`nonwear` must be a gazepoint_nonwear_detection object or data frame.",
      call. = FALSE
    )
  }

  required <- c(
    "n_samples",
    "n_intervals",
    "n_flagged_samples",
    "n_missing_run",
    "n_zero_run",
    "n_constant_run",
    "n_low_variance_run"
  )

  missing_required <- setdiff(required, names(summary))
  if (length(missing_required) > 0) {
    stop(
      "`nonwear` is missing required columns: ",
      paste(missing_required, collapse = ", "),
      call. = FALSE
    )
  }

  by <- as.character(by)
  missing_by <- setdiff(by, names(summary))
  if (length(missing_by) > 0) {
    stop(
      "`by` contains columns not found in `nonwear`: ",
      paste(missing_by, collapse = ", "),
      call. = FALSE
    )
  }

  split_index <- interaction(summary[by], drop = TRUE, lex.order = TRUE)
  pieces <- split(summary, split_index, drop = TRUE)

  out <- lapply(pieces, function(piece) {
    group_values <- piece[1, by, drop = FALSE]
    n_samples_total <- sum(piece$n_samples, na.rm = TRUE)
    n_flagged_total <- sum(piece$n_flagged_samples, na.rm = TRUE)

    cbind(
      group_values,
      data.frame(
        n_signal_segments = nrow(piece),
        n_samples_total = n_samples_total,
        n_intervals_total = sum(piece$n_intervals, na.rm = TRUE),
        n_flagged_samples_total = n_flagged_total,
        prop_flagged_samples = if (n_samples_total > 0) {
          n_flagged_total / n_samples_total
        } else {
          NA_real_
        },
        n_missing_run = sum(piece$n_missing_run, na.rm = TRUE),
        n_zero_run = sum(piece$n_zero_run, na.rm = TRUE),
        n_constant_run = sum(piece$n_constant_run, na.rm = TRUE),
        n_low_variance_run = sum(piece$n_low_variance_run, na.rm = TRUE),
        stringsAsFactors = FALSE
      ),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL
  out
}

#' Apply lightweight preprocessing to signal columns
#'
#' Applies conservative base-R preprocessing to selected numeric signal columns.
#' Supported methods are moving average, rolling median, and linear detrending.
#' The function returns new columns by default and records a processing log.
#'
#' @param data A data frame.
#' @param signal_cols Character vector of numeric signal columns.
#' @param method One of \code{"moving_average"}, \code{"rolling_median"}, or
#'   \code{"detrend"}.
#' @param group_cols Optional grouping columns.
#' @param time_col Optional numeric time column used for ordering within groups.
#' @param window Window length for moving-average and rolling-median methods.
#' @param suffix Optional suffix for created columns. If \code{NULL}, a suffix
#'   is derived from \code{method}.
#' @param overwrite Logical. If \code{TRUE}, overwrite input signal columns.
#' @param na_rm Logical. If \code{TRUE}, ignore missing values inside rolling
#'   windows.
#'
#' @return A data frame with class \code{gazepoint_filtered_signal}.
#' @export
filter_gazepoint_signal <- function(data,
                                    signal_cols,
                                    method = c("moving_average", "rolling_median", "detrend"),
                                    group_cols = NULL,
                                    time_col = NULL,
                                    window = 5,
                                    suffix = NULL,
                                    overwrite = FALSE,
                                    na_rm = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (missing(signal_cols) || length(signal_cols) == 0) {
    stop("`signal_cols` must contain at least one column name.", call. = FALSE)
  }

  method <- match.arg(method)
  signal_cols <- as.character(signal_cols)

  missing_signal_cols <- setdiff(signal_cols, names(data))
  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(group_cols)) {
    group_cols <- as.character(group_cols)
    missing_group_cols <- setdiff(group_cols, names(data))
    if (length(missing_group_cols) > 0) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_group_cols, collapse = ", "),
        call. = FALSE
      )
    }
  }

  if (!is.null(time_col)) {
    time_col <- as.character(time_col)[1]
    if (!time_col %in% names(data)) {
      stop("`time_col` was not found in `data`.", call. = FALSE)
    }
    if (!is.numeric(data[[time_col]])) {
      stop("`time_col` must be numeric.", call. = FALSE)
    }
  }

  if (method %in% c("moving_average", "rolling_median")) {
    gazepoint_check_positive_integer(window, "window")
  }

  gazepoint_check_logical_one(overwrite, "overwrite")
  gazepoint_check_logical_one(na_rm, "na_rm")

  if (is.null(suffix)) {
    suffix <- paste0("_", method)
  }

  if (!is.character(suffix) || length(suffix) != 1 || is.na(suffix)) {
    stop("`suffix` must be `NULL` or a single character string.", call. = FALSE)
  }

  out <- data
  log_rows <- list()
  log_i <- 0L

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(data)))
  } else {
    interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  }

  index_pieces <- split(seq_len(nrow(data)), split_index, drop = TRUE)

  for (signal in signal_cols) {
    output_col <- if (overwrite) signal else paste0(signal, suffix)

    if (!overwrite && output_col %in% names(out)) {
      stop(
        "Output column already exists: ",
        output_col,
        ". Choose another `suffix` or set `overwrite = TRUE`.",
        call. = FALSE
      )
    }

    out[[output_col]] <- NA_real_

    for (piece_name in names(index_pieces)) {
      idx <- index_pieces[[piece_name]]

      if (!is.null(time_col)) {
        idx <- idx[order(data[[time_col]][idx], na.last = TRUE)]
      }

      x <- data[[signal]][idx]

      filtered <- switch(
        method,
        moving_average = gazepoint_roll_numeric(x, window, mean, na_rm = na_rm),
        rolling_median = gazepoint_roll_numeric(x, window, stats::median, na_rm = na_rm),
        detrend = gazepoint_detrend_numeric(
          x,
          time = if (!is.null(time_col)) data[[time_col]][idx] else seq_along(x)
        )
      )

      out[[output_col]][idx] <- filtered

      log_i <- log_i + 1L
      log_rows[[log_i]] <- data.frame(
        signal = signal,
        output_col = output_col,
        group = piece_name,
        method = method,
        window = if (method == "detrend") NA_integer_ else as.integer(window),
        n_samples = length(x),
        n_nonmissing_input = sum(is.finite(x)),
        n_nonmissing_output = sum(is.finite(filtered)),
        stringsAsFactors = FALSE
      )
    }
  }

  filter_log <- do.call(rbind, log_rows)
  rownames(filter_log) <- NULL

  attr(out, "filter_log") <- filter_log
  class(out) <- c("gazepoint_filtered_signal", class(out))
  out
}

gazepoint_roll_numeric <- function(x, window, fun, na_rm) {
  n <- length(x)
  y <- rep(NA_real_, n)

  if (n == 0) {
    return(y)
  }

  x_work <- x
  x_work[!is.finite(x_work)] <- NA_real_

  left <- floor((window - 1L) / 2L)
  right <- ceiling((window - 1L) / 2L)

  for (i in seq_len(n)) {
    idx <- seq.int(max(1L, i - left), min(n, i + right))
    values <- x_work[idx]

    if (!na_rm && any(is.na(values))) {
      y[i] <- NA_real_
    } else if (na_rm && all(is.na(values))) {
      y[i] <- NA_real_
    } else {
      y[i] <- fun(values, na.rm = na_rm)
    }
  }

  y
}

gazepoint_detrend_numeric <- function(x, time) {
  y <- rep(NA_real_, length(x))
  finite <- is.finite(x) & is.finite(time)

  if (sum(finite) < 2) {
    return(y)
  }

  model <- stats::lm(x[finite] ~ time[finite])
  trend <- stats::predict(model, newdata = data.frame(time = time[finite]))
  y[finite] <- x[finite] - (trend - mean(trend, na.rm = TRUE))
  y
}

#' Regularize signal data to an evenly spaced time grid
#'
#' Uses \code{stats::approx()} to interpolate selected numeric signals onto a
#' regular time grid within each group. The function records an interpolation
#' log and does not extrapolate beyond the observed time range.
#'
#' @param data A data frame.
#' @param time_col Numeric time column.
#' @param signal_cols Optional character vector of numeric signal columns. If
#'   \code{NULL}, all numeric columns except grouping and time columns are used.
#' @param group_cols Optional grouping columns.
#' @param interval Numeric interval for the output time grid, in the same units
#'   as \code{time_col}. If \code{NULL}, the median positive time difference is
#'   used within each group.
#' @param method Interpolation method passed to \code{stats::approx()}:
#'   \code{"linear"} or \code{"constant"}.
#'
#' @return A data frame with class \code{gazepoint_upsampled_data}.
#' @export
upsample_gazepoint_data <- function(data,
                                    time_col,
                                    signal_cols = NULL,
                                    group_cols = NULL,
                                    interval = NULL,
                                    method = c("linear", "constant")) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  time_col <- as.character(time_col)[1]
  if (!time_col %in% names(data)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.numeric(data[[time_col]])) {
    stop("`time_col` must be numeric.", call. = FALSE)
  }

  if (!is.null(group_cols)) {
    group_cols <- as.character(group_cols)
    missing_group_cols <- setdiff(group_cols, names(data))
    if (length(missing_group_cols) > 0) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_group_cols, collapse = ", "),
        call. = FALSE
      )
    }
  }

  if (is.null(signal_cols)) {
    numeric_cols <- names(data)[vapply(data, is.numeric, logical(1))]
    signal_cols <- setdiff(numeric_cols, c(time_col, group_cols))
  }

  signal_cols <- as.character(signal_cols)

  if (length(signal_cols) == 0) {
    stop("No numeric signal columns were selected.", call. = FALSE)
  }

  missing_signal_cols <- setdiff(signal_cols, names(data))
  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(interval)) {
    gazepoint_check_positive_number(interval, "interval")
  }

  method <- match.arg(method)

  split_index <- if (is.null(group_cols) || length(group_cols) == 0) {
    factor(rep("all", nrow(data)))
  } else {
    interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  }

  index_pieces <- split(seq_len(nrow(data)), split_index, drop = TRUE)
  out_rows <- list()
  log_rows <- list()

  for (piece_i in seq_along(index_pieces)) {
    idx <- index_pieces[[piece_i]]
    piece <- data[idx, , drop = FALSE]
    piece <- piece[order(piece[[time_col]], na.last = TRUE), , drop = FALSE]

    valid_time <- is.finite(piece[[time_col]])

    if (sum(valid_time) < 2) {
      next
    }

    piece <- piece[valid_time, , drop = FALSE]
    times <- piece[[time_col]]
    unique_times <- sort(unique(times))
    diffs <- diff(unique_times)
    positive_diffs <- diffs[is.finite(diffs) & diffs > 0]

    if (length(positive_diffs) == 0) {
      next
    }

    interval_i <- if (is.null(interval)) {
      stats::median(positive_diffs)
    } else {
      interval
    }

    time_grid <- seq(min(unique_times), max(unique_times), by = interval_i)

    group_values <- if (is.null(group_cols) || length(group_cols) == 0) {
      data.frame(segment_id = names(index_pieces)[piece_i], stringsAsFactors = FALSE)
    } else {
      piece[1, group_cols, drop = FALSE]
    }

    out_piece <- group_values[rep(1, length(time_grid)), , drop = FALSE]
    rownames(out_piece) <- NULL

    out_piece[[time_col]] <- time_grid

    for (signal in signal_cols) {
      out_piece[[signal]] <- gazepoint_approx_signal(
        time = times,
        value = piece[[signal]],
        xout = time_grid,
        method = method
      )
    }

    out_rows[[length(out_rows) + 1L]] <- out_piece

    log_rows[[length(log_rows) + 1L]] <- cbind(
      group_values,
      data.frame(
        n_input_rows = nrow(piece),
        n_output_rows = length(time_grid),
        time_min = min(unique_times),
        time_max = max(unique_times),
        interval = interval_i,
        method = method,
        signals = paste(signal_cols, collapse = ","),
        stringsAsFactors = FALSE
      ),
      stringsAsFactors = FALSE
    )
  }

  out <- if (length(out_rows) == 0) {
    stop("No groups contained at least two finite time points.", call. = FALSE)
  } else {
    do.call(rbind, out_rows)
  }

  log <- do.call(rbind, log_rows)

  rownames(out) <- NULL
  rownames(log) <- NULL

  attr(out, "upsample_log") <- log
  class(out) <- c("gazepoint_upsampled_data", class(out))
  out
}

gazepoint_approx_signal <- function(time, value, xout, method) {
  valid <- is.finite(time) & is.finite(value)

  if (sum(valid) < 2) {
    return(rep(NA_real_, length(xout)))
  }

  dat <- data.frame(time = time[valid], value = value[valid])
  dat <- stats::aggregate(value ~ time, dat, mean)

  stats::approx(
    x = dat$time,
    y = dat$value,
    xout = xout,
    method = method,
    rule = 1,
    ties = mean
  )$y
}

gazepoint_check_positive_integer <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || is.na(x) || x < 1) {
    stop("`", name, "` must be a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gazepoint_check_positive_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x <= 0) {
    stop("`", name, "` must be a single positive number.", call. = FALSE)
  }

  invisible(TRUE)
}

gazepoint_check_nonnegative_number <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x < 0) {
    stop("`", name, "` must be a single non-negative number.", call. = FALSE)
  }

  invisible(TRUE)
}

gazepoint_check_logical_one <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
