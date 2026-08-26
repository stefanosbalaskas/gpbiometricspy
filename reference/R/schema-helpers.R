#' Standardise Gazepoint biometric column names
#'
#' Standardises common Gazepoint Biometrics column-name variants to stable
#' canonical names. The helper is intentionally conservative: it recognises
#' common biometric, timing, marker, participant, and stimulus columns, but it
#' leaves unknown columns unchanged apart from optional snake-case cleaning.
#'
#' @param data A data frame or a character vector of column names.
#' @param style Naming style to return. `"canonical"` returns uppercase
#'   Gazepoint-style names for recognised columns. `"snake"` returns lowercase
#'   snake-case names.
#' @param rename Logical. If `data` is a data frame, should the returned data
#'   frame have standardised names? If `FALSE`, a name-mapping table is returned.
#'
#' @return If `data` is a character vector, a character vector of standardised
#'   names. If `data` is a data frame and `rename = TRUE`, the data frame with
#'   standardised names. If `rename = FALSE`, a data frame mapping original names
#'   to standardised names.
#'
#' @examples
#' standardise_gazepoint_biometric_names(c("time ms", "heart rate", "eda uS"))
#'
#' df <- data.frame(`time ms` = 1:3, `heart rate` = c(70, 72, 71))
#' names(standardise_gazepoint_biometric_names(df))
#'
#' @export
standardise_gazepoint_biometric_names <- function(data,
                                                  style = c("canonical", "snake"),
                                                  rename = TRUE) {
  style <- match.arg(style)

  if (is.data.frame(data)) {
    original_names <- names(data)
  } else if (is.character(data)) {
    original_names <- data
  } else {
    stop("`data` must be a data frame or a character vector of column names.",
         call. = FALSE)
  }

  cleaned <- .gpbiom_clean_name(original_names)
  canonical <- .gpbiom_canonical_name(cleaned)

  if (identical(style, "snake")) {
    standard_names <- tolower(canonical)
  } else {
    standard_names <- canonical
  }

  standard_names <- make.unique(standard_names, sep = "_")

  if (is.character(data)) {
    return(standard_names)
  }

  mapping <- data.frame(
    original_name = original_names,
    standard_name = standard_names,
    changed = !identical(original_names, standard_names) &
      original_names != standard_names,
    stringsAsFactors = FALSE
  )

  if (!isTRUE(rename)) {
    return(mapping)
  }

  names(data) <- standard_names
  data
}


#' Detect Gazepoint biometric time columns
#'
#' Detects likely timing and counter columns in Gazepoint Biometrics exports.
#' The function reports candidate timing columns rather than assuming that any
#' single time variable is always present or always measured in the same unit.
#'
#' @param data A data frame or a character vector of column names.
#'
#' @return A data frame with one row per detected time-related column.
#'
#' @examples
#' detect_gazepoint_time_columns(c("CNT", "TIME_MS", "GSR", "HR"))
#'
#' @export
detect_gazepoint_time_columns <- function(data) {
  if (is.data.frame(data)) {
    original_names <- names(data)
  } else if (is.character(data)) {
    original_names <- data
  } else {
    stop("`data` must be a data frame or a character vector of column names.",
         call. = FALSE)
  }

  if (length(original_names) == 0L) {
    return(.gpbiom_empty_time_columns())
  }

  cleaned <- .gpbiom_clean_name(original_names)
  canonical <- .gpbiom_canonical_name(cleaned)

  role <- rep(NA_character_, length(original_names))
  unit_hint <- rep(NA_character_, length(original_names))
  confidence <- rep(0, length(original_names))
  reason <- rep(NA_character_, length(original_names))

  is_counter <- canonical %in% c("CNT", "SAMPLE", "SAMPLE_INDEX")
  role[is_counter] <- "sample_counter"
  unit_hint[is_counter] <- "samples"
  confidence[is_counter] <- 1
  reason[is_counter] <- "Recognised sample counter column."

  is_seconds <- canonical %in% c("TIME", "TIME_S", "TIMESTAMP_S")
  role[is_seconds] <- "timestamp"
  unit_hint[is_seconds] <- "seconds"
  confidence[is_seconds] <- 0.95
  reason[is_seconds] <- "Recognised time column with seconds-like name."

  is_ms <- canonical %in% c("TIME_MS", "TIMESTAMP_MS")
  role[is_ms] <- "timestamp"
  unit_hint[is_ms] <- "milliseconds"
  confidence[is_ms] <- 0.95
  reason[is_ms] <- "Recognised time column with milliseconds-like name."

  is_tick <- canonical %in% c("TIME_TICK", "TIME_TICKS", "TICK", "TICKS")
  role[is_tick] <- "timestamp"
  unit_hint[is_tick] <- "ticks"
  confidence[is_tick] <- 0.90
  reason[is_tick] <- "Recognised tick-style timing column."

  is_trial_time <- canonical %in% c("TRIAL_TIME", "MEDIA_TIME", "STIMULUS_TIME")
  role[is_trial_time] <- "trial_or_media_time"
  unit_hint[is_trial_time] <- "unknown"
  confidence[is_trial_time] <- 0.80
  reason[is_trial_time] <- "Recognised trial/media-relative timing column."

  generic_time <- is.na(role) & grepl("(^|_)time($|_)", cleaned)
  role[generic_time] <- "candidate_time"
  unit_hint[generic_time] <- "unknown"
  confidence[generic_time] <- 0.60
  reason[generic_time] <- "Column name contains a generic time token."

  detected <- !is.na(role)

  if (!any(detected)) {
    return(.gpbiom_empty_time_columns())
  }

  out <- data.frame(
    column = original_names[detected],
    standard_name = canonical[detected],
    role = role[detected],
    unit_hint = unit_hint[detected],
    confidence = confidence[detected],
    reason = reason[detected],
    stringsAsFactors = FALSE
  )

  out[order(-out$confidence, out$column), , drop = FALSE]
}


#' Detect the likely timebase of Gazepoint biometric data
#'
#' Inspects timing and counter columns and returns a conservative summary of the
#' likely primary timebase. Sampling rate is estimated only when numeric timing
#' information is available and intervals are positive.
#'
#' @param data A data frame.
#' @param time_col Optional explicit timing column.
#' @param counter_col Optional explicit counter column.
#'
#' @return A list with `overview`, `time_columns`, `interval_summary`, and
#'   `warnings`.
#'
#' @examples
#' df <- data.frame(CNT = 1:5, TIME = seq(0, by = 1 / 60, length.out = 5))
#' detect_gazepoint_biometric_timebase(df)
#'
#' @export
detect_gazepoint_biometric_timebase <- function(data,
                                                time_col = NULL,
                                                counter_col = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  time_columns <- detect_gazepoint_time_columns(data)
  warnings <- character()

  if (!is.null(time_col)) {
    if (!time_col %in% names(data)) {
      stop("`time_col` was not found in `data`.", call. = FALSE)
    }
    primary_col <- time_col
  } else {
    primary_col <- .gpbiom_choose_primary_time_column(data, time_columns)
  }

  if (!is.null(counter_col)) {
    if (!counter_col %in% names(data)) {
      stop("`counter_col` was not found in `data`.", call. = FALSE)
    }
    counter <- counter_col
  } else {
    counter <- .gpbiom_choose_counter_column(data, time_columns)
  }

  if (is.na(primary_col)) {
    warnings <- c(warnings, "No usable numeric time or counter column detected.")

    overview <- data.frame(
      n_rows = nrow(data),
      primary_time_column = NA_character_,
      primary_time_role = NA_character_,
      unit = NA_character_,
      median_interval = NA_real_,
      sampling_rate_hz = NA_real_,
      counter_column = ifelse(is.na(counter), NA_character_, counter),
      n_valid_intervals = 0L,
      status = "no_timebase_detected",
      stringsAsFactors = FALSE
    )

    return(list(
      overview = overview,
      time_columns = time_columns,
      interval_summary = .gpbiom_empty_interval_summary(),
      warnings = warnings
    ))
  }

  role <- .gpbiom_time_role(primary_col, time_columns)
  unit <- .gpbiom_time_unit(primary_col, time_columns, data[[primary_col]])

  interval_summary <- .gpbiom_interval_summary(data[[primary_col]], unit)
  sampling_rate <- .gpbiom_sampling_rate(interval_summary$median_interval, unit)

  if (is.na(sampling_rate)) {
    warnings <- c(
      warnings,
      "Sampling rate could not be estimated from the selected timebase."
    )
  }

  status <- if (is.na(sampling_rate)) {
    "timebase_detected_without_rate"
  } else {
    "timebase_detected"
  }

  overview <- data.frame(
    n_rows = nrow(data),
    primary_time_column = primary_col,
    primary_time_role = role,
    unit = unit,
    median_interval = interval_summary$median_interval,
    sampling_rate_hz = sampling_rate,
    counter_column = ifelse(is.na(counter), NA_character_, counter),
    n_valid_intervals = interval_summary$n_valid_intervals,
    status = status,
    stringsAsFactors = FALSE
  )

  list(
    overview = overview,
    time_columns = time_columns,
    interval_summary = interval_summary,
    warnings = warnings
  )
}


#' Detect the schema of Gazepoint biometric data
#'
#' Detects likely biometric, timing, marker, and identifying columns in a
#' Gazepoint Biometrics export. The function is deliberately descriptive. It
#' reports what appears to be present and active, but it does not infer emotion,
#' valence, or HRV from ambiguous raw columns.
#'
#' @param data A data frame.
#'
#' @return A list with `overview`, `columns`, `time_columns`, `timebase`,
#'   `name_map`, and `notes`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:5,
#'   TIME = seq(0, by = 1 / 60, length.out = 5),
#'   GSR = c(100, 101, 102, 101, 100),
#'   HR = c(70, 71, 72, 71, 70),
#'   HRV = c(1, 1, 1, 1, 1)
#' )
#' detect_gazepoint_biometric_schema(df)
#'
#' @export
detect_gazepoint_biometric_schema <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  name_map <- standardise_gazepoint_biometric_names(data, rename = FALSE)
  standard_names <- name_map$standard_name

  detected_columns <- .gpbiom_schema_column_table(data, standard_names)
  time_columns <- detect_gazepoint_time_columns(names(data))
  timebase <- detect_gazepoint_biometric_timebase(data)

  has_group <- function(group) {
    any(detected_columns$signal_group == group & detected_columns$present)
  }

  active_group <- function(group) {
    any(detected_columns$signal_group == group & detected_columns$active)
  }

  active_signal_groups <- unique(detected_columns$signal_group[
    detected_columns$active &
      detected_columns$signal_group %in%
      c("gsr_eda", "heart_rate", "ibi", "engagement_dial", "ttl_marker")
  ])

  validation_notes <- c(
    "Treat raw HRV columns as validity or vendor flags unless documentation proves they contain HRV metrics.",
    "IBI-derived HRV summaries should be computed only from genuine IBI/RR interval columns.",
    "GSR/EDA units should not be overclaimed unless the export column or study documentation identifies them."
  )

  status <- if (has_group("timing") &&
                any(c(has_group("gsr_eda"), has_group("heart_rate"),
                      has_group("ibi"), has_group("engagement_dial")))) {
    "biometric_schema_detected"
  } else if (has_group("timing")) {
    "timing_detected_without_clear_biometric_signal"
  } else {
    "limited_schema_detected"
  }

  overview <- data.frame(
    n_rows = nrow(data),
    n_columns = ncol(data),
    time_column_count = nrow(time_columns),
    has_counter = any(standard_names == "CNT"),
    has_gsr_eda = has_group("gsr_eda"),
    has_gsr_conductance = any(standard_names == "GSR_US"),
    has_gsr_resistance = any(standard_names == "GSR_OHMS"),
    has_heart_rate = has_group("heart_rate"),
    has_hrv_flag = any(standard_names == "HRV"),
    has_ibi = has_group("ibi"),
    has_engagement_dial = has_group("engagement_dial"),
    has_ttl_marker = has_group("ttl_marker"),
    active_gsr_eda = active_group("gsr_eda"),
    active_heart_rate = active_group("heart_rate"),
    active_ibi = active_group("ibi"),
    active_engagement_dial = active_group("engagement_dial"),
    active_ttl_marker = active_group("ttl_marker"),
    active_signal_count = length(active_signal_groups),
    status = status,
    stringsAsFactors = FALSE
  )

  list(
    overview = overview,
    columns = detected_columns,
    time_columns = time_columns,
    timebase = timebase,
    name_map = name_map,
    notes = validation_notes
  )
}


.gpbiom_clean_name <- function(x) {
  x <- trimws(as.character(x))
  x <- gsub("\u00B5", "u", x, fixed = TRUE)
  x <- gsub("[^A-Za-z0-9]+", "_", x)
  x <- gsub("_+", "_", x)
  x <- gsub("^_|_$", "", x)
  tolower(x)
}


.gpbiom_canonical_name <- function(cleaned) {
  out <- toupper(cleaned)

  map <- list(
    CNT = c("cnt", "counter", "sample", "sample_index", "sample_number",
            "sample_no", "sample_id"),
    TIME = c("time", "timestamp", "time_s", "time_sec", "timestamp_s",
             "timestamp_sec", "recording_time", "recording_time_s"),
    TIME_MS = c("time_ms", "timestamp_ms", "recording_time_ms"),
    TIME_TICK = c("time_tick", "time_ticks", "tick", "ticks"),
    TRIAL_TIME = c("trial_time", "trial_time_s", "time_in_trial"),
    MEDIA_TIME = c("media_time", "stimulus_time", "stimulus_time_s"),

    USER = c("user", "participant", "participant_id", "subject",
             "subject_id", "id"),
    USER_FILE = c("user_file", "file", "filename", "source_file"),
    MEDIA_ID = c("media_id", "stimulus_id"),
    MEDIA_NAME = c("media_name", "stimulus", "stimulus_name",
                   "image", "video"),
    TRIAL = c("trial", "trial_id", "trial_number"),
    CONDITION = c("condition", "group", "experimental_condition"),

    GSR = c("gsr", "eda", "electrodermal_activity", "skin_conductance",
            "skin_response"),
    GSR_US = c("gsr_us", "gsr_u_s", "gsr_microsiemens",
               "gsr_micro_siemens", "eda_us", "eda_u_s",
               "eda_microsiemens", "conductance", "conductance_us",
               "skin_conductance_us"),
    GSR_OHMS = c("gsr_ohm", "gsr_ohms", "eda_ohm", "eda_ohms",
                 "resistance", "resistance_ohm", "resistance_ohms",
                 "skin_resistance", "skin_resistance_ohms"),

    HR = c("hr", "heart_rate", "heartrate", "bpm", "pulse",
           "pulse_rate"),
    HRV = c("hrv", "hr_valid", "hr_validity", "heart_rate_valid",
            "heart_rate_validity"),
    IBI = c("ibi", "rr", "rr_interval", "rr_intervals",
            "interbeat_interval", "inter_beat_interval",
            "interbeat_interval_ms", "rr_ms"),

    ENGAGEMENT = c("engagement", "engagement_dial", "dial",
                   "dial_value", "engagement_value", "rotary",
                   "self_reported_engagement"),

    TTL = c("ttl", "ttl_value", "ttl_signal", "ttl_marker",
            "event_marker", "marker", "trigger", "digital_marker"),
    EVENT = c("event", "event_name", "event_label")
  )

  for (target in names(map)) {
    out[cleaned %in% map[[target]]] <- target
  }
  ttl_numbered <- grepl("^ttl[0-9]+$", cleaned)
  out[ttl_numbered] <- "TTL"

  ttl_validity <- cleaned %in% c("ttlv", "ttl_valid", "ttl_validity")
  out[ttl_validity] <- "TTLV"
  out
}


.gpbiom_empty_time_columns <- function() {
  data.frame(
    column = character(),
    standard_name = character(),
    role = character(),
    unit_hint = character(),
    confidence = numeric(),
    reason = character(),
    stringsAsFactors = FALSE
  )
}


.gpbiom_choose_primary_time_column <- function(data, time_columns) {
  if (nrow(time_columns) == 0L) {
    return(NA_character_)
  }

  candidates <- time_columns

  usable <- vapply(candidates$column, function(column) {
    column %in% names(data) && is.numeric(data[[column]]) &&
      sum(!is.na(data[[column]])) >= 2L
  }, logical(1))

  candidates <- candidates[usable, , drop = FALSE]

  if (nrow(candidates) == 0L) {
    return(NA_character_)
  }

  preferred_roles <- c("timestamp", "trial_or_media_time", "sample_counter",
                       "candidate_time")

  for (role in preferred_roles) {
    role_candidates <- candidates[candidates$role == role, , drop = FALSE]
    if (nrow(role_candidates) > 0L) {
      return(role_candidates$column[which.max(role_candidates$confidence)])
    }
  }

  candidates$column[which.max(candidates$confidence)]
}


.gpbiom_choose_counter_column <- function(data, time_columns) {
  if (nrow(time_columns) == 0L) {
    return(NA_character_)
  }

  counter_rows <- time_columns[time_columns$role == "sample_counter", ,
                               drop = FALSE]

  if (nrow(counter_rows) == 0L) {
    return(NA_character_)
  }

  usable <- vapply(counter_rows$column, function(column) {
    column %in% names(data) && is.numeric(data[[column]])
  }, logical(1))

  if (!any(usable)) {
    return(NA_character_)
  }

  counter_rows$column[which(usable)[1L]]
}


.gpbiom_time_role <- function(column, time_columns) {
  if (nrow(time_columns) == 0L || !column %in% time_columns$column) {
    return("unknown")
  }

  time_columns$role[match(column, time_columns$column)]
}


.gpbiom_time_unit <- function(column, time_columns, values) {
  if (nrow(time_columns) > 0L && column %in% time_columns$column) {
    hint <- time_columns$unit_hint[match(column, time_columns$column)]

    if (!is.na(hint) && !hint %in% c("unknown", "samples")) {
      return(hint)
    }

    if (!is.na(hint) && identical(hint, "samples")) {
      return("samples")
    }
  }

  numeric_values <- values[!is.na(values)]

  if (length(numeric_values) < 2L || !is.numeric(numeric_values)) {
    return("unknown")
  }

  diffs <- diff(sort(unique(numeric_values)))
  diffs <- diffs[is.finite(diffs) & diffs > 0]

  if (length(diffs) == 0L) {
    return("unknown")
  }

  median_diff <- stats::median(diffs)

  if (is.finite(median_diff) && median_diff > 0 && median_diff < 1) {
    "seconds"
  } else if (is.finite(median_diff) && median_diff >= 1 && median_diff <= 1000) {
    "milliseconds"
  } else {
    "unknown"
  }
}


.gpbiom_interval_summary <- function(values, unit) {
  if (!is.numeric(values)) {
    return(.gpbiom_empty_interval_summary())
  }

  values <- values[!is.na(values)]

  if (length(values) < 2L) {
    return(.gpbiom_empty_interval_summary())
  }

  diffs <- diff(values)
  valid <- diffs[is.finite(diffs) & diffs > 0]

  if (length(valid) == 0L) {
    return(.gpbiom_empty_interval_summary())
  }

  data.frame(
    unit = unit,
    n_intervals = length(diffs),
    n_valid_intervals = length(valid),
    n_zero_or_negative_intervals = sum(is.finite(diffs) & diffs <= 0),
    min_interval = min(valid),
    median_interval = stats::median(valid),
    mean_interval = mean(valid),
    max_interval = max(valid),
    stringsAsFactors = FALSE
  )
}


.gpbiom_empty_interval_summary <- function() {
  data.frame(
    unit = NA_character_,
    n_intervals = 0L,
    n_valid_intervals = 0L,
    n_zero_or_negative_intervals = 0L,
    min_interval = NA_real_,
    median_interval = NA_real_,
    mean_interval = NA_real_,
    max_interval = NA_real_,
    stringsAsFactors = FALSE
  )
}


.gpbiom_sampling_rate <- function(median_interval, unit) {
  if (length(median_interval) != 1L ||
      !is.finite(median_interval) ||
      median_interval <= 0) {
    return(NA_real_)
  }

  if (identical(unit, "seconds")) {
    return(1 / median_interval)
  }

  if (identical(unit, "milliseconds")) {
    return(1000 / median_interval)
  }

  NA_real_
}


.gpbiom_schema_column_table <- function(data, standard_names) {
  groups <- .gpbiom_schema_groups()

  rows <- lapply(seq_along(standard_names), function(i) {
    standard <- standard_names[i]
    column <- names(data)[i]
    values <- data[[i]]

    group <- .gpbiom_schema_group_for_standard(standard, groups)

    non_missing <- sum(!is.na(values))
    unique_non_missing <- length(unique(values[!is.na(values)]))
    active <- non_missing > 0L && unique_non_missing > 0L

    note <- .gpbiom_schema_note(standard)

    data.frame(
      column = column,
      standard_name = standard,
      signal_group = group,
      present = TRUE,
      active = active,
      n_non_missing = non_missing,
      n_unique_non_missing = unique_non_missing,
      interpretation_note = note,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

.gpbiom_schema_group_for_standard <- function(standard, groups) {
  if (standard %in% names(groups)) {
    return(groups[[standard]])
  }

  if (grepl("^TTL(_[0-9]+)?$", standard)) {
    return("ttl_marker")
  }

  if (grepl("^TTLV(_[0-9]+)?$", standard)) {
    return("ttl_validity_flag")
  }

  "other"
}

.gpbiom_schema_groups <- function() {
  c(
    CNT = "timing",
    SAMPLE = "timing",
    SAMPLE_INDEX = "timing",
    TIME = "timing",
    TIME_S = "timing",
    TIMESTAMP_S = "timing",
    TIME_MS = "timing",
    TIMESTAMP_MS = "timing",
    TIME_TICK = "timing",
    TIME_TICKS = "timing",
    TICK = "timing",
    TICKS = "timing",
    TRIAL_TIME = "timing",
    MEDIA_TIME = "timing",
    STIMULUS_TIME = "timing",

    USER = "identifier",
    USER_FILE = "identifier",
    MEDIA_ID = "stimulus",
    MEDIA_NAME = "stimulus",
    TRIAL = "trial",
    CONDITION = "condition",

    GSR = "gsr_eda",
    GSR_US = "gsr_eda",
    GSR_OHMS = "gsr_eda",
    HR = "heart_rate",
    HRV = "heart_rate_validity_flag",
    IBI = "ibi",
    ENGAGEMENT = "engagement_dial",
    TTL = "ttl_marker",
    TTLV = "ttl_validity_flag",
    EVENT = "event"
  )
}


.gpbiom_schema_note <- function(standard_name) {
  if (identical(standard_name, "HRV")) {
    return("Treat as a validity/vendor flag unless documentation proves this column contains HRV metrics.")
  }

  if (identical(standard_name, "IBI")) {
    return("May support IBI/RR-derived HRV summaries if values are genuine inter-beat intervals.")
  }

  if (standard_name %in% c("GSR", "GSR_US", "GSR_OHMS")) {
    return("GSR/EDA unit interpretation depends on export documentation and column naming.")
  }

  if (identical(standard_name, "ENGAGEMENT")) {
    return("Engagement dial/self-report signal; do not interpret as physiological arousal.")
  }

  NA_character_
}
