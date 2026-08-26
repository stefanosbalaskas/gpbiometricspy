#' Export Gazepoint eye-tracking data to BIDS
#'
#' Exports one Gazepoint eye-tracking recording as a BIDS 1.11.1
#' physiological-recording pair consisting of a compressed, headerless
#' `_physio.tsv.gz` file and a matching JSON sidecar.
#'
#' @param data Data frame containing regularly sampled Gazepoint eye-tracking
#'   samples.
#' @param bids_root Root directory of the BIDS dataset.
#' @param subject BIDS subject label without the `sub-` prefix.
#' @param task BIDS task label without the `task-` prefix.
#' @param dataset_name Dataset name used when creating
#'   `dataset_description.json`. May be `NULL` when a valid file already exists.
#' @param recorded_eye Recorded eye: `"left"`, `"right"`, or `"cyclopean"`.
#' @param recording Required BIDS recording label. The recommended labels are
#'   `"eye1"`, `"eye2"`, and `"eye3"`.
#' @param datatype BIDS datatype directory. Supported values are `"beh"`,
#'   `"eeg"`, `"emg"`, `"func"`, `"ieeg"`, `"meg"`, `"motion"`, `"nirs"`,
#'   and `"pet"`.
#' @param session Optional BIDS session label without the `ses-` prefix.
#' @param acquisition Optional BIDS acquisition label without the `acq-`
#'   prefix.
#' @param run Optional non-negative BIDS run index.
#' @param timestamp_col Timestamp column issued by the eye tracker. If `NULL`,
#'   common Gazepoint timestamp columns are searched.
#' @param x_col Horizontal gaze-coordinate column. If `NULL`, common Gazepoint
#'   columns are searched according to `recorded_eye`.
#' @param y_col Vertical gaze-coordinate column. If `NULL`, common Gazepoint
#'   columns are searched according to `recorded_eye`.
#' @param include_pupil Logical. Attempt to include a `pupil_size` column.
#' @param pupil_col Optional pupil-size column. If `NULL` and
#'   `include_pupil = TRUE`, common Gazepoint pupil columns are searched.
#' @param additional_cols Optional additional numeric or logical columns to
#'   append after the prescribed eye-tracking columns.
#' @param timestamp_units Units of the source timestamp: `"auto"`, `"seconds"`,
#'   `"milliseconds"`, or `"microseconds"`.
#' @param coordinate_units Units of the gaze coordinates. `"normalized"` is
#'   encoded as the dimensionless BIDS unit `"1"`.
#' @param pupil_units Units of pupil size when included.
#' @param sample_coordinate_system Coordinate system: `"gaze-on-screen"`,
#'   `"eye-in-head"`, `"gaze-in-world"`, or `"custom"`.
#' @param sampling_rate_hz Optional positive sampling frequency. If omitted,
#'   it is inferred from the timestamps.
#' @param sampling_tolerance Maximum relative deviation from the expected
#'   sampling interval.
#' @param start_time_s BIDS `StartTime`, in seconds relative to the associated
#'   acquisition.
#' @param screen_distance_m Required for `"gaze-on-screen"` unless already
#'   defined in an existing events JSON sidecar.
#' @param screen_origin Two strings describing vertical and horizontal screen
#'   origin, for example `c("top", "left")`.
#' @param screen_resolution_px Two positive integers giving screen width and
#'   height in pixels.
#' @param screen_size_m Two positive numbers giving screen width and height in
#'   metres.
#' @param screen_refresh_rate_hz Optional screen refresh rate.
#' @param stimulus_software_name Optional stimulus-presentation software name.
#' @param stimulus_software_version Optional stimulus-presentation software
#'   version.
#' @param operating_system Optional operating-system description.
#' @param vision_correction Optional vision-correction description.
#' @param manufacturer Optional eye-tracker manufacturer.
#' @param manufacturers_model_name Optional eye-tracker model.
#' @param software_versions Optional acquisition-software version.
#' @param device_serial_number Optional device serial number or pseudonym.
#' @param eye_tracking_method Optional eye-tracking method.
#' @param calibration_type Optional calibration type, for example `"HV9"`.
#' @param calibration_count Optional non-negative calibration count.
#' @param average_calibration_error_deg Optional average calibration error.
#' @param maximal_calibration_error_deg Optional maximal calibration error.
#' @param eye_tracker_distance_m Optional eye-to-tracker distance in metres.
#' @param raw_data_filters Optional description of device-side filters.
#' @param timestamp_origin Description of the timestamp origin.
#' @param custom_coordinate_system_description Required when
#'   `sample_coordinate_system = "custom"`.
#' @param column_metadata Optional named list of additional or replacement
#'   metadata entries for exported columns.
#' @param bids_version BIDS specification version written to a newly created
#'   dataset description.
#' @param dry_run Logical. Validate and preview paths without writing files.
#' @param overwrite Logical. Permit replacement of the recording pair and
#'   merging of supplied stimulus metadata into an existing events JSON file.
#'
#' @return An object of class `"gazepoint_bids_export"` containing the prepared
#'   table, sidecars, file manifest, audit information, and settings.
#'
#' @details
#' One call exports one eye or one cyclopean recording. Binocular recordings
#' should be exported through separate calls with different `recording` labels
#' and appropriate `RecordedEye` metadata.
#'
#' The compressed TSV file is headerless. Its first three columns are always
#' `timestamp`, `x_coordinate`, and `y_coordinate`. Missing numeric values are
#' written as `n/a`.
#'
#' When `sample_coordinate_system = "gaze-on-screen"`, the corresponding events
#' JSON metadata must define screen distance, origin, resolution, and physical
#' size. This function creates or validates that metadata.
#'
#' This helper does not execute the external BIDS Validator. Exported datasets
#' should still be checked with the current official validator.
#'
#' @examples
#' gaze <- data.frame(
#'   TIME = c(0, 1 / 60, 2 / 60),
#'   BPOGX = c(0.45, 0.46, 0.47),
#'   BPOGY = c(0.52, 0.51, 0.50)
#' )
#'
#' preview <- export_gazepoint_to_bids(
#'   gaze,
#'   bids_root = tempfile("bids-"),
#'   subject = "01",
#'   task = "viewing",
#'   dataset_name = "Gazepoint viewing study",
#'   recorded_eye = "cyclopean",
#'   coordinate_units = "normalized",
#'   screen_distance_m = 0.60,
#'   screen_origin = c("top", "left"),
#'   screen_resolution_px = c(1920, 1080),
#'   screen_size_m = c(0.53, 0.30),
#'   dry_run = TRUE
#' )
#'
#' preview$files
#'
#' @seealso [check_gazepoint_bids()]
#'
#' @export
export_gazepoint_to_bids <- function(
    data,
    bids_root,
    subject,
    task,
    dataset_name = NULL,
    recorded_eye = c("cyclopean", "left", "right"),
    recording = "eye1",
    datatype = c(
      "beh", "eeg", "emg", "func", "ieeg",
      "meg", "motion", "nirs", "pet"
    ),
    session = NULL,
    acquisition = NULL,
    run = NULL,
    timestamp_col = NULL,
    x_col = NULL,
    y_col = NULL,
    include_pupil = TRUE,
    pupil_col = NULL,
    additional_cols = NULL,
    timestamp_units = c(
      "auto", "seconds", "milliseconds", "microseconds"
    ),
    coordinate_units = c(
      "normalized", "pixel", "degree", "radian",
      "mm", "cm", "m", "arbitrary"
    ),
    pupil_units = "arbitrary",
    sample_coordinate_system = c(
      "gaze-on-screen", "eye-in-head", "gaze-in-world", "custom"
    ),
    sampling_rate_hz = NULL,
    sampling_tolerance = 0.05,
    start_time_s = 0,
    screen_distance_m = NULL,
    screen_origin = NULL,
    screen_resolution_px = NULL,
    screen_size_m = NULL,
    screen_refresh_rate_hz = NULL,
    stimulus_software_name = NULL,
    stimulus_software_version = NULL,
    operating_system = NULL,
    vision_correction = NULL,
    manufacturer = "Gazepoint",
    manufacturers_model_name = NULL,
    software_versions = NULL,
    device_serial_number = NULL,
    eye_tracking_method = "P-CR",
    calibration_type = NULL,
    calibration_count = NULL,
    average_calibration_error_deg = NULL,
    maximal_calibration_error_deg = NULL,
    eye_tracker_distance_m = NULL,
    raw_data_filters = NULL,
    timestamp_origin = "Eye-tracker clock",
    custom_coordinate_system_description = NULL,
    column_metadata = list(),
    bids_version = "1.11.1",
    dry_run = FALSE,
    overwrite = FALSE) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop(
      "Package `jsonlite` is required for BIDS JSON export.",
      call. = FALSE
    )
  }

  recorded_eye <- match.arg(recorded_eye)
  datatype <- match.arg(datatype)
  timestamp_units <- match.arg(timestamp_units)
  coordinate_units <- match.arg(coordinate_units)
  sample_coordinate_system <- match.arg(sample_coordinate_system)

  .gp_bids_logical_scalar(include_pupil, "include_pupil")
  .gp_bids_logical_scalar(dry_run, "dry_run")
  .gp_bids_logical_scalar(overwrite, "overwrite")

  .gp_bids_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  .gp_bids_finite_scalar(start_time_s, "start_time_s")

  if (!is.null(sampling_rate_hz)) {
    .gp_bids_positive_scalar(
      sampling_rate_hz,
      "sampling_rate_hz"
    )
  }

  bids_root <- .gp_bids_nonempty_string(
    bids_root,
    "bids_root"
  )

  subject <- .gp_bids_label(subject, "subject")
  task <- .gp_bids_label(task, "task")
  recording <- .gp_bids_label(recording, "recording")

  if (!is.null(session)) {
    session <- .gp_bids_label(session, "session")
  }

  if (!is.null(acquisition)) {
    acquisition <- .gp_bids_label(
      acquisition,
      "acquisition"
    )
  }

  run <- .gp_bids_run_index(run)

  bids_version <- .gp_bids_nonempty_string(
    bids_version,
    "bids_version"
  )

  if (!identical(bids_version, "1.11.1")) {
    stop(
      "This exporter currently implements BIDS 1.11.1.",
      call. = FALSE
    )
  }

  if (!is.null(dataset_name)) {
    dataset_name <- .gp_bids_nonempty_string(
      dataset_name,
      "dataset_name"
    )
  }

  if (
    identical(sample_coordinate_system, "custom") &&
      is.null(custom_coordinate_system_description)
  ) {
    stop(
      "`custom_coordinate_system_description` is required when ",
      "`sample_coordinate_system = \"custom\"`.",
      call. = FALSE
    )
  }

  prepared <- .gp_bids_prepare_data(
    data = data,
    recorded_eye = recorded_eye,
    timestamp_col = timestamp_col,
    x_col = x_col,
    y_col = y_col,
    include_pupil = include_pupil,
    pupil_col = pupil_col,
    additional_cols = additional_cols,
    timestamp_units = timestamp_units,
    sampling_rate_hz = sampling_rate_hz,
    sampling_tolerance = sampling_tolerance
  )

  coordinate_unit_metadata <- switch(
    coordinate_units,
    normalized = "1",
    pixel = "pixel",
    degree = "deg",
    radian = "rad",
    mm = "mm",
    cm = "cm",
    m = "m",
    arbitrary = "arbitrary"
  )

  paths <- .gp_bids_paths(
    bids_root = bids_root,
    subject = subject,
    session = session,
    task = task,
    acquisition = acquisition,
    run = run,
    recording = recording,
    datatype = datatype
  )

  dataset_description <- .gp_bids_dataset_description(
    path = paths$dataset_description,
    dataset_name = dataset_name,
    bids_version = bids_version
  )

  stimulus_input <- list(
    ScreenDistance = screen_distance_m,
    ScreenOrigin = screen_origin,
    ScreenResolution = screen_resolution_px,
    ScreenSize = screen_size_m,
    ScreenRefreshRate = screen_refresh_rate_hz,
    SoftwareName = stimulus_software_name,
    SoftwareVersion = stimulus_software_version,
    OperatingSystem = operating_system
  )

  events_result <- .gp_bids_events_metadata(
    path = paths$events_json,
    sample_coordinate_system = sample_coordinate_system,
    stimulus_input = stimulus_input,
    vision_correction = vision_correction,
    overwrite = overwrite
  )

  sidecar <- .gp_bids_physio_sidecar(
    prepared = prepared,
    recorded_eye = recorded_eye,
    sample_coordinate_system = sample_coordinate_system,
    coordinate_units = coordinate_unit_metadata,
    pupil_units = pupil_units,
    start_time_s = start_time_s,
    manufacturer = manufacturer,
    manufacturers_model_name = manufacturers_model_name,
    software_versions = software_versions,
    device_serial_number = device_serial_number,
    eye_tracking_method = eye_tracking_method,
    calibration_type = calibration_type,
    calibration_count = calibration_count,
    average_calibration_error_deg =
      average_calibration_error_deg,
    maximal_calibration_error_deg =
      maximal_calibration_error_deg,
    eye_tracker_distance_m = eye_tracker_distance_m,
    raw_data_filters = raw_data_filters,
    timestamp_origin = timestamp_origin,
    custom_coordinate_system_description =
      custom_coordinate_system_description,
    column_metadata = column_metadata
  )

  recording_exists <- c(
    file.exists(paths$physio_tsv_gz),
    file.exists(paths$physio_json)
  )

  recording_conflict <-
    any(recording_exists) &&
    !isTRUE(overwrite)

  manifest <- data.frame(
    role = c(
      "dataset_description",
      if (events_result$include) "events_json",
      "physio_json",
      "physio_tsv_gz"
    ),
    path = c(
      paths$dataset_description,
      if (events_result$include) paths$events_json,
      paths$physio_json,
      paths$physio_tsv_gz
    ),
    exists = c(
      file.exists(paths$dataset_description),
      if (events_result$include) file.exists(paths$events_json),
      file.exists(paths$physio_json),
      file.exists(paths$physio_tsv_gz)
    ),
    action = c(
      dataset_description$action,
      if (events_result$include) events_result$action,
      if (file.exists(paths$physio_json)) {
        if (overwrite) "overwrite" else "conflict"
      } else {
        "write"
      },
      if (file.exists(paths$physio_tsv_gz)) {
        if (overwrite) "overwrite" else "conflict"
      } else {
        "write"
      }
    ),
    stringsAsFactors = FALSE
  )

  ready_to_write <- !recording_conflict

  audit <- list(
    n_samples = nrow(prepared$data),
    sampling_rate_hz = prepared$sampling_rate_hz,
    inferred_sampling_rate_hz =
      prepared$inferred_sampling_rate_hz,
    timestamp_units = prepared$timestamp_units,
    maximum_relative_interval_error =
      prepared$maximum_relative_interval_error,
    irregular_interval_count =
      prepared$irregular_interval_count,
    missing_x_coordinate =
      sum(!is.finite(prepared$source_x)),
    missing_y_coordinate =
      sum(!is.finite(prepared$source_y)),
    missing_pupil_size = if (
      "pupil_size" %in% names(prepared$data)
    ) {
      sum(!is.finite(prepared$source_pupil))
    } else {
      NA_integer_
    },
    recording_conflict = recording_conflict,
    ready_to_write = ready_to_write,
    external_bids_validation_required = TRUE
  )

  settings <- list(
    bids_version = bids_version,
    subject = subject,
    session = session,
    task = task,
    acquisition = acquisition,
    run = run,
    recording = recording,
    recorded_eye = recorded_eye,
    datatype = datatype,
    timestamp_col = prepared$timestamp_col,
    x_col = prepared$x_col,
    y_col = prepared$y_col,
    pupil_col = prepared$pupil_col,
    additional_cols = prepared$additional_cols,
    coordinate_units = coordinate_unit_metadata,
    sample_coordinate_system =
      sample_coordinate_system,
    dry_run = dry_run,
    overwrite = overwrite
  )

  result <- structure(
    list(
      data = prepared$data,
      row_audit = prepared$row_audit,
      physio_sidecar = sidecar,
      events_sidecar = events_result$metadata,
      dataset_description =
        dataset_description$metadata,
      files = manifest,
      audit = audit,
      settings = settings
    ),
    class = c(
      "gazepoint_bids_export",
      "list"
    )
  )

  if (isTRUE(dry_run)) {
    return(result)
  }

  if (recording_conflict) {
    conflicting <- manifest$path[
      manifest$action == "conflict"
    ]

    stop(
      "BIDS recording output already exists: ",
      conflicting[1L],
      ". Use `overwrite = TRUE` to replace the recording pair.",
      call. = FALSE
    )
  }

  dir.create(
    paths$data_directory,
    recursive = TRUE,
    showWarnings = FALSE
  )

  if (!dir.exists(paths$data_directory)) {
    stop(
      "Could not create the BIDS data directory.",
      call. = FALSE
    )
  }

  writes <- list()

  if (identical(dataset_description$action, "write")) {
    writes[[length(writes) + 1L]] <- list(
      target = paths$dataset_description,
      role = "dataset_description",
      type = "json",
      content = dataset_description$metadata,
      overwrite = FALSE
    )
  }

  if (
    events_result$include &&
      events_result$action %in% c("write", "overwrite")
  ) {
    writes[[length(writes) + 1L]] <- list(
      target = paths$events_json,
      role = "events_json",
      type = "json",
      content = events_result$metadata,
      overwrite = identical(
        events_result$action,
        "overwrite"
      )
    )
  }

  writes[[length(writes) + 1L]] <- list(
    target = paths$physio_json,
    role = "physio_json",
    type = "json",
    content = sidecar,
    overwrite = file.exists(paths$physio_json)
  )

  writes[[length(writes) + 1L]] <- list(
    target = paths$physio_tsv_gz,
    role = "physio_tsv_gz",
    type = "tsv_gz",
    content = prepared$data,
    overwrite = file.exists(paths$physio_tsv_gz)
  )

  .gp_bids_commit_writes(writes)

  result$files$exists <- file.exists(
    result$files$path
  )

  result$files$action[
    result$files$action == "write"
  ] <- "written"

  result$files$action[
    result$files$action == "overwrite"
  ] <- "overwritten"

  result$audit$ready_to_write <- TRUE
  result
}

#' @export
print.gazepoint_bids_export <- function(x, ...) {
  cat("Gazepoint BIDS eye-tracking export\n")
  cat("  Subject: sub-", x$settings$subject, "\n", sep = "")
  cat("  Task: task-", x$settings$task, "\n", sep = "")
  cat(
    "  Recording: recording-",
    x$settings$recording,
    " (",
    x$settings$recorded_eye,
    ")\n",
    sep = ""
  )
  cat(
    "  Samples: ",
    x$audit$n_samples,
    "\n",
    sep = ""
  )
  cat(
    "  Sampling rate: ",
    format(x$audit$sampling_rate_hz),
    " Hz\n",
    sep = ""
  )
  cat(
    "  Ready: ",
    if (isTRUE(x$audit$ready_to_write)) "yes" else "no",
    "\n",
    sep = ""
  )

  invisible(x)
}

.gp_bids_prepare_data <- function(
    data,
    recorded_eye,
    timestamp_col,
    x_col,
    y_col,
    include_pupil,
    pupil_col,
    additional_cols,
    timestamp_units,
    sampling_rate_hz,
    sampling_tolerance) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) < 2L) {
    stop(
      "`data` must contain at least two samples.",
      call. = FALSE
    )
  }

  timestamp_col <- .gp_bids_resolve_column(
    data,
    timestamp_col,
    c(
      "timestamp", "TIMESTAMP", "time_s", "TIME",
      "TIMETICK", "time", "Time", "recording_time_s"
    ),
    "timestamp"
  )

  coordinate_candidates <- switch(
    recorded_eye,
    left = list(
      x = c(
        "LPOGX", "LPOG_X", "left_x",
        "left_gaze_x", "x_coordinate"
      ),
      y = c(
        "LPOGY", "LPOG_Y", "left_y",
        "left_gaze_y", "y_coordinate"
      ),
      pupil = c(
        "LPD", "LPDIA", "left_pupil",
        "left_pupil_size", "pupil_size"
      )
    ),
    right = list(
      x = c(
        "RPOGX", "RPOG_X", "right_x",
        "right_gaze_x", "x_coordinate"
      ),
      y = c(
        "RPOGY", "RPOG_Y", "right_y",
        "right_gaze_y", "y_coordinate"
      ),
      pupil = c(
        "RPD", "RPDIA", "right_pupil",
        "right_pupil_size", "pupil_size"
      )
    ),
    cyclopean = list(
      x = c(
        "BPOGX", "FPOGX", "POGX",
        "gaze_x", "x_coordinate"
      ),
      y = c(
        "BPOGY", "FPOGY", "POGY",
        "gaze_y", "y_coordinate"
      ),
      pupil = c(
        "PUPIL", "pupil", "pupil_size",
        "BPD", "APD"
      )
    )
  )

  x_col <- .gp_bids_resolve_column(
    data,
    x_col,
    coordinate_candidates$x,
    "x-coordinate"
  )

  y_col <- .gp_bids_resolve_column(
    data,
    y_col,
    coordinate_candidates$y,
    "y-coordinate"
  )

  if (identical(x_col, y_col)) {
    stop(
      "`x_col` and `y_col` must identify different columns.",
      call. = FALSE
    )
  }

  if (!is.numeric(data[[timestamp_col]])) {
    stop("Timestamp data must be numeric.", call. = FALSE)
  }

  if (!is.numeric(data[[x_col]])) {
    stop("X-coordinate data must be numeric.", call. = FALSE)
  }

  if (!is.numeric(data[[y_col]])) {
    stop("Y-coordinate data must be numeric.", call. = FALSE)
  }

  resolved_pupil <- NULL

  if (isTRUE(include_pupil)) {
    if (is.null(pupil_col)) {
      resolved_pupil <- .gp_bids_find_candidate(
        names(data),
        coordinate_candidates$pupil
      )
    } else {
      resolved_pupil <- .gp_bids_resolve_column(
        data,
        pupil_col,
        character(),
        "pupil-size"
      )
    }

    if (
      !is.null(resolved_pupil) &&
        !is.numeric(data[[resolved_pupil]])
    ) {
      stop(
        "Pupil-size data must be numeric.",
        call. = FALSE
      )
    }
  }

  if (is.null(additional_cols)) {
    additional_cols <- character()
  } else {
    additional_cols <- unique(
      as.character(additional_cols)
    )
  }

  if (
    anyNA(additional_cols) ||
      any(!nzchar(additional_cols))
  ) {
    stop(
      "`additional_cols` must contain non-empty column names.",
      call. = FALSE
    )
  }

  missing_additional <- setdiff(
    additional_cols,
    names(data)
  )

  if (length(missing_additional) > 0L) {
    stop(
      "Additional columns were not found: ",
      paste(missing_additional, collapse = ", "),
      call. = FALSE
    )
  }

  invalid_additional_names <- additional_cols[
    !grepl("^[A-Za-z0-9_]+$", additional_cols)
  ]

  if (length(invalid_additional_names) > 0L) {
    stop(
      "Additional BIDS column names must contain only letters, ",
      "numbers, and underscores: ",
      paste(invalid_additional_names, collapse = ", "),
      call. = FALSE
    )
  }

  reserved <- c(
    "timestamp",
    "x_coordinate",
    "y_coordinate",
    "pupil_size"
  )

  if (any(additional_cols %in% reserved)) {
    stop(
      "`additional_cols` cannot use prescribed BIDS column names.",
      call. = FALSE
    )
  }

  selected_sources <- c(
    timestamp_col,
    x_col,
    y_col,
    resolved_pupil
  )

  if (any(additional_cols %in% selected_sources)) {
    stop(
      "`additional_cols` must not repeat a prescribed source column.",
      call. = FALSE
    )
  }

  for (column in additional_cols) {
    if (
      !is.numeric(data[[column]]) &&
        !is.logical(data[[column]])
    ) {
      stop(
        "Additional column `",
        column,
        "` must be numeric or logical.",
        call. = FALSE
      )
    }
  }

  timestamp_raw <- as.numeric(data[[timestamp_col]])

  if (any(!is.finite(timestamp_raw))) {
    stop(
      "Timestamp values must all be finite.",
      call. = FALSE
    )
  }

  resolved_timestamp_units <-
    .gp_bids_resolve_timestamp_units(
      timestamp_raw,
      timestamp_col,
      timestamp_units
    )

  timestamp_scale <- switch(
    resolved_timestamp_units,
    seconds = 1,
    milliseconds = 1 / 1000,
    microseconds = 1 / 1000000
  )

  time_s <- timestamp_raw * timestamp_scale

  if (any(diff(time_s) <= 0)) {
    stop(
      "Timestamps must be strictly increasing.",
      call. = FALSE
    )
  }

  intervals <- diff(time_s)

  inferred_sampling_rate_hz <-
    1 / stats::median(intervals)

  resolved_sampling_rate_hz <- if (
    is.null(sampling_rate_hz)
  ) {
    inferred_sampling_rate_hz
  } else {
    sampling_rate_hz
  }

  .gp_bids_positive_scalar(
    resolved_sampling_rate_hz,
    "resolved sampling rate"
  )

  expected_interval <- 1 / resolved_sampling_rate_hz

  relative_interval_error <- abs(
    intervals - expected_interval
  ) / expected_interval

  irregular <- relative_interval_error >
    sampling_tolerance

  if (any(irregular)) {
    stop(
      "The timestamp sequence is not regularly sampled within ",
      "`sampling_tolerance`. Review missing rows, time units, or the ",
      "supplied sampling rate.",
      call. = FALSE
    )
  }

  source_x <- as.numeric(data[[x_col]])
  source_y <- as.numeric(data[[y_col]])

  if (!any(is.finite(source_x))) {
    stop(
      "The selected x-coordinate column contains no finite values.",
      call. = FALSE
    )
  }

  if (!any(is.finite(source_y))) {
    stop(
      "The selected y-coordinate column contains no finite values.",
      call. = FALSE
    )
  }

  output <- data.frame(
    timestamp = timestamp_raw,
    x_coordinate = .gp_bids_nonfinite_to_na(source_x),
    y_coordinate = .gp_bids_nonfinite_to_na(source_y),
    stringsAsFactors = FALSE
  )

  source_pupil <- numeric()

  if (!is.null(resolved_pupil)) {
    source_pupil <- as.numeric(data[[resolved_pupil]])

    output$pupil_size <-
      .gp_bids_nonfinite_to_na(source_pupil)
  }

  for (column in additional_cols) {
    values <- data[[column]]

    if (is.logical(values)) {
      values <- as.integer(values)
    }

    output[[column]] <-
      .gp_bids_nonfinite_to_na(
        as.numeric(values)
      )
  }

  row_audit <- data.frame(
    source_row = seq_len(nrow(data)),
    timestamp = timestamp_raw,
    timestamp_s = time_s,
    finite_x_coordinate = is.finite(source_x),
    finite_y_coordinate = is.finite(source_y),
    stringsAsFactors = FALSE
  )

  if (!is.null(resolved_pupil)) {
    row_audit$finite_pupil_size <-
      is.finite(source_pupil)
  }

  list(
    data = output,
    row_audit = row_audit,
    timestamp_col = timestamp_col,
    x_col = x_col,
    y_col = y_col,
    pupil_col = resolved_pupil,
    additional_cols = additional_cols,
    source_x = source_x,
    source_y = source_y,
    source_pupil = source_pupil,
    timestamp_units = resolved_timestamp_units,
    timestamp_unit_metadata = switch(
      resolved_timestamp_units,
      seconds = "s",
      milliseconds = "ms",
      microseconds = "us"
    ),
    sampling_rate_hz = resolved_sampling_rate_hz,
    inferred_sampling_rate_hz =
      inferred_sampling_rate_hz,
    maximum_relative_interval_error =
      max(relative_interval_error),
    irregular_interval_count = sum(irregular)
  )
}

.gp_bids_physio_sidecar <- function(
    prepared,
    recorded_eye,
    sample_coordinate_system,
    coordinate_units,
    pupil_units,
    start_time_s,
    manufacturer,
    manufacturers_model_name,
    software_versions,
    device_serial_number,
    eye_tracking_method,
    calibration_type,
    calibration_count,
    average_calibration_error_deg,
    maximal_calibration_error_deg,
    eye_tracker_distance_m,
    raw_data_filters,
    timestamp_origin,
    custom_coordinate_system_description,
    column_metadata) {
  if (!is.list(column_metadata)) {
    stop(
      "`column_metadata` must be a named list.",
      call. = FALSE
    )
  }

  if (
    length(column_metadata) > 0L &&
      (
        is.null(names(column_metadata)) ||
          any(!nzchar(names(column_metadata)))
      )
  ) {
    stop(
      "`column_metadata` must be named by exported column.",
      call. = FALSE
    )
  }

  sidecar <- list(
    SamplingFrequency = prepared$sampling_rate_hz,
    StartTime = start_time_s,
    Columns = names(prepared$data),
    PhysioType = "eyetrack",
    RecordedEye = recorded_eye,
    SampleCoordinateSystem =
      sample_coordinate_system
  )

  optional_fields <- list(
    Manufacturer = manufacturer,
    ManufacturersModelName =
      manufacturers_model_name,
    SoftwareVersions = software_versions,
    DeviceSerialNumber = device_serial_number,
    EyeTrackingMethod = eye_tracking_method,
    CalibrationType = calibration_type,
    CalibrationCount = calibration_count,
    AverageCalibrationError =
      average_calibration_error_deg,
    MaximalCalibrationError =
      maximal_calibration_error_deg,
    EyeTrackerDistance =
      eye_tracker_distance_m,
    RawDataFilters = raw_data_filters
  )

  for (field in names(optional_fields)) {
    value <- optional_fields[[field]]

    if (!is.null(value)) {
      sidecar[[field]] <- value
    }
  }

  if (!is.null(calibration_count)) {
    .gp_bids_nonnegative_integer(
      calibration_count,
      "calibration_count"
    )
  }

  for (
    item in c(
      "average_calibration_error_deg",
      "maximal_calibration_error_deg"
    )
  ) {
    value <- get(item)

    if (!is.null(value)) {
      .gp_bids_nonnegative_scalar(value, item)
    }
  }

  if (!is.null(eye_tracker_distance_m)) {
    if (
      !is.numeric(eye_tracker_distance_m) ||
        !length(eye_tracker_distance_m) %in% c(1L, 3L) ||
        any(!is.finite(eye_tracker_distance_m))
    ) {
      stop(
        "`eye_tracker_distance_m` must contain one or three finite numbers.",
        call. = FALSE
      )
    }
  }

  timestamp_metadata <- list(
    LongName = "Eye-tracker timestamp",
    Description = paste0(
      "Continuously increasing timestamp issued by the eye tracker; ",
      "source column: ",
      prepared$timestamp_col,
      "."
    ),
    Units = prepared$timestamp_unit_metadata,
    Origin = timestamp_origin
  )

  x_metadata <- list(
    LongName = "Gaze position (x)",
    Description = paste0(
      "Horizontal gaze coordinate; source column: ",
      prepared$x_col,
      "."
    ),
    Units = coordinate_units
  )

  y_metadata <- list(
    LongName = "Gaze position (y)",
    Description = paste0(
      "Vertical gaze coordinate; source column: ",
      prepared$y_col,
      "."
    ),
    Units = coordinate_units
  )

  timestamp_metadata <- .gp_bids_merge_column_metadata(
    timestamp_metadata,
    column_metadata$timestamp
  )

  x_metadata <- .gp_bids_merge_column_metadata(
    x_metadata,
    column_metadata$x_coordinate
  )

  y_metadata <- .gp_bids_merge_column_metadata(
    y_metadata,
    column_metadata$y_coordinate
  )

  timestamp_metadata$Units <-
    prepared$timestamp_unit_metadata

  x_metadata$Units <- coordinate_units
  y_metadata$Units <- coordinate_units

  sidecar$timestamp <- timestamp_metadata
  sidecar$x_coordinate <- x_metadata
  sidecar$y_coordinate <- y_metadata

  if ("pupil_size" %in% names(prepared$data)) {
    pupil_units <- .gp_bids_nonempty_string(
      pupil_units,
      "pupil_units"
    )

    pupil_metadata <- list(
      LongName = "Pupil size",
      Description = paste0(
        "Pupil size recorded by the eye tracker; source column: ",
        prepared$pupil_col,
        "."
      ),
      Units = pupil_units
    )

    pupil_metadata <- .gp_bids_merge_column_metadata(
      pupil_metadata,
      column_metadata$pupil_size
    )

    pupil_metadata$Units <- pupil_units
    sidecar$pupil_size <- pupil_metadata
  }

  for (column in prepared$additional_cols) {
    metadata <- list(
      Description = paste0(
        "Additional Gazepoint source column: ",
        column,
        "."
      )
    )

    metadata <- .gp_bids_merge_column_metadata(
      metadata,
      column_metadata[[column]]
    )

    sidecar[[column]] <- metadata
  }

  if (
    identical(sample_coordinate_system, "custom")
  ) {
    sidecar$SampleCoordinateSystemDescription <-
      .gp_bids_nonempty_string(
        custom_coordinate_system_description,
        "custom_coordinate_system_description"
      )
  }

  sidecar
}

.gp_bids_dataset_description <- function(
    path,
    dataset_name,
    bids_version) {
  if (file.exists(path)) {
    metadata <- .gp_bids_read_json(path)

    if (
      is.null(metadata$Name) ||
        is.null(metadata$BIDSVersion)
    ) {
      stop(
        "Existing `dataset_description.json` does not contain ",
        "the required Name and BIDSVersion fields.",
        call. = FALSE
      )
    }

    existing_version <- as.character(
      metadata$BIDSVersion
    )

    if (!identical(existing_version, bids_version)) {
      stop(
        "Existing dataset BIDSVersion is `",
        existing_version,
        "`, but this exporter targets `",
        bids_version,
        "`.",
        call. = FALSE
      )
    }

    if (
      !is.null(dataset_name) &&
        !identical(
          as.character(metadata$Name),
          dataset_name
        )
    ) {
      stop(
        "`dataset_name` conflicts with the existing dataset description.",
        call. = FALSE
      )
    }

    return(list(
      metadata = metadata,
      action = "reuse"
    ))
  }

  if (is.null(dataset_name)) {
    stop(
      "`dataset_name` is required when creating a new BIDS dataset.",
      call. = FALSE
    )
  }

  package_version <- tryCatch(
    as.character(
      utils::packageVersion("gpbiometrics")
    ),
    error = function(e) "development"
  )

  list(
    metadata = list(
      Name = dataset_name,
      BIDSVersion = bids_version,
      DatasetType = "raw",
      GeneratedBy = list(
        list(
          Name = "gpbiometrics",
          Version = package_version,
          Description = paste0(
            "Gazepoint eye-tracking conversion using ",
            "export_gazepoint_to_bids()."
          )
        )
      )
    ),
    action = "write"
  )
}

.gp_bids_events_metadata <- function(
    path,
    sample_coordinate_system,
    stimulus_input,
    vision_correction,
    overwrite) {
  existing <- if (file.exists(path)) {
    .gp_bids_read_json(path)
  } else {
    list()
  }

  supplied <- stimulus_input[
    !vapply(
      stimulus_input,
      is.null,
      logical(1)
    )
  ]

  if (!is.null(supplied$ScreenDistance)) {
    .gp_bids_positive_scalar(
      supplied$ScreenDistance,
      "screen_distance_m"
    )
  }

  if (!is.null(supplied$ScreenOrigin)) {
    .gp_bids_screen_origin(
      supplied$ScreenOrigin
    )
  }

  if (!is.null(supplied$ScreenResolution)) {
    .gp_bids_positive_integer_pair(
      supplied$ScreenResolution,
      "screen_resolution_px"
    )
  }

  if (!is.null(supplied$ScreenSize)) {
    .gp_bids_positive_pair(
      supplied$ScreenSize,
      "screen_size_m"
    )
  }

  if (!is.null(supplied$ScreenRefreshRate)) {
    .gp_bids_positive_scalar(
      supplied$ScreenRefreshRate,
      "screen_refresh_rate_hz"
    )
  }

  existing_stimulus <- existing$StimulusPresentation

  if (is.null(existing_stimulus)) {
    existing_stimulus <- list()
  }

  if (
    file.exists(path) &&
      !isTRUE(overwrite) &&
      length(supplied) > 0L
  ) {
    for (field in names(supplied)) {
      existing_value <- existing_stimulus[[field]]

      if (
        is.null(existing_value) ||
          !isTRUE(all.equal(
            unlist(existing_value),
            unlist(supplied[[field]]),
            check.attributes = FALSE
          ))
      ) {
        stop(
          "Supplied stimulus metadata conflicts with or is absent from ",
          "the existing events JSON field `",
          field,
          "`. Use `overwrite = TRUE` to merge it.",
          call. = FALSE
        )
      }
    }
  }

  final <- existing

  if (
    !file.exists(path) ||
      isTRUE(overwrite)
  ) {
    final_stimulus <- existing_stimulus

    for (field in names(supplied)) {
      final_stimulus[[field]] <- supplied[[field]]
    }

    if (length(final_stimulus) > 0L) {
      final$StimulusPresentation <-
        final_stimulus
    }

    if (!is.null(vision_correction)) {
      final$VisionCorrection <-
        vision_correction
    }
  }

  if (
    file.exists(path) &&
      !isTRUE(overwrite)
  ) {
    final <- existing
  }

  if (
    identical(
      sample_coordinate_system,
      "gaze-on-screen"
    )
  ) {
    stimulus <- final$StimulusPresentation

    required <- c(
      "ScreenDistance",
      "ScreenOrigin",
      "ScreenResolution",
      "ScreenSize"
    )

    missing <- required[
      vapply(
        required,
        function(field) {
          is.null(stimulus[[field]])
        },
        logical(1)
      )
    ]

    if (length(missing) > 0L) {
      stop(
        "`gaze-on-screen` BIDS export requires events metadata fields: ",
        paste(missing, collapse = ", "),
        ".",
        call. = FALSE
      )
    }

    .gp_bids_positive_scalar(
      stimulus$ScreenDistance,
      "StimulusPresentation.ScreenDistance"
    )

    .gp_bids_screen_origin(
      unlist(stimulus$ScreenOrigin)
    )

    .gp_bids_positive_integer_pair(
      unlist(stimulus$ScreenResolution),
      "StimulusPresentation.ScreenResolution"
    )

    .gp_bids_positive_pair(
      unlist(stimulus$ScreenSize),
      "StimulusPresentation.ScreenSize"
    )
  }

  include <- identical(
    sample_coordinate_system,
    "gaze-on-screen"
  ) ||
    length(supplied) > 0L ||
    !is.null(vision_correction) ||
    file.exists(path)

  action <- if (!include) {
    "omit"
  } else if (!file.exists(path)) {
    "write"
  } else if (isTRUE(overwrite)) {
    "overwrite"
  } else {
    "reuse"
  }

  list(
    metadata = final,
    include = include,
    action = action
  )
}

.gp_bids_paths <- function(
    bids_root,
    subject,
    session,
    task,
    acquisition,
    run,
    recording,
    datatype) {
  root <- normalizePath(
    bids_root,
    winslash = "/",
    mustWork = FALSE
  )

  subject_dir <- file.path(
    root,
    paste0("sub-", subject)
  )

  base_dir <- subject_dir

  if (!is.null(session)) {
    base_dir <- file.path(
      subject_dir,
      paste0("ses-", session)
    )
  }

  data_directory <- file.path(
    base_dir,
    datatype
  )

  entity_parts <- c(
    paste0("sub-", subject),
    if (!is.null(session)) {
      paste0("ses-", session)
    },
    paste0("task-", task),
    if (!is.null(acquisition)) {
      paste0("acq-", acquisition)
    },
    if (!is.null(run)) {
      paste0("run-", run)
    }
  )

  events_stem <- paste(
    entity_parts,
    collapse = "_"
  )

  physio_stem <- paste(
    c(
      entity_parts,
      paste0("recording-", recording)
    ),
    collapse = "_"
  )

  list(
    root = root,
    data_directory = data_directory,
    dataset_description = file.path(
      root,
      "dataset_description.json"
    ),
    events_json = file.path(
      data_directory,
      paste0(events_stem, "_events.json")
    ),
    physio_json = file.path(
      data_directory,
      paste0(physio_stem, "_physio.json")
    ),
    physio_tsv_gz = file.path(
      data_directory,
      paste0(physio_stem, "_physio.tsv.gz")
    )
  )
}

.gp_bids_commit_writes <- function(writes) {
  targets <- vapply(
    writes,
    `[[`,
    character(1),
    "target"
  )

  duplicate_targets <- duplicated(targets)

  if (any(duplicate_targets)) {
    stop(
      "Internal error: duplicate BIDS output paths.",
      call. = FALSE
    )
  }

  for (target in targets) {
    dir.create(
      dirname(target),
      recursive = TRUE,
      showWarnings = FALSE
    )
  }

  temp_paths <- character(length(writes))

  for (i in seq_along(writes)) {
    temp_paths[i] <- tempfile(
      pattern = ".gpbiometrics-bids-",
      tmpdir = dirname(writes[[i]]$target)
    )
  }

  on.exit(
    unlink(
      temp_paths[file.exists(temp_paths)],
      force = TRUE
    ),
    add = TRUE
  )

  for (i in seq_along(writes)) {
    item <- writes[[i]]

    if (identical(item$type, "json")) {
      jsonlite::write_json(
        item$content,
        path = temp_paths[i],
        auto_unbox = TRUE,
        pretty = TRUE,
        null = "null",
        digits = NA
      )
    } else {
      .gp_bids_write_tsv_gz(
        item$content,
        temp_paths[i]
      )
    }
  }

  for (i in seq_along(writes)) {
    item <- writes[[i]]

    if (file.exists(item$target)) {
      if (!isTRUE(item$overwrite)) {
        stop(
          "Output file unexpectedly exists: ",
          item$target,
          call. = FALSE
        )
      }

      if (!unlink(item$target, force = TRUE)) {
        stop(
          "Could not remove existing output file: ",
          item$target,
          call. = FALSE
        )
      }
    }

    moved <- file.rename(
      temp_paths[i],
      item$target
    )

    if (!isTRUE(moved)) {
      stop(
        "Could not move prepared output into place: ",
        item$target,
        call. = FALSE
      )
    }
  }

  invisible(targets)
}

.gp_bids_write_tsv_gz <- function(data, path) {
  connection <- gzfile(
    path,
    open = "wt",
    encoding = "UTF-8"
  )

  on.exit(
    close(connection),
    add = TRUE
  )

  old_options <- options(
    digits = 17,
    scipen = 999
  )

  on.exit(
    options(old_options),
    add = TRUE
  )

  utils::write.table(
    data,
    file = connection,
    sep = "\t",
    row.names = FALSE,
    col.names = FALSE,
    quote = FALSE,
    na = "n/a",
    eol = "\n"
  )

  invisible(path)
}

.gp_bids_resolve_column <- function(
    data,
    supplied,
    candidates,
    description) {
  if (!is.null(supplied)) {
    supplied <- .gp_bids_nonempty_string(
      supplied,
      paste0(description, "_col")
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

  detected <- .gp_bids_find_candidate(
    names(data),
    candidates
  )

  if (is.null(detected)) {
    stop(
      "Could not identify a ",
      description,
      " column. Supply it explicitly.",
      call. = FALSE
    )
  }

  detected
}

.gp_bids_find_candidate <- function(
    names_vector,
    candidates) {
  lower_names <- tolower(names_vector)

  for (candidate in candidates) {
    hit <- which(
      lower_names == tolower(candidate)
    )

    if (length(hit) > 0L) {
      return(names_vector[hit[1L]])
    }
  }

  NULL
}

.gp_bids_resolve_timestamp_units <- function(
    values,
    column_name,
    timestamp_units) {
  if (!identical(timestamp_units, "auto")) {
    return(timestamp_units)
  }

  lower <- tolower(column_name)

  if (
    grepl(
      "micro|usec|_us$|^us_",
      lower
    )
  ) {
    return("microseconds")
  }

  if (
    grepl(
      "timetick|msec|millisecond|_ms$|^ms_",
      lower
    )
  ) {
    return("milliseconds")
  }

  if (
    identical(lower, "time") ||
      grepl(
        "second|time_s|_sec$|^sec_|timestamp_s",
        lower
      )
  ) {
    return("seconds")
  }

  intervals <- diff(values)
  intervals <- intervals[
    is.finite(intervals) &
      intervals > 0
  ]

  if (length(intervals) == 0L) {
    stop(
      "Could not infer timestamp units.",
      call. = FALSE
    )
  }

  median_interval <- stats::median(intervals)

  if (median_interval < 1) {
    return("seconds")
  }

  if (median_interval >= 5) {
    return("milliseconds")
  }

  stop(
    "Timestamp units are ambiguous. Supply `timestamp_units` explicitly.",
    call. = FALSE
  )
}

.gp_bids_read_json <- function(path) {
  tryCatch(
    jsonlite::read_json(
      path,
      simplifyVector = FALSE
    ),
    error = function(e) {
      stop(
        "Could not read JSON file `",
        path,
        "`: ",
        conditionMessage(e),
        call. = FALSE
      )
    }
  )
}

.gp_bids_merge_column_metadata <- function(
    default,
    override) {
  if (is.null(override)) {
    return(default)
  }

  if (!is.list(override)) {
    stop(
      "Each `column_metadata` entry must be a list.",
      call. = FALSE
    )
  }

  utils::modifyList(
    default,
    override,
    keep.null = TRUE
  )
}

.gp_bids_nonfinite_to_na <- function(x) {
  x[!is.finite(x)] <- NA_real_
  x
}

.gp_bids_label <- function(x, argument) {
  x <- .gp_bids_nonempty_string(
    x,
    argument
  )

  if (!grepl("^[A-Za-z0-9]+$", x)) {
    stop(
      "`",
      argument,
      "` must be a BIDS label containing only letters and numbers.",
      call. = FALSE
    )
  }

  x
}

.gp_bids_run_index <- function(x) {
  if (is.null(x)) {
    return(NULL)
  }

  if (
    is.numeric(x) &&
      length(x) == 1L &&
      is.finite(x) &&
      x >= 0 &&
      x == as.integer(x)
  ) {
    return(as.character(as.integer(x)))
  }

  x <- as.character(x)

  if (
    length(x) != 1L ||
      is.na(x) ||
      !grepl("^[0-9]+$", x)
  ) {
    stop(
      "`run` must be a non-negative integer or digit string.",
      call. = FALSE
    )
  }

  x
}

.gp_bids_screen_origin <- function(x) {
  x <- as.character(x)

  if (
    length(x) != 2L ||
      anyNA(x) ||
      any(!nzchar(x))
  ) {
    stop(
      "`screen_origin` must contain two non-empty strings.",
      call. = FALSE
    )
  }

  vertical <- c("top", "center", "bottom")
  horizontal <- c("left", "center", "right")

  if (
    !x[1L] %in% vertical ||
      !x[2L] %in% horizontal
  ) {
    stop(
      "`screen_origin` should use vertical then horizontal keywords, ",
      "for example `c(\"top\", \"left\")`.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_bids_positive_pair <- function(x, argument) {
  if (
    !is.numeric(x) ||
      length(x) != 2L ||
      any(!is.finite(x)) ||
      any(x <= 0)
  ) {
    stop(
      "`",
      argument,
      "` must contain two positive finite numbers.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_bids_positive_integer_pair <- function(
    x,
    argument) {
  if (
    !is.numeric(x) ||
      length(x) != 2L ||
      any(!is.finite(x)) ||
      any(x <= 0) ||
      any(x != as.integer(x))
  ) {
    stop(
      "`",
      argument,
      "` must contain two positive integers.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_bids_positive_scalar <- function(x, argument) {
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

.gp_bids_nonnegative_scalar <- function(
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

.gp_bids_finite_scalar <- function(x, argument) {
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

.gp_bids_nonnegative_integer <- function(
    x,
    argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x < 0 ||
      x != as.integer(x)
  ) {
    stop(
      "`",
      argument,
      "` must be one non-negative integer.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_bids_logical_scalar <- function(x, argument) {
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

.gp_bids_nonempty_string <- function(x, argument) {
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
