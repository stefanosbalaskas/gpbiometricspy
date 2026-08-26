#' Prepare Gazepoint data for eyetrackingR
#'
#' Converts sample-level Gazepoint gaze and AOI data into a conservative,
#' audited table compatible with `eyetrackingR::make_eyetrackingr_data()`.
#'
#' @param data Sample-level Gazepoint data frame.
#' @param participant_col Participant identifier column. If `NULL`, common
#'   participant names are searched.
#' @param trial_col Trial identifier column. If `NULL`, common trial and
#'   stimulus names are searched.
#' @param time_col Numeric time or sample-counter column. If `NULL`, common
#'   Gazepoint time columns are searched.
#' @param time_unit Source time unit: `"auto"`, `"seconds"`,
#'   `"milliseconds"`, or `"samples"`. Output time is always milliseconds.
#' @param sampling_rate_hz Sampling rate required when `time_unit = "samples"`
#'   or when an automatically detected sample counter is used.
#' @param rezero_time Logical. Subtract the minimum time separately within each
#'   participant-trial group.
#' @param trackloss_col Optional column where `TRUE` or non-zero means tracking
#'   was lost.
#' @param validity_col Optional gaze-validity column where `TRUE`, `"valid"`,
#'   or a positive numeric value means valid tracking.
#' @param valid_values Optional explicit values treated as valid in
#'   `validity_col`.
#' @param x_col,y_col Optional gaze-coordinate columns. Missing or non-finite
#'   coordinates are treated as track loss.
#' @param aoi_col Optional categorical AOI column.
#' @param aoi_cols Optional existing binary or logical AOI columns. Supply
#'   either `aoi_col` or `aoi_cols`, not both.
#' @param aoi_levels Optional ordered AOI labels to create from `aoi_col`.
#' @param outside_aoi_values Values in `aoi_col` treated as valid looks outside
#'   all supplied AOIs rather than track loss.
#' @param allow_aoi_overlap Logical. Permit more than one AOI column to be
#'   `TRUE` in a sample.
#' @param item_cols Optional item identifier columns retained in the output and
#'   passed to `eyetrackingR::make_eyetrackingr_data()`.
#' @param predictor_cols Optional condition or predictor columns retained in
#'   the compatibility table.
#' @param treat_non_aoi_looks_as_missing Logical passed unchanged to
#'   `eyetrackingR::make_eyetrackingr_data()` when `create_object = TRUE`.
#' @param sampling_tolerance Maximum relative deviation from the median
#'   within-trial sampling interval.
#' @param irregular Handling of irregular within-trial sampling:
#'   `"error"` or `"allow"`.
#' @param create_object Logical. If `TRUE`, construct an actual
#'   `eyetrackingR_data` object. The optional eyetrackingR package must then be
#'   installed.
#'
#' @return An object of class `"gazepoint_eyetrackingr_input"` containing:
#'
#' - `data`: plain compatibility data frame;
#' - `object`: optional output from `make_eyetrackingr_data()`;
#' - `row_audit`: row-level derivation and ordering audit;
#' - `sampling`: participant-trial sampling audit;
#' - `manifest`: column mappings and preparation summary;
#' - `settings`: resolved preparation settings.
#'
#' @details
#' The returned compatibility table uses the standardized columns
#' `ParticipantName`, `Trial`, `Time_ms`, and `TrackLoss`. `Time_ms` is expressed in
#' milliseconds. AOI columns are logical.
#'
#' Track loss is derived conservatively from the union of an explicit
#' track-loss flag, an invalid validity flag, and missing or non-finite gaze
#' coordinates. A valid look outside every AOI is not silently reclassified as
#' hardware track loss.
#'
#' eyetrackingR is intended for relatively raw sample-level data in which rows
#' represent equally spaced time samples. Fixation-level or event-level tables
#' should not be supplied to this helper.
#'
#' @examples
#' gaze <- data.frame(
#'   participant = rep("P01", 4),
#'   trial = rep("T01", 4),
#'   time_s = c(0, 0.1, 0.2, 0.3),
#'   gaze_x = c(0.2, 0.5, 0.8, NA),
#'   gaze_y = c(0.5, 0.5, 0.5, NA),
#'   AOI = c("left", "center", "right", NA)
#' )
#'
#' prepared <- prepare_gazepoint_eyetrackingr_input(gaze)
#' prepared$data
#' prepared$sampling
#'
#' @seealso [assign_gazepoint_aoi()]
#'
#' @export
prepare_gazepoint_eyetrackingr_input <- function(
    data,
    participant_col = NULL,
    trial_col = NULL,
    time_col = NULL,
    time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    sampling_rate_hz = NULL,
    rezero_time = FALSE,
    trackloss_col = NULL,
    validity_col = NULL,
    valid_values = NULL,
    x_col = NULL,
    y_col = NULL,
    aoi_col = NULL,
    aoi_cols = NULL,
    aoi_levels = NULL,
    outside_aoi_values = c(
      "",
      "none",
      "no_aoi",
      "outside",
      "outside_aoi",
      "non_aoi",
      "background"
    ),
    allow_aoi_overlap = FALSE,
    item_cols = NULL,
    predictor_cols = NULL,
    treat_non_aoi_looks_as_missing = TRUE,
    sampling_tolerance = 0.05,
    irregular = c("error", "allow"),
    create_object = FALSE) {
  time_unit <- match.arg(time_unit)
  irregular <- match.arg(irregular)

  .gp_etr_logical_scalar(
    rezero_time,
    "rezero_time"
  )

  .gp_etr_logical_scalar(
    allow_aoi_overlap,
    "allow_aoi_overlap"
  )

  .gp_etr_logical_scalar(
    treat_non_aoi_looks_as_missing,
    "treat_non_aoi_looks_as_missing"
  )

  .gp_etr_logical_scalar(
    create_object,
    "create_object"
  )

  .gp_etr_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  if (!is.null(sampling_rate_hz)) {
    .gp_etr_positive_scalar(
      sampling_rate_hz,
      "sampling_rate_hz"
    )
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a sample-level data frame.",
      call. = FALSE
    )
  }

  if (nrow(data) == 0L) {
    stop(
      "`data` must contain at least one sample.",
      call. = FALSE
    )
  }

  participant_col <- .gp_etr_resolve_column(
    data = data,
    supplied = participant_col,
    candidates = c(
      "ParticipantName",
      "participant",
      "participant_id",
      "subject",
      "subject_id",
      "SUBJECT",
      "P"
    ),
    description = "participant",
    required = TRUE
  )

  trial_col <- .gp_etr_resolve_column(
    data = data,
    supplied = trial_col,
    candidates = c(
      "Trial",
      "trial",
      "trial_id",
      "TRIAL",
      "MEDIA_ID",
      "media_id",
      "stimulus",
      "stimulus_id",
      "screen"
    ),
    description = "trial",
    required = TRUE
  )

  time_col <- .gp_etr_resolve_column(
    data = data,
    supplied = time_col,
    candidates = c(
      "TimeFromTrialOnset",
      "time_ms",
      "MSTIMER",
      "TIME",
      "time_s",
      "timestamp_s",
      "timestamp",
      "TIME_TICK",
      "TIMETICK",
      "CNT"
    ),
    description = "time",
    required = TRUE
  )

  if (!is.numeric(data[[time_col]])) {
    stop(
      "`time_col` must identify a numeric column.",
      call. = FALSE
    )
  }

  participant <- as.character(
    data[[participant_col]]
  )

  trial <- as.character(
    data[[trial_col]]
  )

  if (
    anyNA(participant) ||
      any(!nzchar(trimws(participant)))
  ) {
    stop(
      "Participant identifiers must be non-missing and non-empty.",
      call. = FALSE
    )
  }

  if (
    anyNA(trial) ||
      any(!nzchar(trimws(trial)))
  ) {
    stop(
      "Trial identifiers must be non-missing and non-empty.",
      call. = FALSE
    )
  }

  source_time <- suppressWarnings(
    as.numeric(data[[time_col]])
  )

  if (any(!is.finite(source_time))) {
    stop(
      "`time_col` must contain only finite numeric values.",
      call. = FALSE
    )
  }

  resolved_time_unit <- .gp_etr_resolve_time_unit(
    time = source_time,
    time_col = time_col,
    requested = time_unit
  )

  if (
    identical(resolved_time_unit, "samples") &&
      is.null(sampling_rate_hz)
  ) {
    stop(
      "`sampling_rate_hz` is required when time is represented by samples.",
      call. = FALSE
    )
  }

  time_ms <- switch(
    resolved_time_unit,
    seconds = source_time * 1000,
    milliseconds = source_time,
    samples = source_time / sampling_rate_hz * 1000
  )

  group_key <- paste(
    participant,
    trial,
    sep = "\r"
  )

  groups <- split(
    seq_len(nrow(data)),
    factor(
      group_key,
      levels = unique(group_key)
    ),
    drop = TRUE
  )

  if (isTRUE(rezero_time)) {
    for (idx in groups) {
      time_ms[idx] <- time_ms[idx] -
        min(time_ms[idx])
    }
  }

  trackloss_col <- .gp_etr_resolve_column(
    data = data,
    supplied = trackloss_col,
    candidates = c(
      "TrackLoss",
      "trackloss",
      "track_loss",
      "tracking_loss"
    ),
    description = "track-loss",
    required = FALSE
  )

  validity_col <- .gp_etr_resolve_column(
    data = data,
    supplied = validity_col,
    candidates = c(
      "BPOGV",
      "FPOGV",
      "GPOGV",
      "LPOGV",
      "RPOGV",
      "gaze_valid",
      "gaze_validity",
      "validity",
      "valid"
    ),
    description = "validity",
    required = FALSE
  )

  coordinate_result <- .gp_etr_resolve_coordinates(
    data = data,
    x_col = x_col,
    y_col = y_col
  )

  x_col <- coordinate_result$x_col
  y_col <- coordinate_result$y_col

  explicit_trackloss <- rep(
    FALSE,
    nrow(data)
  )

  missing_trackloss_value <- rep(
    FALSE,
    nrow(data)
  )

  if (!is.null(trackloss_col)) {
    converted <- .gp_etr_trackloss_value(
      data[[trackloss_col]]
    )

    explicit_trackloss <- converted$value
    missing_trackloss_value <- converted$missing
  }

  invalid_validity <- rep(
    FALSE,
    nrow(data)
  )

  missing_validity_value <- rep(
    FALSE,
    nrow(data)
  )

  if (!is.null(validity_col)) {
    converted <- .gp_etr_validity_value(
      data[[validity_col]],
      valid_values = valid_values
    )

    invalid_validity <- !converted$value
    missing_validity_value <- converted$missing
  }

  missing_coordinates <- rep(
    FALSE,
    nrow(data)
  )

  if (
    !is.null(x_col) &&
      !is.null(y_col)
  ) {
    x <- suppressWarnings(
      as.numeric(data[[x_col]])
    )

    y <- suppressWarnings(
      as.numeric(data[[y_col]])
    )

    missing_coordinates <-
      !is.finite(x) |
      !is.finite(y)
  }

  if (
    is.null(trackloss_col) &&
      is.null(validity_col) &&
      (
        is.null(x_col) ||
          is.null(y_col)
      )
  ) {
    stop(
      "Track loss could not be derived. Supply `trackloss_col`, ",
      "`validity_col`, or both `x_col` and `y_col`.",
      call. = FALSE
    )
  }

  trackloss <-
    explicit_trackloss |
    invalid_validity |
    missing_coordinates

  aoi_result <- .gp_etr_prepare_aois(
    data = data,
    trackloss = trackloss,
    aoi_col = aoi_col,
    aoi_cols = aoi_cols,
    aoi_levels = aoi_levels,
    outside_aoi_values = outside_aoi_values,
    allow_aoi_overlap = allow_aoi_overlap
  )

  aoi_data <- aoi_result$data
  output_aoi_cols <- names(aoi_data)

  no_aoi_look <-
    rowSums(aoi_data) == 0L &
    !trackloss

  item_cols <- .gp_etr_optional_columns(
    data,
    item_cols,
    "item_cols"
  )

  predictor_cols <- .gp_etr_optional_columns(
    data,
    predictor_cols,
    "predictor_cols"
  )

  retained_cols <- unique(
    c(item_cols, predictor_cols)
  )

  reserved <- c(
    "ParticipantName",
    "Trial",
    "Time_ms",
    "TrackLoss",
    output_aoi_cols
  )

  collisions <- intersect(
    retained_cols,
    reserved
  )

  if (length(collisions) > 0L) {
    stop(
      "Retained item or predictor columns conflict with prepared columns: ",
      paste(collisions, collapse = ", "),
      call. = FALSE
    )
  }

  prepared <- data.frame(
    ParticipantName = participant,
    Trial = trial,
    Time_ms = time_ms,
    TrackLoss = trackloss,
    stringsAsFactors = FALSE
  )

  prepared <- cbind(
    prepared,
    aoi_data
  )

  if (length(retained_cols) > 0L) {
    prepared <- cbind(
      prepared,
      data[retained_cols]
    )
  }

  duplicate_key <- paste(
    prepared$ParticipantName,
    prepared$Trial,
    format(
      prepared$Time_ms,
      digits = 17,
      scientific = FALSE,
      trim = TRUE
    ),
    sep = "\r"
  )

  if (anyDuplicated(duplicate_key)) {
    first_duplicate <- which(
      duplicated(duplicate_key) |
        duplicated(
          duplicate_key,
          fromLast = TRUE
        )
    )[1L]

    stop(
      "Participant-trial-time rows must be unique. ",
      "The first duplicate involves source row ",
      first_duplicate,
      ".",
      call. = FALSE
    )
  }

  order_index <- order(
    prepared$ParticipantName,
    prepared$Trial,
    prepared$Time_ms,
    seq_len(nrow(prepared))
  )

  source_order_changed <- !identical(
    order_index,
    seq_len(nrow(prepared))
  )

  prepared <- prepared[
    order_index,
    ,
    drop = FALSE
  ]

  rownames(prepared) <- NULL

  sampling <- .gp_etr_sampling_audit(
    prepared,
    sampling_tolerance =
      sampling_tolerance
  )

  irregular_groups <- sampling$group_id[
    sampling$irregular_interval_count > 0L
  ]

  if (
    length(irregular_groups) > 0L &&
      identical(irregular, "error")
  ) {
    stop(
      "Irregular within-trial sampling was detected in group `",
      irregular_groups[1L],
      "`. Use `irregular = \"allow\"` only after reviewing ",
      "the sampling audit.",
      call. = FALSE
    )
  }

  prepared_row <- integer(
    nrow(data)
  )

  prepared_row[order_index] <-
    seq_len(nrow(data))

  row_audit <- data.frame(
    source_row = seq_len(nrow(data)),
    prepared_row = prepared_row,
    participant = participant,
    trial = trial,
    source_time = source_time,
    prepared_time_ms = time_ms,
    explicit_trackloss =
      explicit_trackloss,
    invalid_validity =
      invalid_validity,
    missing_coordinates =
      missing_coordinates,
    missing_trackloss_value =
      missing_trackloss_value,
    missing_validity_value =
      missing_validity_value,
    trackloss = trackloss,
    aoi_membership_count =
      rowSums(aoi_data),
    non_aoi_look = no_aoi_look,
    stringsAsFactors = FALSE
  )

  column_manifest <- data.frame(
    role = c(
      "participant",
      "trial",
      "time",
      "trackloss",
      if (!is.null(validity_col)) {
        "validity"
      },
      if (!is.null(x_col)) {
        "gaze_x"
      },
      if (!is.null(y_col)) {
        "gaze_y"
      },
      rep(
        "aoi",
        nrow(aoi_result$mapping)
      ),
      rep(
        "item",
        length(item_cols)
      ),
      rep(
        "predictor",
        length(predictor_cols)
      )
    ),
    source_column = c(
      participant_col,
      trial_col,
      time_col,
      if (is.null(trackloss_col)) {
        NA_character_
      } else {
        trackloss_col
      },
      if (!is.null(validity_col)) {
        validity_col
      },
      if (!is.null(x_col)) {
        x_col
      },
      if (!is.null(y_col)) {
        y_col
      },
      aoi_result$mapping$source_value,
      item_cols,
      predictor_cols
    ),
    output_column = c(
      "ParticipantName",
      "Trial",
      "Time_ms",
      "TrackLoss",
      if (!is.null(validity_col)) {
        "TrackLoss"
      },
      if (!is.null(x_col)) {
        "TrackLoss"
      },
      if (!is.null(y_col)) {
        "TrackLoss"
      },
      aoi_result$mapping$output_column,
      item_cols,
      predictor_cols
    ),
    transformation = c(
      "character identifier",
      "character identifier",
      paste0(
        resolved_time_unit,
        " to milliseconds",
        if (rezero_time) {
          "; rezeroed within participant-trial"
        } else {
          ""
        }
      ),
      if (is.null(trackloss_col)) {
        "derived from available validity and coordinate information"
      } else {
        "non-zero or TRUE interpreted as track loss"
      },
      if (!is.null(validity_col)) {
        "invalid values contribute to TrackLoss"
      },
      if (!is.null(x_col)) {
        "non-finite values contribute to TrackLoss"
      },
      if (!is.null(y_col)) {
        "non-finite values contribute to TrackLoss"
      },
      aoi_result$mapping$transformation,
      rep("retained unchanged", length(item_cols)),
      rep(
        "retained unchanged",
        length(predictor_cols)
      )
    ),
    stringsAsFactors = FALSE
  )

  summary_manifest <- data.frame(
    n_rows = nrow(prepared),
    n_participants = length(
      unique(prepared$ParticipantName)
    ),
    n_trials = length(
      unique(paste(
        prepared$ParticipantName,
        prepared$Trial,
        sep = "\r"
      ))
    ),
    n_aoi_columns =
      length(output_aoi_cols),
    trackloss_rows =
      sum(prepared$TrackLoss),
    trackloss_proportion =
      mean(prepared$TrackLoss),
    non_aoi_look_rows =
      sum(no_aoi_look),
    irregular_group_count =
      sum(
        sampling$irregular_interval_count > 0L
      ),
    source_order_changed =
      source_order_changed,
    object_created = create_object,
    stringsAsFactors = FALSE
  )

  eyetrackingr_object <- NULL

  if (isTRUE(create_object)) {
    if (
      !requireNamespace(
        "eyetrackingR",
        quietly = TRUE
      )
    ) {
      stop(
        "Package `eyetrackingR` is required when ",
        "`create_object = TRUE`.",
        call. = FALSE
      )
    }

    eyetrackingr_object <-
      eyetrackingR::make_eyetrackingr_data(
        data = prepared,
        participant_column =
          "ParticipantName",
        trackloss_column = "TrackLoss",
        time_column = "Time_ms",
        trial_column = "Trial",
        aoi_columns = output_aoi_cols,
        treat_non_aoi_looks_as_missing =
          treat_non_aoi_looks_as_missing,
        item_columns = if (
          length(item_cols) == 0L
        ) {
          NULL
        } else {
          item_cols
        }
      )
  }

  settings <- list(
    participant_col = participant_col,
    trial_col = trial_col,
    time_col = time_col,
    source_time_unit =
      resolved_time_unit,
    output_time_unit = "milliseconds",
    sampling_rate_hz =
      sampling_rate_hz,
    rezero_time = rezero_time,
    trackloss_col = trackloss_col,
    validity_col = validity_col,
    valid_values = valid_values,
    x_col = x_col,
    y_col = y_col,
    aoi_col = aoi_result$aoi_col,
    aoi_cols = output_aoi_cols,
    aoi_mapping = aoi_result$mapping,
    item_cols = item_cols,
    predictor_cols = predictor_cols,
    treat_non_aoi_looks_as_missing =
      treat_non_aoi_looks_as_missing,
    sampling_tolerance =
      sampling_tolerance,
    irregular = irregular,
    create_object = create_object,
    interpretation_notes = c(
      "The compatibility table contains sample-level data, not fixation summaries.",
      "Track loss is derived independently from whether a valid gaze sample falls inside a named AOI.",
      "Looks outside all AOIs remain distinct from hardware or coordinate track loss.",
      "The helper prepares input and does not run time-window, growth-curve, cluster, or inferential analyses."
    )
  )

  structure(
    list(
      data = prepared,
      object = eyetrackingr_object,
      row_audit = row_audit,
      sampling = sampling,
      manifest = list(
        columns = column_manifest,
        summary = summary_manifest
      ),
      settings = settings
    ),
    class = c(
      "gazepoint_eyetrackingr_input",
      "list"
    )
  )
}

#' @export
print.gazepoint_eyetrackingr_input <- function(
    x,
    ...) {
  cat("Gazepoint eyetrackingR input\n")
  cat(
    "  Rows: ",
    nrow(x$data),
    "\n",
    sep = ""
  )
  cat(
    "  Participants: ",
    length(unique(x$data$ParticipantName)),
    "\n",
    sep = ""
  )
  cat(
    "  Participant-trials: ",
    nrow(x$sampling),
    "\n",
    sep = ""
  )
  cat(
    "  AOIs: ",
    paste(
      x$settings$aoi_cols,
      collapse = ", "
    ),
    "\n",
    sep = ""
  )
  cat(
    "  Track loss: ",
    format(
      mean(x$data$TrackLoss),
      digits = 3
    ),
    "\n",
    sep = ""
  )
  cat(
    "  eyetrackingR object created: ",
    if (is.null(x$object)) "no" else "yes",
    "\n",
    sep = ""
  )

  invisible(x)
}

.gp_etr_prepare_aois <- function(
    data,
    trackloss,
    aoi_col,
    aoi_cols,
    aoi_levels,
    outside_aoi_values,
    allow_aoi_overlap) {
  if (
    !is.null(aoi_col) &&
      !is.null(aoi_cols)
  ) {
    stop(
      "Supply either `aoi_col` or `aoi_cols`, not both.",
      call. = FALSE
    )
  }

  if (is.null(aoi_cols)) {
    aoi_col <- .gp_etr_resolve_column(
      data = data,
      supplied = aoi_col,
      candidates = c(
        "AOI",
        "aoi",
        "aoi_name",
        "AOI_NAME",
        "area_of_interest"
      ),
      description = "AOI",
      required = FALSE
    )
  }

  if (
    is.null(aoi_col) &&
      is.null(aoi_cols)
  ) {
    stop(
      "No AOI representation was found. Supply `aoi_col` ",
      "or `aoi_cols`.",
      call. = FALSE
    )
  }

  if (!is.null(aoi_col)) {
    raw <- as.character(
      data[[aoi_col]]
    )

    normalized <- tolower(
      trimws(raw)
    )

    outside <- is.na(raw) |
      normalized %in% tolower(
        trimws(
          as.character(
            outside_aoi_values
          )
        )
      )

    if (is.null(aoi_levels)) {
      levels <- unique(
        raw[!outside]
      )
    } else {
      levels <- as.character(
        aoi_levels
      )

      if (
        anyNA(levels) ||
          any(!nzchar(trimws(levels))) ||
          anyDuplicated(levels)
      ) {
        stop(
          "`aoi_levels` must contain unique, non-empty labels.",
          call. = FALSE
        )
      }

      unexpected <- unique(
        raw[
          !outside &
            !raw %in% levels
        ]
      )

      if (length(unexpected) > 0L) {
        stop(
          "AOI values were not included in `aoi_levels`: ",
          paste(unexpected, collapse = ", "),
          call. = FALSE
        )
      }
    }

    if (length(levels) == 0L) {
      stop(
        "No named AOI levels remained after excluding outside-AOI values.",
        call. = FALSE
      )
    }

    output_names <- .gp_etr_aoi_names(
      levels
    )

    aoi_data <- as.data.frame(
      stats::setNames(
        lapply(
          levels,
          function(level) {
            !is.na(raw) &
              raw == level
          }
        ),
        output_names
      ),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )

    mapping <- data.frame(
      source_value = levels,
      output_column = output_names,
      transformation =
        "categorical AOI converted to logical indicator",
      stringsAsFactors = FALSE
    )
  } else {
    aoi_cols <- .gp_etr_optional_columns(
      data,
      aoi_cols,
      "aoi_cols"
    )

    if (length(aoi_cols) == 0L) {
      stop(
        "`aoi_cols` must contain at least one column.",
        call. = FALSE
      )
    }

    aoi_data <- as.data.frame(
      stats::setNames(
        lapply(
          aoi_cols,
          function(column) {
            .gp_etr_binary_value(
              data[[column]],
              column
            )
          }
        ),
        aoi_cols
      ),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )

    mapping <- data.frame(
      source_value = aoi_cols,
      output_column = aoi_cols,
      transformation =
        "binary AOI column converted to logical",
      stringsAsFactors = FALSE
    )

    aoi_col <- NULL
  }

  overlap <- rowSums(aoi_data) > 1L

  if (
    any(overlap) &&
      !isTRUE(allow_aoi_overlap)
  ) {
    stop(
      "More than one AOI is active in at least one sample. ",
      "Set `allow_aoi_overlap = TRUE` only when overlapping AOIs ",
      "are intentional.",
      call. = FALSE
    )
  }

  if (any(trackloss)) {
    for (column in names(aoi_data)) {
      aoi_data[[column]][trackloss] <-
        FALSE
    }
  }

  list(
    data = aoi_data,
    mapping = mapping,
    aoi_col = aoi_col
  )
}

.gp_etr_sampling_audit <- function(
    data,
    sampling_tolerance) {
  key <- paste(
    data$ParticipantName,
    data$Trial,
    sep = "\r"
  )

  groups <- split(
    seq_len(nrow(data)),
    factor(
      key,
      levels = unique(key)
    ),
    drop = TRUE
  )

  rows <- vector(
    "list",
    length(groups)
  )

  group_names <- names(groups)

  for (i in seq_along(groups)) {
    idx <- groups[[i]]
    time <- data$Time_ms[idx]
    delta <- diff(time)

    repeated <- sum(delta == 0)
    negative <- sum(delta < 0)
    positive <- delta[
      is.finite(delta) &
        delta > 0
    ]

    median_interval <- if (
      length(positive) > 0L
    ) {
      stats::median(positive)
    } else {
      NA_real_
    }

    relative_error <- if (
      is.finite(median_interval) &&
        median_interval > 0
    ) {
      abs(
        positive - median_interval
      ) / median_interval
    } else {
      numeric()
    }

    irregular_count <- if (
      length(relative_error) > 0L
    ) {
      sum(
        relative_error >
          sampling_tolerance
      )
    } else {
      0L
    }

    rows[[i]] <- data.frame(
      ParticipantName =
        data$ParticipantName[idx[1L]],
      Trial =
        data$Trial[idx[1L]],
      group_id = group_names[i],
      sample_count = length(idx),
      start_time_ms = min(time),
      end_time_ms = max(time),
      median_interval_ms =
        median_interval,
      effective_sampling_rate_hz = if (
        is.finite(median_interval) &&
          median_interval > 0
      ) {
        1000 / median_interval
      } else {
        NA_real_
      },
      repeated_timestamp_count =
        repeated,
      negative_time_step_count =
        negative,
      irregular_interval_count =
        irregular_count,
      maximum_relative_interval_error = if (
        length(relative_error) > 0L
      ) {
        max(relative_error)
      } else {
        0
      },
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(
    rbind,
    rows
  )

  rownames(out) <- NULL
  out
}

.gp_etr_resolve_coordinates <- function(
    data,
    x_col,
    y_col) {
  x_supplied <- !is.null(x_col)
  y_supplied <- !is.null(y_col)

  x_col <- .gp_etr_resolve_column(
    data = data,
    supplied = x_col,
    candidates = c(
      "gaze_x",
      "BPOGX",
      "FPOGX",
      "GPOGX",
      "LPOGX",
      "RPOGX",
      "x",
      "X",
      "CX"
    ),
    description = "gaze-x",
    required = FALSE
  )

  y_col <- .gp_etr_resolve_column(
    data = data,
    supplied = y_col,
    candidates = c(
      "gaze_y",
      "BPOGY",
      "FPOGY",
      "GPOGY",
      "LPOGY",
      "RPOGY",
      "y",
      "Y",
      "CY"
    ),
    description = "gaze-y",
    required = FALSE
  )

  if (xor(is.null(x_col), is.null(y_col))) {
    if (x_supplied || y_supplied) {
      stop(
        "Supply both `x_col` and `y_col` when selecting coordinates explicitly.",
        call. = FALSE
      )
    }

    x_col <- NULL
    y_col <- NULL
  }

  if (!is.null(x_col)) {
    if (!is.numeric(data[[x_col]])) {
      stop(
        "`x_col` must identify a numeric column.",
        call. = FALSE
      )
    }

    if (!is.numeric(data[[y_col]])) {
      stop(
        "`y_col` must identify a numeric column.",
        call. = FALSE
      )
    }
  }

  list(
    x_col = x_col,
    y_col = y_col
  )
}

.gp_etr_trackloss_value <- function(x) {
  missing <- is.na(x)

  if (is.logical(x)) {
    value <- x
  } else if (is.numeric(x)) {
    value <- is.finite(x) & x != 0
  } else {
    normalized <- tolower(
      trimws(as.character(x))
    )

    true_values <- c(
      "true",
      "t",
      "yes",
      "y",
      "1",
      "lost",
      "loss",
      "trackloss",
      "invalid"
    )

    false_values <- c(
      "false",
      "f",
      "no",
      "n",
      "0",
      "valid",
      "tracked"
    )

    unknown <- !missing &
      !normalized %in%
      c(true_values, false_values)

    if (any(unknown)) {
      stop(
        "Unsupported values were found in `trackloss_col`: ",
        paste(
          unique(
            as.character(x[unknown])
          ),
          collapse = ", "
        ),
        call. = FALSE
      )
    }

    value <- normalized %in% true_values
  }

  value[is.na(value)] <- TRUE

  list(
    value = as.logical(value),
    missing = missing
  )
}

.gp_etr_validity_value <- function(
    x,
    valid_values = NULL) {
  missing <- is.na(x)

  if (!is.null(valid_values)) {
    value <- as.character(x) %in%
      as.character(valid_values)
  } else if (is.logical(x)) {
    value <- x
  } else if (is.numeric(x)) {
    value <- is.finite(x) & x > 0
  } else {
    normalized <- tolower(
      trimws(as.character(x))
    )

    valid_text <- c(
      "true",
      "t",
      "yes",
      "y",
      "1",
      "valid",
      "tracked"
    )

    invalid_text <- c(
      "false",
      "f",
      "no",
      "n",
      "0",
      "invalid",
      "lost",
      "loss"
    )

    unknown <- !missing &
      !normalized %in%
      c(valid_text, invalid_text)

    if (any(unknown)) {
      stop(
        "Unsupported values were found in `validity_col`. ",
        "Supply `valid_values` explicitly.",
        call. = FALSE
      )
    }

    value <- normalized %in% valid_text
  }

  value[is.na(value)] <- FALSE

  list(
    value = as.logical(value),
    missing = missing
  )
}

.gp_etr_binary_value <- function(x, column) {
  missing <- is.na(x)

  if (is.logical(x)) {
    value <- x
  } else if (is.numeric(x)) {
    finite <- x[is.finite(x)]

    if (
      length(finite) > 0L &&
        any(!finite %in% c(0, 1))
    ) {
      stop(
        "AOI column `",
        column,
        "` must contain only 0, 1, TRUE, FALSE, or missing values.",
        call. = FALSE
      )
    }

    value <- x == 1
  } else {
    normalized <- tolower(
      trimws(as.character(x))
    )

    true_values <- c(
      "true",
      "t",
      "yes",
      "y",
      "1",
      "inside",
      "in"
    )

    false_values <- c(
      "false",
      "f",
      "no",
      "n",
      "0",
      "outside",
      "out"
    )

    unknown <- !missing &
      !normalized %in%
      c(true_values, false_values)

    if (any(unknown)) {
      stop(
        "Unsupported values were found in AOI column `",
        column,
        "`.",
        call. = FALSE
      )
    }

    value <- normalized %in% true_values
  }

  value[is.na(value)] <- FALSE
  as.logical(value)
}

.gp_etr_resolve_time_unit <- function(
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
      "time_s|timestamp_s|second|_sec$|^sec_",
      lower
    )
  ) {
    return("seconds")
  }

  delta <- diff(time)
  delta <- delta[
    is.finite(delta) &
      delta > 0
  ]

  if (length(delta) == 0L) {
    stop(
      "Could not infer `time_unit`; supply it explicitly.",
      call. = FALSE
    )
  }

  median_delta <- stats::median(delta)

  if (median_delta < 1) {
    return("seconds")
  }

  if (median_delta >= 5) {
    return("milliseconds")
  }

  stop(
    "The time unit is ambiguous. Supply `time_unit` explicitly.",
    call. = FALSE
  )
}

.gp_etr_aoi_names <- function(levels) {
  output <- make.names(
    levels,
    unique = TRUE
  )

  reserved <- c(
    "ParticipantName",
    "Trial",
    "Time_ms",
    "TrackLoss"
  )

  output[output %in% reserved] <-
    paste0(
      "AOI_",
      output[output %in% reserved]
    )

  make.unique(output)
}

.gp_etr_optional_columns <- function(
    data,
    columns,
    argument) {
  if (is.null(columns)) {
    return(character())
  }

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
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  columns
}

.gp_etr_resolve_column <- function(
    data,
    supplied,
    candidates,
    description,
    required) {
  if (!is.null(supplied)) {
    supplied <- .gp_etr_nonempty_string(
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

  detected <- .gp_etr_find_candidate(
    names(data),
    candidates
  )

  if (is.null(detected) && isTRUE(required)) {
    stop(
      "Could not identify a ",
      description,
      " column. Supply it explicitly.",
      call. = FALSE
    )
  }

  detected
}

.gp_etr_find_candidate <- function(
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

.gp_etr_positive_scalar <- function(
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

.gp_etr_nonnegative_scalar <- function(
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

.gp_etr_logical_scalar <- function(
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

.gp_etr_nonempty_string <- function(
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
