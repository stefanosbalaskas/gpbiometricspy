#' Estimate lag between two Gazepoint biometric signals
#'
#' Estimates the time shift that maximizes the association between two recorded
#' biometric signals within each group. This is a conservative synchronization
#' diagnostic for inspecting whether two recorded traces show similar temporal
#' structure at different shifts. It should not be interpreted as causal timing
#' or true physiological latency unless the design includes appropriate event
#' markers and independently justified signal-processing assumptions.
#'
#' @param data A Gazepoint biometric data frame.
#' @param signal_x_col Name of the first signal column.
#' @param signal_y_col Name of the second signal column.
#' @param time_col Optional time or counter column. If `NULL`, a common
#'   Gazepoint time/counter column is detected.
#' @param group_cols Optional grouping columns, such as participant, stimulus,
#'   trial, or source file.
#' @param max_lag Maximum absolute lag to evaluate, in the same units as
#'   `time_col`.
#' @param lag_step Step size between candidate lags, in the same units as
#'   `time_col`. If `NULL`, the median positive time step is used.
#' @param method Correlation method passed to [stats::cor()].
#' @param min_complete_pairs Minimum complete aligned observations required for
#'   a candidate lag.
#' @param use_first_difference If `TRUE`, correlations are estimated on first
#'   differences rather than raw signal levels.
#'
#' @return A list with `overview`, `lag_by_group`, `lag_profile`, and `settings`.
#' @export
estimate_gazepoint_signal_lag <- function(data,
                                          signal_x_col,
                                          signal_y_col,
                                          time_col = NULL,
                                          group_cols = NULL,
                                          max_lag = 1000,
                                          lag_step = NULL,
                                          method = c("pearson", "spearman"),
                                          min_complete_pairs = 20,
                                          use_first_difference = FALSE) {
  method <- match.arg(method)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  gpbiometrics_sync_validate_col_name(signal_x_col, "signal_x_col")
  gpbiometrics_sync_validate_col_name(signal_y_col, "signal_y_col")

  if (!is.numeric(max_lag) || length(max_lag) != 1 ||
      is.na(max_lag) || max_lag < 0) {
    stop("`max_lag` must be a single non-negative number.", call. = FALSE)
  }

  if (!is.null(lag_step) &&
      (!is.numeric(lag_step) || length(lag_step) != 1 ||
       is.na(lag_step) || lag_step <= 0)) {
    stop("`lag_step` must be NULL or a single positive number.", call. = FALSE)
  }

  if (!is.numeric(min_complete_pairs) || length(min_complete_pairs) != 1 ||
      is.na(min_complete_pairs) || min_complete_pairs < 2) {
    stop("`min_complete_pairs` must be a single number >= 2.", call. = FALSE)
  }

  if (!is.logical(use_first_difference) ||
      length(use_first_difference) != 1 ||
      is.na(use_first_difference)) {
    stop("`use_first_difference` must be TRUE or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))
  names_dat <- names(dat)

  missing_signals <- setdiff(c(signal_x_col, signal_y_col), names_dat)

  if (length(missing_signals) > 0) {
    stop(
      "Signal columns not found in `data`: ",
      paste(missing_signals, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(time_col)) {
    time_col <- gpbiometrics_sync_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (is.null(time_col) || !time_col %in% names_dat) {
    stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_sync_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (nrow(dat) == 0) {
    lag_by_group <- gpbiometrics_sync_empty_lag_summary(group_cols)
    lag_profile <- gpbiometrics_sync_empty_lag_profile(group_cols)

    return(structure(
      list(
        overview = data.frame(
          input_rows = 0L,
          group_count = 0L,
          candidate_lag_count = 0L,
          estimated_group_count = 0L,
          status = "empty_input",
          interpretation = paste(
            "No rows were available for lag estimation.",
            "No synchronization inference can be made."
          ),
          stringsAsFactors = FALSE
        ),
        lag_by_group = lag_by_group,
        lag_profile = lag_profile,
        settings = list(
          signal_x_col = signal_x_col,
          signal_y_col = signal_y_col,
          time_col = time_col,
          group_cols = group_cols,
          max_lag = max_lag,
          lag_step = lag_step,
          method = method,
          min_complete_pairs = min_complete_pairs,
          use_first_difference = use_first_difference
        )
      ),
      class = c("gazepoint_signal_lag", "list")
    ))
  }

  time_value <- suppressWarnings(as.numeric(dat[[time_col]]))

  if (is.null(lag_step)) {
    lag_step <- gpbiometrics_sync_infer_lag_step(time_value)
  }

  lag_candidates <- gpbiometrics_sync_lag_candidates(max_lag, lag_step)

  dat$.gpbiometrics_group_id <- gpbiometrics_sync_group_id(dat, group_cols)
  group_indices <- split(seq_len(nrow(dat)), dat$.gpbiometrics_group_id, drop = TRUE)

  lag_summary_parts <- list()
  lag_profile_parts <- list()

  for (group_id in names(group_indices)) {
    idx <- group_indices[[group_id]]
    group_values <- gpbiometrics_sync_group_values(dat, group_cols, idx)

    series <- gpbiometrics_sync_prepare_series(
      time = suppressWarnings(as.numeric(dat[[time_col]][idx])),
      signal_x = suppressWarnings(as.numeric(dat[[signal_x_col]][idx])),
      signal_y = suppressWarnings(as.numeric(dat[[signal_y_col]][idx])),
      use_first_difference = use_first_difference
    )

    if (nrow(series) < min_complete_pairs) {
      summary_row <- data.frame(
        group_id = group_id,
        signal_x = signal_x_col,
        signal_y = signal_y_col,
        estimated_lag = NA_real_,
        selected_correlation = NA_real_,
        abs_selected_correlation = NA_real_,
        n_complete_pairs = 0L,
        candidate_count = length(lag_candidates),
        status = "insufficient_data",
        interpretation = paste(
          "Too few usable observations were available.",
          "No lag estimate should be interpreted for this group."
        ),
        stringsAsFactors = FALSE
      )

      lag_summary_parts[[length(lag_summary_parts) + 1L]] <-
        gpbiometrics_sync_prepend_group_values(group_values, summary_row)

      next
    }

    profile_rows <- lapply(lag_candidates, function(lag) {
      y_shifted <- stats::approx(
        x = series$time,
        y = series$signal_y,
        xout = series$time + lag,
        rule = 1,
        ties = mean
      )$y

      complete <- is.finite(series$signal_x) & is.finite(y_shifted)
      n_complete <- sum(complete)

      correlation <- NA_real_
      status <- "insufficient_complete_pairs"

      if (n_complete >= min_complete_pairs) {
        x_complete <- series$signal_x[complete]
        y_complete <- y_shifted[complete]

        if (length(unique(x_complete)) < 2 ||
            length(unique(y_complete)) < 2) {
          status <- "flat_signal"
        } else {
          correlation <- suppressWarnings(stats::cor(
            x_complete,
            y_complete,
            method = method,
            use = "complete.obs"
          ))

          if (is.finite(correlation)) {
            status <- "estimated"
          } else {
            status <- "correlation_unavailable"
          }
        }
      }

      row <- data.frame(
        group_id = group_id,
        signal_x = signal_x_col,
        signal_y = signal_y_col,
        lag = lag,
        n_complete_pairs = as.integer(n_complete),
        correlation = correlation,
        abs_correlation = abs(correlation),
        status = status,
        stringsAsFactors = FALSE
      )

      gpbiometrics_sync_prepend_group_values(group_values, row)
    })

    profile <- gpbiometrics_sync_rbind(profile_rows)
    lag_profile_parts[[length(lag_profile_parts) + 1L]] <- profile

    valid_profile <- profile[
      profile$status == "estimated" & is.finite(profile$correlation),
      ,
      drop = FALSE
    ]

    if (nrow(valid_profile) == 0) {
      summary_row <- data.frame(
        group_id = group_id,
        signal_x = signal_x_col,
        signal_y = signal_y_col,
        estimated_lag = NA_real_,
        selected_correlation = NA_real_,
        abs_selected_correlation = NA_real_,
        n_complete_pairs = max(profile$n_complete_pairs, na.rm = TRUE),
        candidate_count = nrow(profile),
        status = "no_valid_lag_profile",
        interpretation = paste(
          "Candidate lags were evaluated, but no stable finite correlation was available.",
          "No lag estimate should be interpreted for this group."
        ),
        stringsAsFactors = FALSE
      )
    } else {
      best <- valid_profile[which.max(abs(valid_profile$correlation)), , drop = FALSE]

      summary_row <- data.frame(
        group_id = group_id,
        signal_x = signal_x_col,
        signal_y = signal_y_col,
        estimated_lag = best$lag[1],
        selected_correlation = best$correlation[1],
        abs_selected_correlation = abs(best$correlation[1]),
        n_complete_pairs = as.integer(best$n_complete_pairs[1]),
        candidate_count = nrow(profile),
        status = "estimated",
        interpretation = paste(
          "Estimated lag maximizes absolute signal association within the tested range.",
          "Use as a synchronization QC diagnostic only, not as evidence of causal timing or physiological latency."
        ),
        stringsAsFactors = FALSE
      )
    }

    lag_summary_parts[[length(lag_summary_parts) + 1L]] <-
      gpbiometrics_sync_prepend_group_values(group_values, summary_row)
  }

  lag_by_group <- gpbiometrics_sync_rbind(lag_summary_parts)
  lag_profile <- gpbiometrics_sync_rbind(lag_profile_parts)

  estimated_group_count <- sum(lag_by_group$status == "estimated", na.rm = TRUE)

  overview_status <- if (estimated_group_count > 0) {
    "estimated"
  } else {
    "no_valid_estimates"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    group_count = length(group_indices),
    candidate_lag_count = length(lag_candidates),
    estimated_group_count = as.integer(estimated_group_count),
    status = overview_status,
    interpretation = paste(
      "Lag estimates are conservative signal-alignment diagnostics.",
      "They do not establish true physiological latency, causality, emotion, cognition, trust, or preference."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      lag_by_group = lag_by_group,
      lag_profile = lag_profile,
      settings = list(
        signal_x_col = signal_x_col,
        signal_y_col = signal_y_col,
        time_col = time_col,
        group_cols = group_cols,
        max_lag = max_lag,
        lag_step = lag_step,
        method = method,
        min_complete_pairs = min_complete_pairs,
        use_first_difference = use_first_difference
      )
    ),
    class = c("gazepoint_signal_lag", "list")
  )
}

#' Audit Gazepoint biometric synchronization drift
#'
#' Combines time-order/reset diagnostics with conservative signal-lag summaries
#' across signal pairs and groups. The helper is intended for quality control and
#' synchronization review. It does not infer emotional valence, cognitive states,
#' causal timing, or true physiological latency.
#'
#' @param data A Gazepoint biometric data frame.
#' @param time_col Optional time or counter column.
#' @param group_cols Optional grouping columns.
#' @param signal_pairs Optional two-column data frame, matrix, or list defining
#'   signal pairs. If `NULL`, pairs are formed between a reference signal and
#'   other detected biometric signals.
#' @param signal_cols Optional candidate signal columns used when `signal_pairs`
#'   is `NULL`.
#' @param reference_signal_col Optional reference signal used when `signal_pairs`
#'   is `NULL`.
#' @param max_lag Maximum absolute lag to evaluate, in the same units as
#'   `time_col`.
#' @param lag_step Step size between candidate lags. If `NULL`, the median
#'   positive time step is used.
#' @param drift_tolerance Optional threshold for the range of estimated lags
#'   across groups. If `NULL`, drift is summarized but not threshold-classified.
#' @param method Correlation method passed to [stats::cor()].
#' @param min_complete_pairs Minimum complete aligned observations required for
#'   each candidate lag.
#' @param use_first_difference If `TRUE`, lag diagnostics use first differences.
#' @param include_reset_segments If `TRUE`, reset segments from
#'   [audit_gazepoint_time_resets()] are added to grouping when available.
#'
#' @return A list with `overview`, `checks`, `time_reset_audit`,
#'   `lag_by_group`, `lag_profile`, `drift_summary`, and `settings`.
#' @export
audit_gazepoint_biometric_sync_drift <- function(data,
                                                 time_col = NULL,
                                                 group_cols = NULL,
                                                 signal_pairs = NULL,
                                                 signal_cols = NULL,
                                                 reference_signal_col = NULL,
                                                 max_lag = 1000,
                                                 lag_step = NULL,
                                                 drift_tolerance = NULL,
                                                 method = c("pearson", "spearman"),
                                                 min_complete_pairs = 20,
                                                 use_first_difference = FALSE,
                                                 include_reset_segments = TRUE) {
  method <- match.arg(method)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(drift_tolerance) &&
      (!is.numeric(drift_tolerance) || length(drift_tolerance) != 1 ||
       is.na(drift_tolerance) || drift_tolerance < 0)) {
    stop("`drift_tolerance` must be NULL or a single non-negative number.", call. = FALSE)
  }

  if (!is.logical(include_reset_segments) ||
      length(include_reset_segments) != 1 ||
      is.na(include_reset_segments)) {
    stop("`include_reset_segments` must be TRUE or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  names_dat <- names(dat)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_sync_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (is.null(time_col) || !time_col %in% names_dat) {
    stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_sync_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  time_reset_audit <- tryCatch(
    audit_gazepoint_time_resets(
      dat,
      time_col = time_col,
      group_cols = group_cols,
      allow_ties = TRUE,
      split_on_negative_step = TRUE,
      return_reindexed_time = FALSE,
      min_segment_rows = 1
    ),
    error = function(e) {
      structure(
        list(
          overview = data.frame(
            status = "time_reset_audit_failed",
            detail = conditionMessage(e),
            stringsAsFactors = FALSE
          ),
          row_flags = data.frame(stringsAsFactors = FALSE),
          data_with_segments = dat
        ),
        class = c("gazepoint_time_reset_audit_failed", "list")
      )
    }
  )

  time_reset_issue_count <- gpbiometrics_sync_time_reset_issue_count(time_reset_audit)

  lag_data <- dat
  lag_group_cols <- group_cols

  if (isTRUE(include_reset_segments) &&
      is.list(time_reset_audit) &&
      is.data.frame(time_reset_audit$data_with_segments) &&
      "reset_segment_index" %in% names(time_reset_audit$data_with_segments)) {
    lag_data <- as.data.frame(time_reset_audit$data_with_segments, stringsAsFactors = FALSE)
    lag_group_cols <- unique(c(group_cols, "reset_segment_index"))
  }

  pair_table <- gpbiometrics_sync_resolve_signal_pairs(
    names_dat = names(lag_data),
    signal_pairs = signal_pairs,
    signal_cols = signal_cols,
    reference_signal_col = reference_signal_col
  )

  if (nrow(pair_table) == 0) {
    empty_lag_by_group <- gpbiometrics_sync_empty_lag_summary(lag_group_cols)
    empty_lag_profile <- gpbiometrics_sync_empty_lag_profile(lag_group_cols)
    empty_drift <- gpbiometrics_sync_empty_drift_summary()

    checks <- data.frame(
      check = c("time_order", "lag_estimation", "drift_variability"),
      status = c(
        if (is.na(time_reset_issue_count)) "not_available" else if (time_reset_issue_count > 0) "warn" else "pass",
        "warn",
        "not_available"
      ),
      detail = c(
        gpbiometrics_sync_time_reset_detail(time_reset_issue_count),
        "No usable signal pairs were available for lag estimation.",
        "Drift variability was not evaluated because no signal pairs were available."
      ),
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = data.frame(
          input_rows = nrow(dat),
          signal_pair_count = 0L,
          lag_estimate_rows = 0L,
          drift_rows = 0L,
          time_reset_issue_count = time_reset_issue_count,
          drift_issue_count = 0L,
          status = "no_signal_pairs",
          interpretation = paste(
            "No signal-pair synchronization diagnostic was computed.",
            "No synchronization or drift inference can be made."
          ),
          stringsAsFactors = FALSE
        ),
        checks = checks,
        time_reset_audit = time_reset_audit,
        lag_by_group = empty_lag_by_group,
        lag_profile = empty_lag_profile,
        drift_summary = empty_drift,
        settings = list(
          time_col = time_col,
          group_cols = group_cols,
          lag_group_cols = lag_group_cols,
          signal_pairs = pair_table,
          max_lag = max_lag,
          lag_step = lag_step,
          drift_tolerance = drift_tolerance,
          method = method,
          min_complete_pairs = min_complete_pairs,
          use_first_difference = use_first_difference,
          include_reset_segments = include_reset_segments
        )
      ),
      class = c("gazepoint_biometric_sync_drift_audit", "list")
    ))
  }

  lag_results <- lapply(seq_len(nrow(pair_table)), function(i) {
    pair <- pair_table[i, , drop = FALSE]

    out <- estimate_gazepoint_signal_lag(
      data = lag_data,
      signal_x_col = pair$signal_x,
      signal_y_col = pair$signal_y,
      time_col = time_col,
      group_cols = lag_group_cols,
      max_lag = max_lag,
      lag_step = lag_step,
      method = method,
      min_complete_pairs = min_complete_pairs,
      use_first_difference = use_first_difference
    )

    pair_id <- paste(pair$signal_x, pair$signal_y, sep = "__vs__")

    out$lag_by_group$pair_id <- pair_id
    out$lag_profile$pair_id <- pair_id

    out$lag_by_group$signal_x <- pair$signal_x
    out$lag_by_group$signal_y <- pair$signal_y
    out$lag_profile$signal_x <- pair$signal_x
    out$lag_profile$signal_y <- pair$signal_y

    out
  })

  lag_by_group <- gpbiometrics_sync_rbind(lapply(lag_results, `[[`, "lag_by_group"))
  lag_profile <- gpbiometrics_sync_rbind(lapply(lag_results, `[[`, "lag_profile"))

  drift_summary <- gpbiometrics_sync_make_drift_summary(
    lag_by_group = lag_by_group,
    pair_table = pair_table,
    drift_tolerance = drift_tolerance
  )

  lag_estimate_rows <- sum(lag_by_group$status == "estimated", na.rm = TRUE)
  drift_issue_count <- sum(drift_summary$status == "drift_exceeds_tolerance", na.rm = TRUE)

  checks <- data.frame(
    check = c("time_order", "lag_estimation", "drift_variability"),
    status = c(
      if (is.na(time_reset_issue_count)) {
        "not_available"
      } else if (time_reset_issue_count > 0) {
        "warn"
      } else {
        "pass"
      },
      if (lag_estimate_rows > 0) "pass" else "warn",
      if (is.null(drift_tolerance)) {
        "info"
      } else if (drift_issue_count > 0) {
        "warn"
      } else {
        "pass"
      }
    ),
    detail = c(
      gpbiometrics_sync_time_reset_detail(time_reset_issue_count),
      if (lag_estimate_rows > 0) {
        paste(lag_estimate_rows, "group-level lag estimate(s) were available.")
      } else {
        "No valid group-level lag estimates were available."
      },
      if (is.null(drift_tolerance)) {
        "Drift range was summarized without threshold classification."
      } else if (drift_issue_count > 0) {
        paste(drift_issue_count, "signal pair(s) exceeded the drift tolerance.")
      } else {
        "No signal pair exceeded the supplied drift tolerance."
      }
    ),
    stringsAsFactors = FALSE
  )

  overall_status <- if (lag_estimate_rows == 0) {
    "insufficient_lag_evidence"
  } else if ((!is.na(time_reset_issue_count) && time_reset_issue_count > 0) ||
             drift_issue_count > 0) {
    "review_recommended"
  } else {
    "diagnostic_complete"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    signal_pair_count = nrow(pair_table),
    lag_estimate_rows = as.integer(lag_estimate_rows),
    drift_rows = nrow(drift_summary),
    time_reset_issue_count = time_reset_issue_count,
    drift_issue_count = as.integer(drift_issue_count),
    status = overall_status,
    interpretation = paste(
      "Synchronization drift output is a conservative QC diagnostic.",
      "It does not establish true physiological latency, causal timing, emotional valence, cognition, trust, preference, or evaluation."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      checks = checks,
      time_reset_audit = time_reset_audit,
      lag_by_group = lag_by_group,
      lag_profile = lag_profile,
      drift_summary = drift_summary,
      settings = list(
        time_col = time_col,
        group_cols = group_cols,
        lag_group_cols = lag_group_cols,
        signal_pairs = pair_table,
        max_lag = max_lag,
        lag_step = lag_step,
        drift_tolerance = drift_tolerance,
        method = method,
        min_complete_pairs = min_complete_pairs,
        use_first_difference = use_first_difference,
        include_reset_segments = include_reset_segments
      )
    ),
    class = c("gazepoint_biometric_sync_drift_audit", "list")
  )
}

gpbiometrics_sync_validate_col_name <- function(x, arg) {
  if (!is.character(x) || length(x) != 1 || is.na(x) || !nzchar(x)) {
    stop("`", arg, "` must be a single non-empty character value.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_sync_first_existing <- function(names_dat, candidates) {
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

gpbiometrics_sync_resolve_group_cols <- function(names_dat, group_cols) {
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

gpbiometrics_sync_group_id <- function(dat, group_cols) {
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

gpbiometrics_sync_group_values <- function(dat, group_cols, idx) {
  if (length(group_cols) == 0) {
    return(NULL)
  }

  out <- as.data.frame(dat[idx[1], group_cols, drop = FALSE], stringsAsFactors = FALSE)
  rownames(out) <- NULL
  out
}

gpbiometrics_sync_prepend_group_values <- function(group_values, row) {
  row <- as.data.frame(row, stringsAsFactors = FALSE)
  rownames(row) <- NULL

  if (is.null(group_values) || ncol(group_values) == 0) {
    return(row)
  }

  group_values <- as.data.frame(group_values, stringsAsFactors = FALSE)
  rownames(group_values) <- NULL

  cbind(group_values, row, stringsAsFactors = FALSE)
}

gpbiometrics_sync_rbind <- function(x) {
  x <- x[!vapply(x, is.null, logical(1))]

  if (length(x) == 0) {
    return(data.frame(stringsAsFactors = FALSE))
  }

  out <- do.call(rbind, x)
  rownames(out) <- NULL
  out
}

gpbiometrics_sync_infer_lag_step <- function(time_value) {
  time_value <- suppressWarnings(as.numeric(time_value))
  time_value <- time_value[is.finite(time_value)]

  if (length(time_value) < 2) {
    return(1)
  }

  time_value <- sort(unique(time_value))
  delta <- diff(time_value)
  delta <- delta[is.finite(delta) & delta > 0]

  if (length(delta) == 0) {
    return(1)
  }

  stats::median(delta)
}

gpbiometrics_sync_lag_candidates <- function(max_lag, lag_step) {
  if (max_lag == 0) {
    return(0)
  }

  out <- seq(-max_lag, max_lag, by = lag_step)

  if (!any(abs(out) < sqrt(.Machine$double.eps))) {
    out <- c(out, 0)
  }

  sort(unique(out))
}

gpbiometrics_sync_prepare_series <- function(time,
                                             signal_x,
                                             signal_y,
                                             use_first_difference = FALSE) {
  time <- suppressWarnings(as.numeric(time))
  signal_x <- suppressWarnings(as.numeric(signal_x))
  signal_y <- suppressWarnings(as.numeric(signal_y))

  ok_time <- is.finite(time)

  time <- time[ok_time]
  signal_x <- signal_x[ok_time]
  signal_y <- signal_y[ok_time]

  if (length(time) == 0) {
    return(data.frame(
      time = numeric(),
      signal_x = numeric(),
      signal_y = numeric(),
      stringsAsFactors = FALSE
    ))
  }

  ord <- order(time)
  time <- time[ord]
  signal_x <- signal_x[ord]
  signal_y <- signal_y[ord]

  unique_time <- sort(unique(time))

  x_mean <- vapply(unique_time, function(tt) {
    value <- signal_x[time == tt]
    value <- value[is.finite(value)]

    if (length(value) == 0) {
      NA_real_
    } else {
      mean(value)
    }
  }, numeric(1))

  y_mean <- vapply(unique_time, function(tt) {
    value <- signal_y[time == tt]
    value <- value[is.finite(value)]

    if (length(value) == 0) {
      NA_real_
    } else {
      mean(value)
    }
  }, numeric(1))

  out <- data.frame(
    time = unique_time,
    signal_x = x_mean,
    signal_y = y_mean,
    stringsAsFactors = FALSE
  )

  if (isTRUE(use_first_difference)) {
    if (nrow(out) < 3) {
      return(out[0, , drop = FALSE])
    }

    out <- data.frame(
      time = out$time[-1],
      signal_x = diff(out$signal_x),
      signal_y = diff(out$signal_y),
      stringsAsFactors = FALSE
    )
  }

  out
}

gpbiometrics_sync_empty_lag_summary <- function(group_cols = character()) {
  out <- data.frame(
    group_id = character(),
    signal_x = character(),
    signal_y = character(),
    estimated_lag = numeric(),
    selected_correlation = numeric(),
    abs_selected_correlation = numeric(),
    n_complete_pairs = integer(),
    candidate_count = integer(),
    status = character(),
    interpretation = character(),
    stringsAsFactors = FALSE
  )

  if (length(group_cols) == 0) {
    return(out)
  }

  group_data <- as.data.frame(
    stats::setNames(
      rep(list(character()), length(group_cols)),
      group_cols
    ),
    stringsAsFactors = FALSE
  )

  cbind(group_data, out, stringsAsFactors = FALSE)
}

gpbiometrics_sync_empty_lag_profile <- function(group_cols = character()) {
  out <- data.frame(
    group_id = character(),
    signal_x = character(),
    signal_y = character(),
    lag = numeric(),
    n_complete_pairs = integer(),
    correlation = numeric(),
    abs_correlation = numeric(),
    status = character(),
    stringsAsFactors = FALSE
  )

  if (length(group_cols) == 0) {
    return(out)
  }

  group_data <- as.data.frame(
    stats::setNames(
      rep(list(character()), length(group_cols)),
      group_cols
    ),
    stringsAsFactors = FALSE
  )

  cbind(group_data, out, stringsAsFactors = FALSE)
}

gpbiometrics_sync_infer_signal_cols <- function(names_dat) {
  candidates <- c(
    "GSR_US",
    "GSR_US_PHASIC",
    "GSR_US_TONIC",
    "GSR",
    "EDA",
    "eda",
    "eda_clean",
    "eda_phasic",
    "HR",
    "hr",
    "HRP",
    "hrp",
    "IBI",
    "ibi",
    "IBI_clean_ms",
    "DIAL",
    "dial"
  )

  out <- character()

  for (candidate in candidates) {
    idx <- match(tolower(candidate), tolower(names_dat))

    if (!is.na(idx)) {
      out <- c(out, names_dat[idx])
    }
  }

  unique(out)
}

gpbiometrics_sync_resolve_signal_pairs <- function(names_dat,
                                                   signal_pairs = NULL,
                                                   signal_cols = NULL,
                                                   reference_signal_col = NULL) {
  explicit_pairs <- !is.null(signal_pairs)

  if (!is.null(signal_pairs)) {
    if (is.data.frame(signal_pairs)) {
      if (all(c("signal_x", "signal_y") %in% names(signal_pairs))) {
        out <- data.frame(
          signal_x = as.character(signal_pairs$signal_x),
          signal_y = as.character(signal_pairs$signal_y),
          stringsAsFactors = FALSE
        )
      } else if (ncol(signal_pairs) >= 2) {
        out <- data.frame(
          signal_x = as.character(signal_pairs[[1]]),
          signal_y = as.character(signal_pairs[[2]]),
          stringsAsFactors = FALSE
        )
      } else {
        stop("`signal_pairs` must have at least two columns.", call. = FALSE)
      }
    } else if (is.matrix(signal_pairs) && ncol(signal_pairs) >= 2) {
      out <- data.frame(
        signal_x = as.character(signal_pairs[, 1]),
        signal_y = as.character(signal_pairs[, 2]),
        stringsAsFactors = FALSE
      )
    } else if (is.list(signal_pairs)) {
      pair_list <- lapply(signal_pairs, function(x) {
        x <- unlist(x, use.names = FALSE)

        if (length(x) < 2) {
          stop("Each element of `signal_pairs` must contain at least two signal names.", call. = FALSE)
        }

        x[1:2]
      })

      pair_matrix <- do.call(rbind, pair_list)

      out <- data.frame(
        signal_x = as.character(pair_matrix[, 1]),
        signal_y = as.character(pair_matrix[, 2]),
        stringsAsFactors = FALSE
      )
    } else {
      stop(
        "`signal_pairs` must be NULL, a two-column data frame, a matrix, or a list of pairs.",
        call. = FALSE
      )
    }
  } else {
    if (is.null(signal_cols)) {
      signal_cols <- gpbiometrics_sync_infer_signal_cols(names_dat)
    }

    signal_cols <- unique(as.character(signal_cols))
    signal_cols <- signal_cols[signal_cols %in% names_dat]

    if (length(signal_cols) < 2) {
      return(data.frame(
        signal_x = character(),
        signal_y = character(),
        stringsAsFactors = FALSE
      ))
    }

    if (is.null(reference_signal_col)) {
      preferred <- c("GSR_US", "GSR_US_PHASIC", "GSR", "EDA", "HR", "HRP", "DIAL")
      reference_signal_col <- NULL

      for (candidate in preferred) {
        idx <- match(tolower(candidate), tolower(signal_cols))

        if (!is.na(idx)) {
          reference_signal_col <- signal_cols[idx]
          break
        }
      }

      if (is.null(reference_signal_col)) {
        reference_signal_col <- signal_cols[1]
      }
    }

    if (!reference_signal_col %in% signal_cols) {
      stop("`reference_signal_col` must be included in `signal_cols`.", call. = FALSE)
    }

    other_signals <- setdiff(signal_cols, reference_signal_col)

    out <- data.frame(
      signal_x = reference_signal_col,
      signal_y = other_signals,
      stringsAsFactors = FALSE
    )
  }

  out$signal_x <- as.character(out$signal_x)
  out$signal_y <- as.character(out$signal_y)

  out <- out[
    !is.na(out$signal_x) &
      !is.na(out$signal_y) &
      nzchar(out$signal_x) &
      nzchar(out$signal_y) &
      out$signal_x != out$signal_y,
    ,
    drop = FALSE
  ]

  out <- unique(out)

  missing_cols <- setdiff(unique(c(out$signal_x, out$signal_y)), names_dat)

  if (length(missing_cols) > 0 && isTRUE(explicit_pairs)) {
    stop(
      "Signal columns in `signal_pairs` were not found in `data`: ",
      paste(missing_cols, collapse = ", "),
      call. = FALSE
    )
  }

  out <- out[out$signal_x %in% names_dat & out$signal_y %in% names_dat, , drop = FALSE]
  rownames(out) <- NULL

  out
}

gpbiometrics_sync_time_reset_issue_count <- function(time_reset_audit) {
  if (!is.list(time_reset_audit) || !is.data.frame(time_reset_audit$row_flags)) {
    return(NA_integer_)
  }

  row_flags <- time_reset_audit$row_flags

  issue_cols <- intersect(
    c("flag_nonfinite_time", "flag_negative_step", "flag_nonmonotonic"),
    names(row_flags)
  )

  if (length(issue_cols) == 0) {
    return(NA_integer_)
  }

  issue_matrix <- row_flags[issue_cols]
  issue_matrix[] <- lapply(issue_matrix, function(x) {
    x <- as.logical(x)
    x[is.na(x)] <- FALSE
    x
  })

  as.integer(sum(rowSums(issue_matrix) > 0, na.rm = TRUE))
}

gpbiometrics_sync_time_reset_detail <- function(time_reset_issue_count) {
  if (is.na(time_reset_issue_count)) {
    return("Time reset audit was not available.")
  }

  if (time_reset_issue_count > 0) {
    return(paste(
      time_reset_issue_count,
      "row(s) had nonfinite, negative-step, or nonmonotonic time flags."
    ))
  }

  "No nonfinite, negative-step, or nonmonotonic time flags were detected."
}

gpbiometrics_sync_make_drift_summary <- function(lag_by_group,
                                                 pair_table,
                                                 drift_tolerance = NULL) {
  if (!is.data.frame(lag_by_group) || nrow(pair_table) == 0) {
    return(gpbiometrics_sync_empty_drift_summary())
  }

  out <- lapply(seq_len(nrow(pair_table)), function(i) {
    signal_x <- pair_table$signal_x[i]
    signal_y <- pair_table$signal_y[i]
    pair_id <- paste(signal_x, signal_y, sep = "__vs__")

    d <- lag_by_group[
      lag_by_group$pair_id == pair_id &
        lag_by_group$status == "estimated" &
        is.finite(lag_by_group$estimated_lag),
      ,
      drop = FALSE
    ]

    n_estimates <- nrow(d)

    if (n_estimates == 0) {
      lag_min <- NA_real_
      lag_max <- NA_real_
      lag_range <- NA_real_
      lag_median <- NA_real_
      lag_sd <- NA_real_
      max_abs_lag <- NA_real_
      status <- "no_estimates"
      interpretation <- paste(
        "No valid lag estimates were available for this signal pair.",
        "No drift interpretation should be made."
      )
    } else {
      lag_min <- min(d$estimated_lag, na.rm = TRUE)
      lag_max <- max(d$estimated_lag, na.rm = TRUE)
      lag_range <- lag_max - lag_min
      lag_median <- stats::median(d$estimated_lag, na.rm = TRUE)
      lag_sd <- if (n_estimates > 1) stats::sd(d$estimated_lag, na.rm = TRUE) else NA_real_
      max_abs_lag <- max(abs(d$estimated_lag), na.rm = TRUE)

      if (n_estimates == 1) {
        status <- "single_estimate"
        interpretation <- paste(
          "Only one group-level lag estimate was available.",
          "Between-group drift variability cannot be assessed."
        )
      } else if (is.null(drift_tolerance)) {
        status <- "estimated_no_tolerance"
        interpretation <- paste(
          "Lag variability was summarized without threshold classification.",
          "Use as a descriptive synchronization QC diagnostic only."
        )
      } else if (lag_range > drift_tolerance) {
        status <- "drift_exceeds_tolerance"
        interpretation <- paste(
          "Estimated lag range exceeded the supplied tolerance.",
          "Manual synchronization review is recommended."
        )
      } else {
        status <- "drift_within_tolerance"
        interpretation <- paste(
          "Estimated lag range was within the supplied tolerance.",
          "This supports QC consistency only and does not prove true physiological synchronization."
        )
      }
    }

    data.frame(
      pair_id = pair_id,
      signal_x = signal_x,
      signal_y = signal_y,
      n_estimates = as.integer(n_estimates),
      lag_min = lag_min,
      lag_median = lag_median,
      lag_max = lag_max,
      lag_range = lag_range,
      lag_sd = lag_sd,
      max_abs_lag = max_abs_lag,
      drift_tolerance = if (is.null(drift_tolerance)) NA_real_ else drift_tolerance,
      status = status,
      interpretation = interpretation,
      stringsAsFactors = FALSE
    )
  })

  gpbiometrics_sync_rbind(out)
}

gpbiometrics_sync_empty_drift_summary <- function() {
  data.frame(
    pair_id = character(),
    signal_x = character(),
    signal_y = character(),
    n_estimates = integer(),
    lag_min = numeric(),
    lag_median = numeric(),
    lag_max = numeric(),
    lag_range = numeric(),
    lag_sd = numeric(),
    max_abs_lag = numeric(),
    drift_tolerance = numeric(),
    status = character(),
    interpretation = character(),
    stringsAsFactors = FALSE
  )
}
