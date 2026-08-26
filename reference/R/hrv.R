#' Summarise Gazepoint IBI-derived HRV windows
#'
#' Summarises interbeat-interval (IBI) values within participant, stimulus,
#' trial, AOI, or other user-defined windows. This function derives simple
#' time-domain variability features from `IBI`. It does not use the Gazepoint
#' `HRV` column as a heart-rate-variability metric, because `HRV` is treated as
#' the Gazepoint heart-rate validity flag.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Columns defining analysis windows, such as
#'   `c("source_participant", "MEDIA_ID")`.
#' @param ibi_column Interbeat-interval column. Defaults to `"IBI"`.
#' @param validity_column Optional validity column. Defaults to `"HRV"`.
#' @param min_ibi Minimum plausible IBI in seconds.
#' @param max_ibi Maximum plausible IBI in seconds.
#'
#' @return A data frame with one row per window and IBI-derived HRV summaries.
#'
#' @export
summarise_gazepoint_ibi_hrv_windows <- function(data,
                                                group_columns,
                                                ibi_column = "IBI",
                                                validity_column = "HRV",
                                                min_ibi = 0.3,
                                                max_ibi = 2.0) {
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

  if (!ibi_column %in% names(dat)) {
    stop("`ibi_column` was not found in `data`: ", ibi_column, call. = FALSE)
  }

  group_key <- make_group_key(dat, group_columns)
  groups <- unique(group_key)

  rows <- lapply(groups, function(key) {
    in_group <- group_key == key

    group_values <- dat[which(in_group)[1], group_columns, drop = FALSE]

    ibi <- as_numeric_safe(dat[[ibi_column]][in_group])

    valid <- !is.na(ibi) & ibi >= min_ibi & ibi <= max_ibi

    validity_present <- !is.null(validity_column) &&
      length(validity_column) == 1L &&
      validity_column %in% names(dat)

    if (validity_present) {
      validity <- as_numeric_safe(dat[[validity_column]][in_group])
      valid <- valid & !is.na(validity) & validity > 0
    }

    usable_ibi <- ibi[valid]

    summary <- summarise_ibi_vector(
      ibi = usable_ibi,
      n_rows = length(ibi),
      ibi_column = ibi_column,
      validity_column = ifelse(validity_present, validity_column, NA_character_)
    )

    cbind(group_values, summary, stringsAsFactors = FALSE)
  })

  out <- do.call(rbind, rows)
  rownames(out) <- NULL

  out
}


summarise_ibi_vector <- function(ibi,
                                 n_rows,
                                 ibi_column,
                                 validity_column) {
  ibi <- ibi[!is.na(ibi)]

  n_usable <- length(ibi)

  diff_ibi <- diff(ibi)

  data.frame(
    ibi_column = ibi_column,
    validity_column = validity_column,
    n_rows = n_rows,
    ibi_usable_rows = n_usable,
    ibi_usable_pct = safe_pct(n_usable, n_rows),
    mean_ibi_sec = ifelse(n_usable > 0L, mean(ibi), NA_real_),
    median_ibi_sec = ifelse(n_usable > 0L, stats::median(ibi), NA_real_),
    sd_ibi_sec = ifelse(n_usable > 1L, stats::sd(ibi), NA_real_),
    mean_hr_from_ibi_bpm = ifelse(n_usable > 0L, mean(60 / ibi), NA_real_),
    sdnn_ms = ifelse(n_usable > 1L, stats::sd(ibi) * 1000, NA_real_),
    rmssd_ms = ifelse(length(diff_ibi) > 0L, sqrt(mean(diff_ibi^2)) * 1000, NA_real_),
    pnn50 = ifelse(length(diff_ibi) > 0L, mean(abs(diff_ibi) > 0.05), NA_real_),
    min_ibi_sec = ifelse(n_usable > 0L, min(ibi), NA_real_),
    max_ibi_sec = ifelse(n_usable > 0L, max(ibi), NA_real_),
    stringsAsFactors = FALSE
  )
}
