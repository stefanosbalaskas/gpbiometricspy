
# Physiology/QC refinements:
# HRV segment flags, SCR latency, signal-lag matrix, and exploratory
# PPG-derived respiration estimation.

.gp_c3_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_c3_guess_col <- function(data, candidates, label, required = TRUE) {
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

.gp_c3_time_seconds <- function(time) {
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

.gp_c3_time_col <- function(data, required = TRUE) {
  .gp_c3_guess_col(
    data,
    c("time_s", "time", "timestamp", "event_time", "MSTIMER", "TIME", "CNT"),
    "time",
    required = required
  )
}

.gp_c3_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))
  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_c3_bind_rows <- function(rows) {
  rows <- rows[!vapply(rows, is.null, logical(1))]

  if (!length(rows)) {
    return(data.frame())
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

.gp_c3_interval_to_ms <- function(rr) {
  rr <- suppressWarnings(as.numeric(rr))
  finite_rr <- rr[is.finite(rr)]

  if (!length(finite_rr)) {
    return(rr)
  }

  if (stats::median(finite_rr, na.rm = TRUE) < 10) {
    rr * 1000
  } else {
    rr
  }
}

.gp_c3_event_table <- function(events,
                               event_time_col = NULL,
                               event_id_col = NULL) {
  if (is.numeric(events) && is.null(dim(events))) {
    return(data.frame(
      event_id = paste0("E", seq_along(events)),
      event_time_s = .gp_c3_time_seconds(events),
      stringsAsFactors = FALSE
    ))
  }

  .gp_c3_check_df(events, "events")

  if (is.null(event_time_col)) {
    event_time_col <- .gp_c3_guess_col(
      events,
      c("event_time_s", "event_time", "onset", "onset_s", "time_s", "time", "timestamp", "MSTIMER"),
      "event time",
      TRUE
    )
  }

  if (is.null(event_id_col)) {
    event_id_col <- .gp_c3_guess_col(
      events,
      c("event_id", "event", "marker", "trial", "trial_id", "condition"),
      "event id",
      FALSE
    )
  }

  out <- events
  out$event_time_s <- .gp_c3_time_seconds(out[[event_time_col]])

  if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out$event_id <- as.character(out[[event_id_col]])
  } else {
    out$event_id <- paste0("E", seq_len(nrow(out)))
  }

  out
}

.gp_c3_auc <- function(time, value) {
  time <- suppressWarnings(as.numeric(time))
  value <- suppressWarnings(as.numeric(value))
  ok <- is.finite(time) & is.finite(value)

  if (sum(ok) < 2L) {
    return(NA_real_)
  }

  time <- time[ok]
  value <- value[ok]
  ord <- order(time)
  time <- time[ord]
  value <- value[ord]

  sum(diff(time) * (utils::head(value, -1L) + utils::tail(value, -1L)) / 2)
}

.gp_c3_match_event_groups <- function(data, event_row, group_cols) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(seq_len(nrow(data)))
  }

  common <- intersect(group_cols, intersect(names(data), names(event_row)))

  if (!length(common)) {
    return(seq_len(nrow(data)))
  }

  keep <- rep(TRUE, nrow(data))

  for (cc in common) {
    keep <- keep & as.character(data[[cc]]) == as.character(event_row[[cc]][1L])
  }

  which(keep)
}

.gp_c3_regularize_signal <- function(time, value, sampling_rate_hz = NULL) {
  time <- .gp_c3_time_seconds(time)
  value <- suppressWarnings(as.numeric(value))
  ok <- is.finite(time) & is.finite(value)

  if (sum(ok) < 4L) {
    return(list(time = numeric(), value = numeric(), sampling_rate_hz = NA_real_))
  }

  time <- time[ok]
  value <- value[ok]
  ord <- order(time)
  time <- time[ord]
  value <- value[ord]

  keep <- !duplicated(time)
  time <- time[keep]
  value <- value[keep]

  if (length(time) < 4L) {
    return(list(time = numeric(), value = numeric(), sampling_rate_hz = NA_real_))
  }

  if (is.null(sampling_rate_hz)) {
    d <- diff(time)
    d <- d[is.finite(d) & d > 0]
    dt <- if (length(d)) stats::median(d, na.rm = TRUE) else NA_real_
    sampling_rate_hz <- if (is.finite(dt) && dt > 0) 1 / dt else NA_real_
  }

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    return(list(time = numeric(), value = numeric(), sampling_rate_hz = NA_real_))
  }

  grid <- seq(min(time), max(time), by = 1 / sampling_rate_hz)

  list(
    time = grid,
    value = stats::approx(time, value, xout = grid, rule = 2, ties = mean)$y,
    sampling_rate_hz = sampling_rate_hz
  )
}

.gp_c3_fft_spectrum <- function(value, sampling_rate_hz) {
  value <- suppressWarnings(as.numeric(value))
  value <- value[is.finite(value)]

  if (length(value) < 8L || !is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    return(data.frame(frequency_hz = numeric(), power = numeric()))
  }

  value <- value - mean(value, na.rm = TRUE)
  n <- length(value)

  taper <- 0.5 - 0.5 * cos(2 * pi * (seq_len(n) - 1) / max(1, n - 1))
  z <- stats::fft(value * taper)

  half <- seq_len(floor(n / 2))
  freq <- (half - 1) * sampling_rate_hz / n
  power <- (Mod(z[half])^2) / n

  data.frame(
    frequency_hz = freq,
    power = power,
    stringsAsFactors = FALSE
  )
}

#' Flag HRV/RR segments for quality review
#'
#' Splits RR/NN intervals into windows and flags segments with too few beats,
#' implausible intervals, excessive beat-to-beat changes, short duration, or
#' high artifact burden. The helper is intended as transparent QC before HRV
#' summaries or mixed-model analysis.
#'
#' @param data Data frame or numeric RR/NN interval vector.
#' @param rr_col RR/NN interval column for data-frame input.
#' @param time_col Optional timestamp column. If omitted, cumulative RR time is
#'   used.
#' @param group_cols Optional grouping columns such as participant or condition.
#' @param window_s Optional window length in seconds. If NULL, one segment is
#'   returned per group.
#' @param min_beats Minimum finite beats required for `quality_ok`.
#' @param min_duration_s Minimum segment duration in seconds.
#' @param min_rr_ms Minimum plausible RR interval in milliseconds.
#' @param max_rr_ms Maximum plausible RR interval in milliseconds.
#' @param max_artifact_prop Maximum allowed artifact proportion.
#' @param max_successive_change_prop Maximum allowed proportional beat-to-beat
#'   change before an interval is flagged.
#'
#' @return Data frame with one row per segment.
#' @export
flag_gazepoint_hrv_segments <- function(data,
                                        rr_col = NULL,
                                        time_col = NULL,
                                        group_cols = NULL,
                                        window_s = 60,
                                        min_beats = 20,
                                        min_duration_s = 20,
                                        min_rr_ms = 300,
                                        max_rr_ms = 2000,
                                        max_artifact_prop = 0.20,
                                        max_successive_change_prop = 0.20) {
  vector_input <- is.numeric(data) && is.null(dim(data))

  if (isTRUE(vector_input)) {
    rr_ms <- .gp_c3_interval_to_ms(data)
    rr_s <- rr_ms / 1000
    data <- data.frame(
      segment_time_s = cumsum(c(0, utils::head(rr_s, -1L))),
      rr = rr_ms
    )
    rr_col <- "rr"
    time_col <- "segment_time_s"
  }

  .gp_c3_check_df(data)

  if (is.null(rr_col)) {
    rr_col <- .gp_c3_guess_col(
      data,
      c("rr", "RR", "RRI", "NN", "IBI", "ibi", "rr_ms", "ibi_ms"),
      "RR/NN interval",
      TRUE
    )
  }

  if (is.null(time_col)) {
    time_col <- .gp_c3_guess_col(
      data,
      c("time_s", "time", "timestamp", "segment_time_s", "MSTIMER"),
      "time",
      FALSE
    )
  }

  rr_ms_all <- .gp_c3_interval_to_ms(data[[rr_col]])

  if (!is.null(time_col) && time_col %in% names(data)) {
    time_all <- .gp_c3_time_seconds(data[[time_col]])
  } else {
    rr_s <- rr_ms_all / 1000
    time_all <- cumsum(c(0, utils::head(rr_s, -1L)))
  }

  data$.gp_rr_ms <- rr_ms_all
  data$.gp_time_s <- time_all

  groups <- .gp_c3_group_indices(data, group_cols)
  rows <- list()
  k <- 0L

  for (g in names(groups)) {
    idx_group <- groups[[g]]
    z <- data[idx_group, , drop = FALSE]
    time <- z$.gp_time_s
    rr <- z$.gp_rr_ms

    ok_time <- is.finite(time)
    if (!any(ok_time)) {
      next
    }

    start_time <- min(time[ok_time], na.rm = TRUE)

    if (is.null(window_s)) {
      segment_id <- rep(1L, nrow(z))
    } else {
      segment_id <- floor((time - start_time) / window_s) + 1L
    }

    for (seg in sort(unique(segment_id[is.finite(segment_id)]))) {
      idx <- which(segment_id == seg)
      rr_seg <- rr[idx]
      time_seg <- time[idx]

      implausible <- !is.finite(rr_seg) | rr_seg < min_rr_ms | rr_seg > max_rr_ms
      successive_change <- rep(FALSE, length(rr_seg))

      if (length(rr_seg) >= 2L) {
        prev <- utils::head(rr_seg, -1L)
        cur <- utils::tail(rr_seg, -1L)
        change <- abs(cur - prev) / pmax(abs(prev), 1)
        successive_change[-1L] <- is.finite(change) & change > max_successive_change_prop
      }

      artifact <- implausible | successive_change
      finite_rr <- rr_seg[is.finite(rr_seg)]
      clean_rr <- rr_seg[!artifact & is.finite(rr_seg)]

      duration_s <- if (sum(is.finite(time_seg)) >= 2L) {
        diff(range(time_seg[is.finite(time_seg)], na.rm = TRUE))
      } else if (length(finite_rr)) {
        sum(finite_rr, na.rm = TRUE) / 1000
      } else {
        NA_real_
      }

      artifact_prop <- if (length(rr_seg)) mean(artifact, na.rm = TRUE) else NA_real_

      reasons <- character()
      if (length(clean_rr) < min_beats) reasons <- c(reasons, "too_few_clean_beats")
      if (!is.finite(duration_s) || duration_s < min_duration_s) reasons <- c(reasons, "duration_too_short")
      if (is.finite(artifact_prop) && artifact_prop > max_artifact_prop) reasons <- c(reasons, "high_artifact_prop")
      if (any(implausible, na.rm = TRUE)) reasons <- c(reasons, "implausible_rr")
      if (any(successive_change, na.rm = TRUE)) reasons <- c(reasons, "large_successive_change")

      quality_ok <- length(reasons) == 0L

      k <- k + 1L
      row <- data.frame(
        group = g,
        segment_id = seg,
        segment_start_s = if (any(is.finite(time_seg))) min(time_seg, na.rm = TRUE) else NA_real_,
        segment_end_s = if (any(is.finite(time_seg))) max(time_seg, na.rm = TRUE) else NA_real_,
        duration_s = duration_s,
        n_beats = length(rr_seg),
        n_clean_beats = length(clean_rr),
        artifact_prop = artifact_prop,
        mean_rr_ms = if (length(clean_rr)) mean(clean_rr, na.rm = TRUE) else NA_real_,
        median_rr_ms = if (length(clean_rr)) stats::median(clean_rr, na.rm = TRUE) else NA_real_,
        min_rr_ms = if (length(finite_rr)) min(finite_rr, na.rm = TRUE) else NA_real_,
        max_rr_ms = if (length(finite_rr)) max(finite_rr, na.rm = TRUE) else NA_real_,
        n_implausible_rr = sum(implausible, na.rm = TRUE),
        n_large_successive_changes = sum(successive_change, na.rm = TRUE),
        quality_ok = quality_ok,
        reasons = if (length(reasons)) paste(unique(reasons), collapse = ";") else "ok",
        stringsAsFactors = FALSE
      )

      if (!is.null(group_cols) && length(group_cols)) {
        row <- cbind(z[1L, group_cols, drop = FALSE], row[setdiff(names(row), "group")])
      }

      rows[[k]] <- row
    }
  }

  .gp_c3_bind_rows(rows)
}

#' Compute SCR latency metrics from event-locked EDA
#'
#' Estimates onset latency, peak latency, peak amplitude, AUC, and half-recovery
#' latency for each event using a baseline window and response window.
#'
#' @param data Data frame containing EDA/GSR samples.
#' @param events Event table or numeric event times.
#' @param time_col Time column in `data`.
#' @param eda_col EDA/GSR column.
#' @param event_time_col Event-time column.
#' @param event_id_col Event identifier column.
#' @param group_cols Optional grouping columns used to match events to samples.
#' @param baseline_window_s Two-element baseline window relative to event.
#' @param response_window_s Two-element response window relative to event.
#' @param onset_threshold Minimum increase above baseline used for onset.
#' @param recovery_fraction Fraction of peak amplitude used for recovery time.
#'
#' @return Data frame with one row per event.
#' @export
compute_gazepoint_scr_latency <- function(data,
                                          events,
                                          time_col = NULL,
                                          eda_col = NULL,
                                          event_time_col = NULL,
                                          event_id_col = NULL,
                                          group_cols = NULL,
                                          baseline_window_s = c(-1, 0),
                                          response_window_s = c(0, 5),
                                          onset_threshold = 0.01,
                                          recovery_fraction = 0.50) {
  .gp_c3_check_df(data)

  if (is.null(time_col)) {
    time_col <- .gp_c3_time_col(data, required = TRUE)
  }

  if (is.null(eda_col)) {
    eda_col <- .gp_c3_guess_col(
      data,
      c("GSR", "EDA", "skin_conductance", "conductance", "GSR_US", "eda"),
      "EDA/GSR",
      TRUE
    )
  }

  event_table <- .gp_c3_event_table(events, event_time_col, event_id_col)

  time <- .gp_c3_time_seconds(data[[time_col]])
  eda <- suppressWarnings(as.numeric(data[[eda_col]]))

  rows <- vector("list", nrow(event_table))

  for (i in seq_len(nrow(event_table))) {
    ev <- event_table[i, , drop = FALSE]
    sample_idx <- .gp_c3_match_event_groups(data, ev, group_cols)

    rel <- time[sample_idx] - ev$event_time_s
    value <- eda[sample_idx]

    baseline_idx <- is.finite(rel) &
      rel >= baseline_window_s[1L] &
      rel < baseline_window_s[2L] &
      is.finite(value)

    response_idx <- is.finite(rel) &
      rel >= response_window_s[1L] &
      rel <= response_window_s[2L] &
      is.finite(value)

    baseline <- if (any(baseline_idx)) mean(value[baseline_idx], na.rm = TRUE) else NA_real_

    response_time <- rel[response_idx]
    response_value <- value[response_idx]

    ord <- order(response_time)
    response_time <- response_time[ord]
    response_value <- response_value[ord]

    corrected <- response_value - baseline

    if (!length(corrected) || all(!is.finite(corrected))) {
      rows[[i]] <- data.frame(
        event_id = ev$event_id,
        event_time_s = ev$event_time_s,
        baseline_mean = baseline,
        onset_latency_s = NA_real_,
        peak_latency_s = NA_real_,
        peak_amplitude = NA_real_,
        auc = NA_real_,
        recovery_latency_s = NA_real_,
        response_detected = FALSE,
        n_response_samples = length(corrected),
        stringsAsFactors = FALSE
      )
      next
    }

    peak_idx <- which.max(corrected)
    peak_amplitude <- corrected[peak_idx]
    peak_latency <- response_time[peak_idx]

    onset_hits <- which(corrected >= onset_threshold)
    onset_latency <- if (length(onset_hits)) response_time[onset_hits[1L]] else NA_real_

    recovery_latency <- NA_real_
    if (is.finite(peak_amplitude) && peak_amplitude > onset_threshold) {
      recovery_threshold <- peak_amplitude * recovery_fraction
      after_peak <- seq(from = peak_idx, to = length(corrected))

      recovery_hits <- after_peak[corrected[after_peak] <= recovery_threshold]
      if (length(recovery_hits)) {
        recovery_latency <- response_time[recovery_hits[1L]]
      }
    }

    row <- data.frame(
      event_id = ev$event_id,
      event_time_s = ev$event_time_s,
      baseline_mean = baseline,
      onset_latency_s = onset_latency,
      peak_latency_s = peak_latency,
      peak_amplitude = peak_amplitude,
      auc = .gp_c3_auc(response_time, corrected),
      recovery_latency_s = recovery_latency,
      response_detected = is.finite(peak_amplitude) && peak_amplitude >= onset_threshold,
      n_response_samples = length(corrected),
      stringsAsFactors = FALSE
    )

    extra_cols <- setdiff(names(ev), c("event_id", "event_time_s"))
    if (length(extra_cols)) {
      for (cc in extra_cols) {
        row[[cc]] <- ev[[cc]][1L]
      }
    }

    rows[[i]] <- row
  }

  .gp_c3_bind_rows(rows)
}

#' Compute a pairwise signal-lag matrix
#'
#' Computes pairwise lag/correlation summaries across synchronized numeric
#' signals. The output is useful as a compact multimodal lag screen before
#' event-locked or mixed-model analyses.
#'
#' @param data Data frame with a common time column and numeric signals.
#' @param signal_cols Numeric signal columns. If omitted, all numeric columns
#'   except `time_col` and `group_cols` are used.
#' @param time_col Time column.
#' @param group_cols Optional grouping columns.
#' @param max_lag_s Maximum lag in seconds.
#' @param lag_step_s Optional lag-step size. If omitted, the median sample
#'   interval is used.
#' @param min_overlap Minimum paired samples required per lag.
#'
#' @return Data frame with one row per group and signal pair.
#' @export
compute_gazepoint_signal_lag_matrix <- function(data,
                                                signal_cols = NULL,
                                                time_col = NULL,
                                                group_cols = NULL,
                                                max_lag_s = 2,
                                                lag_step_s = NULL,
                                                min_overlap = 10) {
  .gp_c3_check_df(data)

  if (is.null(time_col)) {
    time_col <- .gp_c3_time_col(data, required = TRUE)
  }

  if (is.null(signal_cols)) {
    is_num <- vapply(data, is.numeric, logical(1))
    signal_cols <- names(data)[is_num]
    signal_cols <- setdiff(signal_cols, unique(c(time_col, group_cols)))
  }

  signal_cols <- intersect(signal_cols, names(data))

  if (length(signal_cols) < 2L) {
    stop("At least two numeric `signal_cols` are required.", call. = FALSE)
  }

  groups <- .gp_c3_group_indices(data, group_cols)
  rows <- list()
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- data[idx, , drop = FALSE]
    time <- .gp_c3_time_seconds(z[[time_col]])

    d <- diff(sort(unique(time[is.finite(time)])))
    d <- d[is.finite(d) & d > 0]
    step <- if (!is.null(lag_step_s)) lag_step_s else if (length(d)) stats::median(d, na.rm = TRUE) else NA_real_

    if (!is.finite(step) || step <= 0) {
      next
    }

    lags <- seq(-max_lag_s, max_lag_s, by = step)

    pairs <- utils::combn(signal_cols, 2L, simplify = FALSE)

    for (pair in pairs) {
      x <- suppressWarnings(as.numeric(z[[pair[1L]]]))
      y <- suppressWarnings(as.numeric(z[[pair[2L]]]))

      ok_x <- is.finite(time) & is.finite(x)
      ok_y <- is.finite(time) & is.finite(y)

      if (sum(ok_x) < min_overlap || sum(ok_y) < min_overlap) {
        next
      }

      x_time <- time[ok_x]
      y_time <- time[ok_y]
      x_value <- x[ok_x]
      y_value <- y[ok_y]

      lag_corr <- rep(NA_real_, length(lags))
      lag_n <- rep(0L, length(lags))

      for (j in seq_along(lags)) {
        lag <- lags[j]

        y_shifted <- stats::approx(
          y_time - lag,
          y_value,
          xout = x_time,
          rule = 1,
          ties = mean
        )$y

        ok <- is.finite(x_value) & is.finite(y_shifted)

        lag_n[j] <- sum(ok)
        if (lag_n[j] >= min_overlap && stats::sd(x_value[ok], na.rm = TRUE) > 0 &&
          stats::sd(y_shifted[ok], na.rm = TRUE) > 0) {
          lag_corr[j] <- suppressWarnings(stats::cor(x_value[ok], y_shifted[ok]))
        }
      }

      best <- if (any(is.finite(lag_corr))) {
        which.max(abs(lag_corr))
      } else {
        NA_integer_
      }

      k <- k + 1L
      row <- data.frame(
        group = g,
        signal_1 = pair[1L],
        signal_2 = pair[2L],
        best_lag_s = if (is.na(best)) NA_real_ else lags[best],
        best_correlation = if (is.na(best)) NA_real_ else lag_corr[best],
        abs_best_correlation = if (is.na(best)) NA_real_ else abs(lag_corr[best]),
        n_overlap_at_best = if (is.na(best)) NA_integer_ else lag_n[best],
        max_lag_s = max_lag_s,
        lag_step_s = step,
        stringsAsFactors = FALSE
      )

      if (!is.null(group_cols) && length(group_cols)) {
        row <- cbind(z[1L, group_cols, drop = FALSE], row[setdiff(names(row), "group")])
      }

      rows[[k]] <- row
    }
  }

  .gp_c3_bind_rows(rows)
}

#' Estimate respiration rate from PPG
#'
#' Estimates an exploratory respiration rate from low-frequency modulation in a
#' PPG/BVP signal. This is a lightweight screening helper and should not be
#' interpreted as a replacement for a respiratory sensor.
#'
#' @param data Data frame or numeric PPG vector.
#' @param ppg_col PPG/BVP signal column for data-frame input.
#' @param time_col Optional time column.
#' @param sampling_rate_hz Sampling rate for vector input or when no time column
#'   is available.
#' @param respiratory_band_hz Two-element frequency band used to search for the
#'   respiration peak.
#' @param detrend If TRUE, remove a linear trend before spectral estimation.
#'
#' @return List with `summary`, `spectrum`, and `settings`.
#' @export
estimate_gazepoint_respiration_from_ppg <- function(data,
                                                    ppg_col = NULL,
                                                    time_col = NULL,
                                                    sampling_rate_hz = NULL,
                                                    respiratory_band_hz = c(0.10, 0.50),
                                                    detrend = TRUE) {
  if (is.numeric(data) && is.null(dim(data))) {
    ppg <- suppressWarnings(as.numeric(data))

    if (is.null(sampling_rate_hz)) {
      sampling_rate_hz <- 50
    }

    time <- seq_along(ppg) / sampling_rate_hz
  } else {
    .gp_c3_check_df(data)

    if (is.null(ppg_col)) {
      ppg_col <- .gp_c3_guess_col(
        data,
        c("PPG", "BVP", "HRP", "pulse", "ppg", "bvp"),
        "PPG/BVP",
        TRUE
      )
    }

    if (is.null(time_col)) {
      time_col <- .gp_c3_time_col(data, required = FALSE)
    }

    ppg <- suppressWarnings(as.numeric(data[[ppg_col]]))

    if (!is.null(time_col) && time_col %in% names(data)) {
      time <- .gp_c3_time_seconds(data[[time_col]])
    } else {
      if (is.null(sampling_rate_hz)) {
        sampling_rate_hz <- 50
      }
      time <- seq_along(ppg) / sampling_rate_hz
    }
  }

  regular <- .gp_c3_regularize_signal(time, ppg, sampling_rate_hz)
  time_reg <- regular$time
  ppg_reg <- regular$value
  fs <- regular$sampling_rate_hz

  if (length(ppg_reg) < 8L) {
    out <- list(
      summary = data.frame(
        respiration_rate_bpm = NA_real_,
        respiration_frequency_hz = NA_real_,
        peak_power = NA_real_,
        band_power = NA_real_,
        n_samples = length(ppg_reg),
        sampling_rate_hz = fs,
        stringsAsFactors = FALSE
      ),
      spectrum = data.frame(frequency_hz = numeric(), power = numeric()),
      settings = list(respiratory_band_hz = respiratory_band_hz, detrend = detrend)
    )
    return(out)
  }

  if (isTRUE(detrend)) {
    tt <- seq_along(ppg_reg)
    fit <- stats::lm(ppg_reg ~ tt)
    ppg_reg <- stats::resid(fit)
  }

  spectrum <- .gp_c3_fft_spectrum(ppg_reg, fs)

  in_band <- spectrum$frequency_hz >= respiratory_band_hz[1L] &
    spectrum$frequency_hz <= respiratory_band_hz[2L]

  if (!any(in_band) || all(!is.finite(spectrum$power[in_band]))) {
    respiration_frequency_hz <- NA_real_
    peak_power <- NA_real_
    band_power <- NA_real_
  } else {
    band_spec <- spectrum[in_band, , drop = FALSE]
    best <- which.max(band_spec$power)
    respiration_frequency_hz <- band_spec$frequency_hz[best]
    peak_power <- band_spec$power[best]
    band_power <- sum(band_spec$power, na.rm = TRUE)
  }

  list(
    summary = data.frame(
      respiration_rate_bpm = respiration_frequency_hz * 60,
      respiration_frequency_hz = respiration_frequency_hz,
      peak_power = peak_power,
      band_power = band_power,
      n_samples = length(ppg_reg),
      sampling_rate_hz = fs,
      stringsAsFactors = FALSE
    ),
    spectrum = spectrum,
    settings = list(
      respiratory_band_hz = respiratory_band_hz,
      detrend = detrend,
      interpretation = "exploratory_ppg_derived_respiration_estimate"
    )
  )
}

