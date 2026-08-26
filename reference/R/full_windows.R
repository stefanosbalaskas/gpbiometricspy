#' Summarise full Gazepoint biometric windows
#'
#' Creates a combined window-level summary table containing GSR/EDA,
#' heart-rate, engagement-dial, and IBI-derived HRV summaries. This function is
#' intended for biometric analyses where both continuous physiological values
#' and interbeat-interval variability features are needed.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Columns defining analysis windows, such as
#'   `c("source_participant", "MEDIA_ID")`.
#' @param include_ibi_hrv Logical. Should IBI-derived HRV summaries be included?
#'
#' @return A data frame with one row per window and prefixed biometric summary
#'   columns.
#'
#' @export
summarise_gazepoint_full_biometric_windows <- function(data,
                                                       group_columns,
                                                       include_ibi_hrv = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (missing(group_columns) || is.null(group_columns) || length(group_columns) == 0L) {
    stop("`group_columns` must define the analysis windows.", call. = FALSE)
  }

  missing_groups <- setdiff(group_columns, names(dat))

  if (length(missing_groups) > 0L) {
    stop(
      "`group_columns` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  multimodal <- summarise_gazepoint_multimodal_windows(
    data = dat,
    group_columns = group_columns
  )

  if (!isTRUE(include_ibi_hrv)) {
    return(multimodal)
  }

  if (!"IBI" %in% names(dat)) {
    return(multimodal)
  }

  ibi <- summarise_gazepoint_ibi_hrv_windows(
    data = dat,
    group_columns = group_columns
  )

  ibi <- prefix_ibi_summary(ibi)

  out <- merge(
    multimodal,
    ibi,
    by = group_columns,
    all = TRUE,
    sort = FALSE
  )

  rownames(out) <- NULL
  out
}


prefix_ibi_summary <- function(summary) {
  columns_to_prefix <- setdiff(
    names(summary),
    c("source_participant", "USER", "USERID", "participant", "subject", "MEDIA_ID", "MEDIA_NAME")
  )

  group_like_columns <- names(summary)[
    names(summary) %in% c("source_participant", "USER", "USERID", "participant", "subject", "MEDIA_ID", "MEDIA_NAME")
  ]

  non_group_columns <- setdiff(names(summary), group_like_columns)

  names(summary)[match(non_group_columns, names(summary))] <-
    paste("ibi", non_group_columns, sep = "_")

  summary
}
