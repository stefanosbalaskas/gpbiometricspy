#' Synchronise Gazepoint Biometrics with gaze data
#'
#' Joins Gazepoint Biometrics data to gaze or fixation data using exact key
#' columns. This function is intentionally conservative: it does not perform
#' interpolation, nearest-neighbour matching, or automatic time shifting. For a
#' first reproducible workflow, exact joins by participant, media, trial, sample
#' counter, or fixation identifier are preferred when those fields are available.
#'
#' @param biometrics A Gazepoint Biometrics data frame.
#' @param gaze A gaze, fixation, AOI, or `gp3tools`-style summary data frame.
#' @param by Character vector of key columns used for joining.
#' @param all_x Logical. Should all rows from `gaze` be retained?
#' @param suffixes Character vector of length two used for duplicate non-key
#'   column names.
#'
#' @return A data frame with gaze rows joined to biometric columns. The returned
#'   object has class `"gazepoint_biometrics_sync"` and a `"sync_summary"`
#'   attribute.
#'
#' @export
sync_gazepoint_biometrics_with_gaze <- function(biometrics,
                                                gaze,
                                                by,
                                                all_x = TRUE,
                                                suffixes = c(".gaze", ".bio")) {
  if (!is.data.frame(biometrics)) {
    biometrics <- coerce_gazepoint_biometrics_data(biometrics)
  }

  if (!is.data.frame(gaze)) {
    stop("`gaze` must be a data frame.", call. = FALSE)
  }

  if (missing(by) || !is.character(by) || length(by) == 0L) {
    stop("`by` must be a non-empty character vector of join columns.", call. = FALSE)
  }

  missing_bio_keys <- setdiff(by, names(biometrics))
  missing_gaze_keys <- setdiff(by, names(gaze))

  if (length(missing_bio_keys) > 0L) {
    stop(
      "`by` columns were not found in `biometrics`: ",
      paste(missing_bio_keys, collapse = ", "),
      call. = FALSE
    )
  }

  if (length(missing_gaze_keys) > 0L) {
    stop(
      "`by` columns were not found in `gaze`: ",
      paste(missing_gaze_keys, collapse = ", "),
      call. = FALSE
    )
  }

  biometric_columns <- check_gazepoint_biometric_columns(biometrics)
  present_biometric_columns <- biometric_columns$column[
    biometric_columns$present &
      biometric_columns$signal %in% c(
        "gsr_eda",
        "heart_rate",
        "engagement_dial",
        "ttl_marker"
      )
  ]

  keep_bio <- unique(c(by, present_biometric_columns))
  bio_for_join <- biometrics[keep_bio]

  out <- merge(
    gaze,
    bio_for_join,
    by = by,
    all.x = all_x,
    all.y = FALSE,
    sort = FALSE,
    suffixes = suffixes
  )

  attr(out, "sync_summary") <- data.frame(
    n_gaze_rows = nrow(gaze),
    n_biometric_rows = nrow(biometrics),
    n_output_rows = nrow(out),
    join_keys = paste(by, collapse = ","),
    all_x = all_x,
    biometric_columns_joined = paste(setdiff(names(bio_for_join), by), collapse = ","),
    stringsAsFactors = FALSE
  )

  class(out) <- c("gazepoint_biometrics_sync", class(out))

  out
}


#' Join Gazepoint Biometrics to a master table
#'
#' Convenience wrapper around `sync_gazepoint_biometrics_with_gaze()` for joining
#' biometric data to a `gp3tools`-style master table or any other analysis-ready
#' gaze table.
#'
#' @param master A master gaze or analysis table.
#' @param biometrics A Gazepoint Biometrics data frame.
#' @param by Character vector of key columns used for joining.
#' @param all_x Logical. Should all rows from `master` be retained?
#'
#' @return A data frame with biometric columns joined to the master table.
#'
#' @export
join_gazepoint_biometrics_to_master <- function(master,
                                                biometrics,
                                                by,
                                                all_x = TRUE) {
  sync_gazepoint_biometrics_with_gaze(
    biometrics = biometrics,
    gaze = master,
    by = by,
    all_x = all_x
  )
}
