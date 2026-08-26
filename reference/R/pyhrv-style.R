
# pyHRV-style Gazepoint HRV helpers
#
# These functions provide Gazepoint-native, R-based equivalents for common
# pyHRV-style HRV summaries and plots. They are not a dependency wrapper around
# pyHRV and do not claim clinical/diagnostic interpretation.

.gp_pyhrv_num <- function(x) {
  suppressWarnings(as.numeric(x))
}

.gp_pyhrv_clean_nni <- function(nni_ms, min_ms = 250, max_ms = 2500) {
  x <- .gp_pyhrv_num(nni_ms)
  x[is.finite(x) & x > 0 & x >= min_ms & x <= max_ms]
}

.gp_pyhrv_time_from_nni <- function(nni_ms) {
  cumsum(.gp_pyhrv_num(nni_ms)) / 1000
}

.gp_pyhrv_trapz <- function(x, y) {
  ok <- is.finite(x) & is.finite(y)
  x <- x[ok]
  y <- y[ok]
  if (length(x) < 2L) return(NA_real_)
  o <- order(x)
  x <- x[o]
  y <- y[o]
  sum(diff(x) * (utils::head(y, -1L) + utils::tail(y, -1L)) / 2)
}

.gp_pyhrv_band_summaries <- function(freq, psd,
                                     bands = list(
                                       ulf = c(0.000, 0.003),
                                       vlf = c(0.003, 0.040),
                                       lf = c(0.040, 0.150),
                                       hf = c(0.150, 0.400)
                                     )) {
  powers <- vapply(bands, function(b) {
    keep <- is.finite(freq) & is.finite(psd) & freq >= b[1] & freq < b[2]
    .gp_pyhrv_trapz(freq[keep], psd[keep])
  }, numeric(1))

  peaks <- vapply(bands, function(b) {
    keep <- is.finite(freq) & is.finite(psd) & freq >= b[1] & freq < b[2]
    if (!any(keep)) return(NA_real_)
    ff <- freq[keep]
    pp <- psd[keep]
    ff[which.max(pp)]
  }, numeric(1))

  total <- sum(powers[is.finite(powers)], na.rm = TRUE)
  lf <- if ("lf" %in% names(powers)) powers[["lf"]] else NA_real_
  hf <- if ("hf" %in% names(powers)) powers[["hf"]] else NA_real_
  lf_hf_sum <- lf + hf

  data.frame(
    total_power = total,
    ulf_abs = if ("ulf" %in% names(powers)) powers[["ulf"]] else NA_real_,
    vlf_abs = if ("vlf" %in% names(powers)) powers[["vlf"]] else NA_real_,
    lf_abs = lf,
    hf_abs = hf,
    ulf_rel = if (total > 0 && "ulf" %in% names(powers)) 100 * powers[["ulf"]] / total else NA_real_,
    vlf_rel = if (total > 0 && "vlf" %in% names(powers)) 100 * powers[["vlf"]] / total else NA_real_,
    lf_rel = if (total > 0 && is.finite(lf)) 100 * lf / total else NA_real_,
    hf_rel = if (total > 0 && is.finite(hf)) 100 * hf / total else NA_real_,
    lf_norm = if (is.finite(lf_hf_sum) && lf_hf_sum > 0) 100 * lf / lf_hf_sum else NA_real_,
    hf_norm = if (is.finite(lf_hf_sum) && lf_hf_sum > 0) 100 * hf / lf_hf_sum else NA_real_,
    lf_hf = if (is.finite(hf) && hf > 0) lf / hf else NA_real_,
    ulf_peak = if ("ulf" %in% names(peaks)) peaks[["ulf"]] else NA_real_,
    vlf_peak = if ("vlf" %in% names(peaks)) peaks[["vlf"]] else NA_real_,
    lf_peak = if ("lf" %in% names(peaks)) peaks[["lf"]] else NA_real_,
    hf_peak = if ("hf" %in% names(peaks)) peaks[["hf"]] else NA_real_
  )
}

.gp_pyhrv_resample_nni <- function(nni_ms, time_s = NULL, resample_hz = 4) {
  nni_ms <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(nni_ms) < 4L) {
    return(list(time = numeric(), y = numeric()))
  }

  if (is.null(time_s)) {
    time_s <- .gp_pyhrv_time_from_nni(nni_ms)
  } else {
    time_s <- .gp_pyhrv_num(time_s)
    time_s <- time_s[seq_along(nni_ms)]
  }

  ok <- is.finite(time_s) & is.finite(nni_ms)
  time_s <- time_s[ok]
  nni_ms <- nni_ms[ok]

  if (length(nni_ms) < 4L || diff(range(time_s)) <= 0) {
    return(list(time = numeric(), y = numeric()))
  }

  grid <- seq(min(time_s), max(time_s), by = 1 / resample_hz)
  y <- stats::approx(time_s, nni_ms, xout = grid, rule = 2)$y
  y <- y - mean(y, na.rm = TRUE)

  list(time = grid, y = y)
}

.gp_pyhrv_fft_psd <- function(y, fs) {
  y <- .gp_pyhrv_num(y)
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

  data.frame(frequency_hz = freq[keep], psd = psd[keep])
}

.gp_pyhrv_welch_psd <- function(y, fs, window_seconds = 256, overlap = 0.5) {
  y <- .gp_pyhrv_num(y)
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
    yy <- y[idx]
    taper <- 0.5 - 0.5 * cos(2 * pi * (seq_along(yy) - 1) / (length(yy) - 1))
    .gp_pyhrv_fft_psd(yy * taper, fs)
  })

  freq <- spectra[[1]]$frequency_hz

  psd_mat <- vapply(spectra, function(z) {
    stats::approx(z$frequency_hz, z$psd, xout = freq, rule = 2)$y
  }, numeric(length(freq)))

  data.frame(frequency_hz = freq, psd = rowMeans(psd_mat, na.rm = TRUE))
}

.gp_pyhrv_lomb_psd <- function(nni_ms, time_s = NULL,
                               min_hz = 0.003, max_hz = 0.4,
                               n_freq = 512) {
  nni_ms <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(nni_ms) < 4L) {
    return(data.frame(frequency_hz = numeric(), psd = numeric()))
  }

  if (is.null(time_s)) time_s <- .gp_pyhrv_time_from_nni(nni_ms)
  time_s <- .gp_pyhrv_num(time_s)[seq_along(nni_ms)]

  ok <- is.finite(time_s) & is.finite(nni_ms)
  time_s <- time_s[ok]
  y <- nni_ms[ok] - mean(nni_ms[ok], na.rm = TRUE)

  freq <- seq(min_hz, max_hz, length.out = n_freq)

  psd <- vapply(freq, function(f) {
    w <- 2 * pi * f
    cs <- cos(w * time_s)
    sn <- sin(w * time_s)
    cc <- sum(cs^2)
    ss <- sum(sn^2)
    if (cc <= 0 || ss <= 0) return(NA_real_)
    ((sum(y * cs)^2 / cc) + (sum(y * sn)^2 / ss)) / length(y)
  }, numeric(1))

  data.frame(frequency_hz = freq, psd = psd)
}

.gp_pyhrv_ar_psd <- function(y, fs, order = NULL, n_freq = 512) {
  y <- .gp_pyhrv_num(y)
  y <- y[is.finite(y)]
  if (length(y) < 16L) {
    return(data.frame(frequency_hz = numeric(), psd = numeric()))
  }

  fit <- stats::ar(y, order.max = if (is.null(order)) min(20L, floor(length(y) / 3)) else order, aic = is.null(order))
  ar <- fit$ar
  variance <- fit$var.pred

  freq <- seq(0, fs / 2, length.out = n_freq)

  psd <- vapply(freq, function(f) {
    z <- exp(-1i * 2 * pi * f / fs * seq_along(ar))
    den <- Mod(1 - sum(ar * z))^2
    if (!is.finite(den) || den <= 0) return(NA_real_)
    variance / den / fs
  }, numeric(1))

  data.frame(frequency_hz = freq, psd = Re(psd))
}

#' Extract NN intervals from peak timestamps
#'
#' @param peaks Data frame with peak timestamps, or numeric peak timestamps.
#' @param peak_time_col Peak timestamp column when peaks is a data frame.
#' @param time_unit Unit of peak timestamps: seconds or milliseconds.
#' @return Numeric NN intervals in milliseconds.
#' @export
extract_gazepoint_pyhrv_nn_intervals <- function(peaks,
                                                 peak_time_col = "peak_time_s",
                                                 time_unit = c("seconds", "milliseconds")) {
  time_unit <- match.arg(time_unit)

  if (is.data.frame(peaks)) {
    if (!peak_time_col %in% names(peaks)) {
      stop("`peak_time_col` not found.", call. = FALSE)
    }
    t <- .gp_pyhrv_num(peaks[[peak_time_col]])
  } else {
    t <- .gp_pyhrv_num(peaks)
  }

  t <- sort(t[is.finite(t)])
  if (length(t) < 2L) return(numeric())

  nn <- diff(t)
  if (time_unit == "seconds") nn <- nn * 1000
  nn
}

#' Compute NN interval differences
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param absolute If TRUE, return absolute differences.
#' @return Numeric successive NN differences in milliseconds.
#' @export
compute_gazepoint_pyhrv_nn_diff <- function(nni_ms, absolute = FALSE) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 2L) return(numeric())
  d <- diff(x)
  if (isTRUE(absolute)) abs(d) else d
}

#' Compute heart rate from NN intervals
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Numeric heart rate in beats per minute.
#' @export
compute_gazepoint_pyhrv_heart_rate <- function(nni_ms) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  60000 / x
}

#' Create a time vector from NN intervals
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param start_s Start time in seconds.
#' @return Numeric time vector in seconds.
#' @export
create_gazepoint_pyhrv_time_vector <- function(nni_ms, start_s = 0) {
  start_s + .gp_pyhrv_time_from_nni(.gp_pyhrv_clean_nni(nni_ms))
}

#' Check whether NN intervals are inside a plausible interval
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param min_ms Minimum plausible interval.
#' @param max_ms Maximum plausible interval.
#' @return Data frame with interval status.
#' @export
check_gazepoint_pyhrv_interval <- function(nni_ms, min_ms = 250, max_ms = 2500) {
  x <- .gp_pyhrv_num(nni_ms)
  data.frame(
    index = seq_along(x),
    nni_ms = x,
    valid = is.finite(x) & x >= min_ms & x <= max_ms,
    reason = ifelse(
      is.finite(x) & x >= min_ms & x <= max_ms,
      "valid",
      "outside_interval_or_nonfinite"
    )
  )
}

#' Segment NN intervals into time windows
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param segment_seconds Segment duration.
#' @param overlap Segment overlap proportion.
#' @param min_intervals Minimum intervals per segment.
#' @return Data frame with segment membership.
#' @export
segment_gazepoint_pyhrv_nni <- function(nni_ms,
                                        segment_seconds = 300,
                                        overlap = 0,
                                        min_intervals = 3L) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (!length(x)) return(data.frame())

  t <- .gp_pyhrv_time_from_nni(x)
  step <- segment_seconds * (1 - overlap)
  if (!is.finite(step) || step <= 0) stop("`overlap` must be smaller than 1.", call. = FALSE)

  starts <- seq(min(t), max(t), by = step)
  rows <- list()

  for (i in seq_along(starts)) {
    s <- starts[i]
    e <- s + segment_seconds
    idx <- which(t >= s & t < e)

    if (length(idx) >= min_intervals) {
      rows[[length(rows) + 1L]] <- data.frame(
        segment_id = i,
        start_s = s,
        end_s = e,
        interval_index = idx,
        nni_ms = x[idx]
      )
    }
  }

  if (!length(rows)) return(data.frame())
  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

#' Compute pyHRV-style NNI parameters
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame of NNI parameters.
#' @export
compute_gazepoint_pyhrv_nni_parameters <- function(nni_ms) {
  x <- .gp_pyhrv_clean_nni(nni_ms)

  data.frame(
    nni_counter = length(x),
    nni_mean = if (length(x)) mean(x) else NA_real_,
    nni_min = if (length(x)) min(x) else NA_real_,
    nni_max = if (length(x)) max(x) else NA_real_
  )
}

#' Compute pyHRV-style NNI difference parameters
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame of successive-difference parameters.
#' @export
compute_gazepoint_pyhrv_nni_differences_parameters <- function(nni_ms) {
  d <- compute_gazepoint_pyhrv_nn_diff(nni_ms, absolute = TRUE)

  data.frame(
    nni_diff_counter = length(d),
    nni_diff_mean = if (length(d)) mean(d) else NA_real_,
    nni_diff_min = if (length(d)) min(d) else NA_real_,
    nni_diff_max = if (length(d)) max(d) else NA_real_
  )
}

#' Compute pyHRV-style heart-rate parameters
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame of heart-rate parameters.
#' @export
compute_gazepoint_pyhrv_hr_parameters <- function(nni_ms) {
  hr <- compute_gazepoint_pyhrv_heart_rate(nni_ms)

  data.frame(
    hr_mean = if (length(hr)) mean(hr) else NA_real_,
    hr_min = if (length(hr)) min(hr) else NA_real_,
    hr_max = if (length(hr)) max(hr) else NA_real_,
    hr_std = if (length(hr) > 1L) stats::sd(hr) else NA_real_
  )
}

#' Compute SDNN
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return SDNN in milliseconds.
#' @export
compute_gazepoint_pyhrv_sdnn <- function(nni_ms) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 2L) NA_real_ else stats::sd(x)
}

#' Compute SDNN index
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param segment_seconds Segment length.
#' @return SDNN index in milliseconds.
#' @export
compute_gazepoint_pyhrv_sdnn_index <- function(nni_ms, segment_seconds = 300) {
  seg <- segment_gazepoint_pyhrv_nni(nni_ms, segment_seconds = segment_seconds)
  if (!nrow(seg)) return(NA_real_)

  vals <- tapply(seg$nni_ms, seg$segment_id, function(z) if (length(z) > 1L) stats::sd(z) else NA_real_)
  mean(vals, na.rm = TRUE)
}

#' Compute SDANN
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param segment_seconds Segment length.
#' @return SDANN in milliseconds.
#' @export
compute_gazepoint_pyhrv_sdann <- function(nni_ms, segment_seconds = 300) {
  seg <- segment_gazepoint_pyhrv_nni(nni_ms, segment_seconds = segment_seconds)
  if (!nrow(seg)) return(NA_real_)

  vals <- tapply(seg$nni_ms, seg$segment_id, mean, na.rm = TRUE)
  if (length(vals) < 2L) NA_real_ else stats::sd(vals, na.rm = TRUE)
}

#' Compute RMSSD
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return RMSSD in milliseconds.
#' @export
compute_gazepoint_pyhrv_rmssd <- function(nni_ms) {
  d <- compute_gazepoint_pyhrv_nn_diff(nni_ms)
  if (!length(d)) NA_real_ else sqrt(mean(d^2, na.rm = TRUE))
}

#' Compute SDSD
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return SDSD in milliseconds.
#' @export
compute_gazepoint_pyhrv_sdsd <- function(nni_ms) {
  d <- compute_gazepoint_pyhrv_nn_diff(nni_ms)
  if (length(d) < 2L) NA_real_ else stats::sd(d, na.rm = TRUE)
}

#' Compute NNxx and pNNxx
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param threshold_ms Threshold in milliseconds.
#' @return Data frame with NNxx and pNNxx.
#' @export
compute_gazepoint_pyhrv_nnxx <- function(nni_ms, threshold_ms = 50) {
  d <- compute_gazepoint_pyhrv_nn_diff(nni_ms, absolute = TRUE)
  n <- length(d)
  count <- if (n) sum(d > threshold_ms, na.rm = TRUE) else NA_integer_

  data.frame(
    threshold_ms = threshold_ms,
    nnxx = count,
    pnnxx = if (n > 0) 100 * count / n else NA_real_
  )
}

#' Compute NN50 and pNN50
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame with NN50 and pNN50.
#' @export
compute_gazepoint_pyhrv_nn50 <- function(nni_ms) {
  out <- compute_gazepoint_pyhrv_nnxx(nni_ms, threshold_ms = 50)
  names(out)[names(out) == "nnxx"] <- "nn50"
  names(out)[names(out) == "pnnxx"] <- "pnn50"
  out
}

#' Compute NN20 and pNN20
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame with NN20 and pNN20.
#' @export
compute_gazepoint_pyhrv_nn20 <- function(nni_ms) {
  out <- compute_gazepoint_pyhrv_nnxx(nni_ms, threshold_ms = 20)
  names(out)[names(out) == "nnxx"] <- "nn20"
  names(out)[names(out) == "pnnxx"] <- "pnn20"
  out
}

#' Compute triangular index
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param bin_width_ms Histogram bin width.
#' @return HRV triangular index.
#' @export
compute_gazepoint_pyhrv_triangular_index <- function(nni_ms, bin_width_ms = 7.8125) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 3L) return(NA_real_)

  breaks <- seq(floor(min(x) / bin_width_ms) * bin_width_ms,
                ceiling(max(x) / bin_width_ms) * bin_width_ms + bin_width_ms,
                by = bin_width_ms)
  h <- graphics::hist(x, breaks = breaks, plot = FALSE)
  max_count <- max(h$counts, na.rm = TRUE)
  if (!is.finite(max_count) || max_count <= 0) NA_real_ else length(x) / max_count
}

#' Compute TINN
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param bin_width_ms Histogram bin width.
#' @return Approximate TINN in milliseconds.
#' @export
compute_gazepoint_pyhrv_tinn <- function(nni_ms, bin_width_ms = 7.8125) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 3L) return(NA_real_)

  breaks <- seq(floor(min(x) / bin_width_ms) * bin_width_ms,
                ceiling(max(x) / bin_width_ms) * bin_width_ms + bin_width_ms,
                by = bin_width_ms)
  h <- graphics::hist(x, breaks = breaks, plot = FALSE)
  centers <- h$mids
  counts <- h$counts

  if (!any(counts > 0)) return(NA_real_)

  positive <- centers[counts > 0]
  diff(range(positive))
}

#' Compute pyHRV-style time-domain summary
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param segment_seconds Segment length for SDNN index and SDANN.
#' @return Data frame with time-domain HRV measures.
#' @export
compute_gazepoint_pyhrv_time_domain <- function(nni_ms, segment_seconds = 300) {
  nni <- compute_gazepoint_pyhrv_nni_parameters(nni_ms)
  diffs <- compute_gazepoint_pyhrv_nni_differences_parameters(nni_ms)
  hr <- compute_gazepoint_pyhrv_hr_parameters(nni_ms)
  nn50 <- compute_gazepoint_pyhrv_nn50(nni_ms)
  nn20 <- compute_gazepoint_pyhrv_nn20(nni_ms)

  data.frame(
    nni,
    diffs,
    hr,
    sdnn = compute_gazepoint_pyhrv_sdnn(nni_ms),
    sdnn_index = compute_gazepoint_pyhrv_sdnn_index(nni_ms, segment_seconds = segment_seconds),
    sdann = compute_gazepoint_pyhrv_sdann(nni_ms, segment_seconds = segment_seconds),
    rmssd = compute_gazepoint_pyhrv_rmssd(nni_ms),
    sdsd = compute_gazepoint_pyhrv_sdsd(nni_ms),
    nn50 = nn50$nn50,
    pnn50 = nn50$pnn50,
    nn20 = nn20$nn20,
    pnn20 = nn20$pnn20,
    triangular_index = compute_gazepoint_pyhrv_triangular_index(nni_ms),
    tinn = compute_gazepoint_pyhrv_tinn(nni_ms)
  )
}

#' Compute pyHRV-style Welch PSD
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector in seconds.
#' @param resample_hz Resampling frequency.
#' @param window_seconds Welch window length.
#' @param overlap Window overlap proportion.
#' @return List with PSD and measures.
#' @export
compute_gazepoint_pyhrv_welch_psd <- function(nni_ms,
                                              time_s = NULL,
                                              resample_hz = 4,
                                              window_seconds = 256,
                                              overlap = 0.5) {
  rs <- .gp_pyhrv_resample_nni(nni_ms, time_s = time_s, resample_hz = resample_hz)
  psd <- .gp_pyhrv_welch_psd(rs$y, fs = resample_hz, window_seconds = window_seconds, overlap = overlap)
  measures <- .gp_pyhrv_band_summaries(psd$frequency_hz, psd$psd)
  list(psd = psd, measures = measures, method = "welch")
}

#' Compute pyHRV-style Lomb PSD
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector in seconds.
#' @param min_hz Minimum frequency.
#' @param max_hz Maximum frequency.
#' @param n_freq Number of frequencies.
#' @return List with PSD and measures.
#' @export
compute_gazepoint_pyhrv_lomb_psd <- function(nni_ms,
                                             time_s = NULL,
                                             min_hz = 0.003,
                                             max_hz = 0.4,
                                             n_freq = 512) {
  psd <- .gp_pyhrv_lomb_psd(nni_ms, time_s = time_s, min_hz = min_hz, max_hz = max_hz, n_freq = n_freq)
  measures <- .gp_pyhrv_band_summaries(psd$frequency_hz, psd$psd)
  list(psd = psd, measures = measures, method = "lomb")
}

#' Compute pyHRV-style autoregressive PSD
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector in seconds.
#' @param resample_hz Resampling frequency.
#' @param order Optional AR order.
#' @return List with PSD and measures.
#' @export
compute_gazepoint_pyhrv_ar_psd <- function(nni_ms,
                                           time_s = NULL,
                                           resample_hz = 4,
                                           order = NULL) {
  rs <- .gp_pyhrv_resample_nni(nni_ms, time_s = time_s, resample_hz = resample_hz)
  psd <- .gp_pyhrv_ar_psd(rs$y, fs = resample_hz, order = order)
  measures <- .gp_pyhrv_band_summaries(psd$frequency_hz, psd$psd)
  list(psd = psd, measures = measures, method = "ar")
}

#' Compute pyHRV-style frequency-domain summary
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector in seconds.
#' @param method Frequency method: welch, lomb, or ar.
#' @return List with PSD and measures.
#' @export
compute_gazepoint_pyhrv_frequency_domain <- function(nni_ms,
                                                     time_s = NULL,
                                                     method = c("welch", "lomb", "ar")) {
  method <- match.arg(method)

  switch(
    method,
    welch = compute_gazepoint_pyhrv_welch_psd(nni_ms, time_s = time_s),
    lomb = compute_gazepoint_pyhrv_lomb_psd(nni_ms, time_s = time_s),
    ar = compute_gazepoint_pyhrv_ar_psd(nni_ms, time_s = time_s)
  )
}

#' Compare pyHRV-style PSD methods
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector in seconds.
#' @param methods Methods to compare.
#' @param plot If TRUE, draw a comparison plot.
#' @return List with method outputs and combined measures.
#' @export
compare_gazepoint_pyhrv_psd_methods <- function(nni_ms,
                                                time_s = NULL,
                                                methods = c("welch", "lomb", "ar"),
                                                plot = FALSE) {
  methods <- match.arg(methods, c("welch", "lomb", "ar"), several.ok = TRUE)

  outs <- lapply(methods, function(m) {
    compute_gazepoint_pyhrv_frequency_domain(nni_ms, time_s = time_s, method = m)
  })
  names(outs) <- methods

  measures <- do.call(rbind, lapply(names(outs), function(m) {
    data.frame(method = m, outs[[m]]$measures)
  }))
  row.names(measures) <- NULL

  if (isTRUE(plot)) {
    first <- TRUE
    for (m in names(outs)) {
      p <- outs[[m]]$psd
      if (!nrow(p)) next
      if (first) {
        graphics::plot(p$frequency_hz, p$psd, type = "l",
                       xlab = "Frequency (Hz)", ylab = "Power",
                       main = "pyHRV-style PSD comparison")
        first <- FALSE
      } else {
        graphics::lines(p$frequency_hz, p$psd)
      }
    }
    graphics::legend("topright", legend = names(outs), lty = 1, bty = "n")
  }

  list(outputs = outs, measures = measures)
}

#' Compute pyHRV-style PSD waterfall over segments
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param segment_seconds Segment length.
#' @param method Frequency method.
#' @param plot If TRUE, draw a heatmap-style waterfall.
#' @return List with PSD grid and segment measures.
#' @export
compute_gazepoint_pyhrv_psd_waterfall <- function(nni_ms,
                                                  segment_seconds = 300,
                                                  method = c("welch", "lomb", "ar"),
                                                  plot = FALSE) {
  method <- match.arg(method)
  seg <- segment_gazepoint_pyhrv_nni(nni_ms, segment_seconds = segment_seconds)
  if (!nrow(seg)) return(list(psd = data.frame(), measures = data.frame()))

  ids <- unique(seg$segment_id)

  outs <- lapply(ids, function(id) {
    z <- seg$nni_ms[seg$segment_id == id]
    out <- compute_gazepoint_pyhrv_frequency_domain(z, method = method)
    out$psd$segment_id <- id
    out$measures$segment_id <- id
    out
  })

  psd <- do.call(rbind, lapply(outs, `[[`, "psd"))
  measures <- do.call(rbind, lapply(outs, `[[`, "measures"))

  row.names(psd) <- NULL
  row.names(measures) <- NULL

  if (isTRUE(plot) && nrow(psd)) {
    freq <- sort(unique(psd$frequency_hz))
    segs <- sort(unique(psd$segment_id))
    mat <- matrix(NA_real_, nrow = length(freq), ncol = length(segs))
    for (j in seq_along(segs)) {
      p <- psd[psd$segment_id == segs[j], , drop = FALSE]
      mat[, j] <- stats::approx(p$frequency_hz, p$psd, xout = freq, rule = 2)$y
    }
    graphics::image(segs, freq, t(mat),
                    xlab = "Segment", ylab = "Frequency (Hz)",
                    main = "pyHRV-style PSD waterfall")
  }

  list(psd = psd, measures = measures)
}

#' Compute pyHRV-style Poincare measures
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param plot If TRUE, draw Poincare plot.
#' @return Data frame of Poincare measures.
#' @export
compute_gazepoint_pyhrv_poincare <- function(nni_ms, plot = FALSE) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 3L) {
    return(data.frame(sd1 = NA_real_, sd2 = NA_real_, sd_ratio = NA_real_, ellipse_area = NA_real_))
  }

  x1 <- x[-length(x)]
  x2 <- x[-1L]
  d <- x2 - x1

  sd1 <- sqrt(stats::var(d, na.rm = TRUE) / 2)
  sd2 <- sqrt(2 * stats::var(x, na.rm = TRUE) - 0.5 * stats::var(d, na.rm = TRUE))

  if (isTRUE(plot)) {
    graphics::plot(x1, x2, pch = 19,
                   xlab = "NNI[n] (ms)",
                   ylab = "NNI[n+1] (ms)",
                   main = "pyHRV-style Poincare plot")
    graphics::abline(0, 1, lty = 2)
  }

  data.frame(
    sd1 = sd1,
    sd2 = sd2,
    sd_ratio = if (is.finite(sd2) && sd2 > 0) sd1 / sd2 else NA_real_,
    ellipse_area = pi * sd1 * sd2
  )
}

#' Compute sample entropy
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param m Embedding dimension.
#' @param r Tolerance. If NULL, 0.2 * SD is used.
#' @return Sample entropy.
#' @export
compute_gazepoint_pyhrv_sample_entropy <- function(nni_ms, m = 2L, r = NULL) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  n <- length(x)

  if (n <= m + 2L) return(NA_real_)
  if (is.null(r)) r <- 0.2 * stats::sd(x, na.rm = TRUE)
  if (!is.finite(r) || r <= 0) return(NA_real_)

  count_matches <- function(mm) {
    emb <- stats::embed(x, mm)
    nemb <- nrow(emb)
    count <- 0L

    for (i in seq_len(nemb - 1L)) {
      dist <- apply(abs(t(t(emb[(i + 1L):nemb, , drop = FALSE]) - emb[i, ])), 1, max)
      count <- count + sum(dist <= r, na.rm = TRUE)
    }

    count
  }

  b <- count_matches(m)
  a <- count_matches(m + 1L)

  if (b <= 0 || a <= 0) return(NA_real_)
  -log(a / b)
}

#' Compute detrended fluctuation analysis
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param scales Window sizes in beats.
#' @return Data frame with DFA alpha estimates.
#' @export
compute_gazepoint_pyhrv_dfa <- function(nni_ms,
                                        scales = unique(round(exp(seq(log(4), log(64), length.out = 12))))) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 16L) {
    return(data.frame(alpha = NA_real_, alpha1 = NA_real_, alpha2 = NA_real_))
  }

  y <- cumsum(x - mean(x, na.rm = TRUE))

  fluct <- vapply(scales, function(s) {
    s <- as.integer(s)
    if (s < 4L || s >= length(y) / 2) return(NA_real_)

    starts <- seq(1L, length(y) - s + 1L, by = s)
    rms <- vapply(starts, function(st) {
      idx <- st:(st + s - 1L)
      fit <- stats::lm(y[idx] ~ idx)
      sqrt(mean(stats::residuals(fit)^2))
    }, numeric(1))

    sqrt(mean(rms^2, na.rm = TRUE))
  }, numeric(1))

  ok <- is.finite(scales) & is.finite(fluct) & fluct > 0
  if (sum(ok) < 2L) {
    return(data.frame(alpha = NA_real_, alpha1 = NA_real_, alpha2 = NA_real_))
  }

  df <- data.frame(scale = scales[ok], fluctuation = fluct[ok])
  fit_all <- stats::lm(log(fluctuation) ~ log(scale), data = df)
  alpha <- unname(stats::coef(fit_all)[2])

  df1 <- df[df$scale <= 16, , drop = FALSE]
  df2 <- df[df$scale > 16, , drop = FALSE]

  alpha1 <- if (nrow(df1) >= 2L) unname(stats::coef(stats::lm(log(fluctuation) ~ log(scale), data = df1))[2]) else NA_real_
  alpha2 <- if (nrow(df2) >= 2L) unname(stats::coef(stats::lm(log(fluctuation) ~ log(scale), data = df2))[2]) else NA_real_

  data.frame(alpha = alpha, alpha1 = alpha1, alpha2 = alpha2)
}

#' Compute pyHRV-style nonlinear summary
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @return Data frame with nonlinear measures.
#' @export
compute_gazepoint_pyhrv_nonlinear <- function(nni_ms) {
  data.frame(
    compute_gazepoint_pyhrv_poincare(nni_ms, plot = FALSE),
    sample_entropy = compute_gazepoint_pyhrv_sample_entropy(nni_ms),
    compute_gazepoint_pyhrv_dfa(nni_ms)
  )
}

#' Plot pyHRV-style tachogram
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_s Optional time vector.
#' @return Invisibly returns plotted data.
#' @export
plot_gazepoint_pyhrv_tachogram <- function(nni_ms, time_s = NULL) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (!length(x)) stop("No valid NN intervals.", call. = FALSE)
  if (is.null(time_s)) time_s <- .gp_pyhrv_time_from_nni(x)

  graphics::plot(time_s[seq_along(x)], x, type = "l",
                 xlab = "Time (s)", ylab = "NN interval (ms)",
                 main = "pyHRV-style tachogram")

  invisible(data.frame(time_s = time_s[seq_along(x)], nni_ms = x))
}

#' Plot pyHRV-style heart-rate heatplot
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param time_bins Number of time bins.
#' @param hr_bins Number of heart-rate bins.
#' @return Invisibly returns heatplot data.
#' @export
plot_gazepoint_pyhrv_hr_heatplot <- function(nni_ms, time_bins = 20, hr_bins = 20) {
  x <- .gp_pyhrv_clean_nni(nni_ms)
  if (length(x) < 3L) stop("At least three valid NN intervals are required.", call. = FALSE)

  time_s <- .gp_pyhrv_time_from_nni(x)
  hr <- 60000 / x

  tb <- cut(time_s, breaks = time_bins)
  hb <- cut(hr, breaks = hr_bins)
  tab <- table(tb, hb)

  graphics::image(
    seq_len(nrow(tab)),
    seq_len(ncol(tab)),
    as.matrix(tab),
    xlab = "Time bin",
    ylab = "Heart-rate bin",
    main = "pyHRV-style heart-rate heatplot"
  )

  invisible(list(time_s = time_s, heart_rate_bpm = hr, table = tab))
}

#' Plot pyHRV-style radar chart
#'
#' @param measures Named numeric vector or one-row data frame.
#' @param columns Optional columns to plot.
#' @return Invisibly returns plotted values.
#' @export
plot_gazepoint_pyhrv_radar_chart <- function(measures,
                                             columns = c("sdnn", "rmssd", "sdsd", "pnn50", "lf_norm", "hf_norm", "sd1", "sd2")) {
  if (is.data.frame(measures)) {
    z <- unlist(measures[1, intersect(columns, names(measures)), drop = TRUE])
  } else {
    z <- measures[intersect(columns, names(measures))]
  }

  z <- .gp_pyhrv_num(z)
  names(z) <- intersect(columns, names(measures))

  if (!length(z) || all(!is.finite(z))) stop("No finite radar values.", call. = FALSE)

  z_scaled <- (z - min(z, na.rm = TRUE)) / diff(range(z, na.rm = TRUE))
  if (all(!is.finite(z_scaled))) z_scaled <- rep(0.5, length(z))

  theta <- seq(0, 2 * pi, length.out = length(z_scaled) + 1L)
  r <- c(z_scaled, z_scaled[1L])

  graphics::plot(cos(theta), sin(theta), type = "n", axes = FALSE,
                 xlab = "", ylab = "", main = "pyHRV-style radar chart", asp = 1)
  graphics::polygon(r * cos(theta), r * sin(theta))
  graphics::text(1.1 * cos(theta[-length(theta)]), 1.1 * sin(theta[-length(theta)]), labels = names(z_scaled))

  invisible(data.frame(measure = names(z), value = z, scaled = z_scaled))
}

#' Export pyHRV-style results
#'
#' @param results Result object.
#' @param path Output path. Use .json or .rds.
#' @return Output path invisibly.
#' @export
export_gazepoint_pyhrv_results <- function(results, path) {
  if (missing(path) || !nzchar(path)) stop("Supply `path`.", call. = FALSE)
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)

  if (grepl("[.]json$", path, ignore.case = TRUE)) {
    if (!requireNamespace("jsonlite", quietly = TRUE)) {
      stop("Package `jsonlite` is required for JSON export.", call. = FALSE)
    }
    jsonlite::write_json(results, path = path, auto_unbox = TRUE, pretty = TRUE, null = "null")
  } else {
    saveRDS(results, path)
  }

  invisible(path)
}

#' Import pyHRV-style results
#'
#' @param path Input path. Use .json or .rds.
#' @return Imported object.
#' @export
import_gazepoint_pyhrv_results <- function(path) {
  if (!file.exists(path)) stop("File not found: ", path, call. = FALSE)

  if (grepl("[.]json$", path, ignore.case = TRUE)) {
    if (!requireNamespace("jsonlite", quietly = TRUE)) {
      stop("Package `jsonlite` is required for JSON import.", call. = FALSE)
    }
    jsonlite::read_json(path, simplifyVector = TRUE)
  } else {
    readRDS(path)
  }
}

#' Run pyHRV-style Gazepoint HRV analysis
#'
#' @param nni_ms Numeric NN intervals in milliseconds.
#' @param peaks Optional peak timestamps/table. Used if nni_ms is missing.
#' @param peak_time_col Peak timestamp column if peaks is a data frame.
#' @param time_unit Unit for peaks.
#' @param frequency_method Frequency method.
#' @return List with time-domain, frequency-domain, nonlinear, and intervals.
#' @export
run_gazepoint_pyhrv_style <- function(nni_ms = NULL,
                                      peaks = NULL,
                                      peak_time_col = "peak_time_s",
                                      time_unit = c("seconds", "milliseconds"),
                                      frequency_method = c("welch", "lomb", "ar")) {
  time_unit <- match.arg(time_unit)
  frequency_method <- match.arg(frequency_method)

  if (is.null(nni_ms)) {
    if (is.null(peaks)) stop("Supply `nni_ms` or `peaks`.", call. = FALSE)
    nni_ms <- extract_gazepoint_pyhrv_nn_intervals(peaks, peak_time_col = peak_time_col, time_unit = time_unit)
  }

  nni_ms <- .gp_pyhrv_clean_nni(nni_ms)

  list(
    nni_ms = nni_ms,
    time_domain = compute_gazepoint_pyhrv_time_domain(nni_ms),
    frequency_domain = compute_gazepoint_pyhrv_frequency_domain(nni_ms, method = frequency_method),
    nonlinear = compute_gazepoint_pyhrv_nonlinear(nni_ms)
  )
}

