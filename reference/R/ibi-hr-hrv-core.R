#' Filter implausible Gazepoint IBI values
#'
#' Flags and optionally cleans implausible inter-beat interval values. The helper
#' is conservative and does not remove rows; instead, it returns row-level flags
#' and a cleaned IBI column with implausible values set to `NA`.
#'
#' @param data A Gazepoint biometric data frame.
#' @param ibi_col IBI/RR interval column.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param validity_col Optional validity column.
#' @param unit Unit of the IBI column: `"auto"`, `"ms"`, or `"seconds"`.
#' @param min_ibi_ms Minimum plausible IBI in milliseconds.
#' @param max_ibi_ms Maximum plausible IBI in milliseconds.
#' @param max_change_ms Maximum plausible absolute adjacent IBI change within
#'   group, in milliseconds.
#' @param max_change_prop Maximum plausible proportional adjacent IBI change
#'   within group.
#' @param output_col Name of the cleaned IBI output column.
#'
#' @return A list with `overview`, `data`, `row_flags`, `group_summary`, and
#'   `settings`.
#' @export
filter_gazepoint_ibi_implausible <- function(data,
                                             ibi_col = "IBI",
                                             time_col = NULL,
                                             group_cols = NULL,
                                             validity_col = NULL,
                                             unit = c("auto", "ms", "seconds"),
                                             min_ibi_ms = 300,
                                             max_ibi_ms = 2000,
                                             max_change_ms = 400,
                                             max_change_prop = 0.30,
                                             output_col = "IBI_clean_ms") {
  unit <- match.arg(unit)

  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  data <- as.data.frame(data, stringsAsFactors = FALSE)

  if (!ibi_col %in% names(data)) {
    stop("`ibi_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(data)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.null(validity_col) && !validity_col %in% names(data)) {
    stop("`validity_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_ibi_core_resolve_group_cols(names(data))
  }

  missing_groups <- setdiff(group_cols, names(data))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  gpbiometrics_ibi_core_validate_positive_scalar(min_ibi_ms, "min_ibi_ms")
  gpbiometrics_ibi_core_validate_positive_scalar(max_ibi_ms, "max_ibi_ms")
  gpbiometrics_ibi_core_validate_positive_scalar(max_change_ms, "max_change_ms")
  gpbiometrics_ibi_core_validate_positive_scalar(max_change_prop, "max_change_prop")

  if (max_ibi_ms <= min_ibi_ms) {
    stop("`max_ibi_ms` must be greater than `min_ibi_ms`.", call. = FALSE)
  }

  ibi_raw <- suppressWarnings(as.numeric(data[[ibi_col]]))
  detected_unit <- gpbiometrics_ibi_core_detect_unit(ibi_raw, unit)
  ibi_ms <- if (identical(detected_unit, "seconds")) ibi_raw * 1000 else ibi_raw

  group_id <- gpbiometrics_ibi_core_group_id(data, group_cols)

  flag_nonfinite <- !is.finite(ibi_ms)
  flag_nonpositive <- is.finite(ibi_ms) & ibi_ms <= 0
  flag_too_low <- is.finite(ibi_ms) & ibi_ms < min_ibi_ms
  flag_too_high <- is.finite(ibi_ms) & ibi_ms > max_ibi_ms

  flag_invalid_validity <- rep(FALSE, nrow(data))

  if (!is.null(validity_col)) {
    validity <- suppressWarnings(as.numeric(data[[validity_col]]))
    flag_invalid_validity <- !is.finite(validity) | validity == 0
  }

  change_flags <- gpbiometrics_ibi_core_change_flags(
    ibi_ms = ibi_ms,
    group_id = group_id,
    max_change_ms = max_change_ms,
    max_change_prop = max_change_prop
  )

  flag_implausible <- flag_nonfinite |
    flag_nonpositive |
    flag_too_low |
    flag_too_high |
    flag_invalid_validity |
    change_flags$flag_large_absolute_change |
    change_flags$flag_large_relative_change

  clean_ibi_ms <- ibi_ms
  clean_ibi_ms[flag_implausible] <- NA_real_

  out_data <- data
  out_data[[output_col]] <- clean_ibi_ms

  row_flags <- data.frame(
    row_id = seq_len(nrow(data)),
    group_id = group_id,
    ibi_raw = ibi_raw,
    ibi_ms = ibi_ms,
    ibi_clean_ms = clean_ibi_ms,
    flag_nonfinite = flag_nonfinite,
    flag_nonpositive = flag_nonpositive,
    flag_too_low = flag_too_low,
    flag_too_high = flag_too_high,
    flag_invalid_validity = flag_invalid_validity,
    flag_large_absolute_change = change_flags$flag_large_absolute_change,
    flag_large_relative_change = change_flags$flag_large_relative_change,
    flag_implausible = flag_implausible,
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0) {
    row_flags <- cbind(data[group_cols], row_flags)
  }

  group_summary <- gpbiometrics_ibi_core_group_summary(
    row_flags = row_flags,
    group_cols = group_cols
  )

  overview <- data.frame(
    input_rows = nrow(data),
    ibi_col = ibi_col,
    output_col = output_col,
    detected_unit = detected_unit,
    implausible_rows = sum(flag_implausible, na.rm = TRUE),
    implausible_prop = mean(flag_implausible, na.rm = TRUE),
    clean_rows = sum(is.finite(clean_ibi_ms), na.rm = TRUE),
    group_count = length(unique(group_id)),
    status = if (all(!is.finite(clean_ibi_ms))) {
      "fail_no_clean_ibi_values"
    } else if (any(flag_implausible, na.rm = TRUE)) {
      "warn_implausible_ibi_detected"
    } else {
      "ibi_values_pass"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      data = out_data,
      row_flags = row_flags,
      group_summary = group_summary,
      settings = list(
        ibi_col = ibi_col,
        time_col = time_col,
        group_cols = group_cols,
        validity_col = validity_col,
        unit = unit,
        detected_unit = detected_unit,
        min_ibi_ms = min_ibi_ms,
        max_ibi_ms = max_ibi_ms,
        max_change_ms = max_change_ms,
        max_change_prop = max_change_prop,
        output_col = output_col,
        interpretation_notes = c(
          "IBI filtering flags implausible intervals but does not remove rows automatically.",
          "Thresholds should be reported and may require sensitivity checks.",
          "The Gazepoint HRV column should not be treated as genuine HRV unless independently documented."
        )
      )
    ),
    class = c("gazepoint_ibi_filter", "list")
  )
}

#' Compare Gazepoint HR and IBI-derived heart rate
#'
#' Compares recorded HR against HR derived from genuine IBI/RR intervals using
#' `60000 / IBI_ms`.
#'
#' @param data A Gazepoint biometric data frame or `gazepoint_ibi_filter` object.
#' @param hr_col Heart-rate column in beats per minute.
#' @param ibi_col IBI/RR interval column.
#' @param time_col Optional time/counter column.
#' @param group_cols Optional grouping columns.
#' @param unit Unit of the IBI column: `"auto"`, `"ms"`, or `"seconds"`.
#' @param max_abs_diff_bpm Maximum acceptable absolute HR difference in bpm.
#' @param max_rel_diff_prop Maximum acceptable relative HR difference.
#'
#' @return A list with `overview`, `row_diagnostics`, `group_summary`, and
#'   `settings`.
#' @export
compare_gazepoint_hr_ibi_consistency <- function(data,
                                                 hr_col = "HR",
                                                 ibi_col = "IBI",
                                                 time_col = NULL,
                                                 group_cols = NULL,
                                                 unit = c("auto", "ms", "seconds"),
                                                 max_abs_diff_bpm = 10,
                                                 max_rel_diff_prop = 0.15) {
  unit <- match.arg(unit)

  dat <- gpbiometrics_ibi_core_extract_data(data)

  if (!hr_col %in% names(dat)) {
    stop("`hr_col` was not found in `data`.", call. = FALSE)
  }

  if (!ibi_col %in% names(dat)) {
    stop("`ibi_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_ibi_core_resolve_group_cols(names(dat))
  }

  missing_groups <- setdiff(group_cols, names(dat))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  gpbiometrics_ibi_core_validate_positive_scalar(max_abs_diff_bpm, "max_abs_diff_bpm")
  gpbiometrics_ibi_core_validate_positive_scalar(max_rel_diff_prop, "max_rel_diff_prop")

  hr_observed <- suppressWarnings(as.numeric(dat[[hr_col]]))
  ibi_raw <- suppressWarnings(as.numeric(dat[[ibi_col]]))
  detected_unit <- gpbiometrics_ibi_core_detect_unit(ibi_raw, unit)
  ibi_ms <- if (identical(detected_unit, "seconds")) ibi_raw * 1000 else ibi_raw

  hr_from_ibi <- ifelse(is.finite(ibi_ms) & ibi_ms > 0, 60000 / ibi_ms, NA_real_)

  abs_diff_bpm <- abs(hr_observed - hr_from_ibi)
  rel_diff_prop <- abs_diff_bpm / hr_from_ibi

  flag_missing_pair <- !is.finite(hr_observed) | !is.finite(hr_from_ibi)
  flag_inconsistent <- !flag_missing_pair &
    (abs_diff_bpm > max_abs_diff_bpm | rel_diff_prop > max_rel_diff_prop)

  group_id <- gpbiometrics_ibi_core_group_id(dat, group_cols)

  row_diagnostics <- data.frame(
    row_id = seq_len(nrow(dat)),
    group_id = group_id,
    hr_observed_bpm = hr_observed,
    ibi_ms = ibi_ms,
    hr_from_ibi_bpm = hr_from_ibi,
    abs_diff_bpm = abs_diff_bpm,
    rel_diff_prop = rel_diff_prop,
    flag_missing_pair = flag_missing_pair,
    flag_inconsistent = flag_inconsistent,
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0) {
    row_diagnostics <- cbind(dat[group_cols], row_diagnostics)
  }

  group_summary <- gpbiometrics_hr_ibi_consistency_group_summary(
    row_diagnostics = row_diagnostics,
    group_cols = group_cols
  )

  comparable_rows <- sum(!flag_missing_pair, na.rm = TRUE)
  inconsistent_rows <- sum(flag_inconsistent, na.rm = TRUE)

  overview <- data.frame(
    input_rows = nrow(dat),
    comparable_rows = comparable_rows,
    inconsistent_rows = inconsistent_rows,
    inconsistent_prop = if (comparable_rows > 0) inconsistent_rows / comparable_rows else NA_real_,
    detected_ibi_unit = detected_unit,
    mean_abs_diff_bpm = mean(abs_diff_bpm, na.rm = TRUE),
    median_abs_diff_bpm = stats::median(abs_diff_bpm, na.rm = TRUE),
    group_count = length(unique(group_id)),
    status = if (comparable_rows == 0) {
      "fail_no_comparable_hr_ibi_rows"
    } else if (inconsistent_rows > 0) {
      "warn_hr_ibi_inconsistency_detected"
    } else {
      "hr_ibi_consistency_pass"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      row_diagnostics = row_diagnostics,
      group_summary = group_summary,
      settings = list(
        hr_col = hr_col,
        ibi_col = ibi_col,
        time_col = time_col,
        group_cols = group_cols,
        unit = unit,
        detected_ibi_unit = detected_unit,
        max_abs_diff_bpm = max_abs_diff_bpm,
        max_rel_diff_prop = max_rel_diff_prop,
        interpretation_notes = c(
          "HR derived from IBI is computed as 60000 / IBI_ms.",
          "Discrepancies may reflect smoothing, device timing, missing intervals, or artifacts.",
          "Consistency diagnostics should be used as quality checks rather than automatic exclusions."
        )
      )
    ),
    class = c("gazepoint_hr_ibi_consistency", "list")
  )
}

#' Extract time-domain HRV features from Gazepoint IBI intervals
#'
#' Computes simple time-domain HRV features from genuine IBI/RR intervals. This
#' helper does not use the Gazepoint `HRV` column as an HRV outcome.
#'
#' @param data A Gazepoint biometric data frame or `gazepoint_ibi_filter` object.
#' @param ibi_col IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param unit Unit of the IBI column: `"auto"`, `"ms"`, or `"seconds"`.
#' @param min_intervals Minimum clean intervals required per group.
#' @param min_duration_s Minimum IBI-sequence duration in seconds required before
#'   computed HRV features are treated as fully reportable. Groups below this
#'   duration still return features but receive `warn_short_hrv_duration`.
#' @param diff_threshold_ms Threshold for NN50/pNN50.
#' @param collapse_repeated_intervals Logical. If `TRUE`, consecutive repeated
#'   IBI values are collapsed before HRV features are computed. This is useful
#'   for Gazepoint exports where the same IBI value may be repeated across
#'   multiple gaze-sampling rows until a new interval is available.
#' @param repeated_tolerance_ms Numeric tolerance used when identifying
#'   repeated consecutive IBI values.
#'
#' @return A list with `overview`, `features`, `settings`.
#' @export
extract_gazepoint_hrv_features <- function(data,
                                           ibi_col = "IBI_clean_ms",
                                           group_cols = NULL,
                                           unit = c("auto", "ms", "seconds"),
                                           min_intervals = 3,
                                           min_duration_s = 30,
                                           diff_threshold_ms = 50,
                                           collapse_repeated_intervals = TRUE,
                                           repeated_tolerance_ms = 1e-8) {
  unit <- match.arg(unit)

  dat <- gpbiometrics_ibi_core_extract_data(data)

  if (!ibi_col %in% names(dat)) {
    stop("`ibi_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_ibi_core_resolve_group_cols(names(dat))
  }

  missing_groups <- setdiff(group_cols, names(dat))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  gpbiometrics_ibi_core_validate_positive_scalar(min_intervals, "min_intervals")

  if (!is.numeric(min_duration_s) ||
      length(min_duration_s) != 1 ||
      !is.finite(min_duration_s) ||
      min_duration_s < 0) {
    stop("`min_duration_s` must be a single non-negative finite number.", call. = FALSE)
  }

  gpbiometrics_ibi_core_validate_positive_scalar(diff_threshold_ms, "diff_threshold_ms")

  if (!is.logical(collapse_repeated_intervals) ||
      length(collapse_repeated_intervals) != 1 ||
      is.na(collapse_repeated_intervals)) {
    stop("`collapse_repeated_intervals` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(repeated_tolerance_ms) ||
      length(repeated_tolerance_ms) != 1 ||
      !is.finite(repeated_tolerance_ms) ||
      repeated_tolerance_ms < 0) {
    stop("`repeated_tolerance_ms` must be a single non-negative finite number.", call. = FALSE)
  }

  ibi_raw <- suppressWarnings(as.numeric(dat[[ibi_col]]))
  detected_unit <- gpbiometrics_ibi_core_detect_unit(ibi_raw, unit)
  ibi_ms <- if (identical(detected_unit, "seconds")) ibi_raw * 1000 else ibi_raw

  dat$.ibi_hrv_ms <- ibi_ms
  dat$.group_id <- gpbiometrics_ibi_core_group_id(dat, group_cols)

  group_ids <- unique(dat$.group_id)

  features <- lapply(group_ids, function(group_id) {
    d <- dat[dat$.group_id == group_id, , drop = FALSE]
    x_raw <- d$.ibi_hrv_ms
    x_raw <- x_raw[is.finite(x_raw) & x_raw > 0]

    x <- if (isTRUE(collapse_repeated_intervals)) {
      gpbiometrics_hrv_core_collapse_repeated_intervals(
        ibi_ms = x_raw,
        tolerance_ms = repeated_tolerance_ms
      )
    } else {
      x_raw
    }

    row <- gpbiometrics_hrv_core_features(
      ibi_ms = x,
      min_intervals = min_intervals,
      min_duration_s = min_duration_s,
      diff_threshold_ms = diff_threshold_ms
    )

    row$input_interval_rows <- length(x_raw)
    row$used_intervals_after_collapse <- length(x)
    row$collapsed_repeated_intervals <- isTRUE(collapse_repeated_intervals)
    row$group_id <- group_id

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  features <- do.call(rbind, features)
  rownames(features) <- NULL

  valid_feature_groups <- sum(
    features$feature_status %in% c(
      "features_computed",
      "warn_short_hrv_duration"
    ),
    na.rm = TRUE
  )

  short_duration_groups <- sum(
    features$feature_status == "warn_short_hrv_duration",
    na.rm = TRUE
  )

  overview <- data.frame(
    group_count = nrow(features),
    valid_feature_groups = valid_feature_groups,
    insufficient_interval_groups = sum(features$feature_status == "insufficient_intervals", na.rm = TRUE),
    short_duration_groups = short_duration_groups,
    detected_ibi_unit = detected_unit,
    min_intervals = min_intervals,
    min_duration_s = min_duration_s,
    diff_threshold_ms = diff_threshold_ms,
    status = if (valid_feature_groups == 0) {
      "fail_no_hrv_features_computed"
    } else if (valid_feature_groups < nrow(features)) {
      "warn_some_groups_insufficient_intervals"
    } else if (short_duration_groups > 0) {
      "warn_short_hrv_duration"
    } else {
      "hrv_features_computed"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      features = features,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        unit = unit,
        detected_ibi_unit = detected_unit,
        min_intervals = min_intervals,
        min_duration_s = min_duration_s,
        diff_threshold_ms = diff_threshold_ms,
        collapse_repeated_intervals = collapse_repeated_intervals,
        repeated_tolerance_ms = repeated_tolerance_ms,
        interpretation_notes = c(
          "Features are computed from genuine IBI/RR intervals only.",
          "The Gazepoint HRV column is not used as an HRV outcome.",
          "Short windows provide unstable HRV estimates and should be interpreted cautiously."
        )
      )
    ),
    class = c("gazepoint_hrv_feature_extraction", "list")
  )
}

gpbiometrics_ibi_core_extract_data <- function(data) {
  if (inherits(data, "gazepoint_ibi_filter") && !is.null(data$data)) {
    return(as.data.frame(data$data, stringsAsFactors = FALSE))
  }

  if (is.data.frame(data)) {
    return(as.data.frame(data, stringsAsFactors = FALSE))
  }

  stop("`data` must be a data frame or a `gazepoint_ibi_filter` object.", call. = FALSE)
}

gpbiometrics_ibi_core_resolve_group_cols <- function(names_dat) {
  candidates <- c(
    "source_file",
    "source_participant",
    "USER",
    "USER_FILE",
    "participant",
    "subject",
    "subject_id",
    "MEDIA_ID",
    "MEDIA_NAME",
    "media_id",
    "media_name",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_ibi_core_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_ibi_core_detect_unit <- function(x, unit) {
  if (!identical(unit, "auto")) {
    return(unit)
  }

  finite_x <- x[is.finite(x) & x > 0]

  if (length(finite_x) == 0) {
    return("ms")
  }

  med <- stats::median(finite_x, na.rm = TRUE)

  if (is.finite(med) && med > 0.2 && med < 5) {
    "seconds"
  } else {
    "ms"
  }
}

gpbiometrics_ibi_core_validate_positive_scalar <- function(x, name) {
  if (!is.numeric(x) || length(x) != 1 || !is.finite(x) || x <= 0) {
    stop("`", name, "` must be a single positive finite number.", call. = FALSE)
  }

  invisible(TRUE)
}

gpbiometrics_ibi_core_change_flags <- function(ibi_ms,
                                               group_id,
                                               max_change_ms,
                                               max_change_prop) {
  flag_abs <- rep(FALSE, length(ibi_ms))
  flag_rel <- rep(FALSE, length(ibi_ms))

  groups <- unique(group_id)

  for (g in groups) {
    idx <- which(group_id == g)

    if (length(idx) < 2) {
      next
    }

    x <- ibi_ms[idx]
    prev <- c(NA_real_, utils::head(x, -1))
    diff_abs <- abs(x - prev)
    diff_rel <- diff_abs / prev

    local_abs <- is.finite(diff_abs) & diff_abs > max_change_ms
    local_rel <- is.finite(diff_rel) & diff_rel > max_change_prop

    flag_abs[idx] <- local_abs
    flag_rel[idx] <- local_rel
  }

  list(
    flag_large_absolute_change = flag_abs,
    flag_large_relative_change = flag_rel
  )
}

gpbiometrics_ibi_core_group_summary <- function(row_flags,
                                                group_cols) {
  if (nrow(row_flags) == 0) {
    return(data.frame())
  }

  group_ids <- unique(row_flags$group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- row_flags[row_flags$group_id == group_id, , drop = FALSE]
    clean <- d$ibi_clean_ms[is.finite(d$ibi_clean_ms)]

    row <- data.frame(
      group_id = group_id,
      rows = nrow(d),
      implausible_rows = sum(d$flag_implausible, na.rm = TRUE),
      implausible_prop = mean(d$flag_implausible, na.rm = TRUE),
      clean_rows = length(clean),
      mean_clean_ibi_ms = if (length(clean) > 0) mean(clean, na.rm = TRUE) else NA_real_,
      median_clean_ibi_ms = if (length(clean) > 0) stats::median(clean, na.rm = TRUE) else NA_real_,
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_hr_ibi_consistency_group_summary <- function(row_diagnostics,
                                                          group_cols) {
  group_ids <- unique(row_diagnostics$group_id)

  out <- lapply(group_ids, function(group_id) {
    d <- row_diagnostics[row_diagnostics$group_id == group_id, , drop = FALSE]
    comparable <- !d$flag_missing_pair

    row <- data.frame(
      group_id = group_id,
      rows = nrow(d),
      comparable_rows = sum(comparable, na.rm = TRUE),
      inconsistent_rows = sum(d$flag_inconsistent, na.rm = TRUE),
      inconsistent_prop = if (sum(comparable, na.rm = TRUE) > 0) {
        sum(d$flag_inconsistent, na.rm = TRUE) / sum(comparable, na.rm = TRUE)
      } else {
        NA_real_
      },
      median_abs_diff_bpm = stats::median(d$abs_diff_bpm, na.rm = TRUE),
      mean_abs_diff_bpm = mean(d$abs_diff_bpm, na.rm = TRUE),
      stringsAsFactors = FALSE
    )

    if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
      row <- cbind(d[1, group_cols, drop = FALSE], row)
    }

    row
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_hrv_core_collapse_repeated_intervals <- function(ibi_ms,
                                                              tolerance_ms) {
  if (length(ibi_ms) <= 1) {
    return(ibi_ms)
  }

  diff_value <- abs(diff(ibi_ms))
  keep <- c(TRUE, diff_value > tolerance_ms)

  ibi_ms[keep]
}

gpbiometrics_hrv_core_features <- function(ibi_ms,
                                           min_intervals,
                                           min_duration_s,
                                           diff_threshold_ms) {
  n_intervals <- length(ibi_ms)

  if (n_intervals < min_intervals) {
    return(data.frame(
      n_intervals = n_intervals,
      duration_s = if (n_intervals > 0) sum(ibi_ms, na.rm = TRUE) / 1000 else NA_real_,
      min_duration_s = min_duration_s,
      mean_ibi_ms = NA_real_,
      median_ibi_ms = NA_real_,
      mean_hr_bpm = NA_real_,
      sdnn_ms = NA_real_,
      rmssd_ms = NA_real_,
      sdsd_ms = NA_real_,
      nn50 = NA_integer_,
      pnn50 = NA_real_,
      cvnn = NA_real_,
      min_ibi_ms = if (n_intervals > 0) min(ibi_ms, na.rm = TRUE) else NA_real_,
      max_ibi_ms = if (n_intervals > 0) max(ibi_ms, na.rm = TRUE) else NA_real_,
      feature_status = "insufficient_intervals",
      stringsAsFactors = FALSE
    ))
  }

  diff_ibi <- diff(ibi_ms)

  duration_s <- sum(ibi_ms, na.rm = TRUE) / 1000

  data.frame(
    n_intervals = n_intervals,
    duration_s = duration_s,
    min_duration_s = min_duration_s,
    mean_ibi_ms = mean(ibi_ms, na.rm = TRUE),
    median_ibi_ms = stats::median(ibi_ms, na.rm = TRUE),
    mean_hr_bpm = mean(60000 / ibi_ms, na.rm = TRUE),
    sdnn_ms = if (n_intervals > 1) stats::sd(ibi_ms, na.rm = TRUE) else NA_real_,
    rmssd_ms = if (length(diff_ibi) > 0) sqrt(mean(diff_ibi^2, na.rm = TRUE)) else NA_real_,
    sdsd_ms = if (length(diff_ibi) > 1) stats::sd(diff_ibi, na.rm = TRUE) else NA_real_,
    nn50 = sum(abs(diff_ibi) > diff_threshold_ms, na.rm = TRUE),
    pnn50 = if (length(diff_ibi) > 0) {
      sum(abs(diff_ibi) > diff_threshold_ms, na.rm = TRUE) / length(diff_ibi)
    } else {
      NA_real_
    },
    cvnn = stats::sd(ibi_ms, na.rm = TRUE) / mean(ibi_ms, na.rm = TRUE),
    min_ibi_ms = min(ibi_ms, na.rm = TRUE),
    max_ibi_ms = max(ibi_ms, na.rm = TRUE),
    feature_status = if (is.finite(duration_s) && duration_s < min_duration_s) {
      "warn_short_hrv_duration"
    } else {
      "features_computed"
    },
    stringsAsFactors = FALSE
  )
}
