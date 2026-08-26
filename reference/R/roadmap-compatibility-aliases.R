
# Roadmap compatibility aliases and lightweight discoverability wrappers.

.gp_alias_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_alias_guess_time_col <- function(data, required = FALSE) {
  candidates <- c("time_s", "time", "timestamp", "event_time", "MSTIMER", "TIME", "CNT")
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify a time column. Supply `time_col` explicitly.", call. = FALSE)
  }

  NULL
}

.gp_alias_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(time)
  }

  d <- diff(time[is.finite(time)])
  d <- d[is.finite(d) & d > 0]

  if (!length(d)) {
    return(time)
  }

  med_d <- stats::median(d, na.rm = TRUE)

  if (is.finite(med_d) && med_d > 5) {
    time / 1000
  } else {
    time
  }
}

.gp_alias_guess_pupil_cols <- function(data) {
  nms <- names(data)
  lower <- tolower(nms)

  hits <- grepl("pupil", lower) |
    lower %in% tolower(c("LPD", "RPD", "LPMM", "RPMM", "left_pupil", "right_pupil"))

  nms[hits & vapply(data, is.numeric, logical(1))]
}

.gp_alias_check_cols <- function(data, cols) {
  cols <- cols[!is.na(cols) & nzchar(cols)]
  missing <- setdiff(cols, names(data))

  if (length(missing)) {
    stop("Missing columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }

  invisible(TRUE)
}

.gp_alias_interpolate_one <- function(x,
                                      time = NULL,
                                      mask = NULL,
                                      max_gap_s = NULL,
                                      method = "linear") {
  x <- suppressWarnings(as.numeric(x))

  if (is.null(mask)) {
    mask <- is.na(x) | !is.finite(x)
  } else {
    mask <- as.logical(mask) | is.na(x) | !is.finite(x)
    mask[is.na(mask)] <- FALSE
  }

  if (!any(mask)) {
    return(list(value = x, was_interpolated = rep(FALSE, length(x))))
  }

  good <- !mask & is.finite(x)

  if (sum(good) < 2L) {
    return(list(value = x, was_interpolated = rep(FALSE, length(x))))
  }

  runs <- rle(mask)
  ends <- cumsum(runs$lengths)
  starts <- ends - runs$lengths + 1L
  missing_runs <- which(runs$values)

  eligible <- rep(FALSE, length(x))

  if (!is.null(time)) {
    time <- .gp_alias_time_seconds(time)
  }

  for (rr in missing_runs) {
    s <- starts[rr]
    e <- ends[rr]

    internal <- s > 1L && e < length(x) && good[s - 1L] && good[e + 1L]

    if (!internal) {
      next
    }

    gap_ok <- TRUE

    if (!is.null(max_gap_s) && !is.null(time) &&
      is.finite(time[s]) && is.finite(time[e])) {
      d <- diff(time[is.finite(time)])
      d <- d[d > 0]
      med_d <- if (length(d)) stats::median(d, na.rm = TRUE) else NA_real_
      duration <- max(0, time[e] - time[s]) + ifelse(is.finite(med_d), med_d, 0)
      gap_ok <- is.finite(duration) && duration <= max_gap_s
    }

    if (gap_ok) {
      eligible[s:e] <- TRUE
    }
  }

  out <- x

  if (any(eligible)) {
    index <- seq_along(x)

    interp <- stats::approx(
      x = index[good],
      y = x[good],
      xout = index,
      method = method,
      rule = 1,
      ties = mean
    )$y

    out[eligible] <- interp[eligible]
  }

  list(value = out, was_interpolated = eligible)
}

#' Standardize Gazepoint column names
#'
#' Compatibility alias for `standardize_gazepoint_column_names()`. This exact
#' name is provided for users who search for a shorter column-standardization
#' helper.
#'
#' @param data Data frame or supported object passed to
#'   `standardize_gazepoint_column_names()`.
#' @param ... Additional arguments passed to
#'   `standardize_gazepoint_column_names()`.
#'
#' @return Standardized data object returned by
#'   `standardize_gazepoint_column_names()`.
#' @export
standardize_gazepoint_columns <- function(data, ...) {
  if (!exists("standardize_gazepoint_column_names", mode = "function")) {
    stop("`standardize_gazepoint_column_names()` is not available.", call. = FALSE)
  }

  standardize_gazepoint_column_names(data, ...)
}

#' Validate a Gazepoint-format data frame
#'
#' Lightweight format validator for Gazepoint-style biometric exports. This
#' wrapper checks required and optional columns and, when available, attaches
#' schema and audit outputs from existing package helpers.
#'
#' @param data Data frame to validate.
#' @param required_cols Required column names.
#' @param optional_cols Optional column names to report as present or absent.
#' @param expected_modalities Optional expected modalities passed to
#'   `audit_gazepoint_biometrics_file()` when available.
#' @param standardize If TRUE, standardize column names before validation.
#' @param strict If TRUE, audit warnings make the returned `valid` field FALSE.
#' @param ... Reserved for future extensions.
#'
#' @return Object of class `gazepoint_format_validation`.
#' @export
validate_gazepoint_format <- function(data,
                                      required_cols = NULL,
                                      optional_cols = NULL,
                                      expected_modalities = NULL,
                                      standardize = FALSE,
                                      strict = FALSE,
                                      ...) {
  .gp_alias_check_df(data)

  original_names <- names(data)

  if (isTRUE(standardize) && exists("standardize_gazepoint_column_names", mode = "function")) {
    data <- standardize_gazepoint_column_names(data)
  }

  missing_required <- setdiff(required_cols, names(data))
  present_required <- intersect(required_cols, names(data))
  present_optional <- intersect(optional_cols, names(data))
  missing_optional <- setdiff(optional_cols, names(data))

  schema <- NULL
  schema_error <- NULL

  if (exists("audit_gazepoint_export_schema", mode = "function")) {
    schema <- tryCatch(
      audit_gazepoint_export_schema(data),
      error = function(e) {
        schema_error <<- conditionMessage(e)
        NULL
      }
    )
  }

  audit <- NULL
  audit_warnings <- character()

  if (exists("audit_gazepoint_biometrics_file", mode = "function")) {
    audit <- tryCatch(
      audit_gazepoint_biometrics_file(
        data = data,
        expected_modalities = expected_modalities %||% character(),
        standardize = FALSE
      ),
      error = function(e) NULL
    )

    if (is.list(audit) && length(audit$warnings)) {
      audit_warnings <- audit$warnings
    }
  }

  valid <- length(missing_required) == 0L && is.null(schema_error)

  if (isTRUE(strict) && length(audit_warnings)) {
    valid <- FALSE
  }

  out <- list(
    valid = valid,
    n_rows = nrow(data),
    n_cols = ncol(data),
    original_columns = original_names,
    current_columns = names(data),
    required = data.frame(
      column = required_cols,
      present = required_cols %in% names(data),
      stringsAsFactors = FALSE
    ),
    optional = data.frame(
      column = optional_cols,
      present = optional_cols %in% names(data),
      stringsAsFactors = FALSE
    ),
    missing_required = missing_required,
    present_required = present_required,
    missing_optional = missing_optional,
    present_optional = present_optional,
    schema = schema,
    schema_error = schema_error,
    audit = audit,
    warnings = audit_warnings
  )

  class(out) <- c("gazepoint_format_validation", "list")
  out
}

#' Clean Gazepoint pupil data
#'
#' Compatibility helper for users searching for a short pupil-cleaning function.
#' By default it applies transparent blink/dropout interpolation using
#' `interpolate_gazepoint_pupil_blinks()`. Set `prefer_existing = TRUE` to
#' delegate to `clean_gazepoint_pupil_signal()` when compatible with the
#' supplied arguments.
#'
#' @param data Data frame containing pupil columns.
#' @param pupil_cols Pupil columns to clean. If omitted, common pupil columns are
#'   detected.
#' @param time_col Optional time column.
#' @param blink_col Optional logical/numeric blink mask column.
#' @param max_gap_s Optional maximum interpolated gap duration in seconds.
#' @param method Interpolation method passed to `stats::approx()`.
#' @param suffix Suffix for cleaned pupil columns.
#' @param prefer_existing If TRUE, first try `clean_gazepoint_pupil_signal()`.
#' @param ... Additional arguments passed to the preferred existing cleaner when
#'   `prefer_existing = TRUE`.
#'
#' @return Data frame with cleaned pupil columns and interpolation flags.
#' @export
clean_gazepoint_pupil <- function(data,
                                  pupil_cols = NULL,
                                  time_col = NULL,
                                  blink_col = NULL,
                                  max_gap_s = NULL,
                                  method = c("linear", "constant"),
                                  suffix = "_clean",
                                  prefer_existing = FALSE,
                                  ...) {
  method <- match.arg(method)

  if (isTRUE(prefer_existing) && exists("clean_gazepoint_pupil_signal", mode = "function")) {
    existing <- tryCatch(
      clean_gazepoint_pupil_signal(data, ...),
      error = function(e) NULL
    )

    if (!is.null(existing)) {
      return(existing)
    }
  }

  interpolate_gazepoint_pupil_blinks(
    data = data,
    pupil_cols = pupil_cols,
    time_col = time_col,
    blink_col = blink_col,
    max_gap_s = max_gap_s,
    method = method,
    suffix = suffix
  )
}

#' Interpolate Gazepoint pupil blink/dropout spans
#'
#' Interpolates internal blink or dropout spans in pupil columns using
#' transparent, auditable rules. Leading/trailing gaps are not interpolated.
#'
#' @param data Data frame containing pupil columns.
#' @param pupil_cols Pupil columns to interpolate. If omitted, common pupil
#'   columns are detected.
#' @param time_col Optional time column.
#' @param blink_col Optional logical/numeric blink mask column.
#' @param max_gap_s Optional maximum interpolated gap duration in seconds.
#' @param method Interpolation method passed to `stats::approx()`.
#' @param suffix Suffix for interpolated pupil columns.
#'
#' @return Data frame with interpolated pupil columns and audit flags.
#' @export
interpolate_gazepoint_pupil_blinks <- function(data,
                                               pupil_cols = NULL,
                                               time_col = NULL,
                                               blink_col = NULL,
                                               max_gap_s = NULL,
                                               method = c("linear", "constant"),
                                               suffix = "_interp") {
  method <- match.arg(method)
  .gp_alias_check_df(data)

  if (is.null(pupil_cols)) {
    pupil_cols <- .gp_alias_guess_pupil_cols(data)
  }

  if (!length(pupil_cols)) {
    stop("No pupil columns were supplied or detected.", call. = FALSE)
  }

  .gp_alias_check_cols(data, pupil_cols)

  if (is.null(time_col)) {
    time_col <- .gp_alias_guess_time_col(data, required = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(data)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.null(blink_col) && !blink_col %in% names(data)) {
    stop("`blink_col` was not found in `data`.", call. = FALSE)
  }

  time <- if (!is.null(time_col)) .gp_alias_time_seconds(data[[time_col]]) else NULL
  blink <- if (!is.null(blink_col)) as.logical(data[[blink_col]]) else NULL

  out <- data

  for (cc in pupil_cols) {
    z <- .gp_alias_interpolate_one(
      x = data[[cc]],
      time = time,
      mask = blink,
      max_gap_s = max_gap_s,
      method = method
    )

    clean_col <- paste0(cc, suffix)
    flag_col <- paste0(cc, "_was_interpolated")

    out[[clean_col]] <- z$value
    out[[flag_col]] <- z$was_interpolated
  }

  attr(out, "gazepoint_pupil_interpolation") <- list(
    pupil_cols = pupil_cols,
    time_col = time_col,
    blink_col = blink_col,
    max_gap_s = max_gap_s,
    method = method,
    suffix = suffix
  )

  out
}

#' Estimate respiration from PPG
#'
#' Compatibility alias for `estimate_gazepoint_respiration_from_ppg()`. The
#' returned value should be interpreted as an exploratory PPG-derived
#' respiration-rate estimate, not as a direct respiratory measurement.
#'
#' @param data Data frame or numeric PPG vector.
#' @param ... Additional arguments passed to
#'   `estimate_gazepoint_respiration_from_ppg()`.
#'
#' @return Output from `estimate_gazepoint_respiration_from_ppg()`.
#' @export
respiration_from_ppg <- function(data, ...) {
  if (!exists("estimate_gazepoint_respiration_from_ppg", mode = "function")) {
    stop("`estimate_gazepoint_respiration_from_ppg()` is not available.", call. = FALSE)
  }

  estimate_gazepoint_respiration_from_ppg(data, ...)
}

#' Prepare Gazepoint data for mixed-model analysis
#'
#' Lightweight mixed-model preparation helper for Gazepoint-derived trial-level,
#' event-locked, AOI, or physiology summaries. It coerces identifier and
#' condition columns to factors, optionally drops rows with missing outcomes,
#' and adds centered or standardized numeric predictors.
#'
#' @param data Data frame to prepare.
#' @param outcome_cols Outcome columns used for optional missing-row removal.
#' @param participant_col Optional participant identifier column.
#' @param trial_col Optional trial/item identifier column.
#' @param condition_cols Optional condition columns.
#' @param factor_cols Additional columns to coerce to factors.
#' @param numeric_cols Numeric predictors to center or scale. If omitted, all
#'   numeric columns except outcomes are considered.
#' @param center_numeric If TRUE, add centered numeric columns using suffix
#'   `"_c"`.
#' @param scale_numeric If TRUE, add standardized numeric columns using suffix
#'   `"_z"`.
#' @param drop_missing_outcomes If TRUE, remove rows with missing/non-finite
#'   values in `outcome_cols`.
#' @param ... Reserved for future extensions.
#'
#' @return Data frame of class `gazepoint_mixed_model_data`.
#' @export
prepare_gazepoint_mixed_model_data <- function(data,
                                               outcome_cols = NULL,
                                               participant_col = NULL,
                                               trial_col = NULL,
                                               condition_cols = NULL,
                                               factor_cols = NULL,
                                               numeric_cols = NULL,
                                               center_numeric = TRUE,
                                               scale_numeric = FALSE,
                                               drop_missing_outcomes = TRUE,
                                               ...) {
  .gp_alias_check_df(data)

  id_factor_cols <- unique(c(participant_col, trial_col, condition_cols, factor_cols))
  .gp_alias_check_cols(data, c(outcome_cols, id_factor_cols, numeric_cols))

  out <- data

  if (isTRUE(drop_missing_outcomes) && length(outcome_cols)) {
    keep <- rep(TRUE, nrow(out))

    for (cc in outcome_cols) {
      if (is.numeric(out[[cc]])) {
        keep <- keep & is.finite(out[[cc]])
      } else {
        keep <- keep & !is.na(out[[cc]])
      }
    }

    out <- out[keep, , drop = FALSE]
  }

  for (cc in id_factor_cols) {
    if (!is.null(cc) && cc %in% names(out)) {
      out[[cc]] <- as.factor(out[[cc]])
    }
  }

  if (is.null(numeric_cols)) {
    numeric_cols <- names(out)[vapply(out, is.numeric, logical(1))]
    numeric_cols <- setdiff(numeric_cols, outcome_cols)
  }

  numeric_cols <- intersect(numeric_cols, names(out))

  for (cc in numeric_cols) {
    x <- suppressWarnings(as.numeric(out[[cc]]))

    if (isTRUE(center_numeric)) {
      out[[paste0(cc, "_c")]] <- x - mean(x, na.rm = TRUE)
    }

    if (isTRUE(scale_numeric)) {
      sx <- stats::sd(x, na.rm = TRUE)
      out[[paste0(cc, "_z")]] <- if (is.finite(sx) && sx > 0) {
        (x - mean(x, na.rm = TRUE)) / sx
      } else {
        NA_real_
      }
    }
  }

  attr(out, "gazepoint_mixed_model_data") <- list(
    outcome_cols = outcome_cols,
    participant_col = participant_col,
    trial_col = trial_col,
    condition_cols = condition_cols,
    factor_cols = id_factor_cols,
    numeric_cols = numeric_cols,
    center_numeric = center_numeric,
    scale_numeric = scale_numeric,
    drop_missing_outcomes = drop_missing_outcomes
  )

  class(out) <- c("gazepoint_mixed_model_data", class(out))
  out
}

`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

