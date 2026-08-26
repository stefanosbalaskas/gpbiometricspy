#' Summarise Gazepoint GSR/EDA windows
#'
#' Summarises Gazepoint GSR/EDA values within participant, trial, stimulus, AOI,
#' or other user-defined windows. When available, `GSR_US` is used by default
#' because it represents skin conductance in microsiemens in Gazepoint exports.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Optional grouping columns defining windows, such as
#'   `c("USER", "MEDIA_ID")`.
#' @param value_column Optional GSR/EDA value column. If `NULL`, `GSR_US` is
#'   used when present, otherwise `GSR`.
#' @param validity_column Optional validity column. Defaults to `"GSRV"`.
#' @param exclude_zero Should zero values be excluded from usable summaries?
#'
#' @return A data frame with one row per window.
#'
#' @export
summarise_gazepoint_gsr_windows <- function(data,
                                            group_columns = NULL,
                                            value_column = NULL,
                                            validity_column = "GSRV",
                                            exclude_zero = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  if (is.null(value_column)) {
    value_column <- choose_first_present(dat, c("GSR_US", "GSR"))
  }

  summarise_gazepoint_signal_windows(
    data = dat,
    signal = "gsr_eda",
    group_columns = group_columns,
    value_column = value_column,
    validity_column = validity_column,
    exclude_zero = exclude_zero
  )
}


#' Summarise Gazepoint heart-rate windows
#'
#' Summarises Gazepoint heart-rate values within participant, trial, stimulus,
#' AOI, or other user-defined windows. `HRV` is treated as a validity flag, not
#' as a heart-rate-variability metric.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Optional grouping columns defining windows, such as
#'   `c("USER", "MEDIA_ID")`.
#' @param value_column Heart-rate value column. Defaults to `"HR"`.
#' @param validity_column Heart-rate validity column. Defaults to `"HRV"`.
#' @param exclude_zero Should zero values be excluded from usable summaries?
#'
#' @return A data frame with one row per window.
#'
#' @export
summarise_gazepoint_hr_windows <- function(data,
                                           group_columns = NULL,
                                           value_column = "HR",
                                           validity_column = "HRV",
                                           exclude_zero = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  summarise_gazepoint_signal_windows(
    data = dat,
    signal = "heart_rate",
    group_columns = group_columns,
    value_column = value_column,
    validity_column = validity_column,
    exclude_zero = exclude_zero
  )
}


#' Summarise Gazepoint engagement-dial windows
#'
#' Summarises Gazepoint engagement-dial values within participant, trial,
#' stimulus, AOI, or other user-defined windows.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Optional grouping columns defining windows, such as
#'   `c("USER", "MEDIA_ID")`.
#' @param value_column Engagement-dial value column. Defaults to `"DIAL"`.
#' @param validity_column Engagement-dial validity column. Defaults to
#'   `"DIALV"`.
#' @param exclude_zero Should zero values be excluded from usable summaries?
#'
#' @return A data frame with one row per window.
#'
#' @export
summarise_gazepoint_engagement_windows <- function(data,
                                                   group_columns = NULL,
                                                   value_column = "DIAL",
                                                   validity_column = "DIALV",
                                                   exclude_zero = FALSE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  summarise_gazepoint_signal_windows(
    data = dat,
    signal = "engagement_dial",
    group_columns = group_columns,
    value_column = value_column,
    validity_column = validity_column,
    exclude_zero = exclude_zero
  )
}


#' Summarise Gazepoint multimodal biometric windows
#'
#' Creates a combined window-level summary table for GSR/EDA, heart rate, and
#' engagement dial. The output is suitable for later merging with eye-tracking
#' summaries from `gp3tools`.
#'
#' @param data A data frame or a path to a Gazepoint CSV export.
#' @param group_columns Optional grouping columns defining windows, such as
#'   `c("USER", "MEDIA_ID")`.
#' @param exclude_zero Should zero values be excluded from GSR and heart-rate
#'   summaries?
#'
#' @return A data frame with one row per window and prefixed biometric summary
#'   columns.
#'
#' @export
summarise_gazepoint_multimodal_windows <- function(data,
                                                   group_columns = NULL,
                                                   exclude_zero = TRUE) {
  dat <- coerce_gazepoint_biometrics_data(data)

  gsr <- summarise_gazepoint_gsr_windows(
    dat,
    group_columns = group_columns,
    exclude_zero = exclude_zero
  )

  hr <- summarise_gazepoint_hr_windows(
    dat,
    group_columns = group_columns,
    exclude_zero = exclude_zero
  )

  dial <- summarise_gazepoint_engagement_windows(
    dat,
    group_columns = group_columns,
    exclude_zero = FALSE
  )

  gsr <- prefix_signal_summary(gsr, prefix = "gsr")
  hr <- prefix_signal_summary(hr, prefix = "hr")
  dial <- prefix_signal_summary(dial, prefix = "dial")

  out <- merge_signal_summaries(
    summaries = list(gsr, hr, dial),
    group_columns = group_columns
  )

  rownames(out) <- NULL
  out
}


summarise_gazepoint_signal_windows <- function(data,
                                               signal,
                                               group_columns = NULL,
                                               value_column,
                                               validity_column = NULL,
                                               exclude_zero = TRUE) {
  if (is.null(value_column) || length(value_column) != 1L || is.na(value_column)) {
    stop("`value_column` could not be determined.", call. = FALSE)
  }

  if (!value_column %in% names(data)) {
    stop("`value_column` was not found in `data`: ", value_column, call. = FALSE)
  }

  if (!is.null(group_columns)) {
    missing_groups <- setdiff(group_columns, names(data))

    if (length(missing_groups) > 0L) {
      stop(
        "`group_columns` were not found in `data`: ",
        paste(missing_groups, collapse = ", "),
        call. = FALSE
      )
    }
  }

  if (is.null(group_columns) || length(group_columns) == 0L) {
    group_keys <- rep("all", nrow(data))
    group_frame <- data.frame(.window = "all", stringsAsFactors = FALSE)
    group_columns_out <- ".window"
  } else {
    group_keys <- make_group_key(data, group_columns)
    group_frame <- unique(data[group_columns])
    group_frame$.group_key <- make_group_key(group_frame, group_columns)
    group_columns_out <- group_columns
  }

  unique_keys <- unique(group_keys)

  summaries <- lapply(unique_keys, function(key) {
    rows <- group_keys == key

    group_values <- if (is.null(group_columns) || length(group_columns) == 0L) {
      data.frame(.window = "all", stringsAsFactors = FALSE)
    } else {
      data[which(rows)[1], group_columns, drop = FALSE]
    }

    x <- as_numeric_safe(data[[value_column]][rows])

    valid <- !is.na(x)

    if (isTRUE(exclude_zero)) {
      valid <- valid & x != 0
    }

    validity_present <- !is.null(validity_column) &&
      length(validity_column) == 1L &&
      validity_column %in% names(data)

    if (validity_present) {
      v <- as_numeric_safe(data[[validity_column]][rows])
      valid <- valid & !is.na(v) & v > 0
    }

    usable_x <- x[valid]

    out <- data.frame(
      signal = signal,
      value_column = value_column,
      validity_column = ifelse(validity_present, validity_column, NA_character_),
      n_rows = length(x),
      usable_rows = length(usable_x),
      usable_pct = safe_pct(length(usable_x), length(x)),
      missing_rows = sum(is.na(x)),
      zero_rows = sum(!is.na(x) & x == 0),
      mean_value = ifelse(length(usable_x) > 0L, mean(usable_x), NA_real_),
      median_value = ifelse(length(usable_x) > 0L, stats::median(usable_x), NA_real_),
      sd_value = ifelse(length(usable_x) > 1L, stats::sd(usable_x), NA_real_),
      min_value = ifelse(length(usable_x) > 0L, min(usable_x), NA_real_),
      max_value = ifelse(length(usable_x) > 0L, max(usable_x), NA_real_),
      first_value = ifelse(length(usable_x) > 0L, usable_x[1], NA_real_),
      last_value = ifelse(length(usable_x) > 0L, usable_x[length(usable_x)], NA_real_),
      change_value = ifelse(length(usable_x) > 0L, usable_x[length(usable_x)] - usable_x[1], NA_real_),
      stringsAsFactors = FALSE
    )

    cbind(group_values, out, stringsAsFactors = FALSE)
  })

  out <- do.call(rbind, summaries)
  rownames(out) <- NULL

  if (identical(group_columns_out, ".window")) {
    names(out)[names(out) == ".window"] <- "window"
  }

  out
}


prefix_signal_summary <- function(summary, prefix) {
  metadata_columns <- c(
    "signal",
    "value_column",
    "validity_column",
    "n_rows",
    "usable_rows",
    "usable_pct",
    "missing_rows",
    "zero_rows",
    "mean_value",
    "median_value",
    "sd_value",
    "min_value",
    "max_value",
    "first_value",
    "last_value",
    "change_value"
  )

  columns_to_prefix <- intersect(metadata_columns, names(summary))
  names(summary)[match(columns_to_prefix, names(summary))] <-
    paste(prefix, columns_to_prefix, sep = "_")

  summary
}


merge_signal_summaries <- function(summaries, group_columns = NULL) {
  if (length(summaries) == 0L) {
    return(data.frame())
  }

  if (is.null(group_columns) || length(group_columns) == 0L) {
    group_columns <- "window"
  }

  out <- summaries[[1]]

  if (length(summaries) == 1L) {
    return(out)
  }

  for (i in 2:length(summaries)) {
    out <- merge(
      out,
      summaries[[i]],
      by = group_columns,
      all = TRUE,
      sort = FALSE
    )
  }

  out
}
