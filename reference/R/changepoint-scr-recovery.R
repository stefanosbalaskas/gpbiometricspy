#' Detect stochastic change points in noisy biometric signals
#'
#' Detects abrupt changes in noisy biological time series using a dependency-light
#' stochastic rolling-window approximation. The score combines adjacent-window
#' changes in mean and variance with a robust adaptive threshold.
#'
#' This is not a full reproduction of any specific doubly stochastic model. It
#' is a transparent approximation for QC and exploratory segmentation.
#'
#' @param dat A data frame.
#' @param signal_col Numeric signal column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param window_seconds Window length in seconds.
#' @param step_seconds Step size in seconds.
#' @param threshold_mad_multiplier Robust threshold multiplier.
#' @param min_distance_s Minimum distance between detected change points.
#'
#' @return A list with `overview`, `score_table`, `changepoints`, and `settings`.
#' @export
detect_gazepoint_doubly_stochastic_changepoints <- function(dat,
                                                            signal_col,
                                                            time_col = "CNT",
                                                            group_cols = NULL,
                                                            window_seconds = 10,
                                                            step_seconds = 2,
                                                            threshold_mad_multiplier = 6,
                                                            min_distance_s = 5) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!signal_col %in% names(dat)) {
    stop("Column `", signal_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_cp_split(dat, group_cols)

  score_rows <- list()
  changepoint_rows <- list()
  score_id <- 1L
  cp_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    signal <- dat[[signal_col]][idx]

    starts <- seq(
      min(time, na.rm = TRUE),
      max(time, na.rm = TRUE) - window_seconds,
      by = step_seconds
    )

    if (length(starts) < 3) {
      next
    }

    window_summary <- lapply(seq_along(starts), function(i) {
      start <- starts[i]
      end <- start + window_seconds
      in_window <- is.finite(time) & time >= start & time <= end
      x <- signal[in_window]
      x <- x[is.finite(x)]

      data.frame(
        group_id = group_id,
        window_index = i,
        window_start = start,
        window_end = end,
        window_midpoint = mean(c(start, end)),
        n = length(x),
        mean = if (length(x) > 0) mean(x) else NA_real_,
        variance = if (length(x) > 1) stats::var(x) else NA_real_,
        stringsAsFactors = FALSE
      )
    })

    window_summary <- do.call(rbind, window_summary)

    score <- rep(NA_real_, nrow(window_summary))

    for (i in 2:nrow(window_summary)) {
      m1 <- window_summary$mean[i - 1]
      m2 <- window_summary$mean[i]
      v1 <- window_summary$variance[i - 1]
      v2 <- window_summary$variance[i]

      pooled_sd <- sqrt(mean(c(v1, v2), na.rm = TRUE))
      mean_score <- if (is.finite(pooled_sd) && pooled_sd > 0) {
        abs(m2 - m1) / pooled_sd
      } else {
        0
      }

      variance_score <- if (is.finite(v1) && is.finite(v2) && v1 > 0 && v2 > 0) {
        abs(log(v2 / v1))
      } else {
        0
      }

      score[i] <- mean_score + variance_score
    }

    center <- stats::median(score, na.rm = TRUE)
    mad_score <- stats::mad(score, constant = 1, na.rm = TRUE)

    if (!is.finite(mad_score) || mad_score == 0) {
      mad_score <- .Machine$double.eps
    }

    threshold <- center + threshold_mad_multiplier * mad_score
    is_candidate <- is.finite(score) & score > threshold

    window_summary$change_score <- score
    window_summary$threshold <- threshold
    window_summary$changepoint_candidate <- is_candidate
    window_summary$status <- "changepoint_score_created"

    for (i in seq_len(nrow(window_summary))) {
      score_rows[[score_id]] <- window_summary[i, , drop = FALSE]
      score_id <- score_id + 1L
    }

    selected <- gpbiometrics_cp_select(
      candidate_time = window_summary$window_midpoint[is_candidate],
      candidate_score = window_summary$change_score[is_candidate],
      min_distance_s = min_distance_s
    )

    if (length(selected$time) > 0) {
      for (i in seq_along(selected$time)) {
        changepoint_rows[[cp_id]] <- data.frame(
          group_id = group_id,
          changepoint_index = i,
          changepoint_time = selected$time[i],
          change_score = selected$score[i],
          threshold = threshold,
          status = "changepoint_detected",
          stringsAsFactors = FALSE
        )
        cp_id <- cp_id + 1L
      }
    }
  }

  score_table <- if (length(score_rows) > 0) {
    do.call(rbind, score_rows)
  } else {
    data.frame()
  }

  changepoints <- if (length(changepoint_rows) > 0) {
    do.call(rbind, changepoint_rows)
  } else {
    data.frame()
  }

  overview <- data.frame(
    group_count = length(groups),
    score_rows = nrow(score_table),
    changepoint_rows = nrow(changepoints),
    status = "doubly_stochastic_changepoint_screen_complete",
    interpretation = paste(
      "Detected change points are robust stochastic screening markers for abrupt distributional shifts.",
      "They are not proof of a specific latent state or psychological event."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      score_table = score_table,
      changepoints = changepoints,
      settings = list(
        signal_col = signal_col,
        time_col = time_col,
        group_cols = group_cols,
        window_seconds = window_seconds,
        step_seconds = step_seconds,
        threshold_mad_multiplier = threshold_mad_multiplier,
        min_distance_s = min_distance_s
      )
    ),
    class = c("gazepoint_doubly_stochastic_changepoints", "list")
  )
}

#' Extract SCR recovery times
#'
#' Extracts 50 percent half-recovery time (`rec.t2`) and 63 percent recovery
#' time (`rec.tc`) for skin conductance responses from an EDA waveform and
#' event onsets.
#'
#' @param dat A data frame.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param event_onset_col Optional event onset column. Finite values are treated
#'   as event onsets.
#' @param group_cols Optional grouping columns.
#' @param pre_onset_baseline_s Baseline window before event onset.
#' @param peak_window_s Window after onset used to find the response peak.
#' @param recovery_window_s Window after peak used to find recovery.
#'
#' @return A list with `overview`, `recovery_table`, and `settings`.
#' @export
extract_gazepoint_scr_recovery_times <- function(dat,
                                                 eda_col = "GSR_US",
                                                 time_col = "CNT",
                                                 event_onset_col = NULL,
                                                 group_cols = NULL,
                                                 pre_onset_baseline_s = 2,
                                                 peak_window_s = 5,
                                                 recovery_window_s = 20) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(eda_col, time_col, event_onset_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_cp_split(dat, group_cols)
  recovery_rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    eda <- dat[[eda_col]][idx]

    onsets <- if (!is.null(event_onset_col)) {
      dat[[event_onset_col]][idx]
    } else {
      gpbiometrics_scr_recovery_detect_onsets(time, eda)
    }

    onsets <- sort(unique(onsets[is.finite(onsets)]))

    if (length(onsets) == 0) {
      recovery_rows[[row_id]] <- data.frame(
        group_id = group_id,
        event_index = NA_integer_,
        onset_time = NA_real_,
        baseline = NA_real_,
        peak_time = NA_real_,
        peak_amplitude = NA_real_,
        rec_t2 = NA_real_,
        rec_tc = NA_real_,
        status = "no_events_available",
        stringsAsFactors = FALSE
      )
      row_id <- row_id + 1L
      next
    }

    for (i in seq_along(onsets)) {
      onset <- onsets[i]

      baseline_idx <- is.finite(time) &
        time >= onset - pre_onset_baseline_s &
        time <= onset

      baseline <- if (sum(baseline_idx) > 0) {
        stats::median(eda[baseline_idx], na.rm = TRUE)
      } else {
        eda[which.min(abs(time - onset))]
      }

      peak_idx <- is.finite(time) &
        time >= onset &
        time <= onset + peak_window_s

      if (sum(peak_idx) == 0 || !is.finite(baseline)) {
        recovery_rows[[row_id]] <- data.frame(
          group_id = group_id,
          event_index = i,
          onset_time = onset,
          baseline = baseline,
          peak_time = NA_real_,
          peak_amplitude = NA_real_,
          rec_t2 = NA_real_,
          rec_tc = NA_real_,
          status = "peak_not_found",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
        next
      }

      local_peak <- which.max(eda[peak_idx])
      peak_rows <- which(peak_idx)
      peak_row <- peak_rows[local_peak]
      peak_time <- time[peak_row]
      peak_value <- eda[peak_row]
      amplitude <- peak_value - baseline

      if (!is.finite(amplitude) || amplitude <= 0) {
        recovery_rows[[row_id]] <- data.frame(
          group_id = group_id,
          event_index = i,
          onset_time = onset,
          baseline = baseline,
          peak_time = peak_time,
          peak_amplitude = amplitude,
          rec_t2 = NA_real_,
          rec_tc = NA_real_,
          status = "nonpositive_response_amplitude",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
        next
      }

      recovery_idx <- is.finite(time) &
        time >= peak_time &
        time <= peak_time + recovery_window_s

      rec_t2 <- gpbiometrics_scr_recovery_time(
        time = time[recovery_idx],
        eda = eda[recovery_idx],
        baseline = baseline,
        amplitude = amplitude,
        fraction_recovered = 0.50
      )

      rec_tc <- gpbiometrics_scr_recovery_time(
        time = time[recovery_idx],
        eda = eda[recovery_idx],
        baseline = baseline,
        amplitude = amplitude,
        fraction_recovered = 0.63
      )

      recovery_rows[[row_id]] <- data.frame(
        group_id = group_id,
        event_index = i,
        onset_time = onset,
        baseline = baseline,
        peak_time = peak_time,
        peak_amplitude = amplitude,
        rec_t2 = rec_t2,
        rec_tc = rec_tc,
        status = if (is.finite(rec_t2) || is.finite(rec_tc)) {
          "scr_recovery_extracted"
        } else {
          "recovery_not_observed"
        },
        stringsAsFactors = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  recovery_table <- do.call(rbind, recovery_rows)
  rownames(recovery_table) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    recovery_rows = nrow(recovery_table),
    recovered_rows = sum(recovery_table$status == "scr_recovery_extracted"),
    problem_rows = sum(recovery_table$status != "scr_recovery_extracted"),
    status = if (any(recovery_table$status == "scr_recovery_extracted")) {
      "scr_recovery_times_extracted"
    } else {
      "scr_recovery_times_not_extracted"
    },
    interpretation = paste(
      "SCR recovery times describe conductance decay kinetics after a response peak.",
      "They do not directly infer psychological or clinical state."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      recovery_table = recovery_table,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        event_onset_col = event_onset_col,
        group_cols = group_cols,
        pre_onset_baseline_s = pre_onset_baseline_s,
        peak_window_s = peak_window_s,
        recovery_window_s = recovery_window_s
      )
    ),
    class = c("gazepoint_scr_recovery_times", "list")
  )
}

gpbiometrics_cp_split <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(list(all_rows = seq_len(nrow(dat))))
  }

  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_cp_select <- function(candidate_time,
                                   candidate_score,
                                   min_distance_s) {
  keep <- is.finite(candidate_time) & is.finite(candidate_score)

  candidate_time <- candidate_time[keep]
  candidate_score <- candidate_score[keep]

  if (length(candidate_time) == 0) {
    return(list(time = numeric(), score = numeric()))
  }

  ord <- order(candidate_score, decreasing = TRUE)
  candidate_time <- candidate_time[ord]
  candidate_score <- candidate_score[ord]

  selected_time <- numeric()
  selected_score <- numeric()

  for (i in seq_along(candidate_time)) {
    if (length(selected_time) == 0 ||
        all(abs(candidate_time[i] - selected_time) >= min_distance_s)) {
      selected_time <- c(selected_time, candidate_time[i])
      selected_score <- c(selected_score, candidate_score[i])
    }
  }

  ord_time <- order(selected_time)

  list(
    time = selected_time[ord_time],
    score = selected_score[ord_time]
  )
}

gpbiometrics_scr_recovery_time <- function(time,
                                           eda,
                                           baseline,
                                           amplitude,
                                           fraction_recovered) {
  if (length(time) == 0 || !is.finite(amplitude) || amplitude <= 0) {
    return(NA_real_)
  }

  target <- baseline + amplitude * (1 - fraction_recovered)
  hit <- which(is.finite(eda) & eda <= target)

  if (length(hit) == 0) {
    return(NA_real_)
  }

  time[hit[1]] - min(time, na.rm = TRUE)
}

gpbiometrics_scr_recovery_detect_onsets <- function(time, eda) {
  if (length(time) < 5 || length(eda) < 5) {
    return(numeric())
  }

  d <- c(NA_real_, diff(eda))
  threshold <- stats::median(d, na.rm = TRUE) + 6 * stats::mad(d, constant = 1, na.rm = TRUE)

  if (!is.finite(threshold)) {
    return(numeric())
  }

  time[which(is.finite(d) & d > threshold)]
}
