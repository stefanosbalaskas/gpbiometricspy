# Final roadmap-gap helpers for gpbiometrics

#' Validate Gazepoint gaze data
#'
#' Consolidates coordinate, validity, missingness, timestamp, sampling, and
#' large-gap checks for sample-level Gazepoint gaze data.
#'
#' @param data A sample-level data frame.
#' @param time_col Time column. If `NULL`, a likely column is inferred.
#' @param x_col Horizontal gaze-coordinate column.
#' @param y_col Vertical gaze-coordinate column.
#' @param validity_cols Optional validity columns. Logical values and positive
#'   numeric values are treated as valid.
#' @param group_cols Optional grouping columns, such as participant and trial.
#' @param coordinate_system Coordinate system: `"auto"`, `"normalized"`,
#'   `"pixels"`, or `"degrees"`.
#' @param screen_width_px,screen_height_px Screen dimensions required for
#'   bounded pixel-coordinate checks.
#' @param time_unit Time unit: `"auto"`, `"seconds"`, `"milliseconds"`, or
#'   `"samples"`.
#' @param sampling_rate_hz Sampling rate required for sample-index time.
#' @param expected_sampling_rate_hz Optional expected sampling rate.
#' @param sampling_tolerance Relative tolerance around the expected sampling
#'   interval.
#' @param missing_threshold Maximum acceptable missing-gaze proportion.
#' @param gap_multiplier A gap is flagged when it exceeds this multiple of the
#'   expected or median interval.
#'
#' @return A `"gazepoint_gaze_validation"` object containing row-level flags,
#'   group summaries, checks, an overall summary, and resolved settings.
#'
#' @export
validate_gazepoint_gaze <- function(
    data,
    time_col = NULL,
    x_col = NULL,
    y_col = NULL,
    validity_cols = NULL,
    group_cols = NULL,
    coordinate_system = c("auto", "normalized", "pixels", "degrees"),
    screen_width_px = NULL,
    screen_height_px = NULL,
    time_unit = c("auto", "seconds", "milliseconds", "samples"),
    sampling_rate_hz = NULL,
    expected_sampling_rate_hz = NULL,
    sampling_tolerance = 0.20,
    missing_threshold = 0.20,
    gap_multiplier = 3) {
  coordinate_system <- match.arg(coordinate_system)
  time_unit <- match.arg(time_unit)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }
  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  .gp_gap_nonnegative_scalar(sampling_tolerance, "sampling_tolerance")
  .gp_gap_proportion(missing_threshold, "missing_threshold")
  .gp_gap_positive_scalar(gap_multiplier, "gap_multiplier")

  time_col <- .gp_gap_resolve_col(
    data,
    time_col,
    c("time_s", "time_ms", "time", "timestamp", "MSTIMER", "TIME", "CNT"),
    "time",
    TRUE
  )
  x_col <- .gp_gap_resolve_col(
    data,
    x_col,
    c("gaze_x", "x", "FPOGX", "BPOGX", "LPOGX", "RPOGX", "POGX"),
    "horizontal gaze coordinate",
    TRUE
  )
  y_col <- .gp_gap_resolve_col(
    data,
    y_col,
    c("gaze_y", "y", "FPOGY", "BPOGY", "LPOGY", "RPOGY", "POGY"),
    "vertical gaze coordinate",
    TRUE
  )

  group_cols <- .gp_gap_existing_cols(data, group_cols, "group_cols")

  if (is.null(validity_cols)) {
    candidates <- c(
      "valid", "validity", "gaze_valid", "FPOGV", "BPOGV",
      "LPOGV", "RPOGV", "LPOGV", "RPOGV"
    )
    validity_cols <- names(data)[tolower(names(data)) %in% tolower(candidates)]
  } else {
    validity_cols <- .gp_gap_existing_cols(data, validity_cols, "validity_cols")
  }

  raw_time <- suppressWarnings(as.numeric(data[[time_col]]))
  gaze_x <- suppressWarnings(as.numeric(data[[x_col]]))
  gaze_y <- suppressWarnings(as.numeric(data[[y_col]]))

  if (all(!is.finite(raw_time))) {
    stop("The selected time column contains no finite numeric values.", call. = FALSE)
  }

  resolved_time_unit <- .gp_gap_resolve_time_unit(raw_time, time_col, time_unit)
  if (identical(resolved_time_unit, "samples")) {
    .gp_gap_positive_scalar(sampling_rate_hz, "sampling_rate_hz")
  }
  time_s <- .gp_gap_to_seconds(raw_time, resolved_time_unit, sampling_rate_hz)

  if (!is.null(expected_sampling_rate_hz)) {
    .gp_gap_positive_scalar(
      expected_sampling_rate_hz,
      "expected_sampling_rate_hz"
    )
  }

  if (!is.null(screen_width_px)) {
    .gp_gap_positive_scalar(screen_width_px, "screen_width_px")
  }
  if (!is.null(screen_height_px)) {
    .gp_gap_positive_scalar(screen_height_px, "screen_height_px")
  }

  finite_xy <- is.finite(gaze_x) & is.finite(gaze_y)
  resolved_coordinate_system <- .gp_gap_coordinate_system(
    gaze_x,
    gaze_y,
    coordinate_system,
    screen_width_px,
    screen_height_px
  )

  invalid_by_validity <- rep(FALSE, nrow(data))
  if (length(validity_cols) > 0L) {
    validity_matrix <- vapply(
      validity_cols,
      function(column) .gp_gap_valid_values(data[[column]]),
      logical(nrow(data))
    )
    if (is.null(dim(validity_matrix))) {
      validity_matrix <- matrix(validity_matrix, ncol = 1L)
    }
    invalid_by_validity <- rowSums(validity_matrix) < ncol(validity_matrix)
  }

  missing_xy <- !finite_xy
  gaze_invalid <- missing_xy | invalid_by_validity

  out_of_range <- rep(FALSE, nrow(data))
  range_assessed <- TRUE

  if (identical(resolved_coordinate_system, "normalized")) {
    out_of_range <- finite_xy &
      (gaze_x < 0 | gaze_x > 1 | gaze_y < 0 | gaze_y > 1)
  } else if (identical(resolved_coordinate_system, "pixels")) {
    if (is.null(screen_width_px) || is.null(screen_height_px)) {
      range_assessed <- FALSE
    } else {
      out_of_range <- finite_xy &
        (
          gaze_x < 0 |
            gaze_x > screen_width_px |
            gaze_y < 0 |
            gaze_y > screen_height_px
        )
    }
  } else {
    range_assessed <- FALSE
  }

  flags <- data
  flags$.gaze_time_s <- time_s
  flags$.gaze_missing_xy <- missing_xy
  flags$.gaze_invalid_validity <- invalid_by_validity
  flags$.gaze_invalid <- gaze_invalid
  flags$.gaze_out_of_range <- out_of_range
  flags$.gaze_duplicate_time <- FALSE
  flags$.gaze_nonmonotonic_time <- FALSE
  flags$.gaze_large_gap_after <- FALSE

  index_groups <- .gp_gap_split_indices(data, group_cols)
  group_rows <- vector("list", length(index_groups))
  names(group_rows) <- names(index_groups)

  for (i in seq_along(index_groups)) {
    idx <- index_groups[[i]]
    local_time <- time_s[idx]
    local_x <- gaze_x[idx]
    local_y <- gaze_y[idx]
    local_invalid <- gaze_invalid[idx]
    local_out <- out_of_range[idx]

    dt <- diff(local_time)
    duplicate_local <- c(FALSE, is.finite(dt) & dt == 0)
    nonmonotonic_local <- c(FALSE, is.finite(dt) & dt < 0)

    positive_dt <- dt[is.finite(dt) & dt > 0]
    median_interval <- if (length(positive_dt) > 0L) {
      stats::median(positive_dt)
    } else {
      NA_real_
    }

    inferred_rate <- if (is.finite(median_interval) && median_interval > 0) {
      1 / median_interval
    } else {
      NA_real_
    }

    reference_interval <- if (!is.null(expected_sampling_rate_hz)) {
      1 / expected_sampling_rate_hz
    } else {
      median_interval
    }

    large_gap_local <- rep(FALSE, length(idx))
    if (length(dt) > 0L && is.finite(reference_interval) && reference_interval > 0) {
      large_gap_local[seq_along(dt)] <- is.finite(dt) &
        dt > gap_multiplier * reference_interval
    }

    flags$.gaze_duplicate_time[idx] <- duplicate_local
    flags$.gaze_nonmonotonic_time[idx] <- nonmonotonic_local
    flags$.gaze_large_gap_after[idx] <- large_gap_local

    rate_deviation <- if (
      !is.null(expected_sampling_rate_hz) &&
        is.finite(inferred_rate)
    ) {
      abs(inferred_rate - expected_sampling_rate_hz) /
        expected_sampling_rate_hz
    } else {
      NA_real_
    }

    grouping_values <- if (length(group_cols) > 0L) {
      data[idx[1L], group_cols, drop = FALSE]
    } else {
      data.frame(.group = "all", stringsAsFactors = FALSE)
    }

    group_rows[[i]] <- cbind(
      grouping_values,
      data.frame(
        n_samples = length(idx),
        finite_time_count = sum(is.finite(local_time)),
        missing_gaze_count = sum(local_invalid),
        missing_gaze_rate = mean(local_invalid),
        out_of_range_count = sum(local_out),
        out_of_range_rate = mean(local_out),
        duplicate_time_count = sum(duplicate_local),
        nonmonotonic_time_count = sum(nonmonotonic_local),
        large_gap_count = sum(large_gap_local),
        median_interval_s = median_interval,
        inferred_sampling_rate_hz = inferred_rate,
        relative_sampling_rate_deviation = rate_deviation,
        stringsAsFactors = FALSE
      )
    )
  }

  groups <- do.call(rbind, group_rows)
  rownames(groups) <- NULL

  overall_missing_rate <- mean(gaze_invalid)
  overall_out_rate <- mean(out_of_range)
  total_duplicate <- sum(flags$.gaze_duplicate_time)
  total_nonmonotonic <- sum(flags$.gaze_nonmonotonic_time)
  total_gaps <- sum(flags$.gaze_large_gap_after)

  inferred_rates <- groups$inferred_sampling_rate_hz[
    is.finite(groups$inferred_sampling_rate_hz)
  ]
  median_inferred_rate <- if (length(inferred_rates) > 0L) {
    stats::median(inferred_rates)
  } else {
    NA_real_
  }

  overall_sampling_deviation <- if (
    !is.null(expected_sampling_rate_hz) &&
      is.finite(median_inferred_rate)
  ) {
    abs(median_inferred_rate - expected_sampling_rate_hz) /
      expected_sampling_rate_hz
  } else {
    NA_real_
  }

  checks <- rbind(
    .gp_gap_check(
      "finite_time",
      if (all(is.finite(time_s))) "pass" else "fail",
      sum(is.finite(time_s)),
      nrow(data),
      "Finite timestamp count versus total rows."
    ),
    .gp_gap_check(
      "monotonic_time",
      if (total_nonmonotonic == 0L) "pass" else "fail",
      total_nonmonotonic,
      0,
      "Negative within-group time differences."
    ),
    .gp_gap_check(
      "duplicate_time",
      if (total_duplicate == 0L) "pass" else "warn",
      total_duplicate,
      0,
      "Repeated within-group timestamps."
    ),
    .gp_gap_check(
      "missing_gaze",
      if (overall_missing_rate <= missing_threshold) "pass" else "warn",
      overall_missing_rate,
      missing_threshold,
      "Rows with missing coordinates or invalid validity flags."
    ),
    .gp_gap_check(
      "coordinate_range",
      if (!range_assessed) {
        "not_assessed"
      } else if (overall_out_rate == 0) {
        "pass"
      } else {
        "warn"
      },
      if (range_assessed) overall_out_rate else NA_real_,
      0,
      paste0("Resolved coordinate system: ", resolved_coordinate_system, ".")
    ),
    .gp_gap_check(
      "sampling_rate",
      if (is.null(expected_sampling_rate_hz)) {
        "not_assessed"
      } else if (
        is.finite(overall_sampling_deviation) &&
          overall_sampling_deviation <= sampling_tolerance
      ) {
        "pass"
      } else {
        "warn"
      },
      overall_sampling_deviation,
      sampling_tolerance,
      "Relative deviation from the expected sampling rate."
    ),
    .gp_gap_check(
      "large_time_gaps",
      if (total_gaps == 0L) "pass" else "warn",
      total_gaps,
      0,
      paste0("Gap threshold multiplier: ", gap_multiplier, ".")
    )
  )

  rownames(checks) <- NULL

  status_rank <- c(
    not_assessed = 0L,
    pass = 1L,
    warn = 2L,
    fail = 3L
  )
  overall_status <- names(status_rank)[
    which.max(status_rank[checks$status])
  ]

  summary <- data.frame(
    status = overall_status,
    n_samples = nrow(data),
    n_groups = length(index_groups),
    missing_gaze_rate = overall_missing_rate,
    out_of_range_rate = if (range_assessed) overall_out_rate else NA_real_,
    duplicate_time_count = total_duplicate,
    nonmonotonic_time_count = total_nonmonotonic,
    large_gap_count = total_gaps,
    median_inferred_sampling_rate_hz = median_inferred_rate,
    coordinate_system = resolved_coordinate_system,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      summary = summary,
      checks = checks,
      groups = groups,
      data = flags,
      columns = list(
        time = time_col,
        x = x_col,
        y = y_col,
        validity = validity_cols,
        groups = group_cols
      ),
      settings = list(
        coordinate_system = resolved_coordinate_system,
        range_assessed = range_assessed,
        screen_width_px = screen_width_px,
        screen_height_px = screen_height_px,
        time_unit = resolved_time_unit,
        sampling_rate_hz = sampling_rate_hz,
        expected_sampling_rate_hz = expected_sampling_rate_hz,
        sampling_tolerance = sampling_tolerance,
        missing_threshold = missing_threshold,
        gap_multiplier = gap_multiplier
      )
    ),
    class = c("gazepoint_gaze_validation", "list")
  )
}

#' @export
print.gazepoint_gaze_validation <- function(x, ...) {
  cat("Gazepoint gaze validation\n")
  cat("  Status: ", x$summary$status, "\n", sep = "")
  cat("  Samples: ", x$summary$n_samples, "\n", sep = "")
  cat(
    "  Missing/invalid gaze: ",
    formatC(100 * x$summary$missing_gaze_rate, digits = 2, format = "f"),
    "%\n",
    sep = ""
  )
  cat(
    "  Coordinate system: ",
    x$summary$coordinate_system,
    "\n",
    sep = ""
  )
  invisible(x)
}

#' Summarise Gazepoint fixations by area of interest
#'
#' Produces participant-, trial-, and AOI-level fixation counts, duration
#' summaries, dwell proportions, and optional first-fixation latency.
#'
#' @param fixations Fixation-level data frame.
#' @param aoi_col AOI label column.
#' @param participant_col Optional participant column.
#' @param trial_col Optional trial column.
#' @param group_cols Additional grouping columns.
#' @param start_col Fixation-start column.
#' @param end_col Optional fixation-end column.
#' @param duration_col Optional fixation-duration column.
#' @param event_onset_col Optional event/stimulus onset column.
#' @param time_unit Unit for start, end, and event-onset values.
#' @param duration_unit Unit for duration values.
#' @param sampling_rate_hz Sampling frequency required when time or duration values are represented as sample indices.
#' @param include_unassigned Include rows with missing or empty AOI labels.
#' @param unassigned_label Label used for retained unassigned rows.
#'
#' @return A data frame of class `"gazepoint_fixation_aoi_summary"`.
#'
#' @export
summarise_gazepoint_fixations_by_aoi <- function(
    fixations,
    aoi_col = NULL,
    participant_col = NULL,
    trial_col = NULL,
    group_cols = NULL,
    start_col = NULL,
    end_col = NULL,
    duration_col = NULL,
    event_onset_col = NULL,
    time_unit = c("auto", "seconds", "milliseconds", "samples"),
    duration_unit = c("auto", "seconds", "milliseconds", "samples"),
    sampling_rate_hz = NULL,
    include_unassigned = FALSE,
    unassigned_label = "UNASSIGNED") {
  time_unit <- match.arg(time_unit)
  duration_unit <- match.arg(duration_unit)

  if (!is.data.frame(fixations)) {
    stop("`fixations` must be a data frame.", call. = FALSE)
  }
  if (nrow(fixations) == 0L) {
    stop("`fixations` must contain at least one row.", call. = FALSE)
  }
  if (!is.logical(include_unassigned) || length(include_unassigned) != 1L ||
      is.na(include_unassigned)) {
    stop("`include_unassigned` must be TRUE or FALSE.", call. = FALSE)
  }
  unassigned_label <- .gp_gap_nonempty_string(
    unassigned_label,
    "unassigned_label"
  )

  aoi_col <- .gp_gap_resolve_col(
    fixations,
    aoi_col,
    c("aoi", "AOI", "aoi_label", "roi", "region", "area_of_interest"),
    "AOI",
    TRUE
  )
  participant_col <- .gp_gap_resolve_col(
    fixations,
    participant_col,
    c("participant", "participant_id", "subject", "subject_id", "ParticipantName"),
    "participant",
    FALSE
  )
  trial_col <- .gp_gap_resolve_col(
    fixations,
    trial_col,
    c("trial", "trial_id", "stimulus", "stimulus_id", "Trial"),
    "trial",
    FALSE
  )
  start_col <- .gp_gap_resolve_col(
    fixations,
    start_col,
    c(
      "fixation_start_ms", "fixation_start_s", "start_time_ms",
      "start_time_s", "start_time", "start", "FPOGS", "onset"
    ),
    "fixation start",
    TRUE
  )
  end_col <- .gp_gap_resolve_col(
    fixations,
    end_col,
    c(
      "fixation_end_ms", "fixation_end_s", "end_time_ms",
      "end_time_s", "end_time", "end", "offset"
    ),
    "fixation end",
    FALSE
  )
  duration_col <- .gp_gap_resolve_col(
    fixations,
    duration_col,
    c(
      "fixation_duration_ms", "fixation_duration_s", "duration_ms",
      "duration_s", "duration", "FPOGD"
    ),
    "fixation duration",
    FALSE
  )
  event_onset_col <- .gp_gap_resolve_col(
    fixations,
    event_onset_col,
    c(
      "event_onset_ms", "event_onset_s", "event_time_ms",
      "event_time_s", "stimulus_onset", "trial_onset"
    ),
    "event onset",
    FALSE
  )

  if (is.null(end_col) && is.null(duration_col)) {
    stop(
      "Supply or provide an inferable `end_col` or `duration_col`.",
      call. = FALSE
    )
  }

  group_cols <- unique(c(
    participant_col,
    trial_col,
    .gp_gap_existing_cols(fixations, group_cols, "group_cols")
  ))
  group_cols <- group_cols[!is.na(group_cols) & nzchar(group_cols)]

  start_raw <- suppressWarnings(as.numeric(fixations[[start_col]]))
  resolved_time_unit <- .gp_gap_resolve_time_unit(
    start_raw,
    start_col,
    time_unit
  )
  if (identical(resolved_time_unit, "samples")) {
    .gp_gap_positive_scalar(sampling_rate_hz, "sampling_rate_hz")
  }
  start_ms <- 1000 * .gp_gap_to_seconds(
    start_raw,
    resolved_time_unit,
    sampling_rate_hz
  )

  end_ms <- rep(NA_real_, nrow(fixations))
  if (!is.null(end_col)) {
    end_raw <- suppressWarnings(as.numeric(fixations[[end_col]]))
    end_unit <- .gp_gap_resolve_time_unit(end_raw, end_col, time_unit)
    if (identical(end_unit, "samples")) {
      .gp_gap_positive_scalar(sampling_rate_hz, "sampling_rate_hz")
    }
    end_ms <- 1000 * .gp_gap_to_seconds(end_raw, end_unit, sampling_rate_hz)
  }

  duration_ms <- rep(NA_real_, nrow(fixations))
  resolved_duration_unit <- NULL
  if (!is.null(duration_col)) {
    duration_raw <- suppressWarnings(as.numeric(fixations[[duration_col]]))
    resolved_duration_unit <- .gp_gap_resolve_duration_unit(
      duration_raw,
      duration_col,
      duration_unit
    )
    if (identical(resolved_duration_unit, "samples")) {
      .gp_gap_positive_scalar(sampling_rate_hz, "sampling_rate_hz")
    }
    duration_ms <- 1000 * .gp_gap_to_seconds(
      duration_raw,
      resolved_duration_unit,
      sampling_rate_hz
    )
  } else {
    duration_ms <- end_ms - start_ms
    resolved_duration_unit <- "derived"
  }

  if (all(!is.finite(end_ms))) {
    end_ms <- start_ms + duration_ms
  } else {
    missing_end <- !is.finite(end_ms) & is.finite(start_ms) &
      is.finite(duration_ms)
    end_ms[missing_end] <- start_ms[missing_end] + duration_ms[missing_end]
  }

  event_onset_ms <- rep(NA_real_, nrow(fixations))
  if (!is.null(event_onset_col)) {
    onset_raw <- suppressWarnings(as.numeric(fixations[[event_onset_col]]))
    onset_unit <- .gp_gap_resolve_time_unit(
      onset_raw,
      event_onset_col,
      time_unit
    )
    if (identical(onset_unit, "samples")) {
      .gp_gap_positive_scalar(sampling_rate_hz, "sampling_rate_hz")
    }
    event_onset_ms <- 1000 * .gp_gap_to_seconds(
      onset_raw,
      onset_unit,
      sampling_rate_hz
    )
  }

  aoi <- trimws(as.character(fixations[[aoi_col]]))
  unassigned <- is.na(aoi) | !nzchar(aoi)
  if (isTRUE(include_unassigned)) {
    aoi[unassigned] <- unassigned_label
  }

  valid <- is.finite(start_ms) &
    is.finite(end_ms) &
    is.finite(duration_ms) &
    duration_ms > 0 &
    end_ms >= start_ms

  if (!isTRUE(include_unassigned)) {
    valid <- valid & !unassigned
  }

  if (!any(valid)) {
    stop("No valid assigned fixation rows remain.", call. = FALSE)
  }

  work <- fixations[valid, group_cols, drop = FALSE]
  work$.aoi <- aoi[valid]
  work$.start_ms <- start_ms[valid]
  work$.end_ms <- end_ms[valid]
  work$.duration_ms <- duration_ms[valid]
  work$.event_onset_ms <- event_onset_ms[valid]

  split_cols <- c(group_cols, ".aoi")
  split_index <- .gp_gap_split_indices(work, split_cols)

  rows <- lapply(split_index, function(idx) {
    grouping <- work[idx[1L], split_cols, drop = FALSE]
    durations <- work$.duration_ms[idx]
    starts <- work$.start_ms[idx]
    ends <- work$.end_ms[idx]
    onset <- work$.event_onset_ms[idx]
    finite_onset <- onset[is.finite(onset)]

    latency <- if (length(finite_onset) > 0L) {
      min(starts - onset, na.rm = TRUE)
    } else {
      NA_real_
    }

    cbind(
      grouping,
      data.frame(
        fixation_count = length(idx),
        total_fixation_duration_ms = sum(durations),
        mean_fixation_duration_ms = mean(durations),
        median_fixation_duration_ms = stats::median(durations),
        sd_fixation_duration_ms = if (length(durations) > 1L) {
          stats::sd(durations)
        } else {
          NA_real_
        },
        minimum_fixation_duration_ms = min(durations),
        maximum_fixation_duration_ms = max(durations),
        first_fixation_start_ms = min(starts),
        last_fixation_end_ms = max(ends),
        first_fixation_latency_ms = latency,
        stringsAsFactors = FALSE
      )
    )
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  names(out)[names(out) == ".aoi"] <- aoi_col

  denominator_cols <- group_cols
  if (length(denominator_cols) == 0L) {
    denominator_key <- rep("all", nrow(out))
  } else {
    denominator_key <- .gp_gap_group_key(out, denominator_cols)
  }

  denominator <- stats::ave(
    out$total_fixation_duration_ms,
    denominator_key,
    FUN = sum
  )
  out$dwell_proportion <- out$total_fixation_duration_ms / denominator

  ordering <- do.call(
    order,
    c(out[c(group_cols, aoi_col)], list(na.last = TRUE))
  )
  out <- out[ordering, , drop = FALSE]
  rownames(out) <- NULL

  structure(
    out,
    class = c("gazepoint_fixation_aoi_summary", "data.frame"),
    audit = list(
      source_rows = nrow(fixations),
      retained_rows = sum(valid),
      excluded_rows = sum(!valid),
      include_unassigned = include_unassigned,
      time_unit = resolved_time_unit,
      duration_unit = resolved_duration_unit,
      columns = list(
        aoi = aoi_col,
        participant = participant_col,
        trial = trial_col,
        groups = group_cols,
        start = start_col,
        end = end_col,
        duration = duration_col,
        event_onset = event_onset_col
      )
    )
  )
}

#' American-spelling alias for fixation summaries by AOI
#'
#' @return A data frame of class `"gazepoint_fixation_aoi_summary"`.
#' @param ... Arguments passed to [summarise_gazepoint_fixations_by_aoi()].
#' @export
summarize_gazepoint_fixations_by_aoi <- function(...) {
  summarise_gazepoint_fixations_by_aoi(...)
}

#' @export
print.gazepoint_fixation_aoi_summary <- function(x, ...) {
  audit <- attr(x, "audit")
  cat("Gazepoint fixation summary by AOI\n")
  cat("  Summary rows: ", nrow(x), "\n", sep = "")
  if (!is.null(audit)) {
    cat("  Retained fixations: ", audit$retained_rows, "\n", sep = "")
  }
  print.data.frame(x, ...)
  invisible(x)
}

#' Prepare an eye-tracking-only BIDS export
#'
#' A modality-specific convenience wrapper around
#' [export_gazepoint_to_bids()]. Arguments are forwarded without changing the
#' unified export contract. When the unified exporter exposes modality switches,
#' they are set to eye-tracking mode automatically.
#'
#' @param data Gazepoint eye-tracking data accepted by
#'   [export_gazepoint_to_bids()].
#' @param ... Additional arguments forwarded to [export_gazepoint_to_bids()].
#' @param execute If `FALSE`, return the resolved call specification without
#'   writing files.
#'
#' @return The result of [export_gazepoint_to_bids()] or a dry-run specification.
#' @export
prepare_gazepoint_bids_eye <- function(data, ..., execute = TRUE) {
  .gp_gap_bids_wrapper(
    modality = "eye",
    data = data,
    dots = list(...),
    execute = execute
  )
}

#' Prepare a physiology-only BIDS export
#'
#' A modality-specific convenience wrapper around
#' [export_gazepoint_to_bids()]. Arguments are forwarded without changing the
#' unified export contract. When the unified exporter exposes modality switches,
#' they are set to physiology mode automatically.
#'
#' @param data Gazepoint physiological data accepted by
#'   [export_gazepoint_to_bids()].
#' @param ... Additional arguments forwarded to [export_gazepoint_to_bids()].
#' @param execute If `FALSE`, return the resolved call specification without
#'   writing files.
#'
#' @return The result of [export_gazepoint_to_bids()] or a dry-run specification.
#' @export
prepare_gazepoint_bids_physio <- function(data, ..., execute = TRUE) {
  .gp_gap_bids_wrapper(
    modality = "physio",
    data = data,
    dots = list(...),
    execute = execute
  )
}

#' Write prepared Gazepoint data to an MNE FIF file
#'
#' Uses an external Python installation containing `numpy` and `mne`. Python is
#' invoked only when `execute = TRUE`; no Python package is an R dependency.
#'
#' @param x A `"gazepoint_mne_input"` object or a data frame accepted by
#'   [prepare_gazepoint_mne_input()].
#' @param fname Output filename. Use an MNE-compatible suffix such as
#'   `"_raw.fif"` or `"_raw.fif.gz"`.
#' @param events Optional `"gazepoint_mne_events"` object or three-column event
#'   matrix. Prepared event objects are also attached as MNE annotations.
#' @param overwrite Overwrite an existing file.
#' @param fmt FIF numeric format: `"single"` or `"double"`.
#' @param python Optional Python executable or Windows `py` launcher.
#' @param execute If `FALSE`, return a dry-run specification.
#' @param keep_intermediate Retain temporary CSV, TSV, and Python files.
#' @param verbose Show Python/MNE output.
#' @param ... Arguments passed to [prepare_gazepoint_mne_input()] when `x` is a
#'   data frame.
#'
#' @return A `"gazepoint_mne_fif_export"` object.
#' @export
write_gazepoint_mne_fif <- function(
    x,
    fname,
    events = NULL,
    overwrite = FALSE,
    fmt = c("single", "double"),
    python = NULL,
    execute = TRUE,
    keep_intermediate = FALSE,
    verbose = FALSE,
    ...) {
  fmt <- match.arg(fmt)
  .gp_gap_logical_scalar(overwrite, "overwrite")
  .gp_gap_logical_scalar(execute, "execute")
  .gp_gap_logical_scalar(keep_intermediate, "keep_intermediate")
  .gp_gap_logical_scalar(verbose, "verbose")

  fname <- .gp_gap_nonempty_string(fname, "fname")
  if (!grepl("(_raw|_eeg|_ieeg|_meg)\\.fif(\\.gz)?$", basename(fname))) {
    stop(
      "`fname` must use an MNE-compatible suffix such as `_raw.fif`.",
      call. = FALSE
    )
  }

  prepared <- if (inherits(x, "gazepoint_mne_input")) {
    x
  } else if (is.data.frame(x)) {
    prepare_gazepoint_mne_input(x, ...)
  } else {
    stop(
      "`x` must be a `gazepoint_mne_input` object or data frame.",
      call. = FALSE
    )
  }

  if (!is.matrix(prepared$data) || length(prepared$data) == 0L) {
    stop("The prepared MNE data matrix is empty.", call. = FALSE)
  }
  if (any(!is.finite(prepared$data))) {
    stop(
      "FIF writing requires finite channel values. Clean or interpolate ",
      "non-finite values explicitly before export.",
      call. = FALSE
    )
  }

  output_dir <- dirname(fname)
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }
  fname <- normalizePath(fname, winslash = "/", mustWork = FALSE)

  event_matrix <- NULL
  event_dictionary <- NULL
  if (!is.null(events)) {
    if (inherits(events, "gazepoint_mne_events")) {
      event_matrix <- events$events
      event_dictionary <- events$event_dictionary
    } else if (is.matrix(events) || is.data.frame(events)) {
      event_matrix <- as.matrix(events)
    } else {
      stop(
        "`events` must be a `gazepoint_mne_events` object or matrix.",
        call. = FALSE
      )
    }
    if (ncol(event_matrix) != 3L) {
      stop("MNE events must contain exactly three columns.", call. = FALSE)
    }
    storage.mode(event_matrix) <- "integer"
  }

  script_text <- .gp_gap_mne_python_script()

  dry_run <- structure(
    list(
      output = fname,
      n_channels = nrow(prepared$data),
      n_samples = ncol(prepared$data),
      sampling_rate_hz = prepared$info_spec$sfreq,
      first_samp = prepared$rawarray_spec$first_samp,
      channel_info = prepared$channel_info,
      event_count = if (is.null(event_matrix)) 0L else nrow(event_matrix),
      fmt = fmt,
      overwrite = overwrite,
      python = python,
      python_script = script_text,
      executed = FALSE
    ),
    class = c("gazepoint_mne_fif_export", "list")
  )

  if (!isTRUE(execute)) {
    return(dry_run)
  }

  python_spec <- .gp_gap_python_command(python)

  work_dir <- tempfile("gpbiometrics-mne-")
  dir.create(work_dir, recursive = TRUE)

  if (!isTRUE(keep_intermediate)) {
    on.exit(unlink(work_dir, recursive = TRUE, force = TRUE), add = TRUE)
  }

  data_path <- file.path(work_dir, "data.csv")
  channel_path <- file.path(work_dir, "channels.tsv")
  event_path <- file.path(work_dir, "events.csv")
  event_map_path <- file.path(work_dir, "event_map.tsv")
  script_path <- file.path(work_dir, "write_mne_fif.py")

  utils::write.table(
    prepared$data,
    data_path,
    sep = ",",
    row.names = FALSE,
    col.names = FALSE,
    quote = FALSE,
    na = "nan"
  )

  channel_table <- data.frame(
    channel_name = prepared$channel_info$channel_name,
    channel_type = prepared$channel_info$channel_type,
    stringsAsFactors = FALSE
  )
  utils::write.table(
    channel_table,
    channel_path,
    sep = "\t",
    row.names = FALSE,
    col.names = TRUE,
    quote = FALSE
  )

  if (!is.null(event_matrix)) {
    utils::write.table(
      event_matrix,
      event_path,
      sep = ",",
      row.names = FALSE,
      col.names = FALSE,
      quote = FALSE
    )

    if (!is.null(event_dictionary)) {
      utils::write.table(
        event_dictionary[, c("event_code", "event_label"), drop = FALSE],
        event_map_path,
        sep = "\t",
        row.names = FALSE,
        col.names = TRUE,
        quote = FALSE
      )
    } else {
      codes <- sort(unique(event_matrix[, 3L]))
      utils::write.table(
        data.frame(
          event_code = codes,
          event_label = paste0("event_", codes),
          stringsAsFactors = FALSE
        ),
        event_map_path,
        sep = "\t",
        row.names = FALSE,
        col.names = TRUE,
        quote = FALSE
      )
    }
  }

  writeLines(script_text, script_path, useBytes = TRUE)

  args <- c(
    python_spec$prefix,
    shQuote(script_path),
    "--data", shQuote(data_path),
    "--channels", shQuote(channel_path),
    "--output", shQuote(fname),
    "--sfreq", format(prepared$info_spec$sfreq, digits = 17),
    "--first-samp", as.character(prepared$rawarray_spec$first_samp),
    "--fmt", fmt,
    "--overwrite", if (overwrite) "1" else "0",
    "--quiet", if (verbose) "0" else "1"
  )

  if (!is.null(event_matrix)) {
    args <- c(
      args,
      "--events", shQuote(event_path),
      "--event-map", shQuote(event_map_path)
    )
  }

  output <- system2(
    python_spec$command,
    args = args,
    stdout = TRUE,
    stderr = TRUE
  )
  status <- attr(output, "status")
  if (is.null(status)) {
    status <- 0L
  }

  if (status != 0L || !file.exists(fname)) {
    stop(
      "MNE FIF creation failed.\n",
      paste(output, collapse = "\n"),
      call. = FALSE
    )
  }

  version_line <- grep("^MNE_VERSION\\t", output, value = TRUE)
  mne_version <- if (length(version_line) > 0L) {
    sub("^MNE_VERSION\\t", "", version_line[1L])
  } else {
    NA_character_
  }

  result <- dry_run
  result$executed <- TRUE
  result$mne_version <- mne_version
  result$python_output <- output
  result$intermediate_directory <- if (keep_intermediate) {
    normalizePath(work_dir, winslash = "/", mustWork = TRUE)
  } else {
    NA_character_
  }
  result
}

#' @export
print.gazepoint_mne_fif_export <- function(x, ...) {
  cat("Gazepoint MNE FIF export\n")
  cat("  Output: ", x$output, "\n", sep = "")
  cat("  Channels: ", x$n_channels, "\n", sep = "")
  cat("  Samples: ", x$n_samples, "\n", sep = "")
  cat("  Executed: ", if (isTRUE(x$executed)) "yes" else "no", "\n", sep = "")
  invisible(x)
}

#' Estimate live LSL clock offsets through pylsl
#'
#' Resolves active LSL streams and repeatedly calls each inlet's
#' `time_correction()` method. The returned correction is ready to pass to
#' [sync_gazepoint_signals_via_lsl()] as a value added to remote timestamps.
#'
#' @param stream_name Optional exact LSL stream name.
#' @param stream_type Optional exact LSL stream type.
#' @param source_id Optional exact LSL source ID.
#' @param timeout_s Resolution and first-correction timeout.
#' @param n_estimates Number of offset estimates per stream.
#' @param pause_s Pause between estimates.
#' @param python Optional Python executable or Windows `py` launcher.
#' @param execute If `FALSE`, return a dry-run specification.
#'
#' @return A `"gazepoint_lsl_clock_offsets"` object with raw estimates,
#'   stream-level summaries, and named median offsets.
#' @export
estimate_gazepoint_lsl_clock_offsets <- function(
    stream_name = NULL,
    stream_type = NULL,
    source_id = NULL,
    timeout_s = 5,
    n_estimates = 5L,
    pause_s = 0.05,
    python = NULL,
    execute = TRUE) {
  if (!is.null(stream_name)) {
    stream_name <- .gp_gap_nonempty_string(stream_name, "stream_name")
  }
  if (!is.null(stream_type)) {
    stream_type <- .gp_gap_nonempty_string(stream_type, "stream_type")
  }
  if (!is.null(source_id)) {
    source_id <- .gp_gap_nonempty_string(source_id, "source_id")
  }

  .gp_gap_positive_scalar(timeout_s, "timeout_s")
  n_estimates <- .gp_gap_positive_integer(n_estimates, "n_estimates")
  .gp_gap_nonnegative_scalar(pause_s, "pause_s")
  .gp_gap_logical_scalar(execute, "execute")

  script_text <- .gp_gap_lsl_python_script()

  dry_run <- structure(
    list(
      filters = list(
        stream_name = stream_name,
        stream_type = stream_type,
        source_id = source_id
      ),
      timeout_s = timeout_s,
      n_estimates = n_estimates,
      pause_s = pause_s,
      python = python,
      python_script = script_text,
      executed = FALSE
    ),
    class = c("gazepoint_lsl_clock_offsets", "list")
  )

  if (!isTRUE(execute)) {
    return(dry_run)
  }

  python_spec <- .gp_gap_python_command(python)
  script_path <- tempfile(fileext = ".py")
  on.exit(unlink(script_path, force = TRUE), add = TRUE)
  writeLines(script_text, script_path, useBytes = TRUE)

  args <- c(
    python_spec$prefix,
    shQuote(script_path),
    "--timeout", format(timeout_s, digits = 17),
    "--n-estimates", as.character(n_estimates),
    "--pause", format(pause_s, digits = 17)
  )

  if (!is.null(stream_name)) {
    args <- c(args, "--name", shQuote(stream_name))
  }
  if (!is.null(stream_type)) {
    args <- c(args, "--type", shQuote(stream_type))
  }
  if (!is.null(source_id)) {
    args <- c(args, "--source-id", shQuote(source_id))
  }

  output <- system2(
    python_spec$command,
    args = args,
    stdout = TRUE,
    stderr = TRUE
  )
  status <- attr(output, "status")
  if (is.null(status)) {
    status <- 0L
  }

  if (status != 0L) {
    stop(
      "LSL clock-offset estimation failed.\n",
      paste(output, collapse = "\n"),
      call. = FALSE
    )
  }

  estimates <- .gp_gap_parse_lsl_output(output)
  if (nrow(estimates) == 0L) {
    stop("No LSL clock-offset estimates were returned.", call. = FALSE)
  }

  stream_key <- paste(
    estimates$stream_name,
    estimates$stream_type,
    estimates$source_id,
    sep = "|"
  )
  estimates$stream_key <- stream_key

  summary_rows <- lapply(
    split(seq_len(nrow(estimates)), stream_key),
    function(idx) {
      values <- estimates$offset_s[idx]
      data.frame(
        stream_name = estimates$stream_name[idx[1L]],
        stream_type = estimates$stream_type[idx[1L]],
        source_id = estimates$source_id[idx[1L]],
        uid = estimates$uid[idx[1L]],
        hostname = estimates$hostname[idx[1L]],
        n_estimates = length(values),
        median_offset_s = stats::median(values),
        mean_offset_s = mean(values),
        sd_offset_s = if (length(values) > 1L) stats::sd(values) else NA_real_,
        mad_offset_s = stats::mad(values, constant = 1.4826),
        minimum_offset_s = min(values),
        maximum_offset_s = max(values),
        offset_range_s = diff(range(values)),
        stringsAsFactors = FALSE
      )
    }
  )

  summary <- do.call(rbind, summary_rows)
  rownames(summary) <- NULL

  offset_names <- make.unique(summary$stream_name)
  clock_offsets_s <- stats::setNames(
    summary$median_offset_s,
    offset_names
  )

  version_line <- grep("^PYLSL_VERSION\\t", output, value = TRUE)
  pylsl_version <- if (length(version_line) > 0L) {
    sub("^PYLSL_VERSION\\t", "", version_line[1L])
  } else {
    NA_character_
  }

  dry_run$executed <- TRUE
  dry_run$estimates <- estimates
  dry_run$summary <- summary
  dry_run$clock_offsets_s <- clock_offsets_s
  dry_run$pylsl_version <- pylsl_version
  dry_run$python_output <- output
  dry_run
}

#' @export
print.gazepoint_lsl_clock_offsets <- function(x, ...) {
  cat("Gazepoint LSL clock-offset estimates\n")
  cat("  Executed: ", if (isTRUE(x$executed)) "yes" else "no", "\n", sep = "")
  if (isTRUE(x$executed)) {
    cat("  Streams: ", nrow(x$summary), "\n", sep = "")
    cat(
      "  Median offsets (s): ",
      paste(
        paste0(names(x$clock_offsets_s), "=", signif(x$clock_offsets_s, 7)),
        collapse = ", "
      ),
      "\n",
      sep = ""
    )
  }
  invisible(x)
}

.gp_gap_bids_wrapper <- function(modality, data, dots, execute) {
  .gp_gap_logical_scalar(execute, "execute")
  if (!exists("export_gazepoint_to_bids", mode = "function")) {
    stop("`export_gazepoint_to_bids()` is not available.", call. = FALSE)
  }

  exporter <- get("export_gazepoint_to_bids", mode = "function")
  formal_names <- names(formals(exporter))
  args <- c(list(data), dots)

  if ("modality" %in% formal_names && is.null(args$modality)) {
    args$modality <- modality
  }
  if ("modalities" %in% formal_names && is.null(args$modalities)) {
    args$modalities <- modality
  }
  if ("include_eye" %in% formal_names && is.null(args$include_eye)) {
    args$include_eye <- identical(modality, "eye")
  }
  if ("include_physio" %in% formal_names && is.null(args$include_physio)) {
    args$include_physio <- identical(modality, "physio")
  }
  if ("include_biometrics" %in% formal_names &&
      is.null(args$include_biometrics)) {
    args$include_biometrics <- identical(modality, "physio")
  }

  specification <- structure(
    list(
      modality = modality,
      function_name = "export_gazepoint_to_bids",
      arguments = args,
      executed = FALSE
    ),
    class = c("gazepoint_bids_wrapper_spec", "list")
  )

  if (!isTRUE(execute)) {
    return(specification)
  }

  result <- do.call(exporter, args)
  attr(result, "gpbiometrics_bids_modality") <- modality
  result
}

.gp_gap_mne_python_script <- function() {
  paste(
    c(
      "import argparse",
      "import csv",
      "import numpy as np",
      "import mne",
      "",
      "parser = argparse.ArgumentParser()",
      "parser.add_argument('--data', required=True)",
      "parser.add_argument('--channels', required=True)",
      "parser.add_argument('--output', required=True)",
      "parser.add_argument('--sfreq', required=True, type=float)",
      "parser.add_argument('--first-samp', required=True, type=int)",
      "parser.add_argument('--fmt', required=True)",
      "parser.add_argument('--overwrite', required=True, type=int)",
      "parser.add_argument('--quiet', required=True, type=int)",
      "parser.add_argument('--events', default=None)",
      "parser.add_argument('--event-map', default=None)",
      "args = parser.parse_args()",
      "",
      "data = np.loadtxt(args.data, delimiter=',')",
      "if data.ndim == 1:",
      "    data = data.reshape((1, -1))",
      "",
      "with open(args.channels, newline='', encoding='utf-8') as handle:",
      "    rows = list(csv.DictReader(handle, delimiter='\\t'))",
      "channel_names = [row['channel_name'] for row in rows]",
      "channel_types = [row['channel_type'] for row in rows]",
      "",
      "if data.shape[0] != len(channel_names):",
      "    raise ValueError('Channel metadata and data rows do not match.')",
      "",
      "quiet = 'ERROR' if args.quiet else None",
      "info = mne.create_info(",
      "    ch_names=channel_names,",
      "    sfreq=args.sfreq,",
      "    ch_types=channel_types",
      ")",
      "raw = mne.io.RawArray(",
      "    data,",
      "    info,",
      "    first_samp=args.first_samp,",
      "    verbose=quiet",
      ")",
      "",
      "if args.events is not None:",
      "    events = np.loadtxt(args.events, delimiter=',', dtype=int)",
      "    events = np.atleast_2d(events)",
      "    event_desc = {}",
      "    with open(args.event_map, newline='', encoding='utf-8') as handle:",
      "        for row in csv.DictReader(handle, delimiter='\\t'):",
      "            event_desc[int(row['event_code'])] = row['event_label']",
      "    annotations = mne.annotations_from_events(",
      "        events=events,",
      "        sfreq=args.sfreq,",
      "        event_desc=event_desc,",
      "        first_samp=args.first_samp",
      "    )",
      "    raw.set_annotations(annotations)",
      "",
      "raw.save(",
      "    args.output,",
      "    overwrite=bool(args.overwrite),",
      "    fmt=args.fmt,",
      "    verbose=quiet",
      ")",
      "print('MNE_VERSION\\t' + str(mne.__version__))",
      "print('OUTPUT\\t' + args.output)"
    ),
    collapse = "\n"
  )
}

.gp_gap_lsl_python_script <- function() {
  paste(
    c(
      "import argparse",
      "import time",
      "import pylsl",
      "",
      "parser = argparse.ArgumentParser()",
      "parser.add_argument('--name', default=None)",
      "parser.add_argument('--type', default=None)",
      "parser.add_argument('--source-id', default=None)",
      "parser.add_argument('--timeout', required=True, type=float)",
      "parser.add_argument('--n-estimates', required=True, type=int)",
      "parser.add_argument('--pause', required=True, type=float)",
      "args = parser.parse_args()",
      "",
      "def clean(value):",
      "    return str(value).replace('\\t', ' ').replace('\\n', ' ')",
      "",
      "streams = pylsl.resolve_streams(wait_time=args.timeout)",
      "selected = []",
      "for info in streams:",
      "    if args.name is not None and info.name() != args.name:",
      "        continue",
      "    if args.type is not None and info.type() != args.type:",
      "        continue",
      "    if args.source_id is not None and info.source_id() != args.source_id:",
      "        continue",
      "    selected.append(info)",
      "",
      "if not selected:",
      "    raise RuntimeError('No active LSL streams matched the requested filters.')",
      "",
      "print('PYLSL_VERSION\\t' + str(getattr(pylsl, '__version__', 'unknown')))",
      "for info in selected:",
      "    inlet = pylsl.StreamInlet(info, max_buflen=1, recover=True)",
      "    try:",
      "        for index in range(args.n_estimates):",
      "            offset = inlet.time_correction(timeout=args.timeout)",
      "            local_time = pylsl.local_clock()",
      "            fields = [",
      "                'ESTIMATE',",
      "                clean(info.name()),",
      "                clean(info.type()),",
      "                clean(info.source_id()),",
      "                clean(info.uid()),",
      "                clean(info.hostname()),",
      "                str(index + 1),",
      "                format(offset, '.17g'),",
      "                format(local_time, '.17g')",
      "            ]",
      "            print('\\t'.join(fields), flush=True)",
      "            if args.pause > 0 and index + 1 < args.n_estimates:",
      "                time.sleep(args.pause)",
      "    finally:",
      "        inlet.close_stream()"
    ),
    collapse = "\n"
  )
}

.gp_gap_parse_lsl_output <- function(output) {
  lines <- grep("^ESTIMATE\\t", output, value = TRUE)
  if (length(lines) == 0L) {
    return(data.frame())
  }

  parts <- strsplit(lines, "\t", fixed = TRUE)
  widths <- lengths(parts)
  if (any(widths != 9L)) {
    stop("Unexpected pylsl output structure.", call. = FALSE)
  }

  matrix_values <- do.call(rbind, parts)
  data.frame(
    stream_name = matrix_values[, 2L],
    stream_type = matrix_values[, 3L],
    source_id = matrix_values[, 4L],
    uid = matrix_values[, 5L],
    hostname = matrix_values[, 6L],
    estimate_index = as.integer(matrix_values[, 7L]),
    offset_s = as.numeric(matrix_values[, 8L]),
    local_clock_s = as.numeric(matrix_values[, 9L]),
    stringsAsFactors = FALSE
  )
}

.gp_gap_python_command <- function(python = NULL) {
  if (!is.null(python)) {
    python <- .gp_gap_nonempty_string(python, "python")
    command <- python
  } else {
    candidates <- Sys.which(c("python", "python3", "py"))
    candidates <- candidates[nzchar(candidates)]
    if (length(candidates) == 0L) {
      stop(
        "No Python executable was found. Supply `python` explicitly.",
        call. = FALSE
      )
    }
    command <- unname(candidates[1L])
  }

  base <- tolower(basename(command))
  prefix <- if (base %in% c("py", "py.exe")) "-3" else character()

  list(command = command, prefix = prefix)
}

.gp_gap_check <- function(check, status, value, threshold, detail) {
  data.frame(
    check = check,
    status = status,
    value = as.numeric(value),
    threshold = as.numeric(threshold),
    detail = detail,
    stringsAsFactors = FALSE
  )
}

.gp_gap_coordinate_system <- function(
    x,
    y,
    requested,
    width,
    height) {
  if (!identical(requested, "auto")) {
    return(requested)
  }
  finite <- is.finite(x) & is.finite(y)
  if (!any(finite)) {
    return("normalized")
  }
  plausible_normalized <- all(
    x[finite] >= -0.5 & x[finite] <= 1.5 &
      y[finite] >= -0.5 & y[finite] <= 1.5
  )
  within_normalized <- mean(
    x[finite] >= 0 & x[finite] <= 1 &
      y[finite] >= 0 & y[finite] <= 1
  )
  if (plausible_normalized || within_normalized >= 0.90) {
    return("normalized")
  }
  if (!is.null(width) || !is.null(height) ||
      max(abs(c(x[finite], y[finite]))) > 2) {
    return("pixels")
  }
  "degrees"
}

.gp_gap_valid_values <- function(x) {
  if (is.logical(x)) {
    return(!is.na(x) & x)
  }
  if (is.numeric(x)) {
    return(is.finite(x) & x > 0)
  }
  text <- tolower(trimws(as.character(x)))
  !is.na(text) & text %in% c("1", "true", "valid", "yes", "y", "on")
}

.gp_gap_resolve_col <- function(
    data,
    supplied,
    candidates,
    description,
    required) {
  if (!is.null(supplied)) {
    supplied <- .gp_gap_nonempty_string(
      supplied,
      paste0(description, "_col")
    )
    if (!supplied %in% names(data)) {
      stop(
        "Selected ", description, " column was not found: ", supplied, ".",
        call. = FALSE
      )
    }
    return(supplied)
  }

  lower <- tolower(names(data))
  for (candidate in candidates) {
    hit <- which(lower == tolower(candidate))
    if (length(hit) > 0L) {
      return(names(data)[hit[1L]])
    }
  }

  if (isTRUE(required)) {
    stop(
      "Could not identify a ", description, " column. Supply it explicitly.",
      call. = FALSE
    )
  }
  NULL
}

.gp_gap_existing_cols <- function(data, columns, argument) {
  if (is.null(columns)) {
    return(character())
  }
  columns <- unique(as.character(columns))
  if (anyNA(columns) || any(!nzchar(trimws(columns)))) {
    stop("`", argument, "` must contain non-empty names.", call. = FALSE)
  }
  missing <- setdiff(columns, names(data))
  if (length(missing) > 0L) {
    stop(
      "Columns in `", argument, "` were not found: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }
  columns
}

.gp_gap_resolve_time_unit <- function(time, column, requested) {
  if (!identical(requested, "auto")) {
    return(requested)
  }
  lower <- tolower(column)
  if (grepl("cnt|sample|index", lower)) {
    return("samples")
  }
  if (grepl("mstimer|millisecond|msec|_ms$|^ms_", lower)) {
    return("milliseconds")
  }
  if (grepl("time_s|timestamp_s|onset_s|start_s|end_s|second", lower)) {
    return("seconds")
  }

  delta <- diff(sort(unique(time[is.finite(time)])))
  delta <- delta[is.finite(delta) & delta > 0]
  if (length(delta) == 0L) {
    stop("Could not infer the time unit; supply it explicitly.", call. = FALSE)
  }
  median_delta <- stats::median(delta)
  if (median_delta < 1) {
    return("seconds")
  }
  if (median_delta >= 5) {
    return("milliseconds")
  }
  stop("The time unit is ambiguous; supply it explicitly.", call. = FALSE)
}

.gp_gap_resolve_duration_unit <- function(duration, column, requested) {
  if (!identical(requested, "auto")) {
    return(requested)
  }
  lower <- tolower(column)
  if (grepl("sample|count", lower)) {
    return("samples")
  }
  if (grepl("millisecond|msec|_ms$|^ms_|fpogd", lower)) {
    return("milliseconds")
  }
  if (grepl("duration_s|second|_sec$|^sec_", lower)) {
    return("seconds")
  }

  finite <- duration[is.finite(duration) & duration >= 0]
  if (length(finite) == 0L) {
    stop("Could not infer the duration unit; supply it explicitly.", call. = FALSE)
  }
  if (stats::median(finite) > 10) {
    return("milliseconds")
  }
  "seconds"
}

.gp_gap_to_seconds <- function(x, unit, sampling_rate_hz) {
  switch(
    unit,
    seconds = as.numeric(x),
    milliseconds = as.numeric(x) / 1000,
    samples = as.numeric(x) / sampling_rate_hz
  )
}

.gp_gap_split_indices <- function(data, group_cols) {
  if (length(group_cols) == 0L) {
    return(list(all = seq_len(nrow(data))))
  }
  key <- .gp_gap_group_key(data, group_cols)
  split(seq_len(nrow(data)), key, drop = TRUE)
}

.gp_gap_group_key <- function(data, group_cols) {
  values <- lapply(data[group_cols], function(x) {
    text <- as.character(x)
    text[is.na(text)] <- "<NA>"
    text
  })
  do.call(paste, c(values, sep = "\r"))
}

.gp_gap_positive_scalar <- function(x, argument) {
  if (!is.numeric(x) || length(x) != 1L || !is.finite(x) || x <= 0) {
    stop(
      "`", argument, "` must be one positive finite number.",
      call. = FALSE
    )
  }
  invisible(x)
}

.gp_gap_nonnegative_scalar <- function(x, argument) {
  if (!is.numeric(x) || length(x) != 1L || !is.finite(x) || x < 0) {
    stop(
      "`", argument, "` must be one non-negative finite number.",
      call. = FALSE
    )
  }
  invisible(x)
}

.gp_gap_proportion <- function(x, argument) {
  if (!is.numeric(x) || length(x) != 1L || !is.finite(x) ||
      x < 0 || x > 1) {
    stop("`", argument, "` must be between 0 and 1.", call. = FALSE)
  }
  invisible(x)
}

.gp_gap_positive_integer <- function(x, argument) {
  if (!is.numeric(x) || length(x) != 1L || !is.finite(x) ||
      x < 1 || x != round(x)) {
    stop("`", argument, "` must be one positive integer.", call. = FALSE)
  }
  as.integer(x)
}

.gp_gap_logical_scalar <- function(x, argument) {
  if (!is.logical(x) || length(x) != 1L || is.na(x)) {
    stop("`", argument, "` must be TRUE or FALSE.", call. = FALSE)
  }
  invisible(x)
}

.gp_gap_nonempty_string <- function(x, argument) {
  x <- as.character(x)
  if (length(x) != 1L || is.na(x) || !nzchar(trimws(x))) {
    stop(
      "`", argument, "` must be one non-empty character value.",
      call. = FALSE
    )
  }
  x
}
