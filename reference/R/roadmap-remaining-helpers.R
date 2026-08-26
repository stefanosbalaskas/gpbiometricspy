
# Remaining roadmap helpers: SCR, pupil, PPG, events, validation, reproducibility

.gp_rem_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_rem_guess_col <- function(data, candidates, label, required = TRUE) {
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify ", label, " column. Supply it explicitly.", call. = FALSE)
  }

  NULL
}

.gp_rem_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(seq_along(time))
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

.gp_rem_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_rem_standardize_events <- function(events,
                                       event_time_col = NULL,
                                       event_id_col = NULL,
                                       event_label_col = NULL) {
  if (is.numeric(events) && is.null(dim(events))) {
    return(data.frame(
      event_id = seq_along(events),
      event_time = as.numeric(events),
      event_label = paste0("event_", seq_along(events)),
      stringsAsFactors = FALSE
    ))
  }

  if (is.character(events) && length(events) == 1L && file.exists(events)) {
    return(import_gazepoint_event_log(events,
      time_col = event_time_col,
      event_col = event_label_col
    ))
  }

  if (!is.data.frame(events)) {
    stop("`events` must be a numeric vector, data frame, or event-log path.", call. = FALSE)
  }

  if (!nrow(events)) {
    stop("`events` has no rows.", call. = FALSE)
  }

  if (is.null(event_time_col)) {
    event_time_col <- .gp_rem_guess_col(
      events,
      candidates = c("event_time", "time_s", "time", "timestamp", "onset", "onset_time", "trial_onset", "stimulus_onset"),
      label = "event time",
      required = TRUE
    )
  }

  if (!event_time_col %in% names(events)) {
    stop("`event_time_col` not found in `events`.", call. = FALSE)
  }

  if (is.null(event_id_col)) {
    event_id_col <- .gp_rem_guess_col(
      events,
      candidates = c("event_id", "trial_id", "trial", "stimulus", "screen"),
      label = "event id",
      required = FALSE
    )
  }

  if (is.null(event_label_col)) {
    event_label_col <- .gp_rem_guess_col(
      events,
      candidates = c("event_label", "label", "event", "condition", "type", "stimulus"),
      label = "event label",
      required = FALSE
    )
  }

  out <- events
  out$event_time <- .gp_rem_time_seconds(out[[event_time_col]])
  out$event_id <- if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out[[event_id_col]]
  } else {
    seq_len(nrow(out))
  }
  out$event_label <- if (!is.null(event_label_col) && event_label_col %in% names(out)) {
    as.character(out[[event_label_col]])
  } else {
    paste0("event_", seq_len(nrow(out)))
  }

  first <- c("event_id", "event_time", "event_label")
  out[c(first, setdiff(names(out), first))]
}

.gp_rem_auc <- function(time, signal) {
  ok <- is.finite(time) & is.finite(signal)
  time <- time[ok]
  signal <- signal[ok]

  if (length(time) < 2L) {
    return(NA_real_)
  }

  ord <- order(time)
  time <- time[ord]
  signal <- signal[ord]
  dt <- diff(time)

  sum(dt * (signal[-length(signal)] + signal[-1L]) / 2, na.rm = TRUE)
}

.gp_rem_local_peaks <- function(x, min_distance = 1L) {
  x <- suppressWarnings(as.numeric(x))

  if (length(x) < 3L) {
    return(integer())
  }

  peaks <- which(x[-c(1L, length(x))] > x[-c(length(x) - 1L, length(x))] &
    x[-c(1L, 2L)] <= x[-c(1L, length(x))]) + 1L

  peaks <- peaks[is.finite(x[peaks])]

  if (!length(peaks) || min_distance <= 1L) {
    return(peaks)
  }

  kept <- integer()
  last <- -Inf

  for (p in peaks) {
    if (p - last >= min_distance) {
      kept <- c(kept, p)
      last <- p
    } else if (length(kept) && x[p] > x[kept[length(kept)]]) {
      kept[length(kept)] <- p
      last <- p
    }
  }

  kept
}

.gp_rem_detect_delimiter <- function(path) {
  first <- readLines(path, n = 1L, warn = FALSE)

  if (!length(first)) {
    return(",")
  }

  counts <- c(
    comma = lengths(regmatches(first, gregexpr(",", first, fixed = TRUE))),
    semicolon = lengths(regmatches(first, gregexpr(";", first, fixed = TRUE))),
    tab = lengths(regmatches(first, gregexpr("\t", first, fixed = TRUE)))
  )

  winner <- names(which.max(counts))
  switch(
    winner,
    comma = ",",
    semicolon = ";",
    tab = "\t",
    ","
  )
}

.gp_rem_pupil_cols <- function(data, pupil_cols = NULL) {
  if (!is.null(pupil_cols)) {
    missing <- setdiff(pupil_cols, names(data))
    if (length(missing)) {
      stop("Missing pupil columns: ", paste(missing, collapse = ", "), call. = FALSE)
    }
    return(pupil_cols)
  }

  nms <- names(data)
  hit <- grepl("pupil|^LPD$|^RPD$|diameter", nms, ignore.case = TRUE) &
    !grepl("valid|flag|blink|clean|imputed|outlier|spike|was_", nms, ignore.case = TRUE)

  cols <- nms[hit]
  cols <- cols[vapply(data[cols], is.numeric, logical(1))]

  if (!length(cols)) {
    stop("Could not identify pupil columns. Supply `pupil_cols` explicitly.", call. = FALSE)
  }

  cols
}

.gp_rem_validity_for_pupil <- function(data, pupil_col) {
  nms <- names(data)
  candidates <- switch(
    toupper(pupil_col),
    LPD = c("LPV", "left_pupil_valid", "pupil_left_valid"),
    RPD = c("RPV", "right_pupil_valid", "pupil_right_valid"),
    c(paste0(pupil_col, "_valid"), paste0(pupil_col, "_validity"))
  )

  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) nms[idx[1L]] else NULL
}

#' Compute SCR habituation across trials
#'
#' Estimates habituation of SCR amplitudes across ordered trials, either for a
#' vector or within subjects/groups in a data frame.
#'
#' @param data Numeric SCR-amplitude vector or data frame.
#' @param amplitude_col SCR amplitude column for data-frame input.
#' @param trial_col Trial/order column for data-frame input.
#' @param subject_col Optional subject/grouping column.
#' @param method `"linear"` for raw amplitudes, `"log_linear"` for log1p
#'   amplitudes, or `"ratio"` for first/last ratio only.
#' @param min_trials Minimum valid trials required for model-based estimates.
#'
#' @return Data frame with habituation slope, p value, correlation, and
#'   first/last response summaries.
#' @export
compute_gazepoint_scr_habituation <- function(data,
                                              amplitude_col = NULL,
                                              trial_col = NULL,
                                              subject_col = NULL,
                                              method = c("linear", "log_linear", "ratio"),
                                              min_trials = 3) {
  method <- match.arg(method)

  if (is.numeric(data) && is.null(dim(data))) {
    dat <- data.frame(
      .subject = "all",
      .trial = seq_along(data),
      .amplitude = as.numeric(data),
      stringsAsFactors = FALSE
    )
    subject_col <- ".subject"
    trial_col <- ".trial"
    amplitude_col <- ".amplitude"
  } else {
    .gp_rem_check_df(data)

    if (is.null(amplitude_col)) {
      amplitude_col <- .gp_rem_guess_col(
        data,
        c("scr_amplitude", "amplitude", "SCR", "response_amplitude"),
        "SCR amplitude",
        required = TRUE
      )
    }

    if (is.null(trial_col)) {
      trial_col <- .gp_rem_guess_col(
        data,
        c("trial", "trial_id", "event_id", "order", "trial_order"),
        "trial/order",
        required = FALSE
      )
    }

    dat <- data
    if (is.null(trial_col)) {
      dat$.trial <- seq_len(nrow(dat))
      trial_col <- ".trial"
    }

    if (is.null(subject_col)) {
      dat$.subject <- "all"
      subject_col <- ".subject"
    }
  }

  groups <- .gp_rem_group_indices(dat, subject_col)
  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    amp <- suppressWarnings(as.numeric(dat[[amplitude_col]][idx]))
    trial_raw <- dat[[trial_col]][idx]
    trial <- suppressWarnings(as.numeric(trial_raw))

    if (all(is.na(trial))) {
      trial <- seq_along(amp)
    }

    ok <- is.finite(amp) & is.finite(trial)
    amp <- amp[ok]
    trial <- trial[ok]
    ord <- order(trial)
    amp <- amp[ord]
    trial <- trial[ord]

    n <- length(amp)
    split_n <- max(1L, floor(n / 3L))
    first_mean <- if (n) mean(amp[seq_len(split_n)], na.rm = TRUE) else NA_real_
    last_mean <- if (n) mean(amp[(n - split_n + 1L):n], na.rm = TRUE) else NA_real_
    ratio <- if (is.finite(first_mean) && first_mean != 0) last_mean / first_mean else NA_real_

    slope <- intercept <- p_value <- r_value <- NA_real_

    if (n >= min_trials && method != "ratio") {
      y <- if (method == "log_linear") log1p(pmax(amp, 0)) else amp
      fit <- stats::lm(y ~ trial)
      co <- suppressWarnings(stats::coef(summary(fit)))

      intercept <- unname(co[1L, 1L])
      slope <- unname(co[2L, 1L])
      p_value <- unname(co[2L, 4L])
      r_value <- suppressWarnings(stats::cor(trial, y, use = "complete.obs"))
    }

    k <- k + 1L
    rows[[k]] <- data.frame(
      subject = as.character(dat[[subject_col]][idx[1L]]),
      n_trials = n,
      method = method,
      intercept = intercept,
      habituation_slope = slope,
      p_value = p_value,
      r_value = r_value,
      first_mean = first_mean,
      last_mean = last_mean,
      last_first_ratio = ratio,
      habituation_direction = ifelse(is.finite(slope) & slope < 0, "decreasing",
        ifelse(is.finite(slope) & slope > 0, "increasing", "undetermined")
      ),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Summarize SCR recovery around events
#'
#' Computes event-level baseline, peak amplitude, peak latency, recovery latency,
#' and post-peak recovery slope from EDA/GSR data.
#'
#' @param data EDA/GSR data frame.
#' @param events Event timestamps, event data frame, or event-log path.
#' @param pre Seconds before event onset.
#' @param post Seconds after event onset.
#' @param time_col Time column in `data`.
#' @param signal_col EDA/GSR signal column.
#' @param event_time_col Event-time column in `events`.
#' @param event_id_col Event identifier column in `events`.
#' @param baseline_window Baseline window relative to event onset.
#' @param peak_window Peak-search window relative to event onset.
#' @param recovery_fraction Fraction of peak amplitude used as recovery target.
#'
#' @return Data frame with one row per event.
#' @export
summarize_gazepoint_scr_recovery <- function(data,
                                             events,
                                             pre = 1,
                                             post = 6,
                                             time_col = NULL,
                                             signal_col = NULL,
                                             event_time_col = NULL,
                                             event_id_col = NULL,
                                             baseline_window = NULL,
                                             peak_window = c(0.5, 4),
                                             recovery_fraction = 0.5) {
  .gp_rem_check_df(data)

  if (missing(events)) {
    stop("Supply `events`.", call. = FALSE)
  }

  if (!is.numeric(pre) || !is.numeric(post) || pre < 0 || post <= 0) {
    stop("`pre` must be non-negative and `post` must be positive.", call. = FALSE)
  }

  if (is.null(baseline_window)) {
    baseline_window <- c(-pre, 0)
  }

  time_col <- if (is.null(time_col)) {
    .gp_rem_guess_col(data, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", TRUE)
  } else {
    time_col
  }

  signal_col <- if (is.null(signal_col)) {
    .gp_rem_guess_col(data, c("GSR", "EDA", "SCR", "eda", "gsr", "skin_conductance"), "EDA/GSR signal", TRUE)
  } else {
    signal_col
  }

  events <- .gp_rem_standardize_events(events, event_time_col, event_id_col)
  time <- .gp_rem_time_seconds(data[[time_col]])
  signal <- suppressWarnings(as.numeric(data[[signal_col]]))

  rows <- vector("list", nrow(events))

  for (i in seq_len(nrow(events))) {
    et <- as.numeric(events$event_time[i])
    rel <- time - et
    idx <- which(rel >= -pre & rel <= post)

    if (!length(idx)) {
      rows[[i]] <- data.frame(
        event_id = events$event_id[i],
        event_time = et,
        event_label = events$event_label[i],
        n_samples = 0L,
        baseline_mean = NA_real_,
        peak_amplitude = NA_real_,
        peak_latency_s = NA_real_,
        recovery_target = NA_real_,
        recovery_latency_s = NA_real_,
        recovery_slope = NA_real_,
        recovered = FALSE,
        stringsAsFactors = FALSE
      )
      next
    }

    rr <- rel[idx]
    yy <- signal[idx]

    bidx <- rr >= baseline_window[1L] & rr <= baseline_window[2L]
    baseline <- if (any(bidx, na.rm = TRUE)) mean(yy[bidx], na.rm = TRUE) else NA_real_
    bc <- yy - baseline

    pidx <- rr >= peak_window[1L] & rr <= peak_window[2L] & is.finite(bc)

    if (any(pidx)) {
      peak_local <- which(pidx)[which.max(bc[pidx])]
      peak_amp <- bc[peak_local]
      peak_latency <- rr[peak_local]
      target <- peak_amp * recovery_fraction
      after_peak <- which(rr > peak_latency & rr <= post & is.finite(bc))
      recovered_i <- after_peak[bc[after_peak] <= target]
      recovery_latency <- if (length(recovered_i)) rr[recovered_i[1L]] else NA_real_
      recovered <- length(recovered_i) > 0

      slope_idx <- after_peak
      recovery_slope <- if (length(slope_idx) >= 3L) {
        unname(stats::coef(stats::lm(bc[slope_idx] ~ rr[slope_idx]))[2L])
      } else {
        NA_real_
      }
    } else {
      peak_amp <- peak_latency <- target <- recovery_latency <- recovery_slope <- NA_real_
      recovered <- FALSE
    }

    rows[[i]] <- data.frame(
      event_id = events$event_id[i],
      event_time = et,
      event_label = events$event_label[i],
      n_samples = length(idx),
      baseline_mean = baseline,
      peak_amplitude = peak_amp,
      peak_latency_s = peak_latency,
      recovery_target = target,
      recovery_latency_s = recovery_latency,
      recovery_slope = recovery_slope,
      recovered = recovered,
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Summarize event-related pupil responses
#'
#' Computes event-level baseline-corrected pupil metrics, including peak
#' dilation, peak latency, mean response, and area under the curve.
#'
#' @param data Pupil data frame.
#' @param events Event timestamps, event data frame, or event-log path.
#' @param pre Seconds before event onset.
#' @param post Seconds after event onset.
#' @param time_col Time column.
#' @param pupil_col Pupil column.
#' @param event_time_col Event-time column in `events`.
#' @param event_id_col Event identifier column in `events`.
#' @param baseline_window Baseline window relative to event onset.
#' @param response_window Response window relative to event onset.
#'
#' @return Data frame with one row per event.
#' @export
summarize_gazepoint_pupil_events <- function(data,
                                             events,
                                             pre = 1,
                                             post = 3,
                                             time_col = NULL,
                                             pupil_col = NULL,
                                             event_time_col = NULL,
                                             event_id_col = NULL,
                                             baseline_window = NULL,
                                             response_window = c(0, 3)) {
  .gp_rem_check_df(data)

  if (missing(events)) {
    stop("Supply `events`.", call. = FALSE)
  }

  if (is.null(baseline_window)) {
    baseline_window <- c(-pre, 0)
  }

  time_col <- if (is.null(time_col)) {
    .gp_rem_guess_col(data, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", TRUE)
  } else {
    time_col
  }

  pupil_col <- if (is.null(pupil_col)) {
    .gp_rem_pupil_cols(data)[1L]
  } else {
    pupil_col
  }

  events <- .gp_rem_standardize_events(events, event_time_col, event_id_col)
  time <- .gp_rem_time_seconds(data[[time_col]])
  pupil <- suppressWarnings(as.numeric(data[[pupil_col]]))

  rows <- vector("list", nrow(events))

  for (i in seq_len(nrow(events))) {
    et <- as.numeric(events$event_time[i])
    rel <- time - et
    idx <- which(rel >= -pre & rel <= post)

    rr <- rel[idx]
    pp <- pupil[idx]

    bidx <- rr >= baseline_window[1L] & rr <= baseline_window[2L]
    baseline <- if (any(bidx, na.rm = TRUE)) mean(pp[bidx], na.rm = TRUE) else NA_real_
    bc <- pp - baseline

    ridx <- rr >= response_window[1L] & rr <= response_window[2L] & is.finite(bc)

    if (any(ridx)) {
      local <- which(ridx)[which.max(bc[ridx])]
      peak <- bc[local]
      peak_latency <- rr[local]
      response_mean <- mean(bc[ridx], na.rm = TRUE)
      response_auc <- .gp_rem_auc(rr[ridx], bc[ridx])
    } else {
      peak <- peak_latency <- response_mean <- response_auc <- NA_real_
    }

    rows[[i]] <- data.frame(
      event_id = events$event_id[i],
      event_time = et,
      event_label = events$event_label[i],
      n_samples = length(idx),
      baseline_mean = baseline,
      pupil_peak_dilation = peak,
      pupil_peak_latency_s = peak_latency,
      pupil_mean_dilation = response_mean,
      pupil_auc = response_auc,
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Summarize Gazepoint tracking validity
#'
#' Computes valid-pupil, valid-gaze, and combined tracking ratios overall or by
#' participant/trial/group.
#'
#' @param data Eye-tracking data frame.
#' @param pupil_cols Optional pupil columns.
#' @param x_col Optional gaze x column.
#' @param y_col Optional gaze y column.
#' @param group_cols Optional grouping columns.
#' @param screen_bounds Numeric vector `c(x_min, x_max, y_min, y_max)`.
#' @param nonpositive_is_invalid If TRUE, non-positive pupil values are invalid.
#'
#' @return Data frame of tracking ratios by group.
#' @export
summarize_gazepoint_tracking <- function(data,
                                         pupil_cols = NULL,
                                         x_col = NULL,
                                         y_col = NULL,
                                         group_cols = NULL,
                                         screen_bounds = c(0, 1, 0, 1),
                                         nonpositive_is_invalid = TRUE) {
  .gp_rem_check_df(data)

  pupil_cols <- tryCatch(.gp_rem_pupil_cols(data, pupil_cols), error = function(e) character())

  if (is.null(x_col)) {
    x_col <- .gp_rem_guess_col(data, c("BPOGX", "FPOGX", "GPOGX", "x", "gaze_x"), "gaze x", FALSE)
  }
  if (is.null(y_col)) {
    y_col <- .gp_rem_guess_col(data, c("BPOGY", "FPOGY", "GPOGY", "y", "gaze_y"), "gaze y", FALSE)
  }

  groups <- .gp_rem_group_indices(data, group_cols)
  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]

    pupil_valid <- rep(NA, length(idx))
    if (length(pupil_cols)) {
      mat <- matrix(TRUE, nrow = length(idx), ncol = length(pupil_cols))
      for (j in seq_along(pupil_cols)) {
        cc <- pupil_cols[j]
        x <- suppressWarnings(as.numeric(data[[cc]][idx]))
        valid <- is.finite(x)
        if (isTRUE(nonpositive_is_invalid)) valid <- valid & x > 0

        vc <- .gp_rem_validity_for_pupil(data, cc)
        if (!is.null(vc)) {
          vv <- suppressWarnings(as.numeric(data[[vc]][idx]))
          valid <- valid & is.finite(vv) & vv > 0
        }

        mat[, j] <- valid
      }
      pupil_valid <- rowSums(mat) == ncol(mat)
    }

    gaze_valid <- rep(NA, length(idx))
    if (!is.null(x_col) && !is.null(y_col)) {
      gx <- suppressWarnings(as.numeric(data[[x_col]][idx]))
      gy <- suppressWarnings(as.numeric(data[[y_col]][idx]))
      gaze_valid <- is.finite(gx) & is.finite(gy) &
        gx >= screen_bounds[1L] & gx <= screen_bounds[2L] &
        gy >= screen_bounds[3L] & gy <= screen_bounds[4L]
    }

    combined <- if (all(is.na(pupil_valid))) {
      gaze_valid
    } else if (all(is.na(gaze_valid))) {
      pupil_valid
    } else {
      pupil_valid & gaze_valid
    }

    k <- k + 1L
    row <- data.frame(
      group = g,
      n_samples = length(idx),
      pupil_valid_ratio = mean(pupil_valid, na.rm = TRUE),
      gaze_valid_ratio = mean(gaze_valid, na.rm = TRUE),
      tracking_ratio = mean(combined, na.rm = TRUE),
      n_invalid_tracking = sum(!combined, na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    if (!is.null(group_cols) && length(group_cols)) {
      row <- cbind(data[idx[1L], group_cols, drop = FALSE], row[setdiff(names(row), "group")])
    }

    rows[[k]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Audit pupil-luminance confounding
#'
#' Computes correlations between pupil size and luminance/brightness and flags
#' groups where the absolute association exceeds a threshold.
#'
#' @param data Data frame containing pupil and luminance columns.
#' @param pupil_col Pupil column.
#' @param luminance_col Luminance/brightness column.
#' @param group_cols Optional grouping columns.
#' @param threshold Absolute correlation threshold for flagging.
#' @param method Correlation method.
#'
#' @return Data frame with correlation and flag columns.
#' @export
audit_gazepoint_pupil_luminance <- function(data,
                                            pupil_col = NULL,
                                            luminance_col = NULL,
                                            group_cols = NULL,
                                            threshold = 0.30,
                                            method = c("pearson", "spearman")) {
  .gp_rem_check_df(data)
  method <- match.arg(method)

  pupil_col <- if (is.null(pupil_col)) .gp_rem_pupil_cols(data)[1L] else pupil_col
  luminance_col <- if (is.null(luminance_col)) {
    .gp_rem_guess_col(
      data,
      c("luminance", "brightness", "lum", "screen_luminance", "stimulus_luminance"),
      "luminance",
      TRUE
    )
  } else {
    luminance_col
  }

  groups <- .gp_rem_group_indices(data, group_cols)
  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    x <- suppressWarnings(as.numeric(data[[pupil_col]][idx]))
    y <- suppressWarnings(as.numeric(data[[luminance_col]][idx]))
    ok <- is.finite(x) & is.finite(y)

    r <- if (sum(ok) >= 3L) {
      suppressWarnings(stats::cor(x[ok], y[ok], method = method))
    } else {
      NA_real_
    }

    k <- k + 1L
    row <- data.frame(
      group = g,
      n_complete = sum(ok),
      pupil_col = pupil_col,
      luminance_col = luminance_col,
      correlation = r,
      abs_correlation = abs(r),
      threshold = threshold,
      flag_luminance_confound = is.finite(r) && abs(r) >= threshold,
      method = method,
      stringsAsFactors = FALSE
    )

    if (!is.null(group_cols) && length(group_cols)) {
      row <- cbind(data[idx[1L], group_cols, drop = FALSE], row[setdiff(names(row), "group")])
    }

    rows[[k]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Extract simple PPG pulse morphology metrics
#'
#' Extracts peak-centered pulse morphology metrics from a PPG/BVP signal,
#' including rise time, decay time, half-amplitude width, pulse amplitude, and a
#' simple post-peak notch proxy.
#'
#' @param data PPG data frame.
#' @param time_col Time column.
#' @param ppg_col PPG/BVP signal column.
#' @param peaks Optional peak indices or peak times.
#' @param min_peak_distance_s Minimum distance between automatically detected
#'   peaks.
#'
#' @return Data frame with one row per pulse peak.
#' @export
extract_gazepoint_ppg_morphology <- function(data,
                                             time_col = NULL,
                                             ppg_col = NULL,
                                             peaks = NULL,
                                             min_peak_distance_s = 0.30) {
  .gp_rem_check_df(data)

  time_col <- if (is.null(time_col)) {
    .gp_rem_guess_col(data, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", TRUE)
  } else {
    time_col
  }

  ppg_col <- if (is.null(ppg_col)) {
    .gp_rem_guess_col(data, c("PPG", "BVP", "HRP", "ppg", "bvp", "pulse"), "PPG/BVP signal", TRUE)
  } else {
    ppg_col
  }

  time <- .gp_rem_time_seconds(data[[time_col]])
  signal <- suppressWarnings(as.numeric(data[[ppg_col]]))

  dt <- stats::median(diff(time), na.rm = TRUE)
  min_distance <- if (is.finite(dt) && dt > 0) max(1L, round(min_peak_distance_s / dt)) else 1L

  if (is.null(peaks)) {
    peak_idx <- .gp_rem_local_peaks(signal, min_distance = min_distance)
  } else {
    peaks <- suppressWarnings(as.numeric(peaks))
    if (all(is.finite(peaks) & peaks >= 1 & peaks <= length(signal) & abs(peaks - round(peaks)) < 1e-8)) {
      peak_idx <- as.integer(round(peaks))
    } else {
      peak_idx <- vapply(peaks, function(z) which.min(abs(time - z)), integer(1))
    }
  }

  peak_idx <- sort(unique(peak_idx))
  peak_idx <- peak_idx[peak_idx > 2L & peak_idx < length(signal) - 1L]

  if (!length(peak_idx)) {
    return(data.frame())
  }

  rows <- vector("list", length(peak_idx))
  k <- 0L

  for (i in seq_along(peak_idx)) {
    p <- peak_idx[i]
    left_bound <- if (i == 1L) 1L else peak_idx[i - 1L]
    right_bound <- if (i == length(peak_idx)) length(signal) else peak_idx[i + 1L]

    left_range <- left_bound:p
    right_range <- p:right_bound

    left_trough <- left_range[which.min(signal[left_range])]
    right_trough <- right_range[which.min(signal[right_range])]

    amp <- signal[p] - signal[left_trough]
    half_level <- signal[left_trough] + amp / 2

    left_cross_candidates <- left_range[signal[left_range] <= half_level]
    right_cross_candidates <- right_range[signal[right_range] <= half_level]

    left_cross <- if (length(left_cross_candidates)) max(left_cross_candidates) else left_trough
    right_cross <- if (length(right_cross_candidates)) min(right_cross_candidates) else right_trough

    notch_range <- p:min(length(signal), p + max(3L, round(0.35 / dt)))
    notch_idx <- if (length(notch_range) >= 3L) {
      notch_range[which.min(signal[notch_range])]
    } else {
      NA_integer_
    }

    k <- k + 1L
    rows[[k]] <- data.frame(
      pulse_id = k,
      peak_index = p,
      peak_time = time[p],
      peak_value = signal[p],
      left_trough_index = left_trough,
      right_trough_index = right_trough,
      pulse_amplitude = amp,
      rise_time_s = time[p] - time[left_trough],
      decay_time_s = time[right_trough] - time[p],
      half_width_s = time[right_cross] - time[left_cross],
      notch_proxy_index = notch_idx,
      notch_proxy_latency_s = if (is.finite(notch_idx)) time[notch_idx] - time[p] else NA_real_,
      notch_proxy_value = if (is.finite(notch_idx)) signal[notch_idx] else NA_real_,
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Flag segment-level PPG quality
#'
#' Computes windowed PPG quality metrics and flags segments with excessive
#' missingness, flatness, or robust outliers.
#'
#' @param data PPG data frame.
#' @param time_col Time column.
#' @param ppg_col PPG/BVP signal column.
#' @param window_s Window duration in seconds.
#' @param step_s Step size in seconds. Defaults to `window_s`.
#' @param missing_prop_threshold Maximum allowed missing proportion.
#' @param flat_sd_threshold Minimum allowed standard deviation.
#' @param outlier_prop_threshold Maximum allowed robust outlier proportion.
#'
#' @return Data frame with one row per segment.
#' @export
flag_gazepoint_ppg_quality <- function(data,
                                       time_col = NULL,
                                       ppg_col = NULL,
                                       window_s = 10,
                                       step_s = NULL,
                                       missing_prop_threshold = 0.20,
                                       flat_sd_threshold = 1e-6,
                                       outlier_prop_threshold = 0.10) {
  .gp_rem_check_df(data)

  if (is.null(step_s)) {
    step_s <- window_s
  }

  time_col <- if (is.null(time_col)) {
    .gp_rem_guess_col(data, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", TRUE)
  } else {
    time_col
  }

  ppg_col <- if (is.null(ppg_col)) {
    .gp_rem_guess_col(data, c("PPG", "BVP", "HRP", "ppg", "bvp", "pulse"), "PPG/BVP signal", TRUE)
  } else {
    ppg_col
  }

  time <- .gp_rem_time_seconds(data[[time_col]])
  signal <- suppressWarnings(as.numeric(data[[ppg_col]]))

  starts <- seq(min(time, na.rm = TRUE), max(time, na.rm = TRUE), by = step_s)
  rows <- vector("list", length(starts))
  k <- 0L

  for (s in starts) {
    e <- s + window_s
    idx <- which(time >= s & time < e)

    if (!length(idx)) {
      next
    }

    x <- signal[idx]
    missing_prop <- mean(!is.finite(x))
    finite_x <- x[is.finite(x)]
    sd_x <- stats::sd(finite_x, na.rm = TRUE)

    med <- stats::median(finite_x, na.rm = TRUE)
    sc <- stats::mad(finite_x, constant = 1.4826, na.rm = TRUE)

    outlier_prop <- if (!is.finite(sc) || sc == 0 || !length(finite_x)) {
      0
    } else {
      mean(abs(finite_x - med) > 5 * sc, na.rm = TRUE)
    }

    flatline_prop <- if (length(finite_x) >= 2L) {
      mean(abs(diff(finite_x)) <= flat_sd_threshold, na.rm = TRUE)
    } else {
      NA_real_
    }

    quality_ok <- missing_prop <= missing_prop_threshold &&
      is.finite(sd_x) && sd_x >= flat_sd_threshold &&
      outlier_prop <= outlier_prop_threshold

    k <- k + 1L
    rows[[k]] <- data.frame(
      segment_id = k,
      start_time = s,
      end_time = e,
      n_samples = length(idx),
      missing_prop = missing_prop,
      sd_signal = sd_x,
      range_signal = if (length(finite_x)) diff(range(finite_x, na.rm = TRUE)) else NA_real_,
      flatline_prop = flatline_prop,
      outlier_prop = outlier_prop,
      quality_ok = quality_ok,
      quality_flag = ifelse(quality_ok, "ok", "review"),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows[seq_len(k)])
  row.names(out) <- NULL
  out
}

#' Import a generic Gazepoint-compatible event log
#'
#' Reads a CSV/TSV event log and standardizes event identifiers, timestamps, and
#' labels for alignment with Gazepoint biometric or eye-tracking data.
#'
#' @param path Path to a CSV/TSV file, or an existing data frame.
#' @param time_col Event time column.
#' @param event_col Event label column.
#' @param id_col Optional event identifier column.
#' @param sep Optional delimiter. If NULL, it is guessed from the first line.
#' @param ... Additional arguments passed to `utils::read.table()`.
#'
#' @return Data frame with `event_id`, `event_time`, and `event_label`.
#' @export
import_gazepoint_event_log <- function(path,
                                       time_col = NULL,
                                       event_col = NULL,
                                       id_col = NULL,
                                       sep = NULL,
                                       ...) {
  if (is.data.frame(path)) {
    dat <- path
  } else {
    if (!is.character(path) || length(path) != 1L || !file.exists(path)) {
      stop("`path` must be an existing event-log path or a data frame.", call. = FALSE)
    }

    if (is.null(sep)) {
      sep <- .gp_rem_detect_delimiter(path)
    }

    dat <- utils::read.table(
      path,
      sep = sep,
      header = TRUE,
      stringsAsFactors = FALSE,
      check.names = FALSE,
      comment.char = "",
      ...
    )
  }

  .gp_rem_check_df(dat, "event log")

  if (is.null(time_col)) {
    time_col <- .gp_rem_guess_col(
      dat,
      c("event_time", "time_s", "time", "timestamp", "onset", "onset_time", "trial_onset", "stimulus_onset"),
      "event time",
      TRUE
    )
  }

  if (is.null(event_col)) {
    event_col <- .gp_rem_guess_col(
      dat,
      c("event_label", "label", "event", "condition", "type", "stimulus"),
      "event label",
      FALSE
    )
  }

  if (is.null(id_col)) {
    id_col <- .gp_rem_guess_col(
      dat,
      c("event_id", "trial_id", "trial", "id"),
      "event id",
      FALSE
    )
  }

  out <- dat
  out$event_time <- .gp_rem_time_seconds(out[[time_col]])
  out$event_id <- if (!is.null(id_col) && id_col %in% names(out)) out[[id_col]] else seq_len(nrow(out))
  out$event_label <- if (!is.null(event_col) && event_col %in% names(out)) {
    as.character(out[[event_col]])
  } else {
    paste0("event_", seq_len(nrow(out)))
  }

  first <- c("event_id", "event_time", "event_label")
  out <- out[c(first, setdiff(names(out), first))]
  row.names(out) <- NULL
  out
}

#' Match events to biometric windows
#'
#' Aligns event logs to Gazepoint biometric or eye-tracking data and returns
#' either sample-level event windows or event-level summary features.
#'
#' @param data Biometric or eye-tracking data frame.
#' @param events Event timestamps, event data frame, or event-log path.
#' @param pre Seconds before event onset.
#' @param post Seconds after event onset.
#' @param time_col Time column in `data`.
#' @param event_time_col Event-time column in `events`.
#' @param event_id_col Event identifier column in `events`.
#' @param summary_cols Numeric columns to summarize when `return = "summary"`.
#' @param return `"windows"` or `"summary"`.
#'
#' @return Data frame of sample-level windows or event-level summaries.
#' @export
match_gazepoint_events_to_biometrics <- function(data,
                                                 events,
                                                 pre = 0,
                                                 post = 5,
                                                 time_col = NULL,
                                                 event_time_col = NULL,
                                                 event_id_col = NULL,
                                                 summary_cols = NULL,
                                                 return = c("windows", "summary")) {
  .gp_rem_check_df(data)
  return <- match.arg(return)

  if (missing(events)) {
    stop("Supply `events`.", call. = FALSE)
  }

  time_col <- if (is.null(time_col)) {
    .gp_rem_guess_col(data, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", TRUE)
  } else {
    time_col
  }

  events <- .gp_rem_standardize_events(events, event_time_col, event_id_col)
  time <- .gp_rem_time_seconds(data[[time_col]])

  if (is.null(summary_cols)) {
    summary_cols <- setdiff(names(data)[vapply(data, is.numeric, logical(1))], time_col)
  }

  if (return == "windows") {
    rows <- vector("list", nrow(events))

    for (i in seq_len(nrow(events))) {
      et <- as.numeric(events$event_time[i])
      idx <- which(time >= et - pre & time <= et + post)

      if (!length(idx)) {
        rows[[i]] <- NULL
        next
      }

      z <- data[idx, , drop = FALSE]
      z$event_id <- events$event_id[i]
      z$event_time <- et
      z$event_label <- events$event_label[i]
      z$relative_time_s <- time[idx] - et
      rows[[i]] <- z
    }

    out <- do.call(rbind, rows)
    if (is.null(out)) out <- data.frame()
    row.names(out) <- NULL
    return(out)
  }

  rows <- vector("list", nrow(events))

  for (i in seq_len(nrow(events))) {
    et <- as.numeric(events$event_time[i])
    idx <- which(time >= et - pre & time <= et + post)

    row <- data.frame(
      event_id = events$event_id[i],
      event_time = et,
      event_label = events$event_label[i],
      n_samples = length(idx),
      stringsAsFactors = FALSE
    )

    for (cc in summary_cols) {
      x <- suppressWarnings(as.numeric(data[[cc]][idx]))
      row[[paste0(cc, "_mean")]] <- mean(x, na.rm = TRUE)
      row[[paste0(cc, "_sd")]] <- stats::sd(x, na.rm = TRUE)
      row[[paste0(cc, "_min")]] <- if (length(x)) min(x, na.rm = TRUE) else NA_real_
      row[[paste0(cc, "_max")]] <- if (length(x)) max(x, na.rm = TRUE) else NA_real_
      row[[paste0(cc, "_missing_prop")]] <- if (length(x)) mean(!is.finite(x)) else NA_real_
    }

    rows[[i]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Assert that required Gazepoint columns are present
#'
#' Validates expected columns and either throws an error, raises a warning, or
#' returns a summary table.
#'
#' @param data Data frame.
#' @param required Character vector of required columns.
#' @param optional Character vector of optional columns.
#' @param mode `"error"`, `"warning"`, or `"summary"`.
#' @param ignore_case If TRUE, match columns case-insensitively.
#'
#' @return Invisibly TRUE for passing checks, or a summary data frame when
#'   `mode = "summary"`.
#' @export
assert_gazepoint_columns <- function(data,
                                     required,
                                     optional = character(),
                                     mode = c("error", "warning", "summary"),
                                     ignore_case = TRUE) {
  .gp_rem_check_df(data)
  mode <- match.arg(mode)

  if (!is.character(required)) {
    stop("`required` must be a character vector.", call. = FALSE)
  }
  if (!is.character(optional)) {
    stop("`optional` must be a character vector.", call. = FALSE)
  }

  nms <- names(data)

  match_one <- function(x) {
    if (isTRUE(ignore_case)) {
      hit <- match(tolower(x), tolower(nms))
    } else {
      hit <- match(x, nms)
    }

    if (is.na(hit)) NA_character_ else nms[hit]
  }

  required_match <- vapply(required, match_one, character(1))
  optional_match <- vapply(optional, match_one, character(1))

  required_summary <- data.frame(
    column = required,
    role = rep("required", length(required)),
    present = !is.na(required_match),
    matched_name = unname(required_match),
    stringsAsFactors = FALSE
  )

  optional_summary <- data.frame(
    column = optional,
    role = rep("optional", length(optional)),
    present = !is.na(optional_match),
    matched_name = unname(optional_match),
    stringsAsFactors = FALSE
  )

  summary <- rbind(required_summary, optional_summary)

  missing_required <- summary$column[summary$role == "required" & !summary$present]

  if (length(missing_required) && mode == "error") {
    stop("Missing required Gazepoint columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (length(missing_required) && mode == "warning") {
    warning("Missing required Gazepoint columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (mode == "summary") {
    return(summary)
  }

  invisible(TRUE)
}

#' Print gpbiometrics reproducibility information
#'
#' Returns package, R, platform, and session information useful for manuscripts,
#' reproducibility logs, and bug reports.
#'
#' @param print If TRUE, print a compact summary.
#' @param include_session If TRUE, include `utils::sessionInfo()` in the return
#'   object.
#'
#' @return A list with package and session metadata.
#' @export
gpbiometrics_info <- function(print = TRUE, include_session = FALSE) {
  desc <- utils::packageDescription("gpbiometrics")
  version <- as.character(utils::packageVersion("gpbiometrics"))

  out <- list(
    package = "gpbiometrics",
    version = version,
    title = desc$Title,
    url = desc$URL,
    bug_reports = desc$BugReports,
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    platform = R.version$platform,
    os = Sys.info()[["sysname"]],
    date = as.character(Sys.Date())
  )

  if (isTRUE(include_session)) {
    out$session_info <- utils::sessionInfo()
  }

  if (isTRUE(print)) {
    cat("gpbiometrics", version, "\n")
    cat("R", out$r_version, "on", out$platform, "\n")
    if (!is.null(out$url) && nzchar(out$url)) cat("URL:", out$url, "\n")
    if (!is.null(out$bug_reports) && nzchar(out$bug_reports)) cat("Bug reports:", out$bug_reports, "\n")
  }

  invisible(out)
}

