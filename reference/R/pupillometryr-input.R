#' Prepare Gazepoint pupil data for PupillometryR
#'
#' Converts sample-level Gazepoint pupil data into a conservative, audited
#' long-form table compatible with
#' `PupillometryR::make_pupillometryr_data()`.
#'
#' @param data Sample-level Gazepoint pupil data frame.
#' @param participant_col Participant identifier column. If `NULL`, common
#'   Gazepoint participant names are searched.
#' @param trial_col Trial identifier column. If `NULL`, common trial, media,
#'   and stimulus names are searched.
#' @param time_col Numeric time or sample-counter column. If `NULL`, common
#'   Gazepoint time columns are searched.
#' @param condition_col Experimental-condition column. If `NULL`, common
#'   condition names are searched.
#' @param pupil_left_col Optional left-pupil column.
#' @param pupil_right_col Optional right-pupil column.
#' @param pupil_col Optional single, cyclopean, or previously averaged pupil
#'   column. Supply either `pupil_col` or left/right columns, not both.
#' @param time_unit Source time unit: `"auto"`, `"seconds"`,
#'   `"milliseconds"`, or `"samples"`. The prepared `Time` column is expressed
#'   in milliseconds.
#' @param sampling_rate_hz Sampling rate required when time is represented by
#'   sample indices.
#' @param rezero_time Logical. Subtract the first time separately within each
#'   participant-trial group.
#' @param invalid_pupil_values Optional pupil values to flag explicitly as
#'   invalid, for example `c(-1, 0)`.
#' @param validity_cols Optional pupil-validity columns. Supply one column to
#'   apply it to all pupil channels or one column per pupil channel.
#' @param valid_values Optional explicit values treated as valid in
#'   `validity_cols`. Without this argument, positive numeric values, `TRUE`,
#'   and common textual valid labels are treated as valid.
#' @param blink_cols Optional blink columns. Supply one column to apply it to
#'   all pupil channels or one column per pupil channel.
#' @param mask_invalid Logical. When `TRUE`, samples flagged by explicit invalid
#'   values, failed validity, or blink columns are replaced with `NA` in the
#'   prepared pupil columns. Non-finite pupil values are always represented as
#'   `NA`.
#' @param create_mean_pupil Logical. Create `Pupil_Mean` when both left and
#'   right pupil columns are available.
#' @param other_cols Optional additional condition, item, stimulus, block,
#'   or metadata columns retained unchanged.
#' @param sampling_tolerance Maximum relative deviation from the median
#'   within-trial sampling interval.
#' @param irregular Handling of irregular sampling: `"error"` or `"allow"`.
#' @param create_object Logical. If `TRUE`, construct an actual PupillometryR
#'   object. The optional PupillometryR package must then be installed.
#'
#' @return An object of class `"gazepoint_pupillometryr_input"` containing:
#'
#' - `data`: plain PupillometryR-compatible long-form data;
#' - `object`: optional PupillometryR object;
#' - `row_audit`: row-level pupil availability and flag audit;
#' - `sampling`: participant-trial sampling audit;
#' - `manifest`: column mappings and preparation summary;
#' - `settings`: resolved preparation settings.
#'
#' @details
#' The standardized compatibility columns are `Subject`, `Trial`, `Time`, and
#' `Condition`. `Time` is expressed in milliseconds. Pupil columns are named
#' `Pupil_Left`, `Pupil_Right`, `Pupil`, and, when requested and available,
#' `Pupil_Mean`.
#'
#' The helper does not detect blinks, interpolate gaps, filter pupil signals,
#' remove trials, baseline-correct pupil size, or run inferential analyses.
#' Existing blink and validity columns are preserved as audit information and
#' are used for masking only when `mask_invalid = TRUE`.
#'
#' @examples
#' pupil <- data.frame(
#'   participant = rep("P01", 4),
#'   trial = rep("T01", 4),
#'   condition = rep("target", 4),
#'   time_s = c(0, 0.1, 0.2, 0.3),
#'   pupil_left = c(3.1, 3.2, NA, 3.3),
#'   pupil_right = c(3.0, 3.1, NA, 3.2)
#' )
#'
#' prepared <- prepare_gazepoint_pupillometryr_input(pupil)
#' prepared$data
#' prepared$sampling
#'
#' @seealso
#' [detect_gazepoint_pupil_blinks()],
#' [clean_gazepoint_pupil_signal()],
#' [baseline_correct_gazepoint_pupil()]
#'
#' @export
prepare_gazepoint_pupillometryr_input <- function(
    data,
    participant_col = NULL,
    trial_col = NULL,
    time_col = NULL,
    condition_col = NULL,
    pupil_left_col = NULL,
    pupil_right_col = NULL,
    pupil_col = NULL,
    time_unit = c(
      "auto",
      "seconds",
      "milliseconds",
      "samples"
    ),
    sampling_rate_hz = NULL,
    rezero_time = FALSE,
    invalid_pupil_values = NULL,
    validity_cols = NULL,
    valid_values = NULL,
    blink_cols = NULL,
    mask_invalid = FALSE,
    create_mean_pupil = TRUE,
    other_cols = NULL,
    sampling_tolerance = 0.05,
    irregular = c("error", "allow"),
    create_object = FALSE) {
  time_unit <- match.arg(time_unit)
  irregular <- match.arg(irregular)

  .gp_ppr_logical_scalar(
    rezero_time,
    "rezero_time"
  )

  .gp_ppr_logical_scalar(
    mask_invalid,
    "mask_invalid"
  )

  .gp_ppr_logical_scalar(
    create_mean_pupil,
    "create_mean_pupil"
  )

  .gp_ppr_logical_scalar(
    create_object,
    "create_object"
  )

  .gp_ppr_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  if (!is.null(sampling_rate_hz)) {
    .gp_ppr_positive_scalar(
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

  participant_col <- .gp_ppr_resolve_column(
    data = data,
    supplied = participant_col,
    candidates = c(
      "Subject",
      "ParticipantName",
      "participant",
      "participant_id",
      "subject",
      "subject_id",
      "SUBJECT",
      "USER",
      "P"
    ),
    description = "participant",
    required = TRUE
  )

  trial_col <- .gp_ppr_resolve_column(
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

  time_col <- .gp_ppr_resolve_column(
    data = data,
    supplied = time_col,
    candidates = c(
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

  condition_col <- .gp_ppr_resolve_column(
    data = data,
    supplied = condition_col,
    candidates = c(
      "Condition",
      "condition",
      "Type",
      "type",
      "experimental_condition",
      "trial_type",
      "stimulus_condition",
      "group"
    ),
    description = "condition",
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

  condition <- as.character(
    data[[condition_col]]
  )

  .gp_ppr_check_identifiers(
    participant,
    "Participant"
  )

  .gp_ppr_check_identifiers(
    trial,
    "Trial"
  )

  .gp_ppr_check_identifiers(
    condition,
    "Condition"
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

  resolved_time_unit <- .gp_ppr_resolve_time_unit(
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

  pupil_columns <- .gp_ppr_resolve_pupil_columns(
    data = data,
    pupil_left_col = pupil_left_col,
    pupil_right_col = pupil_right_col,
    pupil_col = pupil_col
  )

  source_pupil_cols <-
    pupil_columns$source_column

  pupil_roles <-
    pupil_columns$role

  output_pupil_cols <-
    pupil_columns$output_column

  validity_cols <- .gp_ppr_resolve_flag_columns(
    data = data,
    supplied = validity_cols,
    pupil_count = length(source_pupil_cols),
    argument = "validity_cols"
  )

  blink_cols <- .gp_ppr_resolve_flag_columns(
    data = data,
    supplied = blink_cols,
    pupil_count = length(source_pupil_cols),
    argument = "blink_cols"
  )

  if (!is.null(invalid_pupil_values)) {
    invalid_pupil_values <- suppressWarnings(
      as.numeric(invalid_pupil_values)
    )

    if (
      length(invalid_pupil_values) == 0L ||
        anyNA(invalid_pupil_values)
    ) {
      stop(
        "`invalid_pupil_values` must contain numeric values.",
        call. = FALSE
      )
    }

    invalid_pupil_values <- unique(
      invalid_pupil_values
    )
  }

  pupil_values <- vector(
    "list",
    length(source_pupil_cols)
  )

  finite_flags <- vector(
    "list",
    length(source_pupil_cols)
  )

  explicit_invalid_flags <- vector(
    "list",
    length(source_pupil_cols)
  )

  validity_flags <- vector(
    "list",
    length(source_pupil_cols)
  )

  blink_flags <- vector(
    "list",
    length(source_pupil_cols)
  )

  invalid_flags <- vector(
    "list",
    length(source_pupil_cols)
  )

  for (i in seq_along(source_pupil_cols)) {
    column <- source_pupil_cols[i]

    if (!is.numeric(data[[column]])) {
      stop(
        "Pupil column `",
        column,
        "` must be numeric.",
        call. = FALSE
      )
    }

    raw <- suppressWarnings(
      as.numeric(data[[column]])
    )

    finite <- is.finite(raw)

    explicitly_invalid <- rep(
      FALSE,
      length(raw)
    )

    if (!is.null(invalid_pupil_values)) {
      explicitly_invalid <-
        !is.na(raw) &
        raw %in% invalid_pupil_values
    }

    valid <- rep(
      TRUE,
      length(raw)
    )

    if (length(validity_cols) > 0L) {
      valid <- .gp_ppr_validity_value(
        data[[validity_cols[i]]],
        valid_values = valid_values
      )
    }

    blink <- rep(
      FALSE,
      length(raw)
    )

    if (length(blink_cols) > 0L) {
      blink <- .gp_ppr_blink_value(
        data[[blink_cols[i]]]
      )
    }

    invalid <-
      !finite |
      explicitly_invalid |
      !valid |
      blink

    prepared_value <- raw
    prepared_value[!finite] <- NA_real_

    if (isTRUE(mask_invalid)) {
      prepared_value[
        explicitly_invalid |
          !valid |
          blink
      ] <- NA_real_
    }

    pupil_values[[i]] <- prepared_value
    finite_flags[[i]] <- finite
    explicit_invalid_flags[[i]] <-
      explicitly_invalid
    validity_flags[[i]] <- valid
    blink_flags[[i]] <- blink
    invalid_flags[[i]] <- invalid
  }

  names(pupil_values) <- output_pupil_cols

  prepared_pupils <- as.data.frame(
    pupil_values,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  validity_output_names <- paste0(
    "Valid_",
    .gp_ppr_role_suffix(pupil_roles)
  )

  blink_output_names <- paste0(
    "Blink_",
    .gp_ppr_role_suffix(pupil_roles)
  )

  validity_output <- as.data.frame(
    stats::setNames(
      validity_flags,
      validity_output_names
    ),
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  blink_output <- as.data.frame(
    stats::setNames(
      blink_flags,
      blink_output_names
    ),
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  mean_source_count <- integer(
    nrow(data)
  )

  if (
    isTRUE(create_mean_pupil) &&
      all(
        c("Pupil_Left", "Pupil_Right") %in%
          names(prepared_pupils)
      )
  ) {
    mean_matrix <- cbind(
      prepared_pupils$Pupil_Left,
      prepared_pupils$Pupil_Right
    )

    mean_source_count <- rowSums(
      is.finite(mean_matrix)
    )

    pupil_mean <- rowMeans(
      mean_matrix,
      na.rm = TRUE
    )

    pupil_mean[
      mean_source_count == 0L
    ] <- NA_real_

    prepared_pupils$Pupil_Mean <-
      pupil_mean
  }

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

  condition_problem <- vapply(
    groups,
    function(idx) {
      length(unique(condition[idx])) != 1L
    },
    logical(1)
  )

  if (any(condition_problem)) {
    first_problem <- names(groups)[
      which(condition_problem)[1L]
    ]

    stop(
      "Condition must be constant within each participant-trial group. ",
      "The first conflict is in group `",
      first_problem,
      "`.",
      call. = FALSE
    )
  }

  if (isTRUE(rezero_time)) {
    for (idx in groups) {
      time_ms[idx] <-
        time_ms[idx] -
        min(time_ms[idx])
    }
  }

  duplicate_key <- paste(
    participant,
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
      "Participant-trial-time rows must be unique. ",
      "The first duplicate involves source row ",
      duplicate_row,
      ".",
      call. = FALSE
    )
  }

  other_cols <- .gp_ppr_optional_columns(
    data,
    other_cols,
    "other_cols"
  )

  reserved <- c(
    "Subject",
    "Trial",
    "Time",
    "Condition",
    names(prepared_pupils),
    names(validity_output),
    names(blink_output)
  )

  collisions <- intersect(
    other_cols,
    reserved
  )

  if (length(collisions) > 0L) {
    stop(
      "`other_cols` conflict with prepared columns: ",
      paste(collisions, collapse = ", "),
      call. = FALSE
    )
  }

  prepared <- data.frame(
    Subject = participant,
    Trial = trial,
    Time = time_ms,
    Condition = condition,
    stringsAsFactors = FALSE
  )

  prepared <- cbind(
    prepared,
    prepared_pupils,
    validity_output,
    blink_output
  )

  if (length(other_cols) > 0L) {
    prepared <- cbind(
      prepared,
      data[other_cols]
    )
  }

  order_index <- order(
    prepared$Subject,
    prepared$Trial,
    prepared$Time,
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

  sampling <- .gp_ppr_sampling_audit(
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

  finite_matrix <- do.call(
    cbind,
    finite_flags
  )

  explicit_invalid_matrix <- do.call(
    cbind,
    explicit_invalid_flags
  )

  validity_matrix <- do.call(
    cbind,
    validity_flags
  )

  blink_matrix <- do.call(
    cbind,
    blink_flags
  )

  invalid_matrix <- do.call(
    cbind,
    invalid_flags
  )

  row_audit <- data.frame(
    source_row = seq_len(nrow(data)),
    prepared_row = prepared_row,
    participant = participant,
    trial = trial,
    condition = condition,
    source_time = source_time,
    prepared_time_ms = time_ms,
    finite_pupil_count =
      rowSums(finite_matrix),
    explicit_invalid_count =
      rowSums(explicit_invalid_matrix),
    invalid_validity_count =
      rowSums(!validity_matrix),
    blink_count =
      rowSums(blink_matrix),
    invalid_pupil_count =
      rowSums(invalid_matrix),
    usable_pupil_count =
      rowSums(!invalid_matrix),
    mean_source_count =
      mean_source_count,
    stringsAsFactors = FALSE
  )

  column_manifest <- data.frame(
    role = c(
      "subject",
      "trial",
      "time",
      "condition",
      pupil_roles,
      if (
        "Pupil_Mean" %in%
          names(prepared_pupils)
      ) {
        "mean_pupil"
      },
      rep(
        "validity",
        length(validity_cols)
      ),
      rep(
        "blink",
        length(blink_cols)
      ),
      rep(
        "other",
        length(other_cols)
      )
    ),
    source_column = c(
      participant_col,
      trial_col,
      time_col,
      condition_col,
      source_pupil_cols,
      if (
        "Pupil_Mean" %in%
          names(prepared_pupils)
      ) {
        paste(
          c(
            pupil_left_col,
            pupil_right_col
          ),
          collapse = " + "
        )
      },
      validity_cols,
      blink_cols,
      other_cols
    ),
    output_column = c(
      "Subject",
      "Trial",
      "Time",
      "Condition",
      output_pupil_cols,
      if (
        "Pupil_Mean" %in%
          names(prepared_pupils)
      ) {
        "Pupil_Mean"
      },
      if (length(validity_cols) > 0L) {
        validity_output_names
      },
      if (length(blink_cols) > 0L) {
        blink_output_names
      },
      other_cols
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
      "character condition",
      rep(
        if (mask_invalid) {
          "numeric pupil; invalid, blink, and failed-validity samples set to NA"
        } else {
          "numeric pupil; non-finite values set to NA; flags retained without masking"
        },
        length(source_pupil_cols)
      ),
      if (
        "Pupil_Mean" %in%
          names(prepared_pupils)
      ) {
        "row mean of available prepared left and right pupil values"
      },
      rep(
        "converted to logical validity",
        length(validity_cols)
      ),
      rep(
        "converted to logical blink flag",
        length(blink_cols)
      ),
      rep(
        "retained unchanged",
        length(other_cols)
      )
    ),
    stringsAsFactors = FALSE
  )

  summary_manifest <- data.frame(
    n_rows = nrow(prepared),
    n_participants =
      length(unique(prepared$Subject)),
    n_participant_trials =
      nrow(sampling),
    pupil_channel_count =
      length(source_pupil_cols),
    mean_pupil_created =
      "Pupil_Mean" %in%
      names(prepared),
    rows_with_no_finite_pupil =
      sum(
        row_audit$finite_pupil_count == 0L
      ),
    rows_with_any_invalid_pupil =
      sum(
        row_audit$invalid_pupil_count > 0L
      ),
    rows_with_any_blink =
      sum(
        row_audit$blink_count > 0L
      ),
    irregular_group_count =
      sum(
        sampling$irregular_interval_count > 0L
      ),
    source_order_changed =
      source_order_changed,
    invalid_samples_masked =
      mask_invalid,
    object_created =
      create_object,
    stringsAsFactors = FALSE
  )

  pupillometryr_object <- NULL

  if (isTRUE(create_object)) {
    if (
      !requireNamespace(
        "PupillometryR",
        quietly = TRUE
      )
    ) {
      stop(
        "Package `PupillometryR` is required when ",
        "`create_object = TRUE`.",
        call. = FALSE
      )
    }

    pupillometryr_object <-
      .gp_ppr_make_object(prepared)
  }

  settings <- list(
    participant_col = participant_col,
    trial_col = trial_col,
    time_col = time_col,
    condition_col = condition_col,
    source_time_unit =
      resolved_time_unit,
    output_time_unit = "milliseconds",
    sampling_rate_hz =
      sampling_rate_hz,
    rezero_time = rezero_time,
    pupil_columns =
      pupil_columns,
    invalid_pupil_values =
      invalid_pupil_values,
    validity_cols =
      validity_cols,
    valid_values =
      valid_values,
    blink_cols =
      blink_cols,
    mask_invalid =
      mask_invalid,
    create_mean_pupil =
      create_mean_pupil,
    other_cols =
      other_cols,
    sampling_tolerance =
      sampling_tolerance,
    irregular =
      irregular,
    create_object =
      create_object,
    interpretation_notes = c(
      "The compatibility table contains long-form sample-level pupil data.",
      "Blink detection, interpolation, filtering, trial exclusion, and baseline correction are not performed.",
      "Non-finite pupil values are represented as NA.",
      "Validity and blink flags mask pupil samples only when mask_invalid is TRUE.",
      "The helper prepares input and does not run PupillometryR analyses."
    )
  )

  structure(
    list(
      data = prepared,
      object = pupillometryr_object,
      row_audit = row_audit,
      sampling = sampling,
      manifest = list(
        columns = column_manifest,
        summary = summary_manifest
      ),
      settings = settings
    ),
    class = c(
      "gazepoint_pupillometryr_input",
      "list"
    )
  )
}

#' @export
print.gazepoint_pupillometryr_input <- function(
    x,
    ...) {
  cat("Gazepoint PupillometryR input\n")
  cat(
    "  Rows: ",
    nrow(x$data),
    "\n",
    sep = ""
  )
  cat(
    "  Participants: ",
    length(unique(x$data$Subject)),
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
    "  Pupil columns: ",
    paste(
      intersect(
        c(
          "Pupil_Left",
          "Pupil_Right",
          "Pupil",
          "Pupil_Mean"
        ),
        names(x$data)
      ),
      collapse = ", "
    ),
    "\n",
    sep = ""
  )
  cat(
    "  Rows with no finite pupil: ",
    x$manifest$summary$
      rows_with_no_finite_pupil,
    "\n",
    sep = ""
  )
  cat(
    "  PupillometryR object created: ",
    if (is.null(x$object)) "no" else "yes",
    "\n",
    sep = ""
  )

  invisible(x)
}

.gp_ppr_make_object <- function(prepared) {
  constructor <- getExportedValue(
    "PupillometryR",
    "make_pupillometryr_data"
  )

  call <- as.call(
    list(
      as.name(".constructor"),
      data = as.name(".prepared"),
      subject = as.name("Subject"),
      trial = as.name("Trial"),
      time = as.name("Time"),
      condition = as.name("Condition")
    )
  )

  environment <- list2env(
    list(
      .constructor = constructor,
      .prepared = prepared
    ),
    parent = parent.frame()
  )

  eval(
    call,
    envir = environment
  )
}

.gp_ppr_resolve_pupil_columns <- function(
    data,
    pupil_left_col,
    pupil_right_col,
    pupil_col) {
  if (
    !is.null(pupil_col) &&
      (
        !is.null(pupil_left_col) ||
          !is.null(pupil_right_col)
      )
  ) {
    stop(
      "Supply either `pupil_col` or left/right pupil columns, not both.",
      call. = FALSE
    )
  }

  if (!is.null(pupil_col)) {
    pupil_col <- .gp_ppr_resolve_column(
      data = data,
      supplied = pupil_col,
      candidates = character(),
      description = "pupil",
      required = TRUE
    )

    return(
      data.frame(
        role = "pupil",
        source_column = pupil_col,
        output_column = "Pupil",
        stringsAsFactors = FALSE
      )
    )
  }

  pupil_left_col <- .gp_ppr_resolve_column(
    data = data,
    supplied = pupil_left_col,
    candidates = c(
      "Pupil_Left",
      "pupil_left",
      "left_pupil",
      "left_pupil_diameter",
      "LPupil",
      "LPD",
      "LPMM"
    ),
    description = "left pupil",
    required = FALSE
  )

  pupil_right_col <- .gp_ppr_resolve_column(
    data = data,
    supplied = pupil_right_col,
    candidates = c(
      "Pupil_Right",
      "pupil_right",
      "right_pupil",
      "right_pupil_diameter",
      "RPupil",
      "RPD",
      "RPMM"
    ),
    description = "right pupil",
    required = FALSE
  )

  if (
    is.null(pupil_left_col) &&
      is.null(pupil_right_col)
  ) {
    pupil_col <- .gp_ppr_resolve_column(
      data = data,
      supplied = NULL,
      candidates = c(
        "Pupil",
        "pupil",
        "Pupil_Mean",
        "mean_pupil",
        "pupil_mean",
        "BPD",
        "APD"
      ),
      description = "pupil",
      required = FALSE
    )

    if (is.null(pupil_col)) {
      stop(
        "Could not identify a pupil column. Supply `pupil_col`, ",
        "`pupil_left_col`, or `pupil_right_col` explicitly.",
        call. = FALSE
      )
    }

    return(
      data.frame(
        role = "pupil",
        source_column = pupil_col,
        output_column = "Pupil",
        stringsAsFactors = FALSE
      )
    )
  }

  roles <- character()
  source <- character()
  output <- character()

  if (!is.null(pupil_left_col)) {
    roles <- c(roles, "pupil_left")
    source <- c(source, pupil_left_col)
    output <- c(output, "Pupil_Left")
  }

  if (!is.null(pupil_right_col)) {
    roles <- c(roles, "pupil_right")
    source <- c(source, pupil_right_col)
    output <- c(output, "Pupil_Right")
  }

  data.frame(
    role = roles,
    source_column = source,
    output_column = output,
    stringsAsFactors = FALSE
  )
}

.gp_ppr_resolve_flag_columns <- function(
    data,
    supplied,
    pupil_count,
    argument) {
  if (is.null(supplied)) {
    return(character())
  }

  supplied <- .gp_ppr_optional_columns(
    data,
    supplied,
    argument
  )

  if (length(supplied) == 1L) {
    return(
      rep(
        supplied,
        pupil_count
      )
    )
  }

  if (length(supplied) != pupil_count) {
    stop(
      "`",
      argument,
      "` must contain one shared column or one column per pupil channel.",
      call. = FALSE
    )
  }

  supplied
}

.gp_ppr_validity_value <- function(
    x,
    valid_values = NULL) {
  missing <- is.na(x)

  if (!is.null(valid_values)) {
    valid <- as.character(x) %in%
      as.character(valid_values)
  } else if (is.logical(x)) {
    valid <- x
  } else if (is.numeric(x)) {
    valid <- is.finite(x) & x > 0
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
      c(valid_text, invalid_text)

    if (any(unknown)) {
      stop(
        "Unsupported values were found in `validity_cols`. ",
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

.gp_ppr_blink_value <- function(x) {
  missing <- is.na(x)

  if (is.logical(x)) {
    blink <- x
  } else if (is.numeric(x)) {
    blink <- is.finite(x) & x != 0
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
      c(blink_text, non_blink_text)

    if (any(unknown)) {
      stop(
        "Unsupported values were found in `blink_cols`.",
        call. = FALSE
      )
    }

    blink <- normalized %in%
      blink_text
  }

  blink[is.na(blink)] <- FALSE
  as.logical(blink)
}

.gp_ppr_sampling_audit <- function(
    data,
    sampling_tolerance) {
  key <- paste(
    data$Subject,
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
    time <- data$Time[idx]
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
      Subject =
        data$Subject[idx[1L]],
      Trial =
        data$Trial[idx[1L]],
      Condition =
        data$Condition[idx[1L]],
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

.gp_ppr_resolve_time_unit <- function(
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

.gp_ppr_role_suffix <- function(role) {
  vapply(
    as.character(role),
    function(one_role) {
      switch(
        one_role,
        pupil_left = "Left",
        pupil_right = "Right",
        pupil = "Pupil",
        one_role
      )
    },
    character(1),
    USE.NAMES = FALSE
  )
}

.gp_ppr_check_identifiers <- function(
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

.gp_ppr_optional_columns <- function(
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

.gp_ppr_resolve_column <- function(
    data,
    supplied,
    candidates,
    description,
    required) {
  if (!is.null(supplied)) {
    supplied <- .gp_ppr_nonempty_string(
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

  detected <- .gp_ppr_find_candidate(
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

.gp_ppr_find_candidate <- function(
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

.gp_ppr_positive_scalar <- function(
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

.gp_ppr_nonnegative_scalar <- function(
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

.gp_ppr_logical_scalar <- function(
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

.gp_ppr_nonempty_string <- function(
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
