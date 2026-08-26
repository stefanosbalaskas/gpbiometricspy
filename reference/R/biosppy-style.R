
# BioSPPy-style Gazepoint biosignal helpers
#
# Gazepoint-native R helpers inspired by BioSPPy-style EDA, PPG/BVP,
# RRI, and generic signal-processing workflows. These functions are not
# wrappers around BioSPPy and make no clinical or diagnostic claims.

.gp_biosppy_num <- function(x) {
  suppressWarnings(as.numeric(x))
}

.gp_biosppy_pick_col <- function(data, candidates, label) {
  hits <- candidates[candidates %in% names(data)]
  if (!length(hits)) {
    stop("Could not infer ", label, " column. Please supply it explicitly.", call. = FALSE)
  }
  hits[1]
}

.gp_biosppy_interp_na <- function(x) {
  x <- .gp_biosppy_num(x)

  if (!length(x)) {
    return(x)
  }

  ok <- is.finite(x)

  if (!any(ok)) {
    return(rep(NA_real_, length(x)))
  }

  if (all(ok)) {
    return(x)
  }

  stats::approx(
    x = which(ok),
    y = x[ok],
    xout = seq_along(x),
    rule = 2
  )$y
}

.gp_biosppy_running_mean <- function(x, k) {
  x <- .gp_biosppy_interp_na(x)
  k <- max(1L, as.integer(k))

  if (k <= 1L) {
    return(x)
  }

  y <- as.numeric(stats::filter(x, rep(1 / k, k), sides = 2))
  miss <- !is.finite(y)

  if (any(miss)) {
    y[miss] <- x[miss]
  }

  y
}

.gp_biosppy_running_median <- function(x, k) {
  x <- .gp_biosppy_interp_na(x)
  k <- max(3L, as.integer(k))
  n <- length(x)
  h <- floor(k / 2)

  vapply(seq_len(n), function(i) {
    lo <- max(1L, i - h)
    hi <- min(n, i + h)
    stats::median(x[lo:hi], na.rm = TRUE)
  }, numeric(1))
}

.gp_biosppy_prepare_signal <- function(data,
                                       signal_col = NULL,
                                       time_col = NULL,
                                       group_cols = NULL,
                                       sampling_rate_hz = NULL,
                                       candidates = c("EDA", "GSR", "PPG", "BVP", "PULSE", "signal")) {
  if (is.numeric(data) && is.null(dim(data))) {
    if (is.null(sampling_rate_hz) || !is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
      stop("`sampling_rate_hz` is required for numeric input.", call. = FALSE)
    }

    out <- data.frame(
      time_s = (seq_along(data) - 1) / sampling_rate_hz,
      signal = .gp_biosppy_num(data),
      group = "all",
      stringsAsFactors = FALSE
    )

    return(list(
      data = out,
      signal_col = "signal",
      time_col = "time_s",
      group_cols = "group",
      sampling_rate_hz = sampling_rate_hz
    ))
  }

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame or numeric vector.", call. = FALSE)
  }

  if (is.null(signal_col)) {
    signal_col <- .gp_biosppy_pick_col(data, candidates, "signal")
  }

  if (!signal_col %in% names(data)) {
    stop("`signal_col` not found.", call. = FALSE)
  }

  out <- data

  if (is.null(time_col)) {
    if (is.null(sampling_rate_hz) || !is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
      stop("Supply `time_col` or `sampling_rate_hz`.", call. = FALSE)
    }

    time_col <- "time_s"
    out[[time_col]] <- (seq_len(nrow(out)) - 1) / sampling_rate_hz
  } else if (!time_col %in% names(out)) {
    stop("`time_col` not found.", call. = FALSE)
  }

  if (is.null(group_cols) || !length(group_cols)) {
    group_cols <- "group"
    out[[group_cols]] <- "all"
  } else {
    missing <- setdiff(group_cols, names(out))
    if (length(missing)) {
      stop("Missing group columns: ", paste(missing, collapse = ", "), call. = FALSE)
    }
  }

  out[[signal_col]] <- .gp_biosppy_num(out[[signal_col]])
  out[[time_col]] <- .gp_biosppy_num(out[[time_col]])

  if (is.null(sampling_rate_hz)) {
    dt <- diff(sort(unique(out[[time_col]][is.finite(out[[time_col]])])))
    dt <- dt[is.finite(dt) & dt > 0]
    sampling_rate_hz <- if (length(dt)) 1 / stats::median(dt) else NA_real_
  }

  list(
    data = out,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz
  )
}

.gp_biosppy_group_index <- function(data, group_cols) {
  if (is.null(group_cols) || !length(group_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  g <- interaction(data[group_cols], drop = TRUE, sep = " | ")
  split(seq_len(nrow(data)), g)
}

.gp_biosppy_local_maxima <- function(x) {
  x <- .gp_biosppy_num(x)

  if (length(x) < 3L) {
    return(integer())
  }

  which(
    x[-c(1L, length(x))] > x[-c(length(x) - 1L, length(x))] &
      x[-c(1L, 2L)] <= x[-c(1L, length(x))]
  ) + 1L
}

.gp_biosppy_peak_filter_refractory <- function(idx, score, refractory_samples) {
  if (!length(idx)) {
    return(integer())
  }

  idx <- as.integer(idx)
  score <- .gp_biosppy_num(score)

  o <- order(score, decreasing = TRUE)
  idx_sorted <- idx[o]

  keep <- logical(length(idx_sorted))

  for (i in seq_along(idx_sorted)) {
    if (!any(keep)) {
      keep[i] <- TRUE
    } else {
      keep[i] <- all(abs(idx_sorted[i] - idx_sorted[keep]) > refractory_samples)
    }
  }

  sort(idx_sorted[keep])
}

.gp_biosppy_bandpass_fft <- function(x, sampling_rate_hz, low_hz = NULL, high_hz = NULL) {
  x <- .gp_biosppy_interp_na(x)
  n <- length(x)

  if (n < 4L) {
    return(x)
  }

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Invalid sampling rate.", call. = FALSE)
  }

  y <- x - mean(x, na.rm = TRUE)
  fy <- stats::fft(y)
  freq <- (seq_len(n) - 1L) * sampling_rate_hz / n
  freq2 <- ifelse(freq > sampling_rate_hz / 2, sampling_rate_hz - freq, freq)

  keep <- rep(TRUE, n)

  if (!is.null(low_hz)) {
    keep <- keep & freq2 >= low_hz
  }

  if (!is.null(high_hz)) {
    keep <- keep & freq2 <= high_hz
  }

  fy[!keep] <- 0
  Re(stats::fft(fy, inverse = TRUE) / n)
}

.gp_biosppy_template_matrix <- function(signal, centers, pre_samples, post_samples) {
  signal <- .gp_biosppy_num(signal)
  centers <- as.integer(centers)
  width <- pre_samples + post_samples + 1L

  rows <- lapply(centers, function(cn) {
    idx <- (cn - pre_samples):(cn + post_samples)

    if (min(idx) < 1L || max(idx) > length(signal)) {
      return(NULL)
    }

    signal[idx]
  })

  rows <- rows[!vapply(rows, is.null, logical(1))]

  if (!length(rows)) {
    return(matrix(numeric(), nrow = 0L, ncol = width))
  }

  do.call(rbind, rows)
}

.gp_biosppy_peak_indices <- function(peaks, time, n) {
  if (is.data.frame(peaks)) {
    if ("peak_index" %in% names(peaks)) {
      idx <- as.integer(peaks$peak_index)
    } else if ("sample_index" %in% names(peaks)) {
      idx <- as.integer(peaks$sample_index)
    } else if ("peak_time_s" %in% names(peaks)) {
      idx <- vapply(peaks$peak_time_s, function(tt) which.min(abs(time - tt)), integer(1))
    } else {
      stop("Peak table must contain peak_index, sample_index, or peak_time_s.", call. = FALSE)
    }

    group <- if ("group" %in% names(peaks)) as.character(peaks$group) else rep("all", length(idx))
  } else {
    idx <- as.integer(peaks)
    group <- rep("all", length(idx))
  }

  valid <- is.finite(idx) & idx >= 1L & idx <= n

  list(
    index = idx[valid],
    group = group[valid]
  )
}

.gp_biosppy_first_after <- function(x, threshold) {
  idx <- which(x <= threshold)
  if (length(idx)) idx[1] else NA_integer_
}

#' Extract BioSPPy-style EDA events from Gazepoint GSR/EDA data
#'
#' @param data Data frame or numeric EDA/GSR signal.
#' @param signal_col EDA/GSR column.
#' @param time_col Optional time column in seconds.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param smoothing_seconds Smoothing window for tonic estimate.
#' @param min_amplitude Minimum SCR amplitude.
#' @param min_distance_seconds Minimum distance between SCR peaks.
#' @param onset_window_seconds Window before peak used to find onset.
#' @return Data frame of EDA events.
#' @export
extract_gazepoint_eda_events_biosppy_style <- function(data,
                                                       signal_col = NULL,
                                                       time_col = NULL,
                                                       group_cols = NULL,
                                                       sampling_rate_hz = NULL,
                                                       smoothing_seconds = 1,
                                                       min_amplitude = NULL,
                                                       min_distance_seconds = 1,
                                                       onset_window_seconds = 4) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("EDA", "GSR", "eda", "gsr", "SCR", "signal")
  )

  d <- prep$data
  fs <- prep$sampling_rate_hz

  if (!is.finite(fs) || fs <= 0) {
    stop("Could not infer a valid sampling rate.", call. = FALSE)
  }

  groups <- .gp_biosppy_group_index(d, prep$group_cols)
  out <- list()

  for (g in names(groups)) {
    idx <- groups[[g]]
    dd <- d[idx, , drop = FALSE]

    sig <- .gp_biosppy_interp_na(dd[[prep$signal_col]])
    time <- dd[[prep$time_col]]

    tonic <- .gp_biosppy_running_median(sig, max(3L, round(smoothing_seconds * fs)))
    phasic <- sig - tonic
    phasic_smooth <- .gp_biosppy_running_mean(phasic, max(3L, round(0.25 * fs)))

    cand <- .gp_biosppy_local_maxima(phasic_smooth)

    amp_threshold <- min_amplitude
    if (is.null(amp_threshold)) {
      amp_threshold <- max(
        0.01,
        stats::median(abs(phasic_smooth), na.rm = TRUE) +
          stats::mad(phasic_smooth, na.rm = TRUE)
      )
    }

    cand <- cand[is.finite(phasic_smooth[cand]) & phasic_smooth[cand] >= amp_threshold]

    if (length(cand)) {
      cand <- .gp_biosppy_peak_filter_refractory(
        cand,
        score = phasic_smooth[cand],
        refractory_samples = max(1L, round(min_distance_seconds * fs))
      )
    }

    if (!length(cand)) {
      next
    }

    events <- lapply(seq_along(cand), function(j) {
      peak_i <- cand[j]
      win_start <- max(1L, peak_i - round(onset_window_seconds * fs))
      onset_i <- win_start - 1L + which.min(phasic_smooth[win_start:peak_i])
      amp <- phasic_smooth[peak_i] - phasic_smooth[onset_i]

      data.frame(
        group = g,
        event_id = j,
        onset_index = idx[onset_i],
        peak_index = idx[peak_i],
        onset_time_s = time[onset_i],
        peak_time_s = time[peak_i],
        rise_time_s = time[peak_i] - time[onset_i],
        amplitude = amp,
        tonic_at_peak = tonic[peak_i],
        phasic_peak = phasic_smooth[peak_i],
        stringsAsFactors = FALSE
      )
    })

    out[[length(out) + 1L]] <- do.call(rbind, events)
  }

  if (!length(out)) {
    return(data.frame())
  }

  ans <- do.call(rbind, out)
  row.names(ans) <- NULL
  ans
}

#' Estimate BioSPPy-style EDA recovery times
#'
#' @param data Data frame or numeric EDA/GSR signal.
#' @param events Optional event table from extract_gazepoint_eda_events_biosppy_style().
#' @param signal_col EDA/GSR column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param recovery_prop Proportion of amplitude used for recovery threshold.
#' @param max_recovery_seconds Maximum search window after peak.
#' @return Event table with recovery-time columns.
#' @export
estimate_gazepoint_eda_recovery_times <- function(data,
                                                  events = NULL,
                                                  signal_col = NULL,
                                                  time_col = NULL,
                                                  group_cols = NULL,
                                                  sampling_rate_hz = NULL,
                                                  recovery_prop = 0.5,
                                                  max_recovery_seconds = 10) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("EDA", "GSR", "eda", "gsr", "SCR", "signal")
  )

  if (is.null(events)) {
    events <- extract_gazepoint_eda_events_biosppy_style(
      prep$data,
      signal_col = prep$signal_col,
      time_col = prep$time_col,
      group_cols = prep$group_cols,
      sampling_rate_hz = prep$sampling_rate_hz
    )
  }

  if (!is.data.frame(events) || !nrow(events)) {
    return(data.frame())
  }

  d <- prep$data
  fs <- prep$sampling_rate_hz
  sig <- .gp_biosppy_interp_na(d[[prep$signal_col]])
  time <- d[[prep$time_col]]

  events$recovery_time_s <- NA_real_
  events$recovery_index <- NA_integer_
  events$recovery_timepoint_s <- NA_real_

  for (i in seq_len(nrow(events))) {
    peak_pos <- events$peak_index[i]
    onset_pos <- events$onset_index[i]

    if (!is.finite(peak_pos) || !is.finite(onset_pos)) {
      next
    }

    if (peak_pos < 1L || peak_pos > length(sig) || onset_pos < 1L || onset_pos > length(sig)) {
      next
    }

    baseline <- sig[onset_pos]
    peak_value <- sig[peak_pos]
    threshold <- baseline + recovery_prop * (peak_value - baseline)

    max_i <- min(length(sig), peak_pos + round(max_recovery_seconds * fs))
    segment <- sig[peak_pos:max_i]
    rel <- .gp_biosppy_first_after(segment, threshold)

    if (is.finite(rel)) {
      rec_pos <- peak_pos + rel - 1L
      events$recovery_index[i] <- rec_pos
      events$recovery_timepoint_s[i] <- time[rec_pos]
      events$recovery_time_s[i] <- time[rec_pos] - events$peak_time_s[i]
    }
  }

  events
}

#' Run BioSPPy-style Gazepoint EDA processing
#'
#' @param data Data frame or numeric EDA/GSR signal.
#' @param signal_col EDA/GSR column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param smoothing_seconds Window used for tonic smoothing.
#' @return List with raw table, tonic, phasic, events, and recovery estimates.
#' @export
run_gazepoint_biosppy_eda <- function(data,
                                      signal_col = NULL,
                                      time_col = NULL,
                                      group_cols = NULL,
                                      sampling_rate_hz = NULL,
                                      smoothing_seconds = 4) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("EDA", "GSR", "eda", "gsr", "SCR", "signal")
  )

  d <- prep$data
  fs <- prep$sampling_rate_hz

  if (!is.finite(fs) || fs <= 0) {
    stop("Could not infer a valid sampling rate.", call. = FALSE)
  }

  groups <- .gp_biosppy_group_index(d, prep$group_cols)

  tonic <- rep(NA_real_, nrow(d))
  phasic <- rep(NA_real_, nrow(d))

  for (idx in groups) {
    sig <- .gp_biosppy_interp_na(d[[prep$signal_col]][idx])
    tonic[idx] <- .gp_biosppy_running_median(sig, max(3L, round(smoothing_seconds * fs)))
    phasic[idx] <- sig - tonic[idx]
  }

  signal_table <- data.frame(
    d,
    eda_raw = d[[prep$signal_col]],
    eda_tonic = tonic,
    eda_phasic = phasic
  )

  events <- extract_gazepoint_eda_events_biosppy_style(
    d,
    signal_col = prep$signal_col,
    time_col = prep$time_col,
    group_cols = prep$group_cols,
    sampling_rate_hz = fs
  )

  recovery <- estimate_gazepoint_eda_recovery_times(
    d,
    events = events,
    signal_col = prep$signal_col,
    time_col = prep$time_col,
    group_cols = prep$group_cols,
    sampling_rate_hz = fs
  )

  summary <- data.frame(
    n_samples = nrow(d),
    sampling_rate_hz = fs,
    n_events = nrow(events),
    mean_phasic = mean(phasic, na.rm = TRUE),
    sd_phasic = stats::sd(phasic, na.rm = TRUE),
    mean_tonic = mean(tonic, na.rm = TRUE)
  )

  list(
    signal = signal_table,
    events = events,
    recovery = recovery,
    summary = summary,
    settings = list(sampling_rate_hz = fs, smoothing_seconds = smoothing_seconds)
  )
}

#' Detect BioSPPy-style PPG pulse onsets
#'
#' @param data Data frame or numeric PPG/BVP signal.
#' @param signal_col PPG/BVP column.
#' @param time_col Optional time column.
#' @param peaks Optional peak table or peak indices.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param search_seconds Seconds before peak used to find onset.
#' @return Data frame of onsets.
#' @export
detect_gazepoint_ppg_onsets <- function(data,
                                        signal_col = NULL,
                                        time_col = NULL,
                                        peaks = NULL,
                                        group_cols = NULL,
                                        sampling_rate_hz = NULL,
                                        search_seconds = 0.6) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("PPG", "BVP", "PULSE", "HRP", "pulse", "signal")
  )

  d <- prep$data
  fs <- prep$sampling_rate_hz
  sig <- .gp_biosppy_interp_na(d[[prep$signal_col]])

  if (is.null(peaks)) {
    det <- detect_gazepoint_ppg_peaks(
      d,
      signal_col = prep$signal_col,
      time_col = prep$time_col,
      group_cols = prep$group_cols,
      sampling_rate_hz = fs,
      high_precision = FALSE
    )
    peaks <- det$peaks
  }

  pk <- .gp_biosppy_peak_indices(peaks, time = d[[prep$time_col]], n = length(sig))
  peak_idx <- pk$index

  if (!length(peak_idx)) {
    return(data.frame())
  }

  onsets <- lapply(seq_along(peak_idx), function(i) {
    peak_i <- peak_idx[i]
    lo <- max(1L, peak_i - round(search_seconds * fs))
    seg <- sig[lo:peak_i]
    onset_i <- lo - 1L + which.min(seg)

    data.frame(
      group = pk$group[i],
      beat_id = i,
      onset_index = onset_i,
      onset_time_s = d[[prep$time_col]][onset_i],
      peak_index = peak_i,
      peak_time_s = d[[prep$time_col]][peak_i],
      rise_time_s = d[[prep$time_col]][peak_i] - d[[prep$time_col]][onset_i],
      amplitude = sig[peak_i] - sig[onset_i],
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, onsets)
  row.names(out) <- NULL
  out
}

#' Extract BioSPPy-style PPG pulse templates
#'
#' @param data Data frame or numeric PPG/BVP signal.
#' @param signal_col PPG/BVP column.
#' @param time_col Optional time column.
#' @param peaks Optional peak table or peak indices.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param before_seconds Seconds before peak.
#' @param after_seconds Seconds after peak.
#' @return List with templates, average template, and template time.
#' @export
extract_gazepoint_ppg_templates <- function(data,
                                            signal_col = NULL,
                                            time_col = NULL,
                                            peaks = NULL,
                                            group_cols = NULL,
                                            sampling_rate_hz = NULL,
                                            before_seconds = 0.30,
                                            after_seconds = 0.60) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("PPG", "BVP", "PULSE", "HRP", "pulse", "signal")
  )

  d <- prep$data
  fs <- prep$sampling_rate_hz
  sig <- .gp_biosppy_interp_na(d[[prep$signal_col]])

  if (is.null(peaks)) {
    det <- detect_gazepoint_ppg_peaks(
      d,
      signal_col = prep$signal_col,
      time_col = prep$time_col,
      group_cols = prep$group_cols,
      sampling_rate_hz = fs,
      high_precision = FALSE
    )
    peaks <- det$peaks
  }

  pk <- .gp_biosppy_peak_indices(peaks, time = d[[prep$time_col]], n = length(sig))
  peak_idx <- pk$index

  pre <- max(1L, round(before_seconds * fs))
  post <- max(1L, round(after_seconds * fs))
  mat <- .gp_biosppy_template_matrix(sig, peak_idx, pre, post)

  template_time_s <- (-pre:post) / fs
  avg <- if (nrow(mat)) colMeans(mat, na.rm = TRUE) else rep(NA_real_, length(template_time_s))

  quality <- if (nrow(mat) >= 2L) {
    cors <- suppressWarnings(stats::cor(t(mat), use = "pairwise.complete.obs"))
    mean(cors[upper.tri(cors)], na.rm = TRUE)
  } else {
    NA_real_
  }

  list(
    templates = mat,
    average_template = data.frame(time_s = template_time_s, amplitude = avg),
    template_time_s = template_time_s,
    peak_indices_used = peak_idx,
    template_quality_correlation = quality,
    settings = list(before_seconds = before_seconds, after_seconds = after_seconds, sampling_rate_hz = fs)
  )
}

#' Run BioSPPy-style Gazepoint PPG/BVP processing
#'
#' @param data Data frame or numeric PPG/BVP signal.
#' @param signal_col PPG/BVP column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @return List with filtered signal, peaks, onsets, templates, and heart rate.
#' @export
run_gazepoint_biosppy_ppg <- function(data,
                                      signal_col = NULL,
                                      time_col = NULL,
                                      group_cols = NULL,
                                      sampling_rate_hz = NULL) {
  prep <- .gp_biosppy_prepare_signal(
    data,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz,
    candidates = c("PPG", "BVP", "PULSE", "HRP", "pulse", "signal")
  )

  d <- prep$data
  fs <- prep$sampling_rate_hz

  filtered <- .gp_biosppy_bandpass_fft(d[[prep$signal_col]], fs, low_hz = 0.5, high_hz = 8)
  d$ppg_filtered <- filtered

  det <- detect_gazepoint_ppg_peaks(
    d,
    signal_col = "ppg_filtered",
    time_col = prep$time_col,
    group_cols = prep$group_cols,
    sampling_rate_hz = fs,
    high_precision = FALSE
  )

  peaks <- reject_gazepoint_ppg_peaks(det$peaks)

  onsets <- detect_gazepoint_ppg_onsets(
    d,
    signal_col = "ppg_filtered",
    time_col = prep$time_col,
    peaks = peaks,
    group_cols = prep$group_cols,
    sampling_rate_hz = fs
  )

  templates <- extract_gazepoint_ppg_templates(
    d,
    signal_col = "ppg_filtered",
    time_col = prep$time_col,
    peaks = peaks,
    group_cols = prep$group_cols,
    sampling_rate_hz = fs
  )

  hr <- if (is.data.frame(peaks) && "peak_time_s" %in% names(peaks) && nrow(peaks) >= 2L) {
    data.frame(
      time_s = peaks$peak_time_s[-1L],
      heart_rate_bpm = 60 / diff(peaks$peak_time_s)
    )
  } else {
    data.frame()
  }

  list(
    signal = d,
    peaks = peaks,
    onsets = onsets,
    templates = templates,
    heart_rate = hr,
    settings = list(sampling_rate_hz = fs)
  )
}

#' Detrend RRI/IBI intervals in windows
#'
#' @param rri_ms Numeric RRI/IBI intervals in milliseconds.
#' @param time_s Optional time vector.
#' @param window_seconds Window length for local trend.
#' @param method mean, median, or linear.
#' @return Data frame with original, trend, and detrended RRI.
#' @export
detrend_gazepoint_rri_window <- function(rri_ms,
                                         time_s = NULL,
                                         window_seconds = 60,
                                         method = c("median", "mean", "linear")) {
  method <- match.arg(method)

  rri0 <- .gp_biosppy_num(rri_ms)
  ok <- is.finite(rri0) & rri0 > 0
  rri <- rri0[ok]

  if (is.null(time_s)) {
    time_s <- cumsum(rri) / 1000
  } else {
    time_s <- .gp_biosppy_num(time_s)[ok]
  }

  if (length(rri) < 3L) {
    return(data.frame(
      time_s = time_s,
      rri_ms = rri,
      trend_ms = NA_real_,
      rri_detrended_ms = NA_real_
    ))
  }

  trend <- rep(NA_real_, length(rri))

  for (i in seq_along(rri)) {
    idx <- which(abs(time_s - time_s[i]) <= window_seconds / 2)

    if (method == "median") {
      trend[i] <- stats::median(rri[idx], na.rm = TRUE)
    } else if (method == "mean") {
      trend[i] <- mean(rri[idx], na.rm = TRUE)
    } else {
      if (length(idx) >= 3L) {
        fit <- stats::lm(rri[idx] ~ time_s[idx])
        trend[i] <- stats::predict(fit, newdata = data.frame(time_s = time_s[i]))
      } else {
        trend[i] <- mean(rri[idx], na.rm = TRUE)
      }
    }
  }

  data.frame(
    time_s = time_s,
    rri_ms = rri,
    trend_ms = trend,
    rri_detrended_ms = rri - trend + mean(trend, na.rm = TRUE)
  )
}

#' Correct local RRI/IBI artifacts
#'
#' @param rri_ms Numeric RRI/IBI intervals in milliseconds.
#' @param method local_median, quotient, or zscore.
#' @param window_intervals Local window in intervals.
#' @param threshold Threshold for artifact detection.
#' @param replacement Replacement method: local_median or interpolate.
#' @return Data frame with corrected RRI values and artifact flags.
#' @export
correct_gazepoint_rri_artifacts_local <- function(rri_ms,
                                                  method = c("local_median", "quotient", "zscore"),
                                                  window_intervals = 5L,
                                                  threshold = 0.20,
                                                  replacement = c("local_median", "interpolate")) {
  method <- match.arg(method)
  replacement <- match.arg(replacement)

  rri <- .gp_biosppy_num(rri_ms)
  n <- length(rri)

  artifact <- !is.finite(rri) | rri <= 0
  reason <- ifelse(artifact, "nonfinite_or_nonpositive", "accepted")

  if (n >= 3L) {
    if (method == "local_median") {
      for (i in seq_len(n)) {
        lo <- max(1L, i - window_intervals)
        hi <- min(n, i + window_intervals)
        med <- stats::median(rri[lo:hi], na.rm = TRUE)

        if (is.finite(med) && med > 0 && is.finite(rri[i])) {
          bad <- abs(rri[i] - med) / med > threshold
          if (bad) {
            artifact[i] <- TRUE
            reason[i] <- "local_median_threshold"
          }
        }
      }
    }

    if (method == "quotient") {
      ratio <- rep(1, n)
      ratio[-1L] <- pmin(rri[-1L] / rri[-n], rri[-n] / rri[-1L])
      bad <- is.finite(ratio) & ratio < (1 - threshold)
      artifact[bad] <- TRUE
      reason[bad] <- "quotient_threshold"
    }

    if (method == "zscore") {
      s <- stats::sd(rri, na.rm = TRUE)
      if (is.finite(s) && s > 0) {
        z <- (rri - mean(rri, na.rm = TRUE)) / s
        bad <- is.finite(z) & abs(z) > 3.5
        artifact[bad] <- TRUE
        reason[bad] <- "zscore_threshold"
      }
    }
  }

  corrected <- rri

  if (any(artifact)) {
    if (replacement == "local_median") {
      for (i in which(artifact)) {
        lo <- max(1L, i - window_intervals)
        hi <- min(n, i + window_intervals)
        repl <- stats::median(rri[lo:hi][!artifact[lo:hi]], na.rm = TRUE)
        corrected[i] <- if (is.finite(repl)) repl else NA_real_
      }
    } else {
      ok <- !artifact & is.finite(rri)
      if (sum(ok) >= 2L) {
        corrected[artifact] <- stats::approx(which(ok), rri[ok], xout = which(artifact), rule = 2)$y
      }
    }
  }

  data.frame(
    index = seq_along(rri),
    rri_ms = rri,
    rri_corrected_ms = corrected,
    artifact = artifact,
    reason = reason
  )
}

#' Compute signal power spectrum
#'
#' @param x Numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param detrend If TRUE, remove the mean before FFT.
#' @return Data frame with frequency and power.
#' @export
compute_gazepoint_signal_power_spectrum <- function(x,
                                                    sampling_rate_hz,
                                                    detrend = TRUE) {
  x <- .gp_biosppy_interp_na(x)

  if (!is.finite(sampling_rate_hz) || sampling_rate_hz <= 0) {
    stop("Invalid sampling rate.", call. = FALSE)
  }

  n <- length(x)

  if (n < 4L) {
    return(data.frame(frequency_hz = numeric(), power = numeric()))
  }

  if (isTRUE(detrend)) {
    x <- x - mean(x, na.rm = TRUE)
  }

  fy <- stats::fft(x)
  power <- (Mod(fy)^2) / (n * sampling_rate_hz)
  freq <- (seq_len(n) - 1L) * sampling_rate_hz / n
  keep <- seq_len(floor(n / 2L))

  data.frame(
    frequency_hz = freq[keep],
    power = power[keep]
  )
}

#' Compute signal band power
#'
#' @param x Numeric signal or power-spectrum data frame.
#' @param sampling_rate_hz Sampling rate in Hz when x is a signal.
#' @param bands Named list of frequency bands.
#' @param relative If TRUE, include relative band power.
#' @return Data frame of band powers.
#' @export
compute_gazepoint_signal_band_power <- function(x,
                                                sampling_rate_hz = NULL,
                                                bands = list(
                                                  very_low = c(0.003, 0.04),
                                                  low = c(0.04, 0.15),
                                                  high = c(0.15, 0.40)
                                                ),
                                                relative = TRUE) {
  if (is.data.frame(x) && all(c("frequency_hz", "power") %in% names(x))) {
    psd <- x
  } else {
    if (is.null(sampling_rate_hz)) {
      stop("`sampling_rate_hz` is required when `x` is a signal.", call. = FALSE)
    }
    psd <- compute_gazepoint_signal_power_spectrum(x, sampling_rate_hz)
  }

  total <- sum(psd$power[is.finite(psd$power)], na.rm = TRUE)

  out <- lapply(names(bands), function(nm) {
    b <- bands[[nm]]
    keep <- psd$frequency_hz >= b[1] & psd$frequency_hz < b[2]
    p <- sum(psd$power[keep], na.rm = TRUE)

    data.frame(
      band = nm,
      low_hz = b[1],
      high_hz = b[2],
      power = p,
      relative_power = if (isTRUE(relative) && total > 0) p / total else NA_real_
    )
  })

  out <- do.call(rbind, out)
  row.names(out) <- NULL
  out
}

#' Compute phase-locking value between two signals
#'
#' @param x First numeric signal.
#' @param y Second numeric signal.
#' @param sampling_rate_hz Sampling rate in Hz.
#' @param band Optional two-element frequency band.
#' @return Data frame with phase-locking value and circular phase difference.
#' @export
compute_gazepoint_signal_phase_locking <- function(x,
                                                   y,
                                                   sampling_rate_hz,
                                                   band = NULL) {
  x <- .gp_biosppy_interp_na(x)
  y <- .gp_biosppy_interp_na(y)

  n <- min(length(x), length(y))
  x <- x[seq_len(n)]
  y <- y[seq_len(n)]

  if (!is.null(band)) {
    x <- .gp_biosppy_bandpass_fft(x, sampling_rate_hz, low_hz = band[1], high_hz = band[2])
    y <- .gp_biosppy_bandpass_fft(y, sampling_rate_hz, low_hz = band[1], high_hz = band[2])
  }

  phase_from_fft <- function(z) {
    n <- length(z)
    hz <- stats::fft(z - mean(z, na.rm = TRUE))
    h <- hz
    h[] <- 0

    if (n %% 2 == 0) {
      h[1] <- hz[1]
      h[2:(n / 2)] <- 2 * hz[2:(n / 2)]
      h[(n / 2) + 1L] <- hz[(n / 2) + 1L]
    } else {
      h[1] <- hz[1]
      h[2:((n + 1L) / 2)] <- 2 * hz[2:((n + 1L) / 2)]
    }

    analytic <- stats::fft(h, inverse = TRUE) / n
    atan2(Im(analytic), Re(analytic))
  }

  px <- phase_from_fft(x)
  py <- phase_from_fft(y)
  diff_phase <- px - py

  plv <- Mod(mean(exp(1i * diff_phase), na.rm = TRUE))
  mean_diff <- atan2(mean(sin(diff_phase), na.rm = TRUE), mean(cos(diff_phase), na.rm = TRUE))

  data.frame(
    n = n,
    phase_locking_value = plv,
    mean_phase_difference_rad = mean_diff
  )
}

#' Compute correlation between two Gazepoint signals
#'
#' @param x First numeric signal.
#' @param y Second numeric signal.
#' @param method Correlation method.
#' @param lag_max Optional maximum lag in samples for cross-correlation.
#' @return Correlation summary.
#' @export
compute_gazepoint_signal_correlation <- function(x,
                                                 y,
                                                 method = c("pearson", "spearman", "kendall"),
                                                 lag_max = NULL) {
  method <- match.arg(method)

  x <- .gp_biosppy_num(x)
  y <- .gp_biosppy_num(y)

  n <- min(length(x), length(y))
  x <- x[seq_len(n)]
  y <- y[seq_len(n)]

  ok <- is.finite(x) & is.finite(y)
  cor0 <- if (sum(ok) >= 3L) stats::cor(x[ok], y[ok], method = method) else NA_real_

  if (is.null(lag_max)) {
    return(data.frame(
      n = sum(ok),
      correlation = cor0,
      method = method,
      best_lag = NA_integer_,
      best_lag_correlation = NA_real_
    ))
  }

  lags <- seq(-abs(lag_max), abs(lag_max))

  cors <- vapply(lags, function(lg) {
    if (lg < 0) {
      xx <- x[seq_len(n + lg)]
      yy <- y[(1 - lg):n]
    } else if (lg > 0) {
      xx <- x[(1 + lg):n]
      yy <- y[seq_len(n - lg)]
    } else {
      xx <- x
      yy <- y
    }

    ok2 <- is.finite(xx) & is.finite(yy)

    if (sum(ok2) < 3L) {
      return(NA_real_)
    }

    stats::cor(xx[ok2], yy[ok2], method = method)
  }, numeric(1))

  best <- if (any(is.finite(cors))) which.max(abs(cors)) else NA_integer_

  data.frame(
    n = sum(ok),
    correlation = cor0,
    method = method,
    best_lag = if (is.finite(best)) lags[best] else NA_integer_,
    best_lag_correlation = if (is.finite(best)) cors[best] else NA_real_
  )
}

