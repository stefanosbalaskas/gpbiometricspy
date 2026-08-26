#' Audit Gazepoint EDA/GSR artifacts
#'
#' Flags row-level artifacts in Gazepoint electrodermal activity signals,
#' preferring `GSR_US` conductance when available. The helper detects abrupt
#' jumps, abrupt slopes, flatline runs, zero runs, negative conductance values,
#' and optional out-of-range values. It is a conservative preprocessing/QC
#' helper and does not interpret EDA as emotional valence.
#'
#' @param data A data frame containing Gazepoint biometric rows.
#' @param signal_col Optional EDA/GSR signal column. If `NULL`, the function
#'   prefers `GSR_US` and then falls back to common Gazepoint EDA columns.
#' @param time_col Optional time/counter column. If `NULL`, common Gazepoint
#'   time columns are detected automatically.
#' @param group_cols Optional grouping columns. If `NULL`, available
#'   source/participant/media/trial-like columns are used.
#' @param prefer_gsr_us Logical. If `TRUE`, prefer `GSR_US` when `signal_col`
#'   is not supplied.
#' @param jump_threshold_sd Robust z threshold for absolute signal jumps.
#' @param slope_threshold_sd Robust z threshold for absolute signal slopes.
#' @param flat_run_length Minimum repeated-value run length flagged as flatline.
#' @param zero_run_length Minimum zero-value run length flagged as zero run.
#' @param saturation_min Optional lower bound for acceptable signal values.
#' @param saturation_max Optional upper bound for acceptable signal values.
#' @param negative_allowed Optional logical. If `NULL`, negative values are
#'   allowed for phasic component columns but not for conductance-like columns.
#'
#' @return A list with `overview`, `row_flags`, `artifact_runs`,
#'   `group_summary`, and `settings`.
#' @export
audit_gazepoint_eda_artifacts <- function(data,
                                          signal_col = NULL,
                                          time_col = NULL,
                                          group_cols = NULL,
                                          prefer_gsr_us = TRUE,
                                          jump_threshold_sd = 6,
                                          slope_threshold_sd = 6,
                                          flat_run_length = 20,
                                          zero_run_length = 20,
                                          saturation_min = NULL,
                                          saturation_max = NULL,
                                          negative_allowed = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.logical(prefer_gsr_us) || length(prefer_gsr_us) != 1) {
    stop("`prefer_gsr_us` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(jump_threshold_sd) ||
      length(jump_threshold_sd) != 1 ||
      jump_threshold_sd <= 0) {
    stop("`jump_threshold_sd` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(slope_threshold_sd) ||
      length(slope_threshold_sd) != 1 ||
      slope_threshold_sd <= 0) {
    stop("`slope_threshold_sd` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(flat_run_length) ||
      length(flat_run_length) != 1 ||
      flat_run_length < 1) {
    stop("`flat_run_length` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(zero_run_length) ||
      length(zero_run_length) != 1 ||
      zero_run_length < 1) {
    stop("`zero_run_length` must be a positive number.", call. = FALSE)
  }

  if (!is.null(saturation_min) &&
      (!is.numeric(saturation_min) || length(saturation_min) != 1)) {
    stop("`saturation_min` must be NULL or a single number.", call. = FALSE)
  }

  if (!is.null(saturation_max) &&
      (!is.numeric(saturation_max) || length(saturation_max) != 1)) {
    stop("`saturation_max` must be NULL or a single number.", call. = FALSE)
  }

  if (!is.null(negative_allowed) &&
      (!is.logical(negative_allowed) || length(negative_allowed) != 1)) {
    stop("`negative_allowed` must be NULL, TRUE, or FALSE.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  names_dat <- names(dat)

  if (is.null(signal_col)) {
    signal_col <- gpbiometrics_eda_artifact_infer_signal_col(
      names_dat = names_dat,
      prefer_gsr_us = prefer_gsr_us
    )
  }

  if (is.null(signal_col) || !signal_col %in% names_dat) {
    stop("No usable EDA/GSR signal column was found. Supply `signal_col`.", call. = FALSE)
  }

  if (is.null(time_col)) {
    time_col <- gpbiometrics_eda_artifact_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (!is.null(time_col) && !time_col %in% names_dat) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_eda_artifact_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(negative_allowed)) {
    negative_allowed <- grepl("PHASIC", signal_col, ignore.case = TRUE)
  }

  signal_value <- suppressWarnings(as.numeric(dat[[signal_col]]))

  if (all(is.na(signal_value))) {
    stop("`signal_col` must contain numeric or numeric-coercible values.", call. = FALSE)
  }

  time_value <- if (!is.null(time_col)) {
    suppressWarnings(as.numeric(dat[[time_col]]))
  } else {
    seq_len(nrow(dat))
  }

  group_id <- gpbiometrics_eda_artifact_group_id(dat, group_cols)
  group_indices <- split(seq_len(nrow(dat)), group_id, drop = TRUE)

  row_flags <- data.frame(
    .gpbiometrics_row_id = dat$.gpbiometrics_row_id,
    group_id = group_id,
    signal_col = signal_col,
    signal_value = signal_value,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    time_value = time_value,
    group_row_index = NA_integer_,
    signal_delta = NA_real_,
    time_delta = NA_real_,
    slope = NA_real_,
    robust_jump_z = NA_real_,
    robust_slope_z = NA_real_,
    flag_nonfinite_signal = !is.finite(signal_value),
    flag_nonfinite_time = !is.finite(time_value),
    flag_negative_conductance = FALSE,
    flag_jump = FALSE,
    flag_slope = FALSE,
    flag_flatline_run = FALSE,
    flag_zero_run = FALSE,
    flag_out_of_bounds = FALSE,
    flag_artifact = FALSE,
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0) {
    row_flags <- cbind(dat[group_cols], row_flags)
  }

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]

    row_flags$group_row_index[idx] <- seq_along(idx)

    x <- signal_value[idx]
    t <- time_value[idx]

    dx <- c(NA_real_, diff(x))
    dt <- c(NA_real_, diff(t))

    slope <- rep(NA_real_, length(idx))
    slope[is.finite(dx) & is.finite(dt) & dt != 0] <- dx[
      is.finite(dx) & is.finite(dt) & dt != 0
    ] / dt[is.finite(dx) & is.finite(dt) & dt != 0]

    row_flags$signal_delta[idx] <- dx
    row_flags$time_delta[idx] <- dt
    row_flags$slope[idx] <- slope

    jump_z <- gpbiometrics_eda_artifact_robust_z(dx)
    slope_z <- gpbiometrics_eda_artifact_robust_z(slope)

    row_flags$robust_jump_z[idx] <- jump_z
    row_flags$robust_slope_z[idx] <- slope_z

    row_flags$flag_jump[idx] <- is.finite(jump_z) & abs(jump_z) >= jump_threshold_sd
    row_flags$flag_slope[idx] <- is.finite(slope_z) & abs(slope_z) >= slope_threshold_sd

    row_flags$flag_flatline_run[idx] <- gpbiometrics_eda_artifact_run_flag(
      x = x,
      min_run = flat_run_length,
      zero_only = FALSE
    )

    row_flags$flag_zero_run[idx] <- gpbiometrics_eda_artifact_run_flag(
      x = x,
      min_run = zero_run_length,
      zero_only = TRUE
    )
  }

  if (isFALSE(negative_allowed)) {
    row_flags$flag_negative_conductance <- is.finite(signal_value) & signal_value < 0
  }

  if (!is.null(saturation_min)) {
    row_flags$flag_out_of_bounds <- row_flags$flag_out_of_bounds |
      (is.finite(signal_value) & signal_value < saturation_min)
  }

  if (!is.null(saturation_max)) {
    row_flags$flag_out_of_bounds <- row_flags$flag_out_of_bounds |
      (is.finite(signal_value) & signal_value > saturation_max)
  }

  row_flags$flag_artifact <- row_flags$flag_nonfinite_signal |
    row_flags$flag_negative_conductance |
    row_flags$flag_jump |
    row_flags$flag_slope |
    row_flags$flag_flatline_run |
    row_flags$flag_zero_run |
    row_flags$flag_out_of_bounds

  group_summary <- gpbiometrics_eda_artifact_group_summary(
    row_flags = row_flags,
    group_cols = group_cols
  )

  artifact_runs <- gpbiometrics_eda_artifact_runs(
    row_flags = row_flags,
    group_cols = group_cols
  )

  artifact_rows <- sum(row_flags$flag_artifact, na.rm = TRUE)
  artifact_prop <- if (nrow(row_flags) > 0) artifact_rows / nrow(row_flags) else NA_real_

  status <- if (artifact_rows == 0) {
    "pass"
  } else if (artifact_prop >= 0.50) {
    "fail_high_artifact_rate"
  } else {
    "warn_artifacts_detected"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    signal_col = signal_col,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    group_count = length(group_indices),
    artifact_rows = artifact_rows,
    artifact_prop = artifact_prop,
    nonfinite_signal_rows = sum(row_flags$flag_nonfinite_signal, na.rm = TRUE),
    negative_conductance_rows = sum(row_flags$flag_negative_conductance, na.rm = TRUE),
    jump_rows = sum(row_flags$flag_jump, na.rm = TRUE),
    slope_rows = sum(row_flags$flag_slope, na.rm = TRUE),
    flatline_run_rows = sum(row_flags$flag_flatline_run, na.rm = TRUE),
    zero_run_rows = sum(row_flags$flag_zero_run, na.rm = TRUE),
    out_of_bounds_rows = sum(row_flags$flag_out_of_bounds, na.rm = TRUE),
    status = status,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      row_flags = row_flags,
      artifact_runs = artifact_runs,
      group_summary = group_summary,
      settings = list(
        signal_col = signal_col,
        time_col = time_col,
        group_cols = group_cols,
        prefer_gsr_us = prefer_gsr_us,
        jump_threshold_sd = jump_threshold_sd,
        slope_threshold_sd = slope_threshold_sd,
        flat_run_length = flat_run_length,
        zero_run_length = zero_run_length,
        saturation_min = saturation_min,
        saturation_max = saturation_max,
        negative_allowed = negative_allowed,
        interpretation_notes = c(
          "EDA/GSR artifacts are preprocessing and quality-control indicators, not psychological events.",
          "GSR/EDA should be interpreted as electrodermal or sympathetic arousal-related activity, not emotional valence.",
          "Prefer GSR_US conductance when available; use GSR conversion only conservatively when GSR_US is absent."
        )
      )
    ),
    class = c("gazepoint_eda_artifact_audit", "list")
  )
}

gpbiometrics_eda_artifact_first_existing <- function(names_dat, candidates) {
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

gpbiometrics_eda_artifact_infer_signal_col <- function(names_dat,
                                                       prefer_gsr_us = TRUE) {
  if (isTRUE(prefer_gsr_us)) {
    preferred <- gpbiometrics_eda_artifact_first_existing(
      names_dat,
      c("GSR_US", "gsr_us")
    )

    if (!is.null(preferred)) {
      return(preferred)
    }
  }

  gpbiometrics_eda_artifact_first_existing(
    names_dat,
    c(
      "GSR_US", "gsr_us",
      "GSR_US_TONIC", "gsr_us_tonic",
      "GSR", "gsr",
      "GSR_US_PHASIC", "gsr_us_phasic"
    )
  )
}

gpbiometrics_eda_artifact_resolve_group_cols <- function(names_dat,
                                                         group_cols) {
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

gpbiometrics_eda_artifact_group_id <- function(dat, group_cols) {
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

gpbiometrics_eda_artifact_robust_z <- function(x) {
  out <- rep(NA_real_, length(x))

  finite <- is.finite(x)

  if (sum(finite) < 3) {
    return(out)
  }

  x_finite <- x[finite]
  center <- stats::median(x_finite, na.rm = TRUE)
  mad_value <- stats::median(abs(x_finite - center), na.rm = TRUE)

  scale_value <- mad_value * 1.4826

  if (!is.finite(scale_value) || scale_value == 0) {
    scale_value <- stats::sd(x_finite, na.rm = TRUE)
  }

  if (!is.finite(scale_value) || scale_value == 0) {
    out[finite] <- 0
    return(out)
  }

  out[finite] <- (x_finite - center) / scale_value
  out
}

gpbiometrics_eda_artifact_run_flag <- function(x,
                                               min_run,
                                               zero_only = FALSE) {
  out <- rep(FALSE, length(x))

  if (length(x) == 0) {
    return(out)
  }

  values <- suppressWarnings(as.numeric(x))
  key <- ifelse(is.na(values), "<NA>", as.character(values))

  if (isTRUE(zero_only)) {
    key[!(is.finite(values) & values == 0)] <- paste0("nonzero_", seq_along(values))[
      !(is.finite(values) & values == 0)
    ]
  }

  run_info <- rle(key)
  run_lengths <- run_info$lengths
  run_values <- run_info$values
  run_ends <- cumsum(run_lengths)
  run_starts <- run_ends - run_lengths + 1L

  for (i in seq_along(run_lengths)) {
    if (run_lengths[i] >= min_run) {
      if (isTRUE(zero_only)) {
        if (identical(run_values[i], "0")) {
          out[run_starts[i]:run_ends[i]] <- TRUE
        }
      } else {
        if (!identical(run_values[i], "<NA>")) {
          out[run_starts[i]:run_ends[i]] <- TRUE
        }
      }
    }
  }

  out
}

gpbiometrics_eda_artifact_group_summary <- function(row_flags,
                                                    group_cols) {
  group_ids <- unique(row_flags$group_id)

  out <- lapply(group_ids, function(group_id_i) {
    d <- row_flags[row_flags$group_id == group_id_i, , drop = FALSE]

    artifact_rows <- sum(d$flag_artifact, na.rm = TRUE)
    artifact_prop <- if (nrow(d) > 0) artifact_rows / nrow(d) else NA_real_

    row <- data.frame(
      group_id = group_id_i,
      rows = nrow(d),
      artifact_rows = artifact_rows,
      artifact_prop = artifact_prop,
      nonfinite_signal_rows = sum(d$flag_nonfinite_signal, na.rm = TRUE),
      negative_conductance_rows = sum(d$flag_negative_conductance, na.rm = TRUE),
      jump_rows = sum(d$flag_jump, na.rm = TRUE),
      slope_rows = sum(d$flag_slope, na.rm = TRUE),
      flatline_run_rows = sum(d$flag_flatline_run, na.rm = TRUE),
      zero_run_rows = sum(d$flag_zero_run, na.rm = TRUE),
      out_of_bounds_rows = sum(d$flag_out_of_bounds, na.rm = TRUE),
      status = if (artifact_rows == 0) {
        "pass"
      } else if (artifact_prop >= 0.50) {
        "fail_high_artifact_rate"
      } else {
        "warn_artifacts_detected"
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

gpbiometrics_eda_artifact_runs <- function(row_flags,
                                           group_cols) {
  artifact_types <- c(
    "flag_nonfinite_signal",
    "flag_negative_conductance",
    "flag_jump",
    "flag_slope",
    "flag_flatline_run",
    "flag_zero_run",
    "flag_out_of_bounds"
  )

  out <- list()
  group_ids <- unique(row_flags$group_id)

  for (group_id_i in group_ids) {
    idx_group <- which(row_flags$group_id == group_id_i)

    for (artifact_type in artifact_types) {
      flag <- row_flags[[artifact_type]][idx_group]

      if (!any(flag, na.rm = TRUE)) {
        next
      }

      run_info <- rle(flag)
      run_lengths <- run_info$lengths
      run_values <- run_info$values
      run_ends <- cumsum(run_lengths)
      run_starts <- run_ends - run_lengths + 1L

      artifact_runs <- which(run_values)

      for (run_i in artifact_runs) {
        idx_local <- run_starts[run_i]:run_ends[run_i]
        idx <- idx_group[idx_local]

        row <- data.frame(
          group_id = group_id_i,
          artifact_type = artifact_type,
          start_row_id = row_flags$.gpbiometrics_row_id[idx[1]],
          end_row_id = row_flags$.gpbiometrics_row_id[idx[length(idx)]],
          rows = length(idx),
          start_time = row_flags$time_value[idx[1]],
          end_time = row_flags$time_value[idx[length(idx)]],
          stringsAsFactors = FALSE
        )

        if (length(group_cols) > 0) {
          group_values <- row_flags[idx[1], group_cols, drop = FALSE]
          row <- cbind(group_values, row)
        }

        out[[length(out) + 1L]] <- row
      }
    }
  }

  if (length(out) == 0) {
    empty <- data.frame(
      group_id = character(),
      artifact_type = character(),
      start_row_id = integer(),
      end_row_id = integer(),
      rows = integer(),
      start_time = numeric(),
      end_time = numeric(),
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      for (col in rev(group_cols)) {
        empty <- cbind(stats::setNames(data.frame(character(), stringsAsFactors = FALSE), col), empty)
      }
    }

    return(empty)
  }

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}
