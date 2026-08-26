#' Standardise SCR or SCL using intra-individual z-scoring
#'
#' Adds a within-participant z-scored version of a signal column. This is a
#' lightweight compatibility wrapper around the package's more general
#' within-unit standardisation helper.
#'
#' @param dat A data frame containing SCR, SCL, or another biometric signal.
#' @param signal_col Signal column to standardise.
#' @param group_col Participant or unit column.
#' @param suffix Suffix for the output column.
#' @param min_valid Minimum finite observations required within each group.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with an added z-scored column.
#' @export
standardise_gazepoint_zscore <- function(dat,
                                         signal_col = "SCR_Amplitude",
                                         group_col = "source_participant",
                                         suffix = "_Z",
                                         min_valid = 2,
                                         overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!is.character(signal_col) || length(signal_col) != 1 || is.na(signal_col)) {
    stop("`signal_col` must be a single column name.", call. = FALSE)
  }

  if (!is.character(group_col) || length(group_col) != 1 || is.na(group_col)) {
    stop("`group_col` must be a single column name.", call. = FALSE)
  }

  out <- standardize_gazepoint_biometrics_within_unit(
    data = dat,
    signal_cols = signal_col,
    unit_cols = group_col,
    suffix = suffix,
    center = TRUE,
    scale = TRUE,
    min_valid = min_valid,
    zero_sd_action = "NA",
    overwrite = overwrite
  )

  attr(out, "standardization_method") <- "intra_individual_z_score"
  attr(out, "interpretation") <- paste(
    "Intra-individual z-scoring expresses each observation relative to the participant's own mean and standard deviation.",
    "It supports within-participant comparison but removes between-participant level and scale differences."
  )

  out
}

#' @rdname standardise_gazepoint_zscore
#' @export
standardize_gazepoint_zscore <- function(dat,
                                         signal_col = "SCR_Amplitude",
                                         group_col = "source_participant",
                                         suffix = "_Z",
                                         min_valid = 2,
                                         overwrite = FALSE) {
  standardise_gazepoint_zscore(
    dat = dat,
    signal_col = signal_col,
    group_col = group_col,
    suffix = suffix,
    min_valid = min_valid,
    overwrite = overwrite
  )
}

#' Standardise SCR or SCL using within-participant range correction
#'
#' Adds a range-corrected signal column using `(x - min) / (max - min)` within
#' participant or another grouping unit. This expresses each value as a
#' proportion of the observed within-unit range.
#'
#' @param dat A data frame containing SCR, SCL, or another biometric signal.
#' @param signal_col Signal column to range-correct.
#' @param group_col Participant or unit column.
#' @param suffix Suffix for the output column.
#' @param min_valid Minimum finite observations required within each group.
#' @param zero_range_action What to do when max equals min: `"NA"` or `"zero"`.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with an added range-corrected column.
#' @export
standardise_gazepoint_range_correction <- function(dat,
                                                   signal_col,
                                                   group_col = "source_participant",
                                                   suffix = "_Range_Corrected",
                                                   min_valid = 2,
                                                   zero_range_action = c("NA", "zero"),
                                                   overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  zero_range_action <- match.arg(zero_range_action)

  if (!is.character(signal_col) || length(signal_col) != 1 || is.na(signal_col)) {
    stop("`signal_col` must be a single column name.", call. = FALSE)
  }

  if (!signal_col %in% names(dat)) {
    stop("Column `", signal_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.character(group_col) || length(group_col) != 1 || is.na(group_col)) {
    stop("`group_col` must be a single column name.", call. = FALSE)
  }

  if (!group_col %in% names(dat)) {
    stop("Column `", group_col, "` was not found in `dat`.", call. = FALSE)
  }

  output_col <- paste0(signal_col, suffix)

  if (!isTRUE(overwrite) && output_col %in% names(dat)) {
    stop(
      "Output column `", output_col, "` already exists. Use `overwrite = TRUE` to replace it.",
      call. = FALSE
    )
  }

  out <- dat
  out[[output_col]] <- NA_real_

  groups <- split(seq_len(nrow(dat)), dat[[group_col]], drop = TRUE)

  parameter_rows <- lapply(names(groups), function(unit_id) {
    idx <- groups[[unit_id]]
    x <- dat[[signal_col]][idx]
    finite_x <- x[is.finite(x)]

    n_finite <- length(finite_x)

    min_val <- NA_real_
    max_val <- NA_real_
    range_val <- NA_real_
    status <- "range_corrected"

    if (n_finite < min_valid) {
      status <- "insufficient_finite_rows"
      out[[output_col]][idx] <<- NA_real_
    } else {
      min_val <- min(finite_x)
      max_val <- max(finite_x)
      range_val <- max_val - min_val

      if (!is.finite(range_val) || range_val == 0) {
        status <- "zero_or_missing_range"

        if (identical(zero_range_action, "zero")) {
          corrected <- rep(NA_real_, length(x))
          corrected[is.finite(x)] <- 0
          out[[output_col]][idx] <<- corrected
        } else {
          out[[output_col]][idx] <<- NA_real_
        }
      } else {
        corrected <- (x - min_val) / range_val
        corrected[!is.finite(corrected)] <- NA_real_
        out[[output_col]][idx] <<- corrected
      }
    }

    data.frame(
      unit_id = as.character(unit_id),
      signal_col = signal_col,
      output_col = output_col,
      n_rows = length(idx),
      n_finite = n_finite,
      min_val = min_val,
      max_val = max_val,
      range_val = range_val,
      status = status,
      stringsAsFactors = FALSE
    )
  })

  parameters <- do.call(rbind, parameter_rows)
  rownames(parameters) <- NULL

  summary <- data.frame(
    input_rows = nrow(dat),
    group_count = length(groups),
    signal_col = signal_col,
    output_col = output_col,
    corrected_groups = sum(parameters$status == "range_corrected"),
    problem_groups = sum(parameters$status != "range_corrected"),
    status = if (all(parameters$status == "range_corrected")) {
      "range_correction_complete"
    } else if (any(parameters$status == "range_corrected")) {
      "range_correction_partial"
    } else {
      "range_correction_failed"
    },
    interpretation = paste(
      "Range correction expresses each value as a proportion of the observed within-unit signal range.",
      "It reduces between-unit range differences but depends strongly on the observed minimum and maximum."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "range_correction_summary") <- summary
  attr(out, "range_correction_parameters") <- parameters
  attr(out, "range_correction_settings") <- list(
    signal_col = signal_col,
    group_col = group_col,
    suffix = suffix,
    min_valid = min_valid,
    zero_range_action = zero_range_action,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_range_corrected", class(out)))

  out
}

#' @rdname standardise_gazepoint_range_correction
#' @export
standardize_gazepoint_range_correction <- function(dat,
                                                   signal_col,
                                                   group_col = "source_participant",
                                                   suffix = "_Range_Corrected",
                                                   min_valid = 2,
                                                   zero_range_action = c("NA", "zero"),
                                                   overwrite = FALSE) {
  standardise_gazepoint_range_correction(
    dat = dat,
    signal_col = signal_col,
    group_col = group_col,
    suffix = suffix,
    min_valid = min_valid,
    zero_range_action = zero_range_action,
    overwrite = overwrite
  )
}
