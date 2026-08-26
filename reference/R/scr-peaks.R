#' Detect Gazepoint SCR peaks
#'
#' Detects candidate skin conductance responses (SCRs) from Gazepoint EDA/GSR
#' signals. The helper prefers a phasic channel such as `GSR_US_PHASIC` when
#' available, and otherwise falls back to a conductance-like signal such as
#' `GSR_US`. It returns explicit onset, peak, amplitude, rise-time, and
#' recovery-time fields for downstream event-window summaries and statistical
#' modelling.
#'
#' This is a conservative R-native peak detector. It is not a replacement for
#' full model-based EDA decomposition tools such as Ledalab, PsPM, or cvxEDA.
#'
#' @param data A data frame containing Gazepoint biometric rows.
#' @param signal_col Optional conductance-like signal column, typically
#'   `GSR_US`. Used when `phasic_col` is absent or unavailable.
#' @param phasic_col Optional phasic EDA signal column, typically
#'   `GSR_US_PHASIC`.
#' @param time_col Optional time/counter column. If `NULL`, common Gazepoint
#'   time columns are detected automatically.
#' @param group_cols Optional grouping columns. If `NULL`, available
#'   source/participant/media/trial-like columns are used.
#' @param prefer_vendor_phasic Logical. If `TRUE`, prefer `GSR_US_PHASIC` when
#'   available.
#' @param amplitude_min Minimum trough-to-peak amplitude required for a detected
#'   SCR.
#' @param recovery_fraction Fraction of the peak amplitude used to define
#'   recovery. The default `.5` estimates half-recovery.
#' @param smooth_width Optional odd integer moving-average width. Use `1` for no
#'   smoothing.
#' @param min_peak_distance Minimum distance, in rows, allowed between retained
#'   candidate peaks within each group. The default `1` preserves all local
#'   maxima. Larger values reduce repeated detection of closely spaced local
#'   maxima within a sustained SCR-like response.
#'
#' @return A list with `overview`, `peaks`, `group_summary`, `signal_summary`,
#'   and `settings`.
#' @export
detect_gazepoint_scr_peaks <- function(data,
                                       signal_col = NULL,
                                       phasic_col = NULL,
                                       time_col = NULL,
                                       group_cols = NULL,
                                       prefer_vendor_phasic = TRUE,
                                       amplitude_min = 0.01,
                                       recovery_fraction = 0.5,
                                       smooth_width = 1,
                                       min_peak_distance = 1) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.logical(prefer_vendor_phasic) || length(prefer_vendor_phasic) != 1) {
    stop("`prefer_vendor_phasic` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(amplitude_min) || length(amplitude_min) != 1 || amplitude_min < 0) {
    stop("`amplitude_min` must be a non-negative number.", call. = FALSE)
  }

  if (!is.numeric(recovery_fraction) ||
      length(recovery_fraction) != 1 ||
      recovery_fraction <= 0 ||
      recovery_fraction >= 1) {
    stop("`recovery_fraction` must be a number between 0 and 1.", call. = FALSE)
  }

  if (!is.numeric(smooth_width) || length(smooth_width) != 1 || smooth_width < 1) {
    stop("`smooth_width` must be a positive integer.", call. = FALSE)
  }

  if (!is.numeric(min_peak_distance) ||
      length(min_peak_distance) != 1 ||
      min_peak_distance < 1) {
    stop("`min_peak_distance` must be a positive integer.", call. = FALSE)
  }

  smooth_width <- as.integer(round(smooth_width))
  min_peak_distance <- as.integer(round(min_peak_distance))

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_row_id <- seq_len(nrow(dat))

  names_dat <- names(dat)

  source_signal <- gpbiometrics_scr_resolve_signal_col(
    names_dat = names_dat,
    signal_col = signal_col,
    phasic_col = phasic_col,
    prefer_vendor_phasic = prefer_vendor_phasic
  )

  if (is.null(source_signal) || !source_signal %in% names_dat) {
    stop(
      "No usable SCR signal column was found. Supply `phasic_col` or `signal_col`.",
      call. = FALSE
    )
  }

  if (is.null(time_col)) {
    time_col <- gpbiometrics_scr_first_existing(
      names_dat,
      c(
        "time_ms", "timestamp_ms", "timestamp",
        "TIME", "Time", "time",
        "CNT", "cnt"
      )
    )
  }

  if (!is.null(time_col) && !time_col %in% names_dat) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  group_cols <- gpbiometrics_scr_resolve_group_cols(names_dat, group_cols)

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`group_cols` not found in `data`: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  signal_raw <- suppressWarnings(as.numeric(dat[[source_signal]]))

  if (all(is.na(signal_raw))) {
    stop("The selected SCR signal column must be numeric or numeric-coercible.", call. = FALSE)
  }

  time_value <- if (!is.null(time_col)) {
    suppressWarnings(as.numeric(dat[[time_col]]))
  } else {
    seq_len(nrow(dat))
  }

  group_id <- gpbiometrics_scr_group_id(dat, group_cols)
  group_indices <- split(seq_len(nrow(dat)), group_id, drop = TRUE)

  peaks_list <- list()
  group_summary_list <- list()

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]
    x_raw <- signal_raw[idx]
    t <- time_value[idx]

    x <- gpbiometrics_scr_smooth_signal(x_raw, smooth_width = smooth_width)

    candidate_peak_index <- gpbiometrics_scr_candidate_peaks(x)
    candidate_peak_index <- gpbiometrics_scr_filter_candidate_peaks(
      x = x,
      candidate_peak_index = candidate_peak_index,
      min_peak_distance = min_peak_distance
    )
    candidate_count <- length(candidate_peak_index)

    detected_for_group <- list()
    below_threshold_count <- 0L
    incomplete_recovery_count <- 0L

    if (candidate_count > 0) {
      for (candidate_i in seq_along(candidate_peak_index)) {
        peak_local <- candidate_peak_index[candidate_i]

        peak <- gpbiometrics_scr_score_peak(
          x = x,
          t = t,
          peak_local = peak_local,
          amplitude_min = amplitude_min,
          recovery_fraction = recovery_fraction
        )

        if (is.null(peak)) {
          below_threshold_count <- below_threshold_count + 1L
          next
        }

        if (identical(peak$status, "detected_incomplete_recovery")) {
          incomplete_recovery_count <- incomplete_recovery_count + 1L
        }

        peak_row <- data.frame(
          group_id = group_name,
          peak_id = length(detected_for_group) + 1L,
          source_signal = source_signal,
          onset_row_id = dat$.gpbiometrics_row_id[idx[peak$onset_index]],
          peak_row_id = dat$.gpbiometrics_row_id[idx[peak$peak_index]],
          recovery_row_id = if (is.na(peak$recovery_index)) {
            NA_integer_
          } else {
            dat$.gpbiometrics_row_id[idx[peak$recovery_index]]
          },
          onset_index = peak$onset_index,
          peak_index = peak$peak_index,
          recovery_index = peak$recovery_index,
          onset_time = peak$onset_time,
          peak_time = peak$peak_time,
          recovery_time = peak$recovery_time,
          onset_value = peak$onset_value,
          peak_value = peak$peak_value,
          recovery_value = peak$recovery_value,
          amplitude = peak$amplitude,
          rise_time = peak$rise_time,
          recovery_time_after_peak = peak$recovery_time_after_peak,
          status = peak$status,
          stringsAsFactors = FALSE
        )

        if (length(group_cols) > 0) {
          group_values <- dat[idx[1], group_cols, drop = FALSE]
          peak_row <- cbind(group_values, peak_row)
        }

        detected_for_group[[length(detected_for_group) + 1L]] <- peak_row
      }
    }

    if (length(detected_for_group) > 0) {
      peaks_list <- c(peaks_list, detected_for_group)
    }

    finite_x <- x[is.finite(x)]
    group_status <- if (length(finite_x) < 3) {
      "insufficient_signal"
    } else if (length(detected_for_group) == 0 && candidate_count == 0) {
      "no_candidate_peaks"
    } else if (length(detected_for_group) == 0) {
      "no_peaks_above_threshold"
    } else if (incomplete_recovery_count > 0) {
      "peaks_detected_with_incomplete_recovery"
    } else {
      "peaks_detected"
    }

    group_row <- data.frame(
      group_id = group_name,
      rows = length(idx),
      finite_signal_rows = length(finite_x),
      candidate_peaks = candidate_count,
      detected_peaks = length(detected_for_group),
      below_threshold_peaks = below_threshold_count,
      incomplete_recovery_peaks = incomplete_recovery_count,
      signal_min = if (length(finite_x) > 0) min(finite_x, na.rm = TRUE) else NA_real_,
      signal_max = if (length(finite_x) > 0) max(finite_x, na.rm = TRUE) else NA_real_,
      signal_sd = if (length(finite_x) > 1) stats::sd(finite_x, na.rm = TRUE) else NA_real_,
      status = group_status,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      group_values <- dat[idx[1], group_cols, drop = FALSE]
      group_row <- cbind(group_values, group_row)
    }

    group_summary_list[[length(group_summary_list) + 1L]] <- group_row
  }

  peaks <- if (length(peaks_list) > 0) {
    out <- do.call(rbind, peaks_list)
    rownames(out) <- NULL
    out
  } else {
    gpbiometrics_scr_empty_peaks(group_cols)
  }

  group_summary <- do.call(rbind, group_summary_list)
  rownames(group_summary) <- NULL

  signal_summary <- data.frame(
    source_signal = source_signal,
    input_rows = nrow(dat),
    finite_signal_rows = sum(is.finite(signal_raw)),
    missing_signal_rows = sum(is.na(signal_raw)),
    signal_min = if (any(is.finite(signal_raw))) min(signal_raw, na.rm = TRUE) else NA_real_,
    signal_max = if (any(is.finite(signal_raw))) max(signal_raw, na.rm = TRUE) else NA_real_,
    signal_sd = if (sum(is.finite(signal_raw)) > 1) stats::sd(signal_raw, na.rm = TRUE) else NA_real_,
    stringsAsFactors = FALSE
  )

  total_detected <- nrow(peaks)
  total_candidates <- sum(group_summary$candidate_peaks, na.rm = TRUE)

  status <- if (total_detected > 0) {
    "peaks_detected"
  } else if (total_candidates > 0) {
    "candidate_peaks_below_threshold"
  } else {
    "no_candidate_peaks"
  }

  overview <- data.frame(
    input_rows = nrow(dat),
    source_signal = source_signal,
    time_col = if (is.null(time_col)) NA_character_ else time_col,
    group_count = length(group_indices),
    candidate_peaks = total_candidates,
    detected_peaks = total_detected,
    amplitude_min = amplitude_min,
    recovery_fraction = recovery_fraction,
    status = status,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      peaks = peaks,
      group_summary = group_summary,
      signal_summary = signal_summary,
      settings = list(
        signal_col = signal_col,
        phasic_col = phasic_col,
        source_signal = source_signal,
        time_col = time_col,
        group_cols = group_cols,
        prefer_vendor_phasic = prefer_vendor_phasic,
        amplitude_min = amplitude_min,
        recovery_fraction = recovery_fraction,
        smooth_width = smooth_width,
        min_peak_distance = min_peak_distance,
        interpretation_notes = c(
          "SCR peaks are electrodermal response features, not emotional-valence labels.",
          "This simple detector is intended for transparent Gazepoint-native QC and feature extraction.",
          "For dense or strongly overlapping event designs, external deconvolution cross-checks such as NeuroKit2, Ledalab, PsPM, or cvxEDA may be appropriate."
        )
      )
    ),
    class = c("gazepoint_scr_peak_detection", "list")
  )
}

gpbiometrics_scr_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]

  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

gpbiometrics_scr_resolve_signal_col <- function(names_dat,
                                                signal_col,
                                                phasic_col,
                                                prefer_vendor_phasic) {
  if (!is.null(phasic_col)) {
    if (!phasic_col %in% names_dat) {
      stop("`phasic_col` was not found in `data`.", call. = FALSE)
    }
    return(phasic_col)
  }

  if (isTRUE(prefer_vendor_phasic)) {
    vendor_phasic <- gpbiometrics_scr_first_existing(
      names_dat,
      c("GSR_US_PHASIC", "gsr_us_phasic")
    )

    if (!is.null(vendor_phasic)) {
      return(vendor_phasic)
    }
  }

  if (!is.null(signal_col)) {
    if (!signal_col %in% names_dat) {
      stop("`signal_col` was not found in `data`.", call. = FALSE)
    }
    return(signal_col)
  }

  gpbiometrics_scr_first_existing(
    names_dat,
    c(
      "GSR_US", "gsr_us",
      "GSR_US_TONIC", "gsr_us_tonic",
      "GSR", "gsr"
    )
  )
}

gpbiometrics_scr_resolve_group_cols <- function(names_dat, group_cols) {
  if (!is.null(group_cols)) {
    return(unique(group_cols))
  }

  candidates <- c(
    "source_file",
    "source_participant",
    "USER",
    "USER_FILE",
    "participant",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "media_id",
    "media_name",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_scr_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_scr_smooth_signal <- function(x, smooth_width) {
  x <- suppressWarnings(as.numeric(x))

  if (smooth_width <= 1 || length(x) < smooth_width) {
    return(x)
  }

  if (smooth_width %% 2 == 0) {
    smooth_width <- smooth_width + 1L
  }

  filt <- rep(1 / smooth_width, smooth_width)
  smoothed <- as.numeric(stats::filter(x, filt, sides = 2))

  replace <- is.finite(smoothed)
  x[replace] <- smoothed[replace]

  x
}

gpbiometrics_scr_candidate_peaks <- function(x) {
  n <- length(x)

  if (n < 3) {
    return(integer())
  }

  out <- integer()

  for (i in 2:(n - 1)) {
    if (!is.finite(x[i - 1]) || !is.finite(x[i]) || !is.finite(x[i + 1])) {
      next
    }

    if (x[i] > x[i - 1] && x[i] >= x[i + 1]) {
      out <- c(out, i)
    }
  }

  out
}

gpbiometrics_scr_score_peak <- function(x,
                                        t,
                                        peak_local,
                                        amplitude_min,
                                        recovery_fraction) {
  onset <- peak_local

  while (onset > 1 &&
         is.finite(x[onset - 1]) &&
         is.finite(x[onset]) &&
         x[onset - 1] <= x[onset]) {
    onset <- onset - 1L
  }

  onset_value <- x[onset]
  peak_value <- x[peak_local]

  amplitude <- peak_value - onset_value

  if (!is.finite(amplitude) || amplitude < amplitude_min) {
    return(NULL)
  }

  recovery_target <- peak_value - recovery_fraction * amplitude

  recovery <- NA_integer_

  if (peak_local < length(x)) {
    after_peak <- (peak_local + 1L):length(x)
    recovery_candidates <- after_peak[
      is.finite(x[after_peak]) & x[after_peak] <= recovery_target
    ]

    if (length(recovery_candidates) > 0) {
      recovery <- recovery_candidates[1]
    }
  }

  onset_time <- t[onset]
  peak_time <- t[peak_local]
  recovery_time <- if (is.na(recovery)) NA_real_ else t[recovery]

  rise_time <- if (is.finite(onset_time) && is.finite(peak_time)) {
    peak_time - onset_time
  } else {
    NA_real_
  }

  recovery_time_after_peak <- if (is.finite(peak_time) && is.finite(recovery_time)) {
    recovery_time - peak_time
  } else {
    NA_real_
  }

  list(
    onset_index = onset,
    peak_index = peak_local,
    recovery_index = recovery,
    onset_time = onset_time,
    peak_time = peak_time,
    recovery_time = recovery_time,
    onset_value = onset_value,
    peak_value = peak_value,
    recovery_value = if (is.na(recovery)) NA_real_ else x[recovery],
    amplitude = amplitude,
    rise_time = rise_time,
    recovery_time_after_peak = recovery_time_after_peak,
    status = if (is.na(recovery)) {
      "detected_incomplete_recovery"
    } else {
      "detected"
    }
  )
}

gpbiometrics_scr_empty_peaks <- function(group_cols) {
  out <- data.frame(stringsAsFactors = FALSE)

  if (length(group_cols) > 0) {
    for (col in group_cols) {
      out[[col]] <- character()
    }
  }

  out$group_id <- character()
  out$peak_id <- integer()
  out$source_signal <- character()
  out$onset_row_id <- integer()
  out$peak_row_id <- integer()
  out$recovery_row_id <- integer()
  out$onset_index <- integer()
  out$peak_index <- integer()
  out$recovery_index <- integer()
  out$onset_time <- numeric()
  out$peak_time <- numeric()
  out$recovery_time <- numeric()
  out$onset_value <- numeric()
  out$peak_value <- numeric()
  out$recovery_value <- numeric()
  out$amplitude <- numeric()
  out$rise_time <- numeric()
  out$recovery_time_after_peak <- numeric()
  out$status <- character()

  out
}

gpbiometrics_scr_filter_candidate_peaks <- function(x,
                                                    candidate_peak_index,
                                                    min_peak_distance) {
  if (length(candidate_peak_index) <= 1 || min_peak_distance <= 1) {
    return(candidate_peak_index)
  }

  peak_values <- x[candidate_peak_index]
  order_by_height <- order(peak_values, decreasing = TRUE, na.last = NA)

  selected <- integer()

  for (candidate in candidate_peak_index[order_by_height]) {
    if (length(selected) == 0) {
      selected <- candidate
      next
    }

    if (all(abs(candidate - selected) >= min_peak_distance)) {
      selected <- c(selected, candidate)
    }
  }

  sort(selected)
}
