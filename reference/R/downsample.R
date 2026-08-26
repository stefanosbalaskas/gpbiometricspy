
#' Downsample Gazepoint time-series data
#'
#' Aggregates selected numeric gaze or biometric signals into fixed-width time
#' bins. Processing can be performed independently within participant, trial,
#' session, or other user-defined groups. Only occupied bins are returned; the
#' function does not fabricate observations for empty periods.
#'
#' The returned object records the number of contributing source rows for each
#' bin and stores a structured downsampling log and settings as attributes.
#'
#' @param data A data frame containing a numeric time column and one or more
#'   numeric signal columns.
#' @param time_col Name of the numeric time column.
#' @param signal_cols Optional character vector of numeric columns to aggregate.
#'   If `NULL`, all numeric columns except `time_col` and `group_cols` are used.
#' @param group_cols Optional character vector of grouping columns. Downsampling
#'   is performed independently within each group.
#' @param interval Positive width of each output time bin, expressed in the same
#'   units as `time_col`.
#' @param method Aggregation method applied to each signal within each bin:
#'   `"mean"`, `"median"`, `"first"`, or `"last"`.
#' @param na_rm Logical. If `TRUE`, missing signal values are removed before
#'   aggregation. If `FALSE`, a missing value causes mean or median aggregation
#'   for that signal-bin combination to return `NA`.
#' @param time_value Value assigned to the output time column: the bin
#'   `"start"`, bin `"center"`, or mean observed sample time (`"mean"`).
#' @param origin Optional finite numeric origin used to align the bin grid. If
#'   `NULL`, the minimum finite time across the complete input is used.
#'
#' @return A data frame with class `"gazepoint_downsampled_data"`. The output
#'   contains grouping columns, the downsampled time column, aggregated signals,
#'   and `n_source_rows`. Attributes `downsample_log` and
#'   `downsample_settings` provide provenance information.
#'
#' @examples
#' dat <- data.frame(
#'   participant = rep(c("P01", "P02"), each = 6),
#'   time_ms = rep(0:5, 2),
#'   pupil = c(3.0, 3.1, 3.2, 3.3, 3.4, 3.5,
#'             2.9, 3.0, 3.1, 3.2, 3.3, 3.4)
#' )
#'
#' downsample_gazepoint_data(
#'   dat,
#'   time_col = "time_ms",
#'   signal_cols = "pupil",
#'   group_cols = "participant",
#'   interval = 3
#' )
#'
#' @export
downsample_gazepoint_data <- function(data,
                                      time_col,
                                      signal_cols = NULL,
                                      group_cols = NULL,
                                      interval,
                                      method = c(
                                        "mean",
                                        "median",
                                        "first",
                                        "last"
                                      ),
                                      na_rm = TRUE,
                                      time_value = c(
                                        "start",
                                        "center",
                                        "mean"
                                      ),
                                      origin = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  time_col <- as.character(time_col)

  if (
    length(time_col) != 1L ||
      is.na(time_col) ||
      !nzchar(time_col)
  ) {
    stop("`time_col` must be one non-empty column name.", call. = FALSE)
  }

  if (!time_col %in% names(data)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.numeric(data[[time_col]])) {
    stop("`time_col` must be numeric.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  } else {
    group_cols <- unique(as.character(group_cols))

    if (anyNA(group_cols) || any(!nzchar(group_cols))) {
      stop(
        "`group_cols` must contain non-empty column names.",
        call. = FALSE
      )
    }

    missing_group_cols <- setdiff(group_cols, names(data))

    if (length(missing_group_cols) > 0L) {
      stop(
        "`group_cols` contains columns not found in `data`: ",
        paste(missing_group_cols, collapse = ", "),
        call. = FALSE
      )
    }

    if (time_col %in% group_cols) {
      stop(
        "`group_cols` must not include `time_col`.",
        call. = FALSE
      )
    }
  }

  if (is.null(signal_cols)) {
    numeric_cols <- names(data)[
      vapply(data, is.numeric, logical(1))
    ]

    signal_cols <- setdiff(
      numeric_cols,
      c(time_col, group_cols)
    )
  } else {
    signal_cols <- unique(as.character(signal_cols))
  }

  if (
    length(signal_cols) == 0L ||
      anyNA(signal_cols) ||
      any(!nzchar(signal_cols))
  ) {
    stop("No numeric signal columns were selected.", call. = FALSE)
  }

  missing_signal_cols <- setdiff(signal_cols, names(data))

  if (length(missing_signal_cols) > 0L) {
    stop(
      "`signal_cols` contains columns not found in `data`: ",
      paste(missing_signal_cols, collapse = ", "),
      call. = FALSE
    )
  }

  overlap_cols <- intersect(signal_cols, c(time_col, group_cols))

  if (length(overlap_cols) > 0L) {
    stop(
      "`signal_cols` must not include time or grouping columns: ",
      paste(overlap_cols, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- signal_cols[
    !vapply(data[signal_cols], is.numeric, logical(1))
  ]

  if (length(non_numeric) > 0L) {
    stop(
      "All `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  if (
    !is.numeric(interval) ||
      length(interval) != 1L ||
      !is.finite(interval) ||
      interval <= 0
  ) {
    stop(
      "`interval` must be a single positive finite number.",
      call. = FALSE
    )
  }

  if (
    !is.logical(na_rm) ||
      length(na_rm) != 1L ||
      is.na(na_rm)
  ) {
    stop("`na_rm` must be TRUE or FALSE.", call. = FALSE)
  }

  method <- match.arg(method)
  time_value <- match.arg(time_value)

  finite_times <- data[[time_col]][is.finite(data[[time_col]])]

  if (length(finite_times) == 0L) {
    stop(
      "`time_col` does not contain any finite values.",
      call. = FALSE
    )
  }

  if (is.null(origin)) {
    origin <- min(finite_times)
  } else if (
    !is.numeric(origin) ||
      length(origin) != 1L ||
      !is.finite(origin)
  ) {
    stop(
      "`origin` must be NULL or one finite numeric value.",
      call. = FALSE
    )
  }

  split_index <- if (length(group_cols) == 0L) {
    factor(rep("all", nrow(data)))
  } else {
    interaction(
      data[group_cols],
      drop = TRUE,
      lex.order = TRUE
    )
  }

  index_pieces <- split(
    seq_len(nrow(data)),
    split_index,
    drop = TRUE
  )

  output_rows <- list()
  log_rows <- list()

  for (piece_i in seq_along(index_pieces)) {
    original_index <- index_pieces[[piece_i]]
    piece <- data[original_index, , drop = FALSE]

    valid_time <- is.finite(piece[[time_col]])
    n_original_rows <- nrow(piece)
    n_invalid_time_rows <- sum(!valid_time)

    if (!any(valid_time)) {
      next
    }

    piece <- piece[valid_time, , drop = FALSE]
    piece <- piece[
      order(piece[[time_col]], na.last = TRUE),
      ,
      drop = FALSE
    ]

    times <- piece[[time_col]]
    scaled_time <- (times - origin) / interval

    tolerance <- sqrt(.Machine$double.eps) *
      pmax(1, abs(scaled_time))

    bin_id <- floor(scaled_time + tolerance)
    bin_levels <- sort(unique(bin_id))

    group_values <- if (length(group_cols) == 0L) {
      data.frame(
        segment_id = names(index_pieces)[piece_i],
        stringsAsFactors = FALSE
      )
    } else {
      piece[1L, group_cols, drop = FALSE]
    }

    source_counts <- integer(length(bin_levels))

    for (bin_i in seq_along(bin_levels)) {
      current_bin <- bin_levels[bin_i]
      bin_rows <- which(bin_id == current_bin)
      source_counts[bin_i] <- length(bin_rows)

      bin_start <- origin + current_bin * interval

      output_time <- switch(
        time_value,
        start = bin_start,
        center = bin_start + interval / 2,
        mean = mean(times[bin_rows])
      )

      output_row <- group_values
      output_row[[time_col]] <- output_time

      for (signal in signal_cols) {
        output_row[[signal]] <- .gp_downsample_value(
          piece[[signal]][bin_rows],
          method = method,
          na_rm = na_rm
        )
      }

      output_row$n_source_rows <- length(bin_rows)

      output_rows[[length(output_rows) + 1L]] <- output_row
    }

    unique_times <- sort(unique(times))
    positive_diffs <- diff(unique_times)
    positive_diffs <- positive_diffs[
      is.finite(positive_diffs) & positive_diffs > 0
    ]

    median_input_interval <- if (length(positive_diffs) > 0L) {
      stats::median(positive_diffs)
    } else {
      NA_real_
    }

    log_rows[[length(log_rows) + 1L]] <- cbind(
      group_values,
      data.frame(
        n_input_rows = n_original_rows,
        n_finite_time_rows = nrow(piece),
        n_invalid_time_rows = n_invalid_time_rows,
        n_output_rows = length(bin_levels),
        time_min = min(times),
        time_max = max(times),
        median_input_interval = median_input_interval,
        interval = interval,
        origin = origin,
        method = method,
        time_value = time_value,
        na_rm = na_rm,
        mean_source_rows_per_bin = mean(source_counts),
        min_source_rows_per_bin = min(source_counts),
        max_source_rows_per_bin = max(source_counts),
        signals = paste(signal_cols, collapse = ","),
        stringsAsFactors = FALSE
      ),
      stringsAsFactors = FALSE
    )
  }

  if (length(output_rows) == 0L) {
    stop(
      "No groups contained finite time values.",
      call. = FALSE
    )
  }

  out <- do.call(rbind, output_rows)
  log <- do.call(rbind, log_rows)

  rownames(out) <- NULL
  rownames(log) <- NULL

  attr(out, "downsample_log") <- log
  attr(out, "downsample_settings") <- list(
    time_col = time_col,
    signal_cols = signal_cols,
    group_cols = group_cols,
    interval = interval,
    method = method,
    na_rm = na_rm,
    time_value = time_value,
    origin = origin
  )

  class(out) <- unique(c(
    "gazepoint_downsampled_data",
    class(out)
  ))

  out
}

.gp_downsample_value <- function(x,
                                 method,
                                 na_rm) {
  if (isTRUE(na_rm)) {
    x <- x[!is.na(x)]
  } else if (
    method %in% c("mean", "median") &&
      anyNA(x)
  ) {
    return(NA_real_)
  }

  if (length(x) == 0L) {
    return(NA_real_)
  }

  switch(
    method,
    mean = mean(x),
    median = stats::median(x),
    first = x[1L],
    last = x[length(x)]
  )
}
