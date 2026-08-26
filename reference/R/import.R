#' Import a Gazepoint Biometrics export
#'
#' Reads a Gazepoint CSV export containing biometric columns such as GSR,
#' heart rate, interbeat interval, pulse signal, engagement dial, and TTL
#' synchronization fields. The function is conservative: it preserves original
#' column names, removes only empty trailing columns, and attaches a basic
#' biometric-column summary as an attribute.
#'
#' @param file Path to a Gazepoint CSV export.
#' @param na Values that should be treated as missing.
#'
#' @return A data frame with Gazepoint export columns preserved. The returned
#'   object has class `"gazepoint_biometrics"` and an attribute named
#'   `"biometric_columns"`.
#'
#' @export
import_gazepoint_biometrics <- function(file, na = c("", "NA", "NaN")) {
  if (missing(file) || length(file) != 1L || !nzchar(file)) {
    stop("`file` must be a single non-empty file path.", call. = FALSE)
  }

  if (!file.exists(file)) {
    stop("File does not exist: ", file, call. = FALSE)
  }

  dat <- utils::read.csv(
    file,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = na
  )

  dat <- drop_empty_trailing_columns(dat)

  attr(dat, "biometric_columns") <- check_gazepoint_biometric_columns(dat)
  class(dat) <- c("gazepoint_biometrics", class(dat))

  dat
}


#' Check Gazepoint biometric columns
#'
#' Checks whether a data frame contains known Gazepoint Biometrics columns.
#' This function does not assume that the channels are active. It only checks
#' whether the expected columns are present.
#'
#' @param data A data frame imported from a Gazepoint export.
#'
#' @return A data frame describing expected columns, their signal family,
#'   interpretation, and whether they are present.
#'
#' @export
check_gazepoint_biometric_columns <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  expected <- data.frame(
    column = c(
      "DIAL", "DIALV",
      "GSR", "GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSRV",
      "HR", "HRV", "HRP", "IBI",
      paste0("TTL", 0:6), "TTLV",
      "CNT", "TIME", "TIME_TICK", "USER", "USERID", "MEDIA_ID",
      "MEDIA_NAME", "FPOGX", "FPOGY", "FPOGS", "FPOGD", "FPOGID"
    ),
    signal = c(
      "engagement_dial", "engagement_dial",
      rep("gsr_eda", 5),
      rep("heart_rate", 4),
      rep("ttl_marker", 8),
      rep("time_identity_sync", 7),
      rep("fixation_gaze", 5)
    ),
    role = c(
      "dial_value", "dial_validity",
      "gsr_raw_or_resistance", "gsr_conductance_microsiemens",
      "gsr_tonic_component", "gsr_phasic_component", "gsr_validity",
      "heart_rate_bpm", "heart_rate_validity_not_hrv_metric",
      "pulse_signal", "interbeat_interval_seconds",
      rep("ttl_channel", 7), "ttl_validity",
      "sample_counter", "recording_time", "recording_tick",
      "user_label", "user_identifier", "media_identifier",
      "media_name", "fixation_x", "fixation_y",
      "fixation_start_time", "fixation_duration", "fixation_identifier"
    ),
    stringsAsFactors = FALSE
  )

  expected$present <- expected$column %in% names(data)
  expected
}


#' Detect active Gazepoint biometric channels
#'
#' Detects whether GSR/EDA, heart-rate, engagement-dial, and TTL channels are
#' present and whether they appear active. A channel can be present but inactive
#' when validity flags are zero or the signal contains only zeros or missing
#' values. For each signal family, `summary_column` identifies the primary
#' column used for the reported minimum and maximum values.
#'
#' @param data A data frame imported from a Gazepoint export.
#'
#' @return A data frame with one row per signal family.
#'
#' @export
detect_active_biometric_channels <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  out <- rbind(
    detect_one_channel(
      data = data,
      signal = "gsr_eda",
      value_columns = c("GSR_US", "GSR", "GSR_US_TONIC", "GSR_US_PHASIC"),
      validity_columns = "GSRV"
    ),
    detect_one_channel(
      data = data,
      signal = "heart_rate",
      value_columns = c("HR", "IBI", "HRP"),
      validity_columns = "HRV"
    ),
    detect_one_channel(
      data = data,
      signal = "engagement_dial",
      value_columns = "DIAL",
      validity_columns = "DIALV"
    ),
    detect_one_channel(
      data = data,
      signal = "ttl_marker",
      value_columns = paste0("TTL", 0:6),
      validity_columns = "TTLV"
    )
  )

  rownames(out) <- NULL
  out
}


drop_empty_trailing_columns <- function(data) {
  if (!is.data.frame(data) || ncol(data) == 0L) {
    return(data)
  }

  empty_name <- names(data) == "" | is.na(names(data))

  empty_values <- vapply(
    data,
    function(x) all(is.na(x) | trimws(as.character(x)) == ""),
    logical(1)
  )

  drop <- empty_name & empty_values

  if (any(drop)) {
    data <- data[, !drop, drop = FALSE]
  }

  data
}


detect_one_channel <- function(data, signal, value_columns, validity_columns) {
  present_value_columns <- intersect(value_columns, names(data))
  present_validity_columns <- intersect(validity_columns, names(data))

  present <- length(present_value_columns) > 0L ||
    length(present_validity_columns) > 0L

  if (!present) {
    return(data.frame(
      signal = signal,
      present = FALSE,
      active = FALSE,
      value_columns = NA_character_,
      summary_column = NA_character_,
      validity_columns = NA_character_,
      valid_rows = 0L,
      nonzero_rows = 0L,
      min_value = NA_real_,
      max_value = NA_real_,
      stringsAsFactors = FALSE
    ))
  }

  summary_column <- choose_signal_summary_column(
    signal = signal,
    present_value_columns = present_value_columns
  )

  if (is.na(summary_column)) {
    x <- rep(NA_real_, nrow(data))
  } else {
    x <- as_numeric_safe(data[[summary_column]])
  }

  valid <- !is.na(x)

  if (length(present_validity_columns) > 0L) {
    validity_values <- lapply(present_validity_columns, function(column) {
      as_numeric_safe(data[[column]])
    })

    validity_matrix <- do.call(cbind, validity_values)

    valid <- valid &
      rowSums(!is.na(validity_matrix) & validity_matrix > 0) > 0
  }

  nonzero <- !is.na(x) & x != 0

  active <- any(nonzero & valid)

  usable_values <- x[valid & !is.na(x)]

  data.frame(
    signal = signal,
    present = TRUE,
    active = active,
    value_columns = paste(present_value_columns, collapse = ","),
    summary_column = summary_column,
    validity_columns = ifelse(
      length(present_validity_columns) > 0L,
      paste(present_validity_columns, collapse = ","),
      NA_character_
    ),
    valid_rows = sum(valid),
    nonzero_rows = sum(nonzero),
    min_value = ifelse(length(usable_values) > 0L, min(usable_values), NA_real_),
    max_value = ifelse(length(usable_values) > 0L, max(usable_values), NA_real_),
    stringsAsFactors = FALSE
  )
}


choose_signal_summary_column <- function(signal, present_value_columns) {
  if (length(present_value_columns) == 0L) {
    return(NA_character_)
  }

  priority <- switch(
    signal,
    gsr_eda = c("GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSR"),
    heart_rate = c("HR", "IBI", "HRP"),
    engagement_dial = c("DIAL"),
    ttl_marker = c("TTL0", "TTL1", "TTL2", "TTL3", "TTL4", "TTL5", "TTL6"),
    present_value_columns
  )

  candidates <- intersect(priority, present_value_columns)

  if (length(candidates) > 0L) {
    return(candidates[1])
  }

  present_value_columns[1]
}


as_numeric_safe <- function(x) {
  suppressWarnings(as.numeric(x))
}
