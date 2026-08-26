#' Screen Gazepoint EDA/SCR nonresponders
#'
#' Screens groups, usually participants, for low or absent SCR responding using
#' either SCR event-window summaries or SCR peak-detection outputs. The helper
#' reports candidate nonresponders under explicit, user-controlled criteria.
#'
#' @param x A `gazepoint_scr_event_window_summary`,
#'   `gazepoint_scr_peak_detection`, or data frame.
#' @param group_cols Optional grouping columns, usually participant columns.
#' @param response_col Binary response column for event-window data.
#' @param amplitude_col SCR amplitude column.
#' @param min_events Minimum number of events required before event-window
#'   nonresponder classification is made.
#' @param min_response_events Minimum number of response events required.
#' @param min_response_rate Minimum response rate required.
#' @param min_detected_peaks Minimum detected peaks required when only peak data
#'   are available.
#'
#' @return A list with `overview`, `group_summary`, `candidate_nonresponders`,
#'   and `settings`.
#' @export
screen_gazepoint_eda_nonresponders <- function(x,
                                               group_cols = NULL,
                                               response_col = "response_flag",
                                               amplitude_col = "scr_amplitude",
                                               min_events = 1,
                                               min_response_events = 1,
                                               min_response_rate = 0.05,
                                               min_detected_peaks = 1) {
  if (missing(x) || is.null(x)) {
    stop("`x` must be supplied.", call. = FALSE)
  }

  if (!is.numeric(min_events) || length(min_events) != 1 ||
      !is.finite(min_events) || min_events < 0) {
    stop("`min_events` must be a single non-negative finite number.", call. = FALSE)
  }

  if (!is.numeric(min_response_events) ||
      length(min_response_events) != 1 ||
      !is.finite(min_response_events) ||
      min_response_events < 0) {
    stop("`min_response_events` must be a single non-negative finite number.", call. = FALSE)
  }

  if (!is.numeric(min_response_rate) ||
      length(min_response_rate) != 1 ||
      !is.finite(min_response_rate) ||
      min_response_rate < 0 ||
      min_response_rate > 1) {
    stop("`min_response_rate` must be between 0 and 1.", call. = FALSE)
  }

  if (!is.numeric(min_detected_peaks) ||
      length(min_detected_peaks) != 1 ||
      !is.finite(min_detected_peaks) ||
      min_detected_peaks < 0) {
    stop("`min_detected_peaks` must be a single non-negative finite number.", call. = FALSE)
  }

  event_table <- gpbiometrics_eda_nonresponder_extract_events(x)
  peak_table <- gpbiometrics_eda_nonresponder_extract_peaks(x)

  if (is.null(event_table) && is.null(peak_table)) {
    stop("`x` must contain SCR event-window or peak-detection data.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_eda_nonresponder_resolve_group_cols(
      event_table = event_table,
      peak_table = peak_table
    )
  }

  event_summary <- gpbiometrics_eda_nonresponder_event_summary(
    event_table = event_table,
    group_cols = group_cols,
    response_col = response_col,
    amplitude_col = amplitude_col
  )

  peak_summary <- gpbiometrics_eda_nonresponder_peak_summary(
    peak_table = peak_table,
    group_cols = group_cols,
    amplitude_col = amplitude_col
  )

  group_summary <- gpbiometrics_eda_nonresponder_merge_summaries(
    event_summary = event_summary,
    peak_summary = peak_summary,
    group_cols = group_cols,
    min_events = min_events,
    min_response_events = min_response_events,
    min_response_rate = min_response_rate,
    min_detected_peaks = min_detected_peaks
  )

  candidate_nonresponders <- group_summary[
    group_summary$candidate_nonresponder %in% TRUE,
    ,
    drop = FALSE
  ]

  overview <- data.frame(
    group_count = nrow(group_summary),
    candidate_nonresponder_count = nrow(candidate_nonresponders),
    event_window_groups = if (nrow(group_summary) > 0) {
      sum(!is.na(group_summary$event_count))
    } else {
      0L
    },
    peak_detection_groups = if (nrow(group_summary) > 0) {
      sum(!is.na(group_summary$detected_peaks))
    } else {
      0L
    },
    min_events = min_events,
    min_response_events = min_response_events,
    min_response_rate = min_response_rate,
    min_detected_peaks = min_detected_peaks,
    status = if (nrow(group_summary) == 0) {
      "fail_no_groups"
    } else if (nrow(candidate_nonresponders) > 0) {
      "candidate_nonresponders_detected"
    } else {
      "no_candidate_nonresponders_detected"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      group_summary = group_summary,
      candidate_nonresponders = candidate_nonresponders,
      settings = list(
        group_cols = group_cols,
        response_col = response_col,
        amplitude_col = amplitude_col,
        min_events = min_events,
        min_response_events = min_response_events,
        min_response_rate = min_response_rate,
        min_detected_peaks = min_detected_peaks,
        interpretation_notes = c(
          "Nonresponder screening is threshold-dependent and should be reported with the selected criteria.",
          "Candidate nonresponders should not be automatically excluded without study-specific justification.",
          "EDA/SCR response presence is not an emotional-valence measure."
        )
      )
    ),
    class = c("gazepoint_eda_nonresponder_screen", "list")
  )
}

gpbiometrics_eda_nonresponder_extract_events <- function(x) {
  if (inherits(x, "gazepoint_scr_event_window_summary") &&
      !is.null(x$event_table)) {
    return(as.data.frame(x$event_table, stringsAsFactors = FALSE))
  }

  if (is.list(x) && !is.null(x$event_table) && is.data.frame(x$event_table)) {
    return(as.data.frame(x$event_table, stringsAsFactors = FALSE))
  }

  if (is.data.frame(x) &&
      any(c("response_flag", "scr_response_binary") %in% names(x))) {
    return(as.data.frame(x, stringsAsFactors = FALSE))
  }

  NULL
}

gpbiometrics_eda_nonresponder_extract_peaks <- function(x) {
  if (inherits(x, "gazepoint_scr_peak_detection") && !is.null(x$peaks)) {
    return(as.data.frame(x$peaks, stringsAsFactors = FALSE))
  }

  if (inherits(x, "gazepoint_scr_event_window_summary") && !is.null(x$peaks)) {
    return(as.data.frame(x$peaks, stringsAsFactors = FALSE))
  }

  if (is.list(x) && !is.null(x$peaks) && is.data.frame(x$peaks)) {
    return(as.data.frame(x$peaks, stringsAsFactors = FALSE))
  }

  if (is.data.frame(x) && "peak_time" %in% names(x)) {
    return(as.data.frame(x, stringsAsFactors = FALSE))
  }

  NULL
}

gpbiometrics_eda_nonresponder_resolve_group_cols <- function(event_table,
                                                             peak_table) {
  candidates <- c(
    "source_participant",
    "participant",
    "subject",
    "subject_id",
    "USER",
    "USER_FILE",
    "source_file",
    "MEDIA_ID",
    "MEDIA_NAME",
    "trial",
    "trial_id"
  )

  event_names <- if (is.null(event_table)) character() else names(event_table)
  peak_names <- if (is.null(peak_table)) character() else names(peak_table)

  common <- candidates[candidates %in% event_names & candidates %in% peak_names]

  if (length(common) > 0) {
    return(common)
  }

  event_only <- candidates[candidates %in% event_names]

  if (length(event_only) > 0) {
    return(event_only)
  }

  peak_only <- candidates[candidates %in% peak_names]

  if (length(peak_only) > 0) {
    return(peak_only)
  }

  character()
}

gpbiometrics_eda_nonresponder_group_id <- function(dat, group_cols) {
  if (is.null(dat) || nrow(dat) == 0) {
    return(character())
  }

  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  if (!all(group_cols %in% names(dat))) {
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

gpbiometrics_eda_nonresponder_event_summary <- function(event_table,
                                                        group_cols,
                                                        response_col,
                                                        amplitude_col) {
  if (is.null(event_table) || nrow(event_table) == 0) {
    return(data.frame())
  }

  if (!response_col %in% names(event_table) &&
      "scr_response_binary" %in% names(event_table)) {
    response_col <- "scr_response_binary"
  }

  if (!response_col %in% names(event_table)) {
    return(data.frame())
  }

  event_table$.group_id <- gpbiometrics_eda_nonresponder_group_id(
    event_table,
    group_cols
  )

  group_ids <- unique(event_table$.group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- event_table[event_table$.group_id == group_id, , drop = FALSE]

    response <- suppressWarnings(as.numeric(d[[response_col]]))
    response_binary <- ifelse(is.finite(response) & response > 0, 1L, 0L)
    response_binary[!is.finite(response)] <- NA_integer_

    amplitude <- if (amplitude_col %in% names(d)) {
      suppressWarnings(as.numeric(d[[amplitude_col]]))
    } else {
      rep(NA_real_, nrow(d))
    }

    finite_amp <- amplitude[is.finite(amplitude)]

    row <- data.frame(
      group_id = group_id,
      event_count = nrow(d),
      response_events = sum(response_binary == 1L, na.rm = TRUE),
      no_response_events = sum(response_binary == 0L, na.rm = TRUE),
      response_rate = mean(response_binary == 1L, na.rm = TRUE),
      positive_amplitude_events = sum(is.finite(amplitude) & amplitude > 0, na.rm = TRUE),
      median_response_amplitude = if (length(finite_amp) > 0) {
        stats::median(finite_amp, na.rm = TRUE)
      } else {
        NA_real_
      },
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_eda_nonresponder_peak_summary <- function(peak_table,
                                                       group_cols,
                                                       amplitude_col) {
  if (is.null(peak_table) || nrow(peak_table) == 0) {
    return(data.frame())
  }

  peak_table$.group_id <- gpbiometrics_eda_nonresponder_group_id(
    peak_table,
    group_cols
  )

  group_ids <- unique(peak_table$.group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- peak_table[peak_table$.group_id == group_id, , drop = FALSE]

    amplitude <- if (amplitude_col %in% names(d)) {
      suppressWarnings(as.numeric(d[[amplitude_col]]))
    } else if ("amplitude" %in% names(d)) {
      suppressWarnings(as.numeric(d$amplitude))
    } else {
      rep(NA_real_, nrow(d))
    }

    finite_amp <- amplitude[is.finite(amplitude)]

    complete_recovery <- if ("status" %in% names(d)) {
      sum(as.character(d$status) == "detected", na.rm = TRUE)
    } else {
      NA_integer_
    }

    row <- data.frame(
      group_id = group_id,
      detected_peaks = nrow(d),
      complete_recovery_peaks = complete_recovery,
      incomplete_recovery_peaks = if ("status" %in% names(d)) {
        sum(as.character(d$status) == "detected_incomplete_recovery", na.rm = TRUE)
      } else {
        NA_integer_
      },
      median_peak_amplitude = if (length(finite_amp) > 0) {
        stats::median(finite_amp, na.rm = TRUE)
      } else {
        NA_real_
      },
      max_peak_amplitude = if (length(finite_amp) > 0) {
        max(finite_amp, na.rm = TRUE)
      } else {
        NA_real_
      },
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_eda_nonresponder_merge_summaries <- function(event_summary,
                                                          peak_summary,
                                                          group_cols,
                                                          min_events,
                                                          min_response_events,
                                                          min_response_rate,
                                                          min_detected_peaks) {
  event_ids <- if (nrow(event_summary) > 0) event_summary$group_id else character()
  peak_ids <- if (nrow(peak_summary) > 0) peak_summary$group_id else character()

  group_ids <- unique(c(event_ids, peak_ids))

  if (length(group_ids) == 0) {
    return(data.frame())
  }

  out <- lapply(group_ids, function(group_id) {
    event_row <- event_summary[event_summary$group_id == group_id, , drop = FALSE]
    peak_row <- peak_summary[peak_summary$group_id == group_id, , drop = FALSE]

    row <- data.frame(group_id = group_id, stringsAsFactors = FALSE)

    if (length(group_cols) > 0) {
      source_row <- if (nrow(event_row) > 0) event_row else peak_row

      if (nrow(source_row) > 0 && all(group_cols %in% names(source_row))) {
        row <- cbind(source_row[1, group_cols, drop = FALSE], row)
      }
    }

    event_count <- if (nrow(event_row) > 0) event_row$event_count else NA_integer_
    response_events <- if (nrow(event_row) > 0) event_row$response_events else NA_integer_
    response_rate <- if (nrow(event_row) > 0) event_row$response_rate else NA_real_
    detected_peaks <- if (nrow(peak_row) > 0) peak_row$detected_peaks else NA_integer_

    classification_basis <- if (is.finite(event_count)) {
      "event_windows"
    } else if (is.finite(detected_peaks)) {
      "peak_detection"
    } else {
      "none"
    }

    candidate_nonresponder <- NA

    classification_status <- "insufficient_information"

    if (identical(classification_basis, "event_windows")) {
      if (event_count < min_events) {
        candidate_nonresponder <- NA
        classification_status <- "insufficient_events"
      } else {
        candidate_nonresponder <- response_events < min_response_events ||
          response_rate < min_response_rate
        classification_status <- if (candidate_nonresponder) {
          "candidate_nonresponder"
        } else {
          "responder_detected"
        }
      }
    } else if (identical(classification_basis, "peak_detection")) {
      candidate_nonresponder <- detected_peaks < min_detected_peaks
      classification_status <- if (candidate_nonresponder) {
        "candidate_nonresponder"
      } else {
        "responder_detected"
      }
    }

    event_cols <- c(
      "event_count",
      "response_events",
      "no_response_events",
      "response_rate",
      "positive_amplitude_events",
      "median_response_amplitude"
    )

    peak_cols <- c(
      "detected_peaks",
      "complete_recovery_peaks",
      "incomplete_recovery_peaks",
      "median_peak_amplitude",
      "max_peak_amplitude"
    )

    for (col in event_cols) {
      row[[col]] <- if (nrow(event_row) > 0 && col %in% names(event_row)) {
        event_row[[col]][1]
      } else {
        NA
      }
    }

    for (col in peak_cols) {
      row[[col]] <- if (nrow(peak_row) > 0 && col %in% names(peak_row)) {
        peak_row[[col]][1]
      } else {
        NA
      }
    }

    row$classification_basis <- classification_basis
    row$candidate_nonresponder <- candidate_nonresponder
    row$class_status <- classification_status

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}
