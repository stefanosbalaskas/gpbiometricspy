#' Prepare Gazepoint multimodal model data
#'
#' Creates a model-ready table from Gazepoint biometric window summaries and,
#' optionally, eye-tracking summaries produced by `gp3tools` or another
#' workflow. The function is intentionally conservative: it does not fit a
#' model, impute missing values, or remove rows automatically.
#'
#' @param biometrics A data frame containing row-level Gazepoint Biometrics data
#'   or an already summarised biometric window table.
#' @param eye_tracking Optional eye-tracking summary table to merge with the
#'   biometric summaries.
#' @param group_columns Columns defining the analysis unit, such as
#'   `c("USER", "MEDIA_ID")`.
#' @param biometric_is_summarised Logical. If `FALSE`, biometric window
#'   summaries are created using [summarise_gazepoint_multimodal_windows()].
#'   If `TRUE`, `biometrics` is treated as already summarised.
#' @param by Optional merge keys. If `NULL`, `group_columns` are used.
#' @param all Should a full outer join be used when eye-tracking data are
#'   supplied? Defaults to `FALSE`, giving an inner join.
#'
#' @return A data frame with class `"gazepoint_multimodal_model_data"` and a
#'   `"model_data_summary"` attribute.
#'
#' @export
prepare_gazepoint_multimodal_model_data <- function(biometrics,
                                                    eye_tracking = NULL,
                                                    group_columns = NULL,
                                                    biometric_is_summarised = FALSE,
                                                    by = NULL,
                                                    all = FALSE) {
  if (!is.data.frame(biometrics)) {
    biometrics <- coerce_gazepoint_biometrics_data(biometrics)
  }

  if (is.null(group_columns) || length(group_columns) == 0L) {
    stop("`group_columns` must define the model-data analysis unit.", call. = FALSE)
  }

  if (!all(group_columns %in% names(biometrics))) {
    missing_groups <- setdiff(group_columns, names(biometrics))
    stop(
      "`group_columns` were not found in `biometrics`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  if (isTRUE(biometric_is_summarised)) {
    biometric_summary <- biometrics
  } else {
    biometric_summary <- summarise_gazepoint_multimodal_windows(
      biometrics,
      group_columns = group_columns
    )
  }

  if (is.null(eye_tracking)) {
    out <- biometric_summary
    source <- "biometrics_only"
  } else {
    if (!is.data.frame(eye_tracking)) {
      stop("`eye_tracking` must be a data frame when supplied.", call. = FALSE)
    }

    if (is.null(by)) {
      by <- group_columns
    }

    missing_bio_keys <- setdiff(by, names(biometric_summary))
    missing_eye_keys <- setdiff(by, names(eye_tracking))

    if (length(missing_bio_keys) > 0L) {
      stop(
        "`by` columns were not found in biometric summaries: ",
        paste(missing_bio_keys, collapse = ", "),
        call. = FALSE
      )
    }

    if (length(missing_eye_keys) > 0L) {
      stop(
        "`by` columns were not found in `eye_tracking`: ",
        paste(missing_eye_keys, collapse = ", "),
        call. = FALSE
      )
    }

    out <- merge(
      eye_tracking,
      biometric_summary,
      by = by,
      all = all,
      sort = FALSE
    )

    source <- "eye_tracking_plus_biometrics"
  }

  attr(out, "model_data_summary") <- data.frame(
    source = source,
    n_rows = nrow(out),
    n_columns = ncol(out),
    group_columns = paste(group_columns, collapse = ","),
    has_eye_tracking = !is.null(eye_tracking),
    stringsAsFactors = FALSE
  )

  class(out) <- c("gazepoint_multimodal_model_data", class(out))

  out
}
