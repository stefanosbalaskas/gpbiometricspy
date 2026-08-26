#' Prepare Gazepoint data for gazeR
#'
#' Converts long-form sample-level Gazepoint gaze and pupil data into a
#' conservative, audited table compatible with `gazer::make_gazer()`.
#'
#' @param data Sample-level Gazepoint data frame.
#' @param participant_col Participant identifier column. If `NULL`, common
#'   participant names are searched.
#' @param trial_col Trial identifier column. If `NULL`, common trial, media,
#'   and stimulus names are searched.
#' @param time_col Numeric time or sample-counter column. If `NULL`, common
#'   Gazepoint time columns are searched.
#' @param time_unit Source time unit: `"auto"`, `"seconds"`,
#'   `"milliseconds"`, or `"samples"`. Output time is expressed in
#'   milliseconds.
#' @param sampling_rate_hz Sampling rate required when time is represented by
#'   sample indices.
#' @param rezero_time Logical. Subtract the minimum time separately within
#'   each participant-trial group.
#' @param x_col,y_col Optional monocular or already-combined gaze-coordinate
#'   columns.
#' @param x_left_col,y_left_col Optional left-eye gaze-coordinate columns.
#' @param x_right_col,y_right_col Optional right-eye gaze-coordinate columns.
#' @param pupil_col Optional monocular, cyclopean, or previously combined
#'   pupil column.
#' @param pupil_left_col,pupil_right_col Optional left- and right-eye pupil
#'   columns.
#' @param validity_col Optional shared gaze/pupil validity column.
#' @param validity_left_col,validity_right_col Optional per-eye validity
#'   columns.
#' @param valid_values Optional explicit values treated as valid. Without this
#'   argument, positive numeric values, `TRUE`, and common textual valid labels
#'   are treated as valid.
#' @param blink_col Optional shared blink column.
#' @param blink_left_col,blink_right_col Optional per-eye blink columns.
#' @param invalid_coordinate_values Optional coordinate values to flag
#'   explicitly as invalid. Zero is not treated as invalid by default because
#'   it can be a valid screen-edge coordinate.
#' @param invalid_pupil_values Optional pupil values to flag explicitly as
#'   invalid, for example `c(-1, 0)`.
#' @param mask_invalid Logical. If `TRUE`, explicitly invalid values, failed
#'   validity samples, and blink samples are replaced by `NA` in the prepared
#'   gaze and pupil columns. Non-finite values are always represented as `NA`.
#' @param other_cols Optional item, condition, block, AOI, stimulus, or other
#'   metadata columns retained unchanged.
#' @param sampling_tolerance Maximum relative deviation from the median
#'   within-trial sampling interval.
#' @param irregular Handling of irregular within-trial sampling:
#'   `"error"` or `"allow"`.
#' @param create_object Logical. If `TRUE`, call `make_gazer()` from a locally
#'   installed gazeR package. gazeR is GitHub-hosted and is therefore not a
#'   declared gpbiometrics dependency.
#'
#' @return An object of class `"gazepoint_gazer_input"` containing:
#'
#' - `data`: plain gazeR-compatible long-form data;
#' - `object`: optional output from `make_gazer()`;
#' - `row_audit`: row-level availability and invalidity audit;
#' - `sampling`: participant-trial sampling audit;
#' - `manifest`: column mappings and preparation summary;
#' - `settings`: resolved preparation settings.
#'
#' @details
#' The standardized identifier columns are `subject`, `trial`, and `time`.
#' `time` is expressed in milliseconds.
#'
#' Monocular or combined input uses the canonical columns `x`, `y`, and
#' `pupil`. Binocular input uses `x_left`, `y_left`, `pupil_left`,
#' `x_right`, `y_right`, and `pupil_right` as available. gazeR retains
#' multiple selected eye columns when constructing its compatibility table.
#'
#' The helper does not assign AOIs, calculate track loss, detect or extend
#' blinks, interpolate data, smooth signals, downsample, upsample,
#' baseline-correct pupil size, or run inferential analyses.
#'
#' @examples
#' gaze <- data.frame(
#'   participant = rep("P01", 4),
#'   trial = rep("T01", 4),
#'   time_s = c(0, 0.1, 0.2, 0.3),
#'   gaze_x = c(0.2, 0.4, 0.6, NA),
#'   gaze_y = c(0.5, 0.5, 0.5, NA),
#'   pupil_left = c(3.1, 3.2, 3.3, NA),
#'   pupil_right = c(3.0, 3.1, 3.2, NA)
#' )
#'
#' prepared <- prepare_gazepoint_gazer_input(gaze)
#' prepared$data
#' prepared$sampling
#'
#' @seealso
#' [assign_gazepoint_aoi()],
#' [downsample_gazepoint_data()],
#' [detect_gazepoint_pupil_blinks()],
#' [clean_gazepoint_pupil_signal()]
#'
#' @export
prepare_gazepoint_gazer_input <- function(
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
    x_col = NULL,
    y_col = NULL,
    x_left_col = NULL,
    y_left_col = NULL,
    x_right_col = NULL,
    y_right_col = NULL,
    pupil_col = NULL,
    pupil_left_col = NULL,
    pupil_right_col = NULL,
    validity_col = NULL,
    validity_left_col = NULL,
    validity_right_col = NULL,
    valid_values = NULL,
    blink_col = NULL,
    blink_left_col = NULL,
    blink_right_col = NULL,
    invalid_coordinate_values = NULL,
    invalid_pupil_values = NULL,
    mask_invalid = FALSE,
    other_cols = NULL,
    sampling_tolerance = 0.05,
    irregular = c("error", "allow"),
    create_object = FALSE) {
  time_unit <- match.arg(time_unit)
  irregular <- match.arg(irregular)

  .gp_gzr_logical_scalar(
    rezero_time,
    "rezero_time"
  )

  .gp_gzr_logical_scalar(
    mask_invalid,
    "mask_invalid"
  )

  .gp_gzr_logical_scalar(
    create_object,
    "create_object"
  )

  .gp_gzr_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  if (!is.null(sampling_rate_hz)) {
    .gp_gzr_positive_scalar(
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

  participant_col <- .gp_gzr_resolve_column(
    data = data,
    supplied = participant_col,
    candidates = c(
      "subject",
      "Subject",
      "ParticipantName",
      "participant",
      "participant_id",
      "subject_id",
      "SUBJECT",
      "USER",
      "P"
    ),
    description = "participant",
    required = TRUE
  )

  trial_col <- .gp_gzr_resolve_column(
    data = data,
    supplied = trial_col,
    candidates = c(
      "trial",
      "Trial",
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

  time_col <- .gp_gzr_resolve_column(
    data = data,
    supplied = time_col,
    candidates = c(
      "time",
      "Time",
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

  subject <- as.character(
    data[[participant_col]]
  )

  trial <- as.character(
    data[[trial_col]]
  )

  .gp_gzr_check_identifier(
    subject,
    "Subject"
  )

  .gp_gzr_check_identifier(
    trial,
    "Trial"
  )

  source_time <- suppressWarnings(
    as.numeric(data[[time_col]])
  )

  if (any(!is.finite(source_time))) {
    stop(
      "`time_col` must contain only finite numeric values.",
      call. = FALSE
    )
  }

  resolved_time_unit <- .gp_gzr_resolve_time_unit(
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

  channels <- .gp_gzr_resolve_channels(
    data = data,
    x_col = x_col,
    y_col = y_col,
    x_left_col = x_left_col,
    y_left_col = y_left_col,
    x_right_col = x_right_col,
    y_right_col = y_right_col,
    pupil_col = pupil_col,
    pupil_left_col = pupil_left_col,
    pupil_right_col = pupil_right_col
  )

  active_roles <- unique(
    c(
      channels$gaze$role,
      channels$pupil$role
    )
  )

  validity <- .gp_gzr_resolve_role_flags(
    data = data,
    active_roles = active_roles,
    generic_col = validity_col,
    left_col = validity_left_col,
    right_col = validity_right_col,
    generic_candidates = c(
      "valid",
      "validity",
      "gaze_valid",
      "BPOGV",
      "FPOGV"
    ),
    left_candidates = c(
      "valid_left",
      "validity_left",
      "left_valid",
      "LPV",
      "LPOGV"
    ),
    right_candidates = c(
      "valid_right",
      "validity_right",
      "right_valid",
      "RPV",
      "RPOGV"
    ),
    description = "validity"
  )

  blink <- .gp_gzr_resolve_role_flags(
    data = data,
    active_roles = active_roles,
    generic_col = blink_col,
    left_col = blink_left_col,
    right_col = blink_right_col,
    generic_candidates = c(
      "blink",
      "BLINK",
      "is_blink"
    ),
    left_candidates = c(
      "blink_left",
      "left_blink",
      "BLINK_LEFT"
    ),
    right_candidates = c(
      "blink_right",
      "right_blink",
      "BLINK_RIGHT"
    ),
    description = "blink"
  )

  invalid_coordinate_values <-
    .gp_gzr_numeric_values(
      invalid_coordinate_values,
      "invalid_coordinate_values"
    )

  invalid_pupil_values <-
    .gp_gzr_numeric_values(
      invalid_pupil_values,
      "invalid_pupil_values"
    )

  role_validity <- list()
  role_blink <- list()
  role_validity_source <- list()
  role_blink_source <- list()

  for (role in active_roles) {
    validity_source <-
      validity[[role]]

    blink_source <-
      blink[[role]]

    role_validity[[role]] <- if (
      is.null(validity_source)
    ) {
      rep(TRUE, nrow(data))
    } else {
      .gp_gzr_validity_value(
        data[[validity_source]],
        valid_values = valid_values
      )
    }

    role_blink[[role]] <- if (
      is.null(blink_source)
    ) {
      rep(FALSE, nrow(data))
    } else {
      .gp_gzr_blink_value(
        data[[blink_source]]
      )
    }

    role_validity_source[[role]] <-
      validity_source

    role_blink_source[[role]] <-
      blink_source
  }

  channel_table <- rbind(
    channels$gaze[
      ,
      c(
        "measure",
        "role",
        "source_column",
        "output_column"
      ),
      drop = FALSE
    ],
    channels$pupil[
      ,
      c(
        "measure",
        "role",
        "source_column",
        "output_column"
      ),
      drop = FALSE
    ]
  )

  prepared_channels <- list()
  finite_flags <- list()
  explicit_invalid_flags <- list()
  role_invalid_flags <- list()

  for (i in seq_len(nrow(channel_table))) {
    source_column <-
      channel_table$source_column[i]

    output_column <-
      channel_table$output_column[i]

    measure <-
      channel_table$measure[i]

    role <-
      channel_table$role[i]

    if (!is.numeric(data[[source_column]])) {
      stop(
        "Channel `",
        source_column,
        "` must be numeric.",
        call. = FALSE
      )
    }

    raw <- suppressWarnings(
      as.numeric(data[[source_column]])
    )

    finite <- is.finite(raw)

    invalid_values <- if (
      identical(measure, "pupil")
    ) {
      invalid_pupil_values
    } else {
      invalid_coordinate_values
    }

    explicitly_invalid <- rep(
      FALSE,
      length(raw)
    )

    if (length(invalid_values) > 0L) {
      explicitly_invalid <-
        !is.na(raw) &
        raw %in% invalid_values
    }

    role_invalid <-
      !role_validity[[role]] |
      role_blink[[role]]

    prepared_value <- raw
    prepared_value[!finite] <- NA_real_

    if (isTRUE(mask_invalid)) {
      prepared_value[
        explicitly_invalid |
          role_invalid
      ] <- NA_real_
    }

    prepared_channels[[output_column]] <-
      prepared_value

    finite_flags[[output_column]] <-
      finite

    explicit_invalid_flags[[output_column]] <-
      explicitly_invalid

    role_invalid_flags[[output_column]] <-
      role_invalid
  }

  prepared_channels <- as.data.frame(
    prepared_channels,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  flag_output <- list()
  flag_manifest <- list()

  for (role in active_roles) {
    suffix <- .gp_gzr_role_suffix(role)

    validity_source <-
      role_validity_source[[role]]

    blink_source <-
      role_blink_source[[role]]

    if (!is.null(validity_source)) {
      output_name <- if (
        identical(role, "generic")
      ) {
        "valid"
      } else {
        paste0(
          "valid_",
          suffix
        )
      }

      flag_output[[output_name]] <-
        role_validity[[role]]

      flag_manifest[[length(flag_manifest) + 1L]] <-
        data.frame(
          role = paste0(
            "validity_",
            role
          ),
          source_column =
            validity_source,
          output_column =
            output_name,
          transformation =
            "converted to logical validity",
          stringsAsFactors = FALSE
        )
    }

    if (!is.null(blink_source)) {
      output_name <- if (
        identical(role, "generic")
      ) {
        "blink"
      } else {
        paste0(
          "blink_",
          suffix
        )
      }

      flag_output[[output_name]] <-
        role_blink[[role]]

      flag_manifest[[length(flag_manifest) + 1L]] <-
        data.frame(
          role = paste0(
            "blink_",
            role
          ),
          source_column =
            blink_source,
          output_column =
            output_name,
          transformation =
            "converted to logical blink flag",
          stringsAsFactors = FALSE
        )
    }
  }

  flag_output <- as.data.frame(
    flag_output,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  group_key <- paste(
    subject,
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
      time_ms[idx] <-
        time_ms[idx] -
        min(time_ms[idx])
    }
  }

  duplicate_key <- paste(
    subject,
    trial,
    format(
      time_ms,
      digits = 17,
      scientific = FALSE,
      trim = TRUE
    ),
    sep = "\r"
  )

  if (anyDuplicated(duplicate_key)) {
    duplicate_row <- which(
      duplicated(duplicate_key) |
        duplicated(
          duplicate_key,
          fromLast = TRUE
        )
    )[1L]

    stop(
      "Subject-trial-time rows must be unique. ",
      "The first duplicate involves source row ",
      duplicate_row,
      ".",
      call. = FALSE
    )
  }

  other_cols <- .gp_gzr_optional_columns(
    data,
    other_cols,
    "other_cols"
  )

  reserved <- c(
    "subject",
    "trial",
    "time",
    names(prepared_channels),
    names(flag_output)
  )

  collisions <- intersect(
    other_cols,
    reserved
  )

  if (length(collisions) > 0L) {
    stop(
      "`other_cols` conflict with prepared columns: ",
      paste(
        collisions,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  prepared <- data.frame(
    subject = subject,
    trial = trial,
    time = time_ms,
    stringsAsFactors = FALSE
  )

  prepared <- cbind(
    prepared,
    prepared_channels
  )

  if (ncol(flag_output) > 0L) {
    prepared <- cbind(
      prepared,
      flag_output
    )
  }

  if (length(other_cols) > 0L) {
    prepared <- cbind(
      prepared,
      data[other_cols]
    )
  }

  order_index <- order(
    prepared$subject,
    prepared$trial,
    prepared$time,
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

  sampling <- .gp_gzr_sampling_audit(
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

  gaze_roles <- channels$gaze$role[
    channels$gaze$measure == "x"
  ]

  finite_gaze_pair <- matrix(
    FALSE,
    nrow = nrow(data),
    ncol = length(gaze_roles)
  )

  usable_gaze_pair <- matrix(
    FALSE,
    nrow = nrow(data),
    ncol = length(gaze_roles)
  )

  if (length(gaze_roles) > 0L) {
    for (i in seq_along(gaze_roles)) {
      role <- gaze_roles[i]

      x_output <- channels$gaze$output_column[
        channels$gaze$role == role &
          channels$gaze$measure == "x"
      ]

      y_output <- channels$gaze$output_column[
        channels$gaze$role == role &
          channels$gaze$measure == "y"
      ]

      x_finite <- finite_flags[[x_output]]
      y_finite <- finite_flags[[y_output]]

      x_explicit <-
        explicit_invalid_flags[[x_output]]

      y_explicit <-
        explicit_invalid_flags[[y_output]]

      finite_gaze_pair[, i] <-
        x_finite &
        y_finite

      usable_gaze_pair[, i] <-
        x_finite &
        y_finite &
        !x_explicit &
        !y_explicit &
        role_validity[[role]] &
        !role_blink[[role]]
    }
  }

  pupil_outputs <-
    channels$pupil$output_column

  finite_pupil <- if (
    length(pupil_outputs) > 0L
  ) {
    do.call(
      cbind,
      finite_flags[pupil_outputs]
    )
  } else {
    matrix(
      logical(),
      nrow = nrow(data),
      ncol = 0L
    )
  }

  usable_pupil <- if (
    length(pupil_outputs) > 0L
  ) {
    result <- matrix(
      FALSE,
      nrow = nrow(data),
      ncol = length(pupil_outputs)
    )

    for (i in seq_along(pupil_outputs)) {
      output <- pupil_outputs[i]
      role <- channels$pupil$role[i]

      result[, i] <-
        finite_flags[[output]] &
        !explicit_invalid_flags[[output]] &
        role_validity[[role]] &
        !role_blink[[role]]
    }

    result
  } else {
    matrix(
      logical(),
      nrow = nrow(data),
      ncol = 0L
    )
  }

  all_explicit_invalid <- if (
    length(explicit_invalid_flags) > 0L
  ) {
    do.call(
      cbind,
      explicit_invalid_flags
    )
  } else {
    matrix(
      logical(),
      nrow = nrow(data),
      ncol = 0L
    )
  }

  validity_matrix <- if (
    length(active_roles) > 0L
  ) {
    do.call(
      cbind,
      role_validity[active_roles]
    )
  } else {
    matrix(
      logical(),
      nrow = nrow(data),
      ncol = 0L
    )
  }

  blink_matrix <- if (
    length(active_roles) > 0L
  ) {
    do.call(
      cbind,
      role_blink[active_roles]
    )
  } else {
    matrix(
      logical(),
      nrow = nrow(data),
      ncol = 0L
    )
  }

  row_audit <- data.frame(
    source_row =
      seq_len(nrow(data)),
    prepared_row =
      prepared_row,
    subject =
      subject,
    trial =
      trial,
    source_time =
      source_time,
    prepared_time_ms =
      time_ms,
    finite_gaze_pair_count = if (
      ncol(finite_gaze_pair) > 0L
    ) {
      rowSums(finite_gaze_pair)
    } else {
      0L
    },
    usable_gaze_pair_count = if (
      ncol(usable_gaze_pair) > 0L
    ) {
      rowSums(usable_gaze_pair)
    } else {
      0L
    },
    finite_pupil_count = if (
      ncol(finite_pupil) > 0L
    ) {
      rowSums(finite_pupil)
    } else {
      0L
    },
    usable_pupil_count = if (
      ncol(usable_pupil) > 0L
    ) {
      rowSums(usable_pupil)
    } else {
      0L
    },
    explicit_invalid_channel_count = if (
      ncol(all_explicit_invalid) > 0L
    ) {
      rowSums(all_explicit_invalid)
    } else {
      0L
    },
    invalid_validity_count = if (
      ncol(validity_matrix) > 0L
    ) {
      rowSums(!validity_matrix)
    } else {
      0L
    },
    blink_count = if (
      ncol(blink_matrix) > 0L
    ) {
      rowSums(blink_matrix)
    } else {
      0L
    },
    stringsAsFactors = FALSE
  )

  channel_manifest <- data.frame(
    role = c(
      "subject",
      "trial",
      "time",
      paste0(
        channel_table$measure,
        "_",
        channel_table$role
      )
    ),
    source_column = c(
      participant_col,
      trial_col,
      time_col,
      channel_table$source_column
    ),
    output_column = c(
      "subject",
      "trial",
      "time",
      channel_table$output_column
    ),
    transformation = c(
      "character identifier",
      "character identifier",
      paste0(
        resolved_time_unit,
        " to milliseconds",
        if (rezero_time) {
          "; rezeroed within subject-trial"
        } else {
          ""
        }
      ),
      rep(
        if (mask_invalid) {
          "numeric channel; invalid, blink, and failed-validity samples set to NA"
        } else {
          "numeric channel; non-finite values set to NA; flags retained without masking"
        },
        nrow(channel_table)
      )
    ),
    stringsAsFactors = FALSE
  )

  if (length(flag_manifest) > 0L) {
    channel_manifest <- rbind(
      channel_manifest,
      do.call(
        rbind,
        flag_manifest
      )
    )
  }

  if (length(other_cols) > 0L) {
    channel_manifest <- rbind(
      channel_manifest,
      data.frame(
        role = rep(
          "other",
          length(other_cols)
        ),
        source_column =
          other_cols,
        output_column =
          other_cols,
        transformation =
          rep(
            "retained unchanged",
            length(other_cols)
          ),
        stringsAsFactors = FALSE
      )
    )
  }

  x_output_cols <- channels$gaze$output_column[
    channels$gaze$measure == "x"
  ]

  y_output_cols <- channels$gaze$output_column[
    channels$gaze$measure == "y"
  ]

  pupil_output_cols <-
    channels$pupil$output_column

  gazer_object <- NULL
  gazer_info <- NULL

  if (isTRUE(create_object)) {
    object_result <- .gp_gzr_make_object(
      prepared = prepared,
      x_cols = x_output_cols,
      y_cols = y_output_cols,
      pupil_cols = pupil_output_cols
    )

    gazer_object <-
      object_result$object

    gazer_info <-
      object_result$package
  }

  summary_manifest <- data.frame(
    n_rows = nrow(prepared),
    n_subjects =
      length(unique(prepared$subject)),
    n_subject_trials =
      nrow(sampling),
    gaze_pair_count =
      length(x_output_cols),
    pupil_channel_count =
      length(pupil_output_cols),
    binocular_gaze =
      length(x_output_cols) > 1L,
    binocular_pupil =
      length(pupil_output_cols) > 1L,
    rows_with_no_finite_gaze_pair =
      if (length(x_output_cols) > 0L) {
        sum(
          row_audit$
            finite_gaze_pair_count == 0L
        )
      } else {
        NA_integer_
      },
    rows_with_no_finite_pupil =
      if (length(pupil_output_cols) > 0L) {
        sum(
          row_audit$
            finite_pupil_count == 0L
        )
      } else {
        NA_integer_
      },
    rows_with_any_invalid_channel =
      sum(
        row_audit$
          explicit_invalid_channel_count > 0L |
          row_audit$
            invalid_validity_count > 0L |
          row_audit$
            blink_count > 0L
      ),
    irregular_group_count =
      sum(
        sampling$
          irregular_interval_count > 0L
      ),
    source_order_changed =
      source_order_changed,
    invalid_samples_masked =
      mask_invalid,
    object_created =
      create_object,
    stringsAsFactors = FALSE
  )

  settings <- list(
    participant_col =
      participant_col,
    trial_col =
      trial_col,
    time_col =
      time_col,
    source_time_unit =
      resolved_time_unit,
    output_time_unit =
      "milliseconds",
    sampling_rate_hz =
      sampling_rate_hz,
    rezero_time =
      rezero_time,
    channels =
      channels,
    validity_sources =
      role_validity_source,
    valid_values =
      valid_values,
    blink_sources =
      role_blink_source,
    invalid_coordinate_values =
      invalid_coordinate_values,
    invalid_pupil_values =
      invalid_pupil_values,
    mask_invalid =
      mask_invalid,
    other_cols =
      other_cols,
    sampling_tolerance =
      sampling_tolerance,
    irregular =
      irregular,
    create_object =
      create_object,
    gazer_package =
      gazer_info,
    interpretation_notes = c(
      "The compatibility table contains long-form sample-level data.",
      "Time is expressed in milliseconds.",
      "Coordinate scale is preserved and is not inferred or transformed.",
      "AOI assignment, track-loss calculation, blink detection, interpolation, filtering, resampling, and baseline correction are not performed.",
      "Validity and blink flags mask selected channels only when mask_invalid is TRUE.",
      "gazer is accessed only at runtime when create_object is TRUE."
    )
  )

  structure(
    list(
      data = prepared,
      object = gazer_object,
      row_audit = row_audit,
      sampling = sampling,
      manifest = list(
        columns = channel_manifest,
        summary = summary_manifest
      ),
      settings = settings
    ),
    class = c(
      "gazepoint_gazer_input",
      "list"
    )
  )
}

#' @export
print.gazepoint_gazer_input <- function(
    x,
    ...) {
  cat("Gazepoint gazeR input\n")

  cat(
    "  Rows: ",
    nrow(x$data),
    "\n",
    sep = ""
  )

  cat(
    "  Subjects: ",
    length(unique(x$data$subject)),
    "\n",
    sep = ""
  )

  cat(
    "  Subject-trials: ",
    nrow(x$sampling),
    "\n",
    sep = ""
  )

  gaze_cols <- intersect(
    c(
      "x",
      "y",
      "x_left",
      "y_left",
      "x_right",
      "y_right"
    ),
    names(x$data)
  )

  pupil_cols <- intersect(
    c(
      "pupil",
      "pupil_left",
      "pupil_right"
    ),
    names(x$data)
  )

  cat(
    "  Gaze columns: ",
    if (length(gaze_cols) == 0L) {
      "none"
    } else {
      paste(
        gaze_cols,
        collapse = ", "
      )
    },
    "\n",
    sep = ""
  )

  cat(
    "  Pupil columns: ",
    if (length(pupil_cols) == 0L) {
      "none"
    } else {
      paste(
        pupil_cols,
        collapse = ", "
      )
    },
    "\n",
    sep = ""
  )

  cat(
    "  gazeR object created: ",
    if (is.null(x$object)) {
      "no"
    } else {
      "yes"
    },
    "\n",
    sep = ""
  )

  invisible(x)
}

.gp_gzr_make_object <- function(
    prepared,
    x_cols,
    y_cols,
    pupil_cols) {
  namespace <- tryCatch(
    getNamespace("gazer"),
    error = function(e) NULL
  )

  if (is.null(namespace)) {
    stop(
      "A locally installed gazeR package (`gazer`) is required when ",
      "`create_object = TRUE`. Install it from its official GitHub ",
      "repository before requesting object construction.",
      call. = FALSE
    )
  }

  constructor <- get(
    "make_gazer",
    envir = namespace,
    inherits = FALSE
  )

  object <- do.call(
    constructor,
    list(
      data = prepared,
      subject = "subject",
      trial = "trial",
      time = "time",
      x = if (
        length(x_cols) == 0L
      ) {
        NULL
      } else {
        x_cols
      },
      y = if (
        length(y_cols) == 0L
      ) {
        NULL
      } else {
        y_cols
      },
      pupil = if (
        length(pupil_cols) == 0L
      ) {
        NULL
      } else {
        pupil_cols
      }
    )
  )

  description <- suppressWarnings(
    tryCatch(
      utils::packageDescription(
        "gazer"
      ),
      error = function(e) NULL
    )
  )

  package_info <- if (
    is.null(description)
  ) {
    list(
      package = "gazer",
      version = NA_character_,
      github_sha1 = NA_character_
    )
  } else {
    list(
      package =
        description$Package,
      version =
        description$Version,
      github_sha1 =
        if (is.null(description$GithubSHA1)) {
          NA_character_
        } else {
          description$GithubSHA1
        }
    )
  }

  list(
    object = object,
    package = package_info
  )
}

.gp_gzr_resolve_channels <- function(
    data,
    x_col,
    y_col,
    x_left_col,
    y_left_col,
    x_right_col,
    y_right_col,
    pupil_col,
    pupil_left_col,
    pupil_right_col) {
  generic_gaze_supplied <-
    !is.null(x_col) ||
    !is.null(y_col)

  eye_gaze_supplied <-
    !is.null(x_left_col) ||
    !is.null(y_left_col) ||
    !is.null(x_right_col) ||
    !is.null(y_right_col)

  if (
    generic_gaze_supplied &&
      eye_gaze_supplied
  ) {
    stop(
      "Supply either `x_col`/`y_col` or per-eye gaze columns, not both.",
      call. = FALSE
    )
  }

  gaze_rows <- list()

  if (generic_gaze_supplied) {
    if (
      is.null(x_col) ||
        is.null(y_col)
    ) {
      stop(
        "`x_col` and `y_col` must be supplied together.",
        call. = FALSE
      )
    }

    x_col <- .gp_gzr_resolve_column(
      data,
      x_col,
      character(),
      "gaze x",
      TRUE
    )

    y_col <- .gp_gzr_resolve_column(
      data,
      y_col,
      character(),
      "gaze y",
      TRUE
    )

    gaze_rows[[1L]] <- data.frame(
      measure = c("x", "y"),
      role = c(
        "generic",
        "generic"
      ),
      source_column = c(
        x_col,
        y_col
      ),
      output_column = c(
        "x",
        "y"
      ),
      stringsAsFactors = FALSE
    )
  } else if (eye_gaze_supplied) {
    left_pair <- .gp_gzr_resolve_pair(
      data = data,
      first = x_left_col,
      second = y_left_col,
      first_name = "x_left_col",
      second_name = "y_left_col",
      role = "left",
      output = c(
        "x_left",
        "y_left"
      )
    )

    right_pair <- .gp_gzr_resolve_pair(
      data = data,
      first = x_right_col,
      second = y_right_col,
      first_name = "x_right_col",
      second_name = "y_right_col",
      role = "right",
      output = c(
        "x_right",
        "y_right"
      )
    )

    if (!is.null(left_pair)) {
      gaze_rows[[length(gaze_rows) + 1L]] <-
        left_pair
    }

    if (!is.null(right_pair)) {
      gaze_rows[[length(gaze_rows) + 1L]] <-
        right_pair
    }
  } else {
    left_x <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "x_left",
        "gaze_x_left",
        "left_gaze_x",
        "LPOGX",
        "L_GAZE_X"
      ),
      "left gaze x",
      FALSE
    )

    left_y <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "y_left",
        "gaze_y_left",
        "left_gaze_y",
        "LPOGY",
        "L_GAZE_Y"
      ),
      "left gaze y",
      FALSE
    )

    right_x <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "x_right",
        "gaze_x_right",
        "right_gaze_x",
        "RPOGX",
        "R_GAZE_X"
      ),
      "right gaze x",
      FALSE
    )

    right_y <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "y_right",
        "gaze_y_right",
        "right_gaze_y",
        "RPOGY",
        "R_GAZE_Y"
      ),
      "right gaze y",
      FALSE
    )

    if (xor(is.null(left_x), is.null(left_y))) {
      stop(
        "An incomplete automatically detected left-eye gaze pair was found.",
        call. = FALSE
      )
    }

    if (xor(is.null(right_x), is.null(right_y))) {
      stop(
        "An incomplete automatically detected right-eye gaze pair was found.",
        call. = FALSE
      )
    }

    if (
      !is.null(left_x) &&
        !is.null(left_y)
    ) {
      gaze_rows[[length(gaze_rows) + 1L]] <-
        data.frame(
          measure = c("x", "y"),
          role = c("left", "left"),
          source_column = c(
            left_x,
            left_y
          ),
          output_column = c(
            "x_left",
            "y_left"
          ),
          stringsAsFactors = FALSE
        )
    }

    if (
      !is.null(right_x) &&
        !is.null(right_y)
    ) {
      gaze_rows[[length(gaze_rows) + 1L]] <-
        data.frame(
          measure = c("x", "y"),
          role = c(
            "right",
            "right"
          ),
          source_column = c(
            right_x,
            right_y
          ),
          output_column = c(
            "x_right",
            "y_right"
          ),
          stringsAsFactors = FALSE
        )
    }

    if (length(gaze_rows) == 0L) {
      generic_x <- .gp_gzr_resolve_column(
        data,
        NULL,
        c(
          "x",
          "gaze_x",
          "BPOGX",
          "FPOGX",
          "GAZE_X",
          "GazePointX"
        ),
        "gaze x",
        FALSE
      )

      generic_y <- .gp_gzr_resolve_column(
        data,
        NULL,
        c(
          "y",
          "gaze_y",
          "BPOGY",
          "FPOGY",
          "GAZE_Y",
          "GazePointY"
        ),
        "gaze y",
        FALSE
      )

      if (
        xor(
          is.null(generic_x),
          is.null(generic_y)
        )
      ) {
        stop(
          "An incomplete automatically detected gaze-coordinate pair was found.",
          call. = FALSE
        )
      }

      if (
        !is.null(generic_x) &&
          !is.null(generic_y)
      ) {
        gaze_rows[[1L]] <-
          data.frame(
            measure = c("x", "y"),
            role = c(
              "generic",
              "generic"
            ),
            source_column = c(
              generic_x,
              generic_y
            ),
            output_column = c(
              "x",
              "y"
            ),
            stringsAsFactors = FALSE
          )
      }
    }
  }

  generic_pupil_supplied <-
    !is.null(pupil_col)

  eye_pupil_supplied <-
    !is.null(pupil_left_col) ||
    !is.null(pupil_right_col)

  if (
    generic_pupil_supplied &&
      eye_pupil_supplied
  ) {
    stop(
      "Supply either `pupil_col` or per-eye pupil columns, not both.",
      call. = FALSE
    )
  }

  pupil_rows <- list()

  if (generic_pupil_supplied) {
    pupil_col <- .gp_gzr_resolve_column(
      data,
      pupil_col,
      character(),
      "pupil",
      TRUE
    )

    pupil_rows[[1L]] <- data.frame(
      measure = "pupil",
      role = "generic",
      source_column =
        pupil_col,
      output_column =
        "pupil",
      stringsAsFactors = FALSE
    )
  } else if (eye_pupil_supplied) {
    if (!is.null(pupil_left_col)) {
      pupil_left_col <-
        .gp_gzr_resolve_column(
          data,
          pupil_left_col,
          character(),
          "left pupil",
          TRUE
        )

      pupil_rows[[length(pupil_rows) + 1L]] <-
        data.frame(
          measure = "pupil",
          role = "left",
          source_column =
            pupil_left_col,
          output_column =
            "pupil_left",
          stringsAsFactors = FALSE
        )
    }

    if (!is.null(pupil_right_col)) {
      pupil_right_col <-
        .gp_gzr_resolve_column(
          data,
          pupil_right_col,
          character(),
          "right pupil",
          TRUE
        )

      pupil_rows[[length(pupil_rows) + 1L]] <-
        data.frame(
          measure = "pupil",
          role = "right",
          source_column =
            pupil_right_col,
          output_column =
            "pupil_right",
          stringsAsFactors = FALSE
        )
    }
  } else {
    left_pupil <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "pupil_left",
        "left_pupil",
        "left_pupil_diameter",
        "LPD",
        "LPMM"
      ),
      "left pupil",
      FALSE
    )

    right_pupil <- .gp_gzr_resolve_column(
      data,
      NULL,
      c(
        "pupil_right",
        "right_pupil",
        "right_pupil_diameter",
        "RPD",
        "RPMM"
      ),
      "right pupil",
      FALSE
    )

    if (!is.null(left_pupil)) {
      pupil_rows[[length(pupil_rows) + 1L]] <-
        data.frame(
          measure = "pupil",
          role = "left",
          source_column =
            left_pupil,
          output_column =
            "pupil_left",
          stringsAsFactors = FALSE
        )
    }

    if (!is.null(right_pupil)) {
      pupil_rows[[length(pupil_rows) + 1L]] <-
        data.frame(
          measure = "pupil",
          role = "right",
          source_column =
            right_pupil,
          output_column =
            "pupil_right",
          stringsAsFactors = FALSE
        )
    }

    if (length(pupil_rows) == 0L) {
      generic_pupil <- .gp_gzr_resolve_column(
        data,
        NULL,
        c(
          "pupil",
          "Pupil",
          "Pupil_Mean",
          "mean_pupil",
          "pupil_mean",
          "BPD",
          "APD"
        ),
        "pupil",
        FALSE
      )

      if (!is.null(generic_pupil)) {
        pupil_rows[[1L]] <-
          data.frame(
            measure = "pupil",
            role = "generic",
            source_column =
              generic_pupil,
            output_column =
              "pupil",
            stringsAsFactors = FALSE
          )
      }
    }
  }

  gaze <- if (
    length(gaze_rows) > 0L
  ) {
    do.call(
      rbind,
      gaze_rows
    )
  } else {
    data.frame(
      measure = character(),
      role = character(),
      source_column = character(),
      output_column = character(),
      stringsAsFactors = FALSE
    )
  }

  pupil <- if (
    length(pupil_rows) > 0L
  ) {
    do.call(
      rbind,
      pupil_rows
    )
  } else {
    data.frame(
      measure = character(),
      role = character(),
      source_column = character(),
      output_column = character(),
      stringsAsFactors = FALSE
    )
  }

  rownames(gaze) <- NULL
  rownames(pupil) <- NULL

  if (
    nrow(gaze) == 0L &&
      nrow(pupil) == 0L
  ) {
    stop(
      "Could not identify gaze or pupil channels. Supply the relevant ",
      "column arguments explicitly.",
      call. = FALSE
    )
  }

  list(
    gaze = gaze,
    pupil = pupil
  )
}

.gp_gzr_resolve_pair <- function(
    data,
    first,
    second,
    first_name,
    second_name,
    role,
    output) {
  if (
    is.null(first) &&
      is.null(second)
  ) {
    return(NULL)
  }

  if (
    is.null(first) ||
      is.null(second)
  ) {
    stop(
      "`",
      first_name,
      "` and `",
      second_name,
      "` must be supplied together.",
      call. = FALSE
    )
  }

  first <- .gp_gzr_resolve_column(
    data,
    first,
    character(),
    first_name,
    TRUE
  )

  second <- .gp_gzr_resolve_column(
    data,
    second,
    character(),
    second_name,
    TRUE
  )

  data.frame(
    measure = c("x", "y"),
    role = rep(role, 2L),
    source_column = c(
      first,
      second
    ),
    output_column = output,
    stringsAsFactors = FALSE
  )
}

.gp_gzr_resolve_role_flags <- function(
    data,
    active_roles,
    generic_col,
    left_col,
    right_col,
    generic_candidates,
    left_candidates,
    right_candidates,
    description) {
  generic_col <- .gp_gzr_resolve_column(
    data,
    generic_col,
    generic_candidates,
    paste0(
      "shared ",
      description
    ),
    FALSE
  )

  left_col <- if (
    "left" %in% active_roles
  ) {
    .gp_gzr_resolve_column(
      data,
      left_col,
      left_candidates,
      paste0(
        "left ",
        description
      ),
      FALSE
    )
  } else {
    NULL
  }

  right_col <- if (
    "right" %in% active_roles
  ) {
    .gp_gzr_resolve_column(
      data,
      right_col,
      right_candidates,
      paste0(
        "right ",
        description
      ),
      FALSE
    )
  } else {
    NULL
  }

  result <- list(
    generic = if (
      "generic" %in% active_roles
    ) {
      generic_col
    } else {
      NULL
    },
    left = if (
      "left" %in% active_roles
    ) {
      if (!is.null(left_col)) {
        left_col
      } else {
        generic_col
      }
    } else {
      NULL
    },
    right = if (
      "right" %in% active_roles
    ) {
      if (!is.null(right_col)) {
        right_col
      } else {
        generic_col
      }
    } else {
      NULL
    }
  )

  result[active_roles]
}

.gp_gzr_validity_value <- function(
    x,
    valid_values = NULL) {
  missing <- is.na(x)

  if (!is.null(valid_values)) {
    valid <- as.character(x) %in%
      as.character(valid_values)
  } else if (is.logical(x)) {
    valid <- x
  } else if (is.numeric(x)) {
    valid <-
      is.finite(x) &
      x > 0
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

    unknown <-
      !missing &
      !normalized %in%
      c(
        valid_text,
        invalid_text
      )

    if (any(unknown)) {
      stop(
        "Unsupported values were found in a validity column. ",
        "Supply `valid_values` explicitly.",
        call. = FALSE
      )
    }

    valid <- normalized %in%
      valid_text
  }

  valid[is.na(valid)] <- FALSE
  as.logical(valid)
}

.gp_gzr_blink_value <- function(x) {
  missing <- is.na(x)

  if (is.logical(x)) {
    blink <- x
  } else if (is.numeric(x)) {
    blink <-
      is.finite(x) &
      x != 0
  } else {
    normalized <- tolower(
      trimws(as.character(x))
    )

    blink_text <- c(
      "true",
      "t",
      "yes",
      "y",
      "1",
      "blink",
      "blinking"
    )

    non_blink_text <- c(
      "false",
      "f",
      "no",
      "n",
      "0",
      "valid",
      "open",
      "no_blink"
    )

    unknown <-
      !missing &
      !normalized %in%
      c(
        blink_text,
        non_blink_text
      )

    if (any(unknown)) {
      stop(
        "Unsupported values were found in a blink column.",
        call. = FALSE
      )
    }

    blink <- normalized %in%
      blink_text
  }

  blink[is.na(blink)] <- FALSE
  as.logical(blink)
}

.gp_gzr_sampling_audit <- function(
    data,
    sampling_tolerance) {
  key <- paste(
    data$subject,
    data$trial,
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
    time <- data$time[idx]
    delta <- diff(time)

    repeated <- sum(
      delta == 0
    )

    negative <- sum(
      delta < 0
    )

    positive <- delta[
      is.finite(delta) &
        delta > 0
    ]

    median_interval <- if (
      length(positive) > 0L
    ) {
      stats::median(
        positive
      )
    } else {
      NA_real_
    }

    relative_error <- if (
      is.finite(median_interval) &&
        median_interval > 0
    ) {
      abs(
        positive -
          median_interval
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
      subject =
        data$subject[idx[1L]],
      trial =
        data$trial[idx[1L]],
      group_id =
        group_names[i],
      sample_count =
        length(idx),
      start_time_ms =
        min(time),
      end_time_ms =
        max(time),
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

.gp_gzr_resolve_time_unit <- function(
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
    "The time unit is ambiguous. Supply `time_unit` explicitly.",
    call. = FALSE
  )
}

.gp_gzr_numeric_values <- function(
    x,
    argument) {
  if (is.null(x)) {
    return(numeric())
  }

  x <- suppressWarnings(
    as.numeric(x)
  )

  if (
    length(x) == 0L ||
      anyNA(x)
  ) {
    stop(
      "`",
      argument,
      "` must contain numeric values.",
      call. = FALSE
    )
  }

  unique(x)
}

.gp_gzr_role_suffix <- function(role) {
  switch(
    role,
    generic = "",
    left = "left",
    right = "right",
    role
  )
}

.gp_gzr_check_identifier <- function(
    x,
    label) {
  if (
    anyNA(x) ||
      any(!nzchar(trimws(x)))
  ) {
    stop(
      label,
      " values must be non-missing and non-empty.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_gzr_optional_columns <- function(
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
      paste(
        missing,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  columns
}

.gp_gzr_resolve_column <- function(
    data,
    supplied,
    candidates,
    description,
    required) {
  if (!is.null(supplied)) {
    supplied <- .gp_gzr_nonempty_string(
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

  detected <- .gp_gzr_find_candidate(
    names(data),
    candidates
  )

  if (
    is.null(detected) &&
      isTRUE(required)
  ) {
    stop(
      "Could not identify a ",
      description,
      " column. Supply it explicitly.",
      call. = FALSE
    )
  }

  detected
}

.gp_gzr_find_candidate <- function(
    names_vector,
    candidates) {
  lower_names <- tolower(
    names_vector
  )

  for (candidate in candidates) {
    hit <- which(
      lower_names ==
        tolower(candidate)
    )

    if (length(hit) > 0L) {
      return(
        names_vector[hit[1L]]
      )
    }
  }

  NULL
}

.gp_gzr_positive_scalar <- function(
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

.gp_gzr_nonnegative_scalar <- function(
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

.gp_gzr_logical_scalar <- function(
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

.gp_gzr_nonempty_string <- function(
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
