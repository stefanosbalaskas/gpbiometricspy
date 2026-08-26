
#' Detect fixations and saccades in Gazepoint gaze samples
#'
#' Applies a transparent velocity-threshold classification to raw Gazepoint
#' gaze coordinates. Samples are classified as fixation, saccade, unclassified,
#' or invalid, after which fixation- and saccade-level event tables are derived.
#'
#' This is an I-VT-style detector rather than an exact reproduction of a
#' specific vendor or external-toolbox implementation. The velocity threshold
#' must match the supplied coordinate unit and should be justified, reported,
#' and sensitivity-checked for the recording design.
#'
#' @param data A data frame containing sample-level gaze coordinates.
#' @param time_col Numeric time column. If `NULL`, common Gazepoint time-column
#'   names are searched.
#' @param x_col Numeric horizontal gaze-coordinate column. If `NULL`, common
#'   Gazepoint names such as `BPOGX`, `gaze_x`, and `FPOGX` are searched.
#' @param y_col Numeric vertical gaze-coordinate column. If `NULL`, common
#'   Gazepoint names such as `BPOGY`, `gaze_y`, and `FPOGY` are searched.
#' @param group_cols Optional participant, trial, session, or file columns.
#'   Detection is performed independently within each group.
#' @param valid_col Optional gaze-validity column.
#' @param valid_values Values in `valid_col` treated as valid.
#' @param time_unit Unit of `time_col`: `"seconds"`, `"milliseconds"`,
#'   `"microseconds"`, or `"samples"`.
#' @param sampling_rate_hz Sampling rate required when
#'   `time_unit = "samples"`.
#' @param coordinate_unit Descriptive unit of the gaze coordinates:
#'   `"native"`, `"normalized"`, `"pixels"`, or `"degrees"`. Coordinates are
#'   not transformed automatically.
#' @param velocity_threshold Positive velocity threshold expressed in coordinate
#'   units per second. Samples above this threshold are classified as saccadic.
#' @param min_fixation_duration_ms Minimum fixation duration in milliseconds.
#'   Shorter fixation runs are labelled `"unclassified"`.
#' @param min_saccade_duration_ms Minimum saccade duration in milliseconds.
#'   Shorter saccade runs are labelled `"unclassified"`.
#' @param max_gap_ms Maximum permitted time difference between adjacent samples.
#'   Larger gaps split events. Set to `NULL` to disable this check.
#' @param velocity_col Name of the generated sample-velocity column.
#' @param class_col Name of the generated sample-classification column.
#' @param event_id_col Name of the generated sample event-ID column.
#' @param overwrite Logical. If `FALSE`, existing generated columns are
#'   protected.
#'
#' @return An object of class `"gazepoint_gaze_events"` containing:
#'
#' - `samples`: original rows with velocity, class, and event ID;
#' - `fixations`: fixation-level timing, location, and dispersion summaries;
#' - `saccades`: saccade-level timing, amplitude, direction, and velocity;
#' - `summary`: group-level sample and event counts;
#' - `settings`: complete detector settings.
#'
#' @references
#' Salvucci, D. D., and Goldberg, J. H. (2000). Identifying fixations and
#' saccades in eye-tracking protocols. Proceedings of the Eye Tracking Research
#' and Applications Symposium.
#'
#' @seealso [detect_gazepoint_saccades()],
#'   [plot_gazepoint_saccade_main_sequence()],
#'   [summarize_gazepoint_fixations()]
#'
#' @examples
#' gaze <- data.frame(
#'   time_s = seq(0, 0.9, by = 0.1),
#'   gaze_x = c(0, 0.01, 0.02, 0.03, 1, 1.01, 1.02, 1.03, 1.04, 1.05),
#'   gaze_y = 0
#' )
#'
#' events <- detect_gazepoint_fixations(
#'   gaze,
#'   time_col = "time_s",
#'   x_col = "gaze_x",
#'   y_col = "gaze_y",
#'   velocity_threshold = 2,
#'   min_fixation_duration_ms = 100,
#'   min_saccade_duration_ms = 50
#' )
#'
#' events$fixations
#' events$saccades
#'
#' @export
detect_gazepoint_fixations <- function(
    data,
    time_col = NULL,
    x_col = NULL,
    y_col = NULL,
    group_cols = NULL,
    valid_col = NULL,
    valid_values = c(1, TRUE),
    time_unit = c(
      "seconds",
      "milliseconds",
      "microseconds",
      "samples"
    ),
    sampling_rate_hz = NULL,
    coordinate_unit = c(
      "native",
      "normalized",
      "pixels",
      "degrees"
    ),
    velocity_threshold,
    min_fixation_duration_ms = 100,
    min_saccade_duration_ms = 10,
    max_gap_ms = 100,
    velocity_col = "gaze_velocity",
    class_col = "gaze_class",
    event_id_col = "gaze_event_id",
    overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  time_col <- .gp_gaze_evt_resolve_numeric_col(
    data,
    supplied = time_col,
    candidates = c(
      "time_s",
      "time_ms",
      "TIME_MS",
      "TIME",
      "Time",
      "time",
      "timestamp",
      "TIMESTAMP",
      "CNT"
    ),
    argument = "time_col"
  )

  x_col <- .gp_gaze_evt_resolve_numeric_col(
    data,
    supplied = x_col,
    candidates = c(
      "BPOGX",
      "gaze_x",
      "GAZE_X",
      "FPOGX",
      "LPOGX",
      "RPOGX",
      "x",
      "X"
    ),
    argument = "x_col"
  )

  y_col <- .gp_gaze_evt_resolve_numeric_col(
    data,
    supplied = y_col,
    candidates = c(
      "BPOGY",
      "gaze_y",
      "GAZE_Y",
      "FPOGY",
      "LPOGY",
      "RPOGY",
      "y",
      "Y"
    ),
    argument = "y_col"
  )

  if (identical(x_col, y_col)) {
    stop(
      "`x_col` and `y_col` must identify different columns.",
      call. = FALSE
    )
  }

  time_unit <- match.arg(time_unit)
  coordinate_unit <- match.arg(coordinate_unit)

  .gp_gaze_evt_positive_scalar(
    velocity_threshold,
    "velocity_threshold"
  )

  .gp_gaze_evt_nonnegative_scalar(
    min_fixation_duration_ms,
    "min_fixation_duration_ms"
  )

  .gp_gaze_evt_nonnegative_scalar(
    min_saccade_duration_ms,
    "min_saccade_duration_ms"
  )

  if (!is.null(max_gap_ms)) {
    .gp_gaze_evt_positive_scalar(max_gap_ms, "max_gap_ms")
  }

  if (identical(time_unit, "samples")) {
    if (is.null(sampling_rate_hz)) {
      stop(
        "`sampling_rate_hz` is required when `time_unit = \"samples\"`.",
        call. = FALSE
      )
    }

    .gp_gaze_evt_positive_scalar(
      sampling_rate_hz,
      "sampling_rate_hz"
    )
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  } else {
    group_cols <- unique(as.character(group_cols))

    if (anyNA(group_cols) || any(!nzchar(group_cols))) {
      stop(
        "`group_cols` must contain non-empty column names.",
        call. = FALSE
      )
    }

    missing_groups <- setdiff(group_cols, names(data))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }
  }

  protected_cols <- c(time_col, x_col, y_col)

  if (length(intersect(group_cols, protected_cols)) > 0L) {
    stop(
      "`group_cols` must not include time or gaze-coordinate columns.",
      call. = FALSE
    )
  }

  if (!is.null(valid_col)) {
    valid_col <- as.character(valid_col)

    if (
      length(valid_col) != 1L ||
        is.na(valid_col) ||
        !nzchar(valid_col)
    ) {
      stop(
        "`valid_col` must be NULL or one non-empty column name.",
        call. = FALSE
      )
    }

    if (!valid_col %in% names(data)) {
      stop("`valid_col` was not found in `data`.", call. = FALSE)
    }

    if (length(valid_values) == 0L) {
      stop("`valid_values` must not be empty.", call. = FALSE)
    }
  }

  output_cols <- c(velocity_col, class_col, event_id_col)

  if (
    length(output_cols) != 3L ||
      anyNA(output_cols) ||
      any(!nzchar(output_cols)) ||
      anyDuplicated(output_cols)
  ) {
    stop(
      "Generated column names must be distinct non-empty strings.",
      call. = FALSE
    )
  }

  existing_outputs <- intersect(output_cols, names(data))

  if (!isTRUE(overwrite) && length(existing_outputs) > 0L) {
    stop(
      "Generated columns already exist: ",
      paste(existing_outputs, collapse = ", "),
      ". Use `overwrite = TRUE` to replace them.",
      call. = FALSE
    )
  }

  if (
    !is.logical(overwrite) ||
      length(overwrite) != 1L ||
      is.na(overwrite)
  ) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  groups <- .gp_gaze_evt_split_indices(data, group_cols)

  samples <- data
  samples[[velocity_col]] <- NA_real_
  samples[[class_col]] <- "invalid"
  samples[[event_id_col]] <- NA_integer_

  fixation_rows <- list()
  saccade_rows <- list()
  summary_rows <- list()

  for (group_i in seq_along(groups)) {
    source_idx <- groups[[group_i]]
    piece <- data[source_idx, , drop = FALSE]

    order_index <- order(
      piece[[time_col]],
      seq_len(nrow(piece)),
      na.last = TRUE
    )

    source_idx <- source_idx[order_index]
    piece <- piece[order_index, , drop = FALSE]

    time_seconds <- .gp_gaze_evt_time_seconds(
      piece[[time_col]],
      time_unit = time_unit,
      sampling_rate_hz = sampling_rate_hz
    )

    gaze_x <- piece[[x_col]]
    gaze_y <- piece[[y_col]]

    valid <- is.finite(time_seconds) &
      is.finite(gaze_x) &
      is.finite(gaze_y)

    if (!is.null(valid_col)) {
      valid <- valid &
        piece[[valid_col]] %in% valid_values
    }

    n_piece <- nrow(piece)
    delta_time <- c(NA_real_, diff(time_seconds))

    break_before <- rep(FALSE, n_piece)
    break_before[1L] <- TRUE

    if (n_piece > 1L) {
      break_before[2:n_piece] <-
        !is.finite(delta_time[2:n_piece]) |
        delta_time[2:n_piece] <= 0

      if (!is.null(max_gap_ms)) {
        gap_ms <- delta_time[2:n_piece] * 1000
        gap_tolerance <- sqrt(.Machine$double.eps) *
          pmax(1, abs(gap_ms), abs(max_gap_ms))

        break_before[2:n_piece] <-
          break_before[2:n_piece] |
          gap_ms > max_gap_ms + gap_tolerance
      }
    }

    velocity <- rep(NA_real_, n_piece)

    if (n_piece > 1L) {
      pair_valid <- valid[2:n_piece] &
        valid[1:(n_piece - 1L)] &
        !break_before[2:n_piece]

      destination <- which(pair_valid) + 1L

      if (length(destination) > 0L) {
        displacement <- sqrt(
          (gaze_x[destination] -
             gaze_x[destination - 1L])^2 +
            (gaze_y[destination] -
               gaze_y[destination - 1L])^2
        )

        velocity[destination] <-
          displacement / delta_time[destination]
      }
    }

    saccade_flag <- is.finite(velocity) &
      velocity > velocity_threshold

    saccade_destinations <- which(saccade_flag)

    if (length(saccade_destinations) > 0L) {
      possible_onsets <- saccade_destinations - 1L
      keep_onsets <- possible_onsets >= 1L &
        valid[possible_onsets] &
        !break_before[saccade_destinations]

      saccade_flag[
        possible_onsets[keep_onsets]
      ] <- TRUE
    }

    classification <- rep("invalid", n_piece)
    classification[valid] <- "fixation"
    classification[saccade_flag & valid] <- "saccade"

    initial_runs <- .gp_gaze_evt_runs(
      classification,
      break_before
    )

    for (run_rows in initial_runs) {
      run_class <- classification[run_rows[1L]]

      if (!run_class %in% c("fixation", "saccade")) {
        next
      }

      duration_ms <- .gp_gaze_evt_duration_ms(
        time_seconds[run_rows]
      )

      minimum_duration <- if (
        identical(run_class, "fixation")
      ) {
        min_fixation_duration_ms
      } else {
        min_saccade_duration_ms
      }

      if (
        !is.finite(duration_ms) ||
          duration_ms < minimum_duration
      ) {
        classification[run_rows] <- "unclassified"
      }
    }

    final_runs <- .gp_gaze_evt_runs(
      classification,
      break_before
    )

    sample_event_id <- rep(NA_integer_, n_piece)
    fixation_counter <- 0L
    saccade_counter <- 0L
    event_counter <- 0L

    group_values <- if (length(group_cols) == 0L) {
      data.frame(
        segment_id = names(groups)[group_i],
        stringsAsFactors = FALSE
      )
    } else {
      piece[1L, group_cols, drop = FALSE]
    }

    for (run_rows in final_runs) {
      run_class <- classification[run_rows[1L]]

      if (!run_class %in% c("fixation", "saccade")) {
        next
      }

      event_counter <- event_counter + 1L
      sample_event_id[run_rows] <- event_counter

      event_time <- piece[[time_col]][run_rows]
      event_time_seconds <- time_seconds[run_rows]
      event_x <- gaze_x[run_rows]
      event_y <- gaze_y[run_rows]
      event_velocity <- velocity[run_rows]

      duration_ms <- .gp_gaze_evt_duration_ms(
        event_time_seconds
      )

      if (identical(run_class, "fixation")) {
        fixation_counter <- fixation_counter + 1L

        range_x <- diff(range(event_x, na.rm = TRUE))
        range_y <- diff(range(event_y, na.rm = TRUE))

        fixation_rows[[length(fixation_rows) + 1L]] <-
          cbind(
            group_values,
            data.frame(
              fixation_id = fixation_counter,
              gaze_event_id = event_counter,
              start_row = source_idx[run_rows[1L]],
              end_row = source_idx[run_rows[length(run_rows)]],
              start_time = event_time[1L],
              end_time = event_time[length(event_time)],
              duration_ms = duration_ms,
              n_samples = length(run_rows),
              mean_x = mean(event_x),
              mean_y = mean(event_y),
              median_x = stats::median(event_x),
              median_y = stats::median(event_y),
              range_x = range_x,
              range_y = range_y,
              dispersion = range_x + range_y,
              stringsAsFactors = FALSE
            ),
            stringsAsFactors = FALSE
          )
      } else {
        saccade_counter <- saccade_counter + 1L

        delta_x <- event_x[length(event_x)] -
          event_x[1L]
        delta_y <- event_y[length(event_y)] -
          event_y[1L]

        amplitude <- sqrt(delta_x^2 + delta_y^2)

        direction_deg <- if (amplitude > 0) {
          (
            atan2(delta_y, delta_x) *
              180 / pi + 360
          ) %% 360
        } else {
          NA_real_
        }

        finite_velocity <- event_velocity[
          is.finite(event_velocity)
        ]

        saccade_rows[[length(saccade_rows) + 1L]] <-
          cbind(
            group_values,
            data.frame(
              saccade_id = saccade_counter,
              gaze_event_id = event_counter,
              start_row = source_idx[run_rows[1L]],
              end_row = source_idx[run_rows[length(run_rows)]],
              start_time = event_time[1L],
              end_time = event_time[length(event_time)],
              duration_ms = duration_ms,
              n_samples = length(run_rows),
              start_x = event_x[1L],
              start_y = event_y[1L],
              end_x = event_x[length(event_x)],
              end_y = event_y[length(event_y)],
              delta_x = delta_x,
              delta_y = delta_y,
              amplitude = amplitude,
              direction_deg = direction_deg,
              mean_velocity = if (
                length(finite_velocity) > 0L
              ) {
                mean(finite_velocity)
              } else {
                NA_real_
              },
              peak_velocity = if (
                length(finite_velocity) > 0L
              ) {
                max(finite_velocity)
              } else {
                NA_real_
              },
              stringsAsFactors = FALSE
            ),
            stringsAsFactors = FALSE
          )
      }
    }

    samples[[velocity_col]][source_idx] <- velocity
    samples[[class_col]][source_idx] <- classification
    samples[[event_id_col]][source_idx] <- sample_event_id

    summary_rows[[length(summary_rows) + 1L]] <-
      cbind(
        group_values,
        data.frame(
          n_samples = n_piece,
          n_valid_samples = sum(valid),
          n_invalid_samples = sum(classification == "invalid"),
          n_fixation_samples = sum(classification == "fixation"),
          n_saccade_samples = sum(classification == "saccade"),
          n_unclassified_samples = sum(
            classification == "unclassified"
          ),
          n_fixations = fixation_counter,
          n_saccades = saccade_counter,
          valid_sample_rate = mean(valid),
          fixation_sample_rate = mean(
            classification == "fixation"
          ),
          saccade_sample_rate = mean(
            classification == "saccade"
          ),
          unclassified_sample_rate = mean(
            classification == "unclassified"
          ),
          stringsAsFactors = FALSE
        ),
        stringsAsFactors = FALSE
      )
  }

  fixations <- .gp_gaze_evt_bind_fixations(
    fixation_rows,
    group_cols
  )

  saccades <- .gp_gaze_evt_bind_saccades(
    saccade_rows,
    group_cols
  )

  summary <- do.call(rbind, summary_rows)

  rownames(fixations) <- NULL
  rownames(saccades) <- NULL
  rownames(summary) <- NULL

  settings <- list(
    time_col = time_col,
    x_col = x_col,
    y_col = y_col,
    group_cols = group_cols,
    valid_col = valid_col,
    valid_values = valid_values,
    time_unit = time_unit,
    sampling_rate_hz = sampling_rate_hz,
    coordinate_unit = coordinate_unit,
    velocity_unit = paste0(coordinate_unit, "_per_second"),
    velocity_threshold = velocity_threshold,
    min_fixation_duration_ms = min_fixation_duration_ms,
    min_saccade_duration_ms = min_saccade_duration_ms,
    max_gap_ms = max_gap_ms,
    velocity_col = velocity_col,
    class_col = class_col,
    event_id_col = event_id_col
  )

  out <- list(
    samples = samples,
    fixations = fixations,
    saccades = saccades,
    summary = summary,
    settings = settings
  )

  class(out) <- c(
    "gazepoint_gaze_events",
    "list"
  )

  out
}

#' Detect saccades in Gazepoint gaze samples
#'
#' Convenience wrapper around [detect_gazepoint_fixations()] that returns only
#' the saccade-level event table. Detector settings and group summaries are
#' retained as attributes.
#'
#' @param ... Additional arguments passed to
#'   [detect_gazepoint_fixations()].
#'
#' @return A data frame with class `"gazepoint_detected_saccades"` containing
#'   saccade timing, amplitude, direction, and velocity measures.
#'
#' @examples
#' gaze <- data.frame(
#'   time_s = seq(0, 0.9, by = 0.1),
#'   gaze_x = c(0, 0.01, 0.02, 0.03, 1, 1.01, 1.02, 1.03, 1.04, 1.05),
#'   gaze_y = 0
#' )
#'
#' detect_gazepoint_saccades(
#'   gaze,
#'   time_col = "time_s",
#'   x_col = "gaze_x",
#'   y_col = "gaze_y",
#'   velocity_threshold = 2,
#'   min_saccade_duration_ms = 50
#' )
#'
#' @export
detect_gazepoint_saccades <- function(...) {
  detected <- detect_gazepoint_fixations(...)

  out <- detected$saccades

  attr(out, "gaze_event_summary") <- detected$summary
  attr(out, "gaze_event_settings") <- detected$settings

  class(out) <- unique(c(
    "gazepoint_detected_saccades",
    class(out)
  ))

  out
}

.gp_gaze_evt_resolve_numeric_col <- function(data,
                                        supplied,
                                        candidates,
                                        argument) {
  if (!is.null(supplied)) {
    supplied <- as.character(supplied)

    if (
      length(supplied) != 1L ||
        is.na(supplied) ||
        !nzchar(supplied)
    ) {
      stop(
        "`",
        argument,
        "` must be one non-empty column name.",
        call. = FALSE
      )
    }

    if (!supplied %in% names(data)) {
      stop(
        "Column `",
        supplied,
        "` supplied through `",
        argument,
        "` was not found.",
        call. = FALSE
      )
    }

    if (!is.numeric(data[[supplied]])) {
      stop(
        "`",
        argument,
        "` must identify a numeric column.",
        call. = FALSE
      )
    }

    return(supplied)
  }

  found <- intersect(candidates, names(data))
  found <- found[
    vapply(data[found], is.numeric, logical(1))
  ]

  if (length(found) == 0L) {
    stop(
      "Could not identify a numeric `",
      argument,
      "` column. Supply it explicitly.",
      call. = FALSE
    )
  }

  found[1L]
}

.gp_gaze_evt_positive_scalar <- function(x,
                                    argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x <= 0
  ) {
    stop(
      "`",
      argument,
      "` must be one positive finite number.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_gaze_evt_nonnegative_scalar <- function(x,
                                       argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x < 0
  ) {
    stop(
      "`",
      argument,
      "` must be one non-negative finite number.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_gaze_evt_time_seconds <- function(time,
                                 time_unit,
                                 sampling_rate_hz) {
  switch(
    time_unit,
    seconds = time,
    milliseconds = time / 1000,
    microseconds = time / 1000000,
    samples = time / sampling_rate_hz
  )
}

.gp_gaze_evt_split_indices <- function(data,
                                  group_cols) {
  if (length(group_cols) == 0L) {
    return(list(all_rows = seq_len(nrow(data))))
  }

  group_frame <- data[group_cols]

  group_frame[] <- lapply(
    group_frame,
    function(x) {
      x <- as.character(x)
      x[is.na(x)] <- "<NA>"
      x
    }
  )

  group_key <- do.call(
    paste,
    c(group_frame, sep = " | ")
  )

  split(
    seq_len(nrow(data)),
    group_key,
    drop = TRUE
  )
}

.gp_gaze_evt_runs <- function(classification,
                         break_before) {
  n <- length(classification)

  if (n == 0L) {
    return(list())
  }

  starts_new_run <- c(
    TRUE,
    classification[2:n] != classification[1:(n - 1L)] |
      break_before[2:n]
  )

  run_id <- cumsum(starts_new_run)

  split(
    seq_len(n),
    run_id,
    drop = TRUE
  )
}

.gp_gaze_evt_duration_ms <- function(time_seconds) {
  finite <- time_seconds[is.finite(time_seconds)]

  if (length(finite) == 0L) {
    return(NA_real_)
  }

  (
    max(finite) -
      min(finite)
  ) * 1000
}

.gp_gaze_evt_bind_fixations <- function(rows,
                                   group_cols) {
  if (length(rows) > 0L) {
    return(do.call(rbind, rows))
  }

  grouping_names <- if (length(group_cols) == 0L) {
    "segment_id"
  } else {
    group_cols
  }

  grouping <- as.data.frame(
    stats::setNames(
      replicate(
        length(grouping_names),
        character(),
        simplify = FALSE
      ),
      grouping_names
    ),
    stringsAsFactors = FALSE
  )

  cbind(
    grouping,
    data.frame(
      fixation_id = integer(),
      gaze_event_id = integer(),
      start_row = integer(),
      end_row = integer(),
      start_time = numeric(),
      end_time = numeric(),
      duration_ms = numeric(),
      n_samples = integer(),
      mean_x = numeric(),
      mean_y = numeric(),
      median_x = numeric(),
      median_y = numeric(),
      range_x = numeric(),
      range_y = numeric(),
      dispersion = numeric(),
      stringsAsFactors = FALSE
    )
  )
}

.gp_gaze_evt_bind_saccades <- function(rows,
                                  group_cols) {
  if (length(rows) > 0L) {
    return(do.call(rbind, rows))
  }

  grouping_names <- if (length(group_cols) == 0L) {
    "segment_id"
  } else {
    group_cols
  }

  grouping <- as.data.frame(
    stats::setNames(
      replicate(
        length(grouping_names),
        character(),
        simplify = FALSE
      ),
      grouping_names
    ),
    stringsAsFactors = FALSE
  )

  cbind(
    grouping,
    data.frame(
      saccade_id = integer(),
      gaze_event_id = integer(),
      start_row = integer(),
      end_row = integer(),
      start_time = numeric(),
      end_time = numeric(),
      duration_ms = numeric(),
      n_samples = integer(),
      start_x = numeric(),
      start_y = numeric(),
      end_x = numeric(),
      end_y = numeric(),
      delta_x = numeric(),
      delta_y = numeric(),
      amplitude = numeric(),
      direction_deg = numeric(),
      mean_velocity = numeric(),
      peak_velocity = numeric(),
      stringsAsFactors = FALSE
    )
  )
}
