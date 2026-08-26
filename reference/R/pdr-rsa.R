#' Extract PPG-derived respiration proxy signals
#'
#' Extracts dependency-light PPG-derived respiration proxy features from a
#' Gazepoint pulse/PPG waveform. The function estimates respiration-modulated
#' pulse features such as respiratory-induced intensity variability (RIIV),
#' pulse amplitude variability (PAV), pulse width variability (PWV), and
#' pulse-rate variability (PRV).
#'
#' These are proxy respiratory features. They should not be treated as a
#' replacement for a respiration belt or clinical respiratory measurement.
#'
#' @param dat A data frame containing a PPG/pulse waveform.
#' @param ppg_col Numeric PPG/pulse waveform column, often `HRP`.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param sampling_rate Optional sampling rate in Hz. If `NULL`, estimated from
#'   `time_col`.
#' @param min_peak_distance_s Minimum plausible distance between pulse peaks.
#' @param smooth_window Number of samples used for simple moving-average
#'   smoothing before peak detection.
#' @param respiration_band Expected respiration-frequency band in Hz.
#' @param pdr_resample_rate Resampling rate used for spectral estimation of PDR
#'   proxy signals.
#'
#' @return A list with `overview`, `pulse_features`, `pdr_timeseries`,
#'   `pdr_summary`, and `settings`.
#' @export
extract_gazepoint_pdr_signals <- function(dat,
                                          ppg_col = "HRP",
                                          time_col = "CNT",
                                          group_cols = NULL,
                                          sampling_rate = NULL,
                                          min_peak_distance_s = 0.30,
                                          smooth_window = 5,
                                          respiration_band = c(0.10, 0.60),
                                          pdr_resample_rate = 4) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!ppg_col %in% names(dat)) {
    stop("Column `", ppg_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[ppg_col]])) {
    stop("`ppg_col` must identify a numeric column.", call. = FALSE)
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

  if (!is.numeric(respiration_band) ||
      length(respiration_band) != 2 ||
      any(!is.finite(respiration_band)) ||
      respiration_band[1] <= 0 ||
      respiration_band[1] >= respiration_band[2]) {
    stop("`respiration_band` must be a positive numeric vector of length two.", call. = FALSE)
  }

  groups <- gpbiometrics_pdr_split_indices(dat, group_cols)

  pulse_rows <- list()
  summary_rows <- list()
  pulse_row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    ppg <- dat[[ppg_col]][idx]

    fs <- gpbiometrics_pdr_sampling_rate(time, sampling_rate)

    if (!is.finite(fs) || fs <= 0) {
      fs <- NA_real_
    }

    smoothed <- gpbiometrics_pdr_smooth(ppg, smooth_window)
    peaks <- gpbiometrics_pdr_find_peaks(
      smoothed,
      time = time,
      min_peak_distance_s = min_peak_distance_s
    )

    if (length(peaks) < 3) {
      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_samples = length(idx),
        n_pulses = length(peaks),
        sampling_rate_hz = fs,
        riiv_resp_rate_hz = NA_real_,
        pav_resp_rate_hz = NA_real_,
        pwv_resp_rate_hz = NA_real_,
        prv_resp_rate_hz = NA_real_,
        proxy_resp_rate_hz = NA_real_,
        proxy_resp_rate_bpm = NA_real_,
        status = "insufficient_pulse_peaks",
        stringsAsFactors = FALSE
      )
      next
    }

    for (i in 2:length(peaks)) {
      prev_peak <- peaks[i - 1]
      current_peak <- peaks[i]

      segment <- prev_peak:current_peak
      trough_local <- which.min(smoothed[segment])
      trough <- segment[trough_local]

      prev_prev_peak <- if (i >= 3) peaks[i - 2] else NA_integer_

      pulse_interval_s <- time[current_peak] - time[prev_peak]
      pulse_rate_bpm <- if (is.finite(pulse_interval_s) && pulse_interval_s > 0) {
        60 / pulse_interval_s
      } else {
        NA_real_
      }

      pulse_width_s <- if (is.finite(prev_prev_peak)) {
        time[current_peak] - time[prev_peak]
      } else {
        NA_real_
      }

      pulse_amplitude <- smoothed[current_peak] - smoothed[trough]
      riiv <- smoothed[trough]
      pav <- pulse_amplitude
      pwv <- pulse_width_s
      prv <- pulse_rate_bpm

      pulse_rows[[pulse_row_id]] <- data.frame(
        group_id = group_id,
        pulse_index = i - 1L,
        peak_row = idx[current_peak],
        trough_row = idx[trough],
        peak_time = time[current_peak],
        trough_time = time[trough],
        peak_value = smoothed[current_peak],
        trough_value = smoothed[trough],
        riiv = riiv,
        pav = pav,
        pwv = pwv,
        prv = prv,
        pulse_interval_s = pulse_interval_s,
        pulse_rate_bpm = pulse_rate_bpm,
        stringsAsFactors = FALSE
      )

      pulse_row_id <- pulse_row_id + 1L
    }

    group_pulses <- do.call(rbind, pulse_rows)
    group_pulses <- group_pulses[group_pulses$group_id == group_id, , drop = FALSE]

    if (nrow(group_pulses) == 0) {
      summary_rows[[group_id]] <- data.frame(
        group_id = group_id,
        n_samples = length(idx),
        n_pulses = length(peaks),
        sampling_rate_hz = fs,
        riiv_resp_rate_hz = NA_real_,
        pav_resp_rate_hz = NA_real_,
        pwv_resp_rate_hz = NA_real_,
        prv_resp_rate_hz = NA_real_,
        proxy_resp_rate_hz = NA_real_,
        proxy_resp_rate_bpm = NA_real_,
        status = "pdr_feature_extraction_failed",
        stringsAsFactors = FALSE
      )
      next
    }

    riiv_rate <- gpbiometrics_pdr_rate_from_feature(
      group_pulses$peak_time,
      group_pulses$riiv,
      respiration_band = respiration_band,
      resample_rate = pdr_resample_rate
    )

    pav_rate <- gpbiometrics_pdr_rate_from_feature(
      group_pulses$peak_time,
      group_pulses$pav,
      respiration_band = respiration_band,
      resample_rate = pdr_resample_rate
    )

    pwv_rate <- gpbiometrics_pdr_rate_from_feature(
      group_pulses$peak_time,
      group_pulses$pwv,
      respiration_band = respiration_band,
      resample_rate = pdr_resample_rate
    )

    prv_rate <- gpbiometrics_pdr_rate_from_feature(
      group_pulses$peak_time,
      group_pulses$prv,
      respiration_band = respiration_band,
      resample_rate = pdr_resample_rate
    )

    valid_rates <- c(riiv_rate, pav_rate, pwv_rate, prv_rate)
    proxy_rate <- if (any(is.finite(valid_rates))) {
      stats::median(valid_rates[is.finite(valid_rates)])
    } else {
      NA_real_
    }

    summary_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_samples = length(idx),
      n_pulses = length(peaks),
      sampling_rate_hz = fs,
      riiv_resp_rate_hz = riiv_rate,
      pav_resp_rate_hz = pav_rate,
      pwv_resp_rate_hz = pwv_rate,
      prv_resp_rate_hz = prv_rate,
      proxy_resp_rate_hz = proxy_rate,
      proxy_resp_rate_bpm = proxy_rate * 60,
      status = if (is.finite(proxy_rate)) {
        "pdr_extracted"
      } else {
        "pdr_rate_not_estimated"
      },
      stringsAsFactors = FALSE
    )
  }

  pulse_features <- if (length(pulse_rows) > 0) {
    do.call(rbind, pulse_rows)
  } else {
    data.frame()
  }

  if (nrow(pulse_features) > 0) {
    pulse_features$resp_proxy <- gpbiometrics_pdr_row_proxy(
      pulse_features[, c("riiv", "pav", "pwv", "prv"), drop = FALSE]
    )

    pdr_timeseries <- pulse_features[, c(
      "group_id", "pulse_index", "peak_time", "riiv", "pav", "pwv", "prv",
      "resp_proxy"
    )]
  } else {
    pdr_timeseries <- data.frame()
  }

  pdr_summary <- do.call(rbind, summary_rows)
  rownames(pdr_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    pulse_feature_rows = nrow(pulse_features),
    pdr_summary_rows = nrow(pdr_summary),
    successful_groups = sum(pdr_summary$status == "pdr_extracted"),
    problem_groups = sum(pdr_summary$status != "pdr_extracted"),
    ppg_col = ppg_col,
    time_col = time_col,
    status = if (all(pdr_summary$status == "pdr_extracted")) {
      "pdr_extraction_complete"
    } else if (any(pdr_summary$status == "pdr_extracted")) {
      "pdr_extraction_partial"
    } else {
      "pdr_extraction_failed"
    },
    interpretation = paste(
      "PPG-derived respiration features are proxy estimates from pulse morphology and timing.",
      "They are not a substitute for direct respiratory-belt measurement."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      pulse_features = pulse_features,
      pdr_timeseries = pdr_timeseries,
      pdr_summary = pdr_summary,
      settings = list(
        ppg_col = ppg_col,
        time_col = time_col,
        group_cols = group_cols,
        sampling_rate = sampling_rate,
        min_peak_distance_s = min_peak_distance_s,
        smooth_window = smooth_window,
        respiration_band = respiration_band,
        pdr_resample_rate = pdr_resample_rate
      )
    ),
    class = c("gazepoint_pdr_signals", "list")
  )
}

#' Calculate respiration-informed RSA proxy features
#'
#' Calculates dependency-light RSA proxy summaries from IBI/RR intervals and,
#' optionally, PPG-derived respiration features from
#' `extract_gazepoint_pdr_signals()`. This provides peak-to-trough and
#' Porges-Bohrer-inspired band-power proxy summaries. These outputs should be
#' interpreted as respiration-informed HRV/RSA features, not direct clinical
#' vagal-tone estimates.
#'
#' @param dat A data frame containing IBI/RR data.
#' @param ibi_col IBI/RR interval column.
#' @param time_col Time column for the IBI/RR observations.
#' @param group_cols Optional grouping columns.
#' @param pdr Optional output from `extract_gazepoint_pdr_signals()`.
#' @param resp_rate_hz Optional fixed respiration rate in Hz.
#' @param respiration_band Default respiration/HF band when no PDR rate is
#'   available.
#' @param resample_rate Resampling rate for spectral RSA proxy calculation.
#'
#' @return A list with `overview`, `rsa_summary`, and `settings`.
#' @export
calculate_gazepoint_rsa <- function(dat,
                                    ibi_col = "IBI",
                                    time_col = "CNT",
                                    group_cols = NULL,
                                    pdr = NULL,
                                    resp_rate_hz = NULL,
                                    respiration_band = c(0.12, 0.40),
                                    resample_rate = 4) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!ibi_col %in% names(dat)) {
    stop("Column `", ibi_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
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

  groups <- gpbiometrics_pdr_split_indices(dat, group_cols)

  pdr_summary <- NULL
  pdr_timeseries <- NULL

  if (!is.null(pdr)) {
    if (!inherits(pdr, "gazepoint_pdr_signals")) {
      stop("`pdr` must be output from `extract_gazepoint_pdr_signals()`.", call. = FALSE)
    }
    pdr_summary <- pdr$pdr_summary
    pdr_timeseries <- pdr$pdr_timeseries
  }

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    ibi <- dat[[ibi_col]][idx]

    finite <- is.finite(time) & is.finite(ibi) & ibi > 0

    time <- time[finite]
    ibi <- ibi[finite]

    group_resp_rate <- gpbiometrics_rsa_group_resp_rate(
      group_id = group_id,
      pdr_summary = pdr_summary,
      resp_rate_hz = resp_rate_hz
    )

    p2t <- gpbiometrics_rsa_peak_to_trough_proxy(
      time = time,
      ibi = ibi,
      group_id = group_id,
      pdr_timeseries = pdr_timeseries
    )

    pb <- gpbiometrics_rsa_pb_proxy(
      time = time,
      ibi = ibi,
      resp_rate_hz = group_resp_rate,
      respiration_band = respiration_band,
      resample_rate = resample_rate
    )

    data.frame(
      group_id = group_id,
      n_intervals = length(ibi),
      resp_rate_hz = group_resp_rate,
      resp_rate_bpm = group_resp_rate * 60,
      rsa_p2t_proxy = p2t,
      rsa_pb_log_power_proxy = pb,
      status = if (length(ibi) >= 5 && (is.finite(p2t) || is.finite(pb))) {
        "rsa_proxy_calculated"
      } else {
        "rsa_proxy_insufficient_information"
      },
      stringsAsFactors = FALSE
    )
  })

  rsa_summary <- do.call(rbind, rows)
  rownames(rsa_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    rsa_rows = nrow(rsa_summary),
    successful_groups = sum(rsa_summary$status == "rsa_proxy_calculated"),
    problem_groups = sum(rsa_summary$status != "rsa_proxy_calculated"),
    status = if (all(rsa_summary$status == "rsa_proxy_calculated")) {
      "rsa_proxy_complete"
    } else if (any(rsa_summary$status == "rsa_proxy_calculated")) {
      "rsa_proxy_partial"
    } else {
      "rsa_proxy_failed"
    },
    interpretation = paste(
      "RSA outputs are respiration-informed HRV proxy summaries.",
      "Without direct respiration measurement they should not be interpreted as definitive vagal-tone estimates."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      rsa_summary = rsa_summary,
      settings = list(
        ibi_col = ibi_col,
        time_col = time_col,
        group_cols = group_cols,
        pdr_supplied = !is.null(pdr),
        resp_rate_hz = resp_rate_hz,
        respiration_band = respiration_band,
        resample_rate = resample_rate
      )
    ),
    class = c("gazepoint_rsa_proxy", "list")
  )
}

gpbiometrics_pdr_split_indices <- function(dat, group_cols) {
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

gpbiometrics_pdr_sampling_rate <- function(time, sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    return(sampling_rate)
  }

  time <- time[is.finite(time)]

  if (length(time) < 3) {
    return(NA_real_)
  }

  dt <- diff(time)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) == 0) {
    return(NA_real_)
  }

  median_dt <- stats::median(dt)

  if (median_dt > 10) {
    1000 / median_dt
  } else {
    1 / median_dt
  }
}

gpbiometrics_pdr_smooth <- function(x, window = 5) {
  if (!is.numeric(window) || length(window) != 1 || window <= 1) {
    return(as.numeric(x))
  }

  window <- as.integer(window)

  if (length(x) < window) {
    return(as.numeric(x))
  }

  y <- as.numeric(stats::filter(x, rep(1 / window, window), sides = 2))
  y[!is.finite(y)] <- x[!is.finite(y)]
  y[is.na(y)] <- x[is.na(y)]
  y
}

gpbiometrics_pdr_find_peaks <- function(x, time, min_peak_distance_s = 0.30) {
  finite <- is.finite(x) & is.finite(time)

  if (sum(finite) < 3) {
    return(integer())
  }

  candidate <- which(
    c(FALSE, x[-c(1, length(x))] > x[-c(length(x) - 1, length(x))] &
        x[-c(1, length(x))] >= x[-c(1, 2)], FALSE)
  )

  candidate <- candidate[is.finite(x[candidate]) & is.finite(time[candidate])]

  if (length(candidate) == 0) {
    return(integer())
  }

  selected <- candidate[1]

  if (length(candidate) > 1) {
    for (i in candidate[-1]) {
      if ((time[i] - time[selected[length(selected)]]) >= min_peak_distance_s) {
        selected <- c(selected, i)
      } else if (x[i] > x[selected[length(selected)]]) {
        selected[length(selected)] <- i
      }
    }
  }

  selected
}

gpbiometrics_pdr_rate_from_feature <- function(time,
                                               feature,
                                               respiration_band = c(0.10, 0.60),
                                               resample_rate = 4) {
  keep <- is.finite(time) & is.finite(feature)

  time <- time[keep]
  feature <- feature[keep]

  if (length(time) < 8 || length(unique(time)) < 8 || stats::sd(feature) == 0) {
    return(NA_real_)
  }

  ord <- order(time)
  time <- time[ord]
  feature <- feature[ord]

  grid <- seq(min(time), max(time), by = 1 / resample_rate)

  if (length(grid) < 16) {
    return(NA_real_)
  }

  y <- stats::approx(time, feature, xout = grid, rule = 2)$y
  y <- y - mean(y, na.rm = TRUE)

  if (stats::sd(y, na.rm = TRUE) == 0) {
    return(NA_real_)
  }

  spec <- stats::spec.pgram(
    y,
    taper = 0.1,
    plot = FALSE,
    demean = TRUE,
    detrend = TRUE,
    fast = TRUE
  )

  freq <- spec$freq * resample_rate
  power <- spec$spec

  in_band <- is.finite(freq) &
    is.finite(power) &
    freq >= respiration_band[1] &
    freq <= respiration_band[2]

  if (!any(in_band)) {
    return(NA_real_)
  }

  freq[in_band][which.max(power[in_band])]
}

gpbiometrics_pdr_row_proxy <- function(feature_df) {
  scaled <- lapply(feature_df, function(x) {
    if (sum(is.finite(x)) < 2 || stats::sd(x, na.rm = TRUE) == 0) {
      return(rep(NA_real_, length(x)))
    }
    as.numeric(scale(x))
  })

  scaled <- as.data.frame(scaled)

  apply(scaled, 1, function(x) {
    if (all(!is.finite(x))) {
      NA_real_
    } else {
      mean(x, na.rm = TRUE)
    }
  })
}

gpbiometrics_rsa_group_resp_rate <- function(group_id,
                                             pdr_summary = NULL,
                                             resp_rate_hz = NULL) {
  if (!is.null(resp_rate_hz) &&
      is.numeric(resp_rate_hz) &&
      length(resp_rate_hz) == 1 &&
      is.finite(resp_rate_hz)) {
    return(resp_rate_hz)
  }

  if (is.null(pdr_summary) || nrow(pdr_summary) == 0) {
    return(NA_real_)
  }

  row <- pdr_summary[pdr_summary$group_id == group_id, , drop = FALSE]

  if (nrow(row) == 0 || !is.finite(row$proxy_resp_rate_hz[1])) {
    return(NA_real_)
  }

  row$proxy_resp_rate_hz[1]
}

gpbiometrics_rsa_peak_to_trough_proxy <- function(time,
                                                  ibi,
                                                  group_id,
                                                  pdr_timeseries = NULL) {
  if (is.null(pdr_timeseries) || nrow(pdr_timeseries) == 0) {
    return(NA_real_)
  }

  pdr_group <- pdr_timeseries[pdr_timeseries$group_id == group_id, , drop = FALSE]

  if (nrow(pdr_group) < 4 || !"resp_proxy" %in% names(pdr_group)) {
    return(NA_real_)
  }

  pdr_group <- pdr_group[order(pdr_group$peak_time), , drop = FALSE]
  resp <- pdr_group$resp_proxy
  resp_time <- pdr_group$peak_time

  peaks <- gpbiometrics_pdr_find_peaks(
    resp,
    time = resp_time,
    min_peak_distance_s = 1
  )

  if (length(peaks) < 2) {
    return(NA_real_)
  }

  cycle_values <- numeric()

  for (i in seq_len(length(peaks) - 1)) {
    start_time <- resp_time[peaks[i]]
    end_time <- resp_time[peaks[i + 1]]

    in_cycle <- is.finite(time) &
      time >= start_time &
      time <= end_time

    if (sum(in_cycle) >= 2) {
      cycle_ibi <- ibi[in_cycle]
      cycle_values <- c(
        cycle_values,
        max(cycle_ibi, na.rm = TRUE) - min(cycle_ibi, na.rm = TRUE)
      )
    }
  }

  if (length(cycle_values) == 0) {
    return(NA_real_)
  }

  mean(cycle_values, na.rm = TRUE)
}

gpbiometrics_rsa_pb_proxy <- function(time,
                                      ibi,
                                      resp_rate_hz = NA_real_,
                                      respiration_band = c(0.12, 0.40),
                                      resample_rate = 4) {
  keep <- is.finite(time) & is.finite(ibi) & ibi > 0

  time <- time[keep]
  ibi <- ibi[keep]

  if (length(time) < 8 || length(unique(time)) < 8 || stats::sd(ibi) == 0) {
    return(NA_real_)
  }

  ord <- order(time)
  time <- time[ord]
  ibi <- ibi[ord]

  grid <- seq(min(time), max(time), by = 1 / resample_rate)

  if (length(grid) < 16) {
    return(NA_real_)
  }

  y <- stats::approx(time, ibi, xout = grid, rule = 2)$y
  y <- y - mean(y, na.rm = TRUE)

  band <- respiration_band

  if (is.finite(resp_rate_hz) && resp_rate_hz > 0) {
    band <- c(
      max(0.05, resp_rate_hz - 0.05),
      min(resample_rate / 2 - 0.01, resp_rate_hz + 0.05)
    )
  }

  spec <- stats::spec.pgram(
    y,
    taper = 0.1,
    plot = FALSE,
    demean = TRUE,
    detrend = TRUE,
    fast = TRUE
  )

  freq <- spec$freq * resample_rate
  power <- spec$spec

  in_band <- is.finite(freq) &
    is.finite(power) &
    freq >= band[1] &
    freq <= band[2]

  if (!any(in_band)) {
    return(NA_real_)
  }

  band_power <- sum(power[in_band], na.rm = TRUE)

  if (!is.finite(band_power) || band_power <= 0) {
    return(NA_real_)
  }

  log(band_power)
}
