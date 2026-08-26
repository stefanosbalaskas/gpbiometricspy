# HeartPy-style Gazepoint pulse/PPG helpers

.gp_pick_col <- function(data, candidates, label) {
  nm <- names(data)
  hit <- nm[tolower(nm) %in% tolower(candidates)]
  if (length(hit)) return(hit[1])

  pat <- paste(candidates, collapse = "|")
  hit <- nm[grepl(pat, nm, ignore.case = TRUE)]
  if (length(hit)) return(hit[1])

  stop("Could not infer ", label, " column. Please supply it explicitly.", call. = FALSE)
}

.gp_as_num <- function(x) {
  suppressWarnings(as.numeric(x))
}

.gp_interpolate_na <- function(x) {
  x <- .gp_as_num(x)
  n <- length(x)
  ok <- is.finite(x)
  if (sum(ok) < 2L) return(x)
  stats::approx(seq_len(n)[ok], x[ok], xout = seq_len(n), rule = 2)$y
}

.gp_running_mean <- function(x, k) {
  k <- max(1L, as.integer(k))
  if (k %% 2L == 0L) k <- k + 1L
  if (length(x) < k) return(rep(mean(x, na.rm = TRUE), length(x)))
  as.numeric(stats::filter(x, rep(1 / k, k), sides = 2))
}

.gp_fill_edges <- function(x, fill) {
  x[!is.finite(x)] <- fill
  x
}

.gp_running_median <- function(x, k) {
  k <- max(3L, as.integer(k))
  if (k %% 2L == 0L) k <- k + 1L
  n <- length(x)
  half <- floor(k / 2L)
  out <- numeric(n)
  for (i in seq_len(n)) {
    lo <- max(1L, i - half)
    hi <- min(n, i + half)
    out[i] <- stats::median(x[lo:hi], na.rm = TRUE)
  }
  out
}

.gp_find_runs <- function(flag) {
  flag <- as.logical(flag)
  if (!length(flag) || !any(flag, na.rm = TRUE)) {
    return(data.frame(start = integer(), end = integer(), length = integer()))
  }
  r <- rle(flag)
  ends <- cumsum(r$lengths)
  starts <- ends - r$lengths + 1L
  keep <- which(r$values)
  data.frame(start = starts[keep], end = ends[keep], length = r$lengths[keep])
}

.gp_peak_rois <- function(x, threshold, min_distance_samples = 1L) {
  above <- x > threshold & is.finite(x) & is.finite(threshold)
  runs <- .gp_find_runs(above)
  if (!nrow(runs)) return(integer())

  peaks <- vapply(seq_len(nrow(runs)), function(i) {
    idx <- runs$start[i]:runs$end[i]
    idx[which.max(x[idx])]
  }, integer(1))

  peaks <- sort(unique(peaks))
  if (length(peaks) <= 1L || min_distance_samples <= 1L) return(peaks)

  kept <- integer()
  for (p in peaks) {
    if (!length(kept) || p - kept[length(kept)] >= min_distance_samples) {
      kept <- c(kept, p)
    } else if (x[p] > x[kept[length(kept)]]) {
      kept[length(kept)] <- p
    }
  }
  kept
}

.gp_measure_sdsd <- function(peak_time) {
  if (length(peak_time) < 4L) return(Inf)
  rr <- diff(peak_time) * 1000
  if (length(rr) < 3L) return(Inf)
  stats::sd(diff(rr), na.rm = TRUE)
}

.gp_high_precision_peak <- function(x, time, peak_index, window_s = 0.1, target_hz = 1000) {
  pt <- time[peak_index]
  idx <- which(time >= pt - window_s & time <= pt + window_s)
  idx <- idx[is.finite(x[idx]) & is.finite(time[idx])]
  if (length(idx) < 4L) {
    return(list(time = pt, value = x[peak_index]))
  }
  new_time <- seq(min(time[idx]), max(time[idx]), by = 1 / target_hz)
  if (length(new_time) < 3L) {
    return(list(time = pt, value = x[peak_index]))
  }
  y <- tryCatch(stats::spline(time[idx], x[idx], xout = new_time)$y, error = function(e) NULL)
  if (is.null(y) || all(!is.finite(y))) return(list(time = pt, value = x[peak_index]))
  j <- which.max(y)
  list(time = new_time[j], value = y[j])
}

.gp_prepare_group_index <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(`__all__` = seq_len(nrow(data))))
  }
  missing <- setdiff(group_cols, names(data))
  if (length(missing)) stop("Missing group columns: ", paste(missing, collapse = ", "), call. = FALSE)
  split(seq_len(nrow(data)), interaction(data[group_cols], drop = TRUE, sep = " | "))
}

.gp_spectral_rr <- function(rr_ms, rr_time_s = NULL, resample_hz = 4, min_points = 8L) {
  rr_ms <- .gp_as_num(rr_ms)
  ok <- is.finite(rr_ms) & rr_ms > 0
  rr_ms <- rr_ms[ok]
  if (length(rr_ms) < min_points) {
    return(list(freq = numeric(), psd = numeric()))
  }
  if (is.null(rr_time_s)) {
    rr_time_s <- cumsum(rr_ms) / 1000
  } else {
    rr_time_s <- .gp_as_num(rr_time_s)[ok]
  }
  ok2 <- is.finite(rr_time_s)
  rr_time_s <- rr_time_s[ok2]
  rr_ms <- rr_ms[ok2]
  if (length(rr_ms) < min_points || diff(range(rr_time_s)) <= 0) {
    return(list(freq = numeric(), psd = numeric()))
  }

  grid <- seq(min(rr_time_s), max(rr_time_s), by = 1 / resample_hz)
  if (length(grid) < min_points) return(list(freq = numeric(), psd = numeric()))
  y <- stats::approx(rr_time_s, rr_ms, xout = grid, rule = 2)$y
  y <- y - mean(y, na.rm = TRUE)
  n <- length(y)
  taper <- stats::window(stats::spec.taper(rep(1, n), p = 0.1), start = 1, end = n)
  y <- y * taper
  fft_y <- stats::fft(y)
  psd <- (Mod(fft_y)^2) / (n * resample_hz)
  freq <- (seq_len(n) - 1L) * resample_hz / n
  keep <- seq_len(floor(n / 2L))
  list(freq = freq[keep], psd = psd[keep])
}

.gp_band_power <- function(freq, psd, low, high) {
  keep <- is.finite(freq) & is.finite(psd) & freq >= low & freq < high
  if (!any(keep)) return(NA_real_)
  sum(psd[keep], na.rm = TRUE)
}

#' Prepare Gazepoint pulse/PPG data for HeartPy-style workflows
#'
#' Creates a compact table with time, signal, and optional grouping columns from
#' Gazepoint Biometrics exports. No files are written unless output_dir is supplied.
#' @param data Data frame containing Gazepoint biometric samples.
#' @param signal_col Pulse/PPG signal column. If NULL, a likely column is inferred.
#' @param time_col Time column in seconds. If NULL, a likely column is inferred or created from sampling_rate_hz.
#' @param group_cols Optional grouping columns such as participant or trial identifiers.
#' @param sampling_rate_hz Sampling rate in Hz. Required if time_col cannot be inferred.
#' @param output_dir Optional directory for CSV export. If NULL, no files are written.
#' @param prefix File prefix used when output_dir is supplied.
#' @return A list with signal_table, sampling_rate_hz, group_summary, and path.
#' @export
prepare_gazepoint_heartpy_input <- function(data,
                                           signal_col = NULL,
                                           time_col = NULL,
                                           group_cols = NULL,
                                           sampling_rate_hz = NULL,
                                           output_dir = NULL,
                                           prefix = "gazepoint_heartpy") {
  if (!is.data.frame(data)) stop("`data` must be a data frame.", call. = FALSE)
  if (!nrow(data)) stop("`data` must contain at least one row.", call. = FALSE)

  if (is.null(signal_col)) {
    signal_col <- .gp_pick_col(data, c("PULSE", "PPG", "HRP", "PULSE_SIGNAL", "heart_signal", "biometric_pulse"), "pulse/PPG signal")
  }
  if (!signal_col %in% names(data)) stop("`signal_col` not found in data.", call. = FALSE)

  if (is.null(time_col)) {
    candidates <- c("TIME", "TIME_SECONDS", "TIMESTAMP", "FPOGX", "time_s", "timestamp_s")
    hit <- names(data)[tolower(names(data)) %in% tolower(candidates)]
    if (!length(hit)) hit <- names(data)[grepl("time|timestamp", names(data), ignore.case = TRUE)]
    time_col <- if (length(hit)) hit[1] else NULL
  }

  signal <- .gp_interpolate_na(data[[signal_col]])

  if (!is.null(time_col)) {
    if (!time_col %in% names(data)) stop("`time_col` not found in data.", call. = FALSE)
    time <- .gp_as_num(data[[time_col]])
    if (all(!is.finite(time))) stop("`time_col` could not be converted to numeric time.", call. = FALSE)
    time <- time - min(time, na.rm = TRUE)
    if (is.null(sampling_rate_hz)) {
      dt <- diff(sort(unique(time[is.finite(time)])))
      dt <- dt[is.finite(dt) & dt > 0]
      sampling_rate_hz <- if (length(dt)) 1 / stats::median(dt) else NA_real_
    }
  } else {
    if (is.null(sampling_rate_hz) || !is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
      stop("Supply `sampling_rate_hz` when no time column can be inferred.", call. = FALSE)
    }
    time <- (seq_along(signal) - 1) / sampling_rate_hz
  }

  out <- data.frame(time_s = time, signal = signal)
  if (!is.null(group_cols) && length(group_cols)) {
    missing <- setdiff(group_cols, names(data))
    if (length(missing)) stop("Missing group columns: ", paste(missing, collapse = ", "), call. = FALSE)
    out <- cbind(data[group_cols], out)
  }

  group_summary <- if (!is.null(group_cols) && length(group_cols)) {
    stats::aggregate(out$signal, out[group_cols], function(z) sum(is.finite(z)))
  } else {
    data.frame(group = "all", finite_samples = sum(is.finite(out$signal)))
  }
  names(group_summary)[ncol(group_summary)] <- "finite_samples"

  paths <- character()
  if (!is.null(output_dir)) {
    if (!is.character(output_dir) || length(output_dir) != 1L || !nzchar(output_dir)) {
      stop("`output_dir` must be NULL or a single non-empty character value.", call. = FALSE)
    }
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    signal_file <- file.path(output_dir, paste0(prefix, "_signal.csv"))
    summary_file <- file.path(output_dir, paste0(prefix, "_group_summary.csv"))
    utils::write.csv(out, signal_file, row.names = FALSE)
    utils::write.csv(group_summary, summary_file, row.names = FALSE)
    paths <- normalizePath(c(signal_file, summary_file), winslash = "/", mustWork = FALSE)
  }

  list(
    signal_table = out,
    sampling_rate_hz = sampling_rate_hz,
    group_summary = group_summary,
    path = paths
  )
}

#' Export Gazepoint pulse/PPG data for HeartPy-style workflows
#' @inheritParams prepare_gazepoint_heartpy_input
#' @return A list returned by prepare_gazepoint_heartpy_input().
#' @export
export_gazepoint_heartpy_input <- function(data,
                                           signal_col = NULL,
                                           time_col = NULL,
                                           group_cols = NULL,
                                           sampling_rate_hz = NULL,
                                           output_dir,
                                           prefix = "gazepoint_heartpy") {
  if (missing(output_dir) || is.null(output_dir)) {
    stop("`output_dir` must be supplied. Use tempdir() for temporary outputs.", call. = FALSE)
  }
  prepare_gazepoint_heartpy_input(
    data = data, signal_col = signal_col, time_col = time_col,
    group_cols = group_cols, sampling_rate_hz = sampling_rate_hz,
    output_dir = output_dir, prefix = prefix
  )
}

#' Detect and reconstruct clipped pulse/PPG samples
#' @param x Numeric pulse/PPG signal.
#' @param near_max_prop Proportion of the observed range used to define near-maximum samples.
#' @param flat_diff_prop Proportion of the observed range used to define near-flat differences.
#' @param min_run Minimum number of consecutive clipped samples.
#' @return A list with signal, clipped, and runs.
#' @export
reconstruct_gazepoint_ppg_clipping <- function(x, near_max_prop = 0.02, flat_diff_prop = 0.001, min_run = 2L) {
  x <- .gp_interpolate_na(x)
  n <- length(x)
  if (n < 4L || all(!is.finite(x))) {
    return(list(signal = x, clipped = rep(FALSE, n), runs = data.frame(start = integer(), end = integer(), length = integer())))
  }

  rng <- range(x, na.rm = TRUE)
  amp <- diff(rng)
  if (!is.finite(amp) || amp <= 0) {
    return(list(signal = x, clipped = rep(FALSE, n), runs = data.frame(start = integer(), end = integer(), length = integer())))
  }

  near_max <- x >= (rng[2] - near_max_prop * amp)
  dx <- c(NA_real_, abs(diff(x)))
  flat <- dx <= flat_diff_prop * amp | c(abs(diff(x)), NA_real_) <= flat_diff_prop * amp
  clipped <- near_max & flat
  runs <- .gp_find_runs(clipped)
  runs <- runs[runs$length >= min_run, , drop = FALSE]
  clipped2 <- rep(FALSE, n)
  if (nrow(runs)) {
    for (i in seq_len(nrow(runs))) clipped2[runs$start[i]:runs$end[i]] <- TRUE
  }

  y <- x
  if (any(clipped2) && sum(!clipped2 & is.finite(x)) >= 4L) {
    idx_ok <- which(!clipped2 & is.finite(x))
    sf <- stats::splinefun(idx_ok, x[idx_ok], method = "natural")
    idx_bad <- which(clipped2)
    y[idx_bad] <- sf(idx_bad)
  }

  list(signal = y, clipped = clipped2, runs = runs)
}

#' Enhance pulse/PPG peaks using repeated local baseline removal
#' @param x Numeric pulse/PPG signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param iterations Number of enhancement passes.
#' @return Enhanced numeric signal.
#' @export
enhance_gazepoint_ppg_peaks <- function(x, sampling_rate_hz, iterations = 2L) {
  x <- .gp_interpolate_na(x)
  iterations <- max(0L, as.integer(iterations))
  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) stop("Invalid sampling rate.", call. = FALSE)
  if (!iterations) return(x)
  y <- x
  k <- max(3L, round(0.75 * sampling_rate_hz))
  for (i in seq_len(iterations)) {
    base <- .gp_fill_edges(.gp_running_mean(y, k), mean(y, na.rm = TRUE))
    y <- y - base
    s <- stats::mad(y, constant = 1, na.rm = TRUE)
    if (!is.finite(s) || s <= 0) s <- stats::sd(y, na.rm = TRUE)
    if (is.finite(s) && s > 0) y <- y / s
  }
  y
}

#' Apply a second-order Butterworth-style low-pass filter to pulse/PPG data
#' @param x Numeric signal.
#' @param cutoff_hz Low-pass cutoff frequency in Hz.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param passes Number of repeated two-pole sections.
#' @return Filtered numeric signal.
#' @export
filter_gazepoint_ppg_butterworth <- function(x, cutoff_hz = 5, sampling_rate_hz, passes = 1L) {
  x <- .gp_interpolate_na(x)
  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) stop("Invalid sampling rate.", call. = FALSE)
  if (!is.finite(cutoff_hz) || cutoff_hz <= 0 || cutoff_hz >= sampling_rate_hz / 2) {
    stop("`cutoff_hz` must be between 0 and Nyquist frequency.", call. = FALSE)
  }
  passes <- max(1L, as.integer(passes))

  one_pass <- function(sig) {
    k <- tan(pi * cutoff_hz / sampling_rate_hz)
    norm <- 1 / (1 + sqrt(2) * k + k^2)
    b0 <- k^2 * norm
    b1 <- 2 * b0
    b2 <- b0
    a1 <- 2 * (k^2 - 1) * norm
    a2 <- (1 - sqrt(2) * k + k^2) * norm
    y <- numeric(length(sig))
    for (i in seq_along(sig)) {
      x0 <- sig[i]
      x1 <- if (i > 1L) sig[i - 1L] else sig[i]
      x2 <- if (i > 2L) sig[i - 2L] else x1
      y1 <- if (i > 1L) y[i - 1L] else sig[i]
      y2 <- if (i > 2L) y[i - 2L] else y1
      y[i] <- b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
    }
    y
  }

  y <- x
  for (i in seq_len(passes)) y <- one_pass(y)
  y
}

#' Apply Hampel-style correction to raw pulse/PPG data
#' @param x Numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param window_seconds Running median window length.
#' @param n_sigmas Threshold in MAD units.
#' @return Corrected numeric signal.
#' @export
correct_gazepoint_ppg_hampel <- function(x, sampling_rate_hz, window_seconds = 1, n_sigmas = 3) {
  x <- .gp_interpolate_na(x)
  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) stop("Invalid sampling rate.", call. = FALSE)
  k <- max(3L, round(window_seconds * sampling_rate_hz))
  med <- .gp_running_median(x, k)
  resid <- x - med
  scale <- stats::mad(resid, constant = 1.4826, na.rm = TRUE)
  if (!is.finite(scale) || scale <= 0) return(x)
  outlier <- abs(resid) > n_sigmas * scale
  y <- x
  y[outlier] <- med[outlier]
  y
}

#' Detect HeartPy-style pulse/PPG peaks in Gazepoint exports
#' @param data Data frame or numeric signal.
#' @param signal_col Signal column when data is a data frame.
#' @param time_col Optional time column in seconds.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param bpm_min Minimum plausible BPM.
#' @param bpm_max Maximum plausible BPM.
#' @param moving_average_seconds Moving-average half-window scale used for thresholding.
#' @param threshold_offsets Candidate threshold offsets in signal SD units.
#' @param reconstruct_clipping Whether to reconstruct clipped peaks.
#' @param enhance_peaks Whether to run peak enhancement.
#' @param lowpass_hz Optional low-pass cutoff.
#' @param hampel Whether to apply Hampel correction.
#' @param high_precision Whether to refine peak timing by local spline upsampling.
#' @return A list with peaks, processed_signal, settings, and diagnostics.
#' @export
detect_gazepoint_ppg_peaks <- function(data,
                                       signal_col = NULL,
                                       time_col = NULL,
                                       group_cols = NULL,
                                       sampling_rate_hz = NULL,
                                       bpm_min = 40,
                                       bpm_max = 180,
                                       moving_average_seconds = 0.75,
                                       threshold_offsets = seq(-0.25, 1.25, by = 0.05),
                                       reconstruct_clipping = TRUE,
                                       enhance_peaks = FALSE,
                                       lowpass_hz = NULL,
                                       hampel = FALSE,
                                       high_precision = TRUE) {
  if (is.numeric(data) && is.null(dim(data))) {
    if (is.null(sampling_rate_hz)) stop("`sampling_rate_hz` is required for numeric signal input.", call. = FALSE)
    data <- data.frame(signal = data, time_s = (seq_along(data) - 1) / sampling_rate_hz)
    signal_col <- "signal"
    time_col <- "time_s"
  }
  prep <- prepare_gazepoint_heartpy_input(data, signal_col, time_col, group_cols, sampling_rate_hz)
  tbl <- prep$signal_table
  fs <- prep$sampling_rate_hz
  if (!is.finite(fs) || fs <= 0) stop("Could not infer a valid sampling rate.", call. = FALSE)

  groups <- .gp_prepare_group_index(tbl, group_cols)
  peak_list <- list()
  signal_list <- list()
  diag_list <- list()

  for (g in names(groups)) {
    idx <- groups[[g]]
    d <- tbl[idx, , drop = FALSE]
    x0 <- .gp_interpolate_na(d$signal)
    time <- .gp_as_num(d$time_s)
    if (any(!is.finite(time))) time <- (seq_along(x0) - 1) / fs

    clip <- list(signal = x0, clipped = rep(FALSE, length(x0)), runs = data.frame())
    x <- x0
    if (isTRUE(reconstruct_clipping)) {
      clip <- reconstruct_gazepoint_ppg_clipping(x)
      x <- clip$signal
    }
    if (isTRUE(hampel)) x <- correct_gazepoint_ppg_hampel(x, fs)
    if (!is.null(lowpass_hz)) x <- filter_gazepoint_ppg_butterworth(x, lowpass_hz, fs)
    if (isTRUE(enhance_peaks)) x <- enhance_gazepoint_ppg_peaks(x, fs)

    k <- max(3L, round((moving_average_seconds * 2) * fs))
    ma <- .gp_fill_edges(.gp_running_mean(x, k), mean(x, na.rm = TRUE))
    sx <- stats::sd(x, na.rm = TRUE)
    if (!is.finite(sx) || sx <= 0) sx <- 1
    min_distance <- max(1L, floor(fs * 60 / bpm_max * 0.8))

    fits <- lapply(threshold_offsets, function(off) {
      threshold <- ma + off * sx
      pk <- .gp_peak_rois(x, threshold, min_distance)
      duration_min <- diff(range(time, na.rm = TRUE)) / 60
      bpm <- if (length(pk) >= 2L && duration_min > 0) length(pk) / duration_min else NA_real_
      sdsd <- .gp_measure_sdsd(time[pk])
      data.frame(offset = off, n_peaks = length(pk), bpm = bpm, sdsd = sdsd)
    })
    fit_tbl <- do.call(rbind, fits)
    valid <- is.finite(fit_tbl$bpm) & fit_tbl$bpm >= bpm_min & fit_tbl$bpm <= bpm_max & fit_tbl$n_peaks >= 3L
    if (any(valid)) {
      candidates <- fit_tbl[valid, , drop = FALSE]
      best_i <- which.min(ifelse(candidates$sdsd > 0, candidates$sdsd, Inf))
      best_offset <- candidates$offset[best_i]
    } else {
      best_offset <- 0
    }

    threshold <- ma + best_offset * sx
    pk <- .gp_peak_rois(x, threshold, min_distance)

    if (length(pk)) {
      refined <- lapply(pk, function(p) {
        if (isTRUE(high_precision)) .gp_high_precision_peak(x, time, p) else list(time = time[p], value = x[p])
      })
      peak_time <- vapply(refined, `[[`, numeric(1), "time")
      peak_value <- vapply(refined, `[[`, numeric(1), "value")
    } else {
      peak_time <- numeric()
      peak_value <- numeric()
    }

    peak_df <- data.frame(
      group = g,
      peak_index = pk,
      peak_time_s = peak_time,
      peak_value = peak_value,
      accepted = TRUE
    )
    if (!is.null(group_cols) && length(group_cols) && nrow(peak_df)) {
      vals <- d[rep(1L, nrow(peak_df)), group_cols, drop = FALSE]
      peak_df <- cbind(vals, peak_df)
    }

    sig_df <- data.frame(
      group = g,
      sample_index = seq_along(x),
      time_s = time,
      signal_raw = x0,
      signal_processed = x,
      moving_average = ma,
      threshold = threshold,
      clipped = clip$clipped
    )
    if (!is.null(group_cols) && length(group_cols)) {
      vals <- d[, group_cols, drop = FALSE]
      sig_df <- cbind(vals, sig_df)
    }

    peak_list[[g]] <- peak_df
    signal_list[[g]] <- sig_df
    diag_list[[g]] <- data.frame(
      group = g,
      sampling_rate_hz = fs,
      best_offset = best_offset,
      n_peaks = length(pk),
      clipped_samples = sum(clip$clipped),
      stringsAsFactors = FALSE
    )
  }

  peaks <- do.call(rbind, peak_list)
  signals <- do.call(rbind, signal_list)
  diagnostics <- do.call(rbind, diag_list)
  row.names(peaks) <- NULL
  row.names(signals) <- NULL
  row.names(diagnostics) <- NULL

  list(
    peaks = peaks,
    processed_signal = signals,
    diagnostics = diagnostics,
    settings = list(
      sampling_rate_hz = fs, bpm_min = bpm_min, bpm_max = bpm_max,
      moving_average_seconds = moving_average_seconds,
      reconstruct_clipping = reconstruct_clipping, enhance_peaks = enhance_peaks,
      lowpass_hz = lowpass_hz, hampel = hampel, high_precision = high_precision
    )
  )
}

#' Reject implausible pulse/PPG peaks using RR-interval thresholds
#' @param peaks Peak table returned by detect_gazepoint_ppg_peaks().
#' @param group_col Group column.
#' @param rr_tolerance Proportional RR tolerance around the group mean.
#' @param min_rr_ms Minimum absolute tolerance in milliseconds.
#' @return Peak table with accepted and rr_ms columns.
#' @export
reject_gazepoint_ppg_peaks <- function(peaks, group_col = "group", rr_tolerance = 0.30, min_rr_ms = 300) {
  if (!is.data.frame(peaks) || !nrow(peaks)) return(peaks)
  if (!"peak_time_s" %in% names(peaks)) stop("`peaks` must contain `peak_time_s`.", call. = FALSE)
  if (!group_col %in% names(peaks)) peaks[[group_col]] <- "all"

  out <- peaks[order(peaks[[group_col]], peaks$peak_time_s), , drop = FALSE]
  out$rr_ms <- NA_real_
  out$accepted <- TRUE

  for (g in unique(out[[group_col]])) {
    idx <- which(out[[group_col]] == g)
    if (length(idx) < 3L) next
    rr <- c(NA_real_, diff(out$peak_time_s[idx]) * 1000)
    rr_mean <- mean(rr, na.rm = TRUE)
    tol <- max(rr_tolerance * rr_mean, min_rr_ms)
    bad_interval <- is.finite(rr) & (rr < rr_mean - tol | rr > rr_mean + tol)
    out$rr_ms[idx] <- rr
    out$accepted[idx[bad_interval]] <- FALSE
  }
  row.names(out) <- NULL
  out
}

#' Compute HeartPy-style pulse/PPG measures
#' @param peaks Peak table from detect_gazepoint_ppg_peaks() or reject_gazepoint_ppg_peaks().
#' @param group_col Group column.
#' @return Data frame with BPM, IBI, SDNN, SDSD, RMSSD, pNN20, pNN50, MAD, LF, HF, HF/LF, and breathing rate.
#' @export
compute_gazepoint_ppg_measures <- function(peaks, group_col = "group") {
  if (!is.data.frame(peaks) || !nrow(peaks)) return(data.frame())
  if (!"peak_time_s" %in% names(peaks)) stop("`peaks` must contain `peak_time_s`.", call. = FALSE)
  if (!"accepted" %in% names(peaks)) peaks$accepted <- TRUE
  if (!group_col %in% names(peaks)) peaks[[group_col]] <- "all"

  groups <- split(peaks, peaks[[group_col]])
  out <- lapply(names(groups), function(g) {
    d <- groups[[g]]
    d <- d[isTRUE(TRUE) & d$accepted %in% TRUE & is.finite(d$peak_time_s), , drop = FALSE]
    d <- d[order(d$peak_time_s), , drop = FALSE]
    if (nrow(d) < 3L) {
      return(data.frame(group = g, n_peaks = nrow(d), bpm = NA_real_, ibi_ms = NA_real_, sdnn_ms = NA_real_, sdsd_ms = NA_real_, rmssd_ms = NA_real_, pnn20 = NA_real_, pnn50 = NA_real_, mad_rr_ms = NA_real_, lf = NA_real_, hf = NA_real_, hf_lf = NA_real_, breathing_rate_hz = NA_real_))
    }
    rr <- diff(d$peak_time_s) * 1000
    dr <- diff(rr)
    duration_min <- diff(range(d$peak_time_s)) / 60
    spec <- .gp_spectral_rr(rr, cumsum(rr) / 1000)
    lf <- .gp_band_power(spec$freq, spec$psd, 0.05, 0.15)
    hf <- .gp_band_power(spec$freq, spec$psd, 0.15, 0.50)
    br <- estimate_gazepoint_breathing_rate_from_ibi(rr_ms = rr)
    data.frame(
      group = g,
      n_peaks = nrow(d),
      bpm = if (duration_min > 0) nrow(d) / duration_min else NA_real_,
      ibi_ms = mean(rr, na.rm = TRUE),
      sdnn_ms = stats::sd(rr, na.rm = TRUE),
      sdsd_ms = stats::sd(dr, na.rm = TRUE),
      rmssd_ms = sqrt(mean(dr^2, na.rm = TRUE)),
      pnn20 = mean(abs(dr) > 20, na.rm = TRUE),
      pnn50 = mean(abs(dr) > 50, na.rm = TRUE),
      mad_rr_ms = stats::mad(rr, constant = 1.4826, na.rm = TRUE),
      lf = lf,
      hf = hf,
      hf_lf = if (is.finite(lf) && lf > 0) hf / lf else NA_real_,
      breathing_rate_hz = br$breathing_rate_hz
    )
  })
  out <- do.call(rbind, out)
  row.names(out) <- NULL
  out
}

#' Estimate breathing rate from RR/IBI frequency content
#' @param rr_ms RR or IBI intervals in milliseconds.
#' @param rr_time_s Optional interval time stamps in seconds.
#' @param resample_hz Interpolation frequency.
#' @param breathing_band Frequency band for breathing-rate search.
#' @return A list with breathing_rate_hz, frequency, psd, and band.
#' @export
estimate_gazepoint_breathing_rate_from_ibi <- function(rr_ms, rr_time_s = NULL, resample_hz = 4, breathing_band = c(0.10, 0.50)) {
  spec <- .gp_spectral_rr(rr_ms, rr_time_s, resample_hz = resample_hz)
  if (!length(spec$freq)) {
    return(list(breathing_rate_hz = NA_real_, frequency = spec$freq, psd = spec$psd, band = breathing_band))
  }
  keep <- spec$freq >= breathing_band[1] & spec$freq <= breathing_band[2] & is.finite(spec$psd)
  if (!any(keep)) {
    return(list(breathing_rate_hz = NA_real_, frequency = spec$freq, psd = spec$psd, band = breathing_band))
  }
  f <- spec$freq[keep]
  p <- spec$psd[keep]
  list(breathing_rate_hz = f[which.max(p)], frequency = spec$freq, psd = spec$psd, band = breathing_band)
}

#' Plot Gazepoint pulse/PPG peak detection results
#' @param detection Detection object returned by detect_gazepoint_ppg_peaks().
#' @param group Optional group to plot.
#' @param accepted_only Whether to show only accepted peaks.
#' @return Invisibly returns the plotted data.
#' @export
plot_gazepoint_ppg_peak_detection <- function(detection, group = NULL, accepted_only = FALSE) {
  if (!is.list(detection) || is.null(detection$processed_signal) || is.null(detection$peaks)) {
    stop("`detection` must be returned by detect_gazepoint_ppg_peaks().", call. = FALSE)
  }
  sig <- detection$processed_signal
  pk <- detection$peaks
  if (!is.null(group)) {
    sig <- sig[sig$group == group, , drop = FALSE]
    pk <- pk[pk$group == group, , drop = FALSE]
  }
  if (isTRUE(accepted_only) && "accepted" %in% names(pk)) pk <- pk[pk$accepted, , drop = FALSE]
  graphics::plot(sig$time_s, sig$signal_processed, type = "l", xlab = "Time (s)", ylab = "Processed pulse/PPG", main = "Gazepoint pulse/PPG peak detection")
  graphics::lines(sig$time_s, sig$moving_average, lty = 2)
  graphics::lines(sig$time_s, sig$threshold, lty = 3)
  if (nrow(pk)) graphics::points(pk$peak_time_s, pk$peak_value, pch = 19)
  invisible(list(signal = sig, peaks = pk))
}

#' Create HeartPy-style report tables for Gazepoint pulse/PPG data
#' @param detection Detection object returned by detect_gazepoint_ppg_peaks().
#' @param output_dir Optional output directory. If NULL, no files are written.
#' @param prefix File prefix when output_dir is supplied.
#' @return A list with peaks, measures, diagnostics, and paths.
#' @export
create_gazepoint_heartpy_report <- function(detection, output_dir = NULL, prefix = "gazepoint_heartpy") {
  if (!is.list(detection) || is.null(detection$peaks)) stop("Invalid detection object.", call. = FALSE)
  rejected <- reject_gazepoint_ppg_peaks(detection$peaks)
  measures <- compute_gazepoint_ppg_measures(rejected)
  diagnostics <- detection$diagnostics
  paths <- character()

  if (!is.null(output_dir)) {
    if (!is.character(output_dir) || length(output_dir) != 1L || !nzchar(output_dir)) {
      stop("`output_dir` must be NULL or a single non-empty character value.", call. = FALSE)
    }
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
    peak_file <- file.path(output_dir, paste0(prefix, "_peaks.csv"))
    measure_file <- file.path(output_dir, paste0(prefix, "_measures.csv"))
    diag_file <- file.path(output_dir, paste0(prefix, "_diagnostics.csv"))
    txt_file <- file.path(output_dir, paste0(prefix, "_report.txt"))
    utils::write.csv(rejected, peak_file, row.names = FALSE)
    utils::write.csv(measures, measure_file, row.names = FALSE)
    utils::write.csv(diagnostics, diag_file, row.names = FALSE)
    lines <- c(
      "Gazepoint HeartPy-style pulse/PPG report",
      paste0("Generated: ", Sys.time()),
      paste0("Groups: ", length(unique(rejected$group))),
      paste0("Peaks: ", nrow(rejected))
    )
    writeLines(lines, txt_file, useBytes = TRUE)
    paths <- normalizePath(c(peak_file, measure_file, diag_file, txt_file), winslash = "/", mustWork = FALSE)
  }

  list(peaks = rejected, measures = measures, diagnostics = diagnostics, path = paths)
}

#' Run a Gazepoint pulse/PPG cross-check against HeartPy when available
#'
#' If Python HeartPy is available through reticulate, this function attempts to run
#' heartpy.process() on the first group. Otherwise it returns native Gazepoint
#' HeartPy-style results only.
#' @param data Data frame containing Gazepoint pulse/PPG samples.
#' @param signal_col Signal column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param ... Additional arguments passed to detect_gazepoint_ppg_peaks().
#' @return A list with native, heartpy, and heartpy_available.
#' @export
run_gazepoint_heartpy_crosscheck <- function(data, signal_col = NULL, time_col = NULL, group_cols = NULL, sampling_rate_hz = NULL, ...) {
  native <- detect_gazepoint_ppg_peaks(
    data = data, signal_col = signal_col, time_col = time_col,
    group_cols = group_cols, sampling_rate_hz = sampling_rate_hz, ...
  )
  report <- create_gazepoint_heartpy_report(native)

  hp_result <- NULL
  hp_available <- FALSE
  if (requireNamespace("reticulate", quietly = TRUE)) {
    hp_available <- tryCatch(reticulate::py_module_available("heartpy"), error = function(e) FALSE)
    if (isTRUE(hp_available)) {
      hp_result <- tryCatch({
        hp <- reticulate::import("heartpy", delay_load = TRUE)
        sig <- native$processed_signal$signal_raw
        fs <- native$settings$sampling_rate_hz
        res <- hp$process(as.numeric(sig), as.numeric(fs), report_time = FALSE)
        list(working_data = res[[1]], measures = res[[2]])
      }, error = function(e) list(error = conditionMessage(e)))
    }
  }

  list(
    native = report,
    heartpy = hp_result,
    heartpy_available = hp_available
  )
}
