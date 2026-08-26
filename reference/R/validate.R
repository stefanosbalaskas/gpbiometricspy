#' Validate a Gazepoint Biometrics export
#'
#' Performs a conservative validation of a Gazepoint Biometrics table or CSV
#' file. The function checks whether known biometric columns are present,
#' whether biometric channels appear active, whether common time/synchronisation
#' columns are available, and whether obvious structural issues are present.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param require_active_signal Logical. If `TRUE`, validation reports a warning
#'   when no active GSR/EDA, heart-rate, or engagement-dial channel is detected.
#'
#' @return A list with `overview`, `columns`, `active_channels`, and `issues`.
#'   The returned object has class `"gazepoint_biometrics_validation"`.
#'
#' @export
validate_gazepoint_biometrics <- function(data, require_active_signal = FALSE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  cols <- check_gazepoint_biometric_columns(dat)
  active <- detect_active_biometric_channels(dat)

  biometric_signals <- c("gsr_eda", "heart_rate", "engagement_dial")
  biometric_or_marker_signals <- c(biometric_signals, "ttl_marker")

  has_known_biometric_columns <- any(
    cols$present[cols$signal %in% biometric_or_marker_signals]
  )

  active_signal_count <- sum(
    active$active[active$signal %in% biometric_signals],
    na.rm = TRUE
  )

  time_columns <- c("CNT", "TIME", "TIME_TICK")
  present_time_columns <- intersect(time_columns, names(dat))

  empty_column_names <- names(dat) == "" | is.na(names(dat))

  issues <- empty_validation_issues()

  if (nrow(dat) == 0L) {
    issues <- add_validation_issue(
      issues,
      issue = "empty_data",
      severity = "error",
      details = "The data contain zero rows."
    )
  }

  if (any(empty_column_names)) {
    issues <- add_validation_issue(
      issues,
      issue = "empty_column_names",
      severity = "warning",
      details = paste0(sum(empty_column_names), " column name(s) are empty or missing.")
    )
  }

  if (!has_known_biometric_columns) {
    issues <- add_validation_issue(
      issues,
      issue = "no_known_biometric_columns",
      severity = "error",
      details = "No known Gazepoint Biometrics columns were detected."
    )
  }

  if (length(present_time_columns) == 0L) {
    issues <- add_validation_issue(
      issues,
      issue = "no_time_columns",
      severity = "warning",
      details = "No common Gazepoint time columns were detected: CNT, TIME, or TIME_TICK."
    )
  }

  if (isTRUE(require_active_signal) && active_signal_count == 0L) {
    issues <- add_validation_issue(
      issues,
      issue = "no_active_biometric_signal",
      severity = "warning",
      details = "Biometric columns are present, but no active GSR/EDA, heart-rate, or engagement-dial signal was detected."
    )
  }

  overview <- data.frame(
    n_rows = nrow(dat),
    n_columns = ncol(dat),
    known_biometric_columns = sum(cols$present[cols$signal %in% biometric_or_marker_signals]),
    active_signal_count = active_signal_count,
    present_time_columns = paste(present_time_columns, collapse = ","),
    issue_count = nrow(issues),
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    columns = cols,
    active_channels = active,
    issues = issues
  )

  class(out) <- c("gazepoint_biometrics_validation", "list")
  out
}


#' Audit missingness in Gazepoint biometric channels
#'
#' Summarises missingness and zero values for Gazepoint biometric columns. This
#' is useful because Gazepoint exports may contain biometric columns even when a
#' channel was inactive or invalid during recording.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param columns Optional character vector of columns to audit. If `NULL`,
#'   known present Gazepoint biometric, TTL, and validity columns are audited.
#'
#' @return A data frame with one row per audited column.
#'
#' @export
audit_gazepoint_biometric_missingness <- function(data, columns = NULL) {
  dat <- coerce_gazepoint_biometrics_data(data)

  cols <- check_gazepoint_biometric_columns(dat)

  if (is.null(columns)) {
    columns <- cols$column[
      cols$present &
        cols$signal %in% c("gsr_eda", "heart_rate", "engagement_dial", "ttl_marker")
    ]
  }

  if (!is.character(columns)) {
    stop("`columns` must be a character vector or NULL.", call. = FALSE)
  }

  columns <- intersect(columns, names(dat))

  if (length(columns) == 0L) {
    return(data.frame(
      column = character(0),
      signal = character(0),
      role = character(0),
      n_rows = integer(0),
      missing_rows = integer(0),
      missing_pct = numeric(0),
      zero_rows = integer(0),
      zero_pct = numeric(0),
      min_value = numeric(0),
      max_value = numeric(0),
      stringsAsFactors = FALSE
    ))
  }

  out <- lapply(columns, function(column) {
    x <- dat[[column]]
    x_chr <- trimws(as.character(x))
    x_num <- as_numeric_safe(x)

    missing <- is.na(x) | x_chr == ""
    zero <- !is.na(x_num) & x_num == 0

    non_missing_numeric <- x_num[!is.na(x_num)]

    signal <- cols$signal[match(column, cols$column)]
    role <- cols$role[match(column, cols$column)]

    data.frame(
      column = column,
      signal = ifelse(is.na(signal), "unknown", signal),
      role = ifelse(is.na(role), "unknown", role),
      n_rows = nrow(dat),
      missing_rows = sum(missing),
      missing_pct = safe_pct(sum(missing), nrow(dat)),
      zero_rows = sum(zero),
      zero_pct = safe_pct(sum(zero), nrow(dat)),
      min_value = ifelse(
        length(non_missing_numeric) > 0L,
        min(non_missing_numeric, na.rm = TRUE),
        NA_real_
      ),
      max_value = ifelse(
        length(non_missing_numeric) > 0L,
        max(non_missing_numeric, na.rm = TRUE),
        NA_real_
      ),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL
  out
}


coerce_gazepoint_biometrics_data <- function(data) {
  if (is.character(data) && length(data) == 1L && nzchar(data)) {
    return(import_gazepoint_biometrics(data))
  }

  if (is.data.frame(data)) {
    return(data)
  }

  stop(
    "`data` must be a data frame or a single path to a Gazepoint CSV export.",
    call. = FALSE
  )
}


empty_validation_issues <- function() {
  data.frame(
    issue = character(0),
    severity = character(0),
    details = character(0),
    stringsAsFactors = FALSE
  )
}


add_validation_issue <- function(issues, issue, severity, details) {
  rbind(
    issues,
    data.frame(
      issue = issue,
      severity = severity,
      details = details,
      stringsAsFactors = FALSE
    )
  )
}


safe_pct <- function(numerator, denominator) {
  if (is.na(denominator) || denominator == 0L) {
    return(NA_real_)
  }

  100 * numerator / denominator
}
