#' Summarise validity and availability of Gazepoint biometric signals
#'
#' Summarises missingness, finite numeric availability, variability, and optional
#' validity-flag columns for Gazepoint Biometrics data. The helper is descriptive:
#' it reports whether biometric signals appear available and usable, but it does
#' not infer emotion, valence, or HRV from ambiguous raw columns. In particular,
#' raw `HRV` columns are treated as validity/vendor flags unless the user has
#' independent documentation proving otherwise.
#'
#' @param data A data frame.
#' @param signal_cols Optional character vector of biometric signal columns to
#'   summarise. If `NULL`, common Gazepoint biometric signal columns are detected
#'   from the column names.
#' @param validity_cols Optional character vector of validity-flag columns to
#'   summarise. If `NULL`, common validity-like columns are detected, including
#'   `HRV` when present.
#' @param group_cols Optional character vector of grouping columns, such as
#'   participant, stimulus, trial, or condition columns.
#' @param active_min_unique Minimum number of unique finite values required for
#'   a numeric signal to be treated as active.
#'
#' @return A list with `overview`, `signals`, `validity_flags`,
#'   `group_summary`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   USER = rep(c("P1", "P2"), each = 4),
#'   GSR = c(1, 2, NA, 4, 2, 2, 2, 2),
#'   HR = c(70, 71, 72, NA, 80, 81, 82, 83),
#'   HRV = c(1, 1, 0, 1, 1, 1, 1, 1)
#' )
#' summarise_gazepoint_biometric_validity(df, group_cols = "USER")
#'
#' @export
summarise_gazepoint_biometric_validity <- function(data,
                                                   signal_cols = NULL,
                                                   validity_cols = NULL,
                                                   group_cols = NULL,
                                                   active_min_unique = 2L) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(signal_cols)) {
    .gpbiom_assert_columns(data, signal_cols, "signal_cols")
  }

  if (!is.null(validity_cols)) {
    .gpbiom_assert_columns(data, validity_cols, "validity_cols")
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.numeric(active_min_unique) ||
      length(active_min_unique) != 1L ||
      is.na(active_min_unique) ||
      active_min_unique < 1) {
    stop("`active_min_unique` must be a positive number.", call. = FALSE)
  }

  active_min_unique <- as.integer(active_min_unique)

  if (is.null(signal_cols)) {
    signal_cols <- .gpbiom_detect_signal_columns(data)
  }

  if (is.null(validity_cols)) {
    validity_cols <- .gpbiom_detect_validity_columns(data)
  }

  signal_summary <- .gpbiom_summarise_signal_columns(
    data = data,
    signal_cols = signal_cols,
    active_min_unique = active_min_unique
  )

  validity_summary <- .gpbiom_summarise_validity_columns(
    data = data,
    validity_cols = validity_cols
  )

  group_summary <- .gpbiom_summarise_signal_groups(
    data = data,
    signal_cols = signal_cols,
    group_cols = group_cols,
    active_min_unique = active_min_unique
  )

  active_signal_count <- sum(signal_summary$status == "active_signal")
  inactive_signal_count <- nrow(signal_summary) - active_signal_count

  overview <- data.frame(
    n_rows = nrow(data),
    n_columns = ncol(data),
    signal_column_count = length(signal_cols),
    active_signal_count = active_signal_count,
    inactive_signal_count = inactive_signal_count,
    validity_flag_column_count = length(validity_cols),
    group_column_count = length(group_cols),
    status = if (length(signal_cols) == 0L) {
      "no_biometric_signal_columns_detected"
    } else if (active_signal_count == 0L) {
      "no_active_biometric_signals_detected"
    } else if (inactive_signal_count > 0L) {
      "some_biometric_signals_inactive_or_limited"
    } else {
      "biometric_signals_available"
    },
    stringsAsFactors = FALSE
  )

  settings <- list(
    signal_cols = signal_cols,
    validity_cols = validity_cols,
    group_cols = group_cols,
    active_min_unique = active_min_unique,
    notes = c(
      "GSR/EDA availability does not identify emotional valence.",
      "Heart-rate availability requires baseline/task context for interpretation.",
      "Raw HRV columns are treated as validity/vendor flags unless independently documented as HRV metrics."
    )
  )

  list(
    overview = overview,
    signals = signal_summary,
    validity_flags = validity_summary,
    group_summary = group_summary,
    settings = settings
  )
}


#' Flag biometric dropouts and flatline periods
#'
#' Flags missing-value runs and sustained flatline runs in Gazepoint biometric
#' signal columns. Missing dropouts are defined as consecutive missing or
#' non-finite numeric samples. Flatline dropouts are defined as consecutive
#' finite numeric samples that remain unchanged within a tolerance.
#'
#' The function adds row-level flags and stores a dropout summary in the returned
#' data frame attributes. It does not remove rows.
#'
#' @param data A data frame.
#' @param signal_cols Optional character vector of biometric signal columns. If
#'   `NULL`, common Gazepoint biometric signal columns are detected.
#' @param group_cols Optional grouping columns. Runs are computed separately
#'   within each group.
#' @param time_col Optional time column used to order rows within each group
#'   before run detection. If `NULL`, the current row order is used.
#' @param min_missing_run Minimum consecutive missing/non-finite samples required
#'   to flag a missing dropout.
#' @param min_flatline_run Minimum consecutive unchanged finite samples required
#'   to flag a flatline dropout.
#' @param constant_tolerance Numeric tolerance used when detecting unchanged
#'   values for flatline runs.
#' @param prefix Prefix for generated dropout columns.
#'
#' @return The input data frame with added logical dropout columns. The attributes
#'   `dropout_summary` and `dropout_settings` contain structured summaries.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:8,
#'   GSR = c(1, NA, NA, NA, 2, 2, 2, 3),
#'   HR = c(70, 71, 72, 73, 74, 75, 76, 77)
#' )
#' flag_gazepoint_biometric_dropouts(df, min_missing_run = 3, min_flatline_run = 3)
#'
#' @export
flag_gazepoint_biometric_dropouts <- function(data,
                                              signal_cols = NULL,
                                              group_cols = NULL,
                                              time_col = NULL,
                                              min_missing_run = 5L,
                                              min_flatline_run = 10L,
                                              constant_tolerance = 0,
                                              prefix = "biometric_dropout") {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(signal_cols)) {
    .gpbiom_assert_columns(data, signal_cols, "signal_cols")
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
  }

  .gpbiom_assert_positive_integer(min_missing_run, "min_missing_run")
  .gpbiom_assert_positive_integer(min_flatline_run, "min_flatline_run")

  if (!is.numeric(constant_tolerance) ||
      length(constant_tolerance) != 1L ||
      is.na(constant_tolerance) ||
      constant_tolerance < 0) {
    stop("`constant_tolerance` must be a non-negative number.", call. = FALSE)
  }

  if (!is.character(prefix) || length(prefix) != 1L || is.na(prefix) ||
      !nzchar(prefix)) {
    stop("`prefix` must be a non-empty character string.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    signal_cols <- .gpbiom_detect_signal_columns(data)
  }

  out <- data

  if (length(signal_cols) == 0L) {
    any_col <- paste0(prefix, "_any")
    out[[any_col]] <- FALSE

    attr(out, "dropout_summary") <- .gpbiom_empty_dropout_summary()
    attr(out, "dropout_settings") <- list(
      signal_cols = signal_cols,
      group_cols = group_cols,
      time_col = time_col,
      min_missing_run = as.integer(min_missing_run),
      min_flatline_run = as.integer(min_flatline_run),
      constant_tolerance = constant_tolerance,
      prefix = prefix
    )

    return(out)
  }

  row_order_groups <- .gpbiom_group_indices(out, group_cols)

  added_signal_cols <- character()

  for (signal in signal_cols) {
    safe_signal <- .gpbiom_safe_colname(signal)

    missing_col <- paste0(prefix, "_", safe_signal, "_missing")
    flatline_col <- paste0(prefix, "_", safe_signal, "_flatline")
    signal_any_col <- paste0(prefix, "_", safe_signal, "_any")

    out[[missing_col]] <- FALSE
    out[[flatline_col]] <- FALSE

    for (indices in row_order_groups) {
      ordered_indices <- .gpbiom_order_indices(out, indices, time_col)
      values <- out[[signal]][ordered_indices]

      missing_flags <- .gpbiom_missing_run_flags(values, min_missing_run)
      flatline_flags <- .gpbiom_flatline_run_flags(
        values = values,
        min_flatline_run = min_flatline_run,
        constant_tolerance = constant_tolerance
      )

      out[[missing_col]][ordered_indices] <- missing_flags
      out[[flatline_col]][ordered_indices] <- flatline_flags
    }

    out[[signal_any_col]] <- out[[missing_col]] | out[[flatline_col]]
    added_signal_cols <- c(added_signal_cols, signal_any_col)
  }

  any_col <- paste0(prefix, "_any")
  out[[any_col]] <- Reduce(`|`, out[added_signal_cols])

  dropout_summary <- .gpbiom_dropout_summary(
    out = out,
    signal_cols = signal_cols,
    prefix = prefix
  )

  attr(out, "dropout_summary") <- dropout_summary
  attr(out, "dropout_settings") <- list(
    signal_cols = signal_cols,
    group_cols = group_cols,
    time_col = time_col,
    min_missing_run = as.integer(min_missing_run),
    min_flatline_run = as.integer(min_flatline_run),
    constant_tolerance = constant_tolerance,
    prefix = prefix
  )

  out
}


.gpbiom_assert_columns <- function(data, columns, argument_name) {
  if (!is.character(columns) || anyNA(columns)) {
    stop("`", argument_name, "` must be a character vector of column names.",
         call. = FALSE)
  }

  missing <- setdiff(columns, names(data))

  if (length(missing) > 0L) {
    stop(
      "`", argument_name, "` contains columns not found in `data`: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  invisible(TRUE)
}


.gpbiom_assert_positive_integer <- function(x, argument_name) {
  if (!is.numeric(x) ||
      length(x) != 1L ||
      is.na(x) ||
      x < 1 ||
      x != as.integer(x)) {
    stop("`", argument_name, "` must be a positive integer.", call. = FALSE)
  }

  invisible(TRUE)
}


.gpbiom_detect_signal_columns <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)

  signal_standards <- c(
    "GSR",
    "GSR_US",
    "GSR_OHMS",
    "HR",
    "IBI",
    "ENGAGEMENT"
  )

  mapping$original_name[mapping$standard_name %in% signal_standards]
}


.gpbiom_detect_validity_columns <- function(data) {
  mapping <- standardise_gazepoint_biometric_names(data, rename = FALSE)
  cleaned <- .gpbiom_clean_name(mapping$original_name)

  validity_like <- mapping$standard_name %in% c("HRV") |
    grepl("valid|validity|quality", cleaned)

  mapping$original_name[validity_like]
}


.gpbiom_signal_type <- function(column) {
  standard <- standardise_gazepoint_biometric_names(column)

  if (standard %in% c("GSR", "GSR_US", "GSR_OHMS")) {
    return("gsr_eda")
  }

  if (identical(standard, "HR")) {
    return("heart_rate")
  }

  if (identical(standard, "IBI")) {
    return("ibi")
  }

  if (identical(standard, "ENGAGEMENT")) {
    return("engagement_dial")
  }

  "other"
}


.gpbiom_summarise_signal_columns <- function(data,
                                             signal_cols,
                                             active_min_unique) {
  if (length(signal_cols) == 0L) {
    return(data.frame(
      column = character(),
      signal_type = character(),
      n = integer(),
      n_missing = integer(),
      missing_rate = numeric(),
      n_non_missing = integer(),
      n_finite = integer(),
      finite_rate = numeric(),
      n_unique_finite = integer(),
      mean = numeric(),
      median = numeric(),
      sd = numeric(),
      min = numeric(),
      max = numeric(),
      status = character(),
      stringsAsFactors = FALSE
    ))
  }

  rows <- lapply(signal_cols, function(column) {
    values <- data[[column]]
    n <- length(values)
    missing <- is.na(values)

    if (is.numeric(values)) {
      finite <- is.finite(values)
      finite_values <- values[finite]
      n_unique_finite <- length(unique(finite_values))

      status <- if (length(finite_values) == 0L) {
        "all_missing_or_nonfinite"
      } else if (n_unique_finite < active_min_unique) {
        "constant_or_low_variability_signal"
      } else {
        "active_signal"
      }

      data.frame(
        column = column,
        signal_type = .gpbiom_signal_type(column),
        n = n,
        n_missing = sum(missing),
        missing_rate = if (n > 0L) mean(missing) else NA_real_,
        n_non_missing = sum(!missing),
        n_finite = length(finite_values),
        finite_rate = if (n > 0L) length(finite_values) / n else NA_real_,
        n_unique_finite = n_unique_finite,
        mean = if (length(finite_values) > 0L) mean(finite_values) else NA_real_,
        median = if (length(finite_values) > 0L) stats::median(finite_values) else NA_real_,
        sd = if (length(finite_values) > 1L) stats::sd(finite_values) else NA_real_,
        min = if (length(finite_values) > 0L) min(finite_values) else NA_real_,
        max = if (length(finite_values) > 0L) max(finite_values) else NA_real_,
        status = status,
        stringsAsFactors = FALSE
      )
    } else {
      non_missing_values <- values[!missing]
      n_unique <- length(unique(non_missing_values))

      status <- if (length(non_missing_values) == 0L) {
        "all_missing"
      } else if (n_unique < active_min_unique) {
        "constant_or_low_variability_signal"
      } else {
        "non_numeric_signal_present"
      }

      data.frame(
        column = column,
        signal_type = .gpbiom_signal_type(column),
        n = n,
        n_missing = sum(missing),
        missing_rate = if (n > 0L) mean(missing) else NA_real_,
        n_non_missing = sum(!missing),
        n_finite = NA_integer_,
        finite_rate = NA_real_,
        n_unique_finite = NA_integer_,
        mean = NA_real_,
        median = NA_real_,
        sd = NA_real_,
        min = NA_real_,
        max = NA_real_,
        status = status,
        stringsAsFactors = FALSE
      )
    }
  })

  do.call(rbind, rows)
}


.gpbiom_summarise_validity_columns <- function(data, validity_cols) {
  if (length(validity_cols) == 0L) {
    return(data.frame(
      column = character(),
      standard_name = character(),
      n = integer(),
      n_missing = integer(),
      missing_rate = numeric(),
      n_valid_like = integer(),
      valid_like_rate = numeric(),
      n_invalid_like = integer(),
      invalid_like_rate = numeric(),
      interpretation_note = character(),
      stringsAsFactors = FALSE
    ))
  }

  rows <- lapply(validity_cols, function(column) {
    values <- data[[column]]
    n <- length(values)
    missing <- is.na(values)

    valid_like <- .gpbiom_valid_like(values)
    invalid_like <- .gpbiom_invalid_like(values)

    standard <- standardise_gazepoint_biometric_names(column)

    note <- if (identical(standard, "HRV")) {
      "Treated as a validity/vendor flag, not as an HRV metric."
    } else {
      "Detected as a validity-like column from its name."
    }

    data.frame(
      column = column,
      standard_name = standard,
      n = n,
      n_missing = sum(missing),
      missing_rate = if (n > 0L) mean(missing) else NA_real_,
      n_valid_like = sum(valid_like, na.rm = TRUE),
      valid_like_rate = if (n > 0L) mean(valid_like, na.rm = TRUE) else NA_real_,
      n_invalid_like = sum(invalid_like, na.rm = TRUE),
      invalid_like_rate = if (n > 0L) mean(invalid_like, na.rm = TRUE) else NA_real_,
      interpretation_note = note,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_valid_like <- function(values) {
  if (is.logical(values)) {
    return(!is.na(values) & values)
  }

  if (is.numeric(values)) {
    return(!is.na(values) & is.finite(values) & values > 0)
  }

  cleaned <- tolower(trimws(as.character(values)))

  !is.na(values) & cleaned %in% c(
    "1", "true", "valid", "yes", "y", "ok", "good", "pass"
  )
}


.gpbiom_invalid_like <- function(values) {
  if (is.logical(values)) {
    return(!is.na(values) & !values)
  }

  if (is.numeric(values)) {
    return(!is.na(values) & is.finite(values) & values <= 0)
  }

  cleaned <- tolower(trimws(as.character(values)))

  !is.na(values) & cleaned %in% c(
    "0", "false", "invalid", "no", "n", "bad", "fail"
  )
}


.gpbiom_summarise_signal_groups <- function(data,
                                            signal_cols,
                                            group_cols,
                                            active_min_unique) {
  if (length(signal_cols) == 0L || length(group_cols) == 0L) {
    return(data.frame(
      group = character(),
      signal_column_count = integer(),
      active_signal_count = integer(),
      status = character(),
      stringsAsFactors = FALSE
    ))
  }

  split_key <- interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  indices <- split(seq_len(nrow(data)), split_key)

  rows <- lapply(names(indices), function(group_name) {
    group_data <- data[indices[[group_name]], , drop = FALSE]
    signal_summary <- .gpbiom_summarise_signal_columns(
      data = group_data,
      signal_cols = signal_cols,
      active_min_unique = active_min_unique
    )

    active_signal_count <- sum(signal_summary$status == "active_signal")

    data.frame(
      group = group_name,
      n_rows = nrow(group_data),
      signal_column_count = length(signal_cols),
      active_signal_count = active_signal_count,
      status = if (active_signal_count == 0L) {
        "no_active_signals_in_group"
      } else if (active_signal_count < length(signal_cols)) {
        "some_signals_inactive_or_limited_in_group"
      } else {
        "signals_available_in_group"
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_group_indices <- function(data, group_cols) {
  if (length(group_cols) == 0L) {
    return(list(seq_len(nrow(data))))
  }

  split_key <- interaction(data[group_cols], drop = TRUE, lex.order = TRUE)
  unname(split(seq_len(nrow(data)), split_key))
}


.gpbiom_order_indices <- function(data, indices, time_col) {
  if (is.null(time_col)) {
    return(indices)
  }

  values <- data[[time_col]][indices]
  indices[order(values, na.last = TRUE)]
}


.gpbiom_missing_run_flags <- function(values, min_missing_run) {
  missing <- is.na(values)

  if (is.numeric(values)) {
    missing <- missing | !is.finite(values)
  }

  .gpbiom_run_flags(missing, min_missing_run)
}


.gpbiom_flatline_run_flags <- function(values,
                                       min_flatline_run,
                                       constant_tolerance) {
  if (!is.numeric(values)) {
    return(rep(FALSE, length(values)))
  }

  valid <- !is.na(values) & is.finite(values)

  if (length(values) == 0L || sum(valid) < min_flatline_run) {
    return(rep(FALSE, length(values)))
  }

  flags <- rep(FALSE, length(values))
  run_start <- NA_integer_
  run_length <- 0L

  for (i in seq_along(values)) {
    if (!valid[i]) {
      if (!is.na(run_start) && run_length >= min_flatline_run) {
        flags[run_start:(i - 1L)] <- TRUE
      }
      run_start <- NA_integer_
      run_length <- 0L
      next
    }

    if (is.na(run_start)) {
      run_start <- i
      run_length <- 1L
      next
    }

    previous <- values[i - 1L]

    if (valid[i - 1L] && abs(values[i] - previous) <= constant_tolerance) {
      run_length <- run_length + 1L
    } else {
      if (run_length >= min_flatline_run) {
        flags[run_start:(i - 1L)] <- TRUE
      }
      run_start <- i
      run_length <- 1L
    }
  }

  if (!is.na(run_start) && run_length >= min_flatline_run) {
    flags[run_start:length(values)] <- TRUE
  }

  flags
}


.gpbiom_run_flags <- function(condition, min_run) {
  condition[is.na(condition)] <- FALSE

  if (length(condition) == 0L || !any(condition)) {
    return(rep(FALSE, length(condition)))
  }

  run <- rle(condition)
  flags <- rep(FALSE, length(condition))
  ends <- cumsum(run$lengths)
  starts <- ends - run$lengths + 1L

  flagged_runs <- which(run$values & run$lengths >= min_run)

  for (i in flagged_runs) {
    flags[starts[i]:ends[i]] <- TRUE
  }

  flags
}


.gpbiom_safe_colname <- function(x) {
  cleaned <- gsub("[^A-Za-z0-9]+", "_", as.character(x))
  cleaned <- gsub("_+", "_", cleaned)
  cleaned <- gsub("^_|_$", "", cleaned)

  if (!nzchar(cleaned)) {
    cleaned <- "signal"
  }

  make.names(cleaned)
}


.gpbiom_dropout_summary <- function(out, signal_cols, prefix) {
  rows <- lapply(signal_cols, function(signal) {
    safe_signal <- .gpbiom_safe_colname(signal)

    missing_col <- paste0(prefix, "_", safe_signal, "_missing")
    flatline_col <- paste0(prefix, "_", safe_signal, "_flatline")
    any_col <- paste0(prefix, "_", safe_signal, "_any")

    data.frame(
      column = signal,
      signal_type = .gpbiom_signal_type(signal),
      n = nrow(out),
      n_missing_dropout = sum(out[[missing_col]], na.rm = TRUE),
      missing_dropout_rate = if (nrow(out) > 0L) {
        mean(out[[missing_col]], na.rm = TRUE)
      } else {
        NA_real_
      },
      n_flatline_dropout = sum(out[[flatline_col]], na.rm = TRUE),
      flatline_dropout_rate = if (nrow(out) > 0L) {
        mean(out[[flatline_col]], na.rm = TRUE)
      } else {
        NA_real_
      },
      n_any_dropout = sum(out[[any_col]], na.rm = TRUE),
      any_dropout_rate = if (nrow(out) > 0L) {
        mean(out[[any_col]], na.rm = TRUE)
      } else {
        NA_real_
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_empty_dropout_summary <- function() {
  data.frame(
    column = character(),
    signal_type = character(),
    n = integer(),
    n_missing_dropout = integer(),
    missing_dropout_rate = numeric(),
    n_flatline_dropout = integer(),
    flatline_dropout_rate = numeric(),
    n_any_dropout = integer(),
    any_dropout_rate = numeric(),
    stringsAsFactors = FALSE
  )
}
