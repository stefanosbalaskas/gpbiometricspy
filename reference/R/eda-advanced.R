#' Decompose Gazepoint GSR/EDA into tonic and phasic components
#'
#' Creates descriptive tonic and phasic EDA columns from Gazepoint GSR/EDA data.
#' If vendor-provided tonic/phasic columns such as `GSR_US_TONIC` and
#' `GSR_US_PHASIC` are available, they are used by default. Otherwise, a simple
#' rolling-median tonic estimate is used and the phasic component is calculated
#' as signal minus tonic. This helper is intentionally conservative and does not
#' replace specialised biosignal-processing software.
#'
#' @param data A data frame.
#' @param signal_col Optional GSR/EDA signal column. If `NULL`, a likely
#'   conductance-like column is detected.
#' @param tonic_col Optional existing tonic column.
#' @param phasic_col Optional existing phasic column.
#' @param time_col Optional time/order column.
#' @param group_cols Optional grouping columns.
#' @param window_size Rolling-median window size used when existing tonic/phasic
#'   columns are not available. Even values are increased by one.
#' @param output_prefix Prefix for output columns.
#' @param overwrite Logical. Should existing output columns be overwritten?
#'
#' @return A data frame with added tonic, phasic, and method columns. Attributes
#'   include `overview` and `settings`.
#'
#' @examples
#' df <- data.frame(CNT = 1:10, GSR_US = seq(1, 2, length.out = 10))
#' out <- decompose_gazepoint_eda(df, signal_col = "GSR_US", window_size = 3)
#' names(out)
#'
#' @export
decompose_gazepoint_eda <- function(data,
                                    signal_col = NULL,
                                    tonic_col = NULL,
                                    phasic_col = NULL,
                                    time_col = NULL,
                                    group_cols = NULL,
                                    window_size = 31L,
                                    output_prefix = "eda",
                                    overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(signal_col)) {
    .gpbiom_assert_columns(data, signal_col, "signal_col")
    if (length(signal_col) != 1L) {
      stop("`signal_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(tonic_col)) {
    .gpbiom_assert_columns(data, tonic_col, "tonic_col")
    if (length(tonic_col) != 1L) {
      stop("`tonic_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(phasic_col)) {
    .gpbiom_assert_columns(data, phasic_col, "phasic_col")
    if (length(phasic_col) != 1L) {
      stop("`phasic_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
    if (length(time_col) != 1L) {
      stop("`time_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  .gpbiom_assert_positive_integer(window_size, "window_size")

  if (!is.character(output_prefix) ||
      length(output_prefix) != 1L ||
      is.na(output_prefix) ||
      !nzchar(output_prefix)) {
    stop("`output_prefix` must be a non-empty character string.",
         call. = FALSE)
  }

  if (!is.logical(overwrite) || length(overwrite) != 1L || is.na(overwrite)) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  if (is.null(signal_col)) {
    signal_col <- .gpbiom_choose_eda_signal_column(data)
  }

  if (is.na(signal_col) || !signal_col %in% names(data)) {
    stop("No GSR/EDA signal column was detected. Provide `signal_col` explicitly.",
         call. = FALSE)
  }

  if (!is.numeric(data[[signal_col]])) {
    stop("`signal_col` must be numeric.", call. = FALSE)
  }

  existing <- .gpbiom_detect_existing_eda_components(data, tonic_col, phasic_col)

  tonic_out <- paste0(output_prefix, "_tonic")
  phasic_out <- paste0(output_prefix, "_phasic")
  method_out <- paste0(output_prefix, "_decomposition_method")

  new_cols <- c(tonic_out, phasic_out, method_out)
  conflicts <- new_cols[new_cols %in% names(data)]

  if (length(conflicts) > 0L && !isTRUE(overwrite)) {
    stop(
      "Output columns already exist: ",
      paste(conflicts, collapse = ", "),
      ". Use `overwrite = TRUE` to replace them.",
      call. = FALSE
    )
  }

  out <- data
  out[[tonic_out]] <- NA_real_
  out[[phasic_out]] <- NA_real_
  out[[method_out]] <- NA_character_

  groups <- .gpbiom_eda_group_indices(out, group_cols)

  if (!is.na(existing$tonic_col) && !is.na(existing$phasic_col)) {
    out[[tonic_out]] <- as.numeric(out[[existing$tonic_col]])
    out[[phasic_out]] <- as.numeric(out[[existing$phasic_col]])
    out[[method_out]] <- "existing_tonic_phasic_columns"
    method <- "existing_tonic_phasic_columns"
  } else {
    window_size <- as.integer(window_size)
    if (window_size %% 2L == 0L) {
      window_size <- window_size + 1L
    }

    for (group_name in names(groups)) {
      idx <- groups[[group_name]]
      idx <- .gpbiom_eda_order_index(out, idx, time_col)

      signal <- as.numeric(out[[signal_col]][idx])
      tonic <- .gpbiom_eda_rolling_median(signal, window_size = window_size)

      out[[tonic_out]][idx] <- tonic
      out[[phasic_out]][idx] <- signal - tonic
      out[[method_out]][idx] <- "rolling_median_residual"
    }

    method <- "rolling_median_residual"
  }

  overview <- data.frame(
    n_rows = nrow(out),
    signal_col = signal_col,
    tonic_col = tonic_out,
    phasic_col = phasic_out,
    method = method,
    used_existing_components = !is.na(existing$tonic_col) &&
      !is.na(existing$phasic_col),
    group_count = length(groups),
    n_tonic_non_missing = sum(!is.na(out[[tonic_out]])),
    n_phasic_non_missing = sum(!is.na(out[[phasic_out]])),
    status = "eda_decomposition_created",
    stringsAsFactors = FALSE
  )

  attr(out, "overview") <- overview
  attr(out, "settings") <- list(
    signal_col = signal_col,
    input_tonic_col = existing$tonic_col,
    input_phasic_col = existing$phasic_col,
    time_col = time_col,
    group_cols = group_cols,
    window_size = as.integer(window_size),
    output_prefix = output_prefix,
    note = paste0(
      "EDA decomposition is descriptive. Use specialised biosignal software ",
      "for confirmatory SCR/EDA decomposition when required."
    )
  )

  out
}


#' Detect SCR-like events in Gazepoint GSR/EDA data
#'
#' Detects simple SCR-like peaks from a phasic EDA signal. If a phasic column is
#' not supplied, the function first creates a descriptive phasic component using
#' `decompose_gazepoint_eda()`. This helper is intended for exploratory quality
#' control and descriptive summaries, not as a replacement for specialised SCR
#' detection pipelines.
#'
#' @param data A data frame.
#' @param phasic_col Optional phasic EDA column.
#' @param signal_col Optional raw/conductance EDA column used when `phasic_col`
#'   is not supplied.
#' @param time_col Optional time/order column.
#' @param group_cols Optional grouping columns.
#' @param threshold Optional numeric detection threshold. If `NULL`, a robust
#'   group-specific threshold is estimated as median plus three MADs, bounded
#'   below by zero.
#' @param min_peak_distance Minimum distance between retained peaks in samples.
#' @param window_size Rolling-median window size used if decomposition is needed.
#'
#' @return A list with `overview`, `events`, `group_summary`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:20,
#'   GSR_US_PHASIC = c(rep(0, 5), 0.2, 0.8, 0.2, rep(0, 12))
#' )
#' detect_gazepoint_scr_events(df, phasic_col = "GSR_US_PHASIC", time_col = "CNT")
#'
#' @export
detect_gazepoint_scr_events <- function(data,
                                        phasic_col = NULL,
                                        signal_col = NULL,
                                        time_col = NULL,
                                        group_cols = NULL,
                                        threshold = NULL,
                                        min_peak_distance = 10L,
                                        window_size = 31L) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(phasic_col)) {
    .gpbiom_assert_columns(data, phasic_col, "phasic_col")
    if (length(phasic_col) != 1L) {
      stop("`phasic_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(signal_col)) {
    .gpbiom_assert_columns(data, signal_col, "signal_col")
    if (length(signal_col) != 1L) {
      stop("`signal_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
    if (length(time_col) != 1L) {
      stop("`time_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(group_cols)) {
    .gpbiom_assert_columns(data, group_cols, "group_cols")
  }

  if (!is.null(threshold) &&
      (!is.numeric(threshold) ||
       length(threshold) != 1L ||
       is.na(threshold))) {
    stop("`threshold` must be NULL or a single numeric value.", call. = FALSE)
  }

  .gpbiom_assert_positive_integer(min_peak_distance, "min_peak_distance")
  .gpbiom_assert_positive_integer(window_size, "window_size")

  working <- data
  decomposition_used <- FALSE

  if (is.null(phasic_col)) {
    existing <- .gpbiom_detect_existing_eda_components(working, NULL, NULL)

    if (!is.na(existing$phasic_col)) {
      phasic_col <- existing$phasic_col
    } else {
      working <- decompose_gazepoint_eda(
        working,
        signal_col = signal_col,
        time_col = time_col,
        group_cols = group_cols,
        window_size = window_size,
        output_prefix = "scr_detection_eda",
        overwrite = TRUE
      )
      phasic_col <- "scr_detection_eda_phasic"
      decomposition_used <- TRUE
    }
  }

  if (!is.numeric(working[[phasic_col]])) {
    stop("`phasic_col` must be numeric.", call. = FALSE)
  }

  groups <- .gpbiom_eda_group_indices(working, group_cols)

  event_rows <- list()
  summary_rows <- list()
  event_id <- 0L

  for (group_name in names(groups)) {
    idx <- groups[[group_name]]
    idx <- .gpbiom_eda_order_index(working, idx, time_col)

    values <- as.numeric(working[[phasic_col]][idx])
    local_threshold <- if (is.null(threshold)) {
      .gpbiom_scr_default_threshold(values)
    } else {
      threshold
    }

    peaks <- .gpbiom_scr_peak_indices(
      values = values,
      threshold = local_threshold,
      min_peak_distance = min_peak_distance
    )

    if (length(peaks) > 0L) {
      for (peak in peaks) {
        event_id <- event_id + 1L
        row_index <- idx[peak]

        event_rows[[length(event_rows) + 1L]] <- data.frame(
          event_id = event_id,
          group = group_name,
          row_index = row_index,
          time = if (is.null(time_col)) NA_real_ else working[[time_col]][row_index],
          peak_value = values[peak],
          threshold = local_threshold,
          phasic_col = phasic_col,
          detection_method = "local_peak_above_threshold",
          stringsAsFactors = FALSE
        )
      }
    }

    summary_rows[[length(summary_rows) + 1L]] <- data.frame(
      group = group_name,
      n_samples = length(values),
      threshold = local_threshold,
      n_events = length(peaks),
      event_rate_per_1000_samples = if (length(values) > 0L) {
        length(peaks) / length(values) * 1000
      } else {
        NA_real_
      },
      stringsAsFactors = FALSE
    )
  }

  events <- if (length(event_rows) == 0L) {
    .gpbiom_empty_scr_events()
  } else {
    do.call(rbind, event_rows)
  }

  group_summary <- if (length(summary_rows) == 0L) {
    data.frame(
      group = character(),
      n_samples = integer(),
      threshold = numeric(),
      n_events = integer(),
      event_rate_per_1000_samples = numeric(),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, summary_rows)
  }

  overview <- data.frame(
    n_rows = nrow(data),
    group_count = length(groups),
    phasic_col = phasic_col,
    decomposition_used = decomposition_used,
    threshold = if (is.null(threshold)) NA_real_ else threshold,
    min_peak_distance = as.integer(min_peak_distance),
    n_events = nrow(events),
    status = if (nrow(events) > 0L) {
      "scr_events_detected"
    } else {
      "no_scr_events_detected"
    },
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    events = events,
    group_summary = group_summary,
    settings = list(
      phasic_col = phasic_col,
      signal_col = signal_col,
      time_col = time_col,
      group_cols = group_cols,
      threshold = threshold,
      min_peak_distance = as.integer(min_peak_distance),
      window_size = as.integer(window_size),
      note = paste0(
        "SCR events are simple SCR-like local peaks. Use specialised ",
        "biosignal software for confirmatory SCR event detection."
      )
    )
  )

  class(out) <- c("gazepoint_scr_events", class(out))
  out
}


.gpbiom_choose_eda_signal_column <- function(data) {
  preferred <- c(
    "GSR_US", "EDA_US", "GSR", "EDA",
    "GSR_OHMS", "SKIN_CONDUCTANCE"
  )

  existing <- preferred[preferred %in% names(data)]

  numeric_existing <- existing[vapply(existing, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(numeric_existing) > 0L) {
    return(numeric_existing[1L])
  }

  gsr_like <- names(data)[grepl("GSR|EDA|CONDUCTANCE", names(data), ignore.case = TRUE)]

  numeric_gsr_like <- gsr_like[vapply(gsr_like, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(numeric_gsr_like) > 0L) {
    return(numeric_gsr_like[1L])
  }

  NA_character_
}


.gpbiom_detect_existing_eda_components <- function(data,
                                                   tonic_col = NULL,
                                                   phasic_col = NULL) {
  if (is.null(tonic_col)) {
    tonic_candidates <- c(
      "GSR_US_TONIC", "EDA_TONIC", "GSR_TONIC",
      "TONIC", "SCL"
    )
    tonic_col <- tonic_candidates[tonic_candidates %in% names(data)][1L]
  }

  if (is.null(phasic_col)) {
    phasic_candidates <- c(
      "GSR_US_PHASIC", "EDA_PHASIC", "GSR_PHASIC",
      "PHASIC", "SCR"
    )
    phasic_col <- phasic_candidates[phasic_candidates %in% names(data)][1L]
  }

  if (length(tonic_col) == 0L || is.na(tonic_col)) {
    tonic_col <- NA_character_
  }

  if (length(phasic_col) == 0L || is.na(phasic_col)) {
    phasic_col <- NA_character_
  }

  list(tonic_col = tonic_col, phasic_col = phasic_col)
}


.gpbiom_eda_group_indices <- function(data, group_cols = NULL) {
  if (is.null(group_cols) || length(group_cols) == 0L) {
    return(list(all = seq_len(nrow(data))))
  }

  grouping <- interaction(data[group_cols], drop = TRUE, sep = " | ")
  split(seq_len(nrow(data)), grouping)
}


.gpbiom_eda_order_index <- function(data, idx, time_col = NULL) {
  if (is.null(time_col)) {
    return(idx)
  }

  idx[order(data[[time_col]][idx], na.last = TRUE)]
}


.gpbiom_scr_default_threshold <- function(values) {
  finite <- values[is.finite(values)]

  if (length(finite) == 0L) {
    return(Inf)
  }

  center <- stats::median(finite)
  spread <- stats::mad(finite, constant = 1.4826)

  if (!is.finite(spread) || spread == 0) {
    spread <- stats::sd(finite, na.rm = TRUE)
  }

  if (!is.finite(spread) || spread == 0) {
    return(max(0, center))
  }

  max(0, center + 3 * spread)
}


.gpbiom_scr_peak_indices <- function(values,
                                     threshold,
                                     min_peak_distance = 10L) {
  if (length(values) < 3L) {
    return(integer())
  }

  candidate <- which(
    is.finite(values) &
      values >= threshold &
      c(FALSE, values[-c(1L, length(values))] >= values[-c(length(values) - 1L, length(values))], FALSE) &
      c(FALSE, values[-c(1L, length(values))] >= values[-c(1L, 2L)], FALSE)
  )

  candidate <- candidate[candidate > 1L & candidate < length(values)]

  if (length(candidate) == 0L) {
    return(integer())
  }

  candidate <- candidate[order(values[candidate], decreasing = TRUE)]

  kept <- integer()

  for (idx in candidate) {
    if (length(kept) == 0L ||
        all(abs(idx - kept) >= min_peak_distance)) {
      kept <- c(kept, idx)
    }
  }

  sort(kept)
}

.gpbiom_eda_rolling_median <- function(values, window_size = 31L) {
  values <- as.numeric(values)

  if (length(values) == 0L) {
    return(numeric())
  }

  window_size <- as.integer(window_size)

  if (is.na(window_size) || window_size < 1L) {
    stop("`window_size` must be a positive integer.", call. = FALSE)
  }

  if (window_size %% 2L == 0L) {
    window_size <- window_size + 1L
  }

  half_window <- floor(window_size / 2L)
  out <- rep(NA_real_, length(values))

  for (i in seq_along(values)) {
    from <- max(1L, i - half_window)
    to <- min(length(values), i + half_window)
    window_values <- values[from:to]
    window_values <- window_values[is.finite(window_values)]

    if (length(window_values) > 0L) {
      out[i] <- stats::median(window_values)
    }
  }

  out
}

.gpbiom_empty_scr_events <- function() {
  data.frame(
    event_id = integer(),
    group = character(),
    row_index = integer(),
    time = numeric(),
    peak_value = numeric(),
    threshold = numeric(),
    phasic_col = character(),
    detection_method = character(),
    stringsAsFactors = FALSE
  )
}
