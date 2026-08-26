#' Standardize biometric signals within participant or other analysis units
#'
#' Adds within-unit standardized biometric columns, usually within participant
#' or participant-by-session/stimulus groups. This is useful when the analysis
#' focuses on relative within-person signal change rather than absolute
#' between-person level differences.
#'
#' The helper is intentionally conservative. It does not run automatically in
#' the main workflow and does not infer emotion, valence, stress, trust,
#' preference, cognition, or diagnosis. Within-unit z-scoring removes
#' between-unit level and scale differences and should therefore be reported
#' explicitly.
#'
#' @param data A data frame containing Gazepoint biometric data.
#' @param signal_cols Character vector of biometric signal columns to
#'   standardize. If `NULL`, common numeric biometric columns are detected.
#' @param unit_cols Character vector defining the unit within which means and
#'   standard deviations are computed. If `NULL`, common participant/session
#'   columns are detected. If no columns are detected, the whole data frame is
#'   treated as one unit.
#' @param reference_col Optional logical or categorical column identifying rows
#'   used to estimate the reference mean and standard deviation. For example,
#'   this can be a baseline-window flag. The resulting parameters are then
#'   applied to all rows in the same unit.
#' @param reference_value Value in `reference_col` that marks reference rows.
#'   Defaults to `TRUE`.
#' @param suffix Suffix for standardized output columns.
#' @param center Logical. If `TRUE`, subtract the within-unit reference mean.
#' @param scale Logical. If `TRUE`, divide by the within-unit reference
#'   standard deviation.
#' @param min_valid Minimum number of finite reference observations required
#'   per unit and signal.
#' @param zero_sd_action What to do when the within-unit standard deviation is
#'   zero or unavailable. `"NA"` returns `NA`; `"zero"` returns zero for finite
#'   centered values.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with added standardized columns. Attributes include
#'   `standardization_summary`, `standardization_parameters`, and `settings`.
#' @export
standardize_gazepoint_biometrics_within_unit <- function(data,
                                                         signal_cols = NULL,
                                                         unit_cols = NULL,
                                                         reference_col = NULL,
                                                         reference_value = TRUE,
                                                         suffix = "_z_within",
                                                         center = TRUE,
                                                         scale = TRUE,
                                                         min_valid = 2,
                                                         zero_sd_action = c("NA", "zero"),
                                                         overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  zero_sd_action <- match.arg(zero_sd_action)

  gpbiometrics_within_z_validate_logical(center, "center")
  gpbiometrics_within_z_validate_logical(scale, "scale")
  gpbiometrics_within_z_validate_logical(overwrite, "overwrite")

  if (!is.character(suffix) || length(suffix) != 1 || is.na(suffix) || !nzchar(suffix)) {
    stop("`suffix` must be a non-empty character string.", call. = FALSE)
  }

  if (!is.numeric(min_valid) || length(min_valid) != 1 || is.na(min_valid) || min_valid < 1) {
    stop("`min_valid` must be a positive number.", call. = FALSE)
  }

  min_valid <- as.integer(min_valid)

  signal_cols <- gpbiometrics_within_z_resolve_signal_cols(data, signal_cols)
  unit_cols <- gpbiometrics_within_z_resolve_unit_cols(data, unit_cols)

  if (!is.null(reference_col)) {
    if (!is.character(reference_col) || length(reference_col) != 1 || is.na(reference_col)) {
      stop("`reference_col` must be NULL or a single column name.", call. = FALSE)
    }

    if (!reference_col %in% names(data)) {
      stop("Column `", reference_col, "` was not found in `data`.", call. = FALSE)
    }
  }

  output_cols <- paste0(signal_cols, suffix)

  if (!isTRUE(overwrite)) {
    existing <- intersect(output_cols, names(data))

    if (length(existing) > 0) {
      stop(
        "The following output columns already exist: ",
        paste(existing, collapse = ", "),
        ". Use `overwrite = TRUE` to replace them.",
        call. = FALSE
      )
    }
  }

  out <- data

  for (nm in output_cols) {
    out[[nm]] <- NA_real_
  }

  unit_index <- gpbiometrics_within_z_split_indices(data, unit_cols)

  parameter_rows <- list()

  row_id <- 1L

  for (unit_id in names(unit_index)) {
    idx <- unit_index[[unit_id]]
    unit_values <- gpbiometrics_within_z_unit_values(data, idx, unit_cols, unit_id)

    reference_idx <- idx

    if (!is.null(reference_col)) {
      ref_values <- data[[reference_col]][idx]
      keep_ref <- !is.na(ref_values) & ref_values == reference_value
      reference_idx <- idx[keep_ref]
    }

    for (j in seq_along(signal_cols)) {
      signal_col <- signal_cols[j]
      output_col <- output_cols[j]

      x_reference <- data[[signal_col]][reference_idx]
      finite_reference <- is.finite(x_reference)
      n_reference_finite <- sum(finite_reference)

      status <- "standardized"
      reference_mean <- NA_real_
      reference_sd <- NA_real_

      if (n_reference_finite < min_valid) {
        status <- "insufficient_reference_rows"
        out[[output_col]][idx] <- NA_real_
      } else {
        reference_mean <- mean(x_reference[finite_reference], na.rm = TRUE)
        reference_sd <- stats::sd(x_reference[finite_reference], na.rm = TRUE)

        x_all <- data[[signal_col]][idx]

        transformed <- x_all

        if (isTRUE(center)) {
          transformed <- transformed - reference_mean
        }

        if (isTRUE(scale)) {
          if (!is.finite(reference_sd) || reference_sd == 0) {
            status <- "zero_or_missing_sd"

            if (identical(zero_sd_action, "zero")) {
              transformed[is.finite(transformed)] <- 0
              transformed[!is.finite(transformed)] <- NA_real_
            } else {
              transformed[] <- NA_real_
            }
          } else {
            transformed <- transformed / reference_sd
          }
        }

        transformed[!is.finite(transformed)] <- NA_real_
        out[[output_col]][idx] <- transformed
      }

      parameter_rows[[row_id]] <- data.frame(
        unit_values,
        unit_id = unit_id,
        signal_col = signal_col,
        output_col = output_col,
        n_rows = length(idx),
        n_reference_rows = length(reference_idx),
        n_reference_finite = n_reference_finite,
        reference_mean = reference_mean,
        reference_sd = reference_sd,
        center = center,
        scale = scale,
        status = status,
        stringsAsFactors = FALSE,
        check.names = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  parameters <- do.call(rbind, parameter_rows)
  rownames(parameters) <- NULL

  summary <- data.frame(
    input_rows = nrow(data),
    signal_count = length(signal_cols),
    output_count = length(output_cols),
    unit_count = length(unit_index),
    parameter_rows = nrow(parameters),
    standardized_rows = sum(parameters$status == "standardized"),
    problem_rows = sum(parameters$status != "standardized"),
    center = center,
    scale = scale,
    reference_col = if (is.null(reference_col)) NA_character_ else reference_col,
    suffix = suffix,
    status = if (all(parameters$status == "standardized")) {
      "within_unit_standardization_complete"
    } else if (any(parameters$status == "standardized")) {
      "within_unit_standardization_partial"
    } else {
      "within_unit_standardization_failed"
    },
    interpretation = paste(
      "Within-unit standardization rescales biometric signals relative to each unit's own reference distribution.",
      "It supports within-person comparison but removes between-unit level and scale differences.",
      "It does not infer emotion, valence, stress, trust, preference, cognition, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "standardization_summary") <- summary
  attr(out, "standardization_parameters") <- parameters
  attr(out, "settings") <- list(
    signal_cols = signal_cols,
    unit_cols = unit_cols,
    reference_col = reference_col,
    reference_value = reference_value,
    suffix = suffix,
    center = center,
    scale = scale,
    min_valid = min_valid,
    zero_sd_action = zero_sd_action,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_within_unit_standardized", class(out)))

  out
}

#' @rdname standardize_gazepoint_biometrics_within_unit
#' @export
standardise_gazepoint_biometrics_within_unit <- function(data,
                                                         signal_cols = NULL,
                                                         unit_cols = NULL,
                                                         reference_col = NULL,
                                                         reference_value = TRUE,
                                                         suffix = "_z_within",
                                                         center = TRUE,
                                                         scale = TRUE,
                                                         min_valid = 2,
                                                         zero_sd_action = c("NA", "zero"),
                                                         overwrite = FALSE) {
  standardize_gazepoint_biometrics_within_unit(
    data = data,
    signal_cols = signal_cols,
    unit_cols = unit_cols,
    reference_col = reference_col,
    reference_value = reference_value,
    suffix = suffix,
    center = center,
    scale = scale,
    min_valid = min_valid,
    zero_sd_action = zero_sd_action,
    overwrite = overwrite
  )
}

gpbiometrics_within_z_resolve_signal_cols <- function(data, signal_cols = NULL) {
  if (!is.null(signal_cols)) {
    if (!is.character(signal_cols) || length(signal_cols) == 0) {
      stop("`signal_cols` must be NULL or a non-empty character vector.", call. = FALSE)
    }

    missing_cols <- setdiff(signal_cols, names(data))

    if (length(missing_cols) > 0) {
      stop(
        "The following `signal_cols` were not found in `data`: ",
        paste(missing_cols, collapse = ", "),
        call. = FALSE
      )
    }

    non_numeric <- signal_cols[!vapply(data[signal_cols], is.numeric, logical(1))]

    if (length(non_numeric) > 0) {
      stop(
        "The following `signal_cols` are not numeric: ",
        paste(non_numeric, collapse = ", "),
        call. = FALSE
      )
    }

    return(unique(signal_cols))
  }

  candidates <- c(
    "GSR_US",
    "GSR_US_PHASIC",
    "GSR_US_TONIC",
    "GSR",
    "EDA",
    "HR",
    "HRP",
    "IBI",
    "DIAL"
  )

  found <- intersect(candidates, names(data))
  found <- found[vapply(data[found], is.numeric, logical(1))]

  if (length(found) == 0) {
    stop(
      "No common numeric biometric signal columns were detected. Supply `signal_cols` explicitly.",
      call. = FALSE
    )
  }

  unique(found)
}

gpbiometrics_within_z_resolve_unit_cols <- function(data, unit_cols = NULL) {
  if (!is.null(unit_cols)) {
    if (!is.character(unit_cols)) {
      stop("`unit_cols` must be NULL or a character vector.", call. = FALSE)
    }

    missing_cols <- setdiff(unit_cols, names(data))

    if (length(missing_cols) > 0) {
      stop(
        "The following `unit_cols` were not found in `data`: ",
        paste(missing_cols, collapse = ", "),
        call. = FALSE
      )
    }

    return(unique(unit_cols))
  }

  candidates <- c(
    "source_participant",
    "participant",
    "participant_id",
    "subject",
    "subject_id",
    "USER_FILE",
    "source_file",
    "session",
    "session_id"
  )

  unique(intersect(candidates, names(data)))
}

gpbiometrics_within_z_split_indices <- function(data, unit_cols) {
  if (length(unit_cols) == 0) {
    return(list(all_rows = seq_len(nrow(data))))
  }

  unit_frame <- data[unit_cols]
  unit_frame[] <- lapply(unit_frame, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  unit_key <- do.call(paste, c(unit_frame, sep = " | "))
  split(seq_len(nrow(data)), unit_key)
}

gpbiometrics_within_z_unit_values <- function(data, idx, unit_cols, unit_id) {
  if (length(unit_cols) == 0) {
    return(data.frame(
      unit_label = unit_id,
      stringsAsFactors = FALSE
    ))
  }

  values <- lapply(unit_cols, function(nm) {
    as.character(data[[nm]][idx[1]])
  })

  names(values) <- unit_cols

  as.data.frame(
    values,
    stringsAsFactors = FALSE,
    optional = TRUE
  )
}

gpbiometrics_within_z_validate_logical <- function(x, name) {
  if (!is.logical(x) || length(x) != 1 || is.na(x)) {
    stop("`", name, "` must be TRUE or FALSE.", call. = FALSE)
  }

  invisible(TRUE)
}
