#' Prepare Gazepoint events for MNE-Python
#'
#' Creates an integer MNE-style event matrix with columns representing sample
#' number, previous value, and event code. Input may be an event table, numeric
#' event-time vector, or continuous table containing marker columns.
#'
#' @param events Numeric event-time vector or data frame.
#' @param event_time_col Event-time column for event-table input.
#' @param event_label_col Optional event-label column.
#' @param event_code_col Optional positive integer event-code column.
#' @param marker_cols Optional marker or TTL columns in continuous input.
#' @param participant_col Optional participant column retained in the audit.
#' @param trial_col Optional trial column retained in the audit.
#' @param time_unit Time unit: `"auto"`, `"seconds"`, `"milliseconds"`, or
#'   `"samples"`.
#' @param sampling_rate_hz Positive sampling frequency used to convert event
#'   times to MNE sample numbers.
#' @param recording_start_s Recording start in seconds in the same clock domain
#'   as the converted event times.
#' @param first_samp Integer MNE first-sample offset.
#' @param event_id Optional named integer event dictionary or data frame with
#'   `event_label` and `event_code`.
#' @param previous_value Integer previous-event value placed in the second
#'   event-matrix column.
#' @param marker_onset Whether marker input creates events only on value
#'   changes or for every non-zero row.
#' @param duplicate Handling of repeated event sample numbers.
#' @param export_csv Optional path for a headerless three-column event file.
#'
#' @return A `"gazepoint_mne_events"` object containing the event matrix,
#'   event table, event dictionary, audit, and settings.
#'
#' @export
prepare_gazepoint_mne_events <- function(
    events,
    event_time_col = NULL,
    event_label_col = NULL,
    event_code_col = NULL,
    marker_cols = NULL,
    participant_col = NULL,
    trial_col = NULL,
    time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    sampling_rate_hz,
    recording_start_s = 0,
    first_samp = 0L,
    event_id = NULL,
    previous_value = 0L,
    marker_onset = c("change", "nonzero"),
    duplicate = c("error", "allow"),
    export_csv = NULL) {
  time_unit <- match.arg(time_unit)
  marker_onset <- match.arg(marker_onset)
  duplicate <- match.arg(duplicate)

  .gp_mm_positive_scalar(
    sampling_rate_hz,
    "sampling_rate_hz"
  )

  .gp_mm_finite_scalar(
    recording_start_s,
    "recording_start_s"
  )

  first_samp <- .gp_mm_integer_scalar(
    first_samp,
    "first_samp"
  )

  previous_value <- .gp_mm_integer_scalar(
    previous_value,
    "previous_value"
  )

  if (is.numeric(events) && !is.data.frame(events)) {
    source <- data.frame(
      source_row = seq_along(events),
      source_time = as.numeric(events),
      event_label = rep(
        "event",
        length(events)
      ),
      stringsAsFactors = FALSE
    )

    resolved_time_col <- "numeric_vector"
    resolved_label_col <- NULL
    resolved_code_col <- NULL
    resolved_participant_col <- NULL
    resolved_trial_col <- NULL
    source_mode <- "event_time_vector"
  } else {
    if (!is.data.frame(events)) {
      stop(
        "`events` must be a numeric vector or data frame.",
        call. = FALSE
      )
    }

    if (nrow(events) == 0L) {
      stop(
        "`events` must contain at least one row.",
        call. = FALSE
      )
    }

    resolved_participant_col <- .gp_mm_resolve_col(
      events,
      participant_col,
      c(
        "participant",
        "participant_id",
        "subject",
        "subject_id",
        "ParticipantName",
        "Subject"
      ),
      "participant",
      FALSE
    )

    resolved_trial_col <- .gp_mm_resolve_col(
      events,
      trial_col,
      c(
        "trial",
        "trial_id",
        "Trial",
        "stimulus",
        "stimulus_id"
      ),
      "trial",
      FALSE
    )

    if (!is.null(marker_cols)) {
      marker_cols <- .gp_mm_optional_cols(
        events,
        marker_cols,
        "marker_cols"
      )

      resolved_time_col <- .gp_mm_resolve_col(
        events,
        event_time_col,
        c(
          "event_time_s",
          "event_time",
          "time_s",
          "time_ms",
          "time",
          "timestamp",
          "MSTIMER",
          "CNT"
        ),
        "event time",
        TRUE
      )

      source_rows <- list()

      for (marker_col in marker_cols) {
        marker <- events[[marker_col]]
        marker_text <- trimws(
          as.character(marker)
        )

        inactive_text <- c(
          "",
          "0",
          "false",
          "off",
          "none",
          "na",
          "nan"
        )

        active <- !is.na(marker) &
          !tolower(marker_text) %in%
          inactive_text

        onset <- active

        if (identical(marker_onset, "change")) {
          previous_active <- c(
            FALSE,
            utils::head(active, -1L)
          )

          previous_text <- c(
            NA_character_,
            utils::head(marker_text, -1L)
          )

          onset <- active &
            (
              !previous_active |
                marker_text != previous_text
            )
        }

        idx <- which(onset)

        if (length(idx) == 0L) {
          next
        }

        simple_marker <- tolower(
          marker_text[idx]
        ) %in% c(
          "1",
          "true",
          "on"
        )

        labels <- ifelse(
          simple_marker,
          marker_col,
          paste0(
            marker_col,
            "/",
            marker_text[idx]
          )
        )

        one <- data.frame(
          source_row = idx,
          source_time =
            suppressWarnings(
              as.numeric(
                events[[resolved_time_col]][idx]
              )
            ),
          event_label = labels,
          marker_channel = marker_col,
          marker_value = marker_text[idx],
          stringsAsFactors = FALSE
        )

        if (!is.null(resolved_participant_col)) {
          one$participant <- as.character(
            events[[resolved_participant_col]][idx]
          )
        }

        if (!is.null(resolved_trial_col)) {
          one$trial <- as.character(
            events[[resolved_trial_col]][idx]
          )
        }

        source_rows[[length(source_rows) + 1L]] <-
          one
      }

      if (length(source_rows) == 0L) {
        stop(
          "No active marker events were found.",
          call. = FALSE
        )
      }

      source <- do.call(
        rbind,
        source_rows
      )

      rownames(source) <- NULL
      resolved_label_col <- NULL
      resolved_code_col <- NULL
      source_mode <- "continuous_marker_columns"
    } else {
      resolved_time_col <- .gp_mm_resolve_col(
        events,
        event_time_col,
        c(
          "event_time_s",
          "event_time",
          "onset_s",
          "onset",
          "time_s",
          "time_ms",
          "time",
          "timestamp",
          "MSTIMER",
          "CNT"
        ),
        "event time",
        TRUE
      )

      resolved_label_col <- .gp_mm_resolve_col(
        events,
        event_label_col,
        c(
          "event_label",
          "event",
          "marker_label",
          "condition",
          "stimulus",
          "trial_type"
        ),
        "event label",
        FALSE
      )

      resolved_code_col <- .gp_mm_resolve_col(
        events,
        event_code_col,
        c(
          "event_code",
          "marker_code",
          "trigger_code",
          "value"
        ),
        "event code",
        FALSE
      )

      source <- data.frame(
        source_row = seq_len(nrow(events)),
        source_time =
          suppressWarnings(
            as.numeric(
              events[[resolved_time_col]]
            )
          ),
        stringsAsFactors = FALSE
      )

      if (!is.null(resolved_label_col)) {
        source$event_label <- as.character(
          events[[resolved_label_col]]
        )
      } else if (!is.null(resolved_code_col)) {
        source$event_label <- paste0(
          "event_",
          events[[resolved_code_col]]
        )
      } else {
        source$event_label <- rep(
          "event",
          nrow(events)
        )
      }

      if (!is.null(resolved_code_col)) {
        source$source_event_code <-
          suppressWarnings(
            as.numeric(
              events[[resolved_code_col]]
            )
          )
      }

      if (!is.null(resolved_participant_col)) {
        source$participant <- as.character(
          events[[resolved_participant_col]]
        )
      }

      if (!is.null(resolved_trial_col)) {
        source$trial <- as.character(
          events[[resolved_trial_col]]
        )
      }

      source_mode <- "event_table"
    }
  }

  if (
    anyNA(source$source_time) ||
      any(!is.finite(source$source_time))
  ) {
    stop(
      "Event times must contain only finite numeric values.",
      call. = FALSE
    )
  }

  if (
    anyNA(source$event_label) ||
      any(!nzchar(trimws(source$event_label)))
  ) {
    stop(
      "Event labels must be non-missing and non-empty.",
      call. = FALSE
    )
  }

  resolved_time_unit <- .gp_mm_resolve_time_unit(
    source$source_time,
    resolved_time_col,
    time_unit
  )

  event_time_s <- .gp_mm_convert_time_seconds(
    source$source_time,
    resolved_time_unit,
    sampling_rate_hz
  )

  event_sample <- round(
    (
      event_time_s -
        recording_start_s
    ) *
      sampling_rate_hz
  ) +
    first_samp

  if (
    any(!is.finite(event_sample)) ||
      any(event_sample < 0)
  ) {
    stop(
      "Converted MNE event sample numbers must be finite and non-negative.",
      call. = FALSE
    )
  }

  event_sample <- as.integer(
    event_sample
  )

  dictionary <- NULL

  if ("source_event_code" %in% names(source)) {
    codes <- source$source_event_code

    if (
      anyNA(codes) ||
        any(!is.finite(codes)) ||
        any(codes <= 0) ||
        any(codes != round(codes))
    ) {
      stop(
        "`event_code_col` must contain positive integer values.",
        call. = FALSE
      )
    }

    codes <- as.integer(codes)

    dictionary <- unique(
      data.frame(
        event_label =
          source$event_label,
        event_code =
          codes,
        stringsAsFactors = FALSE
      )
    )

    label_code_count <- tapply(
      dictionary$event_code,
      dictionary$event_label,
      function(x) length(unique(x))
    )

    code_label_count <- tapply(
      dictionary$event_label,
      dictionary$event_code,
      function(x) length(unique(x))
    )

    if (
      any(label_code_count > 1L) ||
        any(code_label_count > 1L)
    ) {
      stop(
        "Event labels and codes must form a one-to-one mapping.",
        call. = FALSE
      )
    }
  } else {
    dictionary <- .gp_mne_event_dictionary(
      source$event_label,
      event_id
    )

    code_map <- stats::setNames(
      dictionary$event_code,
      dictionary$event_label
    )

    codes <- unname(
      code_map[source$event_label]
    )

    if (anyNA(codes)) {
      stop(
        "At least one event label was not mapped to an event code.",
        call. = FALSE
      )
    }

    codes <- as.integer(codes)
  }

  duplicate_sample <- duplicated(event_sample) |
    duplicated(
      event_sample,
      fromLast = TRUE
    )

  if (
    any(duplicate_sample) &&
      identical(duplicate, "error")
  ) {
    stop(
      "Repeated MNE event sample numbers were detected. ",
      "Use `duplicate = \"allow\"` only after reviewing the event table.",
      call. = FALSE
    )
  }

  previous <- rep(
    as.integer(previous_value),
    length(event_sample)
  )

  event_matrix <- cbind(
    sample = event_sample,
    previous = previous,
    event_id = codes
  )

  storage.mode(event_matrix) <- "integer"

  event_table <- source
  event_table$event_time_s <- event_time_s
  event_table$mne_sample <- event_sample
  event_table$previous_value <- previous
  event_table$event_code <- codes

  order_index <- order(
    event_table$mne_sample,
    event_table$source_row
  )

  event_table <- event_table[
    order_index,
    ,
    drop = FALSE
  ]

  event_matrix <- event_matrix[
    order_index,
    ,
    drop = FALSE
  ]

  rownames(event_table) <- NULL
  rownames(event_matrix) <- NULL

  event_id_vector <- stats::setNames(
    as.integer(dictionary$event_code),
    dictionary$event_label
  )

  if (!is.null(export_csv)) {
    export_csv <- .gp_mm_nonempty_string(
      export_csv,
      "export_csv"
    )

    parent <- dirname(export_csv)

    if (!dir.exists(parent)) {
      dir.create(
        parent,
        recursive = TRUE,
        showWarnings = FALSE
      )
    }

    utils::write.table(
      event_matrix,
      file = export_csv,
      sep = " ",
      row.names = FALSE,
      col.names = FALSE,
      quote = FALSE
    )
  }

  audit <- data.frame(
    n_events = nrow(event_table),
    n_event_types = nrow(dictionary),
    minimum_sample =
      min(event_table$mne_sample),
    maximum_sample =
      max(event_table$mne_sample),
    duplicate_sample_count =
      sum(duplicate_sample),
    sampling_rate_hz =
      sampling_rate_hz,
    recording_start_s =
      recording_start_s,
    first_samp =
      first_samp,
    source_mode =
      source_mode,
    source_time_unit =
      resolved_time_unit,
    exported =
      !is.null(export_csv),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      events = event_matrix,
      table = event_table,
      event_id = event_id_vector,
      event_dictionary = dictionary,
      audit = audit,
      settings = list(
        event_time_col =
          resolved_time_col,
        event_label_col =
          resolved_label_col,
        event_code_col =
          resolved_code_col,
        marker_cols =
          marker_cols,
        participant_col =
          resolved_participant_col,
        trial_col =
          resolved_trial_col,
        time_unit =
          resolved_time_unit,
        sampling_rate_hz =
          sampling_rate_hz,
        recording_start_s =
          recording_start_s,
        first_samp =
          first_samp,
        previous_value =
          previous_value,
        marker_onset =
          marker_onset,
        duplicate =
          duplicate,
        export_csv =
          export_csv
      )
    ),
    class = c(
      "gazepoint_mne_events",
      "list"
    )
  )
}

#' @export
print.gazepoint_mne_events <- function(
    x,
    ...) {
  cat("Gazepoint MNE events\n")
  cat(
    "  Events: ",
    nrow(x$events),
    "\n",
    sep = ""
  )
  cat(
    "  Event types: ",
    length(x$event_id),
    "\n",
    sep = ""
  )
  cat(
    "  Sample range: ",
    min(x$events[, 1L]),
    " to ",
    max(x$events[, 1L]),
    "\n",
    sep = ""
  )

  invisible(x)
}

#' Prepare Gazepoint channels for an MNE RawArray
#'
#' Produces a channel-by-sample matrix and metadata specifications suitable for
#' `mne.create_info()` and `mne.io.RawArray()`. No Python execution is required.
#'
#' @param data One continuous sample-level data frame.
#' @param channel_cols Numeric signal columns. If omitted, common Gazepoint
#'   gaze, pupil, physiology, marker, and temperature columns are detected.
#' @param channel_names Optional MNE channel names.
#' @param channel_types Optional MNE channel types, either parallel to
#'   `channel_cols` or named by source column.
#' @param time_col Numeric time column.
#' @param time_unit Time unit.
#' @param sampling_rate_hz Optional sampling frequency. If omitted it is
#'   inferred from the median interval.
#' @param first_samp Integer MNE first-sample offset.
#' @param scale_factors Optional explicit numeric factors applied to channels.
#' @param missing Handling of non-finite signal values.
#' @param irregular Handling of irregular sampling.
#' @param sampling_tolerance Maximum relative interval deviation.
#'
#' @return A `"gazepoint_mne_input"` object.
#'
#' @export
prepare_gazepoint_mne_input <- function(
    data,
    channel_cols = NULL,
    channel_names = NULL,
    channel_types = NULL,
    time_col = NULL,
    time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    sampling_rate_hz = NULL,
    first_samp = 0L,
    scale_factors = NULL,
    missing = c("error", "allow"),
    irregular = c("error", "allow"),
    sampling_tolerance = 0.05) {
  time_unit <- match.arg(time_unit)
  missing <- match.arg(missing)
  irregular <- match.arg(irregular)

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a data frame.",
      call. = FALSE
    )
  }

  if (nrow(data) < 2L) {
    stop(
      "`data` must contain at least two samples.",
      call. = FALSE
    )
  }

  .gp_mm_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  first_samp <- .gp_mm_integer_scalar(
    first_samp,
    "first_samp"
  )

  time_col <- .gp_mm_resolve_col(
    data,
    time_col,
    c(
      "time_s",
      "time_ms",
      "time",
      "timestamp",
      "MSTIMER",
      "TIME",
      "CNT"
    ),
    "time",
    TRUE
  )

  if (!is.numeric(data[[time_col]])) {
    stop(
      "`time_col` must identify a numeric column.",
      call. = FALSE
    )
  }

  source_time <- suppressWarnings(
    as.numeric(data[[time_col]])
  )

  if (
    anyNA(source_time) ||
      any(!is.finite(source_time))
  ) {
    stop(
      "`time_col` must contain only finite values.",
      call. = FALSE
    )
  }

  resolved_time_unit <- .gp_mm_resolve_time_unit(
    source_time,
    time_col,
    time_unit
  )

  if (
    identical(resolved_time_unit, "samples") &&
      is.null(sampling_rate_hz)
  ) {
    stop(
      "`sampling_rate_hz` is required for sample-index time.",
      call. = FALSE
    )
  }

  if (!is.null(sampling_rate_hz)) {
    .gp_mm_positive_scalar(
      sampling_rate_hz,
      "sampling_rate_hz"
    )
  }

  time_s <- .gp_mm_convert_time_seconds(
    source_time,
    resolved_time_unit,
    sampling_rate_hz
  )

  if (anyDuplicated(time_s)) {
    stop(
      "Time values must be unique within an MNE recording.",
      call. = FALSE
    )
  }

  order_index <- order(
    time_s,
    seq_along(time_s)
  )

  source_order_changed <- !identical(
    order_index,
    seq_len(nrow(data))
  )

  data <- data[
    order_index,
    ,
    drop = FALSE
  ]

  source_time <- source_time[order_index]
  time_s <- time_s[order_index]

  if (is.null(channel_cols)) {
    pattern <- paste(
      c(
        "gaze",
        "pog",
        "pupil",
        "gsr",
        "eda",
        "ppg",
        "bvp",
        "pulse",
        "heart",
        "(^|_)hr($|_)",
        "ibi",
        "(^|_)rr($|_)",
        "dial",
        "ttl",
        "marker",
        "trigger",
        "temperature",
        "(^|_)temp($|_)",
        "resp"
      ),
      collapse = "|"
    )

    candidates <- names(data)[
      grepl(
        pattern,
        names(data),
        ignore.case = TRUE
      )
    ]

    channel_cols <- candidates[
      vapply(
        data[candidates],
        is.numeric,
        logical(1)
      )
    ]

    channel_cols <- setdiff(
      channel_cols,
      time_col
    )
  } else {
    channel_cols <- .gp_mm_optional_cols(
      data,
      channel_cols,
      "channel_cols"
    )
  }

  if (length(channel_cols) == 0L) {
    stop(
      "No numeric signal channels were selected.",
      call. = FALSE
    )
  }

  nonnumeric <- channel_cols[
    !vapply(
      data[channel_cols],
      is.numeric,
      logical(1)
    )
  ]

  if (length(nonnumeric) > 0L) {
    stop(
      "MNE channel columns must be numeric: ",
      paste(
        nonnumeric,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  if (is.null(channel_names)) {
    channel_names <- channel_cols
  } else {
    channel_names <- as.character(
      channel_names
    )

    if (length(channel_names) != length(channel_cols)) {
      stop(
        "`channel_names` must have one value per channel.",
        call. = FALSE
      )
    }

    if (
      anyNA(channel_names) ||
        any(!nzchar(trimws(channel_names))) ||
        anyDuplicated(channel_names)
    ) {
      stop(
        "`channel_names` must be unique, non-empty values.",
        call. = FALSE
      )
    }
  }

  channel_types <- .gp_mne_channel_types(
    channel_cols,
    channel_types
  )

  scale_factors <- .gp_mm_parallel_numeric(
    scale_factors,
    channel_cols,
    default = 1,
    argument = "scale_factors"
  )

  signal_frame <- data[
    channel_cols
  ]

  for (i in seq_along(channel_cols)) {
    signal_frame[[i]] <-
      suppressWarnings(
        as.numeric(signal_frame[[i]])
      ) *
      scale_factors[i]
  }

  nonfinite_count <- vapply(
    signal_frame,
    function(x) sum(!is.finite(x)),
    integer(1)
  )

  if (
    any(nonfinite_count > 0L) &&
      identical(missing, "error")
  ) {
    stop(
      "Non-finite signal values were detected. ",
      "Use `missing = \"allow\"` only if NaN values are intentional.",
      call. = FALSE
    )
  }

  for (i in seq_along(signal_frame)) {
    signal_frame[[i]][
      !is.finite(signal_frame[[i]])
    ] <- NA_real_
  }

  intervals <- diff(time_s)
  median_interval_s <- stats::median(
    intervals
  )

  if (
    !is.finite(median_interval_s) ||
      median_interval_s <= 0
  ) {
    stop(
      "A positive sampling interval could not be determined.",
      call. = FALSE
    )
  }

  inferred_rate <- 1 / median_interval_s

  resolved_rate <- if (
    is.null(sampling_rate_hz)
  ) {
    inferred_rate
  } else {
    sampling_rate_hz
  }

  expected_interval <- 1 / resolved_rate

  relative_interval_error <- abs(
    intervals -
      expected_interval
  ) /
    expected_interval

  irregular_count <- sum(
    relative_interval_error >
      sampling_tolerance
  )

  if (
    irregular_count > 0L &&
      identical(irregular, "error")
  ) {
    stop(
      "Irregular sampling was detected. ",
      "Use `irregular = \"allow\"` only after reviewing the audit.",
      call. = FALSE
    )
  }

  recording_start_s <- min(time_s)
  relative_time_s <- time_s -
    recording_start_s

  data_matrix <- t(
    as.matrix(signal_frame)
  )

  rownames(data_matrix) <- channel_names
  colnames(data_matrix) <- NULL
  storage.mode(data_matrix) <- "double"

  channel_info <- data.frame(
    source_column =
      channel_cols,
    channel_name =
      channel_names,
    channel_type =
      channel_types,
    scale_factor =
      scale_factors,
    nonfinite_count =
      nonfinite_count,
    stringsAsFactors = FALSE
  )

  info_spec <- list(
    ch_names = channel_names,
    sfreq = resolved_rate,
    ch_types = channel_types
  )

  rawarray_spec <- list(
    data = data_matrix,
    info = info_spec,
    first_samp = first_samp
  )

  python_code <- paste0(
    "info = mne.create_info(ch_names=",
    .gp_mm_python_list(channel_names),
    ", sfreq=",
    format(
      resolved_rate,
      digits = 16,
      scientific = FALSE
    ),
    ", ch_types=",
    .gp_mm_python_list(channel_types),
    ")\nraw = mne.io.RawArray(data, info, first_samp=",
    first_samp,
    ")"
  )

  sampling <- data.frame(
    n_samples = nrow(data),
    n_channels = length(channel_cols),
    recording_start_s = recording_start_s,
    recording_end_s = max(time_s),
    duration_s =
      max(time_s) -
      recording_start_s,
    median_interval_s =
      median_interval_s,
    inferred_sampling_rate_hz =
      inferred_rate,
    resolved_sampling_rate_hz =
      resolved_rate,
    irregular_interval_count =
      irregular_count,
    maximum_relative_interval_error =
      max(relative_interval_error),
    source_order_changed =
      source_order_changed,
    stringsAsFactors = FALSE
  )

  structure(
    list(
      data = data_matrix,
      times = relative_time_s,
      source_times = time_s,
      channel_info = channel_info,
      info_spec = info_spec,
      rawarray_spec = rawarray_spec,
      python_code = python_code,
      sampling = sampling,
      settings = list(
        time_col = time_col,
        source_time_unit =
          resolved_time_unit,
        first_samp =
          first_samp,
        missing =
          missing,
        irregular =
          irregular,
        sampling_tolerance =
          sampling_tolerance,
        interpretation_notes = c(
          "The data matrix is arranged as channels by samples.",
          "Channel values are preserved unless explicit scale factors are supplied.",
          "MNE-Python expects SI base units for channel types that have physical units.",
          "No filtering, interpolation, resampling, or Python execution is performed."
        )
      )
    ),
    class = c(
      "gazepoint_mne_input",
      "list"
    )
  )
}

#' @export
print.gazepoint_mne_input <- function(
    x,
    ...) {
  cat("Gazepoint MNE input\n")
  cat(
    "  Channels: ",
    nrow(x$data),
    "\n",
    sep = ""
  )
  cat(
    "  Samples: ",
    ncol(x$data),
    "\n",
    sep = ""
  )
  cat(
    "  Sampling rate: ",
    format(
      x$info_spec$sfreq,
      digits = 8
    ),
    " Hz\n",
    sep = ""
  )

  invisible(x)
}

#' Align Gazepoint timestamps to an EEG clock
#'
#' Estimates a constant offset or linear offset-plus-drift mapping from matched
#' Gazepoint and EEG events, then applies that mapping to a Gazepoint stream.
#'
#' @param gazepoint Gazepoint sample-level data.
#' @param gazepoint_events Gazepoint event table or numeric times.
#' @param eeg_events EEG event table or numeric times.
#' @param gazepoint_time_col Gazepoint stream time column.
#' @param gazepoint_event_time_col Gazepoint event-time column.
#' @param eeg_event_time_col EEG event-time column.
#' @param eeg_event_sample_col Optional EEG event-sample column.
#' @param gazepoint_event_id_col Optional Gazepoint event identifier.
#' @param eeg_event_id_col Optional EEG event identifier.
#' @param gazepoint_time_unit Gazepoint time unit.
#' @param eeg_time_unit EEG event-time unit.
#' @param eeg_sampling_rate_hz Required when EEG events are sample numbers.
#' @param method `"offset"` or `"linear"`.
#' @param match_by Match events by identifier or row order.
#' @param robust Use one MAD-based residual refit for linear alignment.
#' @param maximum_residual_s Optional maximum permitted absolute residual.
#' @param residual_action Handling when the residual threshold is exceeded.
#' @param output_col Added aligned-time column.
#'
#' @return A `"gazepoint_eeg_alignment"` object.
#'
#' @export
align_gazepoint_to_eeg <- function(
    gazepoint,
    gazepoint_events,
    eeg_events,
    gazepoint_time_col = NULL,
    gazepoint_event_time_col = NULL,
    eeg_event_time_col = NULL,
    eeg_event_sample_col = NULL,
    gazepoint_event_id_col = NULL,
    eeg_event_id_col = NULL,
    gazepoint_time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    eeg_time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    eeg_sampling_rate_hz = NULL,
    method = c("offset", "linear"),
    match_by = c("auto", "id", "row"),
    robust = TRUE,
    maximum_residual_s = NULL,
    residual_action = c("error", "allow"),
    output_col = "time_eeg_s") {
  gazepoint_time_unit <- match.arg(
    gazepoint_time_unit
  )

  eeg_time_unit <- match.arg(
    eeg_time_unit
  )

  method <- match.arg(method)
  match_by <- match.arg(match_by)
  residual_action <- match.arg(
    residual_action
  )

  .gp_mm_logical_scalar(
    robust,
    "robust"
  )

  output_col <- .gp_mm_nonempty_string(
    output_col,
    "output_col"
  )

  if (!is.null(maximum_residual_s)) {
    .gp_mm_nonnegative_scalar(
      maximum_residual_s,
      "maximum_residual_s"
    )
  }

  if (!is.data.frame(gazepoint)) {
    stop(
      "`gazepoint` must be a data frame.",
      call. = FALSE
    )
  }

  gazepoint_time_col <- .gp_mm_resolve_col(
    gazepoint,
    gazepoint_time_col,
    c(
      "time_s",
      "time_ms",
      "time",
      "timestamp",
      "MSTIMER",
      "CNT"
    ),
    "Gazepoint time",
    TRUE
  )

  stream_time_raw <- suppressWarnings(
    as.numeric(
      gazepoint[[gazepoint_time_col]]
    )
  )

  if (
    anyNA(stream_time_raw) ||
      any(!is.finite(stream_time_raw))
  ) {
    stop(
      "Gazepoint stream time must contain finite values.",
      call. = FALSE
    )
  }

  gp_unit <- .gp_mm_resolve_time_unit(
    stream_time_raw,
    gazepoint_time_col,
    gazepoint_time_unit
  )

  if (
    identical(gp_unit, "samples") &&
      is.null(eeg_sampling_rate_hz)
  ) {
    stop(
      "`eeg_sampling_rate_hz` is required for sample-unit alignment.",
      call. = FALSE
    )
  }

  stream_time_s <- .gp_mm_convert_time_seconds(
    stream_time_raw,
    gp_unit,
    eeg_sampling_rate_hz
  )

  gp_events <- .gp_eeg_event_table(
    gazepoint_events,
    time_col =
      gazepoint_event_time_col,
    sample_col =
      NULL,
    id_col =
      gazepoint_event_id_col,
    time_unit =
      gazepoint_time_unit,
    sampling_rate_hz =
      eeg_sampling_rate_hz,
    label = "Gazepoint"
  )

  eeg_events_standard <- .gp_eeg_event_table(
    eeg_events,
    time_col =
      eeg_event_time_col,
    sample_col =
      eeg_event_sample_col,
    id_col =
      eeg_event_id_col,
    time_unit =
      eeg_time_unit,
    sampling_rate_hz =
      eeg_sampling_rate_hz,
    label = "EEG"
  )

  has_ids <- !all(is.na(gp_events$event_id)) &&
    !all(is.na(eeg_events_standard$event_id))

  resolved_match <- if (
    identical(match_by, "auto")
  ) {
    if (has_ids) "id" else "row"
  } else {
    match_by
  }

  if (
    identical(resolved_match, "id") &&
      !has_ids
  ) {
    stop(
      "Both event tables require usable identifiers for `match_by = \"id\"`.",
      call. = FALSE
    )
  }

  if (identical(resolved_match, "id")) {
    if (
      anyDuplicated(gp_events$event_id) ||
        anyDuplicated(
          eeg_events_standard$event_id
        )
    ) {
      stop(
        "Event identifiers must be unique for ID-based alignment.",
        call. = FALSE
      )
    }

    matched <- merge(
      gp_events,
      eeg_events_standard,
      by = "event_id",
      suffixes = c(
        "_gazepoint",
        "_eeg"
      ),
      sort = FALSE
    )

    matched <- matched[
      match(
        gp_events$event_id,
        matched$event_id
      ),
      ,
      drop = FALSE
    ]

    matched <- matched[
      !is.na(matched$event_id),
      ,
      drop = FALSE
    ]
  } else {
    if (
      nrow(gp_events) !=
        nrow(eeg_events_standard)
    ) {
      stop(
        "Row-based alignment requires equal event counts.",
        call. = FALSE
      )
    }

    matched <- data.frame(
      event_id =
        seq_len(nrow(gp_events)),
      event_time_s_gazepoint =
        gp_events$event_time_s,
      event_time_s_eeg =
        eeg_events_standard$event_time_s,
      stringsAsFactors = FALSE
    )
  }

  if (
    identical(method, "offset") &&
      nrow(matched) < 1L
  ) {
    stop(
      "At least one matched event is required.",
      call. = FALSE
    )
  }

  if (
    identical(method, "linear") &&
      nrow(matched) < 3L
  ) {
    stop(
      "At least three matched events are required for linear alignment.",
      call. = FALSE
    )
  }

  x <- matched$event_time_s_gazepoint
  y <- matched$event_time_s_eeg

  used <- rep(
    TRUE,
    length(x)
  )

  if (identical(method, "offset")) {
    slope <- 1
    intercept <- stats::median(
      y - x
    )
  } else {
    fit <- stats::lm(
      y ~ x
    )

    if (
      isTRUE(robust) &&
        length(x) >= 4L
    ) {
      residual <- stats::residuals(fit)
      residual_median <- stats::median(
        residual
      )
      residual_mad <- stats::mad(
        residual,
        center = residual_median,
        constant = 1.4826
      )

      if (
        is.finite(residual_mad) &&
          residual_mad > 0
      ) {
        used <- abs(
          residual -
            residual_median
        ) <=
          3 * residual_mad

        if (sum(used) >= 3L) {
          fit <- stats::lm(
            y[used] ~ x[used]
          )
        } else {
          used[] <- TRUE
        }
      }
    }

    coefficients <- stats::coef(fit)
    intercept <- unname(
      coefficients[1L]
    )
    slope <- unname(
      coefficients[2L]
    )
  }

  fitted <- intercept +
    slope * x

  residual_s <- y - fitted

  maximum_observed_residual <- max(
    abs(residual_s)
  )

  if (
    !is.null(maximum_residual_s) &&
      maximum_observed_residual >
        maximum_residual_s &&
      identical(residual_action, "error")
  ) {
    stop(
      "Alignment residuals exceed `maximum_residual_s`.",
      call. = FALSE
    )
  }

  aligned_data <- gazepoint

  if (output_col %in% names(aligned_data)) {
    stop(
      "`output_col` already exists in `gazepoint`.",
      call. = FALSE
    )
  }

  aligned_data[[output_col]] <-
    intercept +
    slope * stream_time_s

  if (!is.null(eeg_sampling_rate_hz)) {
    .gp_mm_positive_scalar(
      eeg_sampling_rate_hz,
      "eeg_sampling_rate_hz"
    )

    sample_col <- paste0(
      output_col,
      "_sample"
    )

    aligned_data[[sample_col]] <-
      as.integer(
        round(
          aligned_data[[output_col]] *
            eeg_sampling_rate_hz
        )
      )
  }

  matched$fitted_eeg_time_s <- fitted
  matched$residual_s <- residual_s
  matched$used_for_fit <- used

  audit <- data.frame(
    method = method,
    match_by = resolved_match,
    matched_event_count =
      nrow(matched),
    used_event_count =
      sum(used),
    intercept_s =
      intercept,
    slope =
      slope,
    drift_ppm =
      (slope - 1) * 1e6,
    median_residual_s =
      stats::median(residual_s),
    maximum_absolute_residual_s =
      maximum_observed_residual,
    residual_threshold_s =
      if (is.null(maximum_residual_s)) {
        NA_real_
      } else {
        maximum_residual_s
      },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      data = aligned_data,
      matched_events = matched,
      mapping = list(
        intercept_s = intercept,
        slope = slope,
        equation =
          "eeg_time_s = intercept_s + slope * gazepoint_time_s"
      ),
      audit = audit,
      settings = list(
        gazepoint_time_col =
          gazepoint_time_col,
        gazepoint_time_unit =
          gp_unit,
        eeg_sampling_rate_hz =
          eeg_sampling_rate_hz,
        method =
          method,
        match_by =
          resolved_match,
        robust =
          robust,
        output_col =
          output_col
      )
    ),
    class = c(
      "gazepoint_eeg_alignment",
      "list"
    )
  )
}

#' @export
print.gazepoint_eeg_alignment <- function(
    x,
    ...) {
  cat("Gazepoint-to-EEG alignment\n")
  cat(
    "  Method: ",
    x$audit$method,
    "\n",
    sep = ""
  )
  cat(
    "  Matched events: ",
    x$audit$matched_event_count,
    "\n",
    sep = ""
  )
  cat(
    "  Offset: ",
    format(
      x$audit$intercept_s,
      digits = 8
    ),
    " s\n",
    sep = ""
  )
  cat(
    "  Drift: ",
    format(
      x$audit$drift_ppm,
      digits = 8
    ),
    " ppm\n",
    sep = ""
  )

  invisible(x)
}

#' Create reproducible Gazepoint eye-tracking methods text
#'
#' @param sampling_rate_hz Recording frequency.
#' @param device_model Device model.
#' @param calibration_points Number of calibration points.
#' @param binocular Whether binocular data were recorded.
#' @param software Optional acquisition software.
#' @param screen_resolution Optional width-height pixel vector.
#' @param viewing_distance_cm Optional viewing distance.
#' @param coordinate_space Optional coordinate description.
#' @param preprocessing Optional preprocessing descriptions.
#' @param fixation_detection Optional fixation-detection description.
#' @param aoi_definition Optional AOI description.
#' @param synchronization Optional synchronization description.
#' @param exclusions Optional exclusion description.
#' @param tense `"past"` for manuscripts or `"future"` for preregistrations.
#' @param include_package_version Include the gpbiometrics version.
#'
#' @return A character object of class `"gazepoint_eye_methods_text"`.
#'
#' @export
create_gazepoint_eye_methods_text <- function(
    sampling_rate_hz,
    device_model = "Gazepoint GP3",
    calibration_points = 9L,
    binocular = TRUE,
    software = "Gazepoint Analysis",
    screen_resolution = NULL,
    viewing_distance_cm = NULL,
    coordinate_space = NULL,
    preprocessing = NULL,
    fixation_detection = NULL,
    aoi_definition = NULL,
    synchronization = NULL,
    exclusions = NULL,
    tense = c("past", "future"),
    include_package_version = TRUE) {
  tense <- match.arg(tense)

  .gp_mm_positive_scalar(
    sampling_rate_hz,
    "sampling_rate_hz"
  )

  calibration_points <- .gp_mm_integer_scalar(
    calibration_points,
    "calibration_points"
  )

  .gp_mm_logical_scalar(
    binocular,
    "binocular"
  )

  .gp_mm_logical_scalar(
    include_package_version,
    "include_package_version"
  )

  acquisition_verb <- if (
    identical(tense, "past")
  ) {
    "were recorded"
  } else {
    "will be recorded"
  }

  calibration_verb <- if (
    identical(tense, "past")
  ) {
    "was performed"
  } else {
    "will be performed"
  }

  processing_verb <- if (
    identical(tense, "past")
  ) {
    "were processed"
  } else {
    "will be processed"
  }

  sentences <- c(
    paste0(
      "Eye-tracking data ",
      acquisition_verb,
      " using a ",
      device_model,
      " system at ",
      format(
        sampling_rate_hz,
        trim = TRUE
      ),
      " Hz."
    ),
    paste0(
      "A ",
      calibration_points,
      "-point calibration ",
      calibration_verb,
      " before recording."
    ),
    if (isTRUE(binocular)) {
      "Binocular gaze and pupil channels were retained when available."
    } else {
      "A monocular or combined-eye signal was retained."
    }
  )

  if (!is.null(software)) {
    sentences <- c(
      sentences,
      paste0(
        "Data acquisition used ",
        software,
        "."
      )
    )
  }

  if (!is.null(screen_resolution)) {
    if (
      !is.numeric(screen_resolution) ||
        length(screen_resolution) != 2L ||
        any(!is.finite(screen_resolution)) ||
        any(screen_resolution <= 0)
    ) {
      stop(
        "`screen_resolution` must contain width and height in pixels.",
        call. = FALSE
      )
    }

    sentences <- c(
      sentences,
      paste0(
        "Stimuli were presented at a screen resolution of ",
        round(screen_resolution[1L]),
        " x ",
        round(screen_resolution[2L]),
        " pixels."
      )
    )
  }

  if (!is.null(viewing_distance_cm)) {
    .gp_mm_positive_scalar(
      viewing_distance_cm,
      "viewing_distance_cm"
    )

    sentences <- c(
      sentences,
      paste0(
        "The nominal viewing distance was ",
        format(
          viewing_distance_cm,
          trim = TRUE
        ),
        " cm."
      )
    )
  }

  if (!is.null(coordinate_space)) {
    sentences <- c(
      sentences,
      paste0(
        "Gaze coordinates were represented as ",
        coordinate_space,
        "."
      )
    )
  }

  if (!is.null(preprocessing)) {
    sentences <- c(
      sentences,
      paste0(
        "Eye-tracking samples ",
        processing_verb,
        " using ",
        paste(
          preprocessing,
          collapse = "; "
        ),
        "."
      )
    )
  }

  if (!is.null(fixation_detection)) {
    sentences <- c(
      sentences,
      paste0(
        "Fixations and saccades were defined using ",
        fixation_detection,
        "."
      )
    )
  }

  if (!is.null(aoi_definition)) {
    sentences <- c(
      sentences,
      paste0(
        "Areas of interest were defined as ",
        aoi_definition,
        "."
      )
    )
  }

  if (!is.null(synchronization)) {
    sentences <- c(
      sentences,
      paste0(
        "Multimodal timing was synchronized using ",
        synchronization,
        "."
      )
    )
  }

  if (!is.null(exclusions)) {
    sentences <- c(
      sentences,
      paste0(
        "Data-quality exclusions followed ",
        exclusions,
        "."
      )
    )
  }

  if (isTRUE(include_package_version)) {
    version <- .gp_mm_package_version(
      "gpbiometrics"
    )

    sentences <- c(
      sentences,
      paste0(
        "Data preparation and audit reporting used the gpbiometrics R package",
        if (!is.na(version)) {
          paste0(
            " (version ",
            version,
            ")"
          )
        } else {
          ""
        },
        "."
      )
    )
  }

  text <- paste(
    sentences,
    collapse = " "
  )

  structure(
    text,
    class = c(
      "gazepoint_eye_methods_text",
      "character"
    ),
    settings = list(
      sampling_rate_hz =
        sampling_rate_hz,
      device_model =
        device_model,
      calibration_points =
        calibration_points,
      binocular =
        binocular,
      software =
        software,
      tense =
        tense
    )
  )
}

#' @export
print.gazepoint_eye_methods_text <- function(
    x,
    ...) {
  cat(
    unclass(x),
    "\n",
    sep = ""
  )

  invisible(x)
}

#' Record gpbiometrics session information
#'
#' @param packages Optional additional packages to report.
#' @param include_loaded Include loaded namespaces.
#' @param timestamp Timestamp recorded in the output.
#'
#' @return A `"gazepoint_session_info"` object containing system metadata,
#'   package versions, and printable session text.
#'
#' @export
session_info_gazepoint <- function(
    packages = NULL,
    include_loaded = TRUE,
    timestamp = Sys.time()) {
  .gp_mm_logical_scalar(
    include_loaded,
    "include_loaded"
  )

  requested <- if (is.null(packages)) {
    character()
  } else {
    unique(
      as.character(packages)
    )
  }

  loaded <- if (isTRUE(include_loaded)) {
    loadedNamespaces()
  } else {
    character()
  }

  package_names <- unique(
    c(
      "gpbiometrics",
      requested,
      loaded
    )
  )

  package_table <- data.frame(
    package =
      package_names,
    version =
      vapply(
        package_names,
        .gp_mm_package_version,
        character(1)
      ),
    loaded =
      package_names %in%
      loaded,
    explicitly_requested =
      package_names %in%
      requested,
    stringsAsFactors = FALSE
  )

  package_table <- package_table[
    order(package_table$package),
    ,
    drop = FALSE
  ]

  rownames(package_table) <- NULL

  info <- utils::sessionInfo()

  system <- data.frame(
    field = c(
      "timestamp",
      "r_version",
      "platform",
      "running",
      "timezone",
      "locale"
    ),
    value = c(
      format(
        timestamp,
        tz = "UTC",
        usetz = TRUE
      ),
      R.version.string,
      R.version$platform,
      info$running,
      Sys.timezone(),
      paste(
        info$locale,
        collapse = "; "
      )
    ),
    stringsAsFactors = FALSE
  )

  text <- utils::capture.output(
    utils::sessionInfo()
  )

  structure(
    list(
      system = system,
      packages = package_table,
      text = text,
      timestamp = timestamp
    ),
    class = c(
      "gazepoint_session_info",
      "list"
    )
  )
}

#' @export
print.gazepoint_session_info <- function(
    x,
    ...) {
  cat("Gazepoint session information\n")
  cat(
    "  Timestamp: ",
    x$system$value[
      x$system$field == "timestamp"
    ],
    "\n",
    sep = ""
  )
  cat(
    "  R: ",
    x$system$value[
      x$system$field == "r_version"
    ],
    "\n",
    sep = ""
  )
  cat(
    "  Reported packages: ",
    nrow(x$packages),
    "\n",
    sep = ""
  )

  invisible(x)
}

#' Synchronize imported Gazepoint LSL/XDF streams
#'
#' Applies explicit clock offsets and known latency corrections to already
#' imported LSL/XDF streams. Input may be named data frames or pyxdf-style
#' stream lists containing `time_stamps` and `time_series`.
#'
#' @param streams Named list of imported streams.
#' @param reference Name of the reference stream.
#' @param time_cols Optional named time-column vector or list.
#' @param clock_offsets_s Values added to stream timestamps to place them in
#'   the reference clock domain.
#' @param known_lags_s Known acquisition latencies subtracted from timestamps.
#' @param relative_zero Origin for relative synchronized time.
#' @param dejitter Optional transparent linear timestamp regularization.
#' @param nominal_rates_hz Optional named nominal sampling frequencies.
#' @param merge Whether to return separate streams or a nearest-neighbour
#'   merged table on the reference stream.
#' @param tolerance_s Optional nearest-neighbour tolerance.
#'
#' @return A `"gazepoint_lsl_sync"` object.
#'
#' @seealso [import_gazepoint_lsl_xdf()]
#'
#' @export
sync_gazepoint_signals_via_lsl <- function(
    streams,
    reference = NULL,
    time_cols = NULL,
    clock_offsets_s = NULL,
    known_lags_s = NULL,
    relative_zero = c(
      "reference",
      "global",
      "none"
    ),
    dejitter = c("none", "linear"),
    nominal_rates_hz = NULL,
    merge = c("none", "nearest"),
    tolerance_s = NULL) {
  relative_zero <- match.arg(
    relative_zero
  )

  dejitter <- match.arg(
    dejitter
  )

  merge <- match.arg(
    merge
  )

  if (
    !is.list(streams) ||
      length(streams) == 0L
  ) {
    stop(
      "`streams` must be a non-empty named list.",
      call. = FALSE
    )
  }

  stream_names <- names(streams)

  if (
    is.null(stream_names) ||
      anyNA(stream_names) ||
      any(!nzchar(trimws(stream_names))) ||
      anyDuplicated(stream_names)
  ) {
    stop(
      "`streams` must have unique, non-empty names.",
      call. = FALSE
    )
  }

  if (is.null(reference)) {
    reference <- stream_names[1L]
  }

  reference <- .gp_mm_nonempty_string(
    reference,
    "reference"
  )

  if (!reference %in% stream_names) {
    stop(
      "`reference` was not found in `streams`.",
      call. = FALSE
    )
  }

  if (!is.null(tolerance_s)) {
    .gp_mm_nonnegative_scalar(
      tolerance_s,
      "tolerance_s"
    )
  }

  clock_offsets <- .gp_lsl_stream_values(
    clock_offsets_s,
    stream_names,
    default = 0,
    argument = "clock_offsets_s"
  )

  known_lags <- .gp_lsl_stream_values(
    known_lags_s,
    stream_names,
    default = 0,
    argument = "known_lags_s"
  )

  nominal_rates <- .gp_lsl_stream_values(
    nominal_rates_hz,
    stream_names,
    default = NA_real_,
    argument = "nominal_rates_hz",
    positive_or_missing = TRUE
  )

  normalized <- vector(
    "list",
    length(streams)
  )

  names(normalized) <- stream_names

  original_time_cols <- character(
    length(streams)
  )

  names(original_time_cols) <- stream_names

  for (stream_name in stream_names) {
    supplied_time_col <- .gp_lsl_time_col(
      time_cols,
      stream_name
    )

    one <- .gp_lsl_normalize_stream(
      streams[[stream_name]],
      supplied_time_col,
      stream_name
    )

    original_time <- one$time
    table <- one$data

    corrected_time <- original_time +
      clock_offsets[stream_name] -
      known_lags[stream_name]

    if (
      identical(dejitter, "linear") &&
        length(corrected_time) >= 3L
    ) {
      nominal_rate <-
        nominal_rates[stream_name]

      if (
        is.finite(nominal_rate) &&
          nominal_rate > 0
      ) {
        corrected_time <-
          corrected_time[1L] +
          (
            seq_along(corrected_time) -
              1L
          ) /
          nominal_rate
      } else {
        index <- seq_along(
          corrected_time
        )

        fit <- stats::lm(
          corrected_time ~ index
        )

        corrected_time <-
          as.numeric(
            stats::fitted(fit)
          )
      }
    }

    table$.lsl_time_original_s <-
      original_time

    table$.lsl_time_corrected_s <-
      corrected_time

    normalized[[stream_name]] <-
      table

    original_time_cols[stream_name] <-
      one$time_col
  }

  origin <- switch(
    relative_zero,
    reference =
      min(
        normalized[[reference]]$
          .lsl_time_corrected_s
      ),
    global =
      min(
        vapply(
          normalized,
          function(x) {
            min(
              x$.lsl_time_corrected_s
            )
          },
          numeric(1)
        )
      ),
    none = 0
  )

  for (stream_name in stream_names) {
    normalized[[stream_name]]$
      .lsl_time_relative_s <-
      normalized[[stream_name]]$
        .lsl_time_corrected_s -
      origin
  }

  audit_rows <- lapply(
    stream_names,
    function(stream_name) {
      table <- normalized[[stream_name]]
      time <- table$.lsl_time_corrected_s
      interval <- diff(time)
      positive <- interval[
        is.finite(interval) &
          interval > 0
      ]

      median_interval <- if (
        length(positive) > 0L
      ) {
        stats::median(positive)
      } else {
        NA_real_
      }

      data.frame(
        stream =
          stream_name,
        sample_count =
          nrow(table),
        original_time_col =
          original_time_cols[stream_name],
        start_time_s =
          min(time),
        end_time_s =
          max(time),
        duration_s =
          max(time) -
          min(time),
        median_interval_s =
          median_interval,
        effective_sampling_rate_hz = if (
          is.finite(median_interval) &&
            median_interval > 0
        ) {
          1 / median_interval
        } else {
          NA_real_
        },
        clock_offset_added_s =
          clock_offsets[stream_name],
        known_lag_subtracted_s =
          known_lags[stream_name],
        dejitter =
          dejitter,
        stringsAsFactors = FALSE
      )
    }
  )

  audit <- do.call(
    rbind,
    audit_rows
  )

  rownames(audit) <- NULL

  merged <- NULL

  if (identical(merge, "nearest")) {
    merged <- .gp_lsl_merge_nearest(
      normalized,
      reference,
      tolerance_s
    )
  }

  structure(
    list(
      streams = normalized,
      merged = merged,
      audit = audit,
      settings = list(
        reference =
          reference,
        relative_zero =
          relative_zero,
        origin_s =
          origin,
        dejitter =
          dejitter,
        merge =
          merge,
        tolerance_s =
          tolerance_s,
        interpretation_notes = c(
          "Clock offsets are added to stream timestamps.",
          "Known constant acquisition lags are subtracted.",
          "Linear dejittering is applied only when explicitly requested.",
          "Nearest-neighbour merging does not interpolate signal values.",
          "Raw XDF parsing remains the responsibility of import_gazepoint_lsl_xdf()."
        )
      )
    ),
    class = c(
      "gazepoint_lsl_sync",
      "list"
    )
  )
}

#' @export
print.gazepoint_lsl_sync <- function(
    x,
    ...) {
  cat("Gazepoint LSL/XDF synchronization\n")
  cat(
    "  Streams: ",
    nrow(x$audit),
    "\n",
    sep = ""
  )
  cat(
    "  Reference: ",
    x$settings$reference,
    "\n",
    sep = ""
  )
  cat(
    "  Merged table: ",
    if (is.null(x$merged)) {
      "no"
    } else {
      "yes"
    },
    "\n",
    sep = ""
  )

  invisible(x)
}

.gp_mne_event_dictionary <- function(
    labels,
    event_id) {
  unique_labels <- unique(
    as.character(labels)
  )

  if (is.null(event_id)) {
    return(
      data.frame(
        event_label =
          unique_labels,
        event_code =
          seq_along(unique_labels),
        stringsAsFactors = FALSE
      )
    )
  }

  if (is.data.frame(event_id)) {
    if (
      !all(
        c(
          "event_label",
          "event_code"
        ) %in%
          names(event_id)
      )
    ) {
      stop(
        "`event_id` data frame must contain `event_label` and `event_code`.",
        call. = FALSE
      )
    }

    dictionary <- event_id[
      ,
      c(
        "event_label",
        "event_code"
      ),
      drop = FALSE
    ]
  } else {
    if (
      !is.numeric(event_id) ||
        is.null(names(event_id))
    ) {
      stop(
        "`event_id` must be a named numeric vector or data frame.",
        call. = FALSE
      )
    }

    dictionary <- data.frame(
      event_label =
        names(event_id),
      event_code =
        as.numeric(event_id),
      stringsAsFactors = FALSE
    )
  }

  dictionary$event_label <-
    as.character(
      dictionary$event_label
    )

  dictionary$event_code <-
    suppressWarnings(
      as.numeric(
        dictionary$event_code
      )
    )

  if (
    anyNA(dictionary$event_label) ||
      any(!nzchar(trimws(dictionary$event_label))) ||
      anyNA(dictionary$event_code) ||
      any(!is.finite(dictionary$event_code)) ||
      any(dictionary$event_code <= 0) ||
      any(
        dictionary$event_code !=
          round(dictionary$event_code)
      ) ||
      anyDuplicated(dictionary$event_label) ||
      anyDuplicated(dictionary$event_code)
  ) {
    stop(
      "`event_id` must define unique labels and positive integer codes.",
      call. = FALSE
    )
  }

  missing_labels <- setdiff(
    unique_labels,
    dictionary$event_label
  )

  if (length(missing_labels) > 0L) {
    stop(
      "Unmapped event labels: ",
      paste(
        missing_labels,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  dictionary$event_code <-
    as.integer(
      dictionary$event_code
    )

  dictionary
}

.gp_mne_channel_types <- function(
    channel_cols,
    channel_types) {
  if (is.null(channel_types)) {
    types <- vapply(
      channel_cols,
      .gp_mne_infer_type,
      character(1)
    )
  } else {
    channel_types <- as.character(
      channel_types
    )

    if (!is.null(names(channel_types))) {
      missing <- setdiff(
        channel_cols,
        names(channel_types)
      )

      if (length(missing) > 0L) {
        stop(
          "Missing channel types for: ",
          paste(
            missing,
            collapse = ", "
          ),
          call. = FALSE
        )
      }

      types <- unname(
        channel_types[channel_cols]
      )
    } else {
      if (
        length(channel_types) !=
          length(channel_cols)
      ) {
        stop(
          "`channel_types` must have one value per channel.",
          call. = FALSE
        )
      }

      types <- channel_types
    }
  }

  allowed <- c(
    "eyegaze",
    "pupil",
    "gsr",
    "bio",
    "stim",
    "resp",
    "temperature",
    "misc"
  )

  invalid <- setdiff(
    unique(types),
    allowed
  )

  if (length(invalid) > 0L) {
    stop(
      "Unsupported MNE channel types: ",
      paste(
        invalid,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  types
}

.gp_mne_infer_type <- function(name) {
  lower <- tolower(name)

  if (
    grepl(
      "ttl|marker|trigger|event",
      lower
    )
  ) {
    return("stim")
  }

  if (grepl("pupil", lower) ||
      grepl("(^|_)lpd($|_)", lower) ||
      grepl("(^|_)rpd($|_)", lower)) {
    return("pupil")
  }

  if (
    grepl(
      "gaze|pog|(^|_)[xy](_|$)",
      lower
    )
  ) {
    return("eyegaze")
  }

  if (
    grepl(
      "gsr|eda|conductance",
      lower
    )
  ) {
    return("gsr")
  }

  if (
    grepl(
      "resp|breath",
      lower
    )
  ) {
    return("resp")
  }

  if (
    grepl(
      "temperature|(^|_)temp($|_)",
      lower
    )
  ) {
    return("temperature")
  }

  if (
    grepl(
      "ppg|bvp|pulse|heart|(^|_)hr($|_)|ibi|(^|_)rr($|_)",
      lower
    )
  ) {
    return("bio")
  }

  "misc"
}

.gp_eeg_event_table <- function(
    x,
    time_col,
    sample_col,
    id_col,
    time_unit,
    sampling_rate_hz,
    label) {
  if (is.numeric(x) && !is.data.frame(x)) {
    return(
      data.frame(
        event_id =
          rep(
            NA_character_,
            length(x)
          ),
        event_time_s =
          as.numeric(x),
        stringsAsFactors = FALSE
      )
    )
  }

  if (!is.data.frame(x)) {
    stop(
      "`",
      label,
      " events` must be a numeric vector or data frame.",
      call. = FALSE
    )
  }

  if (nrow(x) == 0L) {
    stop(
      "`",
      label,
      " events` must contain rows.",
      call. = FALSE
    )
  }

  resolved_id <- .gp_mm_resolve_col(
    x,
    id_col,
    c(
      "event_id",
      "trial_id",
      "trial",
      "marker",
      "condition"
    ),
    paste0(label, " event ID"),
    FALSE
  )

  if (!is.null(sample_col)) {
    sample_col <- .gp_mm_resolve_col(
      x,
      sample_col,
      character(),
      paste0(label, " event sample"),
      TRUE
    )

    if (is.null(sampling_rate_hz)) {
      stop(
        "`eeg_sampling_rate_hz` is required with an EEG sample column.",
        call. = FALSE
      )
    }

    .gp_mm_positive_scalar(
      sampling_rate_hz,
      "eeg_sampling_rate_hz"
    )

    event_time_s <- suppressWarnings(
      as.numeric(
        x[[sample_col]]
      )
    ) /
      sampling_rate_hz
  } else {
    resolved_time <- .gp_mm_resolve_col(
      x,
      time_col,
      c(
        "event_time_s",
        "event_time",
        "onset_s",
        "onset",
        "time_s",
        "time_ms",
        "time",
        "timestamp"
      ),
      paste0(label, " event time"),
      TRUE
    )

    raw_time <- suppressWarnings(
      as.numeric(
        x[[resolved_time]]
      )
    )

    resolved_unit <- .gp_mm_resolve_time_unit(
      raw_time,
      resolved_time,
      time_unit
    )

    event_time_s <- .gp_mm_convert_time_seconds(
      raw_time,
      resolved_unit,
      sampling_rate_hz
    )
  }

  if (
    anyNA(event_time_s) ||
      any(!is.finite(event_time_s))
  ) {
    stop(
      label,
      " event times must be finite.",
      call. = FALSE
    )
  }

  data.frame(
    event_id = if (
      is.null(resolved_id)
    ) {
      rep(
        NA_character_,
        nrow(x)
      )
    } else {
      as.character(
        x[[resolved_id]]
      )
    },
    event_time_s =
      event_time_s,
    stringsAsFactors = FALSE
  )
}

.gp_lsl_normalize_stream <- function(
    stream,
    time_col,
    stream_name) {
  if (is.data.frame(stream)) {
    table <- stream
  } else if (
    is.list(stream) &&
      !is.null(stream$data) &&
      is.data.frame(stream$data)
  ) {
    table <- stream$data

    if (
      !is.null(stream$time_stamps) &&
        !"time_stamps" %in% names(table)
    ) {
      table$time_stamps <-
        as.numeric(
          stream$time_stamps
        )
    }
  } else if (
    is.list(stream) &&
      !is.null(stream$time_stamps) &&
      !is.null(stream$time_series)
  ) {
    time_stamps <- as.numeric(
      stream$time_stamps
    )

    series <- stream$time_series

    if (is.data.frame(series)) {
      table <- series
    } else if (is.matrix(series)) {
      if (
        nrow(series) !=
          length(time_stamps) &&
          ncol(series) ==
            length(time_stamps)
      ) {
        series <- t(series)
      }

      if (
        nrow(series) !=
          length(time_stamps)
      ) {
        stop(
          "pyxdf-style stream `",
          stream_name,
          "` has incompatible timestamp and sample dimensions.",
          call. = FALSE
        )
      }

      table <- as.data.frame(
        series,
        stringsAsFactors = FALSE,
        check.names = FALSE
      )
    } else if (
      is.atomic(series) &&
        length(series) ==
          length(time_stamps)
    ) {
      table <- data.frame(
        channel_1 = series,
        stringsAsFactors = FALSE
      )
    } else if (
      is.list(series) &&
        length(series) ==
          length(time_stamps)
    ) {
      matrix_series <- do.call(
        rbind,
        series
      )

      table <- as.data.frame(
        matrix_series,
        stringsAsFactors = FALSE,
        check.names = FALSE
      )
    } else {
      stop(
        "Unsupported pyxdf-style `time_series` structure in stream `",
        stream_name,
        "`.",
        call. = FALSE
      )
    }

    if (
      is.null(names(table)) ||
        any(!nzchar(names(table)))
    ) {
      names(table) <- paste0(
        "channel_",
        seq_len(ncol(table))
      )
    }

    table$time_stamps <-
      time_stamps
  } else {
    stop(
      "Stream `",
      stream_name,
      "` must be a data frame or pyxdf-style stream list.",
      call. = FALSE
    )
  }

  if (nrow(table) == 0L) {
    stop(
      "Stream `",
      stream_name,
      "` contains no samples.",
      call. = FALSE
    )
  }

  resolved_time_col <- .gp_mm_resolve_col(
    table,
    time_col,
    c(
      "time_stamps",
      "lsl_time_s",
      "time_s",
      "timestamp",
      "time"
    ),
    paste0(
      stream_name,
      " time"
    ),
    TRUE
  )

  time <- suppressWarnings(
    as.numeric(
      table[[resolved_time_col]]
    )
  )

  if (
    anyNA(time) ||
      any(!is.finite(time))
  ) {
    stop(
      "Stream `",
      stream_name,
      "` contains non-finite timestamps.",
      call. = FALSE
    )
  }

  order_index <- order(
    time,
    seq_along(time)
  )

  table <- table[
    order_index,
    ,
    drop = FALSE
  ]

  time <- time[order_index]
  rownames(table) <- NULL

  list(
    data = table,
    time = time,
    time_col = resolved_time_col
  )
}

.gp_lsl_merge_nearest <- function(
    streams,
    reference,
    tolerance_s) {
  reference_table <- streams[[reference]]
  reference_time <-
    reference_table$.lsl_time_relative_s

  out <- reference_table

  other_streams <- setdiff(
    names(streams),
    reference
  )

  for (stream_name in other_streams) {
    target <- streams[[stream_name]]
    target_time <-
      target$.lsl_time_relative_s

    idx <- .gp_lsl_nearest_index(
      reference_time,
      target_time
    )

    difference <- target_time[idx] -
      reference_time

    if (!is.null(tolerance_s)) {
      idx[
        abs(difference) >
          tolerance_s
      ] <- NA_integer_

      difference[
        abs(difference) >
          tolerance_s
      ] <- NA_real_
    }

    internal_cols <- c(
      ".lsl_time_original_s",
      ".lsl_time_corrected_s",
      ".lsl_time_relative_s"
    )

    carry <- setdiff(
      names(target),
      internal_cols
    )

    prefix <- make.names(
      stream_name
    )

    for (column in carry) {
      output_name <- paste0(
        prefix,
        "__",
        column
      )

      out[[output_name]] <-
        target[[column]][idx]
    }

    out[[paste0(
      prefix,
      "__time_difference_s"
    )]] <- difference
  }

  out
}

.gp_lsl_nearest_index <- function(
    reference_time,
    target_time) {
  insertion <- findInterval(
    reference_time,
    target_time
  )

  lower <- pmax(
    insertion,
    1L
  )

  upper <- pmin(
    insertion + 1L,
    length(target_time)
  )

  lower_distance <- abs(
    reference_time -
      target_time[lower]
  )

  upper_distance <- abs(
    reference_time -
      target_time[upper]
  )

  ifelse(
    upper_distance <
      lower_distance,
    upper,
    lower
  )
}

.gp_lsl_stream_values <- function(
    x,
    stream_names,
    default,
    argument,
    positive_or_missing = FALSE) {
  if (is.null(x)) {
    result <- rep(
      default,
      length(stream_names)
    )

    names(result) <- stream_names
    return(result)
  }

  x <- as.numeric(x)

  if (!is.null(names(x))) {
    missing <- setdiff(
      stream_names,
      names(x)
    )

    if (length(missing) > 0L) {
      stop(
        "`",
        argument,
        "` is missing values for: ",
        paste(
          missing,
          collapse = ", "
        ),
        call. = FALSE
      )
    }

    x <- x[stream_names]
  } else if (length(x) == 1L) {
    x <- rep(
      x,
      length(stream_names)
    )
  } else if (
    length(x) !=
      length(stream_names)
  ) {
    stop(
      "`",
      argument,
      "` must be scalar, named, or parallel to `streams`.",
      call. = FALSE
    )
  }

  if (
    isTRUE(positive_or_missing)
  ) {
    invalid <- !is.na(x) &
      (
        !is.finite(x) |
          x <= 0
      )
  } else {
    invalid <- !is.finite(x)
  }

  if (any(invalid)) {
    stop(
      "Invalid values in `",
      argument,
      "`.",
      call. = FALSE
    )
  }

  names(x) <- stream_names
  x
}

.gp_lsl_time_col <- function(
    time_cols,
    stream_name) {
  if (is.null(time_cols)) {
    return(NULL)
  }

  if (is.list(time_cols)) {
    value <- time_cols[[stream_name]]
  } else if (!is.null(names(time_cols))) {
    value <- time_cols[stream_name]
  } else if (length(time_cols) == 1L) {
    value <- time_cols
  } else {
    stop(
      "`time_cols` must be named or scalar.",
      call. = FALSE
    )
  }

  if (
    is.null(value) ||
      length(value) == 0L ||
      is.na(value)
  ) {
    return(NULL)
  }

  as.character(value)[1L]
}

.gp_mm_resolve_col <- function(
    data,
    supplied,
    candidates,
    description,
    required) {
  if (!is.null(supplied)) {
    supplied <- .gp_mm_nonempty_string(
      supplied,
      paste0(
        description,
        "_col"
      )
    )

    if (!supplied %in% names(data)) {
      stop(
        "Selected ",
        description,
        " column was not found: ",
        supplied,
        ".",
        call. = FALSE
      )
    }

    return(supplied)
  }

  lower_names <- tolower(
    names(data)
  )

  for (candidate in candidates) {
    hit <- which(
      lower_names ==
        tolower(candidate)
    )

    if (length(hit) > 0L) {
      return(
        names(data)[hit[1L]]
      )
    }
  }

  if (isTRUE(required)) {
    stop(
      "Could not identify a ",
      description,
      " column. Supply it explicitly.",
      call. = FALSE
    )
  }

  NULL
}

.gp_mm_optional_cols <- function(
    data,
    columns,
    argument) {
  columns <- unique(
    as.character(columns)
  )

  if (
    anyNA(columns) ||
      any(!nzchar(trimws(columns)))
  ) {
    stop(
      "`",
      argument,
      "` must contain non-empty column names.",
      call. = FALSE
    )
  }

  missing <- setdiff(
    columns,
    names(data)
  )

  if (length(missing) > 0L) {
    stop(
      "Columns in `",
      argument,
      "` were not found: ",
      paste(
        missing,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  columns
}

.gp_mm_resolve_time_unit <- function(
    time,
    time_col,
    requested) {
  if (!identical(requested, "auto")) {
    return(requested)
  }

  lower <- tolower(time_col)

  if (
    grepl(
      "cnt|sample|index",
      lower
    )
  ) {
    return("samples")
  }

  if (
    grepl(
      "mstimer|timetick|time_tick|millisecond|msec|_ms$|^ms_",
      lower
    )
  ) {
    return("milliseconds")
  }

  if (
    grepl(
      "time_s|timestamp_s|onset_s|event_time_s|second|_sec$|^sec_",
      lower
    )
  ) {
    return("seconds")
  }

  delta <- diff(
    sort(unique(time))
  )

  delta <- delta[
    is.finite(delta) &
      delta > 0
  ]

  if (length(delta) == 0L) {
    stop(
      "Could not infer the time unit; supply it explicitly.",
      call. = FALSE
    )
  }

  median_delta <- stats::median(
    delta
  )

  if (median_delta < 1) {
    return("seconds")
  }

  if (median_delta >= 5) {
    return("milliseconds")
  }

  stop(
    "The time unit is ambiguous. Supply it explicitly.",
    call. = FALSE
  )
}

.gp_mm_convert_time_seconds <- function(
    time,
    unit,
    sampling_rate_hz) {
  switch(
    unit,
    seconds =
      as.numeric(time),
    milliseconds =
      as.numeric(time) / 1000,
    samples = {
      if (is.null(sampling_rate_hz)) {
        stop(
          "`sampling_rate_hz` is required for sample-index time.",
          call. = FALSE
        )
      }

      as.numeric(time) /
        sampling_rate_hz
    }
  )
}

.gp_mm_parallel_numeric <- function(
    x,
    names_reference,
    default,
    argument) {
  if (is.null(x)) {
    result <- rep(
      default,
      length(names_reference)
    )

    names(result) <- names_reference
    return(result)
  }

  x <- suppressWarnings(
    as.numeric(x)
  )

  if (!is.null(names(x))) {
    missing <- setdiff(
      names_reference,
      names(x)
    )

    if (length(missing) > 0L) {
      stop(
        "`",
        argument,
        "` is missing values for: ",
        paste(
          missing,
          collapse = ", "
        ),
        call. = FALSE
      )
    }

    x <- x[names_reference]
  } else if (length(x) == 1L) {
    x <- rep(
      x,
      length(names_reference)
    )
  } else if (
    length(x) !=
      length(names_reference)
  ) {
    stop(
      "`",
      argument,
      "` must be scalar, named, or parallel to the channels.",
      call. = FALSE
    )
  }

  if (
    anyNA(x) ||
      any(!is.finite(x))
  ) {
    stop(
      "`",
      argument,
      "` must contain finite numeric values.",
      call. = FALSE
    )
  }

  names(x) <- names_reference
  x
}

.gp_mm_python_list <- function(x) {
  paste0(
    "[",
    paste(
      paste0(
        "'",
        gsub(
          "'",
          "\\\\'",
          x,
          fixed = TRUE
        ),
        "'"
      ),
      collapse = ", "
    ),
    "]"
  )
}

.gp_mm_package_version <- function(package) {
  version <- tryCatch(
    as.character(
      utils::packageVersion(package)
    ),
    error = function(e) NA_character_
  )

  if (
    is.na(version) &&
      identical(package, "gpbiometrics") &&
      file.exists("DESCRIPTION")
  ) {
    description <- tryCatch(
      read.dcf("DESCRIPTION"),
      error = function(e) NULL
    )

    if (
      !is.null(description) &&
        "Version" %in%
          colnames(description)
    ) {
      version <- description[
        1L,
        "Version"
      ]
    }
  }

  version
}

.gp_mm_positive_scalar <- function(
    x,
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

  invisible(x)
}

.gp_mm_nonnegative_scalar <- function(
    x,
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

  invisible(x)
}

.gp_mm_finite_scalar <- function(
    x,
    argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x)
  ) {
    stop(
      "`",
      argument,
      "` must be one finite number.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_mm_integer_scalar <- function(
    x,
    argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x != round(x)
  ) {
    stop(
      "`",
      argument,
      "` must be one finite integer.",
      call. = FALSE
    )
  }

  as.integer(x)
}

.gp_mm_logical_scalar <- function(
    x,
    argument) {
  if (
    !is.logical(x) ||
      length(x) != 1L ||
      is.na(x)
  ) {
    stop(
      "`",
      argument,
      "` must be TRUE or FALSE.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_mm_nonempty_string <- function(
    x,
    argument) {
  x <- as.character(x)

  if (
    length(x) != 1L ||
      is.na(x) ||
      !nzchar(trimws(x))
  ) {
    stop(
      "`",
      argument,
      "` must be one non-empty character value.",
      call. = FALSE
    )
  }

  x
}
