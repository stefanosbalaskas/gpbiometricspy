#' Summarise Gazepoint SCR responses in event windows
#'
#' Creates one row per event or TTL marker and links detected SCR peaks to
#' event-relative analysis and response windows. The helper is intended to
#' produce transparent event-level EDA/SCR features for downstream mixed models,
#' hurdle models, and reporting.
#'
#' @param data Optional Gazepoint biometric data frame. Required when `events`
#'   is `NULL` and events should be derived from TTL columns.
#' @param scr_peaks A `gazepoint_scr_peak_detection` object returned by
#'   `detect_gazepoint_scr_peaks()`, or a data frame of detected peaks.
#' @param events Optional event data frame. If `NULL`, events are derived from
#'   TTL columns in `data`.
#' @param time_col Optional time/counter column in `data`. Used for TTL-derived
#'   events.
#' @param event_time_col Optional event-time column in `events`. If `NULL`,
#'   common event-time column names are detected.
#' @param event_id_col Optional event identifier column in `events`.
#' @param event_label_col Optional event label/condition column in `events`.
#' @param group_cols Optional grouping columns used to match events and peaks.
#' @param ttl_cols Optional TTL marker columns used when `events = NULL`.
#' @param ttl_valid_col Optional TTL validity column. If supplied, TTL-derived
#'   events require this column to be non-zero.
#' @param event_detection Event-detection rule for TTL columns. `"rising"`
#'   detects rising edges; `"active"` treats every active TTL row as an event.
#' @param analysis_window Numeric length-two vector giving the event-relative
#'   analysis window in the same units as `time_col` or `event_time_col`.
#' @param response_window Numeric length-two vector giving the event-relative
#'   response window used for the binary SCR response flag.
#' @param amplitude_col Column in the peak table containing SCR amplitude.
#' @param peak_time_col Column in the peak table containing peak time.
#' @param onset_time_col Column in the peak table containing onset time.
#' @param rise_time_col Column in the peak table containing SCR rise time.
#' @param recovery_time_col Column in the peak table containing recovery time
#'   after peak.
#' @param peak_status_col Column in the peak table containing peak status.
#' @param peak_selection How to choose one peak when several peaks fall in the
#'   response window. `"largest_amplitude"` selects the largest response;
#'   `"first_peak"` selects the earliest peak.
#' @param collapse_simultaneous_events Logical. If `TRUE`, events with the same
#'   group and event time are collapsed into one row before matching peaks. This
#'   is useful when Gazepoint TTL0--TTL6 channels mark the same event
#'   simultaneously.
#'
#' @return A list with `overview`, `event_table`, `window_qc`, `events`,
#'   `peaks`, and `settings`.
#' @export
summarise_gazepoint_scr_event_windows <- function(data = NULL,
                                                  scr_peaks,
                                                  events = NULL,
                                                  time_col = NULL,
                                                  event_time_col = NULL,
                                                  event_id_col = NULL,
                                                  event_label_col = NULL,
                                                  group_cols = NULL,
                                                  ttl_cols = NULL,
                                                  ttl_valid_col = NULL,
                                                  event_detection = c("rising", "active"),
                                                  analysis_window = c(0, 6),
                                                  response_window = c(1, 4),
                                                  amplitude_col = "amplitude",
                                                  peak_time_col = "peak_time",
                                                  onset_time_col = "onset_time",
                                                  rise_time_col = "rise_time",
                                                  recovery_time_col = "recovery_time_after_peak",
                                                  peak_status_col = "status",
                                                  peak_selection = c("largest_amplitude", "first_peak"),
                                                  collapse_simultaneous_events = FALSE) {
  event_detection <- match.arg(event_detection)
  peak_selection <- match.arg(peak_selection)

  if (missing(scr_peaks) || is.null(scr_peaks)) {
    stop("`scr_peaks` must be supplied.", call. = FALSE)
  }

  if (!is.numeric(analysis_window) ||
      length(analysis_window) != 2 ||
      any(!is.finite(analysis_window)) ||
      analysis_window[2] < analysis_window[1]) {
    stop("`analysis_window` must be a finite length-two vector with end >= start.", call. = FALSE)
  }

  if (!is.numeric(response_window) ||
      length(response_window) != 2 ||
      any(!is.finite(response_window)) ||
      response_window[2] < response_window[1]) {
    stop("`response_window` must be a finite length-two vector with end >= start.", call. = FALSE)
  }

  if (response_window[1] < analysis_window[1] ||
      response_window[2] > analysis_window[2]) {
    stop("`response_window` must fall inside `analysis_window`.", call. = FALSE)
  }

  if (!is.logical(collapse_simultaneous_events) ||
      length(collapse_simultaneous_events) != 1 ||
      is.na(collapse_simultaneous_events)) {
    stop("`collapse_simultaneous_events` must be TRUE or FALSE.", call. = FALSE)
  }

  peaks <- gpbiometrics_scr_event_extract_peaks(scr_peaks)

  required_peak_cols <- c(amplitude_col, peak_time_col)
  missing_peak_cols <- setdiff(required_peak_cols, names(peaks))

  if (length(missing_peak_cols) > 0) {
    stop(
      "`scr_peaks` is missing required columns: ",
      paste(missing_peak_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (is.null(events)) {
    if (is.null(data) || !is.data.frame(data)) {
      stop("`data` must be supplied when `events` is NULL.", call. = FALSE)
    }

    data <- as.data.frame(data, stringsAsFactors = FALSE)

    if (is.null(time_col)) {
      time_col <- gpbiometrics_scr_event_first_existing(
        names(data),
        c(
          "time_ms", "timestamp_ms", "timestamp",
          "TIME", "Time", "time",
          "CNT", "cnt"
        )
      )
    }

    if (is.null(time_col) || !time_col %in% names(data)) {
      stop("No usable time column was found. Supply `time_col`.", call. = FALSE)
    }

    if (is.null(group_cols)) {
      group_cols <- gpbiometrics_scr_event_resolve_group_cols(names(data))
    }

    events_standard <- gpbiometrics_scr_event_derive_ttl_events(
      data = data,
      time_col = time_col,
      group_cols = group_cols,
      ttl_cols = ttl_cols,
      ttl_valid_col = ttl_valid_col,
      event_detection = event_detection
    )
  } else {
    events <- as.data.frame(events, stringsAsFactors = FALSE)

    if (is.null(event_time_col)) {
      event_time_col <- gpbiometrics_scr_event_first_existing(
        names(events),
        c(
          "event_time", "onset_time", "stimulus_time",
          "time_ms", "timestamp_ms", "timestamp",
          "TIME", "Time", "time",
          "CNT", "cnt"
        )
      )
    }

    if (is.null(event_time_col) || !event_time_col %in% names(events)) {
      stop("No usable event-time column was found. Supply `event_time_col`.", call. = FALSE)
    }

    if (is.null(group_cols)) {
      group_cols <- gpbiometrics_scr_event_resolve_common_group_cols(events, peaks)
    }

    events_standard <- gpbiometrics_scr_event_standardise_events(
      events = events,
      event_time_col = event_time_col,
      event_id_col = event_id_col,
      event_label_col = event_label_col,
      group_cols = group_cols
    )
  }

  missing_event_group_cols <- setdiff(group_cols, names(events_standard))
  missing_peak_group_cols <- setdiff(group_cols, names(peaks))

  if (length(group_cols) > 0 && length(missing_event_group_cols) > 0) {
    stop(
      "`events` is missing grouping columns: ",
      paste(missing_event_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  if (length(group_cols) > 0 &&
      length(missing_peak_group_cols) > 0 &&
      !"group_id" %in% names(peaks)) {
    stop(
      "`scr_peaks` is missing grouping columns: ",
      paste(missing_peak_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  events_standard$event_group_id <- gpbiometrics_scr_event_group_id(
    events_standard,
    group_cols
  )

  if (isTRUE(collapse_simultaneous_events)) {
    events_standard <- gpbiometrics_scr_event_collapse_simultaneous_events(
      events_standard
    )
  }

  peaks$event_group_id <- gpbiometrics_scr_event_group_id(
    peaks,
    group_cols
  )

  event_table <- gpbiometrics_scr_event_match_events_to_peaks(
    events = events_standard,
    peaks = peaks,
    group_cols = group_cols,
    analysis_window = analysis_window,
    response_window = response_window,
    amplitude_col = amplitude_col,
    peak_time_col = peak_time_col,
    onset_time_col = onset_time_col,
    rise_time_col = rise_time_col,
    recovery_time_col = recovery_time_col,
    peak_status_col = peak_status_col,
    peak_selection = peak_selection
  )

  window_qc <- gpbiometrics_scr_event_window_qc(
    event_table = event_table,
    group_cols = group_cols
  )

  event_count <- nrow(event_table)
  response_events <- sum(event_table$response_flag == 1, na.rm = TRUE)
  no_response_events <- sum(event_table$response_flag == 0, na.rm = TRUE)

  status <- if (event_count == 0) {
    "fail_no_events"
  } else if (response_events == 0) {
    "warn_no_scr_responses"
  } else {
    "scr_event_windows_summarised"
  }

  overview <- data.frame(
    event_count = event_count,
    peak_count = nrow(peaks),
    response_events = response_events,
    no_response_events = no_response_events,
    response_rate = if (event_count > 0) response_events / event_count else NA_real_,
    group_count = length(unique(events_standard$event_group_id)),
    analysis_window_start = analysis_window[1],
    analysis_window_end = analysis_window[2],
    response_window_start = response_window[1],
    response_window_end = response_window[2],
    status = status,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      event_table = event_table,
      window_qc = window_qc,
      events = events_standard,
      peaks = peaks,
      settings = list(
        time_col = time_col,
        event_time_col = event_time_col,
        event_id_col = event_id_col,
        event_label_col = event_label_col,
        group_cols = group_cols,
        ttl_cols = ttl_cols,
        ttl_valid_col = ttl_valid_col,
        event_detection = event_detection,
        analysis_window = analysis_window,
        response_window = response_window,
        amplitude_col = amplitude_col,
        peak_time_col = peak_time_col,
        onset_time_col = onset_time_col,
        rise_time_col = rise_time_col,
        recovery_time_col = recovery_time_col,
        peak_status_col = peak_status_col,
        peak_selection = peak_selection,
        collapse_simultaneous_events = collapse_simultaneous_events,
        interpretation_notes = c(
          "Event-window SCR summaries are electrodermal response features, not emotion or valence labels.",
          "Latency and amplitude depend on the selected response window, threshold, and peak-detection settings.",
          "For dense or overlapping event designs, sensitivity checks and optional external deconvolution cross-checks should be considered."
        )
      )
    ),
    class = c("gazepoint_scr_event_window_summary", "list")
  )
}

gpbiometrics_scr_event_extract_peaks <- function(scr_peaks) {
  if (inherits(scr_peaks, "gazepoint_scr_peak_detection") &&
      !is.null(scr_peaks$peaks)) {
    return(as.data.frame(scr_peaks$peaks, stringsAsFactors = FALSE))
  }

  if (is.data.frame(scr_peaks)) {
    return(as.data.frame(scr_peaks, stringsAsFactors = FALSE))
  }

  stop("`scr_peaks` must be a peak-detection object or a data frame.", call. = FALSE)
}

gpbiometrics_scr_event_first_existing <- function(names_dat, candidates) {
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

gpbiometrics_scr_event_resolve_group_cols <- function(names_dat) {
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

gpbiometrics_scr_event_resolve_common_group_cols <- function(events, peaks) {
  candidates <- gpbiometrics_scr_event_resolve_group_cols(
    intersect(names(events), names(peaks))
  )

  candidates[candidates %in% names(events) & candidates %in% names(peaks)]
}

gpbiometrics_scr_event_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    if ("group_id" %in% names(dat)) {
      return(as.character(dat$group_id))
    }

    return(rep("all", nrow(dat)))
  }

  if (!all(group_cols %in% names(dat))) {
    if ("group_id" %in% names(dat)) {
      return(as.character(dat$group_id))
    }

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

gpbiometrics_scr_event_standardise_events <- function(events,
                                                      event_time_col,
                                                      event_id_col,
                                                      event_label_col,
                                                      group_cols) {
  out <- events

  event_time <- suppressWarnings(as.numeric(out[[event_time_col]]))

  if (all(is.na(event_time))) {
    stop("`event_time_col` must contain numeric or numeric-coercible values.", call. = FALSE)
  }

  out$event_time <- event_time

  if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out$event_id <- as.character(out[[event_id_col]])
  } else if ("event_id" %in% names(out)) {
    out$event_id <- as.character(out$event_id)
  } else {
    out$event_id <- paste0("event_", seq_len(nrow(out)))
  }

  if (!is.null(event_label_col) && event_label_col %in% names(out)) {
    out$event_label <- as.character(out[[event_label_col]])
  } else if ("event_label" %in% names(out)) {
    out$event_label <- as.character(out$event_label)
  } else if ("condition" %in% names(out)) {
    out$event_label <- as.character(out$condition)
  } else {
    out$event_label <- "event"
  }

  out$source_row_id <- if ("source_row_id" %in% names(out)) {
    out$source_row_id
  } else {
    NA_integer_
  }

  missing_group_cols <- setdiff(group_cols, names(out))

  if (length(missing_group_cols) > 0) {
    stop(
      "`events` is missing grouping columns: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  out
}

gpbiometrics_scr_event_derive_ttl_events <- function(data,
                                                     time_col,
                                                     group_cols,
                                                     ttl_cols,
                                                     ttl_valid_col,
                                                     event_detection) {
  names_dat <- names(data)

  if (is.null(ttl_cols)) {
    ttl_cols <- grep("^TTL[0-9]+$", names_dat, value = TRUE)

    if ("ttl_marker" %in% names_dat) {
      ttl_cols <- c(ttl_cols, "ttl_marker")
    }
  }

  ttl_cols <- unique(ttl_cols)

  if (length(ttl_cols) == 0) {
    stop("No TTL columns were found. Supply `events` or `ttl_cols`.", call. = FALSE)
  }

  missing_ttl <- setdiff(ttl_cols, names_dat)

  if (length(missing_ttl) > 0) {
    stop(
      "`ttl_cols` not found in `data`: ",
      paste(missing_ttl, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(ttl_valid_col) && !ttl_valid_col %in% names_dat) {
    stop("`ttl_valid_col` was not found in `data`.", call. = FALSE)
  }

  missing_group_cols <- setdiff(group_cols, names_dat)

  if (length(missing_group_cols) > 0) {
    stop(
      "`data` is missing grouping columns: ",
      paste(missing_group_cols, collapse = ", "),
      call. = FALSE
    )
  }

  data$.gpbiometrics_row_id <- seq_len(nrow(data))
  group_id <- gpbiometrics_scr_event_group_id(data, group_cols)
  group_indices <- split(seq_len(nrow(data)), group_id, drop = TRUE)

  out <- list()

  for (group_name in names(group_indices)) {
    idx <- group_indices[[group_name]]

    valid <- rep(TRUE, length(idx))

    if (!is.null(ttl_valid_col)) {
      valid_raw <- suppressWarnings(as.numeric(data[[ttl_valid_col]][idx]))
      valid <- is.finite(valid_raw) & valid_raw != 0
    }

    for (ttl_col in ttl_cols) {
      ttl_raw <- suppressWarnings(as.numeric(data[[ttl_col]][idx]))
      active <- is.finite(ttl_raw) & ttl_raw != 0 & valid

      event_local <- if (identical(event_detection, "rising")) {
        active & !c(FALSE, utils::head(active, -1))
      } else {
        active
      }

      event_idx <- idx[which(event_local)]

      if (length(event_idx) == 0) {
        next
      }

      for (row_i in event_idx) {
        row <- data.frame(
          event_id = paste0(ttl_col, "_row_", data$.gpbiometrics_row_id[row_i]),
          event_label = ttl_col,
          event_source = "ttl",
          event_value = suppressWarnings(as.numeric(data[[ttl_col]][row_i])),
          event_time = suppressWarnings(as.numeric(data[[time_col]][row_i])),
          source_row_id = data$.gpbiometrics_row_id[row_i],
          stringsAsFactors = FALSE
        )

        if (length(group_cols) > 0) {
          group_values <- data[row_i, group_cols, drop = FALSE]
          row <- cbind(group_values, row)
        }

        out[[length(out) + 1L]] <- row
      }
    }
  }

  if (length(out) == 0) {
    empty <- data.frame(stringsAsFactors = FALSE)

    if (length(group_cols) > 0) {
      for (col in group_cols) {
        empty[[col]] <- character()
      }
    }

    empty$event_id <- character()
    empty$event_label <- character()
    empty$event_source <- character()
    empty$event_value <- numeric()
    empty$event_time <- numeric()
    empty$source_row_id <- integer()

    return(empty)
  }

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_event_collapse_simultaneous_events <- function(events) {
  if (nrow(events) == 0) {
    events$collapsed_event_count <- integer()
    events$collapsed_event_ids <- character()
    events$collapsed_event_labels <- character()
    return(events)
  }

  if (nrow(events) == 1) {
    events$collapsed_event_count <- 1L
    events$collapsed_event_ids <- as.character(events$event_id)
    events$collapsed_event_labels <- as.character(events$event_label)
    return(events)
  }

  event_time <- suppressWarnings(as.numeric(events$event_time))

  collapse_key <- ifelse(
    is.finite(event_time),
    paste(
      events$event_group_id,
      format(event_time, digits = 15, scientific = FALSE),
      sep = "||"
    ),
    paste(events$event_group_id, "nonfinite", seq_len(nrow(events)), sep = "||")
  )

  split_events <- split(events, collapse_key, drop = TRUE)

  collapsed <- lapply(split_events, function(d) {
    row <- d[1, , drop = FALSE]

    event_ids <- unique(as.character(d$event_id))
    event_labels <- unique(as.character(d$event_label))

    event_ids <- event_ids[!is.na(event_ids) & nzchar(event_ids)]
    event_labels <- event_labels[!is.na(event_labels) & nzchar(event_labels)]

    if (length(event_ids) == 0) {
      event_ids <- "event"
    }

    if (length(event_labels) == 0) {
      event_labels <- "event"
    }

    row$event_id <- paste(event_ids, collapse = "+")
    row$event_label <- paste(event_labels, collapse = "+")
    row$collapsed_event_count <- nrow(d)
    row$collapsed_event_ids <- paste(event_ids, collapse = "+")
    row$collapsed_event_labels <- paste(event_labels, collapse = "+")

    if ("event_value" %in% names(row)) {
      event_values <- suppressWarnings(as.numeric(d$event_value))
      finite_values <- event_values[is.finite(event_values)]

      row$event_value <- if (length(finite_values) == 1) {
        finite_values[1]
      } else {
        NA_real_
      }
    }

    row
  })

  out <- do.call(rbind, collapsed)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_event_match_events_to_peaks <- function(events,
                                                         peaks,
                                                         group_cols,
                                                         analysis_window,
                                                         response_window,
                                                         amplitude_col,
                                                         peak_time_col,
                                                         onset_time_col,
                                                         rise_time_col,
                                                         recovery_time_col,
                                                         peak_status_col,
                                                         peak_selection) {
  out <- list()

  for (i in seq_len(nrow(events))) {
    event <- events[i, , drop = FALSE]
    event_time <- event$event_time
    event_group_id <- event$event_group_id

    analysis_start <- event_time + analysis_window[1]
    analysis_end <- event_time + analysis_window[2]
    response_start <- event_time + response_window[1]
    response_end <- event_time + response_window[2]

    group_peaks <- peaks[
      peaks$event_group_id == event_group_id,
      ,
      drop = FALSE
    ]

    peak_time <- suppressWarnings(as.numeric(group_peaks[[peak_time_col]]))

    in_analysis <- is.finite(peak_time) &
      peak_time >= analysis_start &
      peak_time <= analysis_end

    in_response <- is.finite(peak_time) &
      peak_time >= response_start &
      peak_time <= response_end

    analysis_peaks <- group_peaks[in_analysis, , drop = FALSE]
    response_peaks <- group_peaks[in_response, , drop = FALSE]

    selected <- NULL

    if (nrow(response_peaks) > 0) {
      if (identical(peak_selection, "largest_amplitude")) {
        response_amp <- suppressWarnings(as.numeric(response_peaks[[amplitude_col]]))
        selected <- response_peaks[which.max(response_amp), , drop = FALSE]
      } else {
        response_time <- suppressWarnings(as.numeric(response_peaks[[peak_time_col]]))
        selected <- response_peaks[order(response_time)[1], , drop = FALSE]
      }
    }

    selected_peak_time <- NA_real_
    selected_onset_time <- NA_real_
    selected_amplitude <- NA_real_
    selected_rise_time <- NA_real_
    selected_recovery_time <- NA_real_
    selected_peak_status <- NA_character_
    selected_peak_id <- NA_character_

    if (!is.null(selected) && nrow(selected) > 0) {
      selected_peak_time <- suppressWarnings(as.numeric(selected[[peak_time_col]][1]))
      selected_amplitude <- suppressWarnings(as.numeric(selected[[amplitude_col]][1]))

      if (onset_time_col %in% names(selected)) {
        selected_onset_time <- suppressWarnings(as.numeric(selected[[onset_time_col]][1]))
      }

      if (rise_time_col %in% names(selected)) {
        selected_rise_time <- suppressWarnings(as.numeric(selected[[rise_time_col]][1]))
      }

      if (recovery_time_col %in% names(selected)) {
        selected_recovery_time <- suppressWarnings(as.numeric(selected[[recovery_time_col]][1]))
      }

      if (peak_status_col %in% names(selected)) {
        selected_peak_status <- as.character(selected[[peak_status_col]][1])
      }

      if ("peak_id" %in% names(selected)) {
        selected_peak_id <- as.character(selected$peak_id[1])
      }
    }

    response_flag <- as.integer(!is.null(selected) && nrow(selected) > 0)

    event_status <- if (!is.finite(event_time)) {
      "missing_event_time"
    } else if (nrow(analysis_peaks) == 0) {
      "no_peaks_in_analysis_window"
    } else if (nrow(response_peaks) == 0) {
      "no_peaks_in_response_window"
    } else {
      "response_detected"
    }

    row <- data.frame(
      event_id = event$event_id,
      event_label = event$event_label,
      event_time = event_time,
      event_group_id = event_group_id,
      source_row_id = event$source_row_id,
      window_start = analysis_start,
      window_end = analysis_end,
      response_start = response_start,
      response_end = response_end,
      response_flag = response_flag,
      n_candidate_peaks = nrow(analysis_peaks),
      n_response_window_peaks = nrow(response_peaks),
      selected_peak_id = selected_peak_id,
      selected_peak_time = selected_peak_time,
      selected_onset_time = selected_onset_time,
      scr_latency = selected_peak_time - event_time,
      scr_amplitude = selected_amplitude,
      scr_rise_time = selected_rise_time,
      scr_recovery_time = selected_recovery_time,
      selected_peak_status = selected_peak_status,
      event_status = event_status,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      group_values <- event[1, group_cols, drop = FALSE]
      row <- cbind(group_values, row)
    }

    out[[length(out) + 1L]] <- row
  }

  if (length(out) == 0) {
    return(gpbiometrics_scr_event_empty_event_table(group_cols))
  }

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_scr_event_empty_event_table <- function(group_cols) {
  out <- data.frame(stringsAsFactors = FALSE)

  if (length(group_cols) > 0) {
    for (col in group_cols) {
      out[[col]] <- character()
    }
  }

  out$event_id <- character()
  out$event_label <- character()
  out$event_time <- numeric()
  out$event_group_id <- character()
  out$source_row_id <- integer()
  out$window_start <- numeric()
  out$window_end <- numeric()
  out$response_start <- numeric()
  out$response_end <- numeric()
  out$response_flag <- integer()
  out$n_candidate_peaks <- integer()
  out$n_response_window_peaks <- integer()
  out$selected_peak_id <- character()
  out$selected_peak_time <- numeric()
  out$selected_onset_time <- numeric()
  out$scr_latency <- numeric()
  out$scr_amplitude <- numeric()
  out$scr_rise_time <- numeric()
  out$scr_recovery_time <- numeric()
  out$selected_peak_status <- character()
  out$event_status <- character()

  out
}

gpbiometrics_scr_event_window_qc <- function(event_table,
                                             group_cols) {
  if (nrow(event_table) == 0) {
    out <- data.frame(
      group_id = character(),
      event_count = integer(),
      response_events = integer(),
      response_rate = numeric(),
      no_response_events = integer(),
      events_with_candidate_peaks = integer(),
      stringsAsFactors = FALSE
    )

    return(out)
  }

  group_id <- event_table$event_group_id
  group_ids <- unique(group_id)

  out <- lapply(group_ids, function(group_id_i) {
    d <- event_table[group_id == group_id_i, , drop = FALSE]

    row <- data.frame(
      event_group_id = group_id_i,
      event_count = nrow(d),
      response_events = sum(d$response_flag == 1, na.rm = TRUE),
      response_rate = mean(d$response_flag == 1, na.rm = TRUE),
      no_response_events = sum(d$response_flag == 0, na.rm = TRUE),
      events_with_candidate_peaks = sum(d$n_candidate_peaks > 0, na.rm = TRUE),
      events_with_response_window_peaks = sum(d$n_response_window_peaks > 0, na.rm = TRUE),
      median_scr_amplitude = stats::median(d$scr_amplitude, na.rm = TRUE),
      median_scr_latency = stats::median(d$scr_latency, na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0) {
      group_values <- d[1, group_cols, drop = FALSE]
      row <- cbind(group_values, row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}
