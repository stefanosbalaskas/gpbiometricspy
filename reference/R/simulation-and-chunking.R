#' Simulate Gazepoint-style biometric signals
#'
#' Generates synthetic Gazepoint-style EDA, PPG, HR, IBI, and TTL-like signals
#' with known ground-truth events. This is intended for teaching, examples, unit
#' tests, and model-validation workflows. It does not generate real participant
#' physiology.
#'
#' @param n_seconds Duration in seconds.
#' @param sampling_rate Sampling rate in Hz.
#' @param participant_id Participant identifier.
#' @param scr_onsets Optional SCR onset times in seconds.
#' @param scr_rate_per_min Expected SCR events per minute when `scr_onsets` is
#'   `NULL`.
#' @param pulse_rate_bpm Mean pulse rate.
#' @param respiration_rate_bpm Respiration-modulation rate.
#' @param eda_noise_sd EDA noise SD.
#' @param ppg_noise_sd PPG noise SD.
#' @param include_ttl Logical. If `TRUE`, adds TTL0 pulses at SCR onsets.
#' @param seed Optional random seed.
#'
#' @return A list with `overview`, `data`, `ground_truth`, and `settings`.
#' @export
simulate_gazepoint_biometrics <- function(n_seconds = 120,
                                          sampling_rate = 60,
                                          participant_id = "sim_p1",
                                          scr_onsets = NULL,
                                          scr_rate_per_min = 4,
                                          pulse_rate_bpm = 72,
                                          respiration_rate_bpm = 15,
                                          eda_noise_sd = 0.01,
                                          ppg_noise_sd = 0.02,
                                          include_ttl = TRUE,
                                          seed = NULL) {
  if (!is.null(seed)) {
    set.seed(seed)
  }

  if (!is.numeric(n_seconds) ||
      length(n_seconds) != 1 ||
      !is.finite(n_seconds) ||
      n_seconds <= 0) {
    stop("`n_seconds` must be a positive number.", call. = FALSE)
  }

  if (!is.numeric(sampling_rate) ||
      length(sampling_rate) != 1 ||
      !is.finite(sampling_rate) ||
      sampling_rate <= 0) {
    stop("`sampling_rate` must be a positive number.", call. = FALSE)
  }

  time <- seq(0, n_seconds, by = 1 / sampling_rate)
  n <- length(time)

  if (is.null(scr_onsets)) {
    expected_events <- max(1, round(n_seconds / 60 * scr_rate_per_min))
    scr_onsets <- sort(stats::runif(expected_events, 5, max(6, n_seconds - 5)))
  }

  scr_onsets <- scr_onsets[is.finite(scr_onsets) & scr_onsets >= 0 & scr_onsets <= n_seconds]

  tonic <- 1 + 0.001 * time
  eda <- tonic

  scr_truth <- data.frame(
    event_id = seq_along(scr_onsets),
    onset = scr_onsets,
    amplitude = stats::runif(length(scr_onsets), 0.03, 0.20),
    tau0 = 3.0,
    tau1 = 0.7,
    stringsAsFactors = FALSE
  )

  for (i in seq_along(scr_onsets)) {
    response_time <- pmax(0, time - scr_onsets[i])
    response <- exp(-response_time / scr_truth$tau0[i]) -
      exp(-response_time / scr_truth$tau1[i])
    response[response < 0] <- 0

    if (max(response) > 0) {
      response <- response / max(response)
    }

    eda <- eda + scr_truth$amplitude[i] * response
  }

  eda <- eda + stats::rnorm(n, sd = eda_noise_sd)

  pulse_interval <- 60 / pulse_rate_bpm
  pulse_times <- seq(0.5, n_seconds, by = pulse_interval)
  pulse_times <- pulse_times + stats::rnorm(length(pulse_times), sd = pulse_interval * 0.03)
  pulse_times <- pulse_times[pulse_times >= 0 & pulse_times <= n_seconds]

  respiration <- 1 + 0.15 * sin(2 * pi * (respiration_rate_bpm / 60) * time)

  ppg <- numeric(n)

  for (pt in pulse_times) {
    ppg <- ppg + exp(-0.5 * ((time - pt) / 0.06)^2)
  }

  ppg <- respiration * ppg
  ppg <- ppg / max(ppg)
  ppg <- ppg + stats::rnorm(n, sd = ppg_noise_sd)

  ibi <- rep(pulse_interval, n)

  if (length(pulse_times) >= 2) {
    pulse_ibi <- diff(pulse_times)
    pulse_mid <- pulse_times[-1]
    ibi <- stats::approx(pulse_mid, pulse_ibi, xout = time, rule = 2)$y
  }

  hr <- 60 / ibi

  ttl0 <- rep(0L, n)

  if (isTRUE(include_ttl) && length(scr_onsets) > 0) {
    ttl_idx <- vapply(scr_onsets, function(onset) {
      which.min(abs(time - onset))
    }, integer(1))

    ttl0[ttl_idx] <- 1L
  }

  dat <- data.frame(
    participant_id = participant_id,
    CNT = time,
    GSR_US = eda,
    HRP = ppg,
    HR = hr,
    IBI = ibi,
    TTL0 = ttl0,
    stringsAsFactors = FALSE
  )

  pulse_truth <- data.frame(
    pulse_id = seq_along(pulse_times),
    peak_time = pulse_times,
    expected_ibi = pulse_interval,
    stringsAsFactors = FALSE
  )

  ground_truth <- list(
    scr_events = scr_truth,
    pulse_peaks = pulse_truth,
    respiration_rate_bpm = respiration_rate_bpm,
    pulse_rate_bpm = pulse_rate_bpm
  )

  overview <- data.frame(
    rows = nrow(dat),
    n_seconds = n_seconds,
    sampling_rate_hz = sampling_rate,
    scr_events = nrow(scr_truth),
    pulse_peaks = nrow(pulse_truth),
    status = "synthetic_gazepoint_biometrics_created",
    interpretation = paste(
      "Synthetic signals are for teaching, examples, tests, and model validation.",
      "They are not real participant physiology."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      data = dat,
      ground_truth = ground_truth,
      settings = list(
        n_seconds = n_seconds,
        sampling_rate = sampling_rate,
        participant_id = participant_id,
        scr_onsets = scr_onsets,
        scr_rate_per_min = scr_rate_per_min,
        pulse_rate_bpm = pulse_rate_bpm,
        respiration_rate_bpm = respiration_rate_bpm,
        eda_noise_sd = eda_noise_sd,
        ppg_noise_sd = ppg_noise_sd,
        include_ttl = include_ttl,
        seed = seed
      )
    ),
    class = c("gazepoint_biometrics_simulation", "list")
  )
}

#' Chunk Gazepoint biometric data into fixed analysis episodes
#'
#' Adds programmatic fixed-duration chunks/episodes to continuous biometric data.
#' This is useful for baseline segmentation, repeated-measures feature
#' extraction, and analyses that do not rely on external TTL markers.
#'
#' @param dat A data frame.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param chunk_seconds Chunk duration in seconds.
#' @param start_time Optional fixed start time. If `NULL`, uses group minimum.
#' @param chunk_col Output chunk identifier column.
#' @param episode_col Output episode label column.
#' @param include_partial Logical. If `FALSE`, partial final chunks are marked
#'   but not assigned as complete chunks.
#'
#' @return A data frame with chunk columns and chunk-summary attributes.
#' @export
chunk_gazepoint_biometrics <- function(dat,
                                       time_col = "CNT",
                                       group_cols = NULL,
                                       chunk_seconds = 60,
                                       start_time = NULL,
                                       chunk_col = "chunk_id",
                                       episode_col = "episode_id",
                                       include_partial = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(chunk_seconds) ||
      length(chunk_seconds) != 1 ||
      !is.finite(chunk_seconds) ||
      chunk_seconds <= 0) {
    stop("`chunk_seconds` must be a positive number.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  out <- dat
  out[[chunk_col]] <- NA_integer_
  out[[episode_col]] <- NA_character_
  out$chunk_start <- NA_real_
  out$chunk_end <- NA_real_
  out$chunk_midpoint <- NA_real_
  out$chunk_complete <- FALSE

  groups <- gpbiometrics_chunk_split(out, group_cols)

  summary_rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    time <- out[[time_col]][idx]
    finite <- is.finite(time)

    if (!any(finite)) {
      next
    }

    group_start <- if (!is.null(start_time)) {
      start_time
    } else {
      min(time[finite])
    }

    group_end <- max(time[finite])
    raw_chunk <- floor((time - group_start) / chunk_seconds) + 1L

    raw_chunk[!is.finite(raw_chunk) | raw_chunk < 1] <- NA_integer_

    for (chunk_id in sort(unique(raw_chunk[is.finite(raw_chunk)]))) {
      chunk_idx <- idx[raw_chunk == chunk_id]
      chunk_start <- group_start + (chunk_id - 1) * chunk_seconds
      chunk_end <- chunk_start + chunk_seconds
      chunk_time <- out[[time_col]][chunk_idx]

      complete <- max(chunk_time, na.rm = TRUE) >= chunk_end ||
        isTRUE(include_partial)

      if (!complete && !isTRUE(include_partial)) {
        out[[chunk_col]][chunk_idx] <- NA_integer_
        out[[episode_col]][chunk_idx] <- NA_character_
      } else {
        out[[chunk_col]][chunk_idx] <- chunk_id
        out[[episode_col]][chunk_idx] <- paste0(group_id, "_chunk_", chunk_id)
      }

      out$chunk_start[chunk_idx] <- chunk_start
      out$chunk_end[chunk_idx] <- chunk_end
      out$chunk_midpoint[chunk_idx] <- mean(c(chunk_start, chunk_end))
      out$chunk_complete[chunk_idx] <- complete

      summary_rows[[row_id]] <- data.frame(
        group_id = group_id,
        chunk_id = chunk_id,
        episode_id = paste0(group_id, "_chunk_", chunk_id),
        chunk_start = chunk_start,
        chunk_end = chunk_end,
        chunk_midpoint = mean(c(chunk_start, chunk_end)),
        row_count = length(chunk_idx),
        observed_start = min(chunk_time, na.rm = TRUE),
        observed_end = max(chunk_time, na.rm = TRUE),
        complete = complete,
        assigned = complete || isTRUE(include_partial),
        stringsAsFactors = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  chunk_summary <- if (length(summary_rows) > 0) {
    do.call(rbind, summary_rows)
  } else {
    data.frame()
  }

  rownames(chunk_summary) <- NULL

  overview <- data.frame(
    input_rows = nrow(dat),
    output_rows = nrow(out),
    group_count = length(groups),
    chunk_rows = nrow(chunk_summary),
    assigned_chunks = sum(chunk_summary$assigned, na.rm = TRUE),
    chunk_seconds = chunk_seconds,
    include_partial = include_partial,
    status = "biometric_chunks_created",
    stringsAsFactors = FALSE
  )

  attr(out, "chunk_overview") <- overview
  attr(out, "chunk_summary") <- chunk_summary
  attr(out, "chunk_settings") <- list(
    time_col = time_col,
    group_cols = group_cols,
    chunk_seconds = chunk_seconds,
    start_time = start_time,
    chunk_col = chunk_col,
    episode_col = episode_col,
    include_partial = include_partial
  )

  class(out) <- unique(c("gazepoint_biometric_chunks", class(out)))
  out
}

gpbiometrics_chunk_split <- function(dat, group_cols) {
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
