
# Event-related SCR, RR outlier, and engagement-dial helpers

.gp_evt_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }

  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }

  invisible(data)
}

.gp_evt_guess_col <- function(data, candidates, label, required = TRUE) {
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

.gp_evt_time_seconds <- function(time) {
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

.gp_evt_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  missing <- setdiff(group_cols, names(data))

  if (length(missing)) {
    stop("Missing grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_evt_standardize_events <- function(events,
                                       event_time_col = NULL,
                                       event_id_col = NULL,
                                       event_group_cols = NULL) {
  if (is.numeric(events) && is.null(dim(events))) {
    out <- data.frame(
      event_id = seq_along(events),
      event_time = as.numeric(events),
      stringsAsFactors = FALSE
    )
    return(out)
  }

  if (!is.data.frame(events)) {
    stop("`events` must be a numeric vector of timestamps or a data frame.", call. = FALSE)
  }

  if (!nrow(events)) {
    stop("`events` has no rows.", call. = FALSE)
  }

  if (is.null(event_time_col)) {
    event_time_col <- .gp_evt_guess_col(
      events,
      candidates = c("event_time", "time_s", "time", "timestamp", "onset", "onset_time", "trial_onset", "stimulus_onset"),
      label = "event time",
      required = TRUE
    )
  }

  if (!event_time_col %in% names(events)) {
    stop("`event_time_col` not found in `events`.", call. = FALSE)
  }

  out <- events
  out$event_time <- suppressWarnings(as.numeric(out[[event_time_col]]))

  if (is.null(event_id_col)) {
    event_id_col <- .gp_evt_guess_col(
      events,
      candidates = c("event_id", "trial", "trial_id", "stimulus", "condition"),
      label = "event id",
      required = FALSE
    )
  }

  if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out$event_id <- out[[event_id_col]]
  } else {
    out$event_id <- seq_len(nrow(out))
  }

  keep <- c("event_id", "event_time")

  if (!is.null(event_group_cols) && length(event_group_cols)) {
    missing <- setdiff(event_group_cols, names(out))

    if (length(missing)) {
      stop("Missing event grouping columns: ", paste(missing, collapse = ", "), call. = FALSE)
    }

    keep <- unique(c(keep, event_group_cols))
  }

  out[keep]
}

.gp_evt_detect_scr_peaks <- function(time,
                                     signal,
                                     min_amplitude = 0.01,
                                     min_distance_s = 1,
                                     latency_min_s = 0,
                                     latency_max_s = Inf) {
  ok <- is.finite(time) & is.finite(signal)

  if (sum(ok) < 3L) {
    return(data.frame())
  }

  time <- time[ok]
  signal <- signal[ok]
  ord <- order(time)
  time <- time[ord]
  signal <- signal[ord]

  local <- which(
    signal[-c(1L, length(signal))] > signal[-c(length(signal) - 1L, length(signal))] &
      signal[-c(1L, 2L)] <= signal[-c(1L, length(signal))]
  ) + 1L

  if (!length(local)) {
    return(data.frame())
  }

  local <- local[time[local] >= latency_min_s & time[local] <= latency_max_s]

  if (!length(local)) {
    return(data.frame())
  }

  rows <- list()
  last_peak_time <- -Inf
  k <- 0L

  for (ii in local) {
    if (time[ii] - last_peak_time < min_distance_s) {
      next
    }

    before <- which(time < time[ii])

    if (!length(before)) {
      next
    }

    trough_i <- before[which.min(signal[before])]
    amplitude <- signal[ii] - signal[trough_i]

    if (!is.finite(amplitude) || amplitude < min_amplitude) {
      next
    }

    k <- k + 1L
    rows[[k]] <- data.frame(
      scr_peak_time = time[ii],
      scr_trough_time = time[trough_i],
      scr_amplitude = amplitude,
      scr_peak_value = signal[ii],
      scr_trough_value = signal[trough_i],
      stringsAsFactors = FALSE
    )

    last_peak_time <- time[ii]
  }

  if (!k) {
    return(data.frame())
  }

  do.call(rbind, rows)
}

.gp_evt_normalize_vec <- function(x,
                                  method = c("z", "percent_max", "range", "center", "log_z", "none"),
                                  na.rm = TRUE) {
  method <- match.arg(method)
  x <- suppressWarnings(as.numeric(x))

  if (method == "none") {
    return(x)
  }

  if (method == "log_z") {
    x2 <- log1p(pmax(x, 0))
    mu <- mean(x2, na.rm = na.rm)
    sig <- stats::sd(x2, na.rm = na.rm)

    if (!is.finite(sig) || sig == 0) {
      return(rep(0, length(x)))
    }

    return((x2 - mu) / sig)
  }

  if (method == "z") {
    mu <- mean(x, na.rm = na.rm)
    sig <- stats::sd(x, na.rm = na.rm)

    if (!is.finite(sig) || sig == 0) {
      return(rep(0, length(x)))
    }

    return((x - mu) / sig)
  }

  if (method == "center") {
    return(x - mean(x, na.rm = na.rm))
  }

  if (method == "percent_max") {
    mx <- max(x, na.rm = na.rm)

    if (!is.finite(mx) || mx == 0) {
      return(rep(0, length(x)))
    }

    return(100 * x / mx)
  }

  mn <- min(x, na.rm = na.rm)
  mx <- max(x, na.rm = na.rm)

  if (!is.finite(mx - mn) || (mx - mn) == 0) {
    return(rep(0, length(x)))
  }

  (x - mn) / (mx - mn)
}

.gp_rr_outlier_flags <- function(rr,
                                 method = c("mad", "z", "range"),
                                 z_threshold = 5,
                                 mad_threshold = 5,
                                 min_rr = 300,
                                 max_rr = 2000) {
  method <- match.arg(method)
  rr <- suppressWarnings(as.numeric(rr))

  missing <- !is.finite(rr)
  range_bad <- rr < min_rr | rr > max_rr
  range_bad[missing] <- FALSE

  if (method == "range") {
    return(missing | range_bad)
  }

  ok <- is.finite(rr) & !range_bad

  if (sum(ok) < 3L) {
    stat_bad <- rep(FALSE, length(rr))
  } else if (method == "z") {
    mu <- mean(rr[ok], na.rm = TRUE)
    sig <- stats::sd(rr[ok], na.rm = TRUE)

    if (!is.finite(sig) || sig == 0) {
      stat_bad <- rep(FALSE, length(rr))
    } else {
      stat_bad <- abs((rr - mu) / sig) > z_threshold
      stat_bad[!is.finite(stat_bad)] <- FALSE
    }
  } else {
    med <- stats::median(rr[ok], na.rm = TRUE)
    sc <- stats::mad(rr[ok], constant = 1.4826, na.rm = TRUE)

    if (!is.finite(sc) || sc == 0) {
      sc <- stats::IQR(rr[ok], na.rm = TRUE) / 1.349
    }

    if (!is.finite(sc) || sc == 0) {
      stat_bad <- rep(FALSE, length(rr))
    } else {
      stat_bad <- abs(rr - med) > mad_threshold * sc
      stat_bad[!is.finite(stat_bad)] <- FALSE
    }
  }

  missing | range_bad | stat_bad
}

#' Epoch Gazepoint SCR/EDA data around events
#'
#' Segments an EDA/GSR signal around event timestamps and returns event-level
#' SCR metrics, including SCR count, maximum amplitude, mean amplitude, AUC, and
#' baseline-corrected epoch summaries.
#'
#' @param data Data frame containing time and EDA/GSR columns.
#' @param events Numeric vector of event timestamps or a data frame with an
#'   event-time column.
#' @param pre Seconds before each event to include.
#' @param post Seconds after each event to include.
#' @param time_col Time column in `data`. If NULL, common names are detected.
#' @param signal_col EDA/GSR signal column. If NULL, common names are detected.
#' @param event_time_col Event-time column when `events` is a data frame.
#' @param event_id_col Optional event identifier column.
#' @param event_group_cols Optional event metadata columns to carry into the
#'   output.
#' @param baseline_window Baseline window relative to event time. Defaults to
#'   `c(-pre, 0)`.
#' @param response_window SCR response window relative to event time. Defaults
#'   to `c(0, post)`.
#' @param min_amplitude Minimum peak-minus-trough amplitude counted as SCR.
#' @param min_distance_s Minimum time between counted SCR peaks.
#'
#' @return Data frame with one row per event and event-level SCR metrics.
#' @export
#'
#' @examples
#' eda <- data.frame(time_s = seq(0, 10, by = .1), GSR = sin(seq(0, 10, by = .1)) / 20)
#' epoch_gazepoint_scr(eda, events = 5, pre = 1, post = 3)
epoch_gazepoint_scr <- function(data,
                                events,
                                pre,
                                post,
                                time_col = NULL,
                                signal_col = NULL,
                                event_time_col = NULL,
                                event_id_col = NULL,
                                event_group_cols = NULL,
                                baseline_window = NULL,
                                response_window = NULL,
                                min_amplitude = 0.01,
                                min_distance_s = 1) {
  .gp_evt_check_df(data)

  if (missing(events)) {
    stop("Supply `events` as timestamps or an event data frame.", call. = FALSE)
  }

  if (missing(pre) || missing(post) || !is.numeric(pre) || !is.numeric(post) || pre < 0 || post <= 0) {
    stop("`pre` must be non-negative and `post` must be positive.", call. = FALSE)
  }

  time_col <- if (is.null(time_col)) {
    .gp_evt_guess_col(
      data,
      candidates = c("time_s", "time", "TIME", "timestamp", "MSTIMER"),
      label = "time",
      required = TRUE
    )
  } else {
    time_col
  }

  signal_col <- if (is.null(signal_col)) {
    .gp_evt_guess_col(
      data,
      candidates = c("GSR", "EDA", "SCR", "eda", "gsr", "skin_conductance", "conductance"),
      label = "EDA/GSR signal",
      required = TRUE
    )
  } else {
    signal_col
  }

  if (!time_col %in% names(data)) stop("`time_col` not found in `data`.", call. = FALSE)
  if (!signal_col %in% names(data)) stop("`signal_col` not found in `data`.", call. = FALSE)

  ev <- .gp_evt_standardize_events(
    events = events,
    event_time_col = event_time_col,
    event_id_col = event_id_col,
    event_group_cols = event_group_cols
  )

  time <- .gp_evt_time_seconds(data[[time_col]])
  signal <- suppressWarnings(as.numeric(data[[signal_col]]))

  if (is.null(baseline_window)) {
    baseline_window <- c(-pre, 0)
  }

  if (is.null(response_window)) {
    response_window <- c(0, post)
  }

  rows <- vector("list", nrow(ev))

  for (i in seq_len(nrow(ev))) {
    event_time <- as.numeric(ev$event_time[i])
    rel <- time - event_time
    epoch_idx <- which(rel >= -pre & rel <= post)

    if (!length(epoch_idx)) {
      row <- data.frame(
        event_id = ev$event_id[i],
        event_time = event_time,
        n_samples = 0L,
        baseline_mean = NA_real_,
        epoch_mean = NA_real_,
        response_mean = NA_real_,
        response_auc = NA_real_,
        scr_count = 0L,
        scr_max_amplitude = NA_real_,
        scr_mean_amplitude = NA_real_,
        scr_total_amplitude = 0,
        first_scr_latency_s = NA_real_,
        stringsAsFactors = FALSE
      )
    } else {
      rel_epoch <- rel[epoch_idx]
      sig_epoch <- signal[epoch_idx]

      base_idx <- rel_epoch >= baseline_window[1L] & rel_epoch <= baseline_window[2L]
      resp_idx <- rel_epoch >= response_window[1L] & rel_epoch <= response_window[2L]

      baseline_mean <- if (any(base_idx, na.rm = TRUE)) {
        mean(sig_epoch[base_idx], na.rm = TRUE)
      } else {
        NA_real_
      }

      sig_bc <- sig_epoch - baseline_mean

      peaks <- .gp_evt_detect_scr_peaks(
        time = rel_epoch[resp_idx],
        signal = sig_bc[resp_idx],
        min_amplitude = min_amplitude,
        min_distance_s = min_distance_s,
        latency_min_s = response_window[1L],
        latency_max_s = response_window[2L]
      )

      if (sum(resp_idx, na.rm = TRUE) >= 2L) {
        t_resp <- rel_epoch[resp_idx]
        y_resp <- sig_bc[resp_idx]
        ord <- order(t_resp)
        response_auc <- sum(diff(t_resp[ord]) * (utils::head(y_resp[ord], -1L) + utils::tail(y_resp[ord], -1L)) / 2, na.rm = TRUE)
      } else {
        response_auc <- NA_real_
      }

      row <- data.frame(
        event_id = ev$event_id[i],
        event_time = event_time,
        n_samples = length(epoch_idx),
        baseline_mean = baseline_mean,
        epoch_mean = mean(sig_bc, na.rm = TRUE),
        response_mean = mean(sig_bc[resp_idx], na.rm = TRUE),
        response_auc = response_auc,
        scr_count = nrow(peaks),
        scr_max_amplitude = if (nrow(peaks)) max(peaks$scr_amplitude, na.rm = TRUE) else NA_real_,
        scr_mean_amplitude = if (nrow(peaks)) mean(peaks$scr_amplitude, na.rm = TRUE) else NA_real_,
        scr_total_amplitude = if (nrow(peaks)) sum(peaks$scr_amplitude, na.rm = TRUE) else 0,
        first_scr_latency_s = if (nrow(peaks)) min(peaks$scr_peak_time, na.rm = TRUE) else NA_real_,
        stringsAsFactors = FALSE
      )
    }

    if (!is.null(event_group_cols) && length(event_group_cols)) {
      row <- cbind(ev[i, event_group_cols, drop = FALSE], row)
    }

    rows[[i]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL

  attr(out, "time_col") <- time_col
  attr(out, "signal_col") <- signal_col
  attr(out, "pre") <- pre
  attr(out, "post") <- post
  attr(out, "baseline_window") <- baseline_window
  attr(out, "response_window") <- response_window

  out
}

#' Normalize Gazepoint SCR amplitudes
#'
#' Normalizes SCR amplitudes using z-scores, percent of maximum, min-max range,
#' centered scores, log-z scores, or no transformation.
#'
#' @param amplitudes Numeric vector or data frame.
#' @param method Normalization method: `"z"`, `"percent_max"`, `"range"`,
#'   `"center"`, `"log_z"`, or `"none"`.
#' @param amplitude_col Column to normalize when `amplitudes` is a data frame.
#' @param group_cols Optional grouping columns for subject-specific
#'   normalization.
#' @param output_col Name of normalized column for data-frame input.
#' @param na.rm If TRUE, ignore missing values when computing normalization
#'   constants.
#'
#' @return Numeric vector for vector input, or data frame for data-frame input.
#' @export
#'
#' @examples
#' normalize_gazepoint_scr(c(0.1, 0.2, 0.3), method = "percent_max")
normalize_gazepoint_scr <- function(amplitudes,
                                    method = c("z", "percent_max", "range", "center", "log_z", "none"),
                                    amplitude_col = NULL,
                                    group_cols = NULL,
                                    output_col = "scr_amplitude_normalized",
                                    na.rm = TRUE) {
  method <- match.arg(method)

  if (is.numeric(amplitudes) && is.null(dim(amplitudes))) {
    return(.gp_evt_normalize_vec(amplitudes, method = method, na.rm = na.rm))
  }

  if (!is.data.frame(amplitudes)) {
    stop("`amplitudes` must be a numeric vector or data frame.", call. = FALSE)
  }

  if (is.null(amplitude_col)) {
    amplitude_col <- .gp_evt_guess_col(
      amplitudes,
      candidates = c("scr_amplitude", "amplitude", "SCR", "SCR_Amplitude", "response_amplitude"),
      label = "SCR amplitude",
      required = TRUE
    )
  }

  if (!amplitude_col %in% names(amplitudes)) {
    stop("`amplitude_col` not found in `amplitudes`.", call. = FALSE)
  }

  out <- amplitudes
  out[[output_col]] <- NA_real_

  groups <- .gp_evt_group_indices(out, group_cols = group_cols)

  for (idx in groups) {
    out[[output_col]][idx] <- .gp_evt_normalize_vec(
      out[[amplitude_col]][idx],
      method = method,
      na.rm = na.rm
    )
  }

  attr(out, "normalization_method") <- method
  attr(out, "amplitude_col") <- amplitude_col

  out
}

#' Flag outlying Gazepoint RR/IBI intervals
#'
#' Flags implausible RR intervals using absolute physiological limits and either
#' robust MAD-based or z-score-based deviation rules.
#'
#' @param rr_intervals Numeric RR/IBI vector, usually in milliseconds.
#' @param method `"mad"`, `"z"`, or `"range"`.
#' @param z_threshold Z-score threshold when `method = "z"`.
#' @param mad_threshold Robust MAD threshold when `method = "mad"`.
#' @param min_rr Minimum plausible RR interval in ms.
#' @param max_rr Maximum plausible RR interval in ms.
#' @param return `"flags"`, `"filtered"`, or `"data"`.
#'
#' @return Logical vector, filtered RR vector with outliers set to NA, or a data
#'   frame with reason columns.
#' @export
#'
#' @examples
#' flag_gazepoint_rr_outliers(c(800, 810, 3000, 790))
flag_gazepoint_rr_outliers <- function(rr_intervals,
                                       method = c("mad", "z", "range"),
                                       z_threshold = 5,
                                       mad_threshold = 5,
                                       min_rr = 300,
                                       max_rr = 2000,
                                       return = c("flags", "filtered", "data")) {
  method <- match.arg(method)
  return <- match.arg(return)

  rr <- suppressWarnings(as.numeric(rr_intervals))

  flags <- .gp_rr_outlier_flags(
    rr,
    method = method,
    z_threshold = z_threshold,
    mad_threshold = mad_threshold,
    min_rr = min_rr,
    max_rr = max_rr
  )

  if (return == "flags") {
    return(flags)
  }

  filtered <- rr
  filtered[flags] <- NA_real_

  if (return == "filtered") {
    return(filtered)
  }

  range_bad <- rr < min_rr | rr > max_rr
  range_bad[!is.finite(rr)] <- FALSE

  data.frame(
    index = seq_along(rr),
    rr_interval = rr,
    rr_filtered = filtered,
    is_missing = !is.finite(rr),
    is_range_outlier = range_bad,
    is_outlier = flags,
    method = method,
    stringsAsFactors = FALSE
  )
}

#' Compute engagement-dial summary indices
#'
#' Summarizes a continuous engagement-dial signal, typically scaled from 0 to
#' 100, into interpretable behavioral indices such as mean engagement, percent
#' time above threshold, volatility, and area under the curve.
#'
#' @param dial Numeric engagement-dial values.
#' @param time Optional time vector.
#' @param threshold Engagement threshold.
#' @param group Optional grouping vector for grouped summaries.
#' @param return `"data"` for a one-row data frame per group, or `"scalar"` for
#'   percent time above threshold.
#'
#' @return Data frame of engagement metrics or a scalar.
#' @export
#'
#' @examples
#' compute_gazepoint_engagement_index(c(20, 60, 80), time = 1:3)
compute_gazepoint_engagement_index <- function(dial,
                                               time = NULL,
                                               threshold = 50,
                                               group = NULL,
                                               return = c("data", "scalar")) {
  return <- match.arg(return)

  dial <- suppressWarnings(as.numeric(dial))

  if (is.null(time)) {
    time <- seq_along(dial)
  } else {
    time <- .gp_evt_time_seconds(time)
  }

  if (length(time) != length(dial)) {
    stop("`time` must have the same length as `dial`.", call. = FALSE)
  }

  if (is.null(group)) {
    group <- rep("all", length(dial))
  }

  if (length(group) != length(dial)) {
    stop("`group` must have the same length as `dial`.", call. = FALSE)
  }

  groups <- split(seq_along(dial), group, drop = TRUE)
  rows <- vector("list", length(groups))
  k <- 0L

  for (gname in names(groups)) {
    idx <- groups[[gname]]
    x <- dial[idx]
    tt <- time[idx]
    ok <- is.finite(x) & is.finite(tt)

    if (!any(ok)) {
      k <- k + 1L
      rows[[k]] <- data.frame(
        group = gname,
        n_samples = length(idx),
        n_valid = 0L,
        duration_s = NA_real_,
        mean_engagement = NA_real_,
        median_engagement = NA_real_,
        sd_engagement = NA_real_,
        min_engagement = NA_real_,
        max_engagement = NA_real_,
        percent_time_above_threshold = NA_real_,
        volatility = NA_real_,
        auc_engagement = NA_real_,
        stringsAsFactors = FALSE
      )
      next
    }

    x <- x[ok]
    tt <- tt[ok]
    ord <- order(tt)
    x <- x[ord]
    tt <- tt[ord]

    duration_s <- if (length(tt) >= 2L) max(tt) - min(tt) else 0

    if (length(tt) >= 2L) {
      dt <- diff(tt)
      x_mid <- utils::head(x, -1L)
      valid_dt <- is.finite(dt) & dt >= 0
      total_dt <- sum(dt[valid_dt], na.rm = TRUE)

      if (total_dt > 0) {
        percent_above <- 100 * sum(dt[valid_dt & x_mid > threshold], na.rm = TRUE) / total_dt
        auc <- sum(dt[valid_dt] * (utils::head(x, -1L)[valid_dt] + utils::tail(x, -1L)[valid_dt]) / 2, na.rm = TRUE)
        volatility <- mean(abs(diff(x))[valid_dt], na.rm = TRUE)
      } else {
        percent_above <- 100 * mean(x > threshold, na.rm = TRUE)
        auc <- NA_real_
        volatility <- stats::sd(x, na.rm = TRUE)
      }
    } else {
      percent_above <- 100 * mean(x > threshold, na.rm = TRUE)
      auc <- 0
      volatility <- 0
    }

    k <- k + 1L
    rows[[k]] <- data.frame(
      group = gname,
      n_samples = length(idx),
      n_valid = length(x),
      duration_s = duration_s,
      mean_engagement = mean(x, na.rm = TRUE),
      median_engagement = stats::median(x, na.rm = TRUE),
      sd_engagement = stats::sd(x, na.rm = TRUE),
      min_engagement = min(x, na.rm = TRUE),
      max_engagement = max(x, na.rm = TRUE),
      percent_time_above_threshold = percent_above,
      volatility = volatility,
      auc_engagement = auc,
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  attr(out, "threshold") <- threshold

  if (return == "scalar") {
    if (nrow(out) != 1L) {
      stop("`return = 'scalar'` is only available when a single group is used.", call. = FALSE)
    }

    return(out$percent_time_above_threshold)
  }

  out
}

