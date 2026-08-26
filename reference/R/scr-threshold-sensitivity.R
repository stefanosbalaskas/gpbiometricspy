#' Run Gazepoint SCR threshold sensitivity checks
#'
#' Re-runs SCR peak detection across combinations of amplitude thresholds and
#' minimum peak-distance settings. Optionally, it also carries each peak-detection
#' result through SCR event-window summaries so users can see how preprocessing
#' choices affect event-level response rates.
#'
#' @param data A Gazepoint biometric data frame.
#' @param phasic_col Optional phasic EDA signal column, typically
#'   `GSR_US_PHASIC`.
#' @param signal_col Optional conductance-like fallback signal column, typically
#'   `GSR_US`.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param amplitude_min_values Numeric vector of SCR amplitude thresholds.
#' @param min_peak_distance_values Numeric vector of minimum peak distances.
#' @param recovery_fraction Fraction used by `detect_gazepoint_scr_peaks()` to
#'   define recovery.
#' @param smooth_width Optional moving-average width passed to
#'   `detect_gazepoint_scr_peaks()`.
#' @param events Optional event table passed to
#'   `summarise_gazepoint_scr_event_windows()`.
#' @param event_time_col Optional event-time column when `events` is supplied.
#' @param event_id_col Optional event identifier column when `events` is supplied.
#' @param event_label_col Optional event label column when `events` is supplied.
#' @param ttl_cols Optional TTL columns for event derivation when `events` is
#'   `NULL`.
#' @param ttl_valid_col Optional TTL validity column.
#' @param event_detection Event-detection rule for TTL columns.
#' @param analysis_window Event-relative analysis window.
#' @param response_window Event-relative response window.
#' @param peak_selection Peak-selection rule for event-window summaries.
#' @param collapse_simultaneous_events Logical. Passed to
#'   `summarise_gazepoint_scr_event_windows()`.
#' @param include_event_windows Logical. If `TRUE`, compute event-window
#'   summaries for each sensitivity setting.
#' @param keep_objects Logical. If `TRUE`, retain peak-detection and
#'   event-window objects in list columns.
#'
#' @return A list with `overview`, `sensitivity_grid`,
#'   `peak_group_summary`, `event_window_summary`, optional `objects`, and
#'   `settings`.
#' @export
run_gazepoint_scr_threshold_sensitivity <- function(data,
                                                    phasic_col = NULL,
                                                    signal_col = NULL,
                                                    time_col = NULL,
                                                    group_cols = NULL,
                                                    amplitude_min_values = c(0.005, 0.01, 0.02, 0.03),
                                                    min_peak_distance_values = c(1, 5, 10, 20, 30),
                                                    recovery_fraction = 0.5,
                                                    smooth_width = 1,
                                                    events = NULL,
                                                    event_time_col = NULL,
                                                    event_id_col = NULL,
                                                    event_label_col = NULL,
                                                    ttl_cols = NULL,
                                                    ttl_valid_col = NULL,
                                                    event_detection = c("rising", "active"),
                                                    analysis_window = c(0, 6),
                                                    response_window = c(1, 4),
                                                    peak_selection = c("largest_amplitude", "first_peak"),
                                                    collapse_simultaneous_events = FALSE,
                                                    include_event_windows = TRUE,
                                                    keep_objects = FALSE) {
  event_detection <- match.arg(event_detection)
  peak_selection <- match.arg(peak_selection)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.numeric(amplitude_min_values) ||
      length(amplitude_min_values) == 0 ||
      any(!is.finite(amplitude_min_values)) ||
      any(amplitude_min_values < 0)) {
    stop("`amplitude_min_values` must be a non-empty non-negative numeric vector.", call. = FALSE)
  }

  if (!is.numeric(min_peak_distance_values) ||
      length(min_peak_distance_values) == 0 ||
      any(!is.finite(min_peak_distance_values)) ||
      any(min_peak_distance_values < 1)) {
    stop("`min_peak_distance_values` must be a non-empty numeric vector with values >= 1.", call. = FALSE)
  }

  if (!is.logical(include_event_windows) ||
      length(include_event_windows) != 1 ||
      is.na(include_event_windows)) {
    stop("`include_event_windows` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(keep_objects) ||
      length(keep_objects) != 1 ||
      is.na(keep_objects)) {
    stop("`keep_objects` must be TRUE or FALSE.", call. = FALSE)
  }

  amplitude_min_values <- sort(unique(amplitude_min_values))
  min_peak_distance_values <- sort(unique(as.integer(round(min_peak_distance_values))))

  grid <- expand.grid(
    amplitude_min = amplitude_min_values,
    min_peak_distance = min_peak_distance_values,
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )

  sensitivity_rows <- list()
  peak_group_rows <- list()
  event_window_rows <- list()
  kept_objects <- list()

  for (i in seq_len(nrow(grid))) {
    amp <- grid$amplitude_min[i]
    dist <- grid$min_peak_distance[i]

    peak_result <- tryCatch(
      detect_gazepoint_scr_peaks(
        data = data,
        signal_col = signal_col,
        phasic_col = phasic_col,
        time_col = time_col,
        group_cols = group_cols,
        amplitude_min = amp,
        recovery_fraction = recovery_fraction,
        smooth_width = smooth_width,
        min_peak_distance = dist
      ),
      error = function(e) e
    )

    if (inherits(peak_result, "error")) {
      sensitivity_rows[[length(sensitivity_rows) + 1L]] <- data.frame(
        amplitude_min = amp,
        min_peak_distance = dist,
        source_signal = NA_character_,
        candidate_peaks = NA_integer_,
        detected_peaks = NA_integer_,
        incomplete_recovery_peaks = NA_integer_,
        groups_with_detected_peaks = NA_integer_,
        event_count = NA_integer_,
        response_events = NA_integer_,
        response_rate = NA_real_,
        event_window_status = NA_character_,
        status = "peak_detection_error",
        error_message = conditionMessage(peak_result),
        stringsAsFactors = FALSE
      )
      next
    }

    peak_group <- peak_result$group_summary
    peak_group$amplitude_min <- amp
    peak_group$min_peak_distance <- dist
    peak_group_rows[[length(peak_group_rows) + 1L]] <- peak_group

    event_result <- NULL
    event_status <- NA_character_
    event_count <- NA_integer_
    response_events <- NA_integer_
    response_rate <- NA_real_

    if (isTRUE(include_event_windows)) {
      event_result <- tryCatch(
        summarise_gazepoint_scr_event_windows(
          data = data,
          scr_peaks = peak_result,
          events = events,
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
          peak_selection = peak_selection,
          collapse_simultaneous_events = collapse_simultaneous_events
        ),
        error = function(e) e
      )

      if (inherits(event_result, "error")) {
        event_status <- "event_window_error"
      } else {
        event_status <- event_result$overview$status
        event_count <- event_result$overview$event_count
        response_events <- event_result$overview$response_events
        response_rate <- event_result$overview$response_rate

        event_summary <- event_result$window_qc
        event_summary$amplitude_min <- amp
        event_summary$min_peak_distance <- dist
        event_window_rows[[length(event_window_rows) + 1L]] <- event_summary
      }
    }

    sensitivity_rows[[length(sensitivity_rows) + 1L]] <- data.frame(
      amplitude_min = amp,
      min_peak_distance = dist,
      source_signal = peak_result$overview$source_signal,
      candidate_peaks = peak_result$overview$candidate_peaks,
      detected_peaks = peak_result$overview$detected_peaks,
      incomplete_recovery_peaks = sum(
        peak_result$group_summary$incomplete_recovery_peaks,
        na.rm = TRUE
      ),
      groups_with_detected_peaks = sum(
        peak_result$group_summary$detected_peaks > 0,
        na.rm = TRUE
      ),
      event_count = event_count,
      response_events = response_events,
      response_rate = response_rate,
      event_window_status = event_status,
      status = "sensitivity_completed",
      error_message = NA_character_,
      stringsAsFactors = FALSE
    )

    if (isTRUE(keep_objects)) {
      kept_objects[[paste0("amp_", amp, "_dist_", dist)]] <- list(
        peaks = peak_result,
        event_windows = if (inherits(event_result, "error")) NULL else event_result
      )
    }
  }

  sensitivity_grid <- do.call(rbind, sensitivity_rows)
  rownames(sensitivity_grid) <- NULL

  peak_group_summary <- if (length(peak_group_rows) > 0) {
    out <- do.call(rbind, peak_group_rows)
    rownames(out) <- NULL
    out
  } else {
    data.frame()
  }

  event_window_summary <- if (length(event_window_rows) > 0) {
    out <- do.call(rbind, event_window_rows)
    rownames(out) <- NULL
    out
  } else {
    data.frame()
  }

  completed_rows <- sum(sensitivity_grid$status == "sensitivity_completed", na.rm = TRUE)
  error_rows <- sum(sensitivity_grid$status != "sensitivity_completed", na.rm = TRUE)

  overview <- data.frame(
    grid_rows = nrow(sensitivity_grid),
    completed_rows = completed_rows,
    error_rows = error_rows,
    amplitude_min_count = length(amplitude_min_values),
    min_peak_distance_count = length(min_peak_distance_values),
    include_event_windows = include_event_windows,
    keep_objects = keep_objects,
    status = if (completed_rows == 0) {
      "fail_no_sensitivity_rows_completed"
    } else if (error_rows > 0) {
      "warn_some_sensitivity_rows_failed"
    } else {
      "scr_threshold_sensitivity_completed"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      sensitivity_grid = sensitivity_grid,
      peak_group_summary = peak_group_summary,
      event_window_summary = event_window_summary,
      objects = if (isTRUE(keep_objects)) kept_objects else NULL,
      settings = list(
        phasic_col = phasic_col,
        signal_col = signal_col,
        time_col = time_col,
        group_cols = group_cols,
        amplitude_min_values = amplitude_min_values,
        min_peak_distance_values = min_peak_distance_values,
        recovery_fraction = recovery_fraction,
        smooth_width = smooth_width,
        ttl_cols = ttl_cols,
        ttl_valid_col = ttl_valid_col,
        event_detection = event_detection,
        analysis_window = analysis_window,
        response_window = response_window,
        peak_selection = peak_selection,
        collapse_simultaneous_events = collapse_simultaneous_events,
        include_event_windows = include_event_windows,
        keep_objects = keep_objects,
        interpretation_notes = c(
          "Sensitivity summaries show how SCR response counts vary across detection settings.",
          "They are intended for robustness assessment and reporting, not for selecting thresholds after inspecting desired results.",
          "EDA/SCR features should be interpreted as electrodermal response features, not emotional valence."
        )
      )
    ),
    class = c("gazepoint_scr_threshold_sensitivity", "list")
  )
}
