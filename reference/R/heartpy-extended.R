
# Extended HeartPy-style Gazepoint pulse/PPG helpers

.gp_ppg_safe_sd <- function(x) {
  out <- stats::sd(x, na.rm = TRUE)
  if (!is.finite(out) || out <= 0) NA_real_ else out
}

.gp_ppg_scale_vector <- function(x, method = "zscore", range = c(0, 1)) {
  method <- match.arg(method, c("zscore", "minmax", "robust", "center", "none"))
  x <- .gp_as_num(x)

  if (method == "none") return(x)

  if (method == "center") {
    return(x - mean(x, na.rm = TRUE))
  }

  if (method == "zscore") {
    s <- stats::sd(x, na.rm = TRUE)
    if (!is.finite(s) || s <= 0) return(x * NA_real_)
    return((x - mean(x, na.rm = TRUE)) / s)
  }

  if (method == "robust") {
    med <- stats::median(x, na.rm = TRUE)
    sc <- stats::mad(x, constant = 1.4826, na.rm = TRUE)
    if (!is.finite(sc) || sc <= 0) return(x * NA_real_)
    return((x - med) / sc)
  }

  lo <- min(x, na.rm = TRUE)
  hi <- max(x, na.rm = TRUE)
  if (!is.finite(lo) || !is.finite(hi) || hi <= lo) return(x * NA_real_)

  range[1] + ((x - lo) / (hi - lo)) * diff(range)
}

.gp_ppg_rr_from_peaks <- function(peaks, group_col = "group") {
  if (!is.data.frame(peaks) || !nrow(peaks)) {
    return(data.frame())
  }

  if (!"peak_time_s" %in% names(peaks)) {
    stop("`peaks` must contain `peak_time_s`.", call. = FALSE)
  }

  if (!"accepted" %in% names(peaks)) peaks$accepted <- TRUE
  if (!group_col %in% names(peaks)) peaks[[group_col]] <- "all"

  peaks <- peaks[peaks$accepted %in% TRUE & is.finite(peaks$peak_time_s), , drop = FALSE]
  if (!nrow(peaks)) return(data.frame())

  groups <- split(peaks, peaks[[group_col]])

  out <- lapply(names(groups), function(g) {
    d <- groups[[g]]
    d <- d[order(d$peak_time_s), , drop = FALSE]
    if (nrow(d) < 2L) return(NULL)

    data.frame(
      group = g,
      interval_index = seq_len(nrow(d) - 1L),
      peak_time_s = d$peak_time_s[-1L],
      rr_ms = diff(d$peak_time_s) * 1000,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)

  if (is.null(out)) {
    data.frame()
  } else {
    row.names(out) <- NULL
    out
  }
}

.gp_ppg_resample_rr <- function(rr_ms, rr_time_s = NULL, resample_hz = 4) {
  rr_ms <- .gp_as_num(rr_ms)
  ok <- is.finite(rr_ms) & rr_ms > 0
  rr_ms <- rr_ms[ok]

  if (!length(rr_ms)) {
    return(list(time = numeric(), y = numeric()))
  }

  if (is.null(rr_time_s)) {
    rr_time_s <- cumsum(rr_ms) / 1000
  } else {
    rr_time_s <- .gp_as_num(rr_time_s)[ok]
  }

  ok2 <- is.finite(rr_time_s)
  rr_time_s <- rr_time_s[ok2]
  rr_ms <- rr_ms[ok2]

  if (length(rr_ms) < 4L || diff(range(rr_time_s)) <= 0) {
    return(list(time = numeric(), y = numeric()))
  }

  grid <- seq(min(rr_time_s), max(rr_time_s), by = 1 / resample_hz)

  if (length(grid) < 4L) {
    return(list(time = numeric(), y = numeric()))
  }

  y <- stats::approx(rr_time_s, rr_ms, xout = grid, rule = 2)$y
  y <- y - mean(y, na.rm = TRUE)

  list(time = grid, y = y)
}

.gp_ppg_fft_psd <- function(y, fs) {
  y <- .gp_as_num(y)
  y <- y[is.finite(y)]
  n <- length(y)

  if (n < 4L) {
    return(data.frame(frequency_hz = numeric(), psd = numeric()))
  }

  y <- y - mean(y, na.rm = TRUE)
  fy <- stats::fft(y)
  psd <- (Mod(fy)^2) / (n * fs)
  freq <- (seq_len(n) - 1L) * fs / n
  keep <- seq_len(floor(n / 2L))

  data.frame(
    frequency_hz = freq[keep],
    psd = psd[keep]
  )
}

.gp_ppg_periodogram_psd <- function(y, fs) {
  .gp_ppg_fft_psd(y, fs)
}

.gp_ppg_welch_psd <- function(y, fs, window_seconds = 64, overlap = 0.5) {
  y <- .gp_as_num(y)
  y <- y[is.finite(y)]
  n <- length(y)

  if (n < 8L) {
    return(data.frame(frequency_hz = numeric(), psd = numeric()))
  }

  window_n <- min(n, max(8L, round(window_seconds * fs)))
  step <- max(1L, round(window_n * (1 - overlap)))

  starts <- seq(1L, n - window_n + 1L, by = step)
  if (!length(starts)) starts <- 1L

  spectra <- lapply(starts, function(s) {
    idx <- s:(s + window_n - 1L)
    segment <- y[idx]
    taper <- 0.5 - 0.5 * cos(2 * pi * (seq_along(segment) - 1) / (length(segment) - 1))
    .gp_ppg_fft_psd(segment * taper, fs)
  })

  if (!length(spectra)) {
    return(data.frame(frequency_hz = numeric(), psd = numeric()))
  }

  freq <- spectra[[1]]$frequency_hz

  psd_mat <- vapply(spectra, function(z) {
    stats::approx(z$frequency_hz, z$psd, xout = freq, rule = 2)$y
  }, numeric(length(freq)))

  data.frame(
    frequency_hz = freq,
    psd = rowMeans(psd_mat, na.rm = TRUE)
  )
}

.gp_ppg_segment_starts <- function(time_s, window_seconds, overlap = 0) {
  time_s <- .gp_as_num(time_s)
  time_s <- time_s[is.finite(time_s)]

  if (!length(time_s)) return(numeric())

  start_min <- min(time_s)
  start_max <- max(time_s) - window_seconds

  if (start_max < start_min) return(start_min)

  step <- window_seconds * (1 - overlap)

  if (!is.finite(step) || step <= 0) {
    stop("`overlap` must be smaller than 1.", call. = FALSE)
  }

  seq(start_min, start_max, by = step)
}

#' Estimate sampling rate from a millisecond timer
#'
#' @param mstimer Numeric millisecond timer.
#' @param robust If TRUE, use the median interval.
#' @return Estimated sampling-rate information.
#' @export
estimate_gazepoint_samplerate_mstimer <- function(mstimer, robust = TRUE) {
  mstimer <- .gp_as_num(mstimer)
  mstimer <- mstimer[is.finite(mstimer)]

  if (length(mstimer) < 2L) {
    return(list(
      sampling_rate_hz = NA_real_,
      interval_ms = NA_real_,
      n_intervals = 0L
    ))
  }

  dt <- diff(sort(unique(mstimer)))
  dt <- dt[is.finite(dt) & dt > 0]

  if (!length(dt)) {
    return(list(
      sampling_rate_hz = NA_real_,
      interval_ms = NA_real_,
      n_intervals = 0L
    ))
  }

  interval_ms <- if (isTRUE(robust)) stats::median(dt) else mean(dt)

  list(
    sampling_rate_hz = 1000 / interval_ms,
    interval_ms = interval_ms,
    n_intervals = length(dt),
    interval_iqr_ms = stats::IQR(dt, na.rm = TRUE)
  )
}

#' Estimate sampling rate from datetime stamps
#'
#' @param datetime POSIXct, POSIXlt, Date, or character timestamps.
#' @param format Optional datetime format for character input.
#' @param tz Time zone used when parsing character input.
#' @param robust If TRUE, use the median interval.
#' @return Estimated sampling-rate information.
#' @export
estimate_gazepoint_samplerate_datetime <- function(datetime, format = NULL, tz = "UTC", robust = TRUE) {
  if (inherits(datetime, c("POSIXct", "POSIXlt"))) {
    time <- as.POSIXct(datetime, tz = tz)
  } else if (inherits(datetime, "Date")) {
    time <- as.POSIXct(datetime, tz = tz)
  } else {
    time <- as.POSIXct(datetime, format = format, tz = tz)
  }

  seconds <- as.numeric(time)
  seconds <- seconds[is.finite(seconds)]

  if (length(seconds) < 2L) {
    return(list(
      sampling_rate_hz = NA_real_,
      interval_seconds = NA_real_,
      n_intervals = 0L
    ))
  }

  dt <- diff(sort(unique(seconds)))
  dt <- dt[is.finite(dt) & dt > 0]

  if (!length(dt)) {
    return(list(
      sampling_rate_hz = NA_real_,
      interval_seconds = NA_real_,
      n_intervals = 0L
    ))
  }

  interval_seconds <- if (isTRUE(robust)) stats::median(dt) else mean(dt)

  list(
    sampling_rate_hz = 1 / interval_seconds,
    interval_seconds = interval_seconds,
    n_intervals = length(dt),
    interval_iqr_seconds = stats::IQR(dt, na.rm = TRUE)
  )
}

#' Scale a Gazepoint pulse/PPG signal
#'
#' @param x Numeric signal.
#' @param method Scaling method: zscore, minmax, robust, center, or none.
#' @param range Output range for minmax scaling.
#' @return Scaled numeric vector.
#' @export
scale_gazepoint_ppg_signal <- function(x, method = c("zscore", "minmax", "robust", "center", "none"), range = c(0, 1)) {
  method <- match.arg(method)
  .gp_ppg_scale_vector(x, method = method, range = range)
}

#' Scale Gazepoint pulse/PPG signals within sections
#'
#' @param data Data frame or numeric signal.
#' @param signal_col Signal column when data is a data frame.
#' @param section_cols Optional section/grouping columns.
#' @param method Scaling method.
#' @param output_col Name of the scaled output column.
#' @param range Output range for minmax scaling.
#' @return Data frame with an added scaled column, or a scaled vector for numeric input.
#' @export
scale_gazepoint_ppg_sections <- function(data,
                                         signal_col = NULL,
                                         section_cols = NULL,
                                         method = c("zscore", "minmax", "robust", "center", "none"),
                                         output_col = "ppg_scaled",
                                         range = c(0, 1)) {
  method <- match.arg(method)

  if (is.numeric(data) && is.null(dim(data))) {
    return(.gp_ppg_scale_vector(data, method = method, range = range))
  }

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame or numeric vector.", call. = FALSE)
  }

  if (is.null(signal_col)) {
    signal_col <- .gp_pick_col(
      data,
      c("PULSE", "PPG", "HRP", "PULSE_SIGNAL", "heart_signal", "biometric_pulse"),
      "pulse/PPG signal"
    )
  }

  if (!signal_col %in% names(data)) {
    stop("`signal_col` not found.", call. = FALSE)
  }

  out <- data
  out[[output_col]] <- NA_real_

  if (is.null(section_cols) || !length(section_cols)) {
    out[[output_col]] <- .gp_ppg_scale_vector(out[[signal_col]], method = method, range = range)
    return(out)
  }

  missing <- setdiff(section_cols, names(out))
  if (length(missing)) {
    stop("Missing section columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  idx_list <- split(seq_len(nrow(out)), interaction(out[section_cols], drop = TRUE, sep = " | "))

  for (idx in idx_list) {
    out[[output_col]][idx] <- .gp_ppg_scale_vector(out[[signal_col]][idx], method = method, range = range)
  }

  out
}

#' Flip a Gazepoint pulse/PPG signal
#'
#' @param x Numeric signal.
#' @param method Flip method: negative or max_minus.
#' @return Flipped numeric signal.
#' @export
flip_gazepoint_ppg_signal <- function(x, method = c("negative", "max_minus")) {
  method <- match.arg(method)
  x <- .gp_as_num(x)

  if (method == "negative") {
    return(-x)
  }

  max(x, na.rm = TRUE) - x
}

#' Remove baseline wander from Gazepoint pulse/PPG data
#'
#' @param x Numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param method Baseline method: median or mean.
#' @param window_seconds Baseline window length.
#' @return Baseline-corrected numeric signal.
#' @export
remove_gazepoint_ppg_baseline_wander <- function(x,
                                                 sampling_rate_hz,
                                                 method = c("median", "mean"),
                                                 window_seconds = 2) {
  method <- match.arg(method)
  x <- .gp_interpolate_na(x)

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Invalid sampling rate.", call. = FALSE)
  }

  k <- max(3L, round(window_seconds * sampling_rate_hz))

  if (method == "median") {
    baseline <- .gp_running_median(x, k)
  } else {
    baseline <- .gp_fill_edges(.gp_running_mean(x, k), mean(x, na.rm = TRUE))
  }

  x - baseline
}

#' Smooth a Gazepoint pulse/PPG signal
#'
#' @param x Numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param method Smoothing method: mean or median.
#' @param window_seconds Smoothing window length.
#' @return Smoothed numeric signal.
#' @export
smooth_gazepoint_ppg_signal <- function(x,
                                        sampling_rate_hz,
                                        method = c("mean", "median"),
                                        window_seconds = 0.10) {
  method <- match.arg(method)
  x <- .gp_interpolate_na(x)

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Invalid sampling rate.", call. = FALSE)
  }

  k <- max(3L, round(window_seconds * sampling_rate_hz))

  if (method == "median") {
    .gp_running_median(x, k)
  } else {
    .gp_fill_edges(.gp_running_mean(x, k), mean(x, na.rm = TRUE))
  }
}

#' Apply generic filtering to Gazepoint pulse/PPG data
#'
#' @param x Numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param type Filter type: lowpass, highpass, bandpass, or notch.
#' @param low_hz Low cutoff for highpass, bandpass, or notch.
#' @param high_hz High cutoff for lowpass, bandpass, or notch.
#' @param passes Repeated filter passes.
#' @return Filtered numeric signal.
#' @export
filter_gazepoint_ppg_signal <- function(x,
                                        sampling_rate_hz,
                                        type = c("lowpass", "highpass", "bandpass", "notch"),
                                        low_hz = NULL,
                                        high_hz = NULL,
                                        passes = 1L) {
  type <- match.arg(type)
  x <- .gp_interpolate_na(x)

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Invalid sampling rate.", call. = FALSE)
  }

  if (type == "lowpass") {
    cutoff <- if (is.null(high_hz)) 5 else high_hz
    return(filter_gazepoint_ppg_butterworth(
      x,
      cutoff_hz = cutoff,
      sampling_rate_hz = sampling_rate_hz,
      passes = passes
    ))
  }

  if (type == "highpass") {
    cutoff <- if (is.null(low_hz)) 0.5 else low_hz
    low <- filter_gazepoint_ppg_butterworth(
      x,
      cutoff_hz = cutoff,
      sampling_rate_hz = sampling_rate_hz,
      passes = passes
    )
    return(x - low)
  }

  if (type == "bandpass") {
    if (is.null(low_hz) || is.null(high_hz)) {
      stop("Supply both `low_hz` and `high_hz` for bandpass filtering.", call. = FALSE)
    }

    hp <- filter_gazepoint_ppg_signal(
      x,
      sampling_rate_hz,
      type = "highpass",
      low_hz = low_hz,
      passes = passes
    )

    return(filter_gazepoint_ppg_signal(
      hp,
      sampling_rate_hz,
      type = "lowpass",
      high_hz = high_hz,
      passes = passes
    ))
  }

  if (is.null(low_hz) || is.null(high_hz)) {
    stop("Supply both `low_hz` and `high_hz` for notch filtering.", call. = FALSE)
  }

  n <- length(x)
  fy <- stats::fft(x)
  freq <- (seq_len(n) - 1L) * sampling_rate_hz / n
  freq_alt <- ifelse(freq > sampling_rate_hz / 2, sampling_rate_hz - freq, freq)
  remove <- freq_alt >= low_hz & freq_alt <= high_hz
  fy[remove] <- 0

  Re(stats::fft(fy, inverse = TRUE) / n)
}

#' Clean RR or IBI intervals using HeartPy-style methods
#'
#' @param rr_ms Numeric RR/IBI intervals in milliseconds, or a peak table.
#' @param method Cleaning method: quotient, iqr, modified_z, zscore, or none.
#' @param group_col Group column when rr_ms is a peak table.
#' @param quotient_threshold Maximum allowed ratio between adjacent intervals.
#' @param iqr_multiplier IQR multiplier for IQR cleaning.
#' @param z_threshold Z-score threshold.
#' @return Cleaned interval table, or cleaned peak table when a peak table is supplied.
#' @export
clean_gazepoint_rr_intervals <- function(rr_ms,
                                         method = c("quotient", "iqr", "modified_z", "zscore", "none"),
                                         group_col = "group",
                                         quotient_threshold = 0.20,
                                         iqr_multiplier = 1.5,
                                         z_threshold = 3.5) {
  method <- match.arg(method)

  input_is_peaks <- is.data.frame(rr_ms) && "peak_time_s" %in% names(rr_ms)

  if (input_is_peaks) {
    peaks <- rr_ms

    if (!"accepted" %in% names(peaks)) peaks$accepted <- TRUE
    if (!group_col %in% names(peaks)) peaks[[group_col]] <- "all"

    peaks <- peaks[order(peaks[[group_col]], peaks$peak_time_s), , drop = FALSE]
    peaks$rr_ms <- NA_real_
    peaks$rr_clean <- TRUE
    peaks$rr_clean_reason <- "accepted"

    groups <- split(seq_len(nrow(peaks)), peaks[[group_col]])

    for (idx in groups) {
      if (length(idx) < 3L) next

      rr <- c(NA_real_, diff(peaks$peak_time_s[idx]) * 1000)

      clean <- clean_gazepoint_rr_intervals(
        rr[-1L],
        method = method,
        quotient_threshold = quotient_threshold,
        iqr_multiplier = iqr_multiplier,
        z_threshold = z_threshold
      )

      peaks$rr_ms[idx] <- rr
      peaks$rr_clean[idx[-1L]] <- clean$accepted
      peaks$rr_clean_reason[idx[-1L]] <- clean$reason
      peaks$accepted[idx[-1L]] <- peaks$accepted[idx[-1L]] & clean$accepted
    }

    row.names(peaks) <- NULL
    return(peaks)
  }

  rr <- .gp_as_num(rr_ms)

  out <- data.frame(
    interval_index = seq_along(rr),
    rr_ms = rr,
    accepted = is.finite(rr) & rr > 0,
    reason = ifelse(is.finite(rr) & rr > 0, "accepted", "non_finite_or_non_positive")
  )

  if (method == "none" || !any(out$accepted)) {
    return(out)
  }

  valid <- out$accepted
  rrv <- rr[valid]
  accepted_valid <- rep(TRUE, length(rrv))
  reason_valid <- rep("accepted", length(rrv))

  if (method == "quotient") {
    if (length(rrv) >= 2L) {
      ratio <- c(1, pmin(rrv[-1] / rrv[-length(rrv)], rrv[-length(rrv)] / rrv[-1]))
      bad <- ratio < (1 - quotient_threshold)
      accepted_valid[bad] <- FALSE
      reason_valid[bad] <- "quotient_threshold"
    }
  }

  if (method == "iqr") {
    q <- stats::quantile(rrv, probs = c(.25, .75), na.rm = TRUE, names = FALSE)
    iqr <- diff(q)
    lo <- q[1] - iqr_multiplier * iqr
    hi <- q[2] + iqr_multiplier * iqr
    bad <- rrv < lo | rrv > hi
    accepted_valid[bad] <- FALSE
    reason_valid[bad] <- "iqr_threshold"
  }

  if (method == "modified_z") {
    med <- stats::median(rrv, na.rm = TRUE)
    madv <- stats::mad(rrv, constant = 1, na.rm = TRUE)

    if (is.finite(madv) && madv > 0) {
      mz <- 0.6745 * (rrv - med) / madv
      bad <- abs(mz) > z_threshold
      accepted_valid[bad] <- FALSE
      reason_valid[bad] <- "modified_z_threshold"
    }
  }

  if (method == "zscore") {
    s <- stats::sd(rrv, na.rm = TRUE)

    if (is.finite(s) && s > 0) {
      z <- (rrv - mean(rrv, na.rm = TRUE)) / s
      bad <- abs(z) > z_threshold
      accepted_valid[bad] <- FALSE
      reason_valid[bad] <- "zscore_threshold"
    }
  }

  out$accepted[valid] <- accepted_valid
  out$reason[valid] <- reason_valid
  out
}

#' Compute Gazepoint pulse/PPG frequency-domain measures
#'
#' @param peaks Optional peak table.
#' @param rr_ms Optional RR/IBI intervals in milliseconds.
#' @param rr_time_s Optional interval timestamps.
#' @param group_col Group column when peaks are supplied.
#' @param method PSD method: fft, periodogram, or welch.
#' @param resample_hz RR interpolation frequency.
#' @param bands Named list of frequency bands.
#' @param welch_window_seconds Welch window length.
#' @param welch_overlap Welch overlap proportion.
#' @return Data frame of frequency-domain measures.
#' @export
compute_gazepoint_ppg_frequency_measures <- function(peaks = NULL,
                                                     rr_ms = NULL,
                                                     rr_time_s = NULL,
                                                     group_col = "group",
                                                     method = c("welch", "fft", "periodogram"),
                                                     resample_hz = 4,
                                                     bands = list(
                                                       lf = c(0.05, 0.15),
                                                       hf = c(0.15, 0.50)
                                                     ),
                                                     welch_window_seconds = 64,
                                                     welch_overlap = 0.5) {
  method <- match.arg(method)

  one_group <- function(rr, time = NULL, group = "all") {
    rr <- .gp_as_num(rr)
    ok <- is.finite(rr) & rr > 0
    rr <- rr[ok]

    if (!is.null(time)) {
      time <- .gp_as_num(time)[ok]
    }

    rs <- .gp_ppg_resample_rr(rr, rr_time_s = time, resample_hz = resample_hz)

    if (!length(rs$y)) {
      return(data.frame(
        group = group,
        method = method,
        lf = NA_real_,
        hf = NA_real_,
        hf_lf = NA_real_,
        total_power = NA_real_,
        peak_frequency_hz = NA_real_,
        breathing_rate_hz = NA_real_
      ))
    }

    psd <- switch(
      method,
      fft = .gp_ppg_fft_psd(rs$y, resample_hz),
      periodogram = .gp_ppg_periodogram_psd(rs$y, resample_hz),
      welch = .gp_ppg_welch_psd(
        rs$y,
        resample_hz,
        window_seconds = welch_window_seconds,
        overlap = welch_overlap
      )
    )

    band_power <- vapply(bands, function(b) {
      .gp_band_power(psd$frequency_hz, psd$psd, b[1], b[2])
    }, numeric(1))

    lf <- if ("lf" %in% names(band_power)) band_power[["lf"]] else NA_real_
    hf <- if ("hf" %in% names(band_power)) band_power[["hf"]] else NA_real_

    breathing <- estimate_gazepoint_breathing_rate_from_ibi(
      rr_ms = rr,
      rr_time_s = time,
      resample_hz = resample_hz
    )

    data.frame(
      group = group,
      method = method,
      lf = lf,
      hf = hf,
      hf_lf = if (is.finite(lf) && lf > 0) hf / lf else NA_real_,
      total_power = sum(psd$psd[is.finite(psd$psd)], na.rm = TRUE),
      peak_frequency_hz = if (nrow(psd) && any(is.finite(psd$psd))) {
        psd$frequency_hz[which.max(psd$psd)]
      } else {
        NA_real_
      },
      breathing_rate_hz = breathing$breathing_rate_hz
    )
  }

  if (!is.null(peaks)) {
    rr_tbl <- .gp_ppg_rr_from_peaks(peaks, group_col = group_col)
    if (!nrow(rr_tbl)) return(data.frame())

    groups <- split(rr_tbl, rr_tbl$group)

    out <- lapply(names(groups), function(g) {
      one_group(groups[[g]]$rr_ms, groups[[g]]$peak_time_s, g)
    })

    out <- do.call(rbind, out)
    row.names(out) <- NULL
    return(out)
  }

  if (is.null(rr_ms)) {
    stop("Supply either `peaks` or `rr_ms`.", call. = FALSE)
  }

  one_group(rr_ms, rr_time_s, "all")
}

#' Run a full HeartPy-style Gazepoint pulse/PPG process
#'
#' @param data Data frame or numeric pulse/PPG signal.
#' @param signal_col Signal column when data is a data frame.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param clean_rr Whether to clean RR intervals after peak rejection.
#' @param clean_rr_method RR cleaning method.
#' @param frequency_method Frequency-domain method.
#' @param output_dir Optional output directory. If NULL, no files are written.
#' @param ... Additional arguments passed to detect_gazepoint_ppg_peaks().
#' @return A list with detection, peaks, measures, frequency, quality, report, and settings.
#' @export
process_gazepoint_ppg_heartpy_style <- function(data,
                                                signal_col = NULL,
                                                time_col = NULL,
                                                group_cols = NULL,
                                                sampling_rate_hz = NULL,
                                                clean_rr = TRUE,
                                                clean_rr_method = c("quotient", "iqr", "modified_z", "zscore", "none"),
                                                frequency_method = c("welch", "fft", "periodogram"),
                                                output_dir = NULL,
                                                ...) {
  clean_rr_method <- match.arg(clean_rr_method)
  frequency_method <- match.arg(frequency_method)

  detection <- detect_gazepoint_ppg_peaks(
    data = data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    ...
  )

  peaks <- reject_gazepoint_ppg_peaks(detection$peaks)

  if (isTRUE(clean_rr)) {
    peaks <- clean_gazepoint_rr_intervals(peaks, method = clean_rr_method)
  }

  measures <- compute_gazepoint_ppg_measures(peaks)
  frequency <- compute_gazepoint_ppg_frequency_measures(peaks = peaks, method = frequency_method)
  quality <- check_gazepoint_ppg_binary_quality(measures = measures)
  report <- create_gazepoint_heartpy_report(detection, output_dir = output_dir)

  list(
    detection = detection,
    peaks = peaks,
    measures = measures,
    frequency = frequency,
    quality = quality,
    report = report,
    settings = list(
      clean_rr = clean_rr,
      clean_rr_method = clean_rr_method,
      frequency_method = frequency_method,
      output_dir = output_dir
    )
  )
}

#' Process Gazepoint pulse/PPG data in overlapping HeartPy-style segments
#'
#' @param data Data frame or numeric pulse/PPG signal.
#' @param signal_col Signal column when data is a data frame.
#' @param time_col Time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param window_seconds Segment length.
#' @param overlap Segment overlap proportion.
#' @param min_segment_seconds Minimum segment duration to process.
#' @param clean_rr Whether to clean RR intervals.
#' @param clean_rr_method RR cleaning method.
#' @param frequency_method Frequency-domain method.
#' @param ... Additional arguments passed to detect_gazepoint_ppg_peaks().
#' @return A list with segment table, peaks, measures, frequency, and settings.
#' @export
process_gazepoint_ppg_segmentwise <- function(data,
                                             signal_col = NULL,
                                             time_col = NULL,
                                             group_cols = NULL,
                                             sampling_rate_hz = NULL,
                                             window_seconds = 60,
                                             overlap = 0.5,
                                             min_segment_seconds = 10,
                                             clean_rr = TRUE,
                                             clean_rr_method = c("quotient", "iqr", "modified_z", "zscore", "none"),
                                             frequency_method = c("welch", "fft", "periodogram"),
                                             ...) {
  clean_rr_method <- match.arg(clean_rr_method)
  frequency_method <- match.arg(frequency_method)

  if (is.numeric(data) && is.null(dim(data))) {
    if (is.null(sampling_rate_hz)) {
      stop("`sampling_rate_hz` is required for numeric input.", call. = FALSE)
    }

    data <- data.frame(
      time_s = (seq_along(data) - 1) / sampling_rate_hz,
      signal = data
    )

    signal_col <- "signal"
    time_col <- "time_s"
  }

  prep <- prepare_gazepoint_heartpy_input(
    data = data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz
  )

  tbl <- prep$signal_table
  fs <- prep$sampling_rate_hz

  if (!is.finite(fs) || fs <= 0) {
    stop("Could not infer a valid sampling rate.", call. = FALSE)
  }

  idx_groups <- .gp_prepare_group_index(tbl, group_cols)

  segment_rows <- list()
  peak_rows <- list()
  measure_rows <- list()
  freq_rows <- list()

  segment_id <- 0L

  for (g in names(idx_groups)) {
    base_idx <- idx_groups[[g]]
    d <- tbl[base_idx, , drop = FALSE]
    starts <- .gp_ppg_segment_starts(d$time_s, window_seconds = window_seconds, overlap = overlap)

    for (s in starts) {
      e <- s + window_seconds
      idx <- which(d$time_s >= s & d$time_s < e)

      if (!length(idx)) next

      duration <- diff(range(d$time_s[idx], na.rm = TRUE))
      if (!is.finite(duration) || duration < min_segment_seconds) next

      segment_id <- segment_id + 1L
      seg <- d[idx, , drop = FALSE]
      seg$segment_id <- segment_id

      det <- tryCatch(
        detect_gazepoint_ppg_peaks(
          seg,
          signal_col = "signal",
          time_col = "time_s",
          group_cols = NULL,
          sampling_rate_hz = fs,
          ...
        ),
        error = function(e) e
      )

      if (inherits(det, "error")) {
        segment_rows[[length(segment_rows) + 1L]] <- data.frame(
          segment_id = segment_id,
          group = g,
          start_s = s,
          end_s = e,
          n_samples = nrow(seg),
          status = "error",
          message = conditionMessage(det),
          stringsAsFactors = FALSE
        )
        next
      }

      peaks <- reject_gazepoint_ppg_peaks(det$peaks)

      if (isTRUE(clean_rr)) {
        peaks <- clean_gazepoint_rr_intervals(peaks, method = clean_rr_method)
      }

      measures <- compute_gazepoint_ppg_measures(peaks)
      freq <- compute_gazepoint_ppg_frequency_measures(peaks = peaks, method = frequency_method)

      segment_rows[[length(segment_rows) + 1L]] <- data.frame(
        segment_id = segment_id,
        group = g,
        start_s = s,
        end_s = e,
        n_samples = nrow(seg),
        n_peaks = nrow(peaks),
        status = "ok",
        message = "",
        stringsAsFactors = FALSE
      )

      if (nrow(peaks)) {
        peaks$segment_id <- segment_id
        peaks$segment_group <- g
        peak_rows[[length(peak_rows) + 1L]] <- peaks
      }

      if (nrow(measures)) {
        measures$segment_id <- segment_id
        measures$segment_group <- g
        measures$start_s <- s
        measures$end_s <- e
        measure_rows[[length(measure_rows) + 1L]] <- measures
      }

      if (nrow(freq)) {
        freq$segment_id <- segment_id
        freq$segment_group <- g
        freq$start_s <- s
        freq$end_s <- e
        freq_rows[[length(freq_rows) + 1L]] <- freq
      }
    }
  }

  segments <- if (length(segment_rows)) do.call(rbind, segment_rows) else data.frame()
  peaks <- if (length(peak_rows)) do.call(rbind, peak_rows) else data.frame()
  measures <- if (length(measure_rows)) do.call(rbind, measure_rows) else data.frame()
  frequency <- if (length(freq_rows)) do.call(rbind, freq_rows) else data.frame()

  row.names(segments) <- NULL
  row.names(peaks) <- NULL
  row.names(measures) <- NULL
  row.names(frequency) <- NULL

  list(
    segments = segments,
    peaks = peaks,
    measures = measures,
    frequency = frequency,
    settings = list(
      sampling_rate_hz = fs,
      window_seconds = window_seconds,
      overlap = overlap,
      min_segment_seconds = min_segment_seconds,
      clean_rr = clean_rr,
      clean_rr_method = clean_rr_method,
      frequency_method = frequency_method
    )
  )
}

#' Plot segmentwise Gazepoint pulse/PPG measures
#'
#' @param segmentwise Object returned by process_gazepoint_ppg_segmentwise().
#' @param measure Measure column to plot.
#' @return Invisibly returns plotted data.
#' @export
plot_gazepoint_ppg_segmentwise <- function(segmentwise, measure = "bpm") {
  if (!is.list(segmentwise) || is.null(segmentwise$measures)) {
    stop("`segmentwise` must be returned by process_gazepoint_ppg_segmentwise().", call. = FALSE)
  }

  d <- segmentwise$measures

  if (!nrow(d)) {
    stop("No segmentwise measures available.", call. = FALSE)
  }

  if (!measure %in% names(d)) {
    stop("Measure column not found: ", measure, call. = FALSE)
  }

  x <- if ("start_s" %in% names(d)) d$start_s else seq_len(nrow(d))

  graphics::plot(
    x,
    d[[measure]],
    type = "b",
    xlab = "Segment start (s)",
    ylab = measure,
    main = paste("Segmentwise", measure)
  )

  invisible(d)
}

#' Plot a Poincare plot from Gazepoint pulse/PPG peaks or RR intervals
#'
#' @param peaks Optional peak table.
#' @param rr_ms Optional RR/IBI intervals in milliseconds.
#' @param group_col Group column when peaks are supplied.
#' @return Invisibly returns plotting data and Poincare summaries.
#' @export
plot_gazepoint_ppg_poincare <- function(peaks = NULL, rr_ms = NULL, group_col = "group") {
  if (!is.null(peaks)) {
    rr_tbl <- .gp_ppg_rr_from_peaks(peaks, group_col = group_col)
    rr <- rr_tbl$rr_ms
  } else {
    rr <- .gp_as_num(rr_ms)
  }

  rr <- rr[is.finite(rr) & rr > 0]

  if (length(rr) < 3L) {
    stop("At least three valid RR intervals are required.", call. = FALSE)
  }

  x <- rr[-length(rr)]
  y <- rr[-1L]
  diff_rr <- y - x

  sd1 <- sqrt(stats::var(diff_rr, na.rm = TRUE) / 2)
  sd2 <- sqrt(2 * stats::var(rr, na.rm = TRUE) - 0.5 * stats::var(diff_rr, na.rm = TRUE))

  graphics::plot(
    x,
    y,
    xlab = "RR[n] (ms)",
    ylab = "RR[n+1] (ms)",
    main = "Gazepoint pulse/PPG Poincare plot",
    pch = 19
  )

  graphics::abline(0, 1, lty = 2)

  invisible(list(
    data = data.frame(rr_n_ms = x, rr_next_ms = y),
    sd1_ms = sd1,
    sd2_ms = sd2,
    sd1_sd2 = if (is.finite(sd2) && sd2 > 0) sd1 / sd2 else NA_real_
  ))
}

#' Plot breathing-rate spectrum from Gazepoint RR/IBI intervals
#'
#' @param rr_ms RR/IBI intervals in milliseconds.
#' @param rr_time_s Optional interval timestamps.
#' @param resample_hz RR interpolation frequency.
#' @param breathing_band Breathing frequency band.
#' @return Invisibly returns breathing-rate object.
#' @export
plot_gazepoint_ppg_breathing <- function(rr_ms,
                                         rr_time_s = NULL,
                                         resample_hz = 4,
                                         breathing_band = c(0.10, 0.50)) {
  br <- estimate_gazepoint_breathing_rate_from_ibi(
    rr_ms = rr_ms,
    rr_time_s = rr_time_s,
    resample_hz = resample_hz,
    breathing_band = breathing_band
  )

  if (!length(br$frequency)) {
    stop("No frequency spectrum available.", call. = FALSE)
  }

  graphics::plot(
    br$frequency,
    br$psd,
    type = "l",
    xlab = "Frequency (Hz)",
    ylab = "Power",
    main = "Gazepoint RR/IBI breathing-rate spectrum"
  )

  graphics::abline(v = breathing_band, lty = 2)

  if (is.finite(br$breathing_rate_hz)) {
    graphics::abline(v = br$breathing_rate_hz, lty = 3)
  }

  invisible(br)
}

#' Check binary quality of Gazepoint pulse/PPG analysis results
#'
#' @param measures Optional measures table.
#' @param peaks Optional peaks table.
#' @param min_peaks Minimum accepted peaks.
#' @param bpm_range Plausible BPM range.
#' @param max_missing_prop Maximum missing proportion, if available.
#' @return Data frame with binary quality status.
#' @export
check_gazepoint_ppg_binary_quality <- function(measures = NULL,
                                               peaks = NULL,
                                               min_peaks = 5L,
                                               bpm_range = c(40, 180),
                                               max_missing_prop = 0.25) {
  if (is.null(measures)) {
    if (is.null(peaks)) {
      stop("Supply `measures` or `peaks`.", call. = FALSE)
    }

    measures <- compute_gazepoint_ppg_measures(peaks)
  }

  if (!is.data.frame(measures) || !nrow(measures)) {
    return(data.frame())
  }

  out <- measures

  if (!"n_peaks" %in% names(out)) out$n_peaks <- NA_integer_
  if (!"bpm" %in% names(out)) out$bpm <- NA_real_
  if (!"missing_prop" %in% names(out)) out$missing_prop <- NA_real_

  enough_peaks <- is.finite(out$n_peaks) & out$n_peaks >= min_peaks
  plausible_bpm <- is.finite(out$bpm) & out$bpm >= bpm_range[1] & out$bpm <= bpm_range[2]
  acceptable_missing <- is.na(out$missing_prop) | out$missing_prop <= max_missing_prop

  out$quality_pass <- enough_peaks & plausible_bpm & acceptable_missing

  out$quality_reason <- ifelse(
    out$quality_pass,
    "pass",
    paste(
      ifelse(enough_peaks, NA_character_, "too_few_peaks"),
      ifelse(plausible_bpm, NA_character_, "implausible_bpm"),
      ifelse(acceptable_missing, NA_character_, "high_missingness"),
      sep = ";"
    )
  )

  out$quality_reason <- gsub("NA;|;NA|NA", "", out$quality_reason)
  out$quality_reason[out$quality_reason == ""] <- "fail"

  out
}

