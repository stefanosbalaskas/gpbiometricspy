#' Audit Gazepoint biometric time resets
#'
#' Detects negative time steps, duplicate time steps, non-finite time values, and
#' recording segments within grouped Gazepoint biometric exports. This helper is
#' intended for quality control and synchronization inspection. It does not alter
#' raw values unless `return_reindexed_time = TRUE`, in which case an additional
#' segment-relative time column is added.
#'
#' @param data A data frame containing Gazepoint biometric rows.
#' @param time_col Optional time/counter column. If `NULL`, common Gazepoint time
#'   columns are detected automatically.
#' @param group_cols Optional grouping columns. If `NULL`, available
#'   source/participant/media/trial-like columns are used.
#' @param allow_ties Logical. If `TRUE`, repeated time values are not treated as
#'   non-monotonic.
#' @param split_on_negative_step Logical. If `TRUE`, negative time steps start a
#'   new segment within each group.
#' @param return_reindexed_time Logical. If `TRUE`, adds
#'   `time_reindexed_within_segment`, starting at zero within each detected
#'   segment.
#' @param min_segment_rows Minimum rows expected per segment before a segment is
#'   flagged as short.
#'
#' @return A list with `overview`, `segment_summary`, `row_flags`,
#'   `data_with_segments`, and `settings`.
#' @export
audit_gazepoint_time_resets <- function(data,
                                        time_col = NULL,
                                        group_cols = NULL,
                                        allow_ties = TRUE,
                                        split_on_negative_step = TRUE,
                                        return_reindexed_time = FALSE,
                                        min_segment_rows = 1) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.logical(allow_ties) || length(allow_ties) != 1) {
    stop("`allow_ties` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(split_on_negative_step) || length(split_on_negative_step) != 1) {
    stop("`split_on_negative_step` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(return_reindexed_time) || length(return_reindexed_time) != 1) {
    stop("`return_reindexed_time` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(min_segment_rows) || length(min_segment_rows) != 1 || min_segment_rows < 1) {
    stop("`min_segment_rows` must be a positive number.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  names_dat <- names(dat)

  if (is.null(time_col)) {
    time_col <- gpbiometrics_time_qc_first_existing(
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

  group_cols <- gpbiometrics_time_qc_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  time_value <- suppressWarnings(as.numeric(dat[[time_col]]))

  row_flags <- data.frame(
    .gpbiometrics_row_id = dat$.gpbiometrics_row_id,
    time_col = time_col,
    time_value = time_value,
    group_id = gpbiometrics_time_qc_group_id(dat, group_cols),
    group_row_index = NA_integer_,
    time_delta = NA_real_,
    flag_nonfinite_time = !is.finite(time_value),
    flag_negative_step = FALSE,
    flag_duplicate_time = FALSE,
    flag_nonmonotonic = FALSE,
    reset_segment_index = NA_integer_,
    flag_short_segment = FALSE,
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0) {
    row_flags <- cbind(dat[group_cols], row_flags)
  }

  group_indices <- split(seq_len(nrow(dat)), row_flags$group_id, drop = TRUE)

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]
    row_flags$group_row_index[idx] <- seq_along(idx)

    x <- time_value[idx]
    delta <- c(NA_real_, diff(x))

    negative_step <- is.finite(delta) & delta < 0
    duplicate_step <- is.finite(delta) & delta == 0

    nonmonotonic <- negative_step
    if (!isTRUE(allow_ties)) {
      nonmonotonic <- is.finite(delta) & delta <= 0
    }

    row_flags$time_delta[idx] <- delta
    row_flags$flag_negative_step[idx] <- negative_step
    row_flags$flag_duplicate_time[idx] <- duplicate_step
    row_flags$flag_nonmonotonic[idx] <- nonmonotonic

    if (isTRUE(split_on_negative_step)) {
      row_flags$reset_segment_index[idx] <- cumsum(negative_step) + 1L
    } else {
      row_flags$reset_segment_index[idx] <- 1L
    }
  }

  segment_summary <- gpbiometrics_time_qc_segment_summary(
    dat = dat,
    row_flags = row_flags,
    group_cols = group_cols,
    min_segment_rows = min_segment_rows
  )

  if (nrow(segment_summary) > 0) {
    short_segments <- segment_summary$segment_key[
      segment_summary$rows < min_segment_rows
    ]

    row_flags$flag_short_segment <- paste(
      row_flags$group_id,
      row_flags$reset_segment_index,
      sep = "||segment_"
    ) %in% short_segments
  }

  data_with_segments <- dat
  data_with_segments$time_qc_group_id <- row_flags$group_id
  data_with_segments$time_qc_group_row_index <- row_flags$group_row_index
  data_with_segments$time_qc_delta <- row_flags$time_delta
  data_with_segments$time_qc_negative_step <- row_flags$flag_negative_step
  data_with_segments$time_qc_duplicate_step <- row_flags$flag_duplicate_time
  data_with_segments$time_qc_nonmonotonic <- row_flags$flag_nonmonotonic
  data_with_segments$time_qc_segment_index <- row_flags$reset_segment_index

  if (isTRUE(return_reindexed_time)) {
    data_with_segments$time_reindexed_within_segment <- gpbiometrics_time_qc_reindex_time(
      time_value = time_value,
      group_id = row_flags$group_id,
      segment_index = row_flags$reset_segment_index
    )
  }

  n_negative_steps <- sum(row_flags$flag_negative_step, na.rm = TRUE)
  n_duplicate_steps <- sum(row_flags$flag_duplicate_time, na.rm = TRUE)
  n_nonmonotonic <- sum(row_flags$flag_nonmonotonic, na.rm = TRUE)
  n_nonfinite <- sum(row_flags$flag_nonfinite_time, na.rm = TRUE)
  affected_groups <- length(unique(row_flags$group_id[row_flags$flag_negative_step]))

  status <- if (all(is.na(time_value))) {
    "fail_no_numeric_time"
  } else if (n_negative_steps > 0 || n_nonmonotonic > 0 || n_nonfinite > 0) {
    "warn_time_irregularities_detected"
  } else {
    "pass"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    time_col = time_col,
    group_count = length(group_indices),
    segment_count = nrow(segment_summary),
    negative_steps = n_negative_steps,
    duplicate_steps = n_duplicate_steps,
    nonmonotonic_steps = n_nonmonotonic,
    nonfinite_time_rows = n_nonfinite,
    affected_groups = affected_groups,
    status = status,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      segment_summary = segment_summary,
      row_flags = row_flags,
      data_with_segments = data_with_segments,
      settings = list(
        time_col = time_col,
        group_cols = group_cols,
        allow_ties = allow_ties,
        split_on_negative_step = split_on_negative_step,
        return_reindexed_time = return_reindexed_time,
        min_segment_rows = min_segment_rows
      )
    ),
    class = c("gazepoint_time_reset_audit", "list")
  )
}

#' Audit Gazepoint biometric signal activity
#'
#' Screens biometric signal columns for missingness, all-zero channels, constant
#' values, low variation, and active signal presence within groups. This helper
#' is designed to identify inactive files or channels before event-level EDA,
#' HR, IBI, or multimodal analysis.
#'
#' @param data A data frame containing Gazepoint biometric rows.
#' @param signal_cols Optional signal columns. If `NULL`, common Gazepoint
#'   biometric columns are detected automatically.
#' @param group_cols Optional grouping columns. If `NULL`, available source,
#'   participant, media, or trial columns are used.
#' @param zero_is_inactive Logical. If `TRUE`, all-zero signals are labelled as
#'   inactive.
#' @param min_unique_nonzero Minimum number of distinct non-zero finite values
#'   required for an `"active"` status.
#' @param missing_as_inactive Logical. If `TRUE`, all-missing signals are labelled
#'   as insufficient/inactive.
#'
#' @return A list with `overview`, `signal_by_group`, `inactive_groups`,
#'   `inactive_signals`, and `settings`.
#' @export
audit_gazepoint_signal_activity <- function(data,
                                            signal_cols = NULL,
                                            group_cols = NULL,
                                            zero_is_inactive = TRUE,
                                            min_unique_nonzero = 2,
                                            missing_as_inactive = TRUE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.logical(zero_is_inactive) || length(zero_is_inactive) != 1) {
    stop("`zero_is_inactive` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(min_unique_nonzero) ||
      length(min_unique_nonzero) != 1 ||
      min_unique_nonzero < 1) {
    stop("`min_unique_nonzero` must be a positive number.", call. = FALSE)
  }

  if (!is.logical(missing_as_inactive) || length(missing_as_inactive) != 1) {
    stop("`missing_as_inactive` must be TRUE or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  names_dat <- names(dat)

  if (is.null(signal_cols)) {
    signal_cols <- gpbiometrics_activity_infer_signal_cols(names_dat)
  }

  signal_cols <- unique(signal_cols)

  if (length(signal_cols) == 0) {
    stop("No biometric signal columns were found. Supply `signal_cols`.", call. = FALSE)
  }

  missing_signal_cols <- setdiff(signal_cols, names_dat)

  if (length(missing_signal_cols) > 0) {
    stop(
      "`signal_cols` not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  group_cols <- gpbiometrics_activity_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  group_id <- gpbiometrics_activity_group_id(dat, group_cols)
  group_indices <- split(seq_len(nrow(dat)), group_id, drop = TRUE)

  signal_by_group_parts <- list()

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]
    group_values <- gpbiometrics_activity_group_values(dat, group_cols, idx)

    for (signal in signal_cols) {
      x_raw <- dat[[signal]][idx]
      x_num <- suppressWarnings(as.numeric(x_raw))

      numeric_or_coercible <- !all(is.na(x_num))
      finite_values <- x_num[is.finite(x_num)]
      nonzero_values <- finite_values[finite_values != 0]

      n <- length(x_num)
      n_missing <- sum(is.na(x_num))
      n_zero <- sum(!is.na(x_num) & x_num == 0)
      n_nonzero <- sum(!is.na(x_num) & x_num != 0)
      n_unique_finite <- length(unique(finite_values))
      n_unique_nonzero <- length(unique(nonzero_values))

      sd_value <- if (length(finite_values) > 1) {
        stats::sd(finite_values, na.rm = TRUE)
      } else {
        NA_real_
      }

      mean_value <- if (length(finite_values) > 0) {
        mean(finite_values, na.rm = TRUE)
      } else {
        NA_real_
      }

      min_value <- if (length(finite_values) > 0) {
        min(finite_values, na.rm = TRUE)
      } else {
        NA_real_
      }

      max_value <- if (length(finite_values) > 0) {
        max(finite_values, na.rm = TRUE)
      } else {
        NA_real_
      }

      status <- gpbiometrics_activity_signal_status(
        numeric_or_coercible = numeric_or_coercible,
        n = n,
        n_missing = n_missing,
        n_zero = n_zero,
        n_nonzero = n_nonzero,
        n_unique_finite = n_unique_finite,
        n_unique_nonzero = n_unique_nonzero,
        zero_is_inactive = zero_is_inactive,
        min_unique_nonzero = min_unique_nonzero,
        missing_as_inactive = missing_as_inactive
      )

      row <- data.frame(
        group_id = group_name,
        signal = signal,
        n = n,
        missing_count = n_missing,
        missing_prop = if (n > 0) n_missing / n else NA_real_,
        zero_count = n_zero,
        zero_prop = if (n > 0) n_zero / n else NA_real_,
        nonzero_count = n_nonzero,
        nonzero_prop = if (n > 0) n_nonzero / n else NA_real_,
        unique_finite = n_unique_finite,
        unique_nonzero = n_unique_nonzero,
        mean = mean_value,
        sd = sd_value,
        min = min_value,
        max = max_value,
        numeric_or_coercible = numeric_or_coercible,
        status = status,
        stringsAsFactors = FALSE
      )

      if (length(group_values) > 0) {
        row <- cbind(group_values, row)
      }

      signal_by_group_parts[[length(signal_by_group_parts) + 1L]] <- row
    }
  }

  signal_by_group <- do.call(rbind, signal_by_group_parts)
  rownames(signal_by_group) <- NULL

  inactive_statuses <- c(
    "inactive_all_zero",
    "inactive_constant",
    "low_variation",
    "insufficient_data",
    "nonnumeric"
  )

  group_summary <- gpbiometrics_activity_group_summary(
    signal_by_group = signal_by_group,
    group_cols = group_cols,
    inactive_statuses = inactive_statuses
  )

  inactive_groups <- group_summary[
    group_summary$active_signal_count == 0,
    ,
    drop = FALSE
  ]

  inactive_signals <- gpbiometrics_activity_signal_summary(
    signal_by_group = signal_by_group,
    inactive_statuses = inactive_statuses
  )

  active_group_count <- sum(group_summary$active_signal_count > 0)
  no_active_group_count <- sum(group_summary$active_signal_count == 0)

  status <- if (active_group_count == 0) {
    "fail_no_active_signals"
  } else if (no_active_group_count > 0) {
    "warn_inactive_groups_detected"
  } else if (any(signal_by_group$status != "active")) {
    "warn_inactive_or_low_variation_signals_detected"
  } else {
    "pass"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    signal_count = length(signal_cols),
    group_count = length(group_indices),
    active_group_count = active_group_count,
    no_active_group_count = no_active_group_count,
    inactive_signal_rows = sum(signal_by_group$status %in% inactive_statuses),
    status = status,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      signal_by_group = signal_by_group,
      inactive_groups = inactive_groups,
      inactive_signals = inactive_signals,
      settings = list(
        signal_cols = signal_cols,
        group_cols = group_cols,
        zero_is_inactive = zero_is_inactive,
        min_unique_nonzero = min_unique_nonzero,
        missing_as_inactive = missing_as_inactive
      )
    ),
    class = c("gazepoint_signal_activity_audit", "list")
  )
}

gpbiometrics_time_qc_first_existing <- function(names_dat, candidates) {
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

gpbiometrics_time_qc_resolve_group_cols <- function(names_dat, group_cols) {
  if (!is.null(group_cols)) {
    return(unique(group_cols))
  }

  candidates <- c(
    "source_file",
    "source_participant",
    "USER",
    "USER_FILE",
    "participant",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "media_id",
    "media_name",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_time_qc_group_id <- function(dat, group_cols) {
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

gpbiometrics_time_qc_segment_summary <- function(dat,
                                                 row_flags,
                                                 group_cols,
                                                 min_segment_rows) {
  segment_key <- paste(
    row_flags$group_id,
    row_flags$reset_segment_index,
    sep = "||segment_"
  )

  split_rows <- split(seq_len(nrow(row_flags)), segment_key, drop = TRUE)

  out <- lapply(names(split_rows), function(key) {
    idx <- split_rows[[key]]
    time_values <- row_flags$time_value[idx]
    finite_time <- time_values[is.finite(time_values)]

    row <- data.frame(
      segment_key = key,
      group_id = row_flags$group_id[idx[1]],
      segment_index = row_flags$reset_segment_index[idx[1]],
      start_row_id = row_flags$.gpbiometrics_row_id[idx[1]],
      end_row_id = row_flags$.gpbiometrics_row_id[idx[length(idx)]],
      rows = length(idx),
      start_time = if (length(finite_time) > 0) finite_time[1] else NA_real_,
      end_time = if (length(finite_time) > 0) finite_time[length(finite_time)] else NA_real_,
      duration = if (length(finite_time) > 1) {
        finite_time[length(finite_time)] - finite_time[1]
      } else {
        NA_real_
      },
      nonfinite_time_rows = sum(row_flags$flag_nonfinite_time[idx], na.rm = TRUE),
      negative_steps = sum(row_flags$flag_negative_step[idx], na.rm = TRUE),
      duplicate_steps = sum(row_flags$flag_duplicate_time[idx], na.rm = TRUE),
      nonmonotonic_steps = sum(row_flags$flag_nonmonotonic[idx], na.rm = TRUE),
      short_segment = length(idx) < min_segment_rows,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      row <- cbind(dat[idx[1], group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_time_qc_reindex_time <- function(time_value, group_id, segment_index) {
  out <- rep(NA_real_, length(time_value))
  segment_key <- paste(group_id, segment_index, sep = "||segment_")
  split_rows <- split(seq_along(time_value), segment_key, drop = TRUE)

  for (key in names(split_rows)) {
    idx <- split_rows[[key]]
    x <- time_value[idx]
    finite_idx <- which(is.finite(x))

    if (length(finite_idx) > 0) {
      first_time <- x[finite_idx[1]]
      out[idx] <- x - first_time
    }
  }

  out
}

gpbiometrics_activity_infer_signal_cols <- function(names_dat) {
  candidates <- c(
    "DIAL", "DIALV",
    "GSR", "GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSRV",
    "HR", "HRV", "HRP", "IBI",
    "dial", "dialv",
    "gsr", "gsr_us", "gsr_us_tonic", "gsr_us_phasic", "gsrv",
    "hr", "hrv", "hrp", "ibi"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_activity_resolve_group_cols <- function(names_dat, group_cols) {
  if (!is.null(group_cols)) {
    return(unique(group_cols))
  }

  candidates <- c(
    "source_file",
    "source_participant",
    "USER",
    "USER_FILE",
    "participant",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "media_id",
    "media_name",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_activity_group_id <- function(dat, group_cols) {
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

gpbiometrics_activity_group_values <- function(dat, group_cols, idx) {
  if (length(group_cols) == 0) {
    return(data.frame(stringsAsFactors = FALSE))
  }

  dat[idx[1], group_cols, drop = FALSE]
}

gpbiometrics_activity_signal_status <- function(numeric_or_coercible,
                                                n,
                                                n_missing,
                                                n_zero,
                                                n_nonzero,
                                                n_unique_finite,
                                                n_unique_nonzero,
                                                zero_is_inactive,
                                                min_unique_nonzero,
                                                missing_as_inactive) {
  if (!isTRUE(numeric_or_coercible)) {
    return("nonnumeric")
  }

  if (n == 0 || (isTRUE(missing_as_inactive) && n_missing == n)) {
    return("insufficient_data")
  }

  if (isTRUE(zero_is_inactive) && n_nonzero == 0 && n_zero > 0) {
    return("inactive_all_zero")
  }

  if (n_unique_finite <= 1) {
    return("inactive_constant")
  }

  if (n_unique_nonzero < min_unique_nonzero) {
    return("low_variation")
  }

  "active"
}

gpbiometrics_activity_group_summary <- function(signal_by_group,
                                                group_cols,
                                                inactive_statuses) {
  group_ids <- unique(signal_by_group$group_id)

  out <- lapply(group_ids, function(group_id_i) {
    d <- signal_by_group[signal_by_group$group_id == group_id_i, , drop = FALSE]

    row <- data.frame(
      group_id = group_id_i,
      signal_count = nrow(d),
      active_signal_count = sum(d$status == "active"),
      inactive_signal_count = sum(d$status %in% inactive_statuses),
      low_variation_signal_count = sum(d$status == "low_variation"),
      all_zero_signal_count = sum(d$status == "inactive_all_zero"),
      constant_signal_count = sum(d$status == "inactive_constant"),
      group_status = if (sum(d$status == "active") == 0) {
        "no_active_signals"
      } else if (sum(d$status == "active") < nrow(d)) {
        "partial_active_signals"
      } else {
        "all_signals_active"
      },
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      group_values <- d[1, group_cols, drop = FALSE]
      row <- cbind(group_values, row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_activity_signal_summary <- function(signal_by_group,
                                                 inactive_statuses) {
  signals <- unique(signal_by_group$signal)

  out <- lapply(signals, function(signal_i) {
    d <- signal_by_group[signal_by_group$signal == signal_i, , drop = FALSE]

    data.frame(
      signal = signal_i,
      group_count = nrow(d),
      active_group_count = sum(d$status == "active"),
      inactive_group_count = sum(d$status %in% inactive_statuses),
      all_zero_group_count = sum(d$status == "inactive_all_zero"),
      constant_group_count = sum(d$status == "inactive_constant"),
      low_variation_group_count = sum(d$status == "low_variation"),
      median_nonzero_prop = stats::median(d$nonzero_prop, na.rm = TRUE),
      median_missing_prop = stats::median(d$missing_prop, na.rm = TRUE),
      signal_status = if (sum(d$status == "active") == 0) {
        "inactive_in_all_groups"
      } else if (sum(d$status == "active") < nrow(d)) {
        "active_in_some_groups"
      } else {
        "active_in_all_groups"
      },
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}
